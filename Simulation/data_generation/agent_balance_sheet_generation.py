#!/usr/bin/env python3
"""
Household Balance Sheet Generation for World_Sim

Generates realistic household balance sheets at simulation start based on L2 voter data
and economic indicators. Creates exactly one balance sheet per household (not per agent).

Modeling unit: household/family
Target table: world_sim_simulations.household_balance_sheet_samples
Idempotent: will not duplicate rows for (simulation_id, household_id, sim_clock_datetime)
"""

from __future__ import annotations

import os
import re
import logging
import hashlib
from typing import Dict, Any, Optional, Tuple, List, Set
from datetime import datetime
from decimal import Decimal
import numpy as np
from scipy import stats

from Utils.calibration import CensusCalibration, STATE_ABBR_TO_FIPS

logger = logging.getLogger(__name__)


_CENSUS_CALIBRATION: Optional[CensusCalibration] = None


def _get_census_calibration() -> CensusCalibration:
    """Lazy-load a shared CensusCalibration instance."""
    global _CENSUS_CALIBRATION
    if _CENSUS_CALIBRATION is None:
        _CENSUS_CALIBRATION = CensusCalibration()
    return _CENSUS_CALIBRATION


# ============================================================================
# Public API
# ============================================================================

def ensure_initial_household_balance_sheet_for_agent(
    simulation_id: str,
    lalvoterid: str,
    rng_seed: Optional[int] = None,
    verbosity: int = 3
) -> None:
    """
    Ensures there is exactly one initial balance sheet row per household at simulation start.
    
    Resolves household_id for this agent, checks if a row exists in
    world_sim_simulations.household_balance_sheet_samples at the simulation start timestamp,
    and if not, samples a realistic household balance sheet (one draw) and inserts it.
    
    This function is idempotent and relies on existing db/session utilities.
    
    Args:
        simulation_id: The simulation ID
        lalvoterid: The L2 voter ID
        rng_seed: Optional RNG seed for reproducibility. If None, uses hash of sim+household
        verbosity: Logging verbosity level (0-3). Only log at level >= 3.
    """
    from Database.managers import get_simulations_manager
    from Database.managers.alternative_data import get_alternative_data_manager
    
    sim_mgr = get_simulations_manager()
    alt_mgr = get_alternative_data_manager()
    
    # resolve household_id for this agent
    household_id = _resolve_household_id(sim_mgr, lalvoterid)
    
    # get simulation start datetime
    sim_info = sim_mgr.get_simulation(simulation_id)
    if not sim_info:
        logger.error(f"Simulation {simulation_id} not found")
        return
    
    start_datetime = sim_info.get('simulation_start_datetime')
    if not start_datetime:
        logger.error(f"No simulation_start_datetime for simulation {simulation_id}")
        return
    
    # check if balance sheet already exists (idempotent)
    if _balance_sheet_exists(sim_mgr, simulation_id, household_id, start_datetime):
        logger.debug(f"Balance sheet already exists for household {household_id} in simulation {simulation_id}")
        return
    
    # use deterministic seed if not provided
    if rng_seed is None:
        rng_seed = _generate_deterministic_seed(simulation_id, household_id)
    
    # sample balance sheet
    balance_sheet = _sample_household_balance_sheet(
        sim_mgr=sim_mgr,
        alt_mgr=alt_mgr,
        simulation_id=simulation_id,
        household_id=household_id,
        lalvoterid=lalvoterid,
        start_datetime=start_datetime,
        rng_seed=rng_seed
    )
    
    # insert balance sheet
    _insert_balance_sheet(sim_mgr, balance_sheet)
    
    # Only log individual balance sheet creation at verbosity >= 3
    if verbosity >= 3:
        logger.info(f"Created initial balance sheet for household {household_id} (sim {simulation_id})")


# ============================================================================
# BATCH MODE: Compute-only Worker and Batch Helpers
# ============================================================================

def generate_balance_sheet_compute_only(
    simulation_id: str,
    household_id: str,
    lalvoterid: str,
    start_datetime: datetime,
    features: Dict[str, Any],
    hpi_index_cache: Dict[Tuple[str, str], Dict[Tuple[int, int], float]],
    calibration_stats: Dict[str, Any],
    rng_seed: Optional[int] = None
) -> Dict[str, Any]:
    """
    Compute-only worker function: generates a balance sheet from pre-resolved inputs.
    
    This function does NO database I/O - all required data is passed as arguments.
    Safe for use in multiprocessing workers without DB connection overhead.
    
    Args:
        simulation_id: Simulation ID
        household_id: Resolved household ID
        lalvoterid: L2 voter ID (for logging/debugging)
        start_datetime: Simulation start datetime
        features: Pre-extracted agent features dict
        hpi_index_cache: Pre-fetched HPI data: {(level, place_id): {(yr, quarter): index}}
        calibration_stats: Pre-fetched census calibration statistics
        rng_seed: Optional RNG seed
        
    Returns:
        Balance sheet dict ready for insertion
    """
    # Use deterministic seed if not provided
    if rng_seed is None:
        rng_seed = _generate_deterministic_seed(simulation_id, household_id)
    
    # Sample balance sheet using pre-resolved features and HPI cache
    bs = _sample_household_balance_sheet_with_cache(
        simulation_id=simulation_id,
        household_id=household_id,
        lalvoterid=lalvoterid,
        start_datetime=start_datetime,
        features=features,
        hpi_index_cache=hpi_index_cache,
        calibration_stats=calibration_stats,
        rng_seed=rng_seed
    )
    
    return bs


def batch_resolve_households(sim_mgr, agent_ids: List[str]) -> Dict[str, str]:
    """
    Resolve household_id for all agents in a single query.
    
    Returns:
        Dict mapping agent_id -> household_id
    """
    if not agent_ids:
        return {}
    
    # Build IN clause with placeholders
    placeholders = ', '.join(['%s'] * len(agent_ids))
    query = f"""
        SELECT 
            LALVOTERID,
            Residence_Families_FamilyID,
            Mailing_Families_FamilyID
        FROM world_sim_agents.l2_other_part_1
        WHERE LALVOTERID IN ({placeholders})
    """
    
    rows = sim_mgr.execute_agents_sql_rows(query, tuple(agent_ids))
    
    household_map = {}
    for row in rows:
        lalvoterid = row.get('LALVOTERID')
        if not lalvoterid:
            continue
        
        # Try residence family first
        res_fam = row.get('Residence_Families_FamilyID')
        if res_fam:
            household_map[str(lalvoterid)] = str(res_fam)
            continue
        
        # Fallback to mailing family
        mail_fam = row.get('Mailing_Families_FamilyID')
        if mail_fam:
            household_map[str(lalvoterid)] = str(mail_fam)
            continue
        
        # Synthetic fallback
        household_map[str(lalvoterid)] = f"SYNTH_{lalvoterid}"
    
    # Add synthetic for any missing agents
    for agent_id in agent_ids:
        if str(agent_id) not in household_map:
            household_map[str(agent_id)] = f"SYNTH_{agent_id}"
    
    return household_map


def batch_check_existing_balance_sheets(
    sim_mgr,
    simulation_id: str,
    household_ids: List[str],
    start_datetime: datetime
) -> Set[str]:
    """
    Check which households already have balance sheets for this simulation.
    
    Returns:
        Set of household_ids that already exist
    """
    if not household_ids:
        return set()
    
    placeholders = ', '.join(['%s'] * len(household_ids))
    query = f"""
        SELECT DISTINCT household_id
        FROM {sim_mgr._format_table('household_balance_sheet_samples')}
        WHERE simulation_id = %s
          AND household_id IN ({placeholders})
          AND sim_clock_datetime = %s
    """
    
    params = [simulation_id] + list(household_ids) + [start_datetime]
    result = sim_mgr.execute_query(query, tuple(params), fetch=True)
    
    if result.success and result.data:
        return {row['household_id'] for row in result.data}
    
    return set()


def batch_extract_features(sim_mgr, agent_ids: List[str]) -> Dict[str, Dict[str, Any]]:
    """
    Extract L2 features for all agents in a single query.
    
    Returns:
        Dict mapping agent_id -> features dict
    """
    if not agent_ids:
        return {}
    
    placeholders = ', '.join(['%s'] * len(agent_ids))
    query = f"""
        SELECT 
            c.LALVOTERID,
            -- core
            c.Voters_Age,
            c.Voters_Gender,
            c.Voters_FIPS,
            
            -- other part 1
            o1.ConsumerData_Number_Of_Adults_in_HH,
            o1.ConsumerData_Number_Of_Children_in_HH,
            o1.ConsumerData_Number_Of_Persons_in_HH,
            o1.ConsumerData_Education_of_Person,
            o1.ConsumerData_Marital_Status,
            o1.ConsumerData_Inferred_HH_Rank AS ConsumerData_Likely_Income_Ranking_by_Area,
            
            -- other part 2
            o2.ConsumerData_CBSA_Code,
            o2.ConsumerData_MSA_Code,
            
            -- other part 3
            o3.ConsumerData_Home_Purchase_Year,
            o3.ConsumerData_Home_Purchase_Date,
            o3.ConsumerData_PASS_Prospector_Home_Value_Mortgage_File,
            o3.ConsumerData_Home_Est_Current_Value_Code,
            o3.ConsumerData_TaxAssessedValueTotal,
            o3.ConsumerData_TaxMarketValueTotal,
            o3.ConsumerData_Home_Mortgage_Amount,
            o3.ConsumerData_Home_Mortgage_Amount_Code,
            o3.ConsumerData_Dwelling_Type,
            o3.ConsumerData_BedroomsCount,
            o3.ConsumerData_RoomsCount,
            o3.ConsumerData_Credit_Rating,
            o3.ConsumerData_Estimated_Income_Amount,
            o3.ConsumerData_Presence_Of_CC,
            o3.ConsumerData_Presence_Of_Gold_Plat_CC,
            o3.ConsumerData_Presence_Of_Premium_CC,
            o3.ConsumerData_Auto_Year_1,
            o3.ConsumerData_Auto_Year_2,
            o3.ConsumerData_Auto_Make_1,
            o3.ConsumerData_Auto_Model_1,
            o3.ConsumerData_Auto_Make_2,
            o3.ConsumerData_Auto_Model_2,
            
            -- location
            loc.Residence_Addresses_Property_Home_Square_Footage,
            loc.Residence_Addresses_City,
            loc.Residence_Addresses_State,
            loc.Residence_Addresses_Zip,
            loc.Mailing_Addresses_State,
            
            -- geo
            geo.latitude,
            geo.longitude,
            
            -- political part 3 (net worth bucket)
            p3.ConsumerData_Household_Net_Worth
            
        FROM world_sim_agents.l2_agent_core c
        LEFT JOIN world_sim_agents.l2_other_part_1 o1 ON o1.LALVOTERID = c.LALVOTERID
        LEFT JOIN world_sim_agents.l2_other_part_2 o2 ON o2.LALVOTERID = c.LALVOTERID
        LEFT JOIN world_sim_agents.l2_other_part_3 o3 ON o3.LALVOTERID = c.LALVOTERID
        LEFT JOIN world_sim_agents.l2_location loc ON loc.LALVOTERID = c.LALVOTERID
        LEFT JOIN world_sim_agents.l2_geo geo ON geo.LALVOTERID = c.LALVOTERID
        LEFT JOIN world_sim_agents.l2_political_part_3 p3 ON p3.LALVOTERID = c.LALVOTERID
        WHERE c.LALVOTERID IN ({placeholders})
    """
    
    rows = sim_mgr.execute_agents_sql_rows(query, tuple(agent_ids))
    
    features_map = {}
    for row in rows:
        lalvoterid = str(row.get('LALVOTERID'))
        if not lalvoterid:
            continue
        
        # Parse features from row (same logic as _extract_agent_features)
        features = _parse_features_from_row(row)
        features_map[lalvoterid] = features
    
    # Add default features for missing agents
    for agent_id in agent_ids:
        if str(agent_id) not in features_map:
            features_map[str(agent_id)] = _default_features()
    
    return features_map


