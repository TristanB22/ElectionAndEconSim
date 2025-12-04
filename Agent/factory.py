#!/usr/bin/env python3
"""
Unified Agent Factory - Single Entry Point for Agent Creation

Standardized way to create agents in World_Sim. All production code should
use this factory to ensure L2 data is properly loaded.

Usage:
    from Agent.factory import AgentFactory
    
    # From database (production)
    agent = AgentFactory.from_database(l2_voter_id, simulation_id=sim_id)
    
    # From file (testing)
    agent = AgentFactory.from_file(file_path, row_index, simulation_id=sim_id)
    
    # From dict (custom loading)
    agent = AgentFactory.from_dict(l2_data_dict, agent_id, simulation_id=sim_id)
    
    # Batch creation
    agents = AgentFactory.batch_from_database(voter_ids, simulation_id=sim_id)
"""

from typing import Optional, List, Union, Dict, Any
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
try:
    from tqdm import tqdm
    TQDM_AVAILABLE = True
except ImportError:
    TQDM_AVAILABLE = False
import pandas as pd
import logging
import time
import sys
from pathlib import Path

# Ensure project root is at front of sys.path to avoid module resolution issues
_project_root = Path(__file__).resolve().parents[1]
if str(_project_root) in sys.path:
    sys.path.remove(str(_project_root))
sys.path.insert(0, str(_project_root))

# Removed legacy connection_manager dependency; centralized managers are used elsewhere

from Utils.path_manager import initialize_paths
initialize_paths()

from Agent.agent import Agent
from Agent.models import AgentDTO
from Agent.modules.personal_summary import PersonalSummaryGenerator
from Utils.agent_initializer import AgentInitializer
from Utils.l2_data.l2_data_parser import L2DataParser
from Utils.l2_data.l2_data_objects import L2DataRow

logger = logging.getLogger(__name__)


