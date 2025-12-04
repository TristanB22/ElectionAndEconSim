#!/usr/bin/env python3
"""
God-Given Questions Module

Asks agents questions at the end of simulations and logs responses to the database.
"""

import os
import re
import time
from typing import Dict, Any, Optional, Tuple, List
from datetime import datetime
from Utils.api_manager import APIManager
from concurrent.futures import ThreadPoolExecutor, as_completed
from concurrent.futures import ProcessPoolExecutor

# Try to import tqdm, but don't fail if it's not available
try:
    from tqdm.auto import tqdm
    TQDM_AVAILABLE = True
except ImportError:
    TQDM_AVAILABLE = False


def _ask_worker(agent_id: str,
                question: str,
                agent_context: str,
                use_smart_model: bool,
                max_retries: int = 3) -> Tuple[str, str, str, str]:
    """Multiprocessing-safe worker to ask a single question with retry logic.

    Args:
        agent_id: Agent ID
        question: Question text
        agent_context: Pre-built agent context string
        use_smart_model: Whether to use smart model
        max_retries: Maximum number of retry attempts (default 3)

    Returns: (agent_id, question, answer, reasoning)
    """
    # Local imports in child process
    import os
    from Utils.api_manager import APIManager

    api_key = os.getenv('OPENROUTER_KEY')
    api_manager = APIManager(api_key) if api_key else None
    if not api_manager:
        return agent_id, question, "", "API manager not configured"

    # Build prompt
    prompt = (
        "You are answering a question as if you were the following person. "
        "Use their background, values, and circumstances to inform your answer.\n\n"
        f"{agent_context}\n\n"
        "Now, answer this question as this person would:\n\n"
        f"{question}\n\n"
        "Respond with just your final answer in the exact format requested by the question."
    )

    intelligence_level = 3 if use_smart_model else 1
    
    # Retry logic: attempt up to max_retries times
    last_error = None
    for attempt in range(max_retries):
        try:
            response, reasoning, model_name, metadata = api_manager.make_request(
                prompt=prompt,
                intelligence_level=intelligence_level,
                max_tokens=1000,
                temperature=0.7
            )
            
            if response and response.strip():
                answer = response.strip()
                return agent_id, question, answer, reasoning
            else:
                last_error = "Empty response from LLM"
                if attempt < max_retries - 1:
                    # Brief delay before retry (exponential backoff)
                    import time
                    time.sleep(0.5 * (attempt + 1))
        except Exception as e:
            last_error = str(e)
            if attempt < max_retries - 1:
                # Brief delay before retry (exponential backoff)
                import time
                time.sleep(0.5 * (attempt + 1))
    
    # All retries failed
    return agent_id, question, "", f"Failed after {max_retries} attempts: {last_error}"