def batch_fetch_hpi_data(
    alt_mgr,
    hpi_requests: List[Tuple[str, str]]
) -> Dict[Tuple[str, str], Dict[Tuple[int, int], float]]:
    """
    Fetch HPI data for multiple (level, place_id) pairs.
    
    Args:
        alt_mgr: Alternative data manager
        hpi_requests: List of (level, place_id) tuples
        
    Returns:
        Dict mapping (level, place_id) -> {(yr, quarter): index}
    """
    if not hpi_requests:
        return {}
    
    hpi_cache = {}
    
    # Group by level for efficient querying
    by_level: Dict[str, List[str]] = {}
    for level, place_id in hpi_requests:
        if not level or not place_id:
            continue
        if level not in by_level:
            by_level[level] = []
        by_level[level].append(place_id)
    
    for level, place_ids in by_level.items():
        if not place_ids:
            continue
        
        # Remove duplicates
        unique_places = list(set(place_ids))
        placeholders = ', '.join(['%s'] * len(unique_places))
        
        query = f"""
            SELECT yr, period, index_sa, index_nsa, place_id
            FROM {alt_mgr._format_table('hpi_data')}
            WHERE hpi_type = 'traditional'
              AND hpi_flavor = 'all-transactions'
              AND frequency = 'quarterly'
              AND level = %s
              AND place_id IN ({placeholders})
            ORDER BY place_id, yr, period
        """
        
        params = [level] + unique_places
        result = alt_mgr.execute_query(query, tuple(params), fetch=True)
        
        if result.success and result.data:
            for row in result.data:
                place_id = row['place_id']
                yr = int(row['yr'])
                period = int(row['period'])
                idx = row.get('index_sa') or row.get('index_nsa')
                
                if idx is not None:
                    key = (level, place_id)
                    if key not in hpi_cache:
                        hpi_cache[key] = {}
                    hpi_cache[key][(yr, period)] = float(idx)
    
    return hpi_cache


def batch_fetch_calibration_stats(
    features_map: Dict[str, Dict[str, Any]]
) -> Dict[Tuple[Optional[int], Optional[str]], Dict[str, Any]]:
    """
    Fetch census calibration statistics for unique (cbsa_code, state_fips) pairs.
    
    Args:
        features_map: Dict mapping agent_id -> features dict
        
    Returns:
        Dict mapping (cbsa_code, state_fips) -> {owner_stats, mortgage_stats, etc}
        Stats are serialized as dicts for multiprocessing compatibility.
    """
    # Get unique (cbsa_code, state_fips) pairs
    unique_locations = set()
    for features in features_map.values():
        cbsa_code = _to_int(features.get('cbsa_code'), None)
        state_fips = features.get('state_fips')
        unique_locations.add((cbsa_code, state_fips))
    
    # Fetch stats for each unique location
    calibration = _get_census_calibration()
    calibration_stats = {}
    
    for cbsa_code, state_fips in unique_locations:
        try:
            owner_stats_obj = calibration.get_owner_stats(cbsa_code, state_fips)
            mortgage_stats_obj = calibration.get_mortgage_stats(cbsa_code, state_fips)
            heloc_stats_obj = calibration.get_heloc_stats(cbsa_code, state_fips)
            vehicle_stats_obj = calibration.get_vehicle_stats(cbsa_code, state_fips)
            home_value_stats_obj = calibration.get_home_value_stats(cbsa_code, state_fips)
            
            # Serialize stats objects to dicts for multiprocessing
            stats = {
                'owner_stats': _serialize_owner_stats(owner_stats_obj),
                'mortgage_stats': _serialize_mortgage_stats(mortgage_stats_obj),
                'heloc_stats': _serialize_heloc_stats(heloc_stats_obj),
                'vehicle_stats': _serialize_vehicle_stats(vehicle_stats_obj),
                'home_value_stats': _serialize_home_value_stats(home_value_stats_obj),
            }
            calibration_stats[(cbsa_code, state_fips)] = stats
        except Exception as e:
            logger.warning(f"Failed to fetch calibration stats for cbsa={cbsa_code}, state={state_fips}: {e}")
            # Use default/empty stats
            calibration_stats[(cbsa_code, state_fips)] = {
                'owner_stats': _default_owner_stats(),
                'mortgage_stats': _default_mortgage_stats(),
                'heloc_stats': _default_heloc_stats(),
                'vehicle_stats': _default_vehicle_stats(),
                'home_value_stats': _default_home_value_stats(),
            }
    
    return calibration_stats


def _serialize_owner_stats(stats) -> Dict[str, Any]:
    """Serialize owner stats object to dict."""
    if stats is None:
        return _default_owner_stats()
    return {
        'total_units': getattr(stats, 'total_units', 0),
        'p_owner': getattr(stats, 'p_owner', 0.62),
        'p_renter': getattr(stats, 'p_renter', 0.38),
    }


def _serialize_mortgage_stats(stats) -> Dict[str, Any]:
    """Serialize mortgage stats object to dict."""
    if stats is None:
        return _default_mortgage_stats()
    return {
        'p_with_mortgage': getattr(stats, 'p_with_mortgage', 0.65),
        'p_no_mortgage': getattr(stats, 'p_no_mortgage', 0.35),
    }


def _serialize_heloc_stats(stats) -> Dict[str, Any]:
    """Serialize HELOC stats object to dict."""
    if stats is None:
        return _default_heloc_stats()
    return {
        'p_heloc': getattr(stats, 'p_heloc', 0.08),
    }


def _serialize_vehicle_stats(stats) -> Dict[str, Any]:
    """Serialize vehicle stats object to dict."""
    if stats is None:
        return _default_vehicle_stats()
    return {
        'total_households': getattr(stats, 'total_households', 0),
        'p_no_vehicle': getattr(stats, 'p_no_vehicle', 0.10),
        'p_one_vehicle': getattr(stats, 'p_one_vehicle', 0.35),
        'p_two_vehicles': getattr(stats, 'p_two_vehicles', 0.38),
        'p_three_plus': getattr(stats, 'p_three_plus', 0.17),
    }


def _serialize_home_value_stats(stats) -> Dict[str, Any]:
    """Serialize home value stats object to dict."""
    if stats is None:
        return _default_home_value_stats()
    quantiles = {}
    if hasattr(stats, 'quantiles') and stats.quantiles:
        quantiles = dict(stats.quantiles)
    return {
        'quantiles': quantiles,
    }


def _default_owner_stats() -> Dict[str, Any]:
    """Default owner stats."""
    return {
        'total_units': 0,
        'p_owner': 0.62,
        'p_renter': 0.38,
    }


def _default_mortgage_stats() -> Dict[str, Any]:
    """Default mortgage stats."""
    return {
        'p_with_mortgage': 0.65,
        'p_no_mortgage': 0.35,
    }


def _default_heloc_stats() -> Dict[str, Any]:
    """Default HELOC stats."""
    return {
        'p_heloc': 0.08,
    }


def _default_vehicle_stats() -> Dict[str, Any]:
    """Default vehicle stats."""
    return {
        'total_households': 0,
        'p_no_vehicle': 0.10,
        'p_one_vehicle': 0.35,
        'p_two_vehicles': 0.38,
        'p_three_plus': 0.17,
    }


def _default_home_value_stats() -> Dict[str, Any]:
    """Default home value stats."""
    return {
        'quantiles': {},
    }


# Simple wrapper classes to make serialized stats look like objects
class _StatsWrapper:
    """Base wrapper for stats dicts."""
    def __init__(self, stats_dict: Dict[str, Any]):
        for key, value in stats_dict.items():
            setattr(self, key, value)


def _deserialize_stats(stats_dict: Dict[str, Any]):
    """Wrap a stats dict so it can be accessed like an object."""
    if stats_dict is None:
        return None
    return _StatsWrapper(stats_dict)


