#!/usr/bin/env python3
"""
Bulk L2 Data Loader for World_Sim

Optimized loader that fetches L2 data for multiple agents with a few bulk queries
instead of individual queries per agent. Dramatically reduces database load.

Performance:
- Old: N agents × 9 queries = 9N queries
- New: 9 bulk queries total (regardless of N)
"""

from __future__ import annotations
import os
import time
from typing import Dict, List, Any, Optional
from Database.database_manager import execute_query as dm_execute_query

_agents_db = os.getenv('DB_AGENTS_NAME', 'world_sim_agents')

def execute_agents_query(query: str, params=None, fetch: bool = True):
    """Compatibility wrapper that returns list[dict] when fetch=True."""
    result = dm_execute_query(query, params, database=_agents_db, fetch=fetch)
    if fetch:
        if hasattr(result, 'success') and hasattr(result, 'data'):
            return result.data if result.success else []
        return result or []
    # fetch == False
    if hasattr(result, 'success'):
        return result.success
    return bool(result)


class BulkL2Loader:
    """Loads L2 data for multiple agents efficiently using bulk queries."""
    
    @staticmethod
    def load_bulk_l2_data(voter_ids: List[str]) -> Dict[str, Dict[str, Any]]:
        """
        Load L2 data for multiple voters with bulk queries.
        
        Args:
            voter_ids: List of LALVOTERID strings
            
        Returns:
            Dictionary mapping voter_id -> complete L2 data dict
        """
        verbosity = int(os.getenv('VERBOSITY', os.getenv('VERBOSITY_LEVEL', '1')))
        t_total = time.perf_counter() if verbosity >= 2 else None
        
        if not voter_ids:
            return {}
        
        # Initialize result dictionary with LALVOTERIDs
        results: Dict[str, Dict[str, Any]] = {vid: {'LALVOTERID': vid} for vid in voter_ids}
        
        # Process in chunks to avoid SQL parameter limits (MySQL has ~65k limit)
        chunk_size = 1000
        
        for i in range(0, len(voter_ids), chunk_size):
            chunk = voter_ids[i:i + chunk_size]
            placeholders = ",".join(["%s"] * len(chunk))
            
            # 1) Load from l2_agent_core
            t0 = time.perf_counter() if verbosity >= 3 else None
            core_query = f"SELECT * FROM l2_agent_core WHERE LALVOTERID IN ({placeholders})"
            try:
                core_data = execute_agents_query(core_query, tuple(chunk), fetch=True)
                for row in core_data:
                    vid = row.get('LALVOTERID')
                    if vid in results:
                        results[vid].update(row)
            except Exception as e:
                print(f"Warning: Could not load l2_agent_core for chunk: {e}")
            if verbosity >= 3:
                print(f"[bulk_l2] l2_agent_core for {len(chunk)} agents: {time.perf_counter() - t0:.3f}s")
            
            # 2) Load from l2_location
            t0 = time.perf_counter() if verbosity >= 3 else None
            location_query = f"SELECT * FROM l2_location WHERE LALVOTERID IN ({placeholders})"
            try:
                location_data = execute_agents_query(location_query, tuple(chunk), fetch=True)
                for row in location_data:
                    vid = row.get('LALVOTERID')
                    if vid in results:
                        results[vid].update(row)
            except Exception as e:
                print(f"Warning: Could not load l2_location for chunk: {e}")
            if verbosity >= 3:
                print(f"[bulk_l2] l2_location for {len(chunk)} agents: {time.perf_counter() - t0:.3f}s")
            
            # 3) Load from l2_political partitions (1, 2, 3)
            t0 = time.perf_counter() if verbosity >= 3 else None
            for part_num in range(1, 4):
                political_query = f"SELECT * FROM l2_political_part_{part_num} WHERE LALVOTERID IN ({placeholders})"
                try:
                    political_data = execute_agents_query(political_query, tuple(chunk), fetch=True)
                    for row in political_data:
                        vid = row.get('LALVOTERID')
                        if vid in results:
                            results[vid].update(row)
                except Exception as e:
                    if verbosity >= 2:
                        print(f"Warning: Could not load l2_political_part_{part_num} for chunk: {e}")
                    break  # No more partitions
            if verbosity >= 3:
                print(f"[bulk_l2] l2_political (3 parts) for {len(chunk)} agents: {time.perf_counter() - t0:.3f}s")
            
            # 4) Load from l2_other partitions (1, 2, 3, 4)
            t0 = time.perf_counter() if verbosity >= 3 else None
            for part_num in range(1, 5):
                other_query = f"SELECT * FROM l2_other_part_{part_num} WHERE LALVOTERID IN ({placeholders})"
                try:
                    other_data = execute_agents_query(other_query, tuple(chunk), fetch=True)
                    for row in other_data:
                        vid = row.get('LALVOTERID')
                        if vid in results:
                            results[vid].update(row)
                except Exception as e:
                    if verbosity >= 2:
                        print(f"Warning: Could not load l2_other_part_{part_num} for chunk: {e}")
                    break  # No more partitions
            if verbosity >= 3:
                print(f"[bulk_l2] l2_other (4 parts) for {len(chunk)} agents: {time.perf_counter() - t0:.3f}s")
            
            # 5) Load from l2_geo
            t0 = time.perf_counter() if verbosity >= 3 else None
            geo_query = f"SELECT * FROM l2_geo WHERE LALVOTERID IN ({placeholders})"
            try:
                geo_data = execute_agents_query(geo_query, tuple(chunk), fetch=True)
                for row in geo_data:
                    vid = row.get('LALVOTERID')
                    if vid in results:
                        results[vid].update(row)
            except Exception as e:
                print(f"Warning: Could not load l2_geo for chunk: {e}")
            if verbosity >= 3:
                print(f"[bulk_l2] l2_geo for {len(chunk)} agents: {time.perf_counter() - t0:.3f}s")
        
        if verbosity >= 2:
            print(f"[bulk_l2] TOTAL bulk L2 load for {len(voter_ids)} agents: {time.perf_counter() - t_total:.3f}s")
        
        # Filter out agents with no data (only have LALVOTERID)
        return {vid: data for vid, data in results.items() if len(data) > 1}


# Convenience function
def load_bulk_l2_data(voter_ids: List[str]) -> Dict[str, Dict[str, Any]]:
    """Load L2 data for multiple voters with bulk queries."""
    return BulkL2Loader.load_bulk_l2_data(voter_ids)

