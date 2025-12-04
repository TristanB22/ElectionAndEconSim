#!/usr/bin/env python3
"""
Action Module for Agent Cognitive Processing

Handles agent perception and reaction to events using language model reasoning.
"""

import sys
import os
import re
import time
from typing import List, Dict, Any, Optional

# Add the project root to the path to import Utils
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.append(project_root)

from Utils.api_manager import APIManager

# Import testing components
try:
    from Setup.testing_config import is_testing_mode, should_mock_llm
    from Setup.mock_llm_client import get_mock_llm_client
    TESTING_AVAILABLE = True
except ImportError:
    TESTING_AVAILABLE = False
    is_testing_mode = lambda: False
    should_mock_llm = lambda: False
    get_mock_llm_client = lambda: None

# Import numerical settings
try:
    from Setup.numerical_settings import numerical_settings
    NUMERICAL_SETTINGS_AVAILABLE = True
except ImportError:
    print("Warning: Numerical settings not available in Action module")
    NUMERICAL_SETTINGS_AVAILABLE = False

class Action:
    """
    Handles agent perception and reaction to events using language model reasoning.
    
    INTENSITY THRESHOLDS:
    - MEMORY_RETRIEVAL_THRESHOLD: When an event has impact score >= this value, the agent
      will look to their memory for similar situations to provide context for decision-making.
      This triggers a similarity search in the agent's vector memory.
      
    - MEMORY_CREATION_THRESHOLD: Only events with impact score >= this value will be stored
      as long-term memories in the agent's memory system. Events below this threshold
      are processed but not permanently stored.
      
    MEMORY FLOW:
    1. Event occurs → perceive() analyzes and scores impact (1-10)
    2. If score >= retrieval threshold → retrieve_memory() searches for similar past experiences
    3. If score >= creation threshold → create_memory() generates and stores long-term memory
    4. Lower impact events are processed but not stored permanently
    """
    
    # Formal intensity thresholds for memory management - loaded from configuration
    MEMORY_RETRIEVAL_THRESHOLD = 3  # Default, will be updated in __init__
    MEMORY_CREATION_THRESHOLD = 4   # Default, will be updated in __init__
    
    # LLM configuration parameters - loaded from configuration
    PERCEPTION_INTELLIGENCE_LEVEL = 3  # Use highest intelligence for perception
    MEMORY_CREATION_INTELLIGENCE_LEVEL = 3  # Use highest intelligence for memory creation
    TEST_CONNECTION_INTELLIGENCE_LEVEL = 3  # Use highest intelligence for testing
    
    PERCEPTION_MAX_TOKENS = 300  # Default, will be updated in __init__
    MEMORY_CREATION_MAX_TOKENS = 500  # Default, will be updated in __init__
    TEST_CONNECTION_MAX_TOKENS = 10  # Default, will be updated in __init__
    
    PERCEPTION_TEMPERATURE = 0.3  # Default, will be updated in __init__
    MEMORY_CREATION_TEMPERATURE = 0.4  # Default, will be updated in __init__
    
    # Memory similarity search parameter
    MEMORY_SIMILARITY_SEARCH_K = 3  # Default, will be updated in __init__
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the action module.
        
        Args:
            api_key (str, optional): DEPRECATED. API key is now loaded centrally from APIManager singleton.
        """
        # Use centralized APIManager singleton
        self.api_manager = APIManager.get_instance(api_key)
        
        # Load configuration from numerical settings if available
        if NUMERICAL_SETTINGS_AVAILABLE:
            self._load_configuration()
        
        # Only test connection if not in testing mode
        try:
            from Setup.testing_config import is_testing_mode
            if not is_testing_mode():
                # Test the connection with default intelligence level
                if not self.api_manager.test_connection(self.TEST_CONNECTION_INTELLIGENCE_LEVEL):
                    raise Exception(f"Failed to connect to API")
        except ImportError:
            # If testing config not available, test connection
            if not self.api_manager.test_connection(self.TEST_CONNECTION_INTELLIGENCE_LEVEL):
                raise Exception(f"Failed to connect to API")
    
    def _load_configuration(self):
        """Load configuration from numerical settings."""
        try:
            # Memory thresholds
            self.MEMORY_RETRIEVAL_THRESHOLD = numerical_settings.MEMORY_RETRIEVAL_THRESHOLD
            self.MEMORY_CREATION_THRESHOLD = numerical_settings.MEMORY_CREATION_THRESHOLD
            
            # LLM configuration
            self.PERCEPTION_INTELLIGENCE_LEVEL = numerical_settings.PERCEPTION_INTELLIGENCE_LEVEL
            self.MEMORY_CREATION_INTELLIGENCE_LEVEL = numerical_settings.MEMORY_CREATION_INTELLIGENCE_LEVEL
            self.TEST_CONNECTION_INTELLIGENCE_LEVEL = numerical_settings.TEST_CONNECTION_INTELLIGENCE_LEVEL
            
            self.PERCEPTION_MAX_TOKENS = numerical_settings.PERCEPTION_MAX_TOKENS
            self.MEMORY_CREATION_MAX_TOKENS = numerical_settings.MEMORY_CREATION_MAX_TOKENS
            self.TEST_CONNECTION_MAX_TOKENS = numerical_settings.TEST_CONNECTION_MAX_TOKENS
            
            self.PERCEPTION_TEMPERATURE = numerical_settings.PERCEPTION_TEMPERATURE
            self.MEMORY_CREATION_TEMPERATURE = numerical_settings.MEMORY_CREATION_TEMPERATURE
            
            # Memory similarity search
            self.MEMORY_SIMILARITY_SEARCH_K = numerical_settings.MEMORY_SIMILARITY_SEARCH_K
            
        except Exception as e:
            print(f"Warning: Failed to load configuration: {e}")
            print(f"Full traceback:")
            import traceback
            traceback.print_exc()
            # Keep default values
    
    def set_agent(self, agent: 'Agent'):
        """
        Set the agent reference for memory access.
        
        Args:
            agent: The agent instance that owns this Action module
        """
        self.agent = agent
    
    def process(self, events: List['Event'], agent_state: Dict[str, Any], history: List[str] = None) -> List[Dict[str, Any]]:
        """
        Process a list of events for the agent.
        
        Args:
            events: List of events to process
            agent_state: Current state of the agent
            history: List of previous events/actions in chronological order
            
        Returns:
            List of processing results for each event
        """

        # initialize the history if it is not provided
        if history is None:
            history = []
        
        # process each event
        results = []
        for event in events:
        
            # perceive the event
            # this returns a dictionary with the following keys:
            # - perception: the agent's perception of the event
            # - impact_score: the impact score of the event
            # - should_analyze: whether the agent should analyze the event in historical context
            # - analysis_type: the type of analysis to perform (historical_context or immediate_reaction)
            # - memory_retrieved: whether the agent retrieved a memory for the event
            # - memory_content: the content of the memory retrieved for the event
            # Enrich agent_state with internal context if available
            enriched_state = dict(agent_state or {})
            try:
                if hasattr(self, 'agent') and self.agent is not None:
                    # Attach name and basic persona if missing
                    if hasattr(self.agent, 'get_name') and 'name' not in enriched_state:
                        enriched_state['name'] = self.agent.get_name()
                    # Attach intent values summary if available
                    if hasattr(self.agent, 'intent_manager') and self.agent.intent_manager:
                        try:
                            values_dict = {v.name: v.weight for v in self.agent.intent_manager.values.values()}
                            enriched_state['intent_values'] = values_dict
                        except Exception:
                            pass
                    # Attach personal summary if available
                    if hasattr(self.agent, 'llm_summary') and self.agent.llm_summary:
                        enriched_state['personal_summary'] = self.agent.llm_summary
            except Exception:
                pass

            result = self.perceive(event, enriched_state, history)
            
            # create memory if the impact score meets the threshold
            memory_content = ""
            memory_created = False
            if result['impact_score'] >= self.MEMORY_CREATION_THRESHOLD:
                # Use medium intelligence for first-person memory writing
                memory_content = self.create_memory(
                    event,
                    enriched_state,
                    history,
                    result['impact_score'],
                    intelligence_level=2  # medium
                )
                memory_created = bool(memory_content)
            
            results.append({
                'event_id': event.event_id,
                'event_type': event.event_type,
                'content': event.content,
                'perception': result['perception'],
                'impact_score': result['impact_score'],
                'should_analyze': result['should_analyze'],
                'analysis_type': result['analysis_type'],
                'memory_retrieved': result.get('memory_retrieved', False),
                'memory_content': memory_content,
                'memory_created': memory_created
            })
        
        return results
    
    def perceive(self, 
                event: 'Event', 
                agent_state: Dict[str, Any], 
                history: List[str] = None,
                intelligence_level: int = None,
                max_tokens: int = None,
                temperature: float = None
              ) -> Dict[str, Any]:
        """
        Perceive and analyze an event to understand what the agent thinks about the experience.
        
        Args:
            event: Event object to analyze
            agent_state: Current state of the agent
            history: List of previous events/actions in chronological order
            intelligence_level: Intelligence level for LLM analysis (defaults to env setting)
            max_tokens: Maximum tokens for the response (defaults to env setting)
            temperature: Temperature for response generation (defaults to env setting)
            
        Returns:
            Dict containing perception analysis, impact score, and memory decision
        """
        # Use environment defaults if not specified
        if intelligence_level is None:
            intelligence_level = self.PERCEPTION_INTELLIGENCE_LEVEL
        if max_tokens is None:
            max_tokens = self.PERCEPTION_MAX_TOKENS
        if temperature is None:
            temperature = self.PERCEPTION_TEMPERATURE
        
        # initialize the history if it is not provided
        if history is None:
            history = []
        
        # format the history for the prompt
        history_text = ""
        if history:
            history_limit = int(os.getenv('PERCEPTION_HISTORY_LIMIT', '5'))
            history_text = "\n".join([f"- {event}" for event in history[-history_limit:]])  # Last N events
        
        # format agent state
        agent_state_text = "\n".join([f"- {key}: {value}" for key, value in agent_state.items()])
        
        # Add mood context if available
        mood_context = ""
        if hasattr(self, 'agent') and hasattr(self.agent, 'get_mood_context_for_llm'):
            mood_context = self.agent.get_mood_context_for_llm()
        
        # construct the perception prompt
        prompt = f"""You are an intelligent agent analyzing an event in a simulation. Respond as if you are personally experiencing this event.