def _parse_features_from_row(row: Dict[str, Any]) -> Dict[str, Any]:
    """
    Parse features dict from a database row.
    Same logic as _extract_agent_features but operates on a pre-fetched row.
    """
    features = {}
    
    # household size
    num_persons = _to_int(row.get('ConsumerData_Number_Of_Persons_in_HH'), 0)
    num_adults = _to_int(row.get('ConsumerData_Number_Of_Adults_in_HH'), 0)
    num_children = _to_int(row.get('ConsumerData_Number_Of_Children_in_HH'), 0)
    features['householdSize'] = max(num_persons, num_adults + num_children, 1)
    features['num_adults'] = num_adults
    features['num_children'] = num_children
    
    # income
    estimated_income = _to_float(row.get('ConsumerData_Estimated_Income_Amount'))
    income_ranking = row.get('ConsumerData_Likely_Income_Ranking_by_Area')
    
    if estimated_income is not None:
        features['income'] = float(max(estimated_income, 0.0))
    else:
        features['income'] = 50000.0  # default
    
    # income quantile local
    if income_ranking:
        features['incomeQuantileLocal'] = _normalize_income_ranking(income_ranking)
    else:
        features['incomeQuantileLocal'] = 0.5
    
    # credit tier
    credit_rating = row.get('ConsumerData_Credit_Rating')
    has_premium = row.get('ConsumerData_Presence_Of_Premium_CC') or row.get('ConsumerData_Presence_Of_Gold_Plat_CC')
    has_any_cc = row.get('ConsumerData_Presence_Of_CC')
    features['creditTier'] = _infer_credit_tier(credit_rating, has_premium, has_any_cc)
    
    # years since purchase
    purchase_year = row.get('ConsumerData_Home_Purchase_Year')
    purchase_date = row.get('ConsumerData_Home_Purchase_Date')
    features['yearsSincePurchase'] = _compute_years_since_purchase(purchase_year, purchase_date)
    
    # home value hint
    pass_value = _to_float(row.get('ConsumerData_PASS_Prospector_Home_Value_Mortgage_File'), 0.0)
    tax_assessed = _to_float(row.get('ConsumerData_TaxAssessedValueTotal'), 0.0)
    features['homeValueHint'] = max(pass_value, tax_assessed, 150000.0)
    
    # age
    features['age'] = row.get('Voters_Age') or 45
    
    # vehicles
    auto_year_raw_1 = row.get('ConsumerData_Auto_Year_1')
    auto_year_raw_2 = row.get('ConsumerData_Auto_Year_2')
    auto_make_1 = row.get('ConsumerData_Auto_Make_1')
    auto_model_1 = row.get('ConsumerData_Auto_Model_1')
    auto_make_2 = row.get('ConsumerData_Auto_Make_2')
    auto_model_2 = row.get('ConsumerData_Auto_Model_2')

    vehicle_records = []
    for year_raw, make_raw, model_raw in [
        (auto_year_raw_1, auto_make_1, auto_model_1),
        (auto_year_raw_2, auto_make_2, auto_model_2),
    ]:
        year_val = _normalize_vehicle_year(year_raw)
        make_val = (make_raw or '').strip()
        model_val = (model_raw or '').strip()
        if year_val is not None or make_val or model_val:
            vehicle_records.append({
                'year': year_val,
                'make': make_val,
                'model': model_val,
            })

    features['vehicle_records'] = vehicle_records
    features['numVehicles'] = len(vehicle_records)
    features['auto_year_1'] = vehicle_records[0]['year'] if len(vehicle_records) > 0 else None
    features['auto_year_2'] = vehicle_records[1]['year'] if len(vehicle_records) > 1 else None
    
    # net worth bucket
    features['netWorthBucket'] = row.get('ConsumerData_Household_Net_Worth') or ""
    
    # hpi resolution
    cbsa_code = row.get('ConsumerData_CBSA_Code')
    msa_code = row.get('ConsumerData_MSA_Code')
    state = row.get('Residence_Addresses_State') or row.get('Mailing_Addresses_State')
    
    if cbsa_code:
        formatted_cbsa = _format_cbsa_code(cbsa_code)
        if formatted_cbsa:
            features['hpi_level'] = 'MSA'
            features['hpi_place_id'] = formatted_cbsa
        else:
            features['hpi_level'] = 'MSA'
            features['hpi_place_id'] = None
    elif msa_code:
        formatted_msa = _format_int_str(msa_code)
        features['hpi_level'] = 'MSA'
        features['hpi_place_id'] = formatted_msa
    elif state:
        features['hpi_level'] = 'State'
        features['hpi_place_id'] = str(state)
    else:
        features['hpi_level'] = 'State'
        features['hpi_place_id'] = None
    
    # other fields
    features['sqft'] = row.get('Residence_Addresses_Property_Home_Square_Footage')
    features['dwelling_type'] = row.get('ConsumerData_Dwelling_Type')
    features['bedrooms'] = row.get('ConsumerData_BedroomsCount')
    features['rooms'] = row.get('ConsumerData_RoomsCount')
    features['has_cc'] = bool(has_any_cc)
    features['has_premium_cc'] = bool(has_premium)
    features['education'] = row.get('ConsumerData_Education_of_Person')
    features['marital_status'] = row.get('ConsumerData_Marital_Status')
    features['purchase_year'] = purchase_year
    features['purchase_date'] = purchase_date
    features['home_purchase_price'] = row.get('ConsumerData_PASS_Prospector_Home_Value_Mortgage_File')
    features['mortgage_amount_hint'] = row.get('ConsumerData_Home_Mortgage_Amount')
    features['city'] = row.get('Residence_Addresses_City')
    features['state'] = state
    features['state_fips'] = _resolve_state_fips(row.get('Voters_FIPS'), state)
    features['zip_code'] = row.get('Residence_Addresses_Zip')
    features['latitude'] = row.get('latitude')
    features['longitude'] = row.get('longitude')
    features['cbsa_code'] = cbsa_code
    features['msa_code'] = msa_code
    features['current_value_code'] = row.get('ConsumerData_Home_Est_Current_Value_Code')
    
    return features


# ============================================================================
# Household Resolution
# ============================================================================

def _resolve_household_id(sim_mgr, lalvoterid: str) -> str:
    """
    Resolve household_id from L2 data.
    
    Priority:
    1. Residence_Families_FamilyID
    2. Mailing_Families_FamilyID
    3. Synthetic ID: SYNTH_{lalvoterid}
    """
    query = """
        SELECT 
            o1.Residence_Families_FamilyID,
            o1.Mailing_Families_FamilyID
        FROM world_sim_agents.l2_other_part_1 o1
        WHERE o1.LALVOTERID = %s
    """
    
    rows = sim_mgr.execute_agents_sql_rows(query, (lalvoterid,))
    
    if not rows:
        return f"SYNTH_{lalvoterid}"
    
    row = rows[0]
    
    # try residence family first
    res_fam = row.get('Residence_Families_FamilyID')
    if res_fam:
        return str(res_fam)
    
    # fallback to mailing family
    mail_fam = row.get('Mailing_Families_FamilyID')
    if mail_fam:
        return str(mail_fam)
    
    # synthetic fallback
    return f"SYNTH_{lalvoterid}"


def _balance_sheet_exists(sim_mgr, simulation_id: str, household_id: str, start_datetime: datetime) -> bool:
    """Check if balance sheet already exists for this household at simulation start."""
    query = f"""
        SELECT 1 
        FROM {sim_mgr._format_table('household_balance_sheet_samples')}
        WHERE simulation_id = %s 
          AND household_id = %s
          AND sim_clock_datetime = %s
        LIMIT 1
    """
    
    result = sim_mgr.execute_query(query, (simulation_id, household_id, start_datetime), fetch=True)
    
    return result.success and result.data and len(result.data) > 0


def _generate_deterministic_seed(simulation_id: str, household_id: str) -> int:
    """Generate deterministic seed from simulation_id and household_id."""
    combined = f"{simulation_id}:{household_id}"
    hash_digest = hashlib.sha256(combined.encode()).hexdigest()
    # use first 8 hex chars as seed
    return int(hash_digest[:8], 16)


# ============================================================================
# Feature Extraction from L2 Data
# ============================================================================

def _extract_agent_features(sim_mgr, lalvoterid: str) -> Dict[str, Any]:
    """
    Extract all relevant features from L2 tables for balance sheet sampling.
    
    Returns dict with keys:
        householdSize, income, incomeQuantileLocal, creditTier, yearsSincePurchase,
        homeValueHint, age, numVehicles, netWorthBucket, hpi_level, hpi_place_id,
        dwelling_type, bedrooms, rooms, sqft, has_cc, has_premium_cc, education,
        marital_status, num_adults, num_children, purchase_year, purchase_date,
        home_purchase_price, mortgage_amount_hint, auto_year_1, auto_year_2,
        city, state, zip_code, latitude, longitude, cbsa_code, msa_code
    """
    query = """
        SELECT 
            -- core
            c.Voters_Age,
            c.Voters_Gender,
            c.Voters_FIPS,
            
            -- other part 1
            o1.ConsumerData_Number_Of_Adults_in_HH,
            o1.ConsumerData_Number_Of_Children_in_HH,
            o1.ConsumerData_Number_Of_Persons_in_HH,
            o1.ConsumerData_Education_of_Person,
            o1.ConsumerData_Marital_Status,
            -- fallback income ranking present in part_1 schema
            o1.ConsumerData_Inferred_HH_Rank AS ConsumerData_Likely_Income_Ranking_by_Area,
            
            -- other part 2
            NULL AS ConsumerData_AreaMedianHousingValue,
            NULL AS ConsumerData_EstimatedAreaMedianHHIncome,
            NULL AS ConsumerData_AreaMedianEducationYears,
            o2.ConsumerData_CBSA_Code,
            o2.ConsumerData_MSA_Code,
            NULL AS ConsumerData_StateIncomeDecile,
            NULL AS ConsumerData_Likely_Income_Ranking_by_Area_IGNORED,
            
            -- other part 3
            o3.ConsumerData_Home_Purchase_Year,
            o3.ConsumerData_Home_Purchase_Date,
            o3.ConsumerData_PASS_Prospector_Home_Value_Mortgage_File,
            o3.ConsumerData_Home_Est_Current_Value_Code,
            o3.ConsumerData_TaxAssessedValueTotal,
            o3.ConsumerData_TaxMarketValueTotal,
            o3.ConsumerData_Home_Mortgage_Amount,
            o3.ConsumerData_Home_Mortgage_Amount_Code,
            o3.ConsumerData_Dwelling_Type,
            o3.ConsumerData_BedroomsCount,
            o3.ConsumerData_RoomsCount,
            o3.ConsumerData_Credit_Rating,
            o3.ConsumerData_Estimated_Income_Amount,
            o3.ConsumerData_Presence_Of_CC,
            o3.ConsumerData_Presence_Of_Gold_Plat_CC,
            o3.ConsumerData_Presence_Of_Premium_CC,
            o3.ConsumerData_Auto_Year_1,
            o3.ConsumerData_Auto_Year_2,
            o3.ConsumerData_Auto_Make_1,
            o3.ConsumerData_Auto_Model_1,
            o3.ConsumerData_Auto_Make_2,
            o3.ConsumerData_Auto_Model_2,
            
            -- location
            loc.Residence_Addresses_Property_Home_Square_Footage,
            loc.Residence_Addresses_City,
            loc.Residence_Addresses_State,
            loc.Residence_Addresses_Zip,
            loc.Mailing_Addresses_State,
            
            -- geo
            geo.latitude,
            geo.longitude,
            
            -- political part 3 (net worth bucket)
            p3.ConsumerData_Household_Net_Worth
            
        FROM world_sim_agents.l2_agent_core c
        LEFT JOIN world_sim_agents.l2_other_part_1 o1 ON o1.LALVOTERID = c.LALVOTERID
        LEFT JOIN world_sim_agents.l2_other_part_2 o2 ON o2.LALVOTERID = c.LALVOTERID
        LEFT JOIN world_sim_agents.l2_other_part_3 o3 ON o3.LALVOTERID = c.LALVOTERID
        LEFT JOIN world_sim_agents.l2_location loc ON loc.LALVOTERID = c.LALVOTERID
        LEFT JOIN world_sim_agents.l2_geo geo ON geo.LALVOTERID = c.LALVOTERID
        LEFT JOIN world_sim_agents.l2_political_part_3 p3 ON p3.LALVOTERID = c.LALVOTERID
        WHERE c.LALVOTERID = %s
    """
    
    rows = sim_mgr.execute_agents_sql_rows(query, (lalvoterid,))
    
    if not rows:
        # fallback defaults
        return _default_features()
    
    row = rows[0]
    
    # compute derived features
    features = {}
    
    # household size
    num_persons = _to_int(row.get('ConsumerData_Number_Of_Persons_in_HH'), 0)
    num_adults = _to_int(row.get('ConsumerData_Number_Of_Adults_in_HH'), 0)
    num_children = _to_int(row.get('ConsumerData_Number_Of_Children_in_HH'), 0)
    features['householdSize'] = max(num_persons, num_adults + num_children, 1)
    features['num_adults'] = num_adults
    features['num_children'] = num_children
    
    # income
    estimated_income = _to_float(row.get('ConsumerData_Estimated_Income_Amount'))
    median_income = _to_float(row.get('ConsumerData_EstimatedAreaMedianHHIncome'))
    # prefer explicit ranking if present, else fallback to inferred HH rank from part_1
    income_ranking = row.get('ConsumerData_Likely_Income_Ranking_by_Area') or row.get('ConsumerData_Inferred_HH_Rank')
    
    if estimated_income is not None:
        features['income'] = float(max(estimated_income, 0.0))
    elif median_income is not None and income_ranking:
        # infer from ranking
        rank01 = _normalize_income_ranking(income_ranking)
        features['income'] = float(median_income) * (0.55 + 0.9 * rank01)
    else:
        features['income'] = 50000.0  # default
    
    # income quantile local
    if income_ranking:
        features['incomeQuantileLocal'] = _normalize_income_ranking(income_ranking)
    else:
        features['incomeQuantileLocal'] = 0.5
    
    # credit tier
    credit_rating = row.get('ConsumerData_Credit_Rating')
    has_premium = row.get('ConsumerData_Presence_Of_Premium_CC') or row.get('ConsumerData_Presence_Of_Gold_Plat_CC')
    has_any_cc = row.get('ConsumerData_Presence_Of_CC')
    features['creditTier'] = _infer_credit_tier(credit_rating, has_premium, has_any_cc)
    
    # years since purchase
    purchase_year = row.get('ConsumerData_Home_Purchase_Year')
    purchase_date = row.get('ConsumerData_Home_Purchase_Date')
    features['yearsSincePurchase'] = _compute_years_since_purchase(purchase_year, purchase_date)
    
    # home value hint (median housing not available in part_2 schema → ignore)
    pass_value = _to_float(row.get('ConsumerData_PASS_Prospector_Home_Value_Mortgage_File'), 0.0)
    tax_assessed = _to_float(row.get('ConsumerData_TaxAssessedValueTotal'), 0.0)
    features['homeValueHint'] = max(pass_value, tax_assessed, 150000.0)
    
    # age
    features['age'] = row.get('Voters_Age') or 45
    
    # vehicles
    auto_year_raw_1 = row.get('ConsumerData_Auto_Year_1')
    auto_year_raw_2 = row.get('ConsumerData_Auto_Year_2')
    auto_make_1 = row.get('ConsumerData_Auto_Make_1')
    auto_model_1 = row.get('ConsumerData_Auto_Model_1')
    auto_make_2 = row.get('ConsumerData_Auto_Make_2')
    auto_model_2 = row.get('ConsumerData_Auto_Model_2')

    vehicle_records = []
    for year_raw, make_raw, model_raw in [
        (auto_year_raw_1, auto_make_1, auto_model_1),
        (auto_year_raw_2, auto_make_2, auto_model_2),
    ]:
        year_val = _normalize_vehicle_year(year_raw)
        make_val = (make_raw or '').strip()
        model_val = (model_raw or '').strip()
        if year_val is not None or make_val or model_val:
            vehicle_records.append({
                'year': year_val,
                'make': make_val,
                'model': model_val,
            })

    features['vehicle_records'] = vehicle_records
    features['numVehicles'] = len(vehicle_records)
    features['auto_year_1'] = vehicle_records[0]['year'] if len(vehicle_records) > 0 else None
    features['auto_year_2'] = vehicle_records[1]['year'] if len(vehicle_records) > 1 else None
    
    # net worth bucket
    features['netWorthBucket'] = row.get('ConsumerData_Household_Net_Worth') or ""
    
    # hpi resolution (note: CBSA codes map to MSA level in HPI data)
    cbsa_code = row.get('ConsumerData_CBSA_Code')
    msa_code = row.get('ConsumerData_MSA_Code')
    state = row.get('Residence_Addresses_State') or row.get('Mailing_Addresses_State')
    
    if cbsa_code:
        formatted_cbsa = _format_cbsa_code(cbsa_code)
        if formatted_cbsa:
            features['hpi_level'] = 'MSA'  # CBSA codes stored as MSA in HPI data
            features['hpi_place_id'] = formatted_cbsa
        else:
            features['hpi_level'] = 'MSA'
            features['hpi_place_id'] = None
    elif msa_code:
        formatted_msa = _format_int_str(msa_code)
        features['hpi_level'] = 'MSA'
        features['hpi_place_id'] = formatted_msa
    elif state:
        features['hpi_level'] = 'State'  # exact case from HPI data
        features['hpi_place_id'] = str(state)
    else:
        # leave place unset to avoid querying invalid placeholder
        features['hpi_level'] = 'State'
        features['hpi_place_id'] = None
    
    # other fields
    features['sqft'] = row.get('Residence_Addresses_Property_Home_Square_Footage')
    features['dwelling_type'] = row.get('ConsumerData_Dwelling_Type')
    features['bedrooms'] = row.get('ConsumerData_BedroomsCount')
    features['rooms'] = row.get('ConsumerData_RoomsCount')
    features['has_cc'] = bool(has_any_cc)
    features['has_premium_cc'] = bool(has_premium)
    features['education'] = row.get('ConsumerData_Education_of_Person')
    features['marital_status'] = row.get('ConsumerData_Marital_Status')
    features['purchase_year'] = purchase_year
    features['purchase_date'] = purchase_date
    features['home_purchase_price'] = row.get('ConsumerData_PASS_Prospector_Home_Value_Mortgage_File')
    features['mortgage_amount_hint'] = row.get('ConsumerData_Home_Mortgage_Amount')
    features['city'] = row.get('Residence_Addresses_City')
    features['state'] = state
    features['state_fips'] = _resolve_state_fips(row.get('Voters_FIPS'), state)
    features['zip_code'] = row.get('Residence_Addresses_Zip')
    features['latitude'] = row.get('latitude')
    features['longitude'] = row.get('longitude')
    features['cbsa_code'] = cbsa_code
    features['msa_code'] = msa_code
    features['current_value_code'] = row.get('ConsumerData_Home_Est_Current_Value_Code')
    
    return features