class AgentFactory:
    """
    Centralized factory for creating agents with L2 data.
    
    This factory ensures:
    1. All agents have L2 data from appropriate sources
    2. Consistent validation and error handling
    3. Proper logging for debugging
    4. Single entry point for maintainability
    
    Design Philosophy:
    - Thin wrapper around existing systems (AgentInitializer, L2DataParser)
    - Minimal abstraction layers for performance
    - Backward compatible with existing patterns
    - Easy to test and extend
    """
    
    @staticmethod
    def from_database(l2_voter_id: str, 
                     agent_id: Optional[str] = None,
                     simulation_id: Optional[str] = None) -> 'Agent':
        """
        Create agent from database L2 data.
        
        This is the PRIMARY method for production simulations.
        Uses AgentInitializer to load data from all L2 database tables.
        
        Args:
            l2_voter_id: LALVOTERID to load from database
            agent_id: Optional custom agent ID (defaults to l2_voter_id)
            simulation_id: Optional simulation ID for agent context
            
        Returns:
            Agent instance with complete L2 data
            
        Raises:
            ValueError: If voter ID not found or agent creation fails
            
        Example:
            >>> agent = AgentFactory.from_database("FL000123456", simulation_id="sim_001")
            >>> print(agent.get_name())
        """
        logger.info(f"Creating agent from database for LALVOTERID: {l2_voter_id}...")
        try:
            initializer = AgentInitializer()
            agent = initializer.create_agent_from_l2(
                l2_voter_id, 
                agent_id=agent_id, 
                simulation_id=simulation_id
            )
            if not agent:
                raise ValueError(f"Agent creation failed for LALVOTERID: {l2_voter_id}")
            
            logger.info(f"Successfully created agent {agent.agent_id} from database.")
            return agent
        except Exception as e:
            logger.error(f"Error creating agent from database for {l2_voter_id}: {e}", exc_info=True)
            raise
    
    @staticmethod
    def from_file(file_path: str, 
                  row_index: int,
                  agent_id: Optional[str] = None,
                  simulation_id: Optional[str] = None) -> 'Agent':
        """
        Create agent from a row in a CSV or Excel file.
        
        Useful for testing and offline scenarios.
        
        Args:
            file_path: Path to the data file
            row_index: The integer index of the row to load
            agent_id: Optional custom agent ID (defaults to LALVOTERID from the file)
            simulation_id: Optional simulation ID for agent context
            
        Returns:
            Agent instance with L2 data from the file
        """
        logger.info(f"Creating agent from file: {file_path}, row: {row_index}...")
        try:
            if file_path.endswith('.csv'):
                df = pd.read_csv(file_path, low_memory=False)
            elif file_path.endswith('.xlsx'):
                df = pd.read_excel(file_path)
            else:
                raise ValueError("Unsupported file type, please use .csv or .xlsx")
                
            row_data = df.iloc[row_index].to_dict()
            
            l2_voter_id = row_data.get('LALVOTERID')
            if not l2_voter_id:
                raise ValueError(f"LALVOTERID not found in row {row_index} of {file_path}")

            final_agent_id = agent_id or str(l2_voter_id)

            l2_row_obj = L2DataParser.parse_row(row_data)
            agent = Agent(agent_id=final_agent_id, l2_data=l2_row_obj, simulation_id=simulation_id)
            
            logger.info(f"Successfully created agent {agent.agent_id} from file.")
            return agent
        except Exception as e:
            logger.error(f"Error creating agent from file {file_path} at row {row_index}: {e}", exc_info=True)
            raise

    @staticmethod
    def from_dict(l2_data: Dict[str, Any],
                  agent_id: str,
                  simulation_id: Optional[str] = None) -> 'Agent':
        """
        Create agent from a Python dictionary.
        
        Flexible method for custom data loading or testing.
        
        Args:
            l2_data: Dictionary containing L2 data
            agent_id: The ID for the new agent
            simulation_id: Optional simulation ID for agent context
            
        Returns:
            Agent instance with the provided L2 data
        """
        logger.info(f"Creating agent {agent_id} from dictionary...")
        try:
            # Accept both raw dicts and already-parsed L2DataRow objects
            if isinstance(l2_data, L2DataRow):
                l2_row_obj = l2_data
            else:
                l2_row_obj = L2DataParser.parse_row(l2_data)
            agent = Agent(agent_id=agent_id, l2_data=l2_row_obj, simulation_id=simulation_id)
            logger.info(f"Successfully created agent {agent.agent_id} from dictionary.")
            return agent
        except Exception as e:
            logger.error(f"Error creating agent {agent_id} from dictionary: {e}", exc_info=True)
            raise

    @staticmethod
    def batch_from_database(l2_voter_ids: List[str],
                            simulation_id: Optional[str] = None) -> List['Agent']:
        """
        Create a batch of agents from a list of L2 voter IDs.
        
        Uses bulk L2 data loading for optimal performance (fetches all data in a few queries
        instead of 9 queries per agent).
        
        Args:
            l2_voter_ids: List of LALVOTERIDs
            simulation_id: Optional simulation ID to apply to all agents
            
        Returns:
            List of created Agent instances
        """
        verbosity = int(os.getenv('VERBOSITY_LEVEL', '1'))
        
        if verbosity >= 1:
            logger.info(f"Creating batch of {len(l2_voter_ids)} agents from database...")
        
        agents: List[Agent] = []
        total_start = time.perf_counter()
        
        try:
            # BULK LOAD L2 DATA for all agents at once (massive speedup!)
            t0 = time.perf_counter()
            from Utils.bulk_l2_loader import load_bulk_l2_data
            l2_data_dict = load_bulk_l2_data(l2_voter_ids)
            if verbosity >= 2:
                logger.info(f"Bulk loaded L2 data for {len(l2_data_dict)} agents in {time.perf_counter() - t0:.2f}s")
            
            # Parse L2 data for all agents
            t0 = time.perf_counter()
            parsed_l2_data: Dict[str, Any] = {}
            for voter_id, l2_data in l2_data_dict.items():
                try:
                    parsed_l2_data[voter_id] = L2DataParser.parse_row(l2_data)
                except Exception as e:
                    if verbosity >= 1:
                        logger.warning(f"Failed to parse L2 data for {voter_id}: {e}")
            if verbosity >= 2:
                logger.info(f"Parsed L2 data for {len(parsed_l2_data)} agents in {time.perf_counter() - t0:.2f}s")
            
            # Determine max workers from env/config
            try:
                max_workers = int(os.getenv('AGENT_INIT_MAX_WORKERS', '6'))
            except Exception:
                max_workers = 6
            if max_workers <= 0:
                max_workers = 1
            
            if verbosity >= 1:
                logger.info(f"Using up to {max_workers} parallel workers for agent creation")

            # Create agents with pre-loaded L2 data (now only Agent.__init__ overhead, no DB queries!)
            t0 = time.perf_counter()
            
            def create_agent_with_preloaded_data(voter_id: str) -> Optional[Agent]:
                """Create agent with pre-loaded L2 data."""
                l2_row = parsed_l2_data.get(voter_id)
                if not l2_row:
                    return None
                try:
                    return Agent(agent_id=voter_id, l2_data=l2_row, simulation_id=simulation_id)
                except Exception as e:
                    if verbosity >= 1:
                        logger.error(f"Error creating agent {voter_id}: {e}")
                    return None
            
            # Use ThreadPoolExecutor for parallel agent creation
            futures = {}
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                for voter_id in l2_voter_ids:
                    fut = executor.submit(create_agent_with_preloaded_data, voter_id)
                    futures[fut] = voter_id

                # Collect results
                results_map: Dict[str, Optional[Agent]] = {}
                
                if verbosity == 0 and TQDM_AVAILABLE:
                    futures_iter = tqdm(as_completed(futures), total=len(futures), desc="Creating agents", unit="agent")
                else:
                    futures_iter = as_completed(futures)
                
                for fut in futures_iter:
                    voter_id = futures[fut]
                    try:
                        agent = fut.result()
                        results_map[voter_id] = agent
                    except Exception as e:
                        results_map[voter_id] = None
                        if verbosity >= 1:
                            logger.error(f"Error creating agent for {voter_id}: {e}", exc_info=True)

            # Rebuild list in the same order as input IDs
            for voter_id in l2_voter_ids:
                agent = results_map.get(voter_id)
                if agent:
                    agents.append(agent)
            
            if verbosity >= 2:
                logger.info(f"Created {len(agents)} Agent objects in {time.perf_counter() - t0:.2f}s")

            if verbosity >= 1:
                logger.info(f"Successfully created {len(agents)} agents from batch database operation.")
            if verbosity >= 3:
                logger.info(f"AgentFactory.batch_from_database: total time {time.perf_counter() - total_start:.2f}s for {len(l2_voter_ids)} agents")
            return agents
        except Exception as e:
            logger.error(f"Fatal error during batch agent creation from database: {e}", exc_info=True)
            raise

    @staticmethod
    def batch_dto_from_database(l2_voter_ids: List[str],
                                simulation_id: Optional[str] = None,
                                llm_summaries: Optional[Dict[str, str]] = None) -> List[AgentDTO]:
        """
        Create lightweight AgentDTO objects from database records.

        Args:
            l2_voter_ids: List of LALVOTERIDs to load.
            simulation_id: Simulation context to attach to each DTO.
            llm_summaries: Optional pre-loaded personal summaries keyed by agent_id.

        Returns:
            List[AgentDTO] preserving input order.
        """
        if not l2_voter_ids:
            return []

        verbosity = int(os.getenv('VERBOSITY_LEVEL', '1'))
        if verbosity >= 1:
            logger.info(f"Creating DTO batch of {len(l2_voter_ids)} agents from database...")

        from Utils.bulk_l2_loader import load_bulk_l2_data

        raw_l2_map = load_bulk_l2_data(l2_voter_ids)
        generator = PersonalSummaryGenerator()
        dtos: List[AgentDTO] = []

        for voter_id in l2_voter_ids:
            raw_entry = raw_l2_map.get(voter_id)
            if not raw_entry:
                if verbosity >= 1:
                    logger.warning(f"No L2 data found for {voter_id}; skipping DTO creation")
                continue

            try:
                l2_row = L2DataParser.parse_row(raw_entry)
            except Exception as exc:
                logger.error(f"Failed to parse L2 data for {voter_id}: {exc}", exc_info=True)
                continue

            # Construct a lightweight agent to reuse existing summary helpers
            agent = Agent(agent_id=voter_id, l2_data=l2_row, simulation_id=simulation_id)
            l2_summary = None
            try:
                l2_summary = generator.create_comprehensive_l2_summary(agent)
            except Exception as exc:
                if verbosity >= 1:
                    logger.warning(f"Failed to compute L2 summary for {voter_id}: {exc}")

            dto = AgentDTO(
                agent_id=str(voter_id),
                simulation_id=simulation_id,
                l2_data=raw_entry,
                llm_summary=(llm_summaries or {}).get(str(voter_id)) if llm_summaries else None,
                l2_summary=l2_summary,
            )
            dtos.append(dto)

        return dtos