class GodGivenQuestioner:
    """Asks agents questions using their full context and logs responses."""
    
    def __init__(self, simulation_id: str, api_key: Optional[str] = None):
        """
        Initialize the questioner.
        
        Args:
            simulation_id: The simulation ID for logging responses
            api_key: Optional API key (will use OPENROUTER_KEY env var if not provided)
        """
        self.simulation_id = simulation_id
        
        # Load API key from environment if not provided
        if api_key is None:
            api_key = os.getenv('OPENROUTER_KEY')
        
        self.api_manager = APIManager(api_key) if api_key else None
    
    def _bulk_check_existing_questions(
        self,
        agent_ids: List[str],
        questions: List[str],
        simulation_timestamp: Optional[datetime] = None
    ) -> set:
        """
        Bulk check which (agent_id, question) combinations already exist in the database.
        
        Args:
            agent_ids: List of agent IDs to check
            questions: List of question texts to check
            simulation_timestamp: Optional timestamp filter (if None, checks all timestamps)
            
        Returns:
            Set of tuples (agent_id, question_text) that already exist
        """
        if not agent_ids or not questions:
            return set()
        
        try:
            from Database.database_manager import execute_query
            
            # Build query with IN clauses for agent_ids and questions
            # Process in chunks to avoid SQL parameter limits
            existing_pairs: set = set()
            chunk_size = 500  # Safe chunk size for SQL IN clauses
            
            # Normalize questions for comparison (strip whitespace)
            normalized_questions = [q.strip() for q in questions]
            
            for i in range(0, len(agent_ids), chunk_size):
                agent_chunk = agent_ids[i:i + chunk_size]
                agent_placeholders = ",".join(["%s"] * len(agent_chunk))
                
                for j in range(0, len(normalized_questions), chunk_size):
                    question_chunk = normalized_questions[j:j + chunk_size]
                    question_placeholders = ",".join(["%s"] * len(question_chunk))
                    
                    query = f"""
                        SELECT DISTINCT agent_id, question_text
                        FROM god_given_to_agent_questions
                        WHERE agent_id IN ({agent_placeholders})
                        AND question_text IN ({question_placeholders})
                    """
                    
                    params: List[Any] = list(agent_chunk) + list(question_chunk)
                    
                    if simulation_timestamp:
                        pass
                    
                    result = execute_query(query, tuple(params), database='world_sim_simulations', fetch=True)
                    
                    if result.success and result.data:
                        for row in result.data:
                            agent_id = str(row.get('agent_id', ''))
                            question_text = str(row.get('question_text', '')).strip()
                            existing_pairs.add((agent_id, question_text))
            
            return existing_pairs
            
        except Exception as e:
            print(f"Warning: Could not check existing questions: {e}")
            # If check fails, return empty set (will ask all questions)
            return set()
    
    def _build_agent_context(self, agent) -> str:
        """
        Build comprehensive context string for the agent including:
        - Personal summary (LLM-generated if available)
        - Balance sheet
        - Any other relevant agent state
        
        Args:
            agent: The agent object
            
        Returns:
            Comprehensive context string
        """
        context_parts = []
        
        # Add LLM personal summary if available
        if hasattr(agent, 'llm_summary') and agent.llm_summary:
            context_parts.append("PERSONAL SUMMARY:")
            context_parts.append(agent.llm_summary)
            context_parts.append("")
        elif hasattr(agent, 'get_broad_summary'):
            context_parts.append("PERSONAL SUMMARY:")
            context_parts.append(agent.get_broad_summary())
            context_parts.append("")
        
        # Add balance sheet if available
        # First check if agent has balance_sheet attribute, otherwise fetch from DB
        balance_sheet_data = None
        
        if hasattr(agent, 'balance_sheet') and agent.balance_sheet:
            balance_sheet_data = agent.balance_sheet
        elif hasattr(agent, 'simulation_id') and agent.simulation_id and hasattr(agent, 'agent_id'):
            # Try to fetch balance sheet from database
            try:
                from Database.managers import get_simulations_manager
                from Database.managers import get_agents_manager
                sim_mgr = get_simulations_manager()
                agents_mgr = get_agents_manager()
                
                # Get household ID for this agent
                household_id = agents_mgr.get_agent_household_id(str(agent.agent_id))
                if household_id:
                    balance_sheet_data = sim_mgr.get_household_balance_sheet(agent.simulation_id, household_id)
            except Exception as e:
                # If fetch fails, continue without balance sheet
                pass
        
        if balance_sheet_data:
            try:
                context_parts.append("FINANCIAL SITUATION:")
                
                # Handle both dict-style and object-style balance sheets
                if isinstance(balance_sheet_data, dict):
                    # Database dict format
                    if 'assetsTotal' in balance_sheet_data:
                        context_parts.append(f"Total Assets: ${balance_sheet_data['assetsTotal']:,.2f}")
                    if 'liabilitiesTotal' in balance_sheet_data:
                        context_parts.append(f"Total Liabilities: ${balance_sheet_data['liabilitiesTotal']:,.2f}")
                    if 'netWorth' in balance_sheet_data:
                        context_parts.append(f"Net Worth: ${balance_sheet_data['netWorth']:,.2f}")
                    if 'liquidSavings' in balance_sheet_data:
                        context_parts.append(f"Liquid Savings: ${balance_sheet_data['liquidSavings']:,.2f}")
                    if 'primaryHomeValue' in balance_sheet_data:
                        context_parts.append(f"Home Value: ${balance_sheet_data['primaryHomeValue']:,.2f}")
                    if 'mortgageBalance' in balance_sheet_data:
                        context_parts.append(f"Mortgage Balance: ${balance_sheet_data['mortgageBalance']:,.2f}")
                else:
                    # Object-style balance sheet
                    if hasattr(balance_sheet_data, 'total_assets'):
                        context_parts.append(f"Total Assets: ${balance_sheet_data.total_assets:,.2f}")
                    if hasattr(balance_sheet_data, 'total_liabilities'):
                        context_parts.append(f"Total Liabilities: ${balance_sheet_data.total_liabilities:,.2f}")
                    if hasattr(balance_sheet_data, 'net_worth'):
                        context_parts.append(f"Net Worth: ${balance_sheet_data.net_worth:,.2f}")
                    if hasattr(balance_sheet_data, 'liquid_assets'):
                        context_parts.append(f"Liquid Assets: ${balance_sheet_data.liquid_assets:,.2f}")
                
                context_parts.append("")
            except Exception:
                pass
        
        # Add location if available
        if hasattr(agent, 'l2_data') and agent.l2_data:
            try:
                if hasattr(agent.l2_data, 'residence') and agent.l2_data.residence:
                    if hasattr(agent.l2_data.residence, 'city'):
                        city = agent.l2_data.residence.city
                        state = getattr(agent.l2_data.residence, 'state', 'ME')
                        context_parts.append(f"Location: {city}, {state}")
                        context_parts.append("")
            except Exception:
                pass
        
        return "\n".join(context_parts)
    
    def ask_question(
        self, 
        agent, 
        question: str, 
        simulation_timestamp: Optional[datetime] = None
    ) -> Tuple[str, str]:
        """
        Ask an agent a question and get their answer with reasoning.
        
        Args:
            agent: The agent to ask
            question: The question text
            simulation_timestamp: Optional timestamp (defaults to now)
            
        Returns:
            Tuple of (answer, reasoning)
        """
        if not self.api_manager:
            return "API not available", "No API manager configured"
        
        if simulation_timestamp is None:
            simulation_timestamp = datetime.now()
        
        # Build agent context
        agent_context = self._build_agent_context(agent)
        
        # Build the prompt
        prompt = f"""You are answering a question as if you were the following person. Use their background, values, and circumstances to inform your answer.

{agent_context}

Now, answer this question as this person would:

{question}

Respond with just your final answer in the exact format requested by the question."""
        
        try:
            # Use intelligence level 1 (OPEN_ROUTER_STUPID_MODEL) unless smart model is enabled
            # intelligence_level=1 maps to OPEN_ROUTER_STUPID_MODEL (cheap, fast)
            # intelligence_level=3 maps to OPEN_ROUTER_REASONING_MODEL (expensive, smart)
            use_smart_model = os.getenv('GOD_QUESTIONS_USE_SMART_MODEL', '0').lower() in ('1', 'true', 'yes')
            intelligence_level = 3 if use_smart_model else 1
            
            # Call LLM using make_request which returns (response, reasoning, model_name, metadata)
            response, reasoning, model_name, metadata = self.api_manager.make_request(
                prompt=prompt,
                intelligence_level=intelligence_level,
                max_tokens=1000,
                temperature=0.7
            )
            
            if not response:
                return "Error: No response from LLM", reasoning or "LLM returned empty response"
            
            # The response is the answer, reasoning comes from the API directly
            answer = response.strip()
            
            return answer, reasoning
            
        except Exception as e:
            return f"Error: {str(e)}", f"Exception during LLM call: {str(e)}"
    
    def ask_and_log_question(
        self,
        agent,
        question: str,
        simulation_timestamp: Optional[datetime] = None
    ) -> bool:
        """
        Ask a question, get the answer, and log it to the database.
        
        Args:
            agent: The agent to ask
            question: The question text
            simulation_timestamp: Optional timestamp (defaults to now)
            
        Returns:
            True if successful, False otherwise
        """
        if simulation_timestamp is None:
            simulation_timestamp = datetime.now()
        
        # Get the answer
        answer, reasoning = self.ask_question(agent, question, simulation_timestamp)
        
        # Log to database
        try:
            from Database.database_manager import execute_query
            
            query = """
                INSERT INTO god_given_to_agent_questions 
                (simulation_id, simulation_timestamp, agent_id, question_text, reasoning_text, answer_text)
                VALUES (%s, %s, %s, %s, %s, %s)
            """
            
            params = (
                self.simulation_id,
                simulation_timestamp,
                str(agent.agent_id),
                question,
                reasoning,
                answer
            )
            
            result = execute_query(query, params, database='world_sim_simulations', fetch=False)
            
            if not result.success:
                print(f"Failed to log question response for agent {agent.agent_id}: {result.error}")
                return False
            
            return True
            
        except Exception as e:
            print(f"Error logging question response for agent {agent.agent_id}: {e}")
            return False
    
    def ask_multiple_questions(
        self,
        agents: List[Any],
        questions: List[str],
        simulation_timestamp: Optional[datetime] = None,
        agent_ids_filter: Optional[List[str]] = None,
        skip_existing: bool = False,
    ) -> None:
        """
        Ask multiple questions to multiple agents and log all responses.

        Uses multiprocessing if GOD_QUESTIONS_USE_MULTIPROCESSING is enabled, otherwise threads.
        Limits concurrency with GOD_QUESTIONS_MAX_WORKERS (default 3).
        
        Args:
            agents: List of agent objects
            questions: List of question strings
            simulation_timestamp: Optional timestamp (defaults to now)
            agent_ids_filter: Optional list of agent IDs to include; if None, ask all provided agents
            skip_existing: If True, skip questions that have already been asked to agents (checks database)
        """
        if simulation_timestamp is None:
            simulation_timestamp = datetime.now()

        # Filter agents if a subset is requested
        if agent_ids_filter:
            agent_id_set = set(str(aid) for aid in agent_ids_filter)
            agents = [a for a in agents if str(a.agent_id) in agent_id_set]

        if not agents:
            print("No agents to ask questions to.")
            return

        verbosity = int(os.getenv('VERBOSITY', os.getenv('VERBOSITY_LEVEL', '1')))
        
        # BULK PRE-LOAD balance sheets and household IDs to avoid per-agent DB queries
        # Critical for performance with many agents
        t0 = time.perf_counter() if verbosity >= 2 else None
        balance_sheets_cache: Dict[str, Any] = {}
        household_ids_cache: Dict[str, str] = {}
        
        # Check which agents need balance sheets fetched
        agent_ids_needing_balance_sheets = [
            str(a.agent_id) for a in agents
            if not (hasattr(a, 'balance_sheet') and a.balance_sheet)
        ]
        
        if agent_ids_needing_balance_sheets:
            try:
                from Database.managers import get_simulations_manager, get_agents_manager
                sim_mgr = get_simulations_manager()
                agents_mgr = get_agents_manager()
                
                # Bulk fetch household IDs for all agents using a single query
                if verbosity >= 3:
                    print(f"[god_questions] Bulk fetching household IDs for {len(agent_ids_needing_balance_sheets)} agents...")
                
                # Use a single SQL query to fetch household IDs from l2_other_part_1
                try:
                    from Database.database_manager import execute_query
                    chunk_size = 1000
                    for i in range(0, len(agent_ids_needing_balance_sheets), chunk_size):
                        chunk = agent_ids_needing_balance_sheets[i:i + chunk_size]
                        placeholders = ",".join(["%s"] * len(chunk))
                        query = f"""
                            SELECT LALVOTERID, 
                                   COALESCE(Residence_Families_FamilyID, Mailing_Families_FamilyID, CONCAT('SYNTH_', LALVOTERID)) as household_id
                            FROM l2_other_part_1
                            WHERE LALVOTERID IN ({placeholders})
                        """
                        result = execute_query(query, tuple(chunk), database='world_sim_agents', fetch=True)
                        if result.success and result.data:
                            for row in result.data:
                                agent_id = str(row.get('LALVOTERID', ''))
                                household_id = str(row.get('household_id', ''))
                                if household_id:
                                    household_ids_cache[agent_id] = household_id
                        
                        # For agents not found in l2_other_part_1, use synthetic ID
                        for agent_id in chunk:
                            if agent_id not in household_ids_cache:
                                household_ids_cache[agent_id] = f"SYNTH_{agent_id}"
                except Exception as e:
                    if verbosity >= 2:
                        print(f"Warning: Bulk household ID fetch failed, falling back to individual calls: {e}")
                    # Fallback to individual calls (slower but works)
                    for agent_id in agent_ids_needing_balance_sheets:
                        household_id = agents_mgr.get_agent_household_id(agent_id)
                        if household_id:
                            household_ids_cache[agent_id] = household_id
                
                # Group by household ID to reduce balance sheet fetches
                household_to_agents: Dict[str, List[str]] = {}
                for agent_id, household_id in household_ids_cache.items():
                    if household_id not in household_to_agents:
                        household_to_agents[household_id] = []
                    household_to_agents[household_id].append(agent_id)
                
                # Fetch balance sheets once per unique household
                unique_households = list(household_to_agents.keys())
                if verbosity >= 3:
                    print(f"[god_questions] Fetching balance sheets for {len(unique_households)} unique households...")
                
                for household_id in unique_households:
                    balance_sheet = sim_mgr.get_household_balance_sheet(self.simulation_id, household_id)
                    if balance_sheet:
                        # Share balance sheet across all agents in this household
                        for agent_id in household_to_agents[household_id]:
                            balance_sheets_cache[agent_id] = balance_sheet
                
                if verbosity >= 2:
                    elapsed = time.perf_counter() - t0 if t0 else 0
                    print(f"[god_questions] Pre-loaded {len(balance_sheets_cache)} balance sheets in {elapsed:.2f}s")
            except Exception as e:
                if verbosity >= 1:
                    print(f"Warning: Could not bulk-load balance sheets: {e}")
                # Continue without balance sheets - agents will still have summaries

        # Build contexts once in parent to avoid heavy work in child processes
        # Now using pre-loaded balance sheets cache
        t0 = time.perf_counter() if verbosity >= 2 else None
        contexts: Dict[str, str] = {}
        for agent in agents:
            agent_id_str = str(agent.agent_id)
            # Use cached balance sheet if available
            if agent_id_str in balance_sheets_cache:
                # Temporarily set balance_sheet on agent for _build_agent_context to use
                agent.balance_sheet = balance_sheets_cache[agent_id_str]
            
            context = self._build_agent_context(agent)
            if not context or not context.strip():
                raise ValueError(f"Failed to build context for agent {agent.agent_id}: No personal summary or context available")
            contexts[agent_id_str] = context
            
            # Clean up temporary balance_sheet if we added it
            if agent_id_str in balance_sheets_cache and not hasattr(agent, 'balance_sheet'):
                # Only remove if we added it (check if it was originally None)
                pass  # Leave it - might be useful later
        
        if verbosity >= 2:
            elapsed = time.perf_counter() - t0 if t0 else 0
            print(f"[god_questions] Built contexts for {len(agents)} agents in {elapsed:.2f}s")

        use_mp = os.getenv('GOD_QUESTIONS_USE_MULTIPROCESSING', '1').lower() in ('1','true','yes')
        try:
            max_workers = int(os.getenv('GOD_QUESTIONS_MAX_WORKERS', '3'))
        except Exception:
            max_workers = 3
        max_workers = max(1, max_workers)
        use_smart_model = os.getenv('GOD_QUESTIONS_USE_SMART_MODEL', '0').lower() in ('1','true','yes')

        # Schedule tasks per (agent, question)
        tasks = []
        for agent in agents:
            agent_id = str(agent.agent_id)
            for q in questions:
                tasks.append((agent_id, q, contexts.get(agent_id, "")))

        verbosity = int(os.getenv('VERBOSITY', os.getenv('VERBOSITY_LEVEL', '1')))
        
        # If skip_existing is enabled, bulk check and filter out existing questions
        if skip_existing:
            agent_ids_list = [str(a.agent_id) for a in agents]
            existing_pairs = self._bulk_check_existing_questions(agent_ids_list, questions, simulation_timestamp)
            
            original_count = len(tasks)
            # Filter tasks: keep only those NOT in existing_pairs
            tasks = [
                (agent_id, q, ctx)
                for agent_id, q, ctx in tasks
                if (agent_id, q.strip()) not in existing_pairs
            ]
            
            skipped_count = original_count - len(tasks)
            if skipped_count > 0:
                print(f"⏭ Skipped {skipped_count} question(s) that were already asked (found in database)")
            if verbosity >= 2:
                print(f"  Original tasks: {original_count}, After filtering: {len(tasks)}")
        
        if not tasks:
            print("All questions have already been asked. Nothing to do.")
            return
        
        print(f"Dispatching {len(tasks)} question tasks to {len(agents)} agents (workers={max_workers}, mp={use_mp})")

        # Batch sizes
        ASK_BATCH_SIZE = 500
        INSERT_BATCH_SIZE = 500

        # Aggregates
        total_successful = 0
        total_failed = 0
        total_inserted = 0
        failed_results: List[Tuple[str, str]] = []  # (agent_id, error_message)
        
        # Start timing
        start_time = time.perf_counter()

        # Set up progress bar (always show, regardless of verbosity)
        if TQDM_AVAILABLE:
            pbar = tqdm(total=len(tasks), desc="Asking questions", unit="question")
        else:
            pbar = None

        # Process tasks in batches of ASK_BATCH_SIZE
        for i in range(0, len(tasks), ASK_BATCH_SIZE):
            batch_tasks = tasks[i:i + ASK_BATCH_SIZE]
            batch_results: List[Tuple[str, str, str, str]] = []  # (agent_id, question, answer, reasoning)

            if use_mp:
                with ProcessPoolExecutor(max_workers=max_workers) as executor:
                    futures = [
                        executor.submit(
                            _ask_worker,
                            agent_id,
                            q,
                            ctx,
                            use_smart_model,
                            3  # max_retries
                        ) for agent_id, q, ctx in batch_tasks
                    ]
                    for fut in as_completed(futures):
                        agent_id, question, answer, reasoning = fut.result()
                        if answer:
                            batch_results.append((agent_id, question, answer, reasoning))
                        else:
                            failed_results.append((agent_id, reasoning))
                            total_failed += 1
                            if verbosity >= 2:
                                print(f"  ✗ Failed for agent {agent_id}: {reasoning}")
                        if pbar:
                            pbar.update(1)
            else:
                with ThreadPoolExecutor(max_workers=max_workers) as executor:
                    futures = [
                        executor.submit(
                            _ask_worker,
                            agent_id,
                            q,
                            ctx,
                            use_smart_model,
                            3  # max_retries
                        ) for agent_id, q, ctx in batch_tasks
                    ]
                    for fut in as_completed(futures):
                        agent_id, question, answer, reasoning = fut.result()
                        if answer:
                            batch_results.append((agent_id, question, answer, reasoning))
                        else:
                            failed_results.append((agent_id, reasoning))
                            total_failed += 1
                            if verbosity >= 2:
                                print(f"  ✗ Failed for agent {agent_id}: {reasoning}")
                        if pbar:
                            pbar.update(1)

            # Update counters
            total_successful += len(batch_results)

            # Bulk insert this batch's results in INSERT_BATCH_SIZE chunks
            if batch_results:
                try:
                    from Database.database_manager import execute_query
                    total = len(batch_results)
                    for j in range(0, total, INSERT_BATCH_SIZE):
                        insert_batch = batch_results[j:j + INSERT_BATCH_SIZE]
                        values_clause = ",".join(["(%s,%s,%s,%s,%s,%s)"] * len(insert_batch))
                        query = (
                            "INSERT INTO god_given_to_agent_questions "
                            "(simulation_id, simulation_timestamp, agent_id, question_text, reasoning_text, answer_text) "
                            f"VALUES {values_clause}"
                        )
                        params: List[Any] = []
                        for agent_id, question, answer, reasoning in insert_batch:
                            params.extend([
                                self.simulation_id,
                                simulation_timestamp,
                                agent_id,
                                question,
                                reasoning,
                                answer,
                            ])
                        res = execute_query(query, tuple(params), database='world_sim_simulations', fetch=False)
                        if not res.success:
                            print(f"  ✗ Batch insert failed: {res.error}")
                        else:
                            total_inserted += len(insert_batch)
                except Exception as e:
                    print(f"✗ Bulk insert error: {e}")

        if pbar:
            pbar.close()
        
        # Calculate timing and performance stats
        elapsed_time = time.perf_counter() - start_time
        total_questions = len(tasks)
        
        # Report performance statistics at high verbosity
        if verbosity >= 3:
            questions_per_second = (total_successful / elapsed_time) if elapsed_time > 0 else 0
            print(f"\n[Performance Statistics]")
            print(f"  Total questions: {total_questions}")
            print(f"  Successful: {total_successful}")
            print(f"  Failed: {total_failed}")
            print(f"  Time elapsed: {elapsed_time:.2f} seconds")
            print(f"  Questions per second: {questions_per_second:.2f} q/s")
            if total_questions > 0:
                success_rate = (total_successful / total_questions) * 100
                print(f"  Success rate: {success_rate:.1f}%")
        
        # Report summary at all verbosity levels
        if verbosity >= 1:
            print(f"✓ Inserted {total_inserted}/{total_successful} responses in batches of {INSERT_BATCH_SIZE}")
            if total_failed > 0:
                print(f"{total_failed} question(s) failed after retries (see details above)")
            elif total_successful > 0:
                print(f"All {total_successful} question(s) answered successfully")