def _default_features() -> Dict[str, Any]:
    """Return default features if L2 data is missing."""
    return {
        'householdSize': 2,
        'income': 60000.0,
        'incomeQuantileLocal': 0.5,
        'creditTier': 3,
        'yearsSincePurchase': 8.0,
        'homeValueHint': 250000.0,
        'age': 45,
        'numVehicles': 0,
        'vehicle_records': [],
        'netWorthBucket': '',
        'hpi_level': 'State',
        'hpi_place_id': None,
        'sqft': None,
        'dwelling_type': None,
        'bedrooms': None,
        'rooms': None,
        'has_cc': False,
        'has_premium_cc': False,
        'education': None,
        'marital_status': None,
        'num_adults': 2,
        'num_children': 0,
        'purchase_year': None,
        'purchase_date': None,
        'home_purchase_price': None,
        'mortgage_amount_hint': None,
        'auto_year_1': None,
        'auto_year_2': None,
        'city': None,
        'state': None,
        'zip_code': None,
        'latitude': None,
        'longitude': None,
        'cbsa_code': None,
        'msa_code': None,
        'current_value_code': None,
    }


def _normalize_vehicle_year(year_value: Any) -> Optional[int]:
    """Convert raw vehicle year to integer if plausible."""
    try:
        if year_value is None:
            return None
        year_int = int(str(year_value).strip())
        current_year = datetime.now().year + 1
        if 1900 <= year_int <= current_year:
            return year_int
    except Exception:
        return None
    return None


def _normalize_income_ranking(ranking: Any) -> float:
    """Normalize income ranking to [0, 1]."""
    if ranking is None:
        return 0.5
    try:
        rank_int = int(str(ranking).strip())
        # assuming ranking is 1-10 or 1-100 scale
        if rank_int <= 10:
            return (rank_int - 1) / 9.0
        else:
            return (rank_int - 1) / 99.0
    except (ValueError, TypeError):
        return 0.5


def _infer_credit_tier(credit_rating: Any, has_premium: bool, has_any_cc: bool) -> int:
    """
    Infer credit tier (1-5) from credit rating and CC presence.
    
    Tiers:
    1: <650
    2: 650-699
    3: 700-749
    4: 750-799
    5: 800+
    """
    if credit_rating is not None:
        try:
            score = int(str(credit_rating).strip())
            if score < 650:
                return 1
            elif score < 700:
                return 2
            elif score < 750:
                return 3
            elif score < 800:
                return 4
            else:
                return 5
        except (ValueError, TypeError):
            pass
    
    # fallback based on CC presence
    if has_premium:
        return 4  # at least tier 4
    elif has_any_cc:
        return 2  # at least tier 2
    
    return 3  # default


def _compute_years_since_purchase(purchase_year: Any, purchase_date: Any) -> float:
    """Compute years since home purchase."""
    if purchase_year:
        try:
            year = int(str(purchase_year).strip())
            current_year = datetime.now().year
            return float(current_year - year)
        except (ValueError, TypeError):
            pass
    
    if purchase_date:
        try:
            # try parsing date
            if isinstance(purchase_date, datetime):
                dt = purchase_date
            else:
                # assume YYYY-MM-DD or similar
                dt = datetime.strptime(str(purchase_date)[:10], '%Y-%m-%d')
            years_diff = (datetime.now() - dt).days / 365.25
            return float(years_diff)
        except (ValueError, TypeError):
            pass
    
    return 8.0  # default


def _resolve_state_fips(voters_fips: Any, state_abbr: Optional[str]) -> Optional[str]:
    """Derive 2-digit state FIPS from voter FIPS code or state abbreviation."""
    if voters_fips is not None:
        try:
            digits = ''.join(ch for ch in str(voters_fips) if ch.isdigit())
            if digits:
                return digits.zfill(2)[:2]
        except Exception:
            pass

    if state_abbr:
        abbr = str(state_abbr).strip().upper()
        if abbr in STATE_ABBR_TO_FIPS:
            return STATE_ABBR_TO_FIPS[abbr]
    return None


def _recompute_totals(bs: Dict[str, Any]) -> None:
    """Recalculate aggregate assets, liabilities, and net worth."""
    asset_keys = [
        'primaryHomeValue',
        'secondaryREValue',
        'retirementAccounts',
        'taxableInvestments',
        'liquidSavings',
        'vehiclesValue',
        'durablesOther',
    ]
    liability_keys = [
        'mortgageBalance',
        'autoLoans',
        'creditCardRevolving',
        'studentLoans',
        'otherDebt',
    ]
    bs['assetsTotal'] = float(sum(max(bs.get(k, 0.0), 0.0) for k in asset_keys))
    bs['liabilitiesTotal'] = float(sum(max(bs.get(k, 0.0), 0.0) for k in liability_keys))
    bs['netWorth'] = bs['assetsTotal'] - bs['liabilitiesTotal']


def _align_balance_sheet_to_target(bs: Dict[str, Any], target_net_worth: Optional[float]) -> Dict[str, Any]:
    """Scale assets and liabilities to approach the target net worth."""
    if target_net_worth is None or target_net_worth <= 0:
        return bs

    current = bs.get('netWorth', 0.0)
    if abs(current) < 1.0:
        _boost_liquid_assets(bs, target_net_worth)
        return bs

    scale = float(target_net_worth) / float(current)
    scale = float(np.clip(scale, 0.1, 10.0))

    asset_keys = [
        'primaryHomeValue',
        'secondaryREValue',
        'retirementAccounts',
        'taxableInvestments',
        'liquidSavings',
        'vehiclesValue',
        'durablesOther',
    ]
    liability_keys = [
        'mortgageBalance',
        'autoLoans',
        'creditCardRevolving',
        'studentLoans',
        'otherDebt',
    ]

    for key in asset_keys:
        bs[key] = max(0.0, float(bs.get(key, 0.0)) * scale)
    for key in liability_keys:
        bs[key] = max(0.0, float(bs.get(key, 0.0)) * scale)

    _recompute_totals(bs)
    return bs


