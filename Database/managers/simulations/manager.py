#!/usr/bin/env python3
"""
Simulations Database Manager for World_Sim

Manages all simulation-related database operations including:
- Simulation lifecycle (create, update, complete)
- Initialized agents tracking
- Agent location seeding
- Action and transaction logging
- Performance metrics
"""

from __future__ import annotations

import os
import json
import uuid
import logging
import math
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from contextlib import contextmanager
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor

from ..base import BaseDatabaseManager
from Simulation.spatial.knowledge import (
	AgentSpatialProfile,
	POICandidate,
	cluster_agents_dynamic,
	seed_agent_candidates,
	enrich_with_knowledge_strength,
)
from Utils.spatial.knowledge_variation_config import SOCIAL_SPILLOVER_CONFIG
from Utils.spatial import get_density_class

logger = logging.getLogger(__name__)
import time


# -----------------------------------------------------------------------------
# Worker for multiprocessing: generate a personal summary from flat L2 data
# -----------------------------------------------------------------------------
def _generate_personal_summary_worker(aid: str, l2_flat: dict, simulation_id: Optional[str] = None):
    try:
        # Local imports inside process to avoid pickling issues
        from Agent.models import AgentDTO
        from Agent.services.summary_service import generate_personal_summary

        dto = AgentDTO(
            agent_id=str(aid),
            simulation_id=simulation_id,
            l2_data=l2_flat,
        )
        summary, reasoning, metadata = generate_personal_summary(dto)
        return (aid, summary, reasoning, metadata)
    except Exception:
        # Bubble errors to parent process
        raise


@contextmanager
def _get_postgis_connection():
	"""Get PostGIS connection using environment variables."""
	import psycopg2
	conn = psycopg2.connect(
		host=os.getenv('POSTGRES_HOST', 'localhost'),
		port=int(os.getenv('POSTGRES_PORT', '5432')),
		dbname=os.getenv('POSTGRES_DB', 'world_sim_geo'),
		user=os.getenv('POSTGRES_USER', 'postgres'),
		password=os.getenv('POSTGRES_PASSWORD', '')
	)
	try:
		yield conn
	finally:
		conn.close()


def _init_worker_db_env(required_dbs: str) -> None:
	"""Initializer for multiprocessing workers to limit DB connections.

	Sets minimal pool size and restricts which DB pools are created in each worker
	to avoid exhausting MySQL max_connections.
	"""
	import os as _os
	_os.environ['DB_POOL_SIZE'] = '1'
	_os.environ['SKIP_OPTIONAL_DB_POOLS'] = '1'
	_os.environ['DB_REQUIRED_DBS'] = required_dbs


