# Agent.py
# Author: Tristan Brigham

import sys
import os
import random
import time as time_module
from typing import Optional, List, Dict, Any, Union
from datetime import datetime
import pandas as pd

from Utils.path_manager import initialize_paths
initialize_paths()

# Load environment variables using centralized loader
try:
    from Utils.env_loader import load_environment
    load_environment()
except ImportError:
    # Fallback to basic dotenv loading if centralized loader not available
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        print("Warning: python-dotenv not available. Environment variables may not be loaded from .env file.")

from Agent.modules.action import Action
from Agent.modules.personal_summary import PersonalSummaryGenerator
from Agent.modules.memory_manager import MemoryManager
from Agent.modules.intent import IntentManager
from Agent.modules.perception import Perception
from Agent.modules.action_policy import ActionPolicy
from Utils.l2_data.l2_data_objects import L2DataRow
from Agent.capabilities import get_capability_context
from Agent.cognitive_modules.structured_planning import StructuredPlanner, PlanningHorizon
from Agent.modules.knowledge_base import AgentKnowledgeBase
from Agent.modules.traits import AgentTraits
from Agent.modules.opinions import OpinionsStore
from Agent.modules.policy_llm import PolicyLLM

# Import mood system
try:
    from Agent.modules.mood_system import (
    MoodState, EmotionalMomentum, MoodDecay, MoodUpdater, MoodInfluence,
    create_initial_mood, sample_emotional_momentum, sample_mood_decay
)
    MOOD_SYSTEM_AVAILABLE = True
except ImportError:
    print("Warning: Mood system not available")
    MOOD_SYSTEM_AVAILABLE = False

# Import numerical settings
try:
    from Setup.numerical_settings import numerical_settings
    NUMERICAL_SETTINGS_AVAILABLE = True
except ImportError:
    print("Warning: Numerical settings not available")
    NUMERICAL_SETTINGS_AVAILABLE = False