EVENT TO ANALYZE:
Type: {event.event_type}
Content: {event.content}
Source: {event.source or 'Unknown'}
Priority: {getattr(event, 'priority', 'N/A')}/10

YOUR CURRENT STATE:
{agent_state_text}

RECENT HISTORY:
{history_text if history_text else "No recent events"}

{mood_context if mood_context else ""}

ANALYSIS TASK:
1. Determine if this event should be analyzed in historical context (consider past events) or if it's something to react to immediately
2. Score the personal impact of this event on a scale of 1-10. This should effectively define how memorable an event is -- that is, how long it might stay in your memory and influence your life:
   - 1: Routine and dull daily activities (for example, eating breakfast alone, staring into space)
   - 3: Variations from routine (for example, breakfast had an issue with it, driving to work was delayed)
   - 5: Moderate events (for example, meeting new people, getting a strong score on a standardized test)
   - 7: Significant events (for example, getting a promotion at work, getting a new car)
   - 10: Life-changing events (for example, a family member passing, getting married, winning a lottery)

RESPOND WITH ONLY:
ANALYSIS_TYPE: <historical_context|immediate_reaction>
IMPACT_SCORE: <1-10>
REASONING: <brief explanation in first person about how this affects you>

Example:
ANALYSIS_TYPE: immediate_reaction
IMPACT_SCORE: 3
REASONING: I've experienced this type of event many times before with only slight variations, so it will likely only impact me for the rest of the day at most."""
        
        try:
            # Check if we should use testing mode
            if TESTING_AVAILABLE and should_mock_llm():
                # Use mock LLM client for testing
                mock_client = get_mock_llm_client()
                if mock_client:
                    # Create mock event for testing
                    from Setup.testing_config import MockEvent
                    mock_event = MockEvent(
                        event_id=getattr(event, 'event_id', 1),
                        event_type=event.event_type,
                        content=event.content,
                        timestamp=getattr(event, 'timestamp', time.time())
                    )
                    
                    # Get agent context for personalization
                    agent_context = ""
                    if hasattr(self, 'agent') and hasattr(self.agent, 'get_name'):
                        agent_context = f"{self.agent.get_name()}, age {getattr(self.agent, 'age', 'unknown')}"
                    
                    # Get mock perception response
                    mock_result = mock_client.perceive_event(mock_event, agent_context)
                    
                    # Format response to match expected format
                    response = f"ANALYSIS_TYPE: {mock_result['analysis_type']}\nIMPACT_SCORE: {mock_result['impact_score']}\nREASONING: {mock_result['perception']}"
                    model_name = "mock-llm-testing"
                else:
                    # Fallback to real API if mock client not available
                    response, _, model_name, _ = self.api_manager.make_request(
                        prompt=prompt,
                        intelligence_level=intelligence_level,
                        max_tokens=max_tokens,
                        temperature=temperature
                    )
            else:
                # Use real LLM API
                response, _, model_name, _ = self.api_manager.make_request(
                    prompt=prompt,
                    intelligence_level=intelligence_level,
                    max_tokens=max_tokens,
                    temperature=temperature
                )
            
            # Parse the LLM response with validation and retry logic.
            # This loop attempts to robustly extract the required fields from the LLM output,
            # retrying up to max_retries times if the response is invalid or cannot be parsed.
            max_retries = 3  # Maximum number of parsing/validation attempts
            last_error = None  # Store the last error encountered for reporting

            for attempt in range(max_retries):
                try:
                    # Attempt to parse the LLM response using the dedicated parser.
                    # The parser should return a dict with 'is_valid', parsed values, and 'errors'.
                    parse_result = self._parse_perception_response(response)
                    if parse_result['is_valid']:
                        # If parsing and validation succeed, extract the required fields.
                        analysis_type = parse_result['analysis_type']
                        impact_score = parse_result['impact_score']
                        reasoning = parse_result['reasoning']
                        break  # Exit the retry loop on success
                    else:
                        # If validation fails, record the error and prepare for a retry.
                        last_error = parse_result['errors']
                        if attempt < max_retries - 1:
                            # If retries remain, modify the prompt to request correction
                            print(f"Perception response validation failed (attempt {attempt + 1}/{max_retries}): {last_error}")
                            # Add explicit correction instructions to the prompt for the next LLM call.
                            prompt += f"\n\nCORRECTION NEEDED: Your previous response was invalid. {last_error}"
                            prompt += "\nPlease fix the format and try again."
                            
                            # Request a new response from the LLM with the updated prompt.
                            response, _, model_name, _ = self.api_manager.make_request(
                                prompt=prompt,
                                intelligence_level=intelligence_level,
                                max_tokens=max_tokens,
                                temperature=temperature
                            )
                        else:
                            # If out of retries, log the failure and use default fallback values.
                            print(f"Perception response validation failed after {max_retries} attempts: {last_error}")
                            analysis_type = "immediate_reaction"
                            impact_score = 1
                            reasoning = "Response parsing failed, using defaults"
                except Exception as e:
                    # Handle unexpected exceptions during parsing.
                    last_error = f"Parsing failed: {e}"
                    if attempt < max_retries - 1:
                        # If retries remain, log the error and try again.
                        print(f"Perception parsing failed (attempt {attempt + 1}/{max_retries}): {e}")
                    else:
                        # If out of retries, log the failure and use default fallback values.
                        print(f"Perception parsing failed after {max_retries} attempts: {e}")
                        analysis_type = "immediate_reaction"
                        impact_score = 1
                        reasoning = "Parsing failed, using defaults"
                        break
            # Apply mood influence to impact score if available
            if hasattr(self, 'agent') and hasattr(self.agent, 'get_mood_influenced_impact'):
                original_impact = impact_score
                impact_score = self.agent.get_mood_influenced_impact(impact_score)
                if original_impact != impact_score:
                    print(f"  Mood influence: Impact adjusted from {original_impact} to {impact_score}")
            
            # determine if memory retrieval is needed
            # we retrieve the memories if the impact score is high enough
            # so that the agent can understand how they reacted to this kind of situation in the past 
            memory_retrieved = False
            memory_content = None

            # check if this is something that we care about
            if impact_score >= self.MEMORY_RETRIEVAL_THRESHOLD:

                # attempt to retrieve memory for similar situations
                memory_content = self.retrieve_memory(event, agent_state, history)
                memory_retrieved = True
            
            return {
                'perception': reasoning,
                'impact_score': impact_score,
                'should_analyze': analysis_type == 'historical_context',
                'analysis_type': analysis_type,
                'memory_retrieved': memory_retrieved,
                'memory_content': memory_content
            }
            
        except Exception as e:
            # fallback response
            return {
                'perception': f"Error analyzing event: {e}",
                'impact_score': 1,
                'should_analyze': False,
                'analysis_type': 'immediate_reaction',
                'memory_retrieved': False,
                'memory_content': None
            }
    
    def _parse_perception_response(self, response: str) -> Dict[str, Any]:
        """
        Parse and validate the LLM perception response.
        
        Args:
            response: LLM response string
            
        Returns:
            Dict with 'is_valid' boolean, parsed values, and 'errors' list
        """
        errors = []
        required_fields = ['ANALYSIS_TYPE', 'IMPACT_SCORE', 'REASONING']
        
        # Check if response is empty or None
        if not response or not response.strip():
            errors.append("Response is empty or None")
            return {'is_valid': False, 'errors': errors}
        
        # Split into lines and check each required field
        lines = [line.strip() for line in response.strip().split('\n') if line.strip()]
        
        # Initialize parsed values
        parsed_values = {
            'analysis_type': 'immediate_reaction',
            'impact_score': 1,
            'reasoning': ''
        }
        
        for field in required_fields:
            field_found = False
            
            for line in lines:
                if line.startswith(f'{field}:'):
                    field_found = True
                    try:
                        # Extract value after colon
                        value_str = line.split(':', 1)[1].strip()
                        if not value_str:
                            errors.append(f"{field} has empty value")
                            continue
                        
                        # Parse based on field type
                        if field == 'ANALYSIS_TYPE':
                            if value_str.lower() in ['historical_context', 'immediate_reaction']:
                                parsed_values['analysis_type'] = value_str.lower()
                            else:
                                errors.append(f"{field} value '{value_str}' is not valid (expected 'historical_context' or 'immediate_reaction')")
                        
                        elif field == 'IMPACT_SCORE':
                            try:
                                impact = int(value_str)
                                if 1 <= impact <= 10:
                                    parsed_values['impact_score'] = impact
                                else:
                                    errors.append(f"{field} value {impact} is outside valid range [1, 10]")
                            except ValueError:
                                errors.append(f"{field} value '{value_str}' is not a valid integer")
                        
                        elif field == 'REASONING':
                            parsed_values['reasoning'] = value_str
                        
                    except Exception as e:
                        errors.append(f"Error parsing {field}: {e}")
                    break
            
            if not field_found:
                errors.append(f"Missing required field: {field}")
        
        # Check if we have any errors
        is_valid = len(errors) == 0
        
        return {
            'is_valid': is_valid,
            'errors': errors,
            **parsed_values
        }
    
    def retrieve_memory(self, event: 'Event', agent_state: Dict[str, Any], history: List[str] = None) -> Optional[str]:
        """
        Retrieve relevant memories for similar situations when impact score meets retrieval threshold.
        
        Args:
            event: Event to find similar memories for
            agent_state: Current state of the agent
            history: List of previous events/actions in chronological order
            
        Returns:
            Relevant memory content if found, None otherwise
        """
        try:
            
            # check if the agent has a memory manager
            if not hasattr(self, 'agent') or not hasattr(self.agent, 'memory_manager'):
                return None
            
            # Get similar memories for context
            # Build a first-person search query using event content and current state
            try:
                agent_name = self.agent.get_name() if hasattr(self.agent, 'get_name') else 'I'
            except Exception:
                agent_name = 'I'
            context_bits = []
            try:
                if hasattr(self.agent, 'intent_manager') and self.agent.intent_manager:
                    top_values = sorted(((v.name, v.weight) for v in self.agent.intent_manager.values.values()), key=lambda x: -x[1])[:5]
                    context_bits.append('values: ' + ", ".join(f"{n}={w:.2f}" for n,w in top_values))
            except Exception:
                pass
            query = f"I experienced this: {event.content}. {', '.join(context_bits)}"

            similar_memories = self.agent.memory_manager.search_memories(query, k=self.MEMORY_SIMILARITY_SEARCH_K)
            
            if similar_memories:
                return similar_memories
            else:
                return None
                
        except Exception as e:
            # If memory retrieval fails, return None (agent will proceed without memory context)
            return None
    
    def create_memory(self, 
                     event: 'Event', 
                     agent_state: Dict[str, Any], 
                     history: List[str] = None,
                     impact_score: int = 1,
                     intelligence_level: int = None,
                     max_tokens: int = None,
                     temperature: float = None
                   ) -> str:
        """
        Create a long-form memory summary of an event.
        
        Args:
            event: Event to create memory for
            agent_state: Current state of the agent
            history: List of previous events/actions in chronological order
            impact_score: Impact score of the event (1-10)
            intelligence_level: Intelligence level for LLM analysis (defaults to env setting)
            max_tokens: Maximum tokens for the response (defaults to env setting)
            temperature: Temperature for response generation (defaults to env setting)
            
        Returns:
            Memory content wrapped in <story></story> tags, or empty string if below threshold
        """
        # Use environment defaults if not specified
        if intelligence_level is None:
            intelligence_level = self.MEMORY_CREATION_INTELLIGENCE_LEVEL
        if max_tokens is None:
            max_tokens = self.MEMORY_CREATION_MAX_TOKENS
        if temperature is None:
            temperature = self.MEMORY_CREATION_TEMPERATURE
        
        # Check if impact score meets the memory creation threshold
        if impact_score < self.MEMORY_CREATION_THRESHOLD:
            return ""  # Return empty string for events below threshold
        
        if history is None:
            history = []
        
        # Format the history for the prompt
        history_text = ""
        if history:
            history_limit = int(os.getenv('MEMORY_CREATION_HISTORY_LIMIT', '10'))
            history_text = "\n".join([f"- {event}" for event in history[-history_limit:]])  # Last N events
        
        # Format agent state
        agent_state_text = "\n".join([f"- {key}: {value}" for key, value in agent_state.items()])
        
        # Construct the memory creation prompt
        prompt = f"""You are an intelligent agent creating a personal memory of an important event. Write this memory as if you are personally experiencing and reflecting on what happened.

EVENT TO REMEMBER:
Type: {event.event_type}
Content: {event.content}
Source: {event.source or 'Unknown'}
Impact Score: {impact_score}/10

YOUR CURRENT STATE:
{agent_state_text}

RECENT HISTORY:
{history_text if history_text else "No recent events"}

MEMORY CREATION TASK:
Create a long-form, narrative memory of this event. Write it as a personal story that includes:
1. The context and circumstances - what was happening around me
2. My personal connection to what happened - why this matters to me
3. How it affected me emotionally and practically - what I felt and how it changed my situation
4. What I learned or how it changed me - insights gained or personal growth
5. How it fits into my broader life story - connections to my past experiences and future plans

Write this as a cohesive narrative in first person, using "I", "me", "my" throughout. Make it deeply personal and reflective, as if you're writing in a personal journal about a meaningful experience.

Do NOT wrap your response in any tags - just write the narrative directly."""
        
        try:
            # Check if we should use testing mode
            if TESTING_AVAILABLE and should_mock_llm():
                # Use mock LLM client for testing
                mock_client = get_mock_llm_client()
                if mock_client:
                    # Create mock event for testing
                    from Setup.testing_config import MockEvent
                    mock_event = MockEvent(
                        event_id=getattr(event, 'event_id', 1),
                        event_type=event.event_type,
                        content=event.content,
                        timestamp=getattr(event, 'timestamp', time.time())
                    )
                    
                    # Get agent context for personalization
                    agent_context = ""
                    if hasattr(self, 'agent') and hasattr(self.agent, 'get_name'):
                        agent_context = f"{self.agent.get_name()}, age {getattr(self.agent, 'age', 'unknown')}"
                    
                    # Get mock memory response
                    mock_memory = mock_client.create_memory(mock_event, {'impact_score': impact_score}, agent_context)
                    
                    # Clean the response and remove any story tags
                    clean_response = mock_memory.strip()
                    clean_response = re.sub(r'<story>|</story>', '', clean_response)
                    return clean_response
                else:
                    # Fallback to real API if mock client not available
                    response, _, model_name, _ = self.api_manager.make_request(
                        prompt=prompt,
                        intelligence_level=intelligence_level,
                        max_tokens=max_tokens,
                        temperature=temperature
                    )
                    
                    # Clean the response and remove any story tags
                    clean_response = response.strip()
                    clean_response = re.sub(r'<story>|</story>', '', clean_response)
                    
                    # Additional cleaning: remove any other common unwanted tags or formatting
                    clean_response = re.sub(r'<[^>]*>', '', clean_response)  # Remove any remaining HTML-like tags
                    clean_response = re.sub(r'```.*?```', '', clean_response, flags=re.DOTALL)  # Remove code blocks
                    clean_response = re.sub(r'^["\']|["\']$', '', clean_response)  # Remove leading/trailing quotes
                    
                    # Validate response quality
                    if len(clean_response.strip()) < 10:
                        clean_response = f"Basic memory of {event.event_type} event: {event.content}"
                    
                    return clean_response
            else:
                # Use real LLM API
                response, _, model_name, _ = self.api_manager.make_request(
                    prompt=prompt,
                    intelligence_level=intelligence_level,
                    max_tokens=max_tokens,
                    temperature=temperature
                )
                
                # Clean the response and remove any story tags
                clean_response = response.strip()
                # Remove any existing story tags if they somehow got added
                clean_response = re.sub(r'<story>|</story>', '', clean_response)
                
                # Additional cleaning: remove any other common unwanted tags or formatting
                clean_response = re.sub(r'<[^>]*>', '', clean_response)  # Remove any remaining HTML-like tags
                clean_response = re.sub(r'```.*?```', '', clean_response, flags=re.DOTALL)  # Remove code blocks
                clean_response = re.sub(r'^["\']|["\']$', '', clean_response)  # Remove leading/trailing quotes
                
                # Validate response quality
                if len(clean_response.strip()) < 10:
                    clean_response = f"Basic memory of {event.event_type} event: {event.content}"
                
                return clean_response
            
        except Exception as e:
            # Fallback memory
            return f"Error creating memory: {e}. Basic memory of event: {event.content}"
    
    def test_connection(self, intelligence_level: int = None) -> bool:
        """
        Test the API connection.
        
        Args:
            intelligence_level (int): Intelligence level to test with (defaults to env setting)
            
        Returns:
            bool: True if connection successful
        """
        if intelligence_level is None:
            intelligence_level = self.TEST_CONNECTION_INTELLIGENCE_LEVEL
        return self.api_manager.test_connection(intelligence_level) 