class SimulationsDatabaseManager(BaseDatabaseManager):
	"""
	Specialized manager for simulation data operations.
	
	Handles:
	- Simulation CRUD operations
	- Initialized agents registration
	- Agent starting locations
	- Action and transaction logging
	- Performance metrics and reporting
	"""
	
	_db_name = os.getenv('DB_SIM_NAME', 'world_sim_simulations')
	
	def __init__(self):
		"""Initialize simulations database manager."""
		super().__init__()
		self._agents_db = os.getenv('DB_AGENTS_NAME', 'world_sim_agents')
	
	# -------------------------------------------------------------------------
	# Simulation Lifecycle Management
	# -------------------------------------------------------------------------
	
	def register_simulation(self, started_by: str, description: str,
						sim_start: datetime, tick_granularity: str = "15m",
						config: Optional[Dict[str, Any]] = None,
						agent_ids: Optional[List[str]] = None) -> str:
		"""
		Register a new simulation in the database. If agent_ids are provided,
		they are registered with the simulation and initial locations are seeded automatically.
		
		Args:
			started_by: User/system that started the simulation
			description: Simulation description
			sim_start: Simulation start datetime
			tick_granularity: Time granularity (e.g., "15m", "1h")
			config: Additional configuration dictionary
			agent_ids: Optional list of agent IDs (L2 voter IDs) to include in the simulation.
						If provided, must be non-empty.
			
		Returns:
			Simulation ID (UUID)
		"""
		sim_id = str(uuid.uuid4())
		cfg_json = json.dumps(config or {})
		
		# Validate agent_ids if provided
		if agent_ids is not None:
			if not isinstance(agent_ids, list) or len(agent_ids) == 0:
				raise ValueError("agent_ids must be a non-empty list when provided")
		
		insert_sql = f"""
			INSERT INTO {self._format_table('simulations')} 
			(simulation_id, started_by, description, start_time, status, parameters, results,
			simulation_start_datetime, current_simulation_datetime, simulation_end_datetime, 
			tick_granularity, config_json)
			VALUES (%s, %s, %s, NOW(), 'running', %s, %s, %s, %s, %s, %s, %s)
		"""
		
		params = (
			sim_id, started_by, description,
			json.dumps({}),  # parameters
			json.dumps({}),  # results
			sim_start,
			sim_start,  # current starts at start
			None,  # end_datetime
			tick_granularity,
			cfg_json
		)
		
		result = self.execute_query(insert_sql, params, fetch=False)
		
		if result.success:
			logger.info(f"Registered simulation {sim_id}: {description}")
			# If agent_ids provided, perform fast bulk initialization and seeding
			if agent_ids:
				try:
					self.bulk_initialize_agents(sim_id, agent_ids)
				except Exception as e:
					logger.error(f"Failed to bulk initialize agents for simulation {sim_id}: {e}")
					raise
			return sim_id
		else:
			raise Exception(f"Failed to register simulation: {result.error}")
	
	def complete_simulation(self, simulation_id: str,
						results: Optional[Dict[str, Any]] = None,
						end_dt: Optional[datetime] = None) -> None:
		"""
		Mark simulation as completed and update results.
		
		Args:
			simulation_id: Simulation ID
			results: Results dictionary to store
			end_dt: End datetime (defaults to now)
		"""
		results_json = json.dumps(results or {})
		end_dt_val = end_dt or datetime.now()
		
		update_sql = f"""
			UPDATE {self._format_table('simulations')}
			SET end_time = NOW(), status = 'completed', results = %s,
				simulation_end_datetime = %s, current_simulation_datetime = %s, 
				updated_at = NOW()
			WHERE simulation_id = %s
		"""
		
		result = self.execute_query(
			update_sql, 
			(results_json, end_dt_val, end_dt_val, simulation_id), 
			fetch=False
		)
		
		if result.success:
			logger.info(f"Completed simulation {simulation_id}")
		else:
			logger.error(f"Failed to complete simulation {simulation_id}: {result.error}")
	
	def update_simulation_status(self, simulation_id: str, status: str,
								end_datetime: Optional[datetime] = None) -> bool:
		"""
		Update simulation status.
		
		Args:
			simulation_id: Simulation ID
			status: New status ('running', 'completed', 'failed', 'paused')
			end_datetime: Optional end datetime
			
		Returns:
			True if successful
		"""
		if end_datetime:
			query = f"""
				UPDATE {self._format_table('simulations')}
				SET status = %s, end_time = %s, simulation_end_datetime = %s,
					updated_at = CURRENT_TIMESTAMP
				WHERE simulation_id = %s
			"""
			params = (status, datetime.now(), end_datetime, simulation_id)
		else:
			query = f"""
				UPDATE {self._format_table('simulations')}
				SET status = %s, updated_at = CURRENT_TIMESTAMP
				WHERE simulation_id = %s
			"""
			params = (status, simulation_id)
		
		result = self.execute_query(query, params, fetch=False)
		
		if result.success:
			logger.info(f"Updated simulation {simulation_id} status to {status}")
			return True
		else:
			logger.error(f"Failed to update simulation {simulation_id}: {result.error}")
			return False
	
	def get_simulation(self, simulation_id: str) -> Optional[Dict[str, Any]]:
		"""Get simulation details by ID."""
		query = f"SELECT * FROM {self._format_table('simulations')} WHERE simulation_id = %s"
		result = self.execute_query(query, (simulation_id,), fetch=True)
		
		if result.success and result.data:
			sim_data = result.data[0]
			# Parse JSON fields
			for json_field in ['config_json', 'parameters', 'results']:
				if sim_data.get(json_field):
					try:
						sim_data[json_field] = json.loads(sim_data[json_field])
					except (json.JSONDecodeError, TypeError):
						pass
			return sim_data
		
		return None
	
	def list_simulations(self, limit: int = 100, status: Optional[str] = None) -> List[Dict[str, Any]]:
		"""
		List simulations with optional status filter.
		
		Args:
			limit: Maximum number of simulations to return
			status: Optional status filter
			
		Returns:
			List of simulation dictionaries
		"""
		if status:
			query = f"SELECT * FROM {self._format_table('simulations')} WHERE status = %s ORDER BY start_time DESC LIMIT %s"
			params = (status, limit)
		else:
			query = f"SELECT * FROM {self._format_table('simulations')} ORDER BY start_time DESC LIMIT %s"
			params = (limit,)
		
		result = self.execute_query(query, params, fetch=True)
		
		if result.success:
			simulations = result.data
			# Parse JSON fields
			for sim in simulations:
				for json_field in ['config_json', 'parameters', 'results']:
					if sim.get(json_field):
						try:
							sim[json_field] = json.loads(sim[json_field])
						except (json.JSONDecodeError, TypeError):
							pass
			return simulations
		
		return []

	# -------------------------------------------------------------------------
	# Agent Selection Helpers (migrated from Utils/agent_selection/query_agent_selector.py)
	# -------------------------------------------------------------------------

	def _rows_from_result(self, result: Any) -> List[Dict[str, Any]]:
		"""Normalize QueryResult (or legacy return) to list of dict rows."""
		if hasattr(result, 'success') and hasattr(result, 'data'):
			return result.data if result.success else []
		return result or []

	def execute_agents_sql_rows(self, sql: str, params: tuple = ()) -> List[Dict[str, Any]]:
		"""
		Execute arbitrary SQL against the agents database and return rows.
		This uses the centralized DB manager to target the agents DB directly.
		"""
		from Database.database_manager import execute_query as dm_execute_query
		result = dm_execute_query(sql, params, database=self._agents_db, fetch=True)
		return self._rows_from_result(result)

	def select_voter_ids_raw_sql(self, sql: str, params: tuple = ()) -> List[str]:
		"""
		Execute a custom SQL against the agents database and extract LALVOTERID values.
		The SQL MUST select a column named 'LALVOTERID'.
		"""
		rows = self.execute_agents_sql_rows(sql, params)
		if not rows:
			return []
		if 'LALVOTERID' not in rows[0]:
			raise ValueError("Query result does not include LALVOTERID column")
		return [str(r['LALVOTERID']) for r in rows]
	
	# -------------------------------------------------------------------------
	# Initialized Agents Management
	# -------------------------------------------------------------------------
	
	def register_initialized_agents(self, sim_id: str, agent_ids: List[str]) -> None:
		"""
		Register agents as initialized for a simulation.
		
		Args:
			sim_id: Simulation ID
			agent_ids: List of agent IDs (L2 voter IDs)
		"""
		if not agent_ids:
			return
		
		# Chunked multi-value insert for performance
		values_per_chunk = 1000
		insert_prefix = f"INSERT IGNORE INTO {self._format_table('initialized_agents')} (simulation_id, agent_id) VALUES "
		for i in range(0, len(agent_ids), values_per_chunk):
			chunk = agent_ids[i:i+values_per_chunk]
			placeholders = ",".join(["(%s,%s)"] * len(chunk))
			params: List[Any] = []
			for aid in chunk:
				params.extend([sim_id, aid])
			query = insert_prefix + placeholders
			self.execute_query(query, tuple(params), fetch=False)
		
		logger.info(f"Registered {len(agent_ids)} initialized agents for simulation {sim_id}")

	def upsert_agent_weekly_skeleton(
		self,
		sim_id: str,
		agent_id: str,
		week_start: datetime,
		skeleton: Any,
		provenance: Optional[Any] = None
	) -> bool:
		"""Insert or update an agent's weekly skeleton."""
		week_date = week_start.date() if isinstance(week_start, datetime) else week_start
		skeleton_json = json.dumps(skeleton) if not isinstance(skeleton, str) else skeleton
		prov_json = json.dumps(provenance) if provenance is not None and not isinstance(provenance, str) else provenance
		query = f"""
			INSERT INTO {self._format_table('agent_weekly_skeleton')}
				(simulation_id, agent_id, week_start, skeleton_json, provenance_json)
			VALUES (%s, %s, %s, %s, %s)
			ON DUPLICATE KEY UPDATE
				skeleton_json = VALUES(skeleton_json),
				provenance_json = VALUES(provenance_json),
				updated_at = CURRENT_TIMESTAMP
		"""
		result = self.execute_query(query, (sim_id, agent_id, week_date, skeleton_json, prov_json), fetch=False)
		return bool(result.success)

	def get_agent_weekly_skeleton(self, sim_id: str, agent_id: str, week_start: datetime) -> Optional[Dict[str, Any]]:
		"""Fetch stored weekly skeleton for an agent if available."""
		week_date = week_start.date() if isinstance(week_start, datetime) else week_start
		query = f"""
			SELECT skeleton_json, provenance_json
			FROM {self._format_table('agent_weekly_skeleton')}
			WHERE simulation_id = %s AND agent_id = %s AND week_start = %s
		"""
		result = self.execute_query(query, (sim_id, agent_id, week_date), fetch=True)
		if result.success and result.data:
			row = result.data[0]
			for key in ("skeleton_json", "provenance_json"):
				if row.get(key):
					try:
						row[key] = json.loads(row[key])
					except (json.JSONDecodeError, TypeError):
						pass
			return row
		return None

	def upsert_agent_daily_template(
		self,
		sim_id: str,
		agent_id: str,
		template_date: datetime,
		blocks: Any,
		provenance: Optional[Any] = None
	) -> bool:
		"""Insert or update an agent's daily template."""
		day_date = template_date.date() if isinstance(template_date, datetime) else template_date
		blocks_json = json.dumps(blocks) if not isinstance(blocks, str) else blocks
		prov_json = json.dumps(provenance) if provenance is not None and not isinstance(provenance, str) else provenance
		query = f"""
			INSERT INTO {self._format_table('agent_daily_template')}
				(simulation_id, agent_id, template_date, blocks_json, provenance_json)
			VALUES (%s, %s, %s, %s, %s)
			ON DUPLICATE KEY UPDATE
				blocks_json = VALUES(blocks_json),
				provenance_json = VALUES(provenance_json),
				updated_at = CURRENT_TIMESTAMP
		"""
		result = self.execute_query(query, (sim_id, agent_id, day_date, blocks_json, prov_json), fetch=False)
		return bool(result.success)

	def get_agent_daily_template(self, sim_id: str, agent_id: str, template_date: datetime) -> Optional[Dict[str, Any]]:
		"""Retrieve stored daily template for an agent."""
		day_date = template_date.date() if isinstance(template_date, datetime) else template_date
		query = f"""
			SELECT blocks_json, provenance_json
			FROM {self._format_table('agent_daily_template')}
			WHERE simulation_id = %s AND agent_id = %s AND template_date = %s
		"""
		result = self.execute_query(query, (sim_id, agent_id, day_date), fetch=True)
		if result.success and result.data:
			row = result.data[0]
			for key in ("blocks_json", "provenance_json"):
				if row.get(key):
					try:
						row[key] = json.loads(row[key])
					except (json.JSONDecodeError, TypeError):
						pass
			return row
		return None

	def insert_plan_audit(
		self,
		plan_id: int,
		audit_type: str,
		input_hash: Optional[str],
		model_name: Optional[str],
		issues: Optional[Any],
		edits: Optional[Any]
	) -> bool:
		"""Store an audit record for a generated plan."""
		issues_json = json.dumps(issues) if issues is not None and not isinstance(issues, str) else issues
		edits_json = json.dumps(edits) if edits is not None and not isinstance(edits, str) else edits
		query = f"""
			INSERT INTO {self._format_table('plan_audits')}
				(plan_id, audit_type, input_hash, model_name, issues_json, edits_json)
			VALUES (%s, %s, %s, %s, %s, %s)
		"""
		result = self.execute_query(query, (plan_id, audit_type, input_hash, model_name, issues_json, edits_json), fetch=False)
		return bool(result.success)

	def insert_agent_locations_batch(self, rows: List[Tuple[str, str, float, float, Any]]) -> bool:
		"""Batch insert agent location samples.

		Args:
			rows: List of tuples (simulation_id, agent_id, latitude, longitude, simulation_timestamp)

		Returns:
			True if insert succeeded.
		"""
		if not rows:
			return True
		query = f"""
			INSERT IGNORE INTO {self._format_table('agent_locations')}
				(simulation_id, agent_id, latitude, longitude, simulation_timestamp)
			VALUES (%s, %s, %s, %s, %s)
		"""
		result = self.execute_many(query, rows)
		return bool(result.success)

	def get_poi_coords(self, osm_ids: List[int]) -> Dict[int, Tuple[float, float]]:
		"""Fetch lat/lon for a list of OSM IDs from poi_categories in one query."""
		out: Dict[int, Tuple[float, float]] = {}
		if not osm_ids:
			return out
		# Deduplicate and chunk to avoid very large IN clauses
		unique = list({int(x) for x in osm_ids if x is not None})
		chunk_size = 500
		for i in range(0, len(unique), chunk_size):
			chunk = unique[i:i+chunk_size]
			placeholders = ",".join(["%s"] * len(chunk))
			query = f"""
				SELECT osm_id, lat, lon
				FROM {self._format_table('poi_categories')}
				WHERE osm_id IN ({placeholders})
			"""
			res = self.execute_query(query, tuple(chunk), fetch=True)
			if not res.success or not res.data:
				continue
			for row in res.data:
				try:
					out[int(row["osm_id"])] = (float(row["lat"]), float(row["lon"]))
				except Exception:
					continue
		return out
	
	def seed_agent_start_locations(self, sim_id: str) -> None:
		"""
		Populate starting locations in agent_locations for initialized agents.
		
		Joins initialized_agents with L2 tables to fetch lat/lon, prints how many
		agents are missing coordinates, and inserts rows at simulation_start_datetime
		for those with coordinates.
		
		Args:
			sim_id: Simulation ID
		"""
		# Get simulation start datetime
		start_query = f"SELECT simulation_start_datetime FROM {self._format_table('simulations')} WHERE simulation_id=%s"
		start_result = self.execute_query(start_query, (sim_id,), fetch=True)
		
		if not start_result.success or not start_result.data:
			print(f"No simulation found for {sim_id}")
			return
		
		start_dt = start_result.data[0].get('simulation_start_datetime')
		
		# Count missing coordinates using SQL
		count_missing_sql = f"""
			SELECT COUNT(*) AS missing_count
			FROM {self._format_table('initialized_agents')} ia
			LEFT JOIN {self._agents_db}.l2_geo lg ON lg.LALVOTERID = ia.agent_id
			WHERE ia.simulation_id = %s AND (lg.latitude IS NULL OR lg.longitude IS NULL)
		"""
		miss_res = self.execute_query(count_missing_sql, (sim_id,), fetch=True)
		if miss_res.success and miss_res.data:
			try:
				# Respect global verbosity: print only when >= 2
				import os
				verbosity = int(os.getenv('VERBOSITY', '3'))
				if verbosity >= 2:
					print(f"Initialized agents without coordinates: {int(miss_res.data[0].get('missing_count', 0))}")
			except Exception:
				pass

		# Bulk insert present coordinates using INSERT ... SELECT
		insert_select_sql = f"""
			INSERT IGNORE INTO {self._format_table('agent_locations')}
			(simulation_id, agent_id, latitude, longitude, simulation_timestamp)
			SELECT s.simulation_id, ia.agent_id, lg.latitude, lg.longitude, s.simulation_start_datetime
			FROM {self._format_table('initialized_agents')} ia
			JOIN {self._format_table('simulations')} s ON s.simulation_id = %s
			JOIN {self._agents_db}.l2_geo lg ON lg.LALVOTERID = ia.agent_id
			WHERE ia.simulation_id = %s AND lg.latitude IS NOT NULL AND lg.longitude IS NOT NULL
		"""
		self.execute_query(insert_select_sql, (sim_id, sim_id), fetch=False)
		logger.info(f"Seeded starting locations for simulation {sim_id} (bulk)")

	def bulk_initialize_agents(self, sim_id: str, agent_ids: List[str]) -> None:
		"""
		Fast path to initialize agents for a simulation:
		- Ensure agent records exist (batch)
		- Register initialized agents (batch)
		- Seed starting locations with a single INSERT ... SELECT
		- Generate initial household balance sheets (one per household)
		- Generate missing personal summaries using L2 data (non-overwriting, optional)
		"""
		if not agent_ids:
			raise ValueError("agent_ids must be a non-empty list")

		# Highest verbosity timing
		try:
			verbosity = int(os.getenv('VERBOSITY', '3'))
		except Exception:
			verbosity = 3
		t_total_start = time.perf_counter()

		# 1) Ensure minimal agent records exist in agents DB
		t0 = time.perf_counter()
		self._ensure_agent_records_exist(agent_ids)
		if verbosity >= 3:
			logger.info(f"bulk_initialize_agents: ensured agent records in {time.perf_counter() - t0:.2f}s")

		# 2) Register initialized agents in batch
		t0 = time.perf_counter()
		self.register_initialized_agents(sim_id, agent_ids)
		if verbosity >= 3:
			logger.info(f"bulk_initialize_agents: registered initialized agents in {time.perf_counter() - t0:.2f}s")

		# 3) Seed starting locations in bulk
		t0 = time.perf_counter()
		self.seed_agent_start_locations(sim_id)
		if verbosity >= 3:
			logger.info(f"bulk_initialize_agents: seeded start locations in {time.perf_counter() - t0:.2f}s")

		# 4) Generate initial household balance sheets (one per household, idempotent)
		t0 = time.perf_counter()
		self._generate_initial_household_balance_sheets(sim_id, agent_ids)
		if verbosity >= 3:
			logger.info(f"bulk_initialize_agents: generated household balance sheets in {time.perf_counter() - t0:.2f}s")

		# 5) Ensure LLM personal summaries exist for all agents (optional, non-blocking)
		# Skip if SKIP_PERSONAL_SUMMARY_GENERATION is set to avoid blocking on errors
		skip_summaries = os.getenv('SKIP_PERSONAL_SUMMARY_GENERATION', '0').lower() in ('1', 'true', 'yes')
		if not skip_summaries:
			try:
				t0 = time.perf_counter()
				self._ensure_llm_personal_summaries(agent_ids, sim_id)
				if verbosity >= 3:
					logger.info(f"bulk_initialize_agents: ensured personal summaries in {time.perf_counter() - t0:.2f}s")
			except Exception as exc:
				logger.warning(f"Failed to generate personal summaries for simulation {sim_id}: {exc}")
				logger.warning("Continuing without personal summaries (agents will generate them on demand)")

		# 6) Seed initial spatial knowledge for agents (toggleable via env)
		try:
			enable_spatial = os.getenv('ENABLE_INITIAL_SPATIAL_KNOWLEDGE', '1').lower() in ('1', 'true', 'yes')
			if enable_spatial:
				t0 = time.perf_counter()
				self._seed_initial_agent_poi_knowledge(sim_id, agent_ids)
				if verbosity >= 3:
					logger.info(f"bulk_initialize_agents: seeded spatial knowledge in {time.perf_counter() - t0:.2f}s")
			else:
				logger.info("Skipping initial spatial knowledge seeding (ENABLE_INITIAL_SPATIAL_KNOWLEDGE=0)")
		except Exception as exc:
			logger.error(f"Failed to seed spatial knowledge for simulation {sim_id}: {exc}", exc_info=True)

		if verbosity >= 3:
			logger.info(f"bulk_initialize_agents: total time {time.perf_counter() - t_total_start:.2f}s")

	def _ensure_agent_records_exist(self, agent_ids: List[str]) -> None:
		"""Ensure bare agent rows exist in world_sim_agents.agents using bulk insert-ignore."""
		if not agent_ids:
			return
		from Database.database_manager import execute_query as dm_execute_query
		values_per_chunk = 1000
		insert_prefix = "INSERT IGNORE INTO agents (l2_voter_id) VALUES "
		for i in range(0, len(agent_ids), values_per_chunk):
			chunk = agent_ids[i:i+values_per_chunk]
			placeholders = ",".join(["(%s)"] * len(chunk))
			params: List[Any] = list(chunk)
			query = insert_prefix + placeholders
			# Execute against agents DB
			res = dm_execute_query(query, tuple(params), database=self._agents_db, fetch=False)
			if not res.success:
				logger.error(f"Failed ensuring agent records exist: {res.error}")

	def _ensure_llm_personal_summaries(self, agent_ids: List[str], simulation_id: Optional[str] = None) -> None:
		"""
		Ensure every agent has an LLM-generated personal summary.
		Respects AGENT_INIT_MAX_WORKERS for concurrency; fails hard if any summary cannot be created.
		
		Args:
			agent_ids: List of agent IDs to generate summaries for
			simulation_id: Optional simulation ID to pass to agents when creating them
		"""
		if not agent_ids:
			return

		from Database.managers import get_agents_manager
		ag_mgr = get_agents_manager()
		from Database.l2_data_manager import get_l2_data_by_voter_id
		from concurrent.futures import ThreadPoolExecutor, as_completed

		# Get verbosity for logging
		try:
			verbosity = int(os.getenv('VERBOSITY', '3'))
		except Exception:
			verbosity = 3

		# Get list of agents missing llm_personal using bulk SQL helper
		if verbosity >= 2:
			logger.info(f"Finding agents missing personal summaries from {len(agent_ids)} total agents...")
		missing_ids = ag_mgr.get_missing_summary_ids(agent_ids, summary_type="llm_personal")
		
		if not missing_ids:
			if verbosity >= 2:
				logger.info(f"All {len(agent_ids)} agents already have personal summaries")
			return
		
		if verbosity >= 2:
			logger.info(f"Found {len(missing_ids)} agents needing personal summaries (out of {len(agent_ids)} total)")
		
		# Bulk ensure all agents exist in database (single query)
		if verbosity >= 2:
			logger.info(f"Ensuring {len(missing_ids)} agent records exist...")
		ag_mgr.bulk_ensure_agents(missing_ids)

		def _flatten_l2(voter_data: Dict[str, Any]) -> Dict[str, Any]:
			l2_flat: Dict[str, Any] = {}
			for _table, row in (voter_data or {}).items():
				if not row:
					continue
				for k, v in row.items():
					if v is None:
						continue
					if k not in l2_flat or l2_flat[k] in (None, ''):
						l2_flat[k] = v
			return l2_flat

		# Determine worker count
		try:
			workers = int(os.getenv('AGENT_INIT_MAX_WORKERS', '1'))
		except Exception:
			workers = 1
		workers = max(1, workers)


		# Progress bar setup (tqdm optional)
		try:
			from tqdm.auto import tqdm  # type: ignore
		except Exception:  # pragma: no cover
			def tqdm(x=None, **kwargs):
				return x if x is not None else range(0)

		# Batch processing parameters
		try:
			batch_size = int(os.getenv('PERSONAL_SUMMARY_BATCH_SIZE', '50'))
		except Exception:
			batch_size = 50
		batch_size = max(1, batch_size)

		# Process in batches
		for i in range(0, len(missing_ids), batch_size):
			batch_ids = missing_ids[i:i + batch_size]
			results: List[Tuple[str, str, str, Dict[str, Any]]] = []
			# Prefetch L2 data sequentially to avoid connection spikes
			prefetched: Dict[str, Dict[str, Any]] = {}
			for aid in batch_ids:
				try:
					voter_data = get_l2_data_by_voter_id(aid)
					prefetched[aid] = _flatten_l2(voter_data)
					if verbosity >= 2:
						logger.info(f"Prefetched L2 data for agent {aid}")
				except Exception as exc:
					if verbosity >= 1:
						logger.warning(f"Failed to prefetch L2 data for agent {aid}: {exc}")
					prefetched[aid] = {}
			
			use_mp = os.getenv('PERSONAL_SUMMARY_USE_MULTIPROCESSING', '1').lower() in ('1','true','yes')
			
			def _generate_summary_local(aid_local: str) -> Tuple[str, str, str, Dict[str, Any]]:
				from Agent.models import AgentDTO
				from Agent.services.summary_service import generate_personal_summary

				dto = AgentDTO(
					agent_id=str(aid_local),
					simulation_id=simulation_id,
					l2_data=prefetched.get(aid_local, {}),
				)
				summary, reasoning, metadata = generate_personal_summary(dto)
				if not summary or summary == "LLM API not available":
					raise RuntimeError(f"Failed to generate LLM summary for agent {aid_local}")
				return (aid_local, summary, reasoning, metadata)

			if workers == 1 and not use_mp:
				for aid in tqdm(batch_ids, desc="Generating personal summaries", unit="agent"):
					results.append(_generate_summary_local(aid))
			elif use_mp:
				with ProcessPoolExecutor(
					max_workers=workers,
					initializer=_init_worker_db_env,
					initargs=("",)
				) as executor:
					futs = {executor.submit(_generate_personal_summary_worker, aid, prefetched.get(aid, {}), simulation_id): aid for aid in batch_ids}
					pbar = tqdm(total=len(batch_ids), desc="Generating personal summaries", unit="agent")
					for fut in as_completed(futs):
						res = fut.result()
						results.append(res)
						pbar.update(1)
					pbar.close()
			else:
				with ThreadPoolExecutor(max_workers=workers) as executor:
					futs = {executor.submit(_generate_summary_local, aid): aid for aid in batch_ids}
					pbar = tqdm(total=len(batch_ids), desc="Generating personal summaries", unit="agent")
					for fut in as_completed(futs):
						res = fut.result()
						results.append(res)
						pbar.update(1)
					pbar.close()
			
			# Bulk upsert after each batch
			try:
				bulk_rows: List[Dict[str, Any]] = [
					{"agent_id": aid, "summary": summary, "reasoning": reasoning, "metadata": metadata}
					for (aid, summary, reasoning, metadata) in results if summary
				]
				if bulk_rows:
					get_agents_manager().bulk_upsert_llm_personal_summaries(bulk_rows)
			except Exception as e:
				logger.warning(f"Failed bulk upsert for personal summaries: {e}")


	def _generate_initial_household_balance_sheets(self, sim_id: str, agent_ids: List[str]) -> None:
		"""
		Generate initial household balance sheets for all agents in the simulation.
		Uses batch mode by default for efficiency, with fallback to per-agent mode.
		"""
		if not agent_ids:
			return
		
		import os
		verbosity = int(os.getenv('VERBOSITY', '3'))
		batch_mode = os.getenv('BALANCE_SHEET_BATCH_MODE', '1').lower() in ('1', 'true', 'yes')
		
		if batch_mode:
			self._generate_balance_sheets_batch_mode(sim_id, agent_ids, verbosity)
		else:
			self._generate_balance_sheets_legacy_mode(sim_id, agent_ids, verbosity)
	
	def _generate_balance_sheets_batch_mode(self, sim_id: str, agent_ids: List[str], verbosity: int) -> None:
		"""
		Generate balance sheets using batch mode: pre-fetch all data, compute in parallel, bulk insert.
		This dramatically reduces DB connections and is safe for multiprocessing.
		"""
		from Simulation.data_generation.agent_balance_sheet_generation import (
			batch_resolve_households,
			batch_check_existing_balance_sheets,
			batch_extract_features,
			batch_fetch_hpi_data,
			batch_fetch_calibration_stats,
			generate_balance_sheet_compute_only
		)
		from Database.managers.alternative_data import get_alternative_data_manager
		import os
		from decimal import Decimal
		
		if verbosity >= 3:
			logger.info(f"Generating balance sheets (BATCH MODE) for {len(agent_ids)} agents in simulation {sim_id}")
		
		# Step 1: Get simulation start datetime (single query)
		sim_info = self.get_simulation(sim_id)
		if not sim_info:
			logger.error(f"Simulation {sim_id} not found")
			return
		
		start_datetime = sim_info.get('simulation_start_datetime')
		if not start_datetime:
			logger.error(f"No simulation_start_datetime for simulation {sim_id}")
			return
		
		# Step 2: Batch resolve households (single query)
		if verbosity >= 2:
			logger.info("Resolving households...")
		household_map = batch_resolve_households(self, agent_ids)
		
		# Deduplicate to one entry per household
		unique_households = {}
		for agent_id, household_id in household_map.items():
			if household_id not in unique_households:
				unique_households[household_id] = agent_id  # Keep first agent for this household
		
		if verbosity >= 2:
			logger.info(f"Found {len(unique_households)} unique households from {len(agent_ids)} agents")
		
		# Step 3: Check which households already exist (single query)
		existing_households = batch_check_existing_balance_sheets(
			self,
			sim_id,
			list(unique_households.keys()),
			start_datetime
		)
		
		# Filter to households that need balance sheets
		households_to_generate = {
			hh_id: agent_id
			for hh_id, agent_id in unique_households.items()
			if hh_id not in existing_households
		}
		
		if not households_to_generate:
			if verbosity >= 2:
				logger.info("All households already have balance sheets, skipping generation")
			return
		
		if verbosity >= 2:
			logger.info(f"Generating balance sheets for {len(households_to_generate)} households ({len(existing_households)} already exist)")
		
		# Step 4: Batch extract features for all agents (single query per household rep)
		representative_agents = list(households_to_generate.values())
		if verbosity >= 2:
			logger.info("Extracting features...")
		features_map = batch_extract_features(self, representative_agents)
		
		# Step 5: Batch fetch calibration stats for unique locations
		if verbosity >= 2:
			logger.info("Fetching calibration statistics...")
		calibration_stats = batch_fetch_calibration_stats(features_map)
		
		# Step 6: Batch fetch HPI data for unique (level, place_id) pairs
		hpi_requests = []
		for agent_id in representative_agents:
			features = features_map.get(str(agent_id), {})
			level = features.get('hpi_level')
			place_id = features.get('hpi_place_id')
			if level and place_id:
				hpi_requests.append((level, place_id))
		
		if verbosity >= 2:
			unique_hpi = len(set(hpi_requests))
			logger.info(f"Fetching HPI data for {unique_hpi} unique locations...")
		
		alt_mgr = get_alternative_data_manager()
		hpi_index_cache = batch_fetch_hpi_data(alt_mgr, hpi_requests)
		
		# Step 7: Generate balance sheets in parallel (compute-only, no DB)
		workers_env = os.getenv('BALANCE_SHEET_WORKERS')
		disable_mp = os.getenv('DISABLE_MULTIPROCESSING', '0').lower() in ('1', 'true', 'yes')
		try:
			max_workers = int(workers_env) if workers_env else (os.cpu_count() or 2)
		except Exception:
			max_workers = os.cpu_count() or 2
		
		if disable_mp:
			max_workers = 1
		
		balance_sheets = []
		error_count = 0
		
		if max_workers > 1:
			# Parallel compute-only workers
			from concurrent.futures import ProcessPoolExecutor, as_completed
			
			# Build work items
			work_items = []
			for household_id, agent_id in households_to_generate.items():
				features = features_map.get(str(agent_id), {})
				work_items.append((
					sim_id,
					household_id,
					agent_id,
					start_datetime,
					features,
					hpi_index_cache,
					calibration_stats,
					None  # rng_seed
				))
			
			if verbosity >= 2:
				logger.info(f"Computing balance sheets using {max_workers} workers...")
			
			# Progress bar setup
			use_tqdm = verbosity < 1
			if use_tqdm:
				try:
					from tqdm import tqdm
					pbar = tqdm(total=len(work_items), desc="Computing balance sheets", unit="household")
				except ImportError:
					use_tqdm = False
					pbar = None
			else:
				pbar = None
			
			with ProcessPoolExecutor(max_workers=max_workers) as executor:
				futures = [executor.submit(generate_balance_sheet_compute_only, *item) for item in work_items]
				for fut in as_completed(futures):
					try:
						bs = fut.result()
						balance_sheets.append(bs)
					except Exception as e:
						logger.warning(f"Failed to compute balance sheet: {e}")
						error_count += 1
					finally:
						if pbar:
							try:
								pbar.update(1)
							except Exception:
								pass
			
			if pbar:
				try:
					pbar.close()
				except Exception:
					pass
		else:
			# Sequential computation
			if verbosity >= 2:
				logger.info("Computing balance sheets sequentially...")
			
			for household_id, agent_id in households_to_generate.items():
				try:
					features = features_map.get(str(agent_id), {})
					bs = generate_balance_sheet_compute_only(
						sim_id,
						household_id,
						agent_id,
						start_datetime,
						features,
						hpi_index_cache,
						calibration_stats,
						None
					)
					balance_sheets.append(bs)
				except Exception as e:
					logger.warning(f"Failed to compute balance sheet for household {household_id}: {e}")
					error_count += 1
		
		# Step 8: Bulk insert all balance sheets (single vectorized operation)
		if balance_sheets:
			if verbosity >= 2:
				logger.info(f"Inserting {len(balance_sheets)} balance sheets...")
			
			try:
				self._bulk_insert_balance_sheets(balance_sheets)
				if verbosity >= 2:
					logger.info(
						f"Completed balance sheet generation for simulation {sim_id}: "
						f"{len(balance_sheets)} successful, {error_count} errors"
					)
			except Exception as e:
				logger.error(f"Failed to bulk insert balance sheets: {e}")
		else:
			if verbosity >= 2:
				logger.warning("No balance sheets were generated")
	
	def _generate_balance_sheets_legacy_mode(self, sim_id: str, agent_ids: List[str], verbosity: int) -> None:
		"""
		Legacy per-agent mode with individual DB connections (kept for compatibility).
		"""
		from Simulation.data_generation import ensure_initial_household_balance_sheet_for_agent
		import os
		from concurrent.futures import ProcessPoolExecutor, as_completed
		
		# For verbosity < 1, use tqdm progress bar
		if verbosity < 1:
			try:
				from tqdm import tqdm
				use_tqdm = True
			except ImportError:
				use_tqdm = False
				logger.warning("tqdm not installed, falling back to basic logging")
		else:
			use_tqdm = False

		# Only log initialization message if verbosity >= 3
		if verbosity >= 3:
			logger.info(f"Generating initial household balance sheets (LEGACY MODE) for {len(agent_ids)} agents in simulation {sim_id}")

		success_count = 0
		error_count = 0

		# Use multiprocessing for parallel balance sheet generation (can be disabled via env)
		workers_env = os.getenv('BALANCE_SHEET_WORKERS')
		disable_mp = os.getenv('DISABLE_MULTIPROCESSING', '0').lower() in ('1', 'true', 'yes')
		try:
			max_workers = int(workers_env) if workers_env else (os.cpu_count() or 2)
		except Exception:
			max_workers = os.cpu_count() or 2

		if disable_mp:
			max_workers = 1

		if max_workers and max_workers > 1:
			# Prepare a minimal DB environment for workers to avoid connection spikes
			# Only require simulations, agents, and alternative_data databases in workers
			alt_db = os.getenv('DB_ALT_NAME', 'world_sim_alternative_data')
			required_dbs = f"{self._db_name},{self._agents_db},{alt_db}"
			pbar = None
			if use_tqdm:
				try:
					from tqdm import tqdm
					pbar = tqdm(total=len(agent_ids), desc="Creating balance sheets", unit="agent")
				except Exception:
					pbar = None
			with ProcessPoolExecutor(
				max_workers=max_workers,
				initializer=_init_worker_db_env,
				initargs=(required_dbs,)
			) as executor:
				futures = [executor.submit(ensure_initial_household_balance_sheet_for_agent, sim_id, aid, None, verbosity) for aid in agent_ids]
				for fut in as_completed(futures):
					try:
						fut.result()
						success_count += 1
					except Exception as e:
						logger.warning(f"Failed to generate balance sheet: {e}")
						error_count += 1
					finally:
						if pbar:
							try:
								pbar.update(1)
							except Exception:
								pass
			if pbar:
				try:
					pbar.close()
				except Exception:
					pass
		else:
			# Fallback to sequential generation
			from tqdm import tqdm
			iterator = tqdm(agent_ids, desc="Creating balance sheets", unit="agent") if use_tqdm else agent_ids
			for agent_id in iterator:
				try:
					ensure_initial_household_balance_sheet_for_agent(
						simulation_id=sim_id,
						lalvoterid=agent_id,
						rng_seed=None,
						verbosity=verbosity
					)
					success_count += 1
				except Exception as e:
					logger.warning(f"Failed to generate balance sheet for agent {agent_id}: {e}")
					error_count += 1

		# Only log completion message if verbosity >= 2
		if verbosity >= 2:
			logger.info(
				f"Completed balance sheet generation for simulation {sim_id}: "
				f"{success_count} successful, {error_count} errors"
			)
	
	def _bulk_insert_balance_sheets(self, balance_sheets: List[Dict[str, Any]]) -> None:
		"""
		Insert multiple balance sheets using a single vectorized operation.
		"""
		from decimal import Decimal
		
		if not balance_sheets:
			return
		
		# Prepare data for vectorized insert
		insert_data = []
		for bs in balance_sheets:
			row = {
				'simulation_id': bs['simulation_id'],
				'household_id': bs['household_id'],
				'sim_clock_datetime': bs['sim_clock_datetime'],
				'net_worth_bucket': bs.get('net_worth_bucket', ''),
				'hpi_level': bs.get('hpi_level'),
				'hpi_place_id': bs.get('hpi_place_id'),
				'vehicle_lambda_decay': bs.get('vehicle_lambda_decay', 0.18),
				'primaryHomeValue': Decimal(str(round(bs.get('primaryHomeValue', 0.0), 2))),
				'secondaryREValue': Decimal(str(round(bs.get('secondaryREValue', 0.0), 2))),
				'retirementAccounts': Decimal(str(round(bs.get('retirementAccounts', 0.0), 2))),
				'taxableInvestments': Decimal(str(round(bs.get('taxableInvestments', 0.0), 2))),
				'liquidSavings': Decimal(str(round(bs.get('liquidSavings', 0.0), 2))),
				'vehiclesValue': Decimal(str(round(bs.get('vehiclesValue', 0.0), 2))),
				'durablesOther': Decimal(str(round(bs.get('durablesOther', 0.0), 2))),
				'mortgageBalance': Decimal(str(round(bs.get('mortgageBalance', 0.0), 2))),
				'autoLoans': Decimal(str(round(bs.get('autoLoans', 0.0), 2))),
				'creditCardRevolving': Decimal(str(round(bs.get('creditCardRevolving', 0.0), 2))),
				'studentLoans': Decimal(str(round(bs.get('studentLoans', 0.0), 2))),
				'otherDebt': Decimal(str(round(bs.get('otherDebt', 0.0), 2))),
				'assetsTotal': Decimal(str(round(bs.get('assetsTotal', 0.0), 2))),
				'liabilitiesTotal': Decimal(str(round(bs.get('liabilitiesTotal', 0.0), 2))),
				'netWorth': Decimal(str(round(bs.get('netWorth', 0.0), 2))),
			}
			insert_data.append(row)
		
		# Use vectorized insert with IGNORE to handle duplicates
		table_name = self._format_table('household_balance_sheet_samples')
		
		# Build the INSERT IGNORE query
		columns = list(insert_data[0].keys())
		columns_str = ', '.join(columns)
		placeholders = ', '.join(['%s'] * len(columns))
		
		query = f"""
			INSERT IGNORE INTO {table_name} ({columns_str})
			VALUES ({placeholders})
		"""
		
		# Prepare params list
		params_list = [tuple(row[col] for col in columns) for row in insert_data]
		
		# Execute batch insert
		result = self.execute_many(query, params_list)
		
		if not result.success:
			logger.error(f"Failed to bulk insert balance sheets: {result.error}")
			raise Exception(f"Failed to bulk insert balance sheets: {result.error}")

	# ------------------------------------------------------------------
	# Spatial knowledge helpers
	# ------------------------------------------------------------------

	def _seed_initial_agent_poi_knowledge(self, sim_id: str, agent_ids: List[str]) -> None:
		"""
		Seed initial POI knowledge for all agents in a simulation.
		"""
		if not agent_ids:
			return

		sim_info = self.get_simulation(sim_id)
		if not sim_info or not sim_info.get("simulation_start_datetime"):
			logger.warning("Cannot seed POI knowledge without simulation start datetime")
			return

		start_dt: datetime = sim_info["simulation_start_datetime"]
		profiles = self._fetch_agent_spatial_profiles(sim_id, agent_ids, start_dt)
		if not profiles:
			logger.warning("No agent spatial profiles were produced; skipping POI seeding")
			return

		clusters = cluster_agents_dynamic(profiles, density_class="suburban")
		if not clusters:
			logger.warning("Clustering produced no results; skipping POI seeding")
			return

		records: List[Dict[str, Any]] = []
		for members in clusters.values():
			if not members:
				continue

			# Per-agent dynamic search radius until 250 candidates or 20-mile diameter (10-mile radius)
			target_candidates_per_agent = 250
			max_radius_km = 16.0934  # 10 miles
			growth_factor = 1.8
			initial_radius_km = 1.0

			# Initialize per-agent radii
			radius_by_agent: Dict[str, float] = {p.agent_id: initial_radius_km for p in members}
			per_agent_candidates: Dict[str, List[POICandidate]] = {p.agent_id: [] for p in members}

			# Haversine helper (km)
			def _hv_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
				from math import radians, sin, cos, asin, sqrt
				R = 6371.0
				phi1, phi2 = radians(lat1), radians(lat2)
				dphi = radians(lat2 - lat1)
				dlambda = radians(lon2 - lon1)
				a = sin(dphi / 2.0) ** 2 + cos(phi1) * cos(phi2) * sin(dlambda / 2.0) ** 2
				return 2.0 * R * asin(sqrt(a))

			# Iterate, widening bbox once per cluster per pass for efficiency
			for _ in range(7):
				# Determine cluster query radius as max of current agent radii (capped)
				cluster_radius_km = min(max((radius_by_agent[p.agent_id] for p in members)), max_radius_km)
				bbox = self._compute_cluster_bbox(members, cluster_radius_km)
				candidates = self._fetch_poi_candidates(bbox)

				# If no candidates returned, widen all radii (if possible) and retry
				if not candidates:
					all_capped = True
					for aid in list(radius_by_agent.keys()):
						if radius_by_agent[aid] < max_radius_km:
							radius_by_agent[aid] = min(max_radius_km, radius_by_agent[aid] * growth_factor)
							all_capped = False
					if all_capped:
						break
					continue

				# Compute per-agent candidate sets within each agent's current radius
				for profile in members:
					r = min(max_radius_km, radius_by_agent[profile.agent_id])
					filtered: List[POICandidate] = []
					for poi in candidates:
						d = _hv_km(profile.home_lat, profile.home_lon, poi.lat, poi.lon)
						if d <= r:
							filtered.append(POICandidate(
								osm_id=poi.osm_id,
								category_name=poi.category_name,
								subcategory_name=poi.subcategory_name,
								lat=poi.lat,
								lon=poi.lon,
								distance_km=d,
							))
					per_agent_candidates[profile.agent_id] = filtered

				# Expand radii for agents that still have < target candidates and are not capped
				needs_more = False
				for profile in members:
					if len(per_agent_candidates.get(profile.agent_id, [])) < target_candidates_per_agent and radius_by_agent[profile.agent_id] < max_radius_km:
						radius_by_agent[profile.agent_id] = min(max_radius_km, radius_by_agent[profile.agent_id] * growth_factor)
						needs_more = True

				if not needs_more:
					break

			# Seed per agent using their own candidate pool and density classification
			# First, seed individual knowledge for all agents
			per_agent_seeded: Dict[str, List[Dict[str, Any]]] = {}
			for profile in members:
				agent_id = profile.agent_id
				agent_candidates = per_agent_candidates.get(agent_id, [])
				density_cfg = get_density_class(len(agent_candidates))
				seed_map = seed_agent_candidates([profile], agent_candidates, density_cfg.name, start_dt)
				for a_id, rows in seed_map.items():
					for row in rows:
						entry = dict(row)
						entry["simulation_id"] = sim_id
						entry["agent_id"] = a_id
						records.append(entry)
						if a_id not in per_agent_seeded:
							per_agent_seeded[a_id] = []
						per_agent_seeded[a_id].append(entry)
			
			# Apply household social spillover (share 10-20% of knowledge within households)
			import random
			from collections import defaultdict
			
			# Group agents by household
			household_groups: Dict[str, List[str]] = defaultdict(list)
			for profile in members:
				hid = profile.household_id or profile.agent_id
				household_groups[hid].append(profile.agent_id)
			
			# Share knowledge within households
			for household_id, member_ids in household_groups.items():
				if len(member_ids) < 2:
					continue  # No sharing for single-person households
				
				# For each agent, share some of their POI knowledge with household members
				for agent_id in member_ids:
					agent_pois = per_agent_seeded.get(agent_id, [])
					if not agent_pois:
						continue
					
					# Determine share fraction for this household (10-20%)
					share_fraction = random.uniform(*SOCIAL_SPILLOVER_CONFIG["household_share_fraction"])
					num_to_share = max(1, int(len(agent_pois) * share_fraction))
					
					# Select POIs to share (prefer essentials and higher-score POIs)
					pois_to_share = sorted(agent_pois, key=lambda x: x.get("distance_km_from_home", 999))[:num_to_share]
					
					# Share with each household member
					for other_agent_id in member_ids:
						if other_agent_id == agent_id:
							continue
						
						for poi_entry in pois_to_share:
							# Create shared knowledge entry
							shared_entry = dict(poi_entry)
							shared_entry["agent_id"] = other_agent_id
							shared_entry["source"] = "social"
							# Keep same timestamps (they learned from household member before sim start)
							# But might want to adjust strength slightly - for now keep as-is
							records.append(shared_entry)

		if records:
			self._bulk_insert_poi_seen(records)
			logger.info(f"Seeded {len(records)} POI knowledge rows for simulation {sim_id}")

	def _fetch_agent_spatial_profiles(
		self,
		sim_id: str,
		agent_ids: List[str],
		start_dt: datetime,
	) -> List[AgentSpatialProfile]:
		"""Fetch agent attributes required for spatial heuristics."""
		if not agent_ids:
			return []

		output: List[AgentSpatialProfile] = []
		chunk_size = 500
		for i in range(0, len(agent_ids), chunk_size):
			chunk = agent_ids[i:i + chunk_size]
			placeholders = ",".join(["%s"] * len(chunk))
			query = f"""
				SELECT al.agent_id,
					   al.latitude,
					   al.longitude,
					   o1.ConsumerData_Number_Of_Persons_in_HH AS household_size,
					   COALESCE(o1.Residence_Families_FamilyID, o1.Mailing_Families_FamilyID) AS household_id,
					   o3.ConsumerData_Auto_Year_1,
					   o3.ConsumerData_Auto_Year_2,
					   o3.ConsumerData_Presence_Of_CC,
					   o3.ConsumerData_Presence_Of_Premium_CC,
					   core.Voters_Age,
					   o1.ConsumerData_Inferred_HH_Rank,
					   p3.ConsumerData_Household_Net_Worth,
					   o3.ConsumerData_Home_Purchase_Year,
					   o3.ConsumerData_Home_Purchase_Date,
					   o2.ConsumerData_Health_And_Beauty,
					   o2.ConsumerData_Health_Medical,
					   o2.ConsumerData_Exercise_Health_Grouping,
					   o3.ConsumerData_Travel_Domestic,
					   o3.ConsumerData_Travel_Intl,
					   o3.ConsumerData_Travel_Grouping,
					   o3.ConsumerData_Auto_Buy_Interest,
					   o2.ConsumerData_Lifestyle_Passion_Collectibles,
					   o3.ConsumerData_Do_It_Yourself_Lifestyle_Committed_Choice
				FROM {self._format_table('agent_locations')} al
				LEFT JOIN {self._agents_db}.l2_other_part_1 o1 ON o1.LALVOTERID = al.agent_id
				LEFT JOIN {self._agents_db}.l2_other_part_2 o2 ON o2.LALVOTERID = al.agent_id
				LEFT JOIN {self._agents_db}.l2_other_part_3 o3 ON o3.LALVOTERID = al.agent_id
				LEFT JOIN {self._agents_db}.l2_agent_core core ON core.LALVOTERID = al.agent_id
				LEFT JOIN {self._agents_db}.l2_political_part_3 p3 ON p3.LALVOTERID = al.agent_id
				WHERE al.simulation_id = %s
				  AND al.agent_id IN ({placeholders})
			"""
			params: List[Any] = [sim_id, *chunk]
			result = self.execute_query(query, tuple(params), fetch=True)
			if not result.success or not result.data:
				continue

			for row in result.data:
				if row.get("latitude") is None or row.get("longitude") is None:
					continue

				has_vehicle = any(
					row.get(field) not in (None, "", "0", 0)
					for field in ("ConsumerData_Auto_Year_1", "ConsumerData_Auto_Year_2",
								  "ConsumerData_Presence_Of_CC", "ConsumerData_Presence_Of_Premium_CC")
				)

				household_size = row.get("household_size")
				age = row.get("Voters_Age")

				income_rank = row.get("ConsumerData_Inferred_HH_Rank")
				if income_rank is not None:
					try:
						val = float(income_rank)
						if val <= 10:
							income_quantile = max(0.0, min(1.0, (val - 1.0) / 9.0))
						else:
							income_quantile = max(0.0, min(1.0, (val - 1.0) / 99.0))
					except Exception:
						income_quantile = 0.5
				else:
					income_quantile = 0.5

				tenure_years = 5.0
				try:
					if row.get("ConsumerData_Home_Purchase_Year"):
						tenure_years = max(0.0, start_dt.year - int(float(row["ConsumerData_Home_Purchase_Year"])))
					elif isinstance(row.get("ConsumerData_Home_Purchase_Date"), datetime):
						tenure_years = max(0.0, (start_dt - row["ConsumerData_Home_Purchase_Date"]).days / 365.25)
				except Exception:
					tenure_years = 5.0

				# Determine mobility mode from vehicle ownership and age
				if has_vehicle:
					mobility_mode = "car"
				elif age and age < 30:
					mobility_mode = "bike"  # Younger people more likely to bike
				elif age and age > 65:
					mobility_mode = "walk"  # Seniors more likely to walk
				else:
					mobility_mode = "walk"  # Default to walk
				
				# Extract L2 interests from available fields
				l2_interests = []
				interest_fields = [
					"ConsumerData_Health_And_Beauty",
					"ConsumerData_Health_Medical",
					"ConsumerData_Exercise_Health_Grouping",
					"ConsumerData_Travel_Domestic",
					"ConsumerData_Travel_Intl",
					"ConsumerData_Travel_Grouping",
					"ConsumerData_Auto_Buy_Interest",
					"ConsumerData_Lifestyle_Passion_Collectibles",
					"ConsumerData_Do_It_Yourself_Lifestyle_Committed_Choice",
				]
				for field in interest_fields:
					val = row.get(field)
					if val and val not in (None, "", "0", 0, "N", "No"):
						# Extract meaningful part of field name
						interest_name = field.replace("ConsumerData_", "").replace("_", " ").lower()
						l2_interests.append(interest_name)

				# Get household_id (fallback to synthetic ID if not available)
				household_id = str(row.get("household_id")) if row.get("household_id") else f"SYNTH_{row['agent_id']}"

				output.append(AgentSpatialProfile(
					agent_id=row["agent_id"],
					home_lat=float(row["latitude"]),
					home_lon=float(row["longitude"]),
					household_size=int(household_size) if household_size is not None else None,
					has_vehicle=has_vehicle,
					age=float(age) if age is not None else None,
					income_quantile=income_quantile,
					wealth_bucket=row.get("ConsumerData_Household_Net_Worth"),
					tenure_years=tenure_years,
					mobility_mode=mobility_mode,
					household_id=household_id,
					l2_interests=l2_interests if l2_interests else None,
				))

		return output

	def _compute_cluster_bbox(
		self,
		agents: List[AgentSpatialProfile],
		buffer_km: float,
	) -> Tuple[float, float, float, float]:
		"""Compute a bounding box covering agents with buffer in km."""
		min_lat = min(agent.home_lat for agent in agents)
		max_lat = max(agent.home_lat for agent in agents)
		min_lon = min(agent.home_lon for agent in agents)
		max_lon = max(agent.home_lon for agent in agents)

		lat_pad = buffer_km / 111.0
		center_lat = (min_lat + max_lat) / 2.0
		lon_pad = buffer_km / max(0.0001, 111.0 * math.cos(math.radians(center_lat)))

		return (
			min_lat - lat_pad,
			max_lat + lat_pad,
			min_lon - lon_pad,
			max_lon + lon_pad,
		)

	def _fetch_poi_candidates(self, bbox: Tuple[float, float, float, float]) -> List[POICandidate]:
		"""Fetch POI candidates in a bounding box from PostGIS."""
		min_lat, max_lat, min_lon, max_lon = bbox
		
		try:
			import psycopg2.extras
			
			with _get_postgis_connection() as conn:
				with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
					# Query PostGIS planet_osm_point table, excluding "other" and "building" only POIs
					query = """
						SELECT 
							osm_id,
							ST_Y(ST_Transform(way, 4326)) AS lat,
							ST_X(ST_Transform(way, 4326)) AS lon,
							name,
							amenity, shop, tourism, leisure, office, religion, historic, place,
							hstore_to_json(tags) AS tags_json
						FROM planet_osm_point
						WHERE way && ST_Transform(ST_MakeEnvelope(%s, %s, %s, %s, 4326), 3857)
						AND (
							amenity IS NOT NULL OR
							shop IS NOT NULL OR
							tourism IS NOT NULL OR
							leisure IS NOT NULL OR
							office IS NOT NULL OR
							religion IS NOT NULL OR
							historic IS NOT NULL OR
							place IS NOT NULL OR
							tags ? 'amenity' OR
							tags ? 'shop' OR
							tags ? 'tourism' OR
							tags ? 'leisure' OR
							tags ? 'healthcare' OR
							tags ? 'office' OR
							tags ? 'craft' OR
							tags ? 'religion' OR
							tags ? 'historic' OR
							tags ? 'place'
						)
						LIMIT 50000
					"""
					
					cur.execute(query, (min_lon, min_lat, max_lon, max_lat))
					rows = cur.fetchall()
					
					if not rows:
						logger.warning(f"No POIs found in bbox [{min_lat}, {max_lat}, {min_lon}, {max_lon}]")
						return []
					
					candidates = []
					for row in rows:
						# Use frontend convention: category = OSM key (amenity/shop/...), subcategory = value (restaurant/supermarket/...)
						if row.get('amenity'):
							category_name = 'amenity'
							subcategory_name = str(row.get('amenity'))
						elif row.get('shop'):
							category_name = 'shop'
							subcategory_name = str(row.get('shop'))
						elif row.get('tourism'):
							category_name = 'tourism'
							subcategory_name = str(row.get('tourism'))
						elif row.get('leisure'):
							category_name = 'leisure'
							subcategory_name = str(row.get('leisure'))
						elif row.get('office'):
							category_name = 'office'
							subcategory_name = str(row.get('office'))
						elif row.get('religion'):
							category_name = 'religion'
							subcategory_name = str(row.get('religion'))
						elif row.get('historic'):
							category_name = 'historic'
							subcategory_name = str(row.get('historic'))
						elif row.get('place'):
							category_name = 'place'
							subcategory_name = str(row.get('place'))
						elif row.get('building'):
							category_name = 'building'
							subcategory_name = str(row.get('building'))
						else:
							category_name = 'other'
							subcategory_name = 'unknown'
						
						# Extract name and brand from tags
						name = row.get('name')
						tags_json = row.get('tags_json') or {}
						brand = tags_json.get('brand') if isinstance(tags_json, dict) else None
						
						candidates.append(POICandidate(
							osm_id=int(row['osm_id']),
							category_name=str(category_name),
							subcategory_name=str(subcategory_name),
							lat=float(row['lat']),
							lon=float(row['lon']),
							name=name,
							brand=brand,
						))
					
					logger.info(f"Found {len(candidates)} POI candidates in bbox")
					return candidates
					
		except Exception as e:
			logger.error(f"Failed to fetch POI candidates from PostGIS: {e}", exc_info=True)
			return []

	def _bulk_insert_poi_seen(self, rows: List[Dict[str, Any]]) -> None:
		"""Insert POI knowledge rows using INSERT IGNORE to preserve existing entries.
		Also ensures POIs exist in poi_categories table by syncing from geo database."""
		if not rows:
			return

		# First, ensure poi_categories has the POIs we're about to reference
		# Extract unique OSM IDs from rows
		osm_ids = list(set(row.get("osm_id") for row in rows if row.get("osm_id")))
		if osm_ids:
			self._ensure_poi_categories_exist(osm_ids)

		columns = [
			"simulation_id",
			"agent_id",
			"osm_id",
			"distance_km_from_home",
			"times_seen",
			"first_time_seen",
			"last_time_seen",
			"number_of_times_visited",
			"last_time_visited",
			"first_time_visited",
			"loaded_at_start_of_simulation",
			"source",
		]

		sql = f"""
			INSERT IGNORE INTO {self._format_table('poi_seen')}
			({", ".join(columns)})
			VALUES ({", ".join(["%s"] * len(columns))})
		"""

		params = [tuple(row.get(col) for col in columns) for row in rows]
		self.execute_many(sql, params)
	
	def _ensure_poi_categories_exist(self, osm_ids: List[int]) -> None:
		"""Ensure POIs exist in poi_categories by fetching from PostGIS and inserting."""
		if not osm_ids:
			return
		
		try:
			import psycopg2.extras
			
			# Batch into chunks to avoid parameter limit issues
			chunk_size = 500
			for i in range(0, len(osm_ids), chunk_size):
				chunk = osm_ids[i:i+chunk_size]
				placeholders = ",".join(["%s"] * len(chunk))
				
				# Fetch POIs from PostGIS that need to be added
				with _get_postgis_connection() as conn:
					with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
						query = f"""
							SELECT 
								osm_id,
								ST_Y(ST_Transform(way, 4326)) AS lat,
								ST_X(ST_Transform(way, 4326)) AS lon,
								name,
								amenity, shop, tourism, leisure, office, religion, historic, place, building,
								hstore_to_json(tags) AS tags_json
							FROM planet_osm_point
							WHERE osm_id IN ({placeholders})
						"""
						
						cur.execute(query, tuple(chunk))
						poi_rows = cur.fetchall()
						
						if not poi_rows:
							continue
						
						# Prepare data for insertion using frontend convention (key/value)
						insert_data = []
						for row in poi_rows:
							if row.get('amenity'):
								category_name = 'amenity'
								subcategory_name = str(row.get('amenity'))
							elif row.get('shop'):
								category_name = 'shop'
								subcategory_name = str(row.get('shop'))
							elif row.get('tourism'):
								category_name = 'tourism'
								subcategory_name = str(row.get('tourism'))
							elif row.get('leisure'):
								category_name = 'leisure'
								subcategory_name = str(row.get('leisure'))
							elif row.get('office'):
								category_name = 'office'
								subcategory_name = str(row.get('office'))
							elif row.get('religion'):
								category_name = 'religion'
								subcategory_name = str(row.get('religion'))
							elif row.get('historic'):
								category_name = 'historic'
								subcategory_name = str(row.get('historic'))
							elif row.get('place'):
								category_name = 'place'
								subcategory_name = str(row.get('place'))
							elif row.get('building'):
								category_name = 'building'
								subcategory_name = str(row.get('building'))
							else:
								category_name = 'other'
								subcategory_name = 'unknown'
							
							# Extract name and brand
							name = row.get('name')
							tags_json = row.get('tags_json') or {}
							brand = tags_json.get('brand') if isinstance(tags_json, dict) else None
							
							insert_data.append((
								int(row['osm_id']),
								name,
								str(category_name),
								str(subcategory_name),
								float(row['lat']),
								float(row['lon'])
							))
						
						# Insert into poi_categories table
						if insert_data:
							insert_sql = f"""
								INSERT IGNORE INTO {self._format_table('poi_categories')}
								(osm_id, name, category_name, subcategory_name, lat, lon)
								VALUES (%s, %s, %s, %s, %s, %s)
							"""
							self.execute_many(insert_sql, insert_data)
							logger.info(f"Inserted {len(insert_data)} POIs into poi_categories")
							
		except Exception as e:
			logger.error(f"Failed to ensure POI categories exist: {e}", exc_info=True)

	def get_agent_poi_knowledge(
		self,
		sim_id: str,
		agent_id: str,
		limit: Optional[int] = None,
	) -> List[Dict[str, Any]]:
		"""Fetch POI knowledge rows for an agent with computed metrics for better UI display."""
		home_query = f"""
			SELECT latitude, longitude
			FROM {self._format_table('agent_locations')}
			WHERE simulation_id = %s
			  AND agent_id = %s
			ORDER BY simulation_timestamp ASC
			LIMIT 1
		"""
		home_res = self.execute_query(home_query, (sim_id, agent_id), fetch=True)
		if not home_res.success or not home_res.data:
			return []

		home_lat = float(home_res.data[0]["latitude"])
		home_lon = float(home_res.data[0]["longitude"])
		local_poi_count = self._count_local_pois(home_lat, home_lon, radius_km=1.5)

		# Query from poi_categories table with name
		query = f"""
			SELECT 
				ps.*,
				pc.name,
				pc.category_name,
				pc.subcategory_name,
				pc.lat,
				pc.lon,
				DATEDIFF(NOW(), ps.last_time_seen) AS recency_days,
				DATEDIFF(ps.last_time_seen, ps.first_time_seen) AS days_known
			FROM {self._format_table('poi_seen')} ps
			JOIN {self._format_table('poi_categories')} pc ON pc.osm_id = ps.osm_id
			WHERE ps.simulation_id = %s
			  AND ps.agent_id = %s
			ORDER BY ps.last_time_seen DESC
		"""
		if limit:
			query += " LIMIT %s"
			params: Tuple[Any, ...] = (sim_id, agent_id, limit)
		else:
			params = (sim_id, agent_id)

		result = self.execute_query(query, params, fetch=True)
		if not result.success or not result.data:
			return []

		now = datetime.utcnow()
		rows = []
		for row in result.data:
			mutable = dict(row)
			mutable["local_poi_count"] = local_poi_count
			
			# Compute derived metrics for better UI sorting/filtering
			times_seen = int(mutable.get("times_seen") or 0)
			times_visited = int(mutable.get("number_of_times_visited") or 0)
			days_known = int(mutable.get("days_known") or 1)
			recency_days = int(mutable.get("recency_days") or 0)
			
			# Familiarity score (0-100): weighted combination of seen + visited
			# More weight on visits since they indicate actual engagement
			familiarity_score = min(100, (times_seen * 2) + (times_visited * 10))
			mutable["familiarity_score"] = familiarity_score
			
			# Visit frequency: visits per month (if known > 30 days)
			if days_known >= 30:
				visit_frequency = (times_visited / days_known) * 30  # visits per month
			else:
				visit_frequency = times_visited  # Just raw count for new places
			mutable["visit_frequency"] = round(visit_frequency, 2)
			
			# Engagement level: categorical indicator
			if times_visited >= 5:
				engagement_level = "high"
			elif times_visited >= 1:
				engagement_level = "medium"
			else:
				engagement_level = "low"
			mutable["engagement_level"] = engagement_level
			
			# Category display name: human-friendly version
			category = mutable.get("category_name", "")
			subcategory = mutable.get("subcategory_name", "")
			category_display = self._humanize_category(category, subcategory)
			mutable["category_display_name"] = category_display
			
			# Display name: use name if available, fallback to category
			display_name = mutable.get("name") or category_display or "Unknown Place"
			mutable["display_name"] = display_name
			
			rows.append(mutable)

		return enrich_with_knowledge_strength(rows, now)

	def get_agent_home_location(self, sim_id: str, agent_id: str) -> Optional[Dict[str, float]]:
		"""Return the earliest known home coordinate for an agent within a simulation."""
		query = f"""
			SELECT latitude, longitude
			FROM {self._format_table('agent_locations')}
			WHERE simulation_id = %s
			  AND agent_id = %s
			ORDER BY simulation_timestamp ASC
			LIMIT 1
		"""
		res = self.execute_query(query, (sim_id, agent_id), fetch=True)
		if not res.success or not res.data:
			return None
		row = res.data[0]
		try:
			return {"lat": float(row["latitude"]), "lon": float(row["longitude"])}
		except Exception:
			return None

	def upsert_agent_poi_seen(
		self,
		sim_id: str,
		agent_id: str,
		osm_id: int,
		distance_km: float,
		seen_increment: int = 1,
		visited: bool = False,
		source: str = "need",
		event_time: Optional[datetime] = None,
	) -> None:
		"""
		Insert or update poi_seen records when an agent discovers or visits a place.
		"""
		seen_increment = max(1, int(seen_increment))
		visit_increment = 1 if visited else 0
		timestamp = event_time or datetime.utcnow()

		try:
			self._ensure_poi_categories_exist([osm_id])
		except Exception:
			pass

		insert_sql = f"""
			INSERT INTO {self._format_table('poi_seen')}
			(
				simulation_id,
				agent_id,
				osm_id,
				distance_km_from_home,
				times_seen,
				first_time_seen,
				last_time_seen,
				number_of_times_visited,
				last_time_visited,
				first_time_visited,
				loaded_at_start_of_simulation,
				source
			)
			VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
			ON DUPLICATE KEY UPDATE
				distance_km_from_home = LEAST(distance_km_from_home, VALUES(distance_km_from_home)),
				times_seen = times_seen + VALUES(times_seen),
				last_time_seen = GREATEST(last_time_seen, VALUES(last_time_seen)),
				number_of_times_visited = number_of_times_visited + VALUES(number_of_times_visited),
				last_time_visited = CASE
					WHEN VALUES(number_of_times_visited) > 0 THEN VALUES(last_time_visited)
					ELSE last_time_visited
				END,
				source = CASE
					WHEN source IN ('init', 'system') THEN source
					ELSE VALUES(source)
				END
		"""

		params = (
			sim_id,
			agent_id,
			int(osm_id),
			float(distance_km),
			seen_increment,
			timestamp,
			timestamp,
			visit_increment,
			timestamp,
			timestamp,
			False,
			source,
		)
		self.execute_query(insert_sql, params, fetch=False)
	
	def _humanize_category(self, category: str, subcategory: str) -> str:
		"""Convert OSM category/subcategory to human-friendly display name."""
		# Map common subcategories to friendly names
		friendly_names = {
			"restaurant": "Restaurant",
			"fast_food": "Fast Food",
			"cafe": "Café",
			"pub": "Pub",
			"bar": "Bar",
			"bank": "Bank",
			"atm": "ATM",
			"pharmacy": "Pharmacy",
			"hospital": "Hospital",
			"clinic": "Clinic",
			"doctors": "Doctor's Office",
			"dentist": "Dentist",
			"fuel": "Gas Station",
			"gas_station": "Gas Station",
			"parking": "Parking",
			"supermarket": "Supermarket",
			"grocery": "Grocery Store",
			"convenience": "Convenience Store",
			"school": "School",
			"university": "University",
			"college": "College",
			"library": "Library",
			"post_office": "Post Office",
			"police": "Police Station",
			"fire_station": "Fire Station",
			"townhall": "Town Hall",
			"place_of_worship": "Place of Worship",
			"park": "Park",
			"playground": "Playground",
			"sports_centre": "Sports Center",
			"gym": "Gym",
			"cinema": "Cinema",
			"theatre": "Theatre",
			"museum": "Museum",
			"artwork": "Artwork",
			"viewpoint": "Viewpoint",
			"picnic_site": "Picnic Site",
			"bench": "Bench",
			"toilets": "Restroom",
			"information": "Information",
			"neighbourhood": "Neighborhood",
			"village": "Village",
			"hamlet": "Hamlet",
			"locality": "Locality",
		}
		
		# Try subcategory first
		if subcategory and subcategory in friendly_names:
			return friendly_names[subcategory]
		
		# Fallback to title-cased subcategory
		if subcategory:
			return subcategory.replace('_', ' ').title()
		
		# Last resort: title-cased category
		return category.replace('_', ' ').title() if category else "Unknown"

	def _count_local_pois(self, lat: float, lon: float, radius_km: float) -> int:
		"""Count POIs near a coordinate using a bounding box approximation from poi_categories."""
		lat_pad = radius_km / 111.0
		lon_pad = radius_km / max(0.0001, 111.0 * math.cos(math.radians(lat)))

		query = f"""
			SELECT COUNT(*) AS cnt
			FROM {self._format_table('poi_categories')}
			WHERE lat BETWEEN %s AND %s
			  AND lon BETWEEN %s AND %s
		"""
		res = self.execute_query(
			query,
			(lat - lat_pad, lat + lat_pad, lon - lon_pad, lon + lon_pad),
			fetch=True,
		)
		if res.success and res.data:
			return int(res.data[0].get("cnt") or 0)
		return 0
	
	# -------------------------------------------------------------------------
	# Action and Transaction Logging
	# -------------------------------------------------------------------------
	
	def log_action(self, simulation_id: str, agent_id: str, action_name: str,
				action_params: Optional[Dict[str, Any]] = None,
				events_generated: Optional[List[Dict[str, Any]]] = None,
				journal_entries: Optional[List[Dict[str, Any]]] = None,
				execution_time_ms: Optional[int] = None,
				status: str = "success") -> bool:
		"""
		Log an action to the action ledger.
		
		Args:
			simulation_id: Simulation ID
			agent_id: Agent ID
			action_name: Name of the action
			action_params: Action parameters
			events_generated: Events generated by the action
			journal_entries: Journal entries
			execution_time_ms: Execution time in milliseconds
			status: Action status
			
		Returns:
			True if successful
		"""
		# Get simulation time instead of real time
		try:
			from Environment.simulation_time_manager import get_simulation_time_manager
			time_manager = get_simulation_time_manager(simulation_id)
			sim_time = time_manager.get_current_datetime()
		except Exception:
			sim_time = datetime.now()
		
		query = f"""
			INSERT INTO {self._format_table('action_ledger')}
			(simulation_id, agent_id, action_name, action_params, events_generated,
			journal_entries, execution_time_ms, status, timestamp)
			VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
		"""
		
		params = (
			simulation_id, agent_id, action_name,
			json.dumps(action_params) if action_params else None,
			json.dumps(events_generated) if events_generated else None,
			json.dumps(journal_entries) if journal_entries else None,
			execution_time_ms or 0, status, sim_time
		)
		
		result = self.execute_query(query, params, fetch=False)
		return result.success
	
	def log_transaction(self, simulation_id: str, transaction_type: str,
					from_entity: str, to_entity: str, amount: float,
					**kwargs) -> bool:
		"""
		Log a transaction.
		
		Args:
			simulation_id: Simulation ID
			transaction_type: Type of transaction
			from_entity: Source entity
			to_entity: Destination entity
			amount: Transaction amount
			**kwargs: Additional transaction fields
			
		Returns:
			True if successful
		"""
		# Get simulation time
		try:
			from Environment.simulation_time_manager import get_simulation_time_manager
			time_manager = get_simulation_time_manager(simulation_id)
			sim_time = time_manager.get_current_datetime()
		except Exception:
			sim_time = datetime.now()
		
		query = f"""
			INSERT INTO {self._format_table('transactions')}
			(simulation_id, transaction_type, from_entity, to_entity, amount,
			item_type, item_quantity, event_type, total_amount, sku, quantity,
			created_at, source_timestamp)
			VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
		"""
		
		params = (
			simulation_id, transaction_type, from_entity, to_entity, amount,
			kwargs.get('item_type'), kwargs.get('item_quantity'),
			kwargs.get('event_type'), kwargs.get('total_amount'),
			kwargs.get('sku'), kwargs.get('quantity'),
			sim_time, sim_time
		)
		
		result = self.execute_query(query, params, fetch=False)
		return result.success
	
	# -------------------------------------------------------------------------
	# Route and Location Timeline Management
	# -------------------------------------------------------------------------
	
	def insert_agent_route(self, simulation_id: str, agent_id: str, 
							route_start_time: datetime, route_end_time: datetime,
							origin_lat: float, origin_lon: float,
							destination_lat: float, destination_lon: float,
							mode: str, distance_km: float, duration_minutes: float,
							provider: str = "valhalla",
							origin_place_id: Optional[str] = None,
							destination_place_id: Optional[str] = None,
							route_polyline: Optional[str] = None,
							route_coordinates: Optional[List[List[float]]] = None,
							action_ledger_id: Optional[int] = None,
							planner_metadata: Optional[Dict[str, Any]] = None) -> Optional[int]:
		"""
		Insert a new agent route with full geometry.
		
		Args:
			simulation_id: Simulation ID
			agent_id: Agent ID
			route_start_time: When the route starts (simulation time)
			route_end_time: When the route completes (simulation time)
			origin_lat, origin_lon: Starting coordinates
			destination_lat, destination_lon: Ending coordinates
			mode: Travel mode (pedestrian, bicycle, auto, transit)
			distance_km: Route distance
			duration_minutes: Route duration
			provider: Routing provider (valhalla, haversine, etc.)
			origin_place_id: OSM ID or symbolic location of origin
			destination_place_id: OSM ID or symbolic location of destination
			route_polyline: Encoded polyline string
			route_coordinates: Array of [lat, lon] pairs
			action_ledger_id: Link to action_ledger entry
			planner_metadata: Spatial planner decision context
			
		Returns:
			route_id if successful, None otherwise
		"""
		query = f"""
			INSERT INTO {self._format_table('agent_routes')}
			(simulation_id, agent_id, route_start_time, route_end_time,
			origin_lat, origin_lon, destination_lat, destination_lon,
			origin_place_id, destination_place_id, mode, distance_km, duration_minutes,
			provider, route_polyline, route_coordinates, action_ledger_id, planner_metadata)
			VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
		"""
		
		params = (
			simulation_id, agent_id, route_start_time, route_end_time,
			origin_lat, origin_lon, destination_lat, destination_lon,
			origin_place_id, destination_place_id, mode, distance_km, duration_minutes,
			provider, route_polyline,
			json.dumps(route_coordinates) if route_coordinates else None,
			action_ledger_id,
			json.dumps(planner_metadata) if planner_metadata else None
		)
		
		result = self.execute_query(query, params, fetch=False)
		if result.success:
			# Get the inserted route_id
			id_query = "SELECT LAST_INSERT_ID() as route_id"
			id_result = self.execute_query(id_query, fetch=True)
			if id_result.success and id_result.data:
				return int(id_result.data[0]['route_id'])
		return None
	
	def insert_location_timeline_batch(self, rows: List[Tuple]) -> bool:
		"""
		Batch insert agent location timeline entries.
		
		Args:
			rows: List of tuples (simulation_id, agent_id, timeline_timestamp, latitude, longitude,
						is_traveling, current_route_id, location_type, current_place_id)
		
		Returns:
			True if successful
		"""
		if not rows:
			return True
		
		query = f"""
			INSERT INTO {self._format_table('agent_location_timeline')}
			(simulation_id, agent_id, timeline_timestamp, latitude, longitude,
			is_traveling, current_route_id, location_type, current_place_id)
			VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
			ON DUPLICATE KEY UPDATE
			latitude = VALUES(latitude),
			longitude = VALUES(longitude),
			is_traveling = VALUES(is_traveling),
			current_route_id = VALUES(current_route_id),
			location_type = VALUES(location_type),
			current_place_id = VALUES(current_place_id)
		"""
		
		result = self.execute_many(query, rows)
		return result.success
	
	def get_agent_routes(self, simulation_id: str, agent_id: Optional[str] = None,
						start_time: Optional[datetime] = None, end_time: Optional[datetime] = None,
						mode: Optional[str] = None) -> List[Dict[str, Any]]:
		"""
		Get agent routes with optional filtering.
		
		Args:
			simulation_id: Simulation ID
			agent_id: Optional agent ID filter
			start_time: Optional start time filter
			end_time: Optional end time filter
			mode: Optional mode filter
			
		Returns:
			List of route dictionaries
		"""
		conditions = [f"simulation_id = %s"]
		params = [simulation_id]
		
		if agent_id:
			conditions.append("agent_id = %s")
			params.append(agent_id)
		
		if start_time:
			conditions.append("route_start_time >= %s")
			params.append(start_time)
		
		if end_time:
			conditions.append("route_end_time <= %s")
			params.append(end_time)
		
		if mode:
			conditions.append("mode = %s")
			params.append(mode)
		
		where_clause = " AND ".join(conditions)
		
		query = f"""
			SELECT * FROM {self._format_table('agent_routes')}
			WHERE {where_clause}
			ORDER BY route_start_time ASC
		"""
		
		result = self.execute_query(query, tuple(params), fetch=True)
		if result.success and result.data:
			# Parse JSON fields
			for row in result.data:
				if row.get('route_coordinates') and isinstance(row['route_coordinates'], str):
					try:
						row['route_coordinates'] = json.loads(row['route_coordinates'])
					except:
						pass
				if row.get('planner_metadata') and isinstance(row['planner_metadata'], str):
					try:
						row['planner_metadata'] = json.loads(row['planner_metadata'])
					except:
						pass
			return result.data
		return []
	
	def get_agent_position_at_time(self, simulation_id: str, agent_id: str, timestamp: datetime) -> Optional[Dict[str, Any]]:
		"""
		Get agent position at a specific timestamp, interpolating from timeline if needed.
		
		Args:
			simulation_id: Simulation ID
			agent_id: Agent ID
			timestamp: Query timestamp
			
		Returns:
			Dictionary with {lat, lon, is_traveling, route_id, place_id, location_type} or None
		"""
		# Try exact match first
		query = f"""
			SELECT * FROM {self._format_table('agent_location_timeline')}
			WHERE simulation_id = %s AND agent_id = %s AND timeline_timestamp = %s
			LIMIT 1
		"""
		
		result = self.execute_query(query, (simulation_id, agent_id, timestamp), fetch=True)
		if result.success and result.data:
			return result.data[0]
		
		# Fall back to nearest before timestamp
		query = f"""
			SELECT * FROM {self._format_table('agent_location_timeline')}
			WHERE simulation_id = %s AND agent_id = %s AND timeline_timestamp <= %s
			ORDER BY timeline_timestamp DESC
			LIMIT 1
		"""
		
		result = self.execute_query(query, (simulation_id, agent_id, timestamp), fetch=True)
		if result.success and result.data:
			return result.data[0]
		
		return None
	
	def insert_action_context(self, simulation_id: str, agent_id: str, action_ledger_id: int,
								action_timestamp: datetime, day_offset: int, action_name: str,
								action_summary: Optional[str] = None,
								location_before: Optional[Dict[str, Any]] = None,
								location_after: Optional[Dict[str, Any]] = None,
								route_taken_id: Optional[int] = None,
								counterparties: Optional[List[str]] = None,
								items_exchanged: Optional[Dict[str, Any]] = None,
								success: bool = True,
								outcome_description: Optional[str] = None,
								events_generated: Optional[List[Dict[str, Any]]] = None) -> Optional[int]:
		"""
		Insert rich action context for LLM queries and replay.
		
		Args:
			simulation_id: Simulation ID
			agent_id: Agent ID
			action_ledger_id: Foreign key to action_ledger
			action_timestamp: When the action occurred
			day_offset: Days from simulation start
			action_name: Action type
			action_summary: Human-readable summary
			location_before: {lat, lon, place_id, place_name}
			location_after: {lat, lon, place_id, place_name}
			route_taken_id: Foreign key to agent_routes if travel
			counterparties: List of agent/firm IDs
			items_exchanged: Goods/services/money exchanged
			success: Whether action succeeded
			outcome_description: Text description of outcome
			events_generated: Key events from this action
			
		Returns:
			context_id if successful, None otherwise
		"""
		query = f"""
			INSERT INTO {self._format_table('agent_action_context')}
			(simulation_id, agent_id, action_ledger_id, action_timestamp, day_offset,
			action_name, action_summary, location_before, location_after, route_taken_id,
			counterparties, items_exchanged, success, outcome_description, events_generated)
			VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
		"""
		
		params = (
			simulation_id, agent_id, action_ledger_id, action_timestamp, day_offset,
			action_name, action_summary,
			json.dumps(location_before) if location_before else None,
			json.dumps(location_after) if location_after else None,
			route_taken_id,
			json.dumps(counterparties) if counterparties else None,
			json.dumps(items_exchanged) if items_exchanged else None,
			success, outcome_description,
			json.dumps(events_generated) if events_generated else None
		)
		
		result = self.execute_query(query, params, fetch=False)
		if result.success:
			id_query = "SELECT LAST_INSERT_ID() as context_id"
			id_result = self.execute_query(id_query, fetch=True)
			if id_result.success and id_result.data:
				return int(id_result.data[0]['context_id'])
		return None
	
	def get_agent_action_history(self, simulation_id: str, agent_id: str,
									limit: int = 50, day_offset: Optional[int] = None,
									action_type: Optional[str] = None,
									success_only: bool = False) -> List[Dict[str, Any]]:
		"""
		Get agent action history with rich context for LLM queries.
		
		Args:
			simulation_id: Simulation ID
			agent_id: Agent ID
			limit: Maximum number of actions to return
			day_offset: Filter by specific day
			action_type: Filter by action name
			success_only: Only return successful actions
			
		Returns:
			List of action context dictionaries
		"""
		conditions = [f"simulation_id = %s", "agent_id = %s"]
		params = [simulation_id, agent_id]
		
		if day_offset is not None:
			conditions.append("day_offset = %s")
			params.append(day_offset)
		
		if action_type:
			conditions.append("action_name = %s")
			params.append(action_type)
		
		if success_only:
			conditions.append("success = TRUE")
		
		where_clause = " AND ".join(conditions)
		
		query = f"""
			SELECT * FROM {self._format_table('agent_action_context')}
			WHERE {where_clause}
			ORDER BY action_timestamp DESC
			LIMIT %s
		"""
		
		params.append(limit)
		result = self.execute_query(query, tuple(params), fetch=True)
		
		if result.success and result.data:
			# Parse JSON fields
			for row in result.data:
				for json_field in ['location_before', 'location_after', 'counterparties', 'items_exchanged', 'events_generated']:
					if row.get(json_field) and isinstance(row[json_field], str):
						try:
							row[json_field] = json.loads(row[json_field])
						except:
							pass
			return result.data
		return []
	
	# -------------------------------------------------------------------------
	# Query and Metrics
	# -------------------------------------------------------------------------
	
	def get_simulation_actions(self, simulation_id: str,
							agent_id: Optional[str] = None,
							limit: int = 1000) -> List[Dict[str, Any]]:
		"""Get actions for a simulation."""
		if agent_id:
			query = f"""
				SELECT * FROM {self._format_table('action_ledger')}
				WHERE simulation_id = %s AND agent_id = %s
				ORDER BY timestamp DESC LIMIT %s
			"""
			params = (simulation_id, agent_id, limit)
		else:
			query = f"""
				SELECT * FROM {self._format_table('action_ledger')}
				WHERE simulation_id = %s
				ORDER BY timestamp DESC LIMIT %s
			"""
			params = (simulation_id, limit)
		
		result = self.execute_query(query, params, fetch=True)
		
		if result.success:
			actions = result.data
			# Parse JSON fields
			for action in actions:
				for json_field in ['action_params', 'events_generated', 'journal_entries']:
					if action.get(json_field):
						try:
							action[json_field] = json.loads(action[json_field])
						except (json.JSONDecodeError, TypeError):
							pass
			return actions
		
		return []
	
	def get_simulation_transactions(self, simulation_id: str,
								entity_id: Optional[str] = None,
								limit: int = 1000) -> List[Dict[str, Any]]:
		"""Get transactions for a simulation."""
		if entity_id:
			query = f"""
				SELECT * FROM {self._format_table('transactions')}
				WHERE simulation_id = %s AND (from_entity = %s OR to_entity = %s)
				ORDER BY created_at DESC LIMIT %s
			"""
			params = (simulation_id, entity_id, entity_id, limit)
		else:
			query = f"""
				SELECT * FROM {self._format_table('transactions')}
				WHERE simulation_id = %s
				ORDER BY created_at DESC LIMIT %s
			"""
			params = (simulation_id, limit)
		
		result = self.execute_query(query, params, fetch=True)
		
		if result.success:
			return result.data
		
		return []
	
	def get_simulation_metrics(self, simulation_id: str) -> Dict[str, Any]:
		"""Get performance metrics for a simulation."""
		# Get action metrics
		action_query = f"""
			SELECT 
				COUNT(*) as total_actions,
				COUNT(DISTINCT agent_id) as unique_agents,
				AVG(execution_time_ms) as avg_execution_time,
				MIN(timestamp) as first_action,
				MAX(timestamp) as last_action
			FROM {self._format_table('action_ledger')}
			WHERE simulation_id = %s
		"""
		
		action_result = self.execute_query(action_query, (simulation_id,), fetch=True)
		
		# Get transaction metrics
		transaction_query = f"""
			SELECT 
				COUNT(*) as total_transactions,
				SUM(amount) as total_amount,
				COUNT(DISTINCT from_entity) as unique_senders,
				COUNT(DISTINCT to_entity) as unique_receivers
			FROM {self._format_table('transactions')}
			WHERE simulation_id = %s
		"""
		
		transaction_result = self.execute_query(transaction_query, (simulation_id,), fetch=True)
		
		metrics = {
			'simulation_id': simulation_id,
			'actions': action_result.data[0] if action_result.success and action_result.data else {},
			'transactions': transaction_result.data[0] if transaction_result.success and transaction_result.data else {}
		}
		
		return metrics
	
	def reset_simulations(self) -> bool:
		"""
		Delete all rows from the simulations table.
		
		WARNING: This will permanently delete all simulation records.
		
		Returns:
			True if successful, False otherwise
		"""
		delete_query = f"DELETE FROM {self._format_table('simulations')}"
		result = self.execute_query(delete_query, fetch=False)
		
		if result.success:
			logger.info("Successfully deleted all rows from simulations table")
			return True
		else:
			logger.error(f"Failed to delete simulations: {result.error}")
			return False
	
	# -------------------------------------------------------------------------
	# Household Balance Sheet Queries
	# -------------------------------------------------------------------------
	
	def get_household_balance_sheet(self, simulation_id: str, household_id: str) -> Optional[Dict[str, Any]]:
		"""
		Get household balance sheet for a specific simulation and household.
		
		Args:
			simulation_id: Simulation identifier
			household_id: Household identifier
			
		Returns:
			Balance sheet dictionary or None
		"""
		query = f"""
			SELECT *
			FROM {self._format_table('household_balance_sheet_samples')}
			WHERE simulation_id = %s AND household_id = %s
			ORDER BY sim_clock_datetime DESC
			LIMIT 1
		"""
		
		result = self.execute_query(query, (simulation_id, household_id), fetch=True)
		
		if result.success and result.data:
			return result.data[0]
		
		return None
	
	def get_agents_list_with_details(self, simulation_id: str, limit: int = 250, offset: int = 0) -> List[Dict[str, Any]]:
		"""
		Get list of all agents in a simulation with basic information for display in a list view.
		
		Uses agent_locations as the source of truth for which agents are in a simulation,
		since that's where agents are actually stored during simulation runs.
		
		Args:
			simulation_id: Simulation identifier
			
		Returns:
			List of agent dictionaries with name, age, location, net worth, etc.
		"""
		# Sanitize paging inputs
		try:
			limit = int(limit)
			offset = int(offset)
		except Exception:
			limit, offset = 250, 0
		limit = max(1, min(limit, 1000))
		offset = max(0, offset)
		logger.info(f"[AGENTS_LIST] Starting get_agents_list_with_details for simulation: {simulation_id} (limit={limit}, offset={offset})")
		
		# Step 1: Check how many distinct agents exist in agent_locations
		count_query = f"""
			SELECT COUNT(DISTINCT agent_id) as count
			FROM {self._format_table('agent_locations')}
			WHERE simulation_id = %s
		"""
		count_result = self.execute_query(count_query, (simulation_id,), fetch=True)
		if count_result.success and count_result.data:
			agent_count = count_result.data[0].get('count', 0)
			logger.info(f"[AGENTS_LIST] Found {agent_count} distinct agents in agent_locations table")
			if agent_count == 0:
				logger.warning(f"[AGENTS_LIST] No agents found in agent_locations for simulation {simulation_id}")
				return []
		else:
			logger.error(f"[AGENTS_LIST] Failed to count agents: {count_result.error}")
			return []
		
		# Step 2: Get a sample of agent IDs to verify they exist
		sample_query = f"""
			SELECT DISTINCT agent_id
			FROM {self._format_table('agent_locations')}
			WHERE simulation_id = %s
			LIMIT 3
		"""
		sample_result = self.execute_query(sample_query, (simulation_id,), fetch=True)
		if sample_result.success and sample_result.data:
			sample_ids = [row['agent_id'] for row in sample_result.data]
			logger.info(f"[AGENTS_LIST] Sample agent IDs: {sample_ids}")
		
		# Step 3: Run the full query
		query = f"""
			SELECT 
				al.agent_id,
				a.name as agent_name,
				l2c.Voters_FirstName,
				l2c.Voters_MiddleName,
				l2c.Voters_LastName,
				l2c.Voters_Age,
				l2c.Voters_Gender,
				l2loc.Residence_Addresses_City,
				l2loc.Residence_Addresses_State,
				l2p1.Parties_Description,
				p3.ConsumerData_Household_Net_Worth,
				o1.ConsumerData_Number_Of_Persons_in_HH,
				o3.ConsumerData_Home_Est_Current_Value_Code as home_value
			FROM (
				SELECT DISTINCT agent_id 
				FROM {self._format_table('agent_locations')}
				WHERE simulation_id = %s
			) al
			LEFT JOIN {self._agents_db}.agents a ON al.agent_id = a.l2_voter_id
			LEFT JOIN {self._agents_db}.l2_agent_core l2c ON l2c.LALVOTERID = al.agent_id
			LEFT JOIN {self._agents_db}.l2_location l2loc ON l2loc.LALVOTERID = al.agent_id
			LEFT JOIN {self._agents_db}.l2_political_part_1 l2p1 ON l2p1.LALVOTERID = al.agent_id
			LEFT JOIN {self._agents_db}.l2_political_part_3 p3 ON p3.LALVOTERID = al.agent_id
			LEFT JOIN {self._agents_db}.l2_other_part_1 o1 ON o1.LALVOTERID = al.agent_id
			LEFT JOIN {self._agents_db}.l2_other_part_3 o3 ON o3.LALVOTERID = al.agent_id
			ORDER BY l2c.Voters_LastName, l2c.Voters_FirstName
			LIMIT {limit} OFFSET {offset}
		"""
		
		logger.info(f"[AGENTS_LIST] Executing main query...")
		result = self.execute_query(query, (simulation_id,), fetch=True)
		
		agents: List[Dict[str, Any]] = []
		if result.success:
			row_count = len(result.data) if result.data else 0
			logger.info(f"[AGENTS_LIST] Query returned {row_count} rows")
			
			if row_count == 0:
				logger.warning(f"[AGENTS_LIST] Query succeeded but returned 0 rows - possible JOIN issue")
				# Try a simpler query without JOINs to diagnose
				simple_query = f"""
					SELECT DISTINCT agent_id 
					FROM {self._format_table('agent_locations')}
					WHERE simulation_id = %s
					LIMIT 5
				"""
				simple_result = self.execute_query(simple_query, (simulation_id,), fetch=True)
				if simple_result.success and simple_result.data:
					logger.info(f"[AGENTS_LIST] Simple query returned {len(simple_result.data)} agent IDs: {[r['agent_id'] for r in simple_result.data]}")
				return []
			
			for idx, row in enumerate(result.data):
				# Compute display name
				name = row.get('agent_name')
				if not name:
					name_parts = [
						row.get('Voters_FirstName'),
						row.get('Voters_MiddleName'),
						row.get('Voters_LastName')
					]
					name = ' '.join([p for p in name_parts if p and str(p).strip()])
				
				agent = {
					'agent_id': row['agent_id'],
					'name': name if name else None,
					'age': row.get('Voters_Age'),
					'gender': row.get('Voters_Gender'),
					'city': row.get('Residence_Addresses_City'),
					'state': row.get('Residence_Addresses_State'),
					'party': row.get('Parties_Description'),
					'net_worth': row.get('ConsumerData_Household_Net_Worth'),
					'household_size': row.get('ConsumerData_Number_Of_Persons_in_HH'),
					'home_value': row.get('home_value'),
				}
				agents.append(agent)
				
				if idx < 2:  # Log first 2 agents for debugging
					logger.info(f"[AGENTS_LIST] Agent {idx+1}: ID={agent['agent_id']}, Name={agent['name']}, City={agent['city']}")
		else:
			logger.error(f"[AGENTS_LIST] Query failed for simulation {simulation_id}: {result.error}")
			return []
		
		logger.info(f"[AGENTS_LIST] Returning {len(agents)} agents")
		return agents

	def get_agents_count(self, simulation_id: str) -> int:
		"""Return total distinct agents in a simulation (agent_locations as source of truth)."""
		query = f"""
			SELECT COUNT(DISTINCT agent_id) AS cnt
			FROM {self._format_table('agent_locations')}
			WHERE simulation_id = %s
		"""
		res = self.execute_query(query, (simulation_id,), fetch=True)
		if res.success and res.data:
			try:
				return int(res.data[0].get('cnt') or 0)
			except Exception:
				return 0
		return 0
	
	def get_household_members(self, simulation_id: str, household_id: str) -> List[Dict[str, Any]]:
		"""
		Get all agents (household members) for a specific household.
		
		Args:
			simulation_id: Simulation identifier
			household_id: Household identifier
			
		Returns:
			List of agent dictionaries with computed names
		"""
		query = f"""
			SELECT 
				ia.agent_id,
				a.name as agent_name,
				l2c.Voters_FirstName,
				l2c.Voters_MiddleName,
				l2c.Voters_LastName,
				l2c.Voters_Age,
				l2c.Voters_Gender,
				a.created_at
			FROM {self._format_table('initialized_agents')} ia
			LEFT JOIN {self._agents_db}.agents a ON ia.agent_id = a.l2_voter_id
			LEFT JOIN {self._agents_db}.l2_agent_core l2c ON l2c.LALVOTERID = ia.agent_id
			LEFT JOIN {self._agents_db}.l2_other_part_1 o1 ON o1.LALVOTERID = ia.agent_id
			WHERE ia.simulation_id = %s 
			  AND (o1.Residence_Families_FamilyID = %s OR o1.Mailing_Families_FamilyID = %s)
		"""
		
		result = self.execute_query(query, (simulation_id, household_id, household_id), fetch=True)
		
		members: List[Dict[str, Any]] = []
		if result.success:
			# Compute display name and enrich with basic fields
			for member in result.data:
				name = member.get('agent_name')
				if not name:
					name_parts = [
						member.get('Voters_FirstName'),
						member.get('Voters_MiddleName'),
						member.get('Voters_LastName')
					]
					name = ' '.join([p for p in name_parts if p and str(p).strip()])
				members.append({
					'agent_id': member['agent_id'],
					'name': name if name else None,
					'age': member.get('Voters_Age'),
					'gender': member.get('Voters_Gender'),
					'created_at': member.get('created_at')
				})
		
		# Determine expected household size from L2 data (max across the household)
		expected_count = None
		try:
			expected_query = f"""
				SELECT 
					MAX(o1.ConsumerData_Number_Of_Persons_in_HH) AS hh_size,
					MAX(o1.ConsumerData_Number_Of_Adults_in_HH) AS adults,
					MAX(o1.ConsumerData_Number_Of_Children_in_HH) AS children
				FROM {self._agents_db}.l2_other_part_1 o1
				WHERE (o1.Residence_Families_FamilyID = %s OR o1.Mailing_Families_FamilyID = %s)
			"""
			exp_res = self.execute_query(expected_query, (household_id, household_id), fetch=True)
			if exp_res.success and exp_res.data:
				row = exp_res.data[0]
				try:
					hh_size_val = row.get('hh_size')
					expected_count = int(hh_size_val) if hh_size_val is not None else None
				except Exception:
					expected_count = None
		except Exception as e:
			logger.debug(f"Failed to resolve expected household size for {household_id}: {e}")

		# Add anonymous placeholders if L2 reports more people than initialized agents
		if expected_count and expected_count > len(members):
			missing = expected_count - len(members)
			for idx in range(missing):
				members.append({
					'agent_id': f"ANON-{household_id}-{idx+1}",
					'name': 'Unknown Agent',
					'age': None,
					'gender': None,
					'created_at': None,
					'is_placeholder': True
				})
		
		return members


# Singleton accessor
def get_simulations_manager() -> SimulationsDatabaseManager:
	"""Get the singleton instance of SimulationsDatabaseManager."""
	return SimulationsDatabaseManager.get_singleton()