# Convenience functions for questioning

def ask_scheduled_questions(
    simulation_id: str,
    agents: List[Any],
    questions: List[str],
    simulation_timestamp: Optional[datetime] = None,
    agent_ids: Optional[List[str]] = None,
    skip_existing: bool = False,
) -> None:
    """
    Ask a list of questions to all agents at a scheduled time during simulation.
    
    This can be called at any point during the simulation. The questions will be
    asked immediately and logged with the provided timestamp.
    
    Args:
        simulation_id: The simulation ID
        agents: List of agent objects
        questions: List of question strings
        simulation_timestamp: Timestamp for when questions are being asked (defaults to now)
        agent_ids: Optional list of agent IDs to include; if None, ask all provided agents
        skip_existing: If True, skip questions that have already been asked to agents (checks database)
    """
    questioner = GodGivenQuestioner(simulation_id)
    questioner.ask_multiple_questions(agents, questions, simulation_timestamp, agent_ids_filter=agent_ids, skip_existing=skip_existing)


def ask_end_of_simulation_questions(
    simulation_id: str,
    agents: list,
    questions: list,
    simulation_timestamp: Optional[datetime] = None
) -> None:
    """
    Ask a list of questions to all agents at the end of a simulation.
    
    This is a convenience wrapper around ask_scheduled_questions for backwards compatibility.
    
    Args:
        simulation_id: The simulation ID
        agents: List of agent objects
        questions: List of question strings
        simulation_timestamp: Optional timestamp (defaults to now)
    """
    ask_scheduled_questions(simulation_id, agents, questions, simulation_timestamp)