def _boost_liquid_assets(bs: Dict[str, Any], amount: float) -> None:
    """Increase liquid holdings by a specified amount."""
    if amount <= 0:
        return
    taxable = float(bs.get('taxableInvestments', 0.0))
    liquid = float(bs.get('liquidSavings', 0.0))
    total = taxable + liquid
    if total <= 0:
        bs['taxableInvestments'] = amount * 0.45
        bs['liquidSavings'] = amount * 0.55
    else:
        ratio_taxable = taxable / total
        bs['taxableInvestments'] = taxable + amount * ratio_taxable
        bs['liquidSavings'] = liquid + amount * (1 - ratio_taxable)
    _recompute_totals(bs)


def _trim_assets(bs: Dict[str, Any], surplus: float) -> None:
    """Reduce asset holdings to shed surplus net worth above bucket upper bound."""
    if surplus <= 0:
        return
    adjustable_keys = [
        'taxableInvestments',
        'liquidSavings',
        'retirementAccounts',
        'vehiclesValue',
        'durablesOther',
        'secondaryREValue',
        'primaryHomeValue',
    ]
    total_adjustable = sum(max(bs.get(k, 0.0), 0.0) for k in adjustable_keys)
    if total_adjustable <= 0:
        return
    ratio = float(np.clip(surplus / total_adjustable, 0.0, 1.0))
    for key in adjustable_keys:
        current = float(bs.get(key, 0.0))
        if current <= 0:
            continue
        reduction = current * ratio
        bs[key] = max(0.0, current - reduction)
    _recompute_totals(bs)


def _safe_parse_dollar(value: Any) -> Optional[float]:
    """Parse a numeric value from a currency-like string."""
    try:
        return float(str(value).replace(',', '').strip())
    except (TypeError, ValueError):
        return None


def _interpolate_home_value_quantile(home_value_stats, quantile: float) -> Optional[float]:
    """Interpolate home value at an arbitrary quantile using available ACS quantiles."""
    if not home_value_stats or not getattr(home_value_stats, 'quantiles', None):
        return None
    quantile = float(np.clip(quantile, 0.0, 0.99))
    pairs = []
    for key, value in home_value_stats.quantiles.items():
        if not key.startswith('q'):
            continue
        try:
            q = float(key[1:]) / 100.0
            pairs.append((q, float(value)))
        except Exception:
            continue
    if not pairs:
        return None
    pairs.sort(key=lambda x: x[0])

    if quantile <= pairs[0][0]:
        return pairs[0][1]
    if quantile >= pairs[-1][0]:
        return pairs[-1][1]

    for idx in range(1, len(pairs)):
        q0, v0 = pairs[idx - 1]
        q1, v1 = pairs[idx]
        if q0 <= quantile <= q1 and q1 > q0:
            weight = (quantile - q0) / (q1 - q0)
            return v0 + weight * (v1 - v0)
    return pairs[-1][1]


def _compute_net_worth_anchor(
    features: Dict[str, Any],
    is_owner: bool,
    home_value_stats,
) -> float:
    """Derive a baseline net worth anchor from income and ownership status."""
    income = max(float(features.get('income', 0.0)), 20000.0)
    income_quantile = float(np.clip(features.get('incomeQuantileLocal', 0.5), 0.0, 1.0))

    anchor = income * (2.1 + 1.1 * income_quantile)
    if is_owner:
        median_home = _interpolate_home_value_quantile(home_value_stats, 0.55)
        if median_home:
            anchor += median_home * 0.5
    else:
        anchor += income * 0.35
    return float(max(anchor, 20000.0))


def _sample_target_net_worth(
    rng: np.random.Generator,
    features: Dict[str, Any],
    bucket: str,
    is_owner: bool,
    home_value_stats,
) -> float:
    """Sample a target net worth within (or consistent with) the provided bucket."""
    lower, upper = _parse_net_worth_bounds(bucket)
    anchor = _compute_net_worth_anchor(features, is_owner, home_value_stats)
    income_quantile = float(np.clip(features.get('incomeQuantileLocal', 0.5), 0.0, 1.0))

    if lower is None and upper is None:
        mu = np.log(anchor)
        sigma = 0.55 + 0.25 * (1.0 - income_quantile)
        target = float(rng.lognormal(mu, sigma))
        return float(np.clip(target, 20000.0, anchor * 6.0))

    if lower is not None and upper is not None and upper > lower:
        width = max(upper - lower, 5000.0)
        alpha = 2.0 + 2.5 * income_quantile
        beta = 2.0 + 2.5 * (1.0 - income_quantile)
        percentile = float(rng.beta(alpha, beta))
        target = lower + percentile * width
        margin = max(width * 0.05, 1500.0)
        return float(np.clip(target, lower + margin * 0.25, upper - margin * 0.25))

    if lower is not None and (upper is None or upper <= lower):
        growth = float(rng.lognormal(0.35 + 0.4 * income_quantile, 0.5))
        target = max(anchor, lower) * growth
        return float(np.clip(target, lower + 1000.0, anchor * 8.0))

    if upper is not None:
        base = min(anchor, upper)
        percentile = float(rng.beta(1.1, 2.6))
        target = base * (0.45 + 0.5 * percentile)
        return float(np.clip(target, 15000.0, upper - 1000.0))

    return float(anchor)


def _estimate_homeownership_probability(features: Dict[str, Any], owner_stats) -> float:
    """Blend ACS ownership share with L2 signals to estimate ownership probability."""
    prob = owner_stats.p_owner if owner_stats.total_units > 0 else 0.62

    if features.get('home_purchase_price') or features.get('purchase_year'):
        prob = max(prob, 0.78)
    dwelling = str(features.get('dwelling_type') or '').lower()
    if 'rent' in dwelling or 'apartment' in dwelling:
        prob *= 0.55
    if features.get('homeValueHint', 0.0) > 600000:
        prob = min(0.95, prob + 0.12)
    if features.get('netWorthBucket', '').startswith('Greater than'):
        prob = min(0.97, prob + 0.1)

    return float(np.clip(prob, 0.05, 0.99))


# ============================================================================
# HPI Data Retrieval
# ============================================================================

def _get_hpi_growth_factor_from_cache(
    hpi_index_cache: Dict[Tuple[str, str], Dict[Tuple[int, int], float]],
    hpi_level: str,
    hpi_place_id: str,
    purchase_quarter: Tuple[int, int],
    current_quarter: Tuple[int, int]
) -> float:
    """
    Calculate HPI growth factor from cache (no DB access).
    
    Args:
        hpi_index_cache: Pre-fetched HPI data
        hpi_level: HPI geographic level
        hpi_place_id: Place identifier
        purchase_quarter: (year, quarter) tuple for purchase
        current_quarter: (year, quarter) tuple for current time
        
    Returns:
        Growth factor (current_index / purchase_index), defaults to 1.0 if data missing
    """
    if not hpi_level or not hpi_place_id:
        return 1.0
    
    key = (hpi_level, hpi_place_id)
    index_by_quarter = hpi_index_cache.get(key, {})
    
    if not index_by_quarter:
        return 1.0
    
    # Compute indices with interpolation/extrapolation as needed
    purchase_idx = _get_hpi_index_with_interpolation(index_by_quarter, purchase_quarter)
    current_idx = _get_hpi_index_with_interpolation(index_by_quarter, current_quarter)

    if purchase_idx is None or current_idx is None:
        return 1.0

    if purchase_idx <= 0:
        return 1.0

    return float(current_idx / purchase_idx)


def _get_hpi_growth_factor(
    alt_mgr,
    hpi_level: str,
    hpi_place_id: str,
    purchase_quarter: Tuple[int, int],
    current_quarter: Tuple[int, int]
) -> float:
    """
    Calculate HPI growth factor from purchase to current quarter.
    
    Args:
        alt_mgr: Alternative data manager
        hpi_level: HPI geographic level (CBSA, MSA, STATE)
        hpi_place_id: Place identifier
        purchase_quarter: (year, quarter) tuple for purchase
        current_quarter: (year, quarter) tuple for current time
        
    Returns:
        Growth factor (current_index / purchase_index), defaults to 1.0 if data missing
    """
    if not hpi_level or not hpi_place_id:
        return 1.0

    query = f"""
        SELECT yr, period, index_sa, index_nsa
        FROM {alt_mgr._format_table('hpi_data')}
        WHERE hpi_type = 'traditional'
          AND hpi_flavor = 'all-transactions'
          AND frequency = 'quarterly'
          AND level = %s
          AND place_id = %s
        ORDER BY yr, period
    """
    
    result = alt_mgr.execute_query(query, (hpi_level, hpi_place_id), fetch=True)
    
    if not result.success or not result.data:
        logger.warning(f"No HPI data found for {hpi_level}/{hpi_place_id}")
        return 1.0
    
    # build sorted index timeline
    index_by_quarter: Dict[Tuple[int, int], float] = {}
    for row in result.data:
        yr = int(row['yr'])
        period = int(row['period'])
        idx = row.get('index_sa') or row.get('index_nsa')
        if idx is not None:
            index_by_quarter[(yr, period)] = float(idx)

    if not index_by_quarter:
        logger.warning(f"No HPI data found for {hpi_level}/{hpi_place_id}")
        return 1.0

    # compute indices with interpolation/extrapolation as needed
    purchase_idx = _get_hpi_index_with_interpolation(index_by_quarter, purchase_quarter)
    current_idx = _get_hpi_index_with_interpolation(index_by_quarter, current_quarter)

    if purchase_idx is None or current_idx is None:
        return 1.0

    if purchase_idx <= 0:
        return 1.0

    return float(current_idx / purchase_idx)


def _datetime_to_quarter(dt: datetime) -> Tuple[int, int]:
    """Convert datetime to (year, quarter) tuple."""
    year = dt.year
    quarter = (dt.month - 1) // 3 + 1
    return (year, quarter)


def _format_cbsa_code(code: Any) -> Optional[str]:
    """Normalize CBSA code to a 5-digit zero-padded string."""
    try:
        if code is None:
            return None
        # handle values like '38860.0' → '38860'
        code_int = int(float(str(code).strip()))
        return str(code_int).zfill(5)
    except Exception:
        return None


def _format_int_str(value: Any) -> Optional[str]:
    """Normalize numeric-like string to integer string without decimals."""
    try:
        if value is None:
            return None
        return str(int(float(str(value).strip())))
    except Exception:
        return None


# ============================================================================
# Balance Sheet Sampling
# ============================================================================