class Agent:
    """
    A comprehensive agent class with structured voter data objects.
    Uses categorized L2 data objects for clean, organized access to voter information.
    Comprehensive coverage of all 788 L2 data headers.
    """
    
    def __init__(self, 
                 agent_id: Union[int, str], 
                 l2_data: L2DataRow = None,
                 simulation_id: str = None):
        """
        Initialize an agent with structured L2 data.

        Args:
            agent_id (Union[int, str]): Unique identifier for the agent. Can be integer or string.
            l2_data (L2DataRow, optional): Structured L2 data object.
            simulation_id (str, optional): Simulation ID for database operations.
        
        Raises:
            ValueError: If agent_id is not valid.
        
        Note:
            For production use, agents should be created via AgentFactory to ensure L2 data is loaded.
            Direct constructor use without L2 data is discouraged.
        """
        # Validate and normalize agent_id
        if isinstance(agent_id, str):
            # Try to convert string to integer if possible
            try:
                agent_id = int(agent_id)
            except ValueError:
                # If it's a string that can't be converted to int, keep it as string
                pass
        
        if isinstance(agent_id, int):
            if agent_id <= 0:
                raise ValueError("agent_id must be a positive nonzero integer")
        elif not isinstance(agent_id, str):
            raise ValueError("agent_id must be an integer or string")
        
        self.agent_id = agent_id
        self.simulation_id = simulation_id
        
        # Timing for debugging slow agent initialization (VERBOSITY >= 3)
        verbosity = 0
        try:
            verbosity = int(os.getenv('VERBOSITY', os.getenv('VERBOSITY_LEVEL', '1')))
        except Exception:
            verbosity = 1
        t_init_start = time_module.perf_counter() if verbosity >= 3 else None
        
        # Warn if L2 data is missing (for production use, agents should have L2 data)
        if l2_data is None:
            import warnings
            warnings.warn(
                "Agent created directly without L2 data. "
                "For production use, please use AgentFactory to ensure data integrity.",
                DeprecationWarning,
                stacklevel=2
            )
        
        self.l2_data = l2_data
        
        # Lazy subsystem placeholders (instantiated on first access)
        self._action = None
        self._intent_manager = None
        self._perception = None
        self._action_planner = None
        self._action_policy = None
        self._structured_planner = None
        self._personal_summary = None
        self._memory_manager = None
        self._policy_llm = None
        self._structured_planner_warned = False
        
        # Mood system placeholders (instantiated on demand)
        self._mood_state = None
        self._emotional_momentum = None
        self._mood_decay = None
        self._mood_updater = None
        self._mood_influence = None
        self._mood_initialized = False
        
        # Initialize memory parameters
        try:
            # Memory salience and importance parameters
            self.memory_salience_param = float(os.getenv('MEMORY_SALIENCE_PARAM', '1.0'))
            self.memory_importance_param = float(os.getenv('MEMORY_IMPORTANCE_PARAM', '0.5'))
            
            # Memory time decay parameter
            time_decay_str = os.getenv('MEMORY_TIME_DECAY_PARAM', '1.0')

            # Remove any comments from the value
            time_decay_str = time_decay_str.split('#')[0].strip()
            self.memory_time_decay_param = float(time_decay_str)
            
            # Memory forgetfulness parameters
            forget_mean = float(os.getenv('MEMORY_MAX_IMPORTANCE_TO_FORGET_MEAN', '3.0'))
            forget_std = float(os.getenv('MEMORY_MAX_IMPORTANCE_TO_FORGET_STD', '0.4'))
            
            # Generate random forgetfulness from normal distribution
            self.memory_max_importance_to_forget = random.gauss(forget_mean, forget_std)
            
            # Memory persistence and retrieval parameters
            min_persist_str = os.getenv('MEMORY_MIN_PERSIST_TIME', str(60*60*24*7))
            # Remove any comments and evaluate if it's an expression
            min_persist_str = min_persist_str.split('#')[0].strip()
            try:
                self.memory_min_persist_time = int(min_persist_str)
            except ValueError:
                # Try to evaluate as expression (e.g., "60*60*24*7")
                try:
                    self.memory_min_persist_time = eval(min_persist_str)
                except:
                    self.memory_min_persist_time = 60*60*24*7  # Default 1 week
            
            # Memory top M to return
            self.memory_top_m_to_return = int(os.getenv('MEMORY_TOP_M_TO_RETURN', '7'))
            
        except Exception as e:
            print(f"Warning: Failed to initialize memory parameters: {e}")
            print(f"Full traceback:")
            import traceback
            traceback.print_exc()
            # Set fallback values
            self.memory_salience_param = 1.0
            self.memory_importance_param = 0.5
            self.memory_time_decay_param = 1.0
            self.memory_max_importance_to_forget = 3.0
            self.memory_min_persist_time = 60*60*24*7  # Default 1 week
            self.memory_top_m_to_return = 7
        
        # Initialize agent behavior parameters
        try:
            # Maximum number of recent events to track
            self.max_recent_events = int(os.getenv('AGENT_MAX_RECENT_EVENTS', '100'))
        except Exception as e:
            print(f"Warning: Failed to initialize agent behavior parameters: {e}")
            print(f"Full traceback:")
            import traceback
            traceback.print_exc()
            self.max_recent_events = 100
        
        # Store L2 data if provided
        self.l2_data = l2_data

        # Personal summaries - these are now managed centrally by SimulationsDatabaseManager
        # during bulk_initialize_agents() for optimal performance and batch processing.
        # Agents will load existing summaries from the database on demand, but do NOT
        # auto-generate during initialization to avoid duplicate API calls and slow startup.
        self.llm_summary = None
        self.l2_summary = None
        
        # If L2 data is available, generate the L2 text summary (cheap, no API call)
        # This is kept in Agent init because it's fast and doesn't require API calls
        if self.l2_data and self.personal_summary:
            t0 = time_module.perf_counter() if verbosity >= 3 else None
            try:
                self.l2_summary = self.personal_summary.create_comprehensive_l2_summary(self)
            except Exception as e:
                import traceback
                print(f"[WARNING] Could not generate L2 summary for agent {self.agent_id}: {e}")
                traceback.print_exc()
            if verbosity >= 3:
                print(f"[Agent.__init__] {agent_id}: create_comprehensive_l2_summary {time_module.perf_counter() - t0:.3f}s")
        
        # LLM summary is now pre-loaded via bulk queries before agent creation
        # This avoids per-agent database queries during initialization
        # If summary is provided during creation, it will be set externally
        # Otherwise, it remains None (can be loaded on-demand if needed)

        # variables to store the personal context
        self.personal_context = None

        # variables for the goals that the agent has
        self.immediate_goals = None             # immediate goals are goals that the agent has for the next day
        self.short_term_goals = None            # short term goals are goals that the agent has for the next week
        self.medium_term_goals = None           # medium term goals are goals that the agent has for the next month
        self.long_term_goals = None             # long term goals are goals that the agent has for the agent's lifetime

        # the value set of the agent
        self.value_set = None

        # variables for the agent's current state
        self.current_state = None

        # experiences that the agent has gone through broadly
        self.agent_experiences = None

        # core memories of the agent
        # this includes both traumatic experiences and positive experiences
        self.core_memories = None

        # variables for the agent's current environment
        self.current_environment = None
        
        # Track the last N events experienced by this agent
        self.recent_events = []
        if NUMERICAL_SETTINGS_AVAILABLE:
            self.max_recent_events = numerical_settings.AGENT_MAX_RECENT_EVENTS
        else:
            self.max_recent_events = 100  # Fallback default
        
        # Track the last 5 perceived events for mood analysis
        self.recent_perceived_events = []
        self.max_recent_perceived_events = 5
        
        # Mood system components are initialized lazily on first use
        
        # Print total Agent __init__ time at highest verbosity
        if verbosity >= 3 and t_init_start is not None:
            print(f"[Agent.__init__] {agent_id}: TOTAL __init__ time {time_module.perf_counter() - t_init_start:.3f}s")
    
    # ------------------------------------------------------------------
    # Lazy subsystem accessors
    # ------------------------------------------------------------------
    @property
    def action(self):
        if self._action is None:
            try:
                action_module = Action()
                action_module.set_agent(self)
                self._action = action_module
            except Exception as e:
                print(f"Warning: Failed to initialize action module: {e}")
                import traceback
                traceback.print_exc()
                print("Creating mock action module for offline testing")
                self._action = self._create_mock_action_module()
        return self._action
    
    @action.setter
    def action(self, value):
        self._action = value
    
    @property
    def intent_manager(self):
        if self._intent_manager is None:
            try:
                manager = IntentManager()
                manager.get_default_yale_student_intent()
                self._intent_manager = manager
            except Exception as e:
                print(f"Warning: Failed to initialize intent manager: {e}")
                import traceback
                traceback.print_exc()
                self._intent_manager = None
        return self._intent_manager
    
    @intent_manager.setter
    def intent_manager(self, value):
        self._intent_manager = value
    
    @property
    def perception(self):
        if self._perception is None:
            try:
                self._perception = Perception(self)
            except Exception as e:
                print(f"Warning: Failed to initialize perception module: {e}")
                import traceback
                traceback.print_exc()
                self._perception = None
        return self._perception
    
    @perception.setter
    def perception(self, value):
        self._perception = value
    
    @property
    def action_planner(self):
        if self._action_planner is None:
            try:
                from Agent.modules.action_planner import ActionPlanner
                self._action_planner = ActionPlanner(self)
            except Exception as e:
                print(f"Warning: Failed to initialize action planner module: {e}")
                import traceback
                traceback.print_exc()
                self._action_planner = None
        return self._action_planner
    
    @action_planner.setter
    def action_planner(self, value):
        self._action_planner = value
    
    @property
    def action_policy(self):
        if self._action_policy is None:
            try:
                self._action_policy = ActionPolicy(self)
            except Exception as e:
                print(f"Warning: Failed to initialize action policy module: {e}")
                import traceback
                traceback.print_exc()
                self._action_policy = None
        return self._action_policy
    
    @action_policy.setter
    def action_policy(self, value):
        self._action_policy = value
    
    @property
    def structured_planner(self):
        if self._structured_planner is None:
            if not self.simulation_id:
                if not self._structured_planner_warned:
                    print(f"WARNING: Agent {self.agent_id} created without simulation_id - structured planner will not be available")
                    self._structured_planner_warned = True
                return None
            try:
                self._structured_planner = StructuredPlanner(self.simulation_id)
            except Exception as e:
                print(f"ERROR: Failed to initialize StructuredPlanner for agent {self.agent_id}: {e}")
                import traceback
                traceback.print_exc()
                self._structured_planner = None
        return self._structured_planner
    
    @structured_planner.setter
    def structured_planner(self, value):
        self._structured_planner = value
    
    @property
    def personal_summary(self):
        if self._personal_summary is None:
            try:
                self._personal_summary = PersonalSummaryGenerator()
            except Exception as e:
                print(f"Warning: Failed to initialize personal summary generator: {e}")
                import traceback
                traceback.print_exc()
                self._personal_summary = None
        return self._personal_summary
    
    @personal_summary.setter
    def personal_summary(self, value):
        self._personal_summary = value
    
    @property
    def memory_manager(self):
        if self._memory_manager is None:
            try:
                self._memory_manager = MemoryManager(str(self.agent_id))
            except Exception as e:
                print(f"ERROR: Failed to initialize memory manager: {e}")
                print("Memory system is REQUIRED for agent functionality.")
                print("Please ensure Qdrant is running and all required packages are installed.")
                import traceback
                traceback.print_exc()
                raise RuntimeError(f"Memory system initialization failed: {e}")
        return self._memory_manager
    
    @memory_manager.setter
    def memory_manager(self, value):
        self._memory_manager = value
    
    @property
    def policy_llm(self):
        if self._policy_llm is None:
            try:
                api_manager = getattr(self.action, "api_manager", None)
                api_key = getattr(api_manager, "api_key", None)
                self._policy_llm = PolicyLLM(api_key=api_key)
            except Exception as e:
                print(f"Warning: Failed to initialize policy LLM: {e}")
                import traceback
                traceback.print_exc()
                self._policy_llm = None
        return self._policy_llm
    
    @policy_llm.setter
    def policy_llm(self, value):
        self._policy_llm = value
    
    # ------------------------------------------------------------------
    # Mood system helpers
    # ------------------------------------------------------------------
    def _ensure_mood_system(self):
        if not MOOD_SYSTEM_AVAILABLE:
            return
        if self._mood_initialized:
            return
        try:
            self._mood_state = create_initial_mood()
            self._emotional_momentum = sample_emotional_momentum()
            self._mood_decay = sample_mood_decay()
            api_manager = getattr(self.action, "api_manager", None)
            self._mood_updater = MoodUpdater(
                api_manager=api_manager,
                agent=self
            )
            self._mood_influence = MoodInfluence()
            verbosity = int(os.getenv('VERBOSITY_LEVEL', '1'))
            if verbosity >= 2 and self._mood_state:
                print(f"Mood State: {self._mood_state.get_mood_summary()}")
                if self._emotional_momentum:
                    print(f"Emotional Momentum: {self._emotional_momentum.momentum:.2f} ({self._emotional_momentum.get_stability_description()})")
                if self._mood_decay:
                    print(f"Mood Decay: {self._mood_decay.decay_rate:.3f} ({self._mood_decay.get_decay_description()})")
            self._mood_initialized = True
        except Exception as e:
            print(f"Warning: Failed to initialize mood system: {e}")
            import traceback
            traceback.print_exc()
            self._mood_state = None
            self._emotional_momentum = None
            self._mood_decay = None
            self._mood_updater = None
            self._mood_influence = None
            self._mood_initialized = False
    
    @property
    def mood_state(self):
        if not MOOD_SYSTEM_AVAILABLE:
            return None
        self._ensure_mood_system()
        return self._mood_state
    
    @mood_state.setter
    def mood_state(self, value):
        self._mood_state = value
        if value is not None:
            self._mood_initialized = True
    
    @property
    def emotional_momentum(self):
        if not MOOD_SYSTEM_AVAILABLE:
            return None
        self._ensure_mood_system()
        return self._emotional_momentum
    
    @emotional_momentum.setter
    def emotional_momentum(self, value):
        self._emotional_momentum = value
        if value is not None:
            self._mood_initialized = True
    
    @property
    def mood_decay(self):
        if not MOOD_SYSTEM_AVAILABLE:
            return None
        self._ensure_mood_system()
        return self._mood_decay
    
    @mood_decay.setter
    def mood_decay(self, value):
        self._mood_decay = value
        if value is not None:
            self._mood_initialized = True
    
    @property
    def mood_updater(self):
        if not MOOD_SYSTEM_AVAILABLE:
            return None
        self._ensure_mood_system()
        return self._mood_updater
    
    @mood_updater.setter
    def mood_updater(self, value):
        self._mood_updater = value
        if value is not None:
            self._mood_initialized = True
    
    @property
    def mood_influence(self):
        if not MOOD_SYSTEM_AVAILABLE:
            return None
        self._ensure_mood_system()
        return self._mood_influence
    
    @mood_influence.setter
    def mood_influence(self, value):
        self._mood_influence = value
        if value is not None:
            self._mood_initialized = True
    
    # Core identifier access
    def get_sequence(self) -> Optional[int]:
        """Get sequence number."""
        return getattr(self.l2_data, 'sequence', None) if self.l2_data else None
    
    def get_lal_voter_id(self) -> Optional[str]:
        """Get LAL voter ID."""
        # L2DataRow stores LALVOTERID as `lalvoterid`
        return getattr(self.l2_data, 'lalvoterid', None) if self.l2_data else None
    
    def get_state_voter_id(self) -> Optional[str]:
        """Get state voter ID."""
        return getattr(self.l2_data.personal, 'state_voter_id', None) if self.l2_data else None
    
    # Personal information access
    def get_name(self) -> str:
        """Get full name."""
        if not self.l2_data or not self.l2_data.personal:
            return "Unknown"
        first = self.l2_data.personal.first_name or ""
        last = self.l2_data.personal.last_name or ""
        return f"{first} {last}".strip()
    
    def get_age(self) -> Optional[int]:
        """Get age."""
        return self.l2_data.personal.age if self.l2_data else None
    
    def get_gender(self) -> Optional[str]:
        """Get gender."""
        return self.l2_data.personal.gender if self.l2_data else None
    
    def get_ethnicity(self) -> Optional[str]:
        """Get ethnicity."""
        return self.l2_data.personal.ethnicity if self.l2_data else None
    
    def get_birth_date(self) -> Optional[str]:
        """Get birth date."""
        return self.l2_data.personal.birth_date if self.l2_data else None
    
    def get_place_of_birth(self) -> Optional[str]:
        """Get place of birth."""
        return self.l2_data.personal.place_of_birth if self.l2_data else None
    
    def get_language_code(self) -> Optional[str]:
        """Get language code."""
        return self.l2_data.personal.language_code if self.l2_data else None
    
    def get_marital_status(self) -> Optional[str]:
        """Get marital status."""
        return self.l2_data.personal.marital_status if self.l2_data else None
    
    def get_religion_code(self) -> Optional[str]:
        """Get religion code."""
        return self.l2_data.personal.religion_code if self.l2_data else None
    
    # Address information access
    def get_location(self) -> str:
        """Get location string."""
        if not self.l2_data or not self.l2_data.address:
            return "Unknown"
        city = self.l2_data.address.residence_city or ""
        state = self.l2_data.address.residence_state or ""
        return f"{city}, {state}".strip(", ")
    
    def get_residence_address(self) -> Optional[str]:
        """Get full residence address."""
        return self.l2_data.address.residence_address_line if self.l2_data else None
    
    def get_residence_zip(self) -> Optional[str]:
        """Get residence ZIP code."""
        return self.l2_data.address.residence_zip if self.l2_data else None
    
    def get_mailing_address(self) -> Optional[str]:
        """Get full mailing address."""
        return self.l2_data.address.mailing_address_line if self.l2_data else None
    
    def get_mailing_location(self) -> str:
        """Get mailing location string."""
        if not self.l2_data or not self.l2_data.address:
            return "Unknown"
        city = self.l2_data.address.mailing_city or ""
        state = self.l2_data.address.mailing_state or ""
        return f"{city}, {state}".strip(", ")
    
    def get_county(self) -> Optional[str]:
        """Get county."""
        return self.l2_data.geographic.county if self.l2_data else None
    
    def get_precinct(self) -> Optional[str]:
        """Get precinct."""
        return self.l2_data.geographic.precinct if self.l2_data else None
    
    def get_congressional_district(self) -> Optional[str]:
        """Get congressional district."""
        return self.l2_data.geographic.congressional_district if self.l2_data else None
    
    def get_state_senate_district(self) -> Optional[str]:
        """Get state senate district."""
        return self.l2_data.geographic.state_senate_district if self.l2_data else None
    
    def get_state_house_district(self) -> Optional[str]:
        """Get state house district."""
        return self.l2_data.geographic.state_house_district if self.l2_data else None
    
    # Phone information access
    def has_phone_number(self) -> bool:
        """Check if has phone number."""
        return self.l2_data.phone.phone_number_available if self.l2_data else False
    
    def has_landline(self) -> bool:
        """Check if has landline."""
        return self.l2_data.phone.landline_phone_available if self.l2_data else False
    
    def has_cell_phone(self) -> bool:
        """Check if has cell phone."""
        return self.l2_data.phone.cell_phone_available if self.l2_data else False
    
    def get_landline_formatted(self) -> Optional[str]:
        """Get formatted landline number."""
        return self.l2_data.phone.landline_formatted if self.l2_data else None
    
    def get_cell_phone_formatted(self) -> Optional[str]:
        """Get formatted cell phone number."""
        return self.l2_data.phone.cell_phone_formatted if self.l2_data else None
    
    def is_do_not_call(self) -> bool:
        """Check if on do not call list."""
        return self.l2_data.phone.do_not_call if self.l2_data else False
    
    # Political information access
    def get_party(self) -> Optional[str]:
        """Get political party."""
        return self.l2_data.political.party if self.l2_data else None
    
    def get_registration_date(self) -> Optional[str]:
        """Get registration date."""
        return self.l2_data.political.registration_date if self.l2_data else None
    
    def is_active_voter(self) -> bool:
        """Check if active voter."""
        return self.l2_data.political.is_active if self.l2_data else False
    
    def get_voting_performance(self) -> str:
        """Get voting performance summary."""
        if not self.l2_data or not self.l2_data.political:
            return "Unknown"
        return self.l2_data.political.voting_performance_combined or "Unknown"
    
    def get_absentee_type(self) -> Optional[str]:
        """Get absentee type."""
        return self.l2_data.political.absentee_type if self.l2_data else None
    
    # Political flags and scores
    def is_progressive_democrat(self) -> bool:
        """Check if progressive democrat."""
        return self.l2_data.political.progressive_democrat_flag if self.l2_data else False
    
    def is_moderate_democrat(self) -> bool:
        """Check if moderate democrat."""
        return self.l2_data.political.moderate_democrat_flag if self.l2_data else False
    
    def is_moderate_republican(self) -> bool:
        """Check if moderate republican."""
        return self.l2_data.political.moderate_republican_flag if self.l2_data else False
    
    def is_conservative_republican(self) -> bool:
        """Check if conservative republican."""
        return self.l2_data.political.conservative_republican_flag if self.l2_data else False
    
    def is_likely_3rd_party_voter(self) -> bool:
        """Check if likely 3rd party voter."""
        return self.l2_data.political.likely_to_vote_3rd_party_flag if self.l2_data else False
    
    # Election history access
    def voted_in_general_2024(self) -> bool:
        """Check if voted in 2024 general election."""
        return self.l2_data.election_history.general_2024 == 'Y' if self.l2_data else False
    
    def voted_in_primary_2024(self) -> bool:
        """Check if voted in 2024 primary election."""
        return self.l2_data.election_history.primary_2024 == 'Y' if self.l2_data else False
    
    def voted_in_general_2022(self) -> bool:
        """Check if voted in 2022 general election."""
        return self.l2_data.election_history.general_2022 == 'Y' if self.l2_data else False
    
    def voted_in_general_2020(self) -> bool:
        """Check if voted in 2020 general election."""
        return self.l2_data.election_history.general_2020 == 'Y' if self.l2_data else False
    
    def get_recent_election_participation(self) -> dict:
        """Get recent election participation."""
        if not self.l2_data:
            return {}
        
        return {
            'general_2024': self.l2_data.election_history.general_2024,
            'primary_2024': self.l2_data.election_history.primary_2024,
            'general_2022': self.l2_data.election_history.general_2022,
            'primary_2022': self.l2_data.election_history.primary_2022,
            'general_2020': self.l2_data.election_history.general_2020,
            'primary_2020': self.l2_data.election_history.primary_2020
        }
    
    # FEC donor information access
    def is_fec_donor(self) -> bool:
        """Check if FEC donor."""
        return self.l2_data.fec_donor.number_of_donations > 0 if self.l2_data else False
    
    def get_fec_donations_count(self) -> Optional[int]:
        """Get number of FEC donations."""
        return self.l2_data.fec_donor.number_of_donations if self.l2_data else None
    
    def get_fec_avg_donation(self) -> Optional[str]:
        """Get FEC average donation range."""
        return self.l2_data.fec_donor.avg_donation_range if self.l2_data else None
    
    def get_fec_total_donations(self) -> Optional[str]:
        """Get FEC total donations range."""
        return self.l2_data.fec_donor.total_donations_range if self.l2_data else None
    
    def get_fec_primary_recipient(self) -> Optional[str]:
        """Get FEC primary recipient."""
        return self.l2_data.fec_donor.primary_recipient if self.l2_data else None
    
    # Economic information access
    def get_income(self) -> Optional[str]:
        """Get estimated income."""
        return self.l2_data.economic.estimated_income if self.l2_data else None
    
    def get_home_value(self) -> Optional[str]:
        """Get home value."""
        return self.l2_data.economic.home_value if self.l2_data else None
    
    def get_credit_rating(self) -> Optional[str]:
        """Get credit rating."""
        return self.l2_data.economic.credit_rating if self.l2_data else None
    
    def get_household_net_worth(self) -> Optional[str]:
        """Get household net worth."""
        return self.l2_data.economic.household_net_worth if self.l2_data else None
    
    def get_dwelling_type(self) -> Optional[str]:
        """Get dwelling type."""
        return self.l2_data.economic.dwelling_type if self.l2_data else None
    
    def get_home_square_footage(self) -> Optional[int]:
        """Get home square footage."""
        return self.l2_data.economic.home_square_footage if self.l2_data else None
    
    def get_bedrooms_count(self) -> Optional[int]:
        """Get bedrooms count."""
        return self.l2_data.economic.bedrooms_count if self.l2_data else None
    
    def has_swimming_pool(self) -> bool:
        """Check if has swimming pool."""
        return self.l2_data.economic.home_swimming_pool if self.l2_data else False
    
    def is_soho(self) -> bool:
        """Check if SOHO (Small Office/Home Office)."""
        return self.l2_data.economic.soho_indicator if self.l2_data else False
    
    # Vehicle information
    def get_primary_vehicle(self) -> dict:
        """Get primary vehicle information."""
        if not self.l2_data:
            return {}
        
        return {
            'make': self.l2_data.economic.auto_make_1,
            'model': self.l2_data.economic.auto_model_1,
            'year': self.l2_data.economic.auto_year_1
        }
    
    def get_secondary_vehicle(self) -> dict:
        """Get secondary vehicle information."""
        if not self.l2_data:
            return {}
        
        return {
            'make': self.l2_data.economic.auto_make_2,
            'model': self.l2_data.economic.auto_model_2,
            'year': self.l2_data.economic.auto_year_2
        }
    
    def get_motorcycle(self) -> dict:
        """Get motorcycle information."""
        if not self.l2_data:
            return {}
        
        return {
            'make': self.l2_data.economic.motorcycle_make_1,
            'model': self.l2_data.economic.motorcycle_model_1
        }
    
    # Credit information
    def get_credit_lines_count(self) -> Optional[int]:
        """Get number of credit lines."""
        return self.l2_data.economic.household_number_lines_of_credit if self.l2_data else None
    
    def has_credit_cards(self) -> bool:
        """Check if has credit cards."""
        return self.l2_data.economic.presence_of_cc if self.l2_data else False
    
    def has_premium_credit_cards(self) -> bool:
        """Check if has premium credit cards."""
        return self.l2_data.economic.presence_of_premium_cc if self.l2_data else False
    
    # Family information access
    def get_household_size(self) -> Optional[int]:
        """Get total household size."""
        return self.l2_data.family.total_persons if self.l2_data else None
    
    def get_adults_count(self) -> Optional[int]:
        """Get number of adults in household."""
        return self.l2_data.family.number_of_adults if self.l2_data else None
    
    def get_children_count(self) -> Optional[int]:
        """Get number of children in household."""
        return self.l2_data.family.number_of_children if self.l2_data else None
    
    def has_children(self) -> bool:
        """Check if has children."""
        return self.l2_data.family.has_children if self.l2_data else False
    
    def is_veteran(self) -> bool:
        """Check if veteran."""
        return self.l2_data.family.is_veteran if self.l2_data else False
    
    def is_single_parent(self) -> bool:
        """Check if single parent."""
        return self.l2_data.family.is_single_parent if self.l2_data else False
    
    def has_senior_adult(self) -> bool:
        """Check if has senior adult in household."""
        return self.l2_data.family.has_senior_adult if self.l2_data else False
    
    def has_young_adult(self) -> bool:
        """Check if has young adult in household."""
        return self.l2_data.family.has_young_adult if self.l2_data else False
    
    def has_disabled_person(self) -> bool:
        """Check if has disabled person in household."""
        return self.l2_data.family.disabled_in_hh if self.l2_data else False
    
    def get_household_gender(self) -> Optional[str]:
        """Get household gender composition."""
        return self.l2_data.family.household_gender if self.l2_data else None
    
    def get_household_party(self) -> Optional[str]:
        """Get household party composition."""
        return self.l2_data.family.household_party if self.l2_data else None
    
    def get_household_voters_count(self) -> Optional[int]:
        """Get number of voters in household."""
        return self.l2_data.family.household_voters_count if self.l2_data else None
    
    # Children by age
    def get_children_by_age(self) -> dict:
        """Get children count by age group."""
        if not self.l2_data:
            return {}
        
        return {
            '0-2': self.l2_data.family.children_0_2,
            '3-5': self.l2_data.family.children_3_5,
            '6-10': self.l2_data.family.children_6_10,
            '11-15': self.l2_data.family.children_11_15,
            '16-17': self.l2_data.family.children_16_17
        }
    
    # Work information access
    def get_education(self) -> Optional[str]:
        """Get education level."""
        return self.l2_data.work.education_level if self.l2_data else None
    
    def get_occupation(self) -> Optional[str]:
        """Get occupation."""
        return self.l2_data.work.occupation if self.l2_data else None
    
    def get_occupation_group(self) -> Optional[str]:
        """Get occupation group."""
        return self.l2_data.work.occupation_group if self.l2_data else None
    
    def is_business_owner(self) -> bool:
        """Check if business owner."""
        return self.l2_data.work.is_business_owner if self.l2_data else False
    
    def is_african_american_professional(self) -> bool:
        """Check if African American professional."""
        return self.l2_data.work.is_african_american_professional if self.l2_data else False
    
    def get_recent_employment(self) -> dict:
        """Get recent employment information."""
        if not self.l2_data:
            return {}
        
        return {
            'company': self.l2_data.work.recent_employment_company,
            'title': self.l2_data.work.recent_employment_title,
            'department': self.l2_data.work.recent_employment_department,
            'executive_level': self.l2_data.work.recent_employment_executive_level
        }
    
    # Market area information
    def get_market_area(self) -> dict:
        """Get market area information."""
        if not self.l2_data:
            return {}
        
        return {
            'dma': self.l2_data.market_area.designated_market_area_dma,
            'csa': self.l2_data.market_area.consumerdata_csa,
            'cbsa': self.l2_data.market_area.consumerdata_cbsa,
            'msa': self.l2_data.market_area.consumerdata_msa
        }
    
    def get_area_demographics(self) -> dict:
        """Get area demographic percentages."""
        if not self.l2_data:
            return {}
        
        return {
            'hh_with_children': self.l2_data.market_area.area_pcnt_hh_with_children,
            'married_couple_with_child': self.l2_data.market_area.area_pcnt_hh_married_couple_with_child,
            'married_couple_no_child': self.l2_data.market_area.area_pcnt_hh_married_couple_no_child,
            'spanish_speaking': self.l2_data.market_area.area_pcnt_hh_spanish_speaking,
            'median_housing_value': self.l2_data.market_area.area_median_housing_value,
            'median_hh_income': self.l2_data.market_area.area_median_hh_income,
            'median_education_years': self.l2_data.market_area.area_median_education_years
        }
    
    # Consumer information access
    def get_interests(self) -> list:
        """Get consumer interests."""
        return self.l2_data.consumer.interests if self.l2_data else []
    
    def get_donor_categories(self) -> list:
        """Get donor categories."""
        return self.l2_data.consumer.donor_categories if self.l2_data else []
    
    def get_lifestyle_categories(self) -> list:
        """Get lifestyle categories."""
        return self.l2_data.consumer.lifestyle_categories if self.l2_data else []
    
    def get_shopping_preferences(self) -> list:
        """Get shopping preferences."""
        return self.l2_data.consumer.shopping_preferences if self.l2_data else []
    
    def get_media_preferences(self) -> list:
        """Get media preferences."""
        return self.l2_data.consumer.media_preferences if self.l2_data else []
    
    def get_technology_usage(self) -> list:
        """Get technology usage."""
        return self.l2_data.consumer.technology_usage if self.l2_data else []
    
    def get_travel_preferences(self) -> list:
        """Get travel preferences."""
        return self.l2_data.consumer.travel_preferences if self.l2_data else []
    
    def get_health_interests(self) -> list:
        """Get health interests."""
        return self.l2_data.consumer.health_interests if self.l2_data else []
    
    def get_financial_interests(self) -> list:
        """Get financial interests."""
        return self.l2_data.consumer.financial_interests if self.l2_data else []
    
    # MAID/Device information
    def has_maid_data(self) -> bool:
        """Check if has MAID data."""
        return getattr(self.l2_data, 'mobile_advertising', None).maid_available if (self.l2_data and getattr(self.l2_data, 'mobile_advertising', None)) else False
    
    def has_ip_data(self) -> bool:
        """Check if has IP data."""
        return getattr(self.l2_data, 'mobile_advertising', None).maid_ip_available if (self.l2_data and getattr(self.l2_data, 'mobile_advertising', None)) else False
    
    # Comprehensive summaries
    def get_demographic_summary(self) -> str:
        """Get a human-readable demographic summary."""
        if not self.l2_data:
            return "No voter data loaded"
        
        return self.l2_data.get_demographic_summary()
    
    def get_political_summary(self) -> str:
        """Get political summary."""
        if not self.l2_data:
            return "No voter data loaded"
        
        parts = []
        if self.l2_data.political.party:
            parts.append(f"Party: {self.l2_data.political.party}")
        if self.l2_data.political.registration_date:
            parts.append(f"Registered: {self.l2_data.political.registration_date}")
        if self.l2_data.political.voting_performance_combined:
            parts.append(f"Voting: {self.l2_data.political.voting_performance_combined}")
        if self.is_fec_donor():
            parts.append("FEC Donor")
        
        return " | ".join(parts) if parts else "Limited political data"
    
    def get_economic_summary(self) -> str:
        """Get economic summary."""
        if not self.l2_data:
            return "No voter data loaded"
        
        parts = []
        if self.l2_data.economic.estimated_income:
            parts.append(f"Income: ${self.l2_data.economic.estimated_income}")
        if self.l2_data.economic.home_value:
            parts.append(f"Home: {self.l2_data.economic.home_value}")
        if self.l2_data.economic.credit_rating:
            parts.append(f"Credit: {self.l2_data.economic.credit_rating}")
        if self.is_business_owner():
            parts.append("Business Owner")
        
        return " | ".join(parts) if parts else "Limited economic data"
    
    def get_family_summary(self) -> str:
        """Get family summary."""
        if not self.l2_data:
            return "No voter data loaded"
        
        parts = []
        if self.l2_data.family.total_persons:
            parts.append(f"Household: {self.l2_data.family.total_persons} people")
        if self.has_children():
            parts.append("Has Children")
        if self.is_veteran():
            parts.append("Veteran")
        if self.l2_data.family.household_gender:
            parts.append(f"Type: {self.l2_data.family.household_gender}")
        
        return " | ".join(parts) if parts else "Limited family data"

    def get_broad_summary(self) -> str:
        """Get a broad overview summary of the agent."""
        if not self.l2_data:
            return "No voter data loaded"
        
        parts = []
        
        # Basic identity
        name = self.get_name()
        age = self.get_age()
        if name and name != "Unknown":
            parts.append(f"Name: {name}")
        if age:
            parts.append(f"Age: {age}")
        
        # Location
        location = self.get_location()
        if location and location != "Unknown":
            parts.append(f"Location: {location}")
        
        # Political
        party = self.get_party()
        if party:
            parts.append(f"Party: {party}")
        
        # Economic
        income = self.get_income()
        if income:
            parts.append(f"Income: ${income}")
        
        # Family
        household_size = self.get_household_size()
        if household_size:
            parts.append(f"Household: {household_size} people")
        
        # Work
        education = self.get_education()
        if education:
            parts.append(f"Education: {education}")
        
        # Special characteristics
        if self.has_children():
            parts.append("Has Children")
        if self.is_veteran():
            parts.append("Veteran")
        if self.is_business_owner():
            parts.append("Business Owner")
        
        return " | ".join(parts) if parts else "Limited agent data"

    def get_full_summary(self) -> str:
        """Get a comprehensive full summary of the agent."""
        if not self.l2_data:
            return "No voter data loaded"
        
        summary_lines = []
        
        # Header
        summary_lines.append(f"AGENT {self.agent_id} FULL SUMMARY")
        summary_lines.append("=" * 60)
        
        # Personal Information
        summary_lines.append("\nPERSONAL INFORMATION:")
        summary_lines.append("-" * 30)
        name = self.get_name()
        age = self.get_age()
        gender = self.get_gender()
        ethnicity = self.get_ethnicity()
        
        if name and name != "Unknown":
            summary_lines.append(f"Name: {name}")
        if age:
            summary_lines.append(f"Age: {age}")
        if gender:
            summary_lines.append(f"Gender: {gender}")
        if ethnicity:
            summary_lines.append(f"Ethnicity: {ethnicity}")
        
        # Location Information
        summary_lines.append("\nLOCATION INFORMATION:")
        summary_lines.append("-" * 30)
        location = self.get_location()
        county = self.get_county()
        precinct = self.get_precinct()
        
        if location and location != "Unknown":
            summary_lines.append(f"Residence: {location}")
        if county:
            summary_lines.append(f"County: {county}")
        if precinct:
            summary_lines.append(f"Precinct: {precinct}")
        
        # Political Information
        summary_lines.append("\nPOLITICAL INFORMATION:")
        summary_lines.append("-" * 30)
        party = self.get_party()
        reg_date = self.get_registration_date()
        voting_perf = self.get_voting_performance()
        active = self.is_active_voter()
        
        if party:
            summary_lines.append(f"Party: {party}")
        if reg_date:
            summary_lines.append(f"Registration Date: {reg_date}")
        if voting_perf and voting_perf != "Unknown":
            summary_lines.append(f"Voting Performance: {voting_perf}")
        summary_lines.append(f"Active Voter: {'Yes' if active else 'No'}")
        
        # Economic Information
        summary_lines.append("\nECONOMIC INFORMATION:")
        summary_lines.append("-" * 30)
        income = self.get_income()
        home_value = self.get_home_value()
        credit_rating = self.get_credit_rating()
        
        if income:
            summary_lines.append(f"Estimated Income: ${income}")
        if home_value:
            summary_lines.append(f"Home Value: {home_value}")
        if credit_rating:
            summary_lines.append(f"Credit Rating: {credit_rating}")
        
        # Family Information
        summary_lines.append("\nFAMILY INFORMATION:")
        summary_lines.append("-" * 30)
        household_size = self.get_household_size()
        has_children = self.has_children()
        is_veteran = self.is_veteran()
        
        if household_size:
            summary_lines.append(f"Household Size: {household_size} people")
        summary_lines.append(f"Has Children: {'Yes' if has_children else 'No'}")
        summary_lines.append(f"Is Veteran: {'Yes' if is_veteran else 'No'}")
        
        # Work Information
        summary_lines.append("\nWORK INFORMATION:")
        summary_lines.append("-" * 30)
        education = self.get_education()
        occupation = self.get_occupation()
        is_business_owner = self.is_business_owner()
        
        if education:
            summary_lines.append(f"Education: {education}")
        if occupation:
            summary_lines.append(f"Occupation: {occupation}")
        summary_lines.append(f"Business Owner: {'Yes' if is_business_owner else 'No'}")
        
        # Consumer Information
        summary_lines.append("\nCONSUMER INFORMATION:")
        summary_lines.append("-" * 30)
        interests = self.get_interests()
        donor_categories = self.get_donor_categories()
        lifestyle_categories = self.get_lifestyle_categories()
        
        if interests:
            summary_lines.append(f"Interests: {len(interests)} items")
            for interest in interests[:5]:  # Show first 5
                summary_lines.append(f"  • {interest}")
            if len(interests) > 5:
                summary_lines.append(f"  ... and {len(interests) - 5} more")
        
        if donor_categories:
            summary_lines.append(f"Donor Categories: {len(donor_categories)} categories")
        
        if lifestyle_categories:
            summary_lines.append(f"Lifestyle Categories: {len(lifestyle_categories)} categories")
        
        # Summary Statistics
        summary_lines.append("\nSUMMARY STATISTICS:")
        summary_lines.append("-" * 30)
        summary_lines.append(f"Total Interests: {len(interests)}")
        summary_lines.append(f"Total Donor Categories: {len(donor_categories)}")
        summary_lines.append(f"Total Lifestyle Categories: {len(lifestyle_categories)}")
        
        return "\n".join(summary_lines)

    def generate_personal_context(self) -> str:
        """
        Generate comprehensive personal context for the agent.
        Includes computed voting patterns, demographic information, and personal characteristics.
        """
        if not self.l2_data:
            return "No voter data available for context generation."
        
        context_parts = []
        
        # Basic identity
        name = self.get_name()
        age = self.get_age()
        gender = self.get_gender()
        ethnicity = self.get_ethnicity()
        
        if name and name != "Unknown":
            context_parts.append(f"I am {name}")
        else:
            context_parts.append("I am a registered voter")
        
        # Age and demographic information
        if age and not pd.isna(age):
            context_parts.append(f"I'm a {int(age)} year old")
        else:
            context_parts.append("I'm an adult")
        
        if gender and gender != "Unknown":
            context_parts.append(f"{'male' if gender == 'M' else 'female'}")
        
        if ethnicity and ethnicity != "Unknown" and not pd.isna(ethnicity):
            context_parts.append(f"of {ethnicity} ethnicity")
        
        # Location
        location = self.get_location()
        if location and location != "Unknown":
            context_parts.append(f"living in {location}")
        
        county = self.get_county()
        if county and not pd.isna(county):
            context_parts.append(f"in {county} County")
        
        # Political affiliation and voting behavior
        party = self.get_party()
        if party and party != "Unknown" and not pd.isna(party):
            context_parts.append(f"I'm registered as a {party}")
        
        # Compute voting patterns
        voting_stats = self._compute_voting_statistics()
        if voting_stats['total_elections'] > 0:
            presidential_rate = voting_stats['presidential_rate']
            general_rate = voting_stats['general_rate']
            primary_rate = voting_stats['primary_rate']
            
            voting_info = []
            if presidential_rate > 0:
                voting_info.append(f"{presidential_rate:.0f}% of presidential elections")
            if general_rate > 0:
                voting_info.append(f"{general_rate:.0f}% of general elections")
            if primary_rate > 0:
                voting_info.append(f"{primary_rate:.0f}% of primary elections")
            
            if voting_info:
                context_parts.append(f"I vote in {', '.join(voting_info)}")
        
        # Registration and activity
        reg_date = self.get_registration_date()
        if reg_date and not pd.isna(reg_date):
            context_parts.append(f"I've been registered to vote since {reg_date}")
        
        if not self.is_active_voter():
            context_parts.append("though I'm currently inactive")
        
        # Education and occupation
        education = self.get_education()
        occupation = self.get_occupation()
        occupation_group = self.get_occupation_group()
        
        if education and education != "Unknown" and not pd.isna(education):
            context_parts.append(f"I have {education}")
        
        if occupation and occupation != "Unknown" and not pd.isna(occupation):
            context_parts.append(f"I work as a {occupation}")
        elif occupation_group and occupation_group != "Unknown" and not pd.isna(occupation_group):
            context_parts.append(f"I work in {occupation_group}")
        
        # Business ownership
        if self.is_business_owner():
            context_parts.append("I own my own business")
        
        # Economic status
        income = self.get_income()
        home_value = self.get_home_value()
        credit_rating = self.get_credit_rating()
        
        if income and income != "Unknown" and not pd.isna(income):
            context_parts.append(f"My estimated income is {income}")
        
        if home_value and home_value != "Unknown" and not pd.isna(home_value):
            context_parts.append(f"I live in a home valued at {home_value}")
        
        if credit_rating and credit_rating != "Unknown" and not pd.isna(credit_rating):
            context_parts.append(f"My credit rating is {credit_rating}")
        
        # Family and household
        household_size = self.get_household_size()
        if household_size and not pd.isna(household_size):
            context_parts.append(f"I live in a household of {household_size} people")
        
        if self.has_children():
            children_count = self.get_children_count()
            if children_count and not pd.isna(children_count):
                context_parts.append(f"I have {int(children_count)} children")
            else:
                context_parts.append("I have children")
        
        if self.is_veteran():
            context_parts.append("I'm a military veteran")
        
        if self.is_single_parent():
            context_parts.append("I'm a single parent")
        
        # Special characteristics
        if self.has_senior_adult():
            context_parts.append("I live with senior adults")
        
        if self.has_young_adult():
            context_parts.append("I live with young adults")
        
        if self.has_disabled_person():
            context_parts.append("I live with someone who has a disability")
        
        # FEC donor status
        if self.is_fec_donor():
            donations_count = self.get_fec_donations_count()
            if donations_count and not pd.isna(donations_count):
                context_parts.append(f"I've made {donations_count} political donations")
        
        # Consumer interests and lifestyle
        interests = self.get_interests()
        if interests:
            # Group interests by category
            interest_categories = self._categorize_interests(interests)
            if interest_categories:
                context_parts.append(f"My interests include {', '.join(interest_categories)}")
        
        # Donor categories
        donor_categories = self.get_donor_categories()
        if donor_categories:
            context_parts.append(f"I donate to {', '.join(donor_categories)}")
        
        # Lifestyle categories
        lifestyle_categories = self.get_lifestyle_categories()
        if lifestyle_categories:
            context_parts.append(f"My lifestyle includes {', '.join(lifestyle_categories)}")
        
        # Vehicle information
        primary_vehicle = self.get_primary_vehicle()
        if primary_vehicle and primary_vehicle.get('make') and not pd.isna(primary_vehicle['make']):
            year = primary_vehicle.get('year', '')
            make = primary_vehicle.get('make', '')
            model = primary_vehicle.get('model', '')
            if year and make and model and not pd.isna(year) and not pd.isna(make) and not pd.isna(model):
                context_parts.append(f"I drive a {year} {make} {model}")
        
        # Phone and technology
        if self.has_cell_phone():
            context_parts.append("I have a cell phone")
        if self.has_landline():
            context_parts.append("I have a landline phone")
        
        # Market area information
        market_area = self.get_market_area()
        if market_area.get('dma') and not pd.isna(market_area['dma']):
            context_parts.append(f"I live in the {market_area['dma']} media market")
        
        # Combine all parts
        context = ". ".join(context_parts) + "."
        
        return context

    def _compute_voting_statistics(self) -> dict:
        """Compute detailed voting statistics from election history."""
        if not self.l2_data:
            return {
                'total_elections': 0,
                'presidential_rate': 0,
                'general_rate': 0,
                'primary_rate': 0,
                'recent_participation': 0
            }
        
        # Get all election history
        election_data = self.get_recent_election_participation()
        
        # Count elections by type
        presidential_elections = 0
        presidential_voted = 0
        general_elections = 0
        general_voted = 0
        primary_elections = 0
        primary_voted = 0
        total_elections = 0
        total_voted = 0
        
        # Check specific election fields
        election_fields = [
            'general_2024', 'general_2022', 'general_2020', 'general_2018', 'general_2016',
            'general_2014', 'general_2012', 'general_2010', 'general_2008', 'general_2006',
            'general_2004', 'general_2002', 'general_2000',
            'primary_2024', 'primary_2022', 'primary_2020', 'primary_2018', 'primary_2016',
            'primary_2014', 'primary_2012', 'primary_2010', 'primary_2008', 'primary_2006',
            'primary_2004', 'primary_2002', 'primary_2000'
        ]
        
        for field in election_fields:
            if hasattr(self.l2_data.election_history, field):
                value = getattr(self.l2_data.election_history, field)
                if value is not None:
                    total_elections += 1
                    if value is True:
                        total_voted += 1
                    
                    if 'general' in field:
                        general_elections += 1
                        if value is True:
                            general_voted += 1
                    elif 'primary' in field:
                        primary_elections += 1
                        if value is True:
                            primary_voted += 1
                    
                    # Presidential years (every 4 years)
                    year = int(field.split('_')[-1])
                    if year % 4 == 0:
                        presidential_elections += 1
                        if value is True:
                            presidential_voted += 1
        
        # Calculate rates
        presidential_rate = (presidential_voted / presidential_elections * 100) if presidential_elections > 0 else 0
        general_rate = (general_voted / general_elections * 100) if general_elections > 0 else 0
        primary_rate = (primary_voted / primary_elections * 100) if primary_elections > 0 else 0
        
        # Recent participation (last 3 elections)
        recent_elections = 0
        recent_voted = 0
        recent_fields = ['general_2024', 'general_2022', 'general_2020']
        for field in recent_fields:
            if hasattr(self.l2_data.election_history, field):
                value = getattr(self.l2_data.election_history, field)
                if value is not None:
                    recent_elections += 1
                    if value is True:
                        recent_voted += 1
        
        recent_participation = (recent_voted / recent_elections * 100) if recent_elections > 0 else 0
        
        return {
            'total_elections': total_elections,
            'total_voted': total_voted,
            'presidential_rate': presidential_rate,
            'general_rate': general_rate,
            'primary_rate': primary_rate,
            'recent_participation': recent_participation,
            'presidential_elections': presidential_elections,
            'general_elections': general_elections,
            'primary_elections': primary_elections
        }

    def _categorize_interests(self, interests: list) -> list:
        """Categorize interests into readable groups."""
        if not interests:
            return []
        
        categories = {
            'technology': ['Electronics_Computers', 'Computer_Home_Office', 'Consumer_Electronics', 'High_Tech_Leader'],
            'health_fitness': ['Exercise_Aerobic', 'Exercise_Running_Jogging', 'Exercise_Walking', 'Exercise_Health_Grouping', 'Exercise_Enthusiast', 'Health_Medical', 'Dieting_Weightloss'],
            'outdoor_activities': ['Outdoor_Enthusiast', 'Outdoor_Grouping', 'Outdoor_Sports_Lover', 'Camping_Hiking', 'Hunting_Shooting', 'Boating_Sailing', 'Fishing', 'Scuba_Diving'],
            'sports': ['Sports_Baseball', 'Sports_Basketball', 'Sports_Football', 'Sports_Leisure', 'Sports_Grouping', 'Sports_TV_Sports', 'Golf_Enthusiast', 'Sports_Hockey', 'Sports_Auto_Motorcycle_Racing', 'Active_Motorcycle', 'Active_Nascar', 'Active_Snow_Skiing', 'Sports_Soccer', 'Active_Tennis'],
            'arts_culture': ['Arts_And_Antiques', 'Arts_Int', 'Collectibles_Antiques', 'Collectibles_Arts', 'Cultural_Arts_Living', 'Arts_Art', 'Theater_Performing_Arts', 'Music_Collector', 'Music_Avid_Listener', 'Music_Home_Stereo', 'Musical_Instruments', 'Photography_Video_Equip', 'Photography_Int'],
            'reading_media': ['Book_Buyer', 'Book_Reader', 'Reading_Audio_Books', 'Books_Music_Audio', 'Books_Magazines', 'Books_Music_Books', 'Reading_General', 'Reading_Mags', 'Reading_Sci_Fi', 'Religious_Mags', 'Current_Affairs_Politics', 'Education_Online', 'History_Military', 'News_Financial'],
            'home_garden': ['Home_And_Garden', 'Gardening_Farming_Buyer', 'Gardening', 'House_Plants', 'High_End_Appliances', 'Home_Decor_Enthusiast', 'Home_Furnishings_Decor', 'Home_Improvement', 'Cooking_General', 'Cooking_Enthusiast'],
            'travel': ['Travel_Cruises', 'Travel_Domestic', 'Travel_Int', 'Travel_Intl', 'Luggage_Buyer', 'Travel_Grouping'],
            'automotive': ['Automotive_Buff', 'Auto_Work', 'Autoparts_Accessories', 'Auto_Buy_Interest'],
            'collecting': ['Collectibles_General', 'Collectibles_Coins', 'Lifestyle_Passion_Collectibles', 'Military_Memorabilia_Weapons', 'Collectibles_Sports_Memorabilia', 'Collector_Avid', 'Collectibles_Stamps'],
            'gaming': ['Games_Board_Puzzles', 'Games_PC_Games', 'Games_Video', 'Gaming_Int', 'Gaming_Casino'],
            'pets': ['Pets_Cats', 'Pets_Dogs', 'Pets_Multi', 'Equestrian_Int'],
            'religion': ['Religious_Contributor', 'Religious_Inspiration', 'Christian_Families'],
            'donations': ['Donor_Animal_Welfare', 'Donor_Arts_Cultural', 'Donor_Charitable_Causes', 'Donor_Childrens_Causes', 'Donor_Community_Charity', 'Donor_Environmental', 'Donor_Environmental_Issues', 'Donor_Health_Institution', 'Donor_International_Aid', 'Donor_Political_Conservative', 'Donor_Political_Liberal', 'Donor_Veterans']
        }
        
        categorized = []
        for category, keywords in categories.items():
            category_interests = [interest for interest in interests if any(keyword in interest for keyword in keywords)]
            if category_interests:
                # Convert category name to readable format
                readable_category = category.replace('_', ' ').title()
                categorized.append(readable_category)
        
        return categorized[:5]  # Limit to 5 categories to keep it concise

    def get_comprehensive_l2_summary(self) -> str:
        """Get a comprehensive L2 data-based summary."""
        if not self.personal_summary:
            return "Personal summary generator not available"
        return self.personal_summary.create_comprehensive_l2_summary(self)
    
    def get_stored_llm_summary(self) -> str:
        """
        Get the stored LLM summary from the agent's cache.
        
        NOTE: LLM summaries are now generated centrally by SimulationsDatabaseManager
        during bulk_initialize_agents() for optimal performance. This method returns
        the cached summary that was loaded during agent initialization or set manually.
        
        To generate summaries, use SimulationsDatabaseManager._ensure_llm_personal_summaries()
        which handles batch processing and bulk database inserts.
        
        Returns:
            str: The stored LLM summary, or None if no summary has been generated yet.
        """
        return self.llm_summary
    
    def has_llm_summary(self) -> bool:
        """
        Check if the agent has a stored LLM summary.
        
        Returns:
            bool: True if a summary exists, False otherwise.
        """
        return self.llm_summary is not None and self.llm_summary != "Personal summary generator not available"
    
    def clear_llm_summary(self) -> None:
        """
        Clear the stored LLM summary.
        """
        self.llm_summary = None
    
    # Personal Context getters and setters
    def get_personal_context(self):
        """Get the agent's personal context."""
        return self.personal_context
    
    def set_personal_context(self, context):
        """Set the agent's personal context."""
        self.personal_context = context
    
    # Goals getters and setters
    def get_immediate_goals(self):
        """Get the agent's immediate goals (next day)."""
        return self.immediate_goals
    
    def set_immediate_goals(self, goals):
        """Set the agent's immediate goals (next day)."""
        self.immediate_goals = goals
    
    def get_short_term_goals(self):
        """Get the agent's short-term goals (next week)."""
        return self.short_term_goals
    
    def set_short_term_goals(self, goals):
        """Set the agent's short-term goals (next week)."""
        self.short_term_goals = goals
    
    def get_medium_term_goals(self):
        """Get the agent's medium-term goals (next month)."""
        return self.medium_term_goals
    
    def set_medium_term_goals(self, goals):
        """Set the agent's medium-term goals (next month)."""
        self.medium_term_goals = goals
    
    def get_long_term_goals(self):
        """Get the agent's long-term goals (lifetime)."""
        return self.long_term_goals
    
    def set_long_term_goals(self, goals):
        """Set the agent's long-term goals (lifetime)."""
        self.long_term_goals = goals
    
    # Value set getters and setters
    def get_value_set(self):
        """Get the agent's value set."""
        return self.value_set
    
    def set_value_set(self, value_set):
        """Set the agent's value set."""
        self.value_set = value_set
    
    # Current state getters and setters
    def get_current_state(self):
        """Get the agent's current state."""
        return self.current_state
    
    def set_current_state(self, state):
        """Set the agent's current state."""
        self.current_state = state
    
    # Experiences getters and setters
    def get_agent_experiences(self):
        """Get the agent's experiences."""
        return self.agent_experiences
    
    def set_agent_experiences(self, experiences):
        """Set the agent's experiences."""
        self.agent_experiences = experiences
    
    # Core memories getters and setters
    def get_core_memories(self):
        """Get the agent's core memories."""
        return self.core_memories
    
    def set_core_memories(self, memories):
        """Set the agent's core memories."""
        self.core_memories = memories
    
    # Current environment getters and setters
    def get_current_environment(self):
        """Get the agent's current environment."""
        return self.current_environment
    
    def set_current_environment(self, environment):
        """Set the agent's current environment."""
        self.current_environment = environment
    
    # Memory management methods
    def add_memory(self, content: str, impact_score: int = None) -> bool:
        """
        Add a memory to the agent's memory system.
        
        Args:
            content: The memory content to store
            impact_score: Impact score of the memory (defaults to env setting)
            
        Returns:
            bool: True if memory was added successfully
        """
        if impact_score is None:
            impact_score = int(os.getenv('DEFAULT_MEMORY_IMPACT_SCORE', '5'))
        if self.memory_manager is None:
            print("Warning: Memory manager not available.")
            return False
        return self.memory_manager.add_memory(content, impact_score)
    
    def search_memories(self, query: str, k: int = None):
        """Search for memories similar to the query."""
        if self.memory_manager is None:
            print("Warning: Memory manager not available.")
            return []
        
        # Use agent's default k if not specified
        if k is None:
            k = getattr(self, 'memory_top_m_to_return', 7)
        
        return self.memory_manager.search_memories(query, k)
    
    def get_recent_memories(self, limit: int = None):
        """
        Get recent memories from the agent's memory system.
        
        Args:
            limit: Maximum number of memories to return (defaults to env setting)
            
        Returns:
            List of recent memory contents
        """
        if limit is None:
            limit = int(os.getenv('MEMORY_TOP_M_TO_RETURN', '10'))
        if self.memory_manager is None:
            print("Warning: Memory manager not available.")
            return []
        return self.memory_manager.get_recent_memories(limit)
    
    def get_memory_count(self) -> int:
        """Get the total number of memories for this agent."""
        if self.memory_manager is None:
            return 0
        return self.memory_manager.get_memory_count()
    
    def recall_context(self, query: str, k: int = None) -> str:
        """Recall relevant context for a given query."""
        if self.memory_manager is None:
            return ""
        
        # Use agent's default k if not specified
        if k is None:
            k = getattr(self, 'memory_top_m_to_return', 7)
        
        return self.memory_manager.recall_context(query, k)
    
    def add_experience(self, experience: str) -> bool:
        """Add an experience to the agent's memory."""
        if self.memory_manager is None:
            print("Warning: Memory manager not available.")
            return False
        return self.memory_manager.add_experience(experience)
    
    def add_observation(self, observation: str) -> bool:
        """Add an observation to the agent's memory."""
        if self.memory_manager is None:
            print("Warning: Memory manager not available.")
            return False
        return self.memory_manager.add_observation(observation)
    
    def add_interaction(self, interaction: str) -> bool:
        """Add an interaction to the agent's memory."""
        if self.memory_manager is None:
            print("Warning: Memory manager not available.")
            return False
        return self.memory_manager.add_interaction(interaction)
    
    def add_goal(self, goal: str) -> bool:
        """Add a goal to the agent's memory."""
        if self.memory_manager is None:
            print("Warning: Memory manager not available.")
            return False
        return self.memory_manager.add_goal(goal)
    
    def add_decision(self, decision: str) -> bool:
        """Add a decision to the agent's memory."""
        if self.memory_manager is None:
            print("Warning: Memory manager not available.")
            return False
        return self.memory_manager.add_decision(decision)
    
    def get_memory_summary(self) -> str:
        """Get a summary of the agent's memories."""
        if self.memory_manager is None:
            return "No memory manager available."
        return self.memory_manager.get_memory_summary()
    
    def get_top_similar_memories(self, k: int = None):
        """Get the top k most similar memories for this agent."""
        if self.memory_manager is None:
            print("Warning: Memory manager not available.")
            return []
        
        # Use agent's default k if not specified
        if k is None:
            k = getattr(self, 'memory_top_m_to_return', 7)
        
        return self.memory_manager.get_top_similar_memories(k)
    
    def get_scored_memories(self, 
                           current_context: str, 
                           k: int = None,
                           salience_param: float = None,
                           importance_param: float = None,
                           time_decay_param: float = None):
        """
        Get top k memories scored by the equation:
        score(m) = salience_param⋅semantic_similarity(m,current_context) + 
                   time_decay_param⋅recency_decay(m) + 
                   importance_param⋅importance(m)
        
        Uses agent's memory parameters if not specified.
        """
        if self.memory_manager is None:
            print("Warning: Memory manager not available.")
            return []
        
        # Use agent's memory parameters if not specified
        if k is None:
            k = getattr(self, 'memory_top_m_to_return', 7)
        if salience_param is None:
            salience_param = getattr(self, 'memory_salience_param', 1.0)
        if importance_param is None:
            importance_param = getattr(self, 'memory_importance_param', 0.5)
        if time_decay_param is None:
            time_decay_param = getattr(self, 'memory_time_decay_param', 1.0)
        
        return self.memory_manager.get_scored_memories(
            current_context, k, salience_param, importance_param, time_decay_param
        )
    
    def process_events(self, events: List['Event'], environment) -> List[Dict[str, Any]]:
        """
        Process a list of events for this agent.
        
        Args:
            events: List of events to process
            environment: Environment instance for context
            
        Returns:
            List of processing results for each event
        """
        if self.action is None:
            return []
        
        # Get agent's current state
        agent_state = self.get_current_state()
        if agent_state is None:
            agent_state = {}
        
        # Add basic agent info to state
        agent_state.update({
            'agent_id': self.agent_id,
            'name': self.get_name(),
            'age': self.get_age(),
            'location': self.get_location(),
            'party': self.get_party(),
            'occupation': self.get_occupation(),
            'education': self.get_education()
        })
        
        # Get recent action history for context
        action_history_limit = int(os.getenv('AGENT_ACTION_HISTORY_LIMIT', '20'))
        agent_actions = [action for action in environment.action_history[-action_history_limit:]
                        if action.agent_id == self.agent_id]
        
        # Get recent message history
        message_history_limit = int(os.getenv('AGENT_MESSAGE_HISTORY_LIMIT', '10'))
        history = [action.message for action in agent_actions[-message_history_limit:]]
        
        # Process events
        results = self.action.process(events, agent_state, history)
        
        # Handle memory creation for high-impact events
        for result in results:
            if result['impact_score'] >= environment.min_importance_to_save_memory:
                # Create memory using mid-tier intelligence
                memory_content = self.action.create_memory(
                    event=next(e for e in events if e.event_id == result['event_id']),
                    agent_state=agent_state,
                    history=history,
                    impact_score=result['impact_score'],
                    intelligence_level=2  # Mid-tier intelligence
                )
                
                # Store memory
                if self.memory_manager and memory_content:
                    self.memory_manager.add_memory(
                        content=memory_content,
                        impact_score=result['impact_score']
                    )
                    environment.stats['memories_created'] += 1
                
                result['memory_created'] = True
                result['memory_content'] = memory_content
        
        return results
    
    def get_processed_events(self, environment) -> List['Event']:
        """
        Get events that have been processed by this agent.
        
        Args:
            environment: Environment instance
            
        Returns:
            List of processed events for this agent
        """
        return environment.get_processed_events_for_agent(str(self.agent_id))
    
    def add_recent_event(self, event: 'Event') -> None:
        """
        Add an event to the agent's recent events list.
        Maintains only the last max_recent_events events.
        
        Args:
            event: Event object to add to recent events
        """
        self.recent_events.append(event)
        
        # Keep only the last max_recent_events
        if len(self.recent_events) > self.max_recent_events:
            self.recent_events = self.recent_events[-self.max_recent_events:]
    
    def add_perceived_event(self, event: 'Event', perception_result: Dict[str, Any]) -> None:
        """Add a perceived event to the agent's recent perceived events list for mood analysis."""
        event_data = {
            'event': {
                'event_type': event.event_type,
                'content': event.content,
                'environment': getattr(event, 'environment', 'unknown'),
                'timestamp': getattr(event, 'timestamp', time.time())
            },
            'perception_result': perception_result
        }
        
        self.recent_perceived_events.append(event_data)
        if len(self.recent_perceived_events) > self.max_recent_perceived_events:
            self.recent_perceived_events = self.recent_perceived_events[-self.max_recent_perceived_events:]
    
    def get_recent_events(self, count: int = None) -> List['Event']:
        """
        Get the agent's recent events.
        
        Args:
            count: Number of recent events to return (default: all available)
            
        Returns:
            List of recent events, most recent last
        """
        if count is None:
            return self.recent_events.copy()
        return self.recent_events[-count:] if count <= len(self.recent_events) else self.recent_events.copy()
    
    def clear_recent_events(self) -> None:
        """Clear the agent's recent events list."""
        self.recent_events.clear()
    
    # Mood System Methods
    def get_current_mood(self) -> Optional[MoodState]:
        """Get the agent's current mood state."""
        return self.mood_state if hasattr(self, 'mood_state') else None
    
    def get_emotional_momentum(self) -> Optional[EmotionalMomentum]:
        """Get the agent's emotional momentum."""
        return self.emotional_momentum if hasattr(self, 'emotional_momentum') else None
    
    def get_mood_decay(self) -> Optional[MoodDecay]:
        """Get the agent's mood decay rate."""
        return self.mood_decay if hasattr(self, 'mood_decay') else None
    
    def update_mood(self, event: 'Event', perception_result: Dict[str, Any]) -> bool:
        """
        Update the agent's mood based on an event and perception result.
        
        Args:
            event: The event that occurred
            perception_result: Result from event perception
            
        Returns:
            True if mood was updated successfully, False otherwise
        """
        if not MOOD_SYSTEM_AVAILABLE or not self.mood_updater or not self.mood_state:
            return False
        
        try:
            # Get agent context for mood update
            agent_context = self._get_mood_context()
            
            # Get emotional momentum for mood updates
            emotional_momentum = None
            if hasattr(self, 'emotional_momentum') and self.emotional_momentum:
                emotional_momentum = self.emotional_momentum.momentum
            
            # Update mood with recent event history and emotional momentum
            new_mood = self.mood_updater.update_mood(
                current_mood=self.mood_state,
                event=event,
                perception_result=perception_result,
                agent_context=agent_context,
                recent_events=self.recent_perceived_events,
                emotional_momentum=emotional_momentum
            )
            
            # Update mood state
            self.mood_state = new_mood
            
            return True
            
        except Exception as e:
            print(f"Warning: Failed to update mood: {e}")
            print(f"Full traceback:")
            import traceback
            traceback.print_exc()
            return False
    
    def get_mood_influenced_impact(self, base_impact: int) -> int:
        """
        Get impact score adjusted by current mood.
        
        Args:
            base_impact: Base impact score (1-10)
            
        Returns:
            Mood-influenced impact score (1-10)
        """
        if not MOOD_SYSTEM_AVAILABLE or not self.mood_influence or not self.mood_state:
            return base_impact
        
        try:
            return self.mood_influence.adjust_impact_score(base_impact, self.mood_state)
        except Exception as e:
            print(f"Warning: Failed to adjust impact score: {e}")
            print(f"Full traceback:")
            import traceback
            traceback.print_exc()
            return base_impact
    
    def get_mood_context_for_llm(self) -> str:
        """
        Get mood context formatted for LLM prompts.
        
        Returns:
            Formatted mood context string
        """
        if not MOOD_SYSTEM_AVAILABLE or not self.mood_influence or not self.mood_state:
            return ""
        
        try:
            return self.mood_influence.get_mood_context_prompt(self.mood_state)
        except Exception as e:
            print(f"Warning: Failed to get mood context: {e}")
            print(f"Full traceback:")
            import traceback
            traceback.print_exc()
            return ""
    
    def _get_mood_context(self) -> str:
        """Get agent context for mood updates."""
        context_parts = []
        
        if hasattr(self, 'get_name'):
            context_parts.append(f"Name: {self.get_name()}")
        
        if hasattr(self, 'get_age'):
            age = self.get_age()
            if age:
                context_parts.append(f"Age: {age}")
        
        if hasattr(self, 'get_location'):
            context_parts.append(f"Location: {self.get_location()}")
        
        if hasattr(self, 'get_party'):
            party = self.get_party()
            if party:
                context_parts.append(f"Political Party: {party}")
        
        if hasattr(self, 'get_education'):
            education = self.get_education()
            if education:
                context_parts.append(f"Education: {education}")
        
        return ", ".join(context_parts)
    
    def get_mood_summary(self) -> str:
        """
        Get a comprehensive summary of the agent's current mood.
        
        Returns:
            Formatted mood summary string
        """
        if not MOOD_SYSTEM_AVAILABLE or not self.mood_state:
            return "Mood system not available"
        
        try:
            mood = self.mood_state
            emotional_momentum = self.emotional_momentum
            
            summary = f"=== MOOD SUMMARY ===\n"
            summary += f"Overall Mood: {mood.get_overall_mood()}\n"
            summary += f"Current State: {mood.get_mood_summary()}\n\n"
            
            summary += f"MOOD AXES:\n"
            summary += f"  Valence: {mood.valence:6.1f}/10 (pleasant ↔ unpleasant)\n"
            summary += f"  Arousal: {mood.arousal:6.1f}/10 (energized ↔ lethargic)\n"
            summary += f"  Agency:  {mood.agency:6.1f}/10 (in-control ↔ powerless)\n"
            summary += f"  Social:  {mood.social_warmth:6.1f}/10 (loving ↔ indifferent)\n"
            summary += f"  Certainty:{mood.certainty:5.1f}/10 (certain ↔ uncertain)\n\n"
            
            if emotional_momentum:
                summary += f"EMOTIONAL MOMENTUM:\n"
                summary += f"  Momentum: {emotional_momentum.momentum:5.2f}\n"
                summary += f"  Adaptability: {emotional_momentum.get_adaptability_factor():5.2f}\n"
                summary += f"  Description: {emotional_momentum.get_stability_description()}\n\n"
            
            if hasattr(self, 'mood_decay') and self.mood_decay:
                summary += f"MOOD DECAY:\n"
                summary += f"  Rate: {self.mood_decay.decay_rate:5.3f}\n"
                summary += f"  Description: {self.mood_decay.get_decay_description()}\n\n"
            
            summary += f"LAST UPDATE:\n"
            summary += f"  Time: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(mood.timestamp))}\n"
            summary += f"  Event: {mood.event_id or 'Initial'}\n"
            summary += f"  Reason: {mood.update_reason}\n"
            
            return summary
            
        except Exception as e:
            return f"Mood summary error: {e}"
    
    # Intent System Methods
    def get_mood_context(self) -> str:
        """Get mood context for the perception system."""
        if not MOOD_SYSTEM_AVAILABLE or not self.mood_influence or not self.mood_state:
            return ""
        
        try:
            return self.mood_influence.get_mood_context_prompt(self.mood_state)
        except Exception as e:
            print(f"Warning: Failed to get mood context: {e}")
            print(f"Full traceback:")
            import traceback
            traceback.print_exc()
            return ""
    
    def get_mood_influence(self) -> float:
        """Get mood influence factor for action scoring."""
        if not MOOD_SYSTEM_AVAILABLE or not self.mood_influence or not self.mood_state:
            return 1.0
        
        try:
            # Return a multiplier based on mood state
            mood = self.mood_state
            # Positive mood increases action utility, negative mood decreases it
            if mood.valence > 5:
                return 1.0 + (mood.valence - 5) * 0.1  # Up to 1.5x for very positive mood
            else:
                return 1.0 - (5 - mood.valence) * 0.1  # Down to 0.5x for very negative mood
        except Exception as e:
            print(f"Warning: Failed to get mood influence: {e}")
            return 1.0
    
    def perceive_and_update(self, events: List["Event"]) -> None:
        """
        Main method for perception and goal updates.
        """
        if self.perception:
            self.perception.perceive_and_update(events)
        else:
            print("Warning: Perception module not available")
    
    def get_action_plan(self) -> Optional[Dict[str, Any]]:
        """
        Get the best action plan based on current goals and values.
        """
        if self.action_policy:
            return self.action_policy.get_action_plan()
        else:
            print("Warning: Action policy module not available")
            return None
    
    def get_intent_summary(self) -> str:
        """
        Get a comprehensive summary of the agent's current intent state.
        """
        if not self.intent_manager:
            return "Intent system not available"
        
        try:
            summary = "=== INTENT SUMMARY ===\n\n"
            
            # Values
            summary += "VALUES:\n"
            for value in self.intent_manager.values.values():
                summary += f"  {value.name}: {value.weight:.2f} (plasticity: {value.plasticity:.2f})\n"
            summary += "\n"
            
            # Goals by horizon
            for horizon, goals in self.intent_manager.goals.items():
                active_goals = [g for g in goals if not g.done]
                if active_goals:
                    summary += f"{horizon.value.upper()} GOALS:\n"
                    for goal in active_goals[:5]:  # Show top 5
                        summary += f"  - {goal.description} (priority: {goal.priority:.2f}, progress: {goal.progress:.1%})\n"
                    summary += "\n"
            
            # Current context
            if self.intent_manager.context:
                context = self.intent_manager.context
                summary += "CURRENT CONTEXT:\n"
                summary += f"  Where: {context.where}\n"
                summary += f"  What: {context.what}\n"
                summary += f"  Why: {context.why}\n"
                summary += f"  Constraints: {', '.join(context.constraints)}\n"
                summary += f"  Opportunities: {', '.join(context.opportunities)}\n"
            
            return summary
            
        except Exception as e:
            print(f"Intent summary error: {e}")
            print(f"Full traceback:")
            import traceback
            traceback.print_exc()
            return f"Intent summary error: {e}"
    
    def _create_mock_action_module(self):
        """Create a minimal mock action module for testing when API is not available."""
        class MockActionModule:
            def __init__(self, agent):
                self.agent = agent
                # Add api_manager attribute to prevent mood system errors
                self.api_manager = None
            
            def set_agent(self, agent):
                self.agent = agent
            
            def perceive(self, event, agent_state, history, intelligence_level=None, max_tokens=None, temperature=None):
                """Mock perceive method that simulates realistic perception analysis."""
                event_type = getattr(event, 'event_type', 'unknown')
                content = getattr(event, 'content', 'No content')
                environment = getattr(event, 'environment', 'unknown')
                
                # Simulate realistic perception based on event type
                if event_type == 'interaction':
                    perception = f"This is a social interaction that involves {content[:50]}... I should pay attention to the social dynamics and any information shared."
                    impact_score = 5
                    should_analyze = True
                    analysis_type = 'social_context'
                elif event_type == 'message':
                    perception = f"I received a message: {content[:50]}... This requires my attention and response."
                    impact_score = 4
                    should_analyze = True
                    analysis_type = 'communication'
                elif event_type == 'environmental_change':
                    perception = f"I notice a change in my environment: {content[:50]}... This affects my current situation."
                    impact_score = 3
                    should_analyze = False
                    analysis_type = 'immediate_reaction'
                else:
                    perception = f"I observe: {content[:50]}... This event has moderate significance."
                    impact_score = 3
                    should_analyze = False
                    analysis_type = 'immediate_reaction'
                
                return {
                    'perception': perception,
                    'impact_score': impact_score,
                    'should_analyze': should_analyze,
                    'analysis_type': analysis_type,
                    'memory_retrieved': False,
                    'memory_content': None
                }
            
            def create_memory(self, event, agent_state, history, impact_score=None, intelligence_level=None, max_tokens=None, temperature=None):
                """Mock create_memory method that simulates realistic memory creation."""
                event_type = getattr(event, 'event_type', 'unknown')
                content = getattr(event, 'content', 'No content')
                environment = getattr(event, 'environment', 'unknown')
                
                # Create realistic interpretation based on event type
                if event_type == 'interaction':
                    interpretation = f"I had a meaningful interaction that {content[:100]}... This interaction enriched my day and provided new information."
                elif event_type == 'message':
                    interpretation = f"I received an important message about {content[:100]}... This communication helped me stay connected and informed."
                elif event_type == 'environmental_change':
                    interpretation = f"I experienced a change in my environment: {content[:100]}... This is part of my daily routine and helps me maintain a sense of normalcy."
                else:
                    interpretation = f"I observed an event: {content[:100]}... This experience contributed to my understanding of my current situation."
                
                return interpretation
        
        return MockActionModule(self)
    
    def __str__(self):
        """String representation of the agent."""
        base_info = f"Agent(agent_id={self.agent_id})"
        if self.l2_data:
            return f"{base_info} - {self.get_demographic_summary()}"
        return base_info

    # Planning and acting within a world
    def plan_and_act(self, goal: str, world) -> Dict[str, Any]:
        # Attach environment reference transiently for planner dry_run
        self.environment = world
        caps = get_capability_context(self, world)
        ctx = {
            "capabilities": caps,
            "world_notes": "single firm; Travel has zero cost; prices posted",
        }
        plan = self.action_planner.create_plan(goal, ctx) if self.action_planner else None
        out = {"goal": goal, "executed": [], "skipped": []}
        if not plan:
            return out
        now = world.now()
        for step in plan.steps:
            res = world.interpreter.commit(
                agent_id=str(self.agent_id),
                action_name=step.op,
                params=step.params,
                now=now,
                firm_id=step.params.get("counterparty")
            )
            if res.get("ok"):
                out["executed"].append({"step": step.__dict__, "events": res.get("events", [])})
                # Persist minimal action log for frontend reporting
                try:
                    from Setup.Database import log_action as _log_action
                    _log_action(world.simulation_id, str(self.agent_id), step.op, step.params)
                except Exception:
                    pass
                # Persist transactions for retail payments
                try:
                    from Setup.Database import log_transaction as _log_txn
                    cp = step.params.get("counterparty")
                    for evt in res.get("events", []):
                        if evt.get("event_type") == "retail_payment_received":
                            meta = evt.get("metadata", {})
                            amount = float(meta.get("amount", 0.0))
                            order_id = meta.get("order_id")
                            if amount and cp:
                                _log_txn(
                                    simulation_id=world.simulation_id,
                                    firm_id=str(cp),
                                    agent_id=str(self.agent_id),
                                    transaction_type="retail_payment",
                                    amount=amount,
                                    description=f"Payment for order {order_id}" if order_id else "Retail payment",
                                    transaction_id=str(order_id) if order_id else None,
                                    metadata={"plan_goal": goal, "items": step.params.get("receive", {})}
                                )
                except Exception:
                    pass
            else:
                out["skipped"].append({"step": step.__dict__, "error": res.get("error")})
        # Clear environment reference
        try:
            delattr(self, 'environment')
        except Exception:
            pass
        return out

    def _build_situation_card(self, world, current_datetime: datetime) -> Dict[str, Any]:
        """Builds the SituationCard for the agent."""
        # Use real L2 personal summaries
        personal_summary = self.llm_summary or self.l2_summary or self.get_broad_summary()
        
        # Get current goals (from intent manager or default)
        current_goals = [g.description for g in self.intent_manager.get_active_goals()] if self.intent_manager else ["perform daily activities"]
        
        # Get constraints (cash, time, attention)
        constraints = {
            "cash": 100.0, 
            "time_minutes_remaining": getattr(self, 'time_budget_minutes', 60 * 16),
            "attention_units_remaining": getattr(self, 'attention_budget_minutes', 60 * 8)
        }
        
        # Get traits
        traits_data = self.traits.to_dict() if hasattr(self, 'traits') else {}
        
        # Knowledge snapshot
        knowledge_snapshot = self.knowledge.list_all_known_entities() if hasattr(self, 'knowledge') else []
        
        # Opinions excerpt
        opinions_excerpt = self.opinions.get_all_opinions_summary() if hasattr(self, 'opinions') else {}
        
        # Recent events (from agent's recent_events list)
        recent_events_summary = [f"{e.event_type}: {e.content}" for e in self.get_recent_events(count=5)]
        
        # Telemetry summary
        telemetry_summary = {
            "attention_spent_today": 60 * 8 - getattr(self, 'attention_budget_minutes', 60 * 8),
            "actions_executed_today": getattr(self, 'actions_executed_today', 0),
            "net_time_leftover": getattr(self, 'time_budget_minutes', 60 * 16),
            "conversions_today": getattr(self, 'conversions_today', 0),
            "holdouts_today": getattr(self, 'holdouts_today', 0)
        }
        
        situation_card = {
            "agent_id": str(self.agent_id),
            "current_time": current_datetime.isoformat(),
            "agent_profile": {
                "name": self.get_name(),
                "age": self.get_age(),
                "gender": self.get_gender(),
                "location": self.get_location(),
                "personal_summary": personal_summary
            },
            "goals": current_goals,
            "constraints": constraints,
            "traits": traits_data,
            "knowledge_snapshot": knowledge_snapshot,
            "opinions_excerpt": opinions_excerpt,
            "recent_events": recent_events_summary,
            "telemetry_summary": telemetry_summary
        }
        return situation_card

    def create_day_plan(self, goal: str, world_context: str) -> Optional[int]:
        """
        Creates a structured day plan for the agent to achieve a specific goal.

        Args:
            goal (str): The goal for the day plan.
            world_context (str): The context of the world for planning.

        Returns:
            Optional[int]: Plan ID if successful, None otherwise.
        """
        # attach new modules if missing
        if not hasattr(self, 'knowledge') or self.knowledge is None:
            self.knowledge = AgentKnowledgeBase()
        if not hasattr(self, 'traits') or self.traits is None:
            try:
                self.traits = AgentTraits.from_l2(self.l2_data)
            except Exception:
                self.traits = AgentTraits(0.5, 0.5, 0.5, 0.5, 0.5)
        if not hasattr(self, 'opinions') or self.opinions is None:
            self.opinions = OpinionsStore()
        if not hasattr(self, 'policy_llm') or self.policy_llm is None:
            try:
                api_key = self.action.api_manager.api_key if self.action and hasattr(self.action, 'api_manager') else None
                self.policy_llm = PolicyLLM(api_key=api_key)
            except Exception:
                self.policy_llm = None

        # build situation card
        sc = {
            "agent_profile": {
                "id": str(self.agent_id),
                "personal_summary": self.l2_summary or self.get_broad_summary(),
            },
            "goals": [goal],
            "constraints": {
                "cash": None,
                "time": 24*60,
                "attention": 100,
            },
            "traits": getattr(self, 'traits').__dict__ if getattr(self, 'traits', None) else {},
            "knowledge": {
                "known_firms": [ke.entity_id for ke in self.knowledge.list_by_kind("firm", 0.3)],
                "known_places": [ke.entity_id for ke in self.knowledge.list_by_kind("place", 0.3)],
                "known_channels": [ke.entity_id for ke in self.knowledge.list_by_kind("channel", 0.3)],
                "known_roles": [ke.attrs.get("role") for ke in self.knowledge.list_by_kind("role", 0.3)],
            },
            "opinions": {
                "places": {pid: vars(op) for pid, op in getattr(self.opinions, 'places', {}).items()},
            },
            "credibility": {},
            "recent_events": [],
            "telemetry_summary": {},
        }

        # call policy llm first; fallback to structured planner
        if self.policy_llm:
            try:
                plan_obj = self.policy_llm.decide_day_plan(sc, affordances={})
                if isinstance(plan_obj, dict) and plan_obj.get("plan_steps"):
                    # store via structured planner if available
                    if not self.structured_planner:
                        return None
                    return self.structured_planner.create_plan(
                        agent=self,
                        goal=goal,
                        horizon=PlanningHorizon.DAY,
                        world_context=world_context
                    )
            except Exception:
                pass

        if not self.structured_planner:
            return None
        return self.structured_planner.create_plan(
            agent=self,
            goal=goal,
            horizon=PlanningHorizon.DAY,
            world_context=world_context
        )