def _sample_household_balance_sheet_with_cache(
    simulation_id: str,
    household_id: str,
    lalvoterid: str,
    start_datetime: datetime,
    features: Dict[str, Any],
    hpi_index_cache: Dict[Tuple[str, str], Dict[Tuple[int, int], float]],
    calibration_stats: Dict[str, Any],
    rng_seed: int
) -> Dict[str, Any]:
    """
    Sample balance sheet using pre-fetched features and HPI cache (no DB access).
    
    This is the compute-only version that workers can safely call in parallel.
    """
    rng = np.random.default_rng(rng_seed)
    
    # Use pre-fetched calibration stats instead of loading from DB
    cbsa_code = _to_int(features.get('cbsa_code'), None)
    state_fips = features.get('state_fips')
    
    # Get stats from pre-fetched dict (they were serialized in parent process)
    key = (cbsa_code, state_fips)
    stats = calibration_stats.get(key, {})
    
    # Deserialize stats dicts to wrapper objects
    owner_stats = _deserialize_stats(stats.get('owner_stats'))
    mortgage_stats = _deserialize_stats(stats.get('mortgage_stats'))
    heloc_stats = _deserialize_stats(stats.get('heloc_stats'))
    vehicle_stats = _deserialize_stats(stats.get('vehicle_stats'))
    home_value_stats = _deserialize_stats(stats.get('home_value_stats'))

    owner_prob = _estimate_homeownership_probability(features, owner_stats)
    is_owner = rng.random() < owner_prob
    features['is_owner'] = is_owner

    mortgage_prob = mortgage_stats.p_with_mortgage if is_owner else 0.0
    has_mortgage = bool(is_owner and mortgage_prob > 0.0 and rng.random() < mortgage_prob)
    features['has_mortgage'] = has_mortgage

    # HELOC probability
    heloc_prob = heloc_stats.p_heloc if has_mortgage else 0.0
    features['has_heloc'] = bool(has_mortgage and heloc_prob > 0.0 and rng.random() < heloc_prob)
    
    # Get HPI growth factor from cache
    current_quarter = _datetime_to_quarter(start_datetime)
    purchase_year = features['purchase_year']
    if purchase_year:
        try:
            purchase_quarter = (int(float(str(purchase_year).strip())), 2)
        except Exception:
            purchase_quarter = (start_datetime.year - 8, 2)
    else:
        purchase_quarter = (start_datetime.year - 8, 2)
    
    hpi_growth_factor = _get_hpi_growth_factor_from_cache(
        hpi_index_cache,
        features['hpi_level'],
        features['hpi_place_id'],
        purchase_quarter,
        current_quarter
    )
    
    # Sample balance sheet components
    bs = {}
    
    # identifiers
    bs['simulation_id'] = simulation_id
    bs['household_id'] = household_id
    bs['sim_clock_datetime'] = start_datetime
    bs['net_worth_bucket'] = features['netWorthBucket']
    bs['hpi_level'] = features['hpi_level']
    bs['hpi_place_id'] = features['hpi_place_id']
    
    # sample primary home value
    if is_owner:
        home_result = _sample_primary_home_value(
            rng,
            features,
            hpi_growth_factor,
            home_value_stats,
        )
        bs['primaryHomeValue'] = home_result['value']
        purchase_price = home_result['purchase_price']
    else:
        bs['primaryHomeValue'] = 0.0
        purchase_price = 0.0
    
    # sample mortgage balance
    bs['mortgageBalance'] = _sample_mortgage_balance(
        rng,
        features,
        purchase_price,
        features['yearsSincePurchase'],
        has_mortgage=has_mortgage,
    )
    
    # sample secondary real estate
    if is_owner:
        bs['secondaryREValue'] = _sample_secondary_real_estate(rng, features, bs['primaryHomeValue'])
    else:
        bs['secondaryREValue'] = 0.0
    
    # sample retirement accounts
    bs['retirementAccounts'] = _sample_retirement_accounts(rng, features)
    
    # sample taxable investments
    bs['taxableInvestments'] = _sample_taxable_investments(rng, features)
    
    # sample liquid savings
    bs['liquidSavings'] = _sample_liquid_savings(rng, features)
    
    # sample vehicles
    vehicle_result = _sample_vehicles(rng, features, start_datetime, vehicle_stats)
    bs['vehiclesValue'] = vehicle_result['value']
    bs['vehicle_lambda_decay'] = vehicle_result['lambda_decay']
    inferred_vehicle_count = vehicle_result.get('count', features.get('numVehicles', 0))
    
    # sample durables
    bs['durablesOther'] = _sample_durables(rng)
    
    # sample liabilities
    bs['autoLoans'] = _sample_auto_loans(rng, features, inferred_vehicle_count)
    bs['creditCardRevolving'] = _sample_credit_card_revolving(rng, features)
    bs['studentLoans'] = _sample_student_loans(rng, features)
    bs['otherDebt'] = _sample_other_debt(rng)
    
    # compute totals
    _recompute_totals(bs)

    target_net_worth = _sample_target_net_worth(
        rng,
        features,
        features['netWorthBucket'],
        is_owner,
        home_value_stats,
    )

    bs = _align_balance_sheet_to_target(bs, target_net_worth)
    
    # enforce net worth bucket constraint if present
    bs = _enforce_net_worth_constraint(
        rng,
        bs,
        features['netWorthBucket'],
        target_net_worth=target_net_worth,
    )
    
    return bs


def _sample_household_balance_sheet(
    sim_mgr,
    alt_mgr,
    simulation_id: str,
    household_id: str,
    lalvoterid: str,
    start_datetime: datetime,
    rng_seed: int
) -> Dict[str, Any]:
    """
    Sample a single household balance sheet at simulation start.
    
    Returns dict ready for insertion with all required columns.
    """
    rng = np.random.default_rng(rng_seed)
    
    # extract features
    features = _extract_agent_features(sim_mgr, lalvoterid)
    calibration = _get_census_calibration()
    cbsa_code = _to_int(features.get('cbsa_code'), None)
    state_fips = features.get('state_fips')

    owner_stats = calibration.get_owner_stats(cbsa_code, state_fips)
    mortgage_stats = calibration.get_mortgage_stats(cbsa_code, state_fips)
    heloc_stats = calibration.get_heloc_stats(cbsa_code, state_fips)
    vehicle_stats = calibration.get_vehicle_stats(cbsa_code, state_fips)
    home_value_stats = calibration.get_home_value_stats(cbsa_code, state_fips)

    owner_prob = _estimate_homeownership_probability(features, owner_stats)
    is_owner = rng.random() < owner_prob
    features['is_owner'] = is_owner

    mortgage_prob = mortgage_stats.p_with_mortgage if is_owner else 0.0
    has_mortgage = bool(is_owner and mortgage_prob > 0.0 and rng.random() < mortgage_prob)
    features['has_mortgage'] = has_mortgage

    # HELOC probability (used later)
    heloc_prob = heloc_stats.p_heloc if has_mortgage else 0.0
    features['has_heloc'] = bool(has_mortgage and heloc_prob > 0.0 and rng.random() < heloc_prob)
    
    # get HPI growth factor
    current_quarter = _datetime_to_quarter(start_datetime)
    purchase_year = features['purchase_year']
    if purchase_year:
        # assume Q2 for purchase if no specific date
        try:
            purchase_quarter = (int(float(str(purchase_year).strip())), 2)
        except Exception:
            purchase_quarter = (start_datetime.year - 8, 2)
    else:
        # default to 8 years ago
        purchase_quarter = (start_datetime.year - 8, 2)
    
    hpi_growth_factor = _get_hpi_growth_factor(
        alt_mgr,
        features['hpi_level'],
        features['hpi_place_id'],
        purchase_quarter,
        current_quarter
    )
    
    # sample balance sheet components
    bs = {}
    
    # identifiers
    bs['simulation_id'] = simulation_id
    bs['household_id'] = household_id
    bs['sim_clock_datetime'] = start_datetime
    bs['net_worth_bucket'] = features['netWorthBucket']
    bs['hpi_level'] = features['hpi_level']
    bs['hpi_place_id'] = features['hpi_place_id']
    
    # sample primary home value
    if is_owner:
        home_result = _sample_primary_home_value(
            rng,
            features,
            hpi_growth_factor,
            home_value_stats,
        )
        bs['primaryHomeValue'] = home_result['value']
        purchase_price = home_result['purchase_price']
    else:
        bs['primaryHomeValue'] = 0.0
        purchase_price = 0.0
    
    # sample mortgage balance
    bs['mortgageBalance'] = _sample_mortgage_balance(
        rng,
        features,
        purchase_price,
        features['yearsSincePurchase'],
        has_mortgage=has_mortgage,
    )
    
    # sample secondary real estate
    if is_owner:
        bs['secondaryREValue'] = _sample_secondary_real_estate(rng, features, bs['primaryHomeValue'])
    else:
        bs['secondaryREValue'] = 0.0
    
    # sample retirement accounts
    bs['retirementAccounts'] = _sample_retirement_accounts(rng, features)
    
    # sample taxable investments
    bs['taxableInvestments'] = _sample_taxable_investments(rng, features)
    
    # sample liquid savings
    bs['liquidSavings'] = _sample_liquid_savings(rng, features)
    
    # sample vehicles
    vehicle_result = _sample_vehicles(rng, features, start_datetime, vehicle_stats)
    bs['vehiclesValue'] = vehicle_result['value']
    bs['vehicle_lambda_decay'] = vehicle_result['lambda_decay']
    inferred_vehicle_count = vehicle_result.get('count', features.get('numVehicles', 0))
    
    # sample durables
    bs['durablesOther'] = _sample_durables(rng)
    
    # sample liabilities
    bs['autoLoans'] = _sample_auto_loans(rng, features, inferred_vehicle_count)
    bs['creditCardRevolving'] = _sample_credit_card_revolving(rng, features)
    bs['studentLoans'] = _sample_student_loans(rng, features)
    bs['otherDebt'] = _sample_other_debt(rng)
    
    # compute totals
    _recompute_totals(bs)

    target_net_worth = _sample_target_net_worth(
        rng,
        features,
        features['netWorthBucket'],
        is_owner,
        home_value_stats,
    )

    bs = _align_balance_sheet_to_target(bs, target_net_worth)
    
    # enforce net worth bucket constraint if present
    bs = _enforce_net_worth_constraint(
        rng,
        bs,
        features['netWorthBucket'],
        target_net_worth=target_net_worth,
    )
    
    return bs


def _sample_primary_home_value(
    rng: np.random.Generator,
    features: Dict[str, Any],
    hpi_growth_factor: float,
    home_value_stats
) -> Dict[str, float]:
    """
    Sample primary home value using lognormal distribution.
    
    Returns:
        dict with keys: value, purchase_price
    """
    if not features.get('is_owner'):
        return {'value': 0.0, 'purchase_price': 0.0}

    # estimate purchase price
    if features.get('home_purchase_price'):
        purchase_price = float(features['home_purchase_price'])
    else:
        anchor = _interpolate_home_value_quantile(home_value_stats, features.get('incomeQuantileLocal', 0.5))
        hint = features.get('homeValueHint', 0.0)
        inferred_value = max(anchor or 0.0, float(hint or 0.0))
        if inferred_value <= 0:
            inferred_value = 220000.0
        purchase_price = inferred_value / max(hpi_growth_factor, 0.1)
    
    # current center value
    center_value = purchase_price * hpi_growth_factor
    median_anchor = _interpolate_home_value_quantile(home_value_stats, min(features.get('incomeQuantileLocal', 0.5) + 0.15, 0.95))
    if median_anchor:
        center_value = 0.6 * center_value + 0.4 * median_anchor
    center_value = max(center_value, 80000.0)
    
    # lognormal parameters
    current_value_code = features.get('current_value_code', '')
    if '$1,000,000 Plus' in str(current_value_code):
        sigma_home = 0.18
    else:
        sigma_home = 0.25
    
    sqft = features.get('sqft') or 2000
    sqft_adj = 0.00006 * (sqft - 2000)
    
    income_quantile = features['incomeQuantileLocal']
    income_adj = 0.08 * (income_quantile - 0.5)
    
    mu_home = np.log(center_value) + sqft_adj + income_adj
    
    # sample
    value = float(rng.lognormal(mu_home, sigma_home))
    
    return {'value': max(value, 10000.0), 'purchase_price': purchase_price}


def _sample_mortgage_balance(
    rng: np.random.Generator,
    features: Dict[str, Any],
    purchase_price: float,
    years_since_purchase: float,
    has_mortgage: bool
) -> float:
    """Sample mortgage balance using amortization calculation."""
    if not has_mortgage or purchase_price <= 0:
        return 0.0

    # initial mortgage amount
    mortgage_hint = features.get('mortgage_amount_hint')
    if mortgage_hint:
        initial_principal = float(mortgage_hint)
    else:
        # sample initial LTV based on credit tier
        credit_tier = features['creditTier']
        ltv = _sample_initial_ltv(rng, credit_tier, features['incomeQuantileLocal'])
        initial_principal = ltv * purchase_price
    
    if initial_principal <= 0:
        return 0.0
    
    # amortization parameters
    rate = float(_sample_trunc_normal(rng, 0.05, 0.015, 0.02, 0.09))
    term_years = int(rng.choice([15, 20, 30], p=[0.1, 0.2, 0.7]))
    
    # compute remaining balance
    monthly_rate = rate / 12.0
    term_months = term_years * 12
    elapsed_months = int(round(years_since_purchase * 12))
    
    if elapsed_months >= term_months:
        return 0.0
    
    # monthly payment
    if monthly_rate > 0:
        pmt = initial_principal * monthly_rate / (1 - (1 + monthly_rate) ** (-term_months))
    else:
        pmt = initial_principal / term_months
    
    # remaining balance after elapsed_months
    if monthly_rate > 0:
        remaining = (
            initial_principal * (1 + monthly_rate) ** elapsed_months -
            pmt * ((1 + monthly_rate) ** elapsed_months - 1) / monthly_rate
        )
    else:
        remaining = initial_principal - pmt * elapsed_months
    
    return max(remaining, 0.0)


def _sample_initial_ltv(rng: np.random.Generator, credit_tier: int, income_quantile: float) -> float:
    """Sample initial loan-to-value ratio using beta distribution."""
    # map credit tier to beta parameters
    if credit_tier == 5:
        alpha, beta = 2.5, 2.5
    elif credit_tier == 4:
        alpha, beta = 2.2, 2.0
    elif credit_tier == 3:
        alpha, beta = 2.0, 2.0
    elif credit_tier == 2:
        alpha, beta = 1.9, 1.7
    else:  # tier 1
        alpha, beta = 1.8, 1.4
    
    ltv = float(rng.beta(alpha, beta))
    return np.clip(ltv, 0.0, 0.95)


def _sample_secondary_real_estate(
    rng: np.random.Generator,
    features: Dict[str, Any],
    primary_home_value: float
) -> float:
    """Sample secondary real estate value."""
    income_quantile = features['incomeQuantileLocal']
    credit_tier = features['creditTier']
    
    # probability of owning secondary RE
    p2 = 0.03 + 0.10 * (income_quantile > 0.8) + 0.05 * (credit_tier >= 4)
    
    if rng.random() > p2:
        return 0.0
    
    # sample value
    mu2 = np.log(0.45 * primary_home_value)
    sigma2 = 0.6
    
    value = float(rng.lognormal(mu2, sigma2))
    return max(value, 0.0)


def _sample_retirement_accounts(rng: np.random.Generator, features: Dict[str, Any]) -> float:
    """Sample retirement account balance using gamma distribution."""
    income = features['income']
    age = features['age']
    income_quantile = features['incomeQuantileLocal']
    
    # gamma parameters
    k = 1.0 + 0.35 * np.log1p(income) + 0.025 * age
    theta = 8000 + 12000 * income_quantile
    
    # sample
    value = float(rng.gamma(k, theta))
    
    # cap at 8x income
    return min(value, 8.0 * income)


def _sample_taxable_investments(rng: np.random.Generator, features: Dict[str, Any]) -> float:
    """Sample taxable investment balance using lognormal distribution."""
    income_quantile = features['incomeQuantileLocal']
    credit_tier = features['creditTier']
    
    mu_tax = 9.5 + 0.9 * income_quantile + 0.3 * (credit_tier >= 4)
    sigma_tax = 0.9
    
    value = float(rng.lognormal(mu_tax, sigma_tax))
    return max(value, 0.0)


def _sample_liquid_savings(rng: np.random.Generator, features: Dict[str, Any]) -> float:
    """Sample liquid savings using lognormal distribution."""
    income_quantile = features['incomeQuantileLocal']
    household_size = features['householdSize']
    num_children = features['num_children']
    
    mu_cash = 9.0 + 0.7 * income_quantile - 0.15 * max(household_size - 2, 0)
    sigma_cash = 1.1 if num_children > 0 else 0.8
    
    value = float(rng.lognormal(mu_cash, sigma_cash))
    return max(value, 0.0)


def _sample_vehicles(
    rng: np.random.Generator,
    features: Dict[str, Any],
    current_date: datetime,
    vehicle_stats=None
) -> Dict[str, float]:
    """
    Sample vehicle values using explicit exponential depreciation.
    
    Returns:
        dict with keys: value, lambda_decay
    """
    # sample household-specific decay rate
    lambda_decay = float(_sample_trunc_normal(rng, 0.18, 0.05, 0.08, 0.35))
    
    current_year = current_date.year
    total_value = 0.0
    vehicle_count = 0
    
    vehicle_records: List[Dict[str, Any]] = features.get('vehicle_records', []) or []
    income_quantile = features.get('incomeQuantileLocal', 0.5)
    
    for record in vehicle_records:
        make = record.get('make')
        model = record.get('model')
        recorded_year = record.get('year')
        if recorded_year is not None:
            age = max(0, current_year - recorded_year)
        else:
            age = int(round(_sample_vehicle_age_from_household(rng, features.get('age'))))
        base_price = _estimate_vehicle_base_price(make, model, income_quantile)
        # introduce moderate variability
        msrp = base_price * float(rng.lognormal(0.0, 0.25))
        value = msrp * np.exp(-lambda_decay * max(age, 0))
        total_value += max(value, 0.0)
        vehicle_count += 1
    
    if vehicle_count == 0:
        prob_any_vehicle = 0.7
        if vehicle_stats and vehicle_stats.total_households > 0:
            prob_any_vehicle = float(np.clip(1.0 - vehicle_stats.p_no_vehicle, 0.05, 0.95))

        simulated_count = 0
        if rng.random() < prob_any_vehicle:
            if vehicle_stats and vehicle_stats.total_households > 0:
                dist = [
                    (1, vehicle_stats.p_one_vehicle),
                    (2, vehicle_stats.p_two_vehicles),
                    (3, vehicle_stats.p_three_plus),
                ]
                total_prob = sum(weight for _, weight in dist)
                if total_prob > 0:
                    draw = rng.random() * total_prob
                    cumulative = 0.0
                    chosen = 1
                    for count, weight in dist:
                        cumulative += weight
                        if draw <= cumulative:
                            chosen = 3 if count == 3 else count
                            break
                    if chosen == 3:
                        simulated_count = rng.integers(3, 5)
                    else:
                        simulated_count = chosen
            if simulated_count == 0:
                simulated_count = 1

        for _ in range(simulated_count):
            household_age = features.get('age')
            if household_age is not None and household_age >= 40:
                age = int(round(_sample_vehicle_age_from_household(rng, household_age)))
            else:
                age = int(rng.choice(range(2, 15), p=_vehicle_age_probs()))
            base_price = _estimate_vehicle_base_price(None, None, income_quantile)
            msrp = base_price * float(rng.lognormal(0.0, 0.25))
            total_value += max(msrp * np.exp(-lambda_decay * age), 0.0)
        vehicle_count = simulated_count

    # update downstream expectations
    features['numVehicles'] = vehicle_count
    
    return {
        'value': total_value,
        'lambda_decay': lambda_decay,
        'count': vehicle_count,
    }


def _vehicle_age_probs() -> List[float]:
    """Return probability distribution for vehicle age (2-14 years)."""
    # right-tailed distribution
    ages = np.arange(2, 15)
    probs = np.exp(-0.15 * (ages - 2))
    probs = probs / probs.sum()
    return probs.tolist()


_VEHICLE_MAKE_PRICE_MAP: Dict[str, float] = {
    'BMW': 55000.0,
    'MERCEDES': 60000.0,
    'AUDI': 55000.0,
    'LEXUS': 52000.0,
    'TESLA': 65000.0,
    'VOLVO': 48000.0,
    'CADILLAC': 58000.0,
    'INFINITI': 50000.0,
    'ACURA': 45000.0,
    'TOYOTA': 32000.0,
    'HONDA': 30000.0,
    'FORD': 34000.0,
    'CHEVROLET': 33000.0,
    'GMC': 42000.0,
    'SUBARU': 31000.0,
    'NISSAN': 29000.0,
    'KIA': 27000.0,
    'HYUNDAI': 28000.0,
    'JEEP': 36000.0,
    'DODGE': 36000.0,
    'MAZDA': 29000.0,
    'VOLKSWAGEN': 31000.0,
    'BUICK': 36000.0,
    'CHRYSLER': 34000.0,
    'PORSCHE': 90000.0,
    'LAND ROVER': 90000.0,
    'MINI': 29000.0,
    'MITSUBISHI': 26000.0,
}


def _estimate_vehicle_base_price(
    make: Optional[str],
    model: Optional[str],
    income_quantile: float
) -> float:
    """Estimate a vehicle's base MSRP using make/model cues and income."""
    descriptor = f"{make or ''} {model or ''}".strip().upper()
    make_key = (make or '').strip().upper()
    
    base_price = 30000.0
    if make_key in _VEHICLE_MAKE_PRICE_MAP:
        base_price = _VEHICLE_MAKE_PRICE_MAP[make_key]
    else:
        for key, price in _VEHICLE_MAKE_PRICE_MAP.items():
            if key in descriptor:
                base_price = price
                break
    
    if descriptor:
        if any(keyword in descriptor for keyword in ['TRUCK', 'F-150', 'RAM', 'SILVERADO', 'SIERRA', 'TUNDRA']):
            base_price *= 1.15
        if any(keyword in descriptor for keyword in ['SUV', 'CROSSOVER', 'EXPLORER', 'HIGHLANDER', 'ESCALADE', '4RUNNER']):
            base_price *= 1.08
        if any(keyword in descriptor for keyword in ['HYBRID', 'ELECTRIC', 'EV', 'TESLA']):
            base_price *= 1.12
        if any(keyword in descriptor for keyword in ['MINI', 'CIVIC', 'COROLLA', 'YARIS', 'FIT']):
            base_price *= 0.85
    
    income_adj = np.clip(income_quantile, 0.0, 1.0)
    base_price *= 0.75 + 0.5 * income_adj
    
    return float(np.clip(base_price, 12000.0, 120000.0))


def _sample_vehicle_age_from_household(
    rng: np.random.Generator,
    household_median_age: Optional[float]
) -> float:
    """Sample vehicle age conditioned on household age, bounded between 6 and 15 years."""
    if household_median_age is None:
        return float(rng.choice(range(6, 16)))
    
    mean_age = np.clip(0.4 * (float(household_median_age) - 30.0) + 8.0, 6.0, 15.0)
    std_age = 2.5
    sampled = _sample_trunc_normal(rng, mean_age, std_age, 6.0, 15.0)
    return max(1.0, sampled)


def _sample_durables(rng: np.random.Generator) -> float:
    """Sample other durable goods value."""
    value = float(rng.lognormal(9.2, 0.7))
    return max(value, 0.0)


def _sample_auto_loans(
    rng: np.random.Generator,
    features: Dict[str, Any],
    vehicle_count: Optional[int]
) -> float:
    """Sample auto loan balance."""
    num_vehicles = vehicle_count if vehicle_count is not None else features.get('numVehicles', 0)
    credit_tier = features['creditTier']
    
    p_auto = 0.25 + 0.2 * (num_vehicles >= 1) + 0.15 * (num_vehicles >= 2) - 0.05 * credit_tier
    p_auto = np.clip(p_auto, 0.0, 1.0)
    
    if rng.random() > p_auto:
        return 0.0
    
    value = float(rng.lognormal(10.5, 0.7))
    return max(value, 0.0)


def _sample_credit_card_revolving(rng: np.random.Generator, features: Dict[str, Any]) -> float:
    """Sample credit card revolving balance."""
    has_cc = features['has_cc']
    credit_tier = features['creditTier']
    income = features['income']
    
    p_zero = 0.25 if has_cc else 0.60
    
    if rng.random() < p_zero:
        return 0.0
    
    # tier-specific parameters
    m_map = {1: 0.08, 2: 0.06, 3: 0.04, 4: 0.025, 5: 0.015}
    alpha_map = {1: 1.2, 2: 1.3, 3: 1.6, 4: 2.0, 5: 2.5}
    
    m = m_map.get(credit_tier, 0.04)
    alpha = alpha_map.get(credit_tier, 1.6)
    beta = 10.0
    
    fraction = float(rng.beta(alpha, beta))
    income_safe = max(float(features.get('income', 0.0)), 0.0)
    value = income_safe * m * fraction
    
    return max(value, 0.0)


def _sample_student_loans(rng: np.random.Generator, features: Dict[str, Any]) -> float:
    """Sample student loan balance."""
    education = features.get('education', '')
    age = features['age']
    
    # infer college attendance
    edu_str = str(education) if education is not None else ''
    has_college = ('College' in edu_str) or ('Bachelor' in edu_str) or ('Graduate' in edu_str)
    
    p_stud = 0.18 if has_college else 0.05
    
    if rng.random() > p_stud:
        return 0.0
    
    # sample from gamma
    value = float(rng.gamma(2.2, 12000))
    
    # reduce for older individuals
    if age > 50:
        value *= 0.5
    
    return max(value, 0.0)


def _sample_other_debt(rng: np.random.Generator) -> float:
    """Sample other debt."""
    value = float(rng.lognormal(8.5, 0.9))
    return max(value, 0.0)


def _enforce_net_worth_constraint(
    rng: np.random.Generator,
    bs: Dict[str, Any],
    net_worth_bucket: str,
    *,
    target_net_worth: Optional[float] = None,
) -> Dict[str, Any]:
    """Ensure the balance sheet net worth remains within the indicated bucket."""
    lower_bound, upper_bound = _parse_net_worth_bounds(net_worth_bucket)

    if lower_bound is not None and bs['netWorth'] < lower_bound:
        _boost_liquid_assets(bs, lower_bound - bs['netWorth'])

    if upper_bound is not None and bs['netWorth'] > upper_bound:
        _trim_assets(bs, bs['netWorth'] - upper_bound)

    if target_net_worth is not None and bs['netWorth'] > 0:
        # fine-tune to stay close to the target (minor correction)
        diff_ratio = abs(bs['netWorth'] - target_net_worth) / max(target_net_worth, 1.0)
        if diff_ratio > 0.08:
            bs = _align_balance_sheet_to_target(bs, target_net_worth)

    return bs


def _parse_net_worth_bounds(bucket: str) -> Tuple[Optional[float], Optional[float]]:
    """Return (lower, upper) bounds inferred from the bucket label."""
    if not bucket:
        return None, None

    greater_match = re.search(r'Greater than \$?([\d,]+)', bucket, re.IGNORECASE)
    if greater_match:
        amount = _safe_parse_dollar(greater_match.group(1))
        return (amount + 1.0) if amount is not None else None, None

    range_match = re.search(r'\$?([\d,]+)\s*-\s*\$?([\d,]+)', bucket)
    if range_match:
        lower = _safe_parse_dollar(range_match.group(1))
        upper = _safe_parse_dollar(range_match.group(2))
        return lower, upper

    less_match = re.search(r'Less than \$?([\d,]+)', bucket, re.IGNORECASE)
    if less_match:
        upper = _safe_parse_dollar(less_match.group(1))
        return None, upper

    return None, None


# ============================================================================
# Database Insertion
# ============================================================================

def _insert_balance_sheet(sim_mgr, bs: Dict[str, Any]) -> None:
    """Insert balance sheet row into database."""
    query = f"""
        INSERT IGNORE INTO {sim_mgr._format_table('household_balance_sheet_samples')}
        (
            simulation_id, household_id, sim_clock_datetime,
            net_worth_bucket, hpi_level, hpi_place_id, vehicle_lambda_decay,
            primaryHomeValue, secondaryREValue, retirementAccounts, taxableInvestments,
            liquidSavings, vehiclesValue, durablesOther,
            mortgageBalance, autoLoans, creditCardRevolving, studentLoans, otherDebt,
            assetsTotal, liabilitiesTotal, netWorth
        )
        VALUES (
            %s, %s, %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s,
            %s, %s, %s
        )
    """
    
    params = (
        bs['simulation_id'],
        bs['household_id'],
        bs['sim_clock_datetime'],
        bs['net_worth_bucket'],
        bs['hpi_level'],
        bs['hpi_place_id'],
        bs['vehicle_lambda_decay'],
        Decimal(str(round(bs['primaryHomeValue'], 2))),
        Decimal(str(round(bs['secondaryREValue'], 2))),
        Decimal(str(round(bs['retirementAccounts'], 2))),
        Decimal(str(round(bs['taxableInvestments'], 2))),
        Decimal(str(round(bs['liquidSavings'], 2))),
        Decimal(str(round(bs['vehiclesValue'], 2))),
        Decimal(str(round(bs['durablesOther'], 2))),
        Decimal(str(round(bs['mortgageBalance'], 2))),
        Decimal(str(round(bs['autoLoans'], 2))),
        Decimal(str(round(bs['creditCardRevolving'], 2))),
        Decimal(str(round(bs['studentLoans'], 2))),
        Decimal(str(round(bs['otherDebt'], 2))),
        Decimal(str(round(bs['assetsTotal'], 2))),
        Decimal(str(round(bs['liabilitiesTotal'], 2))),
        Decimal(str(round(bs['netWorth'], 2))),
    )
    
    result = sim_mgr.execute_query(query, params, fetch=False)
    
    if not result.success:
        logger.error(f"Failed to insert balance sheet: {result.error}")
        raise Exception(f"Failed to insert balance sheet: {result.error}")


# ============================================================================
# Helper Functions
# ============================================================================

def _sample_trunc_normal(
    rng: np.random.Generator,
    mean: float,
    std: float,
    lower: float,
    upper: float
) -> float:
    """Sample from truncated normal distribution."""
    a = (lower - mean) / std
    b = (upper - mean) / std
    value = float(stats.truncnorm.rvs(a, b, loc=mean, scale=std, random_state=rng))
    return np.clip(value, lower, upper)


def _to_int(value: Any, default: int = 0) -> int:
    """Safely convert to int, returning default on failure."""
    try:
        if value is None:
            return default
        return int(str(value).strip())
    except Exception:
        return default


def _to_float(value: Any, default: float = None) -> Optional[float]:
    """Safely convert to float, returning default on failure."""
    try:
        if value is None:
            return default
        return float(str(value).replace(',', '').strip())
    except Exception:
        return default


def _get_hpi_index_with_interpolation(
    index_by_quarter: Dict[Tuple[int, int], float],
    target_quarter: Tuple[int, int]
) -> Optional[float]:
    """
    Get HPI index for a target quarter with linear interpolation between nearest neighbors.
    If outside the known range, perform a conservative extrapolation using recent growth rate
    capped to reasonable bounds.
    """
    if target_quarter in index_by_quarter:
        return index_by_quarter[target_quarter]

    # prepare sorted quarters
    quarters = sorted(index_by_quarter.keys())  # sorted by (yr, period)
    if not quarters:
        return None

    # linearize quarter to scalar t = yr*4 + (period-1)
    def q_to_t(q: Tuple[int, int]) -> int:
        return q[0] * 4 + (q[1] - 1)

    t_values = [q_to_t(q) for q in quarters]
    x_values = [index_by_quarter[q] for q in quarters]

    t_target = q_to_t(target_quarter)

    # if inside the range, interpolate between neighbors
    if t_values[0] < t_target < t_values[-1]:
        # find right insertion point
        import bisect
        pos = bisect.bisect_left(t_values, t_target)
        t0, t1 = t_values[pos - 1], t_values[pos]
        x0, x1 = x_values[pos - 1], x_values[pos]
        if t1 == t0:
            return x0
        w = (t_target - t0) / (t1 - t0)
        return x0 + w * (x1 - x0)

    # extrapolation: use last 4 points to compute average quarterly growth rate
    # then project forward/backward, with conservative caps
    window = 4 if len(t_values) >= 4 else len(t_values)
    if window < 2:
        return x_values[-1] if t_target >= t_values[-1] else x_values[0]

    if t_target > t_values[-1]:
        # forward extrapolation from tail
        t_tail = t_values[-window:]
        x_tail = x_values[-window:]
        # compute log growth per quarter to stabilize
        growths = []
        for i in range(1, len(t_tail)):
            dt = t_tail[i] - t_tail[i - 1]
            if dt <= 0 or x_tail[i - 1] <= 0 or x_tail[i] <= 0:
                continue
            g = np.log(x_tail[i] / x_tail[i - 1]) / dt
            growths.append(g)
        gq = np.median(growths) if growths else 0.0
        # cap growth per quarter between [-0.01, 0.02] (~-4% to +8% annually)
        gq = float(np.clip(gq, -0.01, 0.02))
        dt_total = t_target - t_values[-1]
        return float(x_values[-1] * np.exp(gq * dt_total))
    else:
        # backward extrapolation from head
        t_head = t_values[:window]
        x_head = x_values[:window]
        growths = []
        for i in range(1, len(t_head)):
            dt = t_head[i] - t_head[i - 1]
            if dt <= 0 or x_head[i - 1] <= 0 or x_head[i] <= 0:
                continue
            g = np.log(x_head[i] / x_head[i - 1]) / dt
            growths.append(g)
        gq = np.median(growths) if growths else 0.0
        gq = float(np.clip(gq, -0.01, 0.02))
        dt_total = t_values[0] - t_target
        return float(x_values[0] / np.exp(gq * dt_total))
