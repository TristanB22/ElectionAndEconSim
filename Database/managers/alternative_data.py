#!/usr/bin/env python3
"""
Alternative Data Database Manager

Provides simple helpers for inserting FHFA HPI data into
world_sim_alternative_data.hpi_data (see schema 12_alternative_data.sql).
"""

from __future__ import annotations

import logging
import os
from typing import Dict, List, Any, Tuple, Optional, Iterable

from .base import BaseDatabaseManager


logger = logging.getLogger(__name__)


class AlternativeDataDatabaseManager(BaseDatabaseManager):
    """
    Specialized manager for the alternative data database.
    Also handles BLS (Bureau of Labor Statistics) data.
    """

    _db_name = os.getenv('DB_ALT_NAME', 'world_sim_alternative_data')

    def truncate_hpi(self) -> bool:
        """Delete all rows from hpi_data."""
        query = f"DELETE FROM {self._format_table('hpi_data')}"
        result = self.execute_query(query, fetch=False)
        return result.success

    def insert_hpi_rows(self, rows: List[Dict[str, Any]]) -> bool:
        """Bulk insert HPI rows."""
        if not rows:
            return True

        query = (
            f"INSERT INTO {self._format_table('hpi_data')} ("
            "hpi_type, hpi_flavor, frequency, level, place_name, place_id, yr, period, index_nsa, index_sa"
            ") VALUES ("
            "%s, %s, %s, %s, %s, %s, %s, %s, %s, %s"
            ")"
        )

        params_list: List[Tuple] = []
        for r in rows:
            params_list.append((
                r.get('hpi_type'),
                r.get('hpi_flavor'),
                r.get('frequency'),
                r.get('level'),
                r.get('place_name'),
                r.get('place_id'),
                int(r.get('yr')) if r.get('yr') is not None else None,
                int(r.get('period')) if r.get('period') is not None else None,
                float(r.get('index_nsa')) if r.get('index_nsa') is not None else None,
                float(r.get('index_sa')) if r.get('index_sa') is not None else None,
            ))

        result = self.execute_many(query, params_list)
        return result.success

    # ---------------------------------------------------------------------
    # Census support (world_sim_census)
    # ---------------------------------------------------------------------
    def get_census_code_rows(self) -> List[Dict[str, Any]]:
        """Fetch all census code rows from world_sim_census.code_to_db."""
        query = (
            "SELECT code, db_description, link_type, created_at, updated_at "
            "FROM world_sim_census.code_to_db ORDER BY code"
        )
        result = self.execute_query(query, fetch=True)
        if not result.success:
            return []
        return result.data

    def upsert_census_metadata(self, rows: List[Dict[str, Any]]) -> Tuple[bool, str]:
        """
        Bulk upsert census variable metadata into world_sim_census.census_columns.

        Expected keys per row:
          census_code, year, var_code, column_label, column_concept,
          predicate_type, group_code, limit_value, predicate_only
        
        Returns:
            (success: bool, error_message: str)
            If success is False, error_message contains details about the failing row
        """
        if not rows:
            return True, ""

        query = (
            "INSERT INTO world_sim_census.census_columns ("
            "census_code, year, var_code, column_label, column_concept, predicate_type, "
            "group_code, limit_value, predicate_only"
            ") VALUES ("
            "%s, %s, %s, %s, %s, %s, %s, %s, %s"
            ") ON DUPLICATE KEY UPDATE "
            "column_label = VALUES(column_label), "
            "column_concept = VALUES(column_concept), "
            "predicate_type = VALUES(predicate_type), "
            "group_code = VALUES(group_code), "
            "limit_value = VALUES(limit_value), "
            "predicate_only = VALUES(predicate_only), "
            "updated_at = CURRENT_TIMESTAMP"
        )

        params_list: List[Tuple] = []
        for r in rows:
            params_list.append((
                r.get('census_code'),
                int(r.get('year')) if r.get('year') is not None else None,
                r.get('var_code'),
                r.get('column_label'),
                r.get('column_concept'),
                r.get('predicate_type'),
                r.get('group_code'),
                int(r.get('limit_value')) if r.get('limit_value') is not None else 0,
                bool(r.get('predicate_only')),
            ))

        result = self.execute_many(query, params_list)
        if result.success:
            return True, ""

        # Bulk insert failed: fall back to per-row upserts, inserting what we can
        bulk_error_msg = result.error or "Unknown error"
        failures: List[Dict[str, Any]] = []
        inserted_count = 0

        for idx, row in enumerate(rows):
            single_params = params_list[idx]
            single_result = self.execute_query(query, single_params, fetch=False)
            if single_result.success:
                inserted_count += 1
                continue

            failures.append({
                'index': idx,
                'var_code': row.get('var_code', 'unknown'),
                'census_code': row.get('census_code', 'unknown'),
                'year': row.get('year', 'unknown'),
                'group_code': row.get('group_code', 'unknown'),
                'group_code_length': len(str(row.get('group_code', ''))),
                'error': single_result.error or 'Unknown error',
                'column_label': str(row.get('column_label', ''))[:100] if row.get('column_label') else None,
                'column_concept': str(row.get('column_concept', '')),
                'column_concept_length': len(str(row.get('column_concept', '')))
            })

        if failures:
            # Build concise report (show first few failing rows)
            sample = failures[:5]
            details = []
            for f in sample:
                details.append(
                    "  Failing row "
                    f"{f['index']} var_code={f['var_code']} group={f['group_code']} "
                    f"len(concept)={f['column_concept_length']}\n"
                    f"    column_label: {f['column_label']}\n"
                    f"    column_concept (truncated 200): {f['column_concept'][:200]}\n"
                    f"    error: {f['error']}"
                )
            
            more = "" if len(failures) <= 5 else f"  ... and {len(failures) - 5} more failures"
            error_details = (
                f"Bulk upsert failed: {bulk_error_msg}\n"
                f"Inserted {inserted_count} of {len(rows)} rows. {len(failures)} failed.\n" +
                "\n".join(details) + ("\n" + more if more else "")
            )
            # Return False so caller can log/report, but partial success occurred
            return False, error_details

        # No failures means success after fallback
        return True, ""


    # ---------------------------------------------------------------------
    # CBSA/County Crosswalk (world_sim_alternative_data.metro_county_info)
    # ---------------------------------------------------------------------
    def truncate_metro_county_info(self) -> bool:
        """Delete all rows from metro_county_info."""
        query = f"DELETE FROM {self._format_table('metro_county_info')}"
        result = self.execute_query(query, fetch=False)
        return result.success

    def upsert_metro_county_info(self, rows: List[Dict[str, Any]]) -> Tuple[bool, str]:
        """
        Bulk upsert rows into world_sim_alternative_data.metro_county_info.

        Expected keys per row (match table columns):
          cbsa_code, metropolitandivisioncode, csacode, cbsa_title,
          metropolitanmicropolitanstatis, metropolitandivisiontitle, csatitle,
          countycountyequivalent, statename, fipsstatecode, fipscountycode,
          centraloutlyingcounty

        Returns: (success, error_message)
        """
        if not rows:
            return True, ""

        query = (
            f"INSERT INTO {self._format_table('metro_county_info')} ("
            "cbsa_code, metropolitandivisioncode, csacode, cbsa_title, "
            "metropolitanmicropolitanstatis, metropolitandivisiontitle, csatitle, "
            "countycountyequivalent, statename, fipsstatecode, fipscountycode, centraloutlyingcounty"
            ") VALUES ("
            "%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s"
            ") ON DUPLICATE KEY UPDATE "
            "metropolitandivisioncode = VALUES(metropolitandivisioncode), "
            "csacode = VALUES(csacode), "
            "cbsa_title = VALUES(cbsa_title), "
            "metropolitanmicropolitanstatis = VALUES(metropolitanmicropolitanstatis), "
            "metropolitandivisiontitle = VALUES(metropolitandivisiontitle), "
            "csatitle = VALUES(csatitle), "
            "countycountyequivalent = VALUES(countycountyequivalent), "
            "statename = VALUES(statename), "
            "fipsstatecode = VALUES(fipsstatecode), "
            "centraloutlyingcounty = VALUES(centraloutlyingcounty)"
        )

        params_list: List[Tuple] = []
        for r in rows:
            params_list.append((
                (int(r.get('cbsa_code')) if r.get('cbsa_code') not in (None, '') else None),
                (int(r.get('metropolitandivisioncode')) if r.get('metropolitandivisioncode') not in (None, '') else None),
                (int(r.get('csacode')) if r.get('csacode') not in (None, '') else None),
                r.get('cbsa_title', ''),
                r.get('metropolitanmicropolitanstatis', ''),
                r.get('metropolitandivisiontitle', ''),
                r.get('csatitle', ''),
                r.get('countycountyequivalent', ''),
                r.get('statename', ''),
                (int(r.get('fipsstatecode')) if r.get('fipsstatecode') not in (None, '') else None),
                (int(r.get('fipscountycode')) if r.get('fipscountycode') not in (None, '') else None),
                r.get('centraloutlyingcounty', ''),
            ))

        result = self.execute_many(query, params_list)
        if result.success:
            return True, ""

        # Fallback to identify a failing row
        error_msg = result.error or "Unknown error"
        for idx, r in enumerate(rows):
            single_params = params_list[idx]
            single_result = self.execute_query(query, single_params, fetch=False)
            if not single_result.success:
                failing = {
                    'index': idx,
                    'cbsa_code': r.get('cbsa_code'),
                    'fipscountycode': r.get('fipscountycode'),
                    'error': single_result.error or 'Unknown error',
                }
                return False, (
                    f"Bulk upsert failed: {error_msg}\n"
                    f"  First failing row at index {failing['index']} (cbsa_code={failing['cbsa_code']}, "
                    f"fipscountycode={failing['fipscountycode']}): {failing['error']}"
                )

        return False, error_msg

    # ---------------------------------------------------------------------
    # ACS PUMS Housing (world_sim_census.pums_h)
    # ---------------------------------------------------------------------
    def truncate_pums_h(self) -> bool:
        """Delete all rows from world_sim_census.pums_h."""
        query = "DELETE FROM world_sim_census.pums_h"
        result = self.execute_query(query, fetch=False)
        return result.success

    def upsert_pums_h_rows(self, rows: List[Dict[str, Any]]) -> Tuple[bool, str]:
        """
        Bulk upsert harmonized housing records into world_sim_census.pums_h.
        
        Expected keys per row: year, RT, SERIALNO, and all columns from pums_h schema.
        Uses ON DUPLICATE KEY UPDATE on (year, SERIALNO).
        
        Returns: (success, error_message)
        """
        if not rows:
            return True, ""

        # Build column list from first row (all rows should have same structure)
        sample = rows[0]
        cols = sorted(sample.keys())
        
        placeholders = ", ".join(["%s"] * len(cols))
        col_list = ", ".join(cols)
        
        # ON DUPLICATE KEY UPDATE: update all non-key columns
        # Keys are (year, SERIALNO), so update everything else
        update_clauses = []
        for c in cols:
            if c not in ('year', 'SERIALNO'):
                update_clauses.append(f"{c} = VALUES({c})")
        update_clause = ", ".join(update_clauses)
        
        query = (
            f"INSERT INTO world_sim_census.pums_h ({col_list}) "
            f"VALUES ({placeholders}) "
            f"ON DUPLICATE KEY UPDATE {update_clause}"
        )
        
        params_list: List[Tuple] = []
        for r in rows:
            params_list.append(tuple(r.get(c) for c in cols))
        
        result = self.execute_many(query, params_list)
        if result.success:
            return True, ""
        
        # Fallback: try one-by-one to identify failing row
        error_msg = result.error or "Unknown error"
        for idx, r in enumerate(rows):
            single_params = tuple(r.get(c) for c in cols)
            single_result = self.execute_query(query, single_params, fetch=False)
            if not single_result.success:
                failing = {
                    'index': idx,
                    'year': r.get('year'),
                    'SERIALNO': r.get('SERIALNO'),
                    'error': single_result.error or 'Unknown error',
                }
                return False, (
                    f"Bulk upsert failed: {error_msg}\n"
                    f"  First failing row at index {failing['index']} (year={failing['year']}, "
                    f"SERIALNO={failing['SERIALNO']}): {failing['error']}"
                )
        
        return False, error_msg

    # ---------------------------------------------------------------------
    # ACS PUMS Person (world_sim_census.pums_p)
    # ---------------------------------------------------------------------
    def truncate_pums_p(self) -> bool:
        """Delete all rows from world_sim_census.pums_p."""
        query = "DELETE FROM world_sim_census.pums_p"
        result = self.execute_query(query, fetch=False)
        return result.success

    def upsert_pums_p_rows(self, rows: List[Dict[str, Any]]) -> Tuple[bool, str]:
        """
        Bulk upsert harmonized person records into world_sim_census.pums_p.
        
        Expected keys per row: year, RT, SERIALNO, SPORDER, and all columns from pums_p schema.
        Uses ON DUPLICATE KEY UPDATE on (year, SERIALNO, SPORDER).
        
        Returns: (success, error_message)
        """
        if not rows:
            return True, ""

        # Build column list from first row
        sample = rows[0]
        cols = sorted(sample.keys())
        
        placeholders = ", ".join(["%s"] * len(cols))
        col_list = ", ".join(cols)
        
        # ON DUPLICATE KEY UPDATE: update all non-key columns
        # Keys are (year, SERIALNO, SPORDER)
        update_clauses = []
        for c in cols:
            if c not in ('year', 'SERIALNO', 'SPORDER'):
                update_clauses.append(f"{c} = VALUES({c})")
        update_clause = ", ".join(update_clauses)
        
        query = (
            f"INSERT INTO world_sim_census.pums_p ({col_list}) "
            f"VALUES ({placeholders}) "
            f"ON DUPLICATE KEY UPDATE {update_clause}"
        )
        
        params_list: List[Tuple] = []
        for r in rows:
            params_list.append(tuple(r.get(c) for c in cols))
        
        result = self.execute_many(query, params_list)
        if result.success:
            return True, ""
        
        # Fallback: try one-by-one to identify failing row
        error_msg = result.error or "Unknown error"
        for idx, r in enumerate(rows):
            single_params = tuple(r.get(c) for c in cols)
            single_result = self.execute_query(query, single_params, fetch=False)
            if not single_result.success:
                failing = {
                    'index': idx,
                    'year': r.get('year'),
                    'SERIALNO': r.get('SERIALNO'),
                    'SPORDER': r.get('SPORDER'),
                    'error': single_result.error or 'Unknown error',
                }
                return False, (
                    f"Bulk upsert failed: {error_msg}\n"
                    f"  First failing row at index {failing['index']} (year={failing['year']}, "
                    f"SERIALNO={failing['SERIALNO']}, SPORDER={failing['SPORDER']}): {failing['error']}"
                )
        
        return False, error_msg

    def upsert_census_data_rows(self, rows: List[Dict[str, Any]]) -> Tuple[bool, str]:
        """
        Bulk upsert census data into world_sim_census.census_data.

        Expected keys per row:
          census_code, year, var_code, geo_id, geo_name, geo_state, geo_county,
          estimated_value, moe
        
        Returns:
            (success: bool, error_message: str)
            If success is False, error_message contains details about the failing row
        """
        if not rows:
            return True, ""

        query = (
            "INSERT INTO world_sim_census.census_data ("
            "census_code, year, var_code, geo_id, geo_name, geo_state, geo_county, "
            "estimated_value, moe"
            ") VALUES ("
            "%s, %s, %s, %s, %s, %s, %s, %s, %s"
            ") ON DUPLICATE KEY UPDATE "
            "geo_name = VALUES(geo_name), "
            "geo_state = VALUES(geo_state), "
            "geo_county = VALUES(geo_county), "
            "estimated_value = VALUES(estimated_value), "
            "moe = VALUES(moe), "
            "updated_at = CURRENT_TIMESTAMP"
        )

        params_list: List[Tuple] = []
        for r in rows:
            params_list.append((
                r.get('census_code'),
                r.get('year'),
                r.get('var_code'),
                r.get('geo_id'),
                r.get('geo_name'),
                r.get('geo_state'),
                r.get('geo_county'),
                r.get('estimated_value'),
                r.get('moe')
            ))
        
        result = self.execute_many(query, params_list)
        if result.success:
            return True, ""
        
        # Fallback: try one-by-one to identify failing row
        error_msg = result.error or "Unknown error"
        for idx, r in enumerate(rows):
            single_params = (
                r.get('census_code'),
                r.get('year'),
                r.get('var_code'),
                r.get('geo_id'),
                r.get('geo_name'),
                r.get('geo_state'),
                r.get('geo_county'),
                r.get('estimated_value'),
                r.get('moe')
            )
            single_result = self.execute_query(query, single_params, fetch=False)
            if not single_result.success:
                failing = {
                    'index': idx,
                    'census_code': r.get('census_code'),
                    'year': r.get('year'),
                    'var_code': r.get('var_code'),
                    'geo_id': r.get('geo_id'),
                    'error': single_result.error or 'Unknown error',
                }
                return False, (
                    f"Bulk upsert failed: {error_msg}\n"
                    f"  First failing row at index {failing['index']} (code={failing['census_code']}, "
                    f"year={failing['year']}, var={failing['var_code']}, geo={failing['geo_id']}): {failing['error']}"
                )
        
        return False, error_msg

    # ------------------------------------------------------------------
    # Calibration helpers (ACS aggregations by CBSA)
    # ------------------------------------------------------------------
    def get_census_columns_map(self, census_code: str) -> Dict[str, str]:
        """Return mapping of var_code -> column_label for a census table."""
        query = (
            "SELECT var_code, column_label FROM world_sim_census.census_columns "
            "WHERE census_code = %s AND predicate_only = 0 ORDER BY year DESC"
        )
        result = self.execute_query(query, (census_code,), fetch=True)
        if not result.success or not result.data:
            return {}
        mapping: Dict[str, str] = {}
        for row in result.data:
            var_code = row.get('var_code')
            label = row.get('column_label')
            if not var_code or not label:
                continue
            # Preserve first occurrence (latest year first due to ORDER BY year DESC)
            if var_code not in mapping:
                mapping[var_code] = label
        return mapping

    def fetch_census_aggregates(
        self,
        year: int,
        cbsa_code: int,
        census_code: str,
        var_codes: Iterable[str],
        *,
        require_full_coverage: bool = False,
    ) -> Dict[str, float]:
        """
        Sum census estimated values for the provided var_codes across a CBSA.

        Args:
            year: ACS year
            cbsa_code: CBSA identifier from metro_county_info
            census_code: ACS table/group code (e.g., B25003)
            var_codes: Iterable of variable codes within the table to aggregate
            require_full_coverage: When True, emit a warning if not all counties
                in the CBSA have data for the requested vars.
        """
        var_list = list(dict.fromkeys(var_codes))
        if not var_list:
            return {}

        aggregates = self.fetch_census_aggregates_by_scope(
            year=year,
            census_code=census_code,
            var_codes=var_list,
            scope='cbsa',
            scope_value=cbsa_code,
        )

        if require_full_coverage:
            expected = self.get_cbsa_county_count(cbsa_code)
            if expected:
                observed = self.get_cbsa_observed_count(
                    year=year,
                    cbsa_code=cbsa_code,
                    census_code=census_code,
                    var_codes=var_list,
                )
                if observed < expected:
                    logger.warning(
                        "ACS coverage gap for CBSA %s (%s): expected %s counties, observed %s for %s %s",
                        cbsa_code,
                        census_code,
                        expected,
                        observed,
                        census_code,
                        ",".join(var_list),
                    )

        return {vc: float(aggregates.get(vc, 0.0) or 0.0) for vc in var_list}

    def fetch_census_aggregates_by_scope(
        self,
        year: int,
        census_code: str,
        var_codes: Iterable[str],
        *,
        scope: str,
        scope_value: Optional[Any] = None,
    ) -> Dict[str, float]:
        """
        Aggregate ACS values for the provided var_codes under a specific geography scope.

        Supported scopes:
            - 'cbsa': scope_value must be the CBSA code (int)
            - 'state': scope_value must be a 2-digit FIPS string
            - 'nation': scope_value ignored; aggregates across all counties
        """
        var_list = list(dict.fromkeys(var_codes))
        if not var_list:
            return {}

        placeholders = ", ".join(["%s"] * len(var_list))
        joins: List[str] = []
        conditions: List[str] = []
        params: List[Any] = []

        normalized_scope = scope.lower()
        if normalized_scope == 'cbsa':
            if scope_value is None:
                return {vc: 0.0 for vc in var_list}
            joins.append(
                "JOIN world_sim_alternative_data.metro_county_info mci "
                "  ON LPAD(mci.fipsstatecode, 2, '0') = cd.geo_state "
                " AND LPAD(mci.fipscountycode, 3, '0') = cd.geo_county"
            )
            conditions.append("mci.cbsa_code = %s")
            params.append(int(scope_value))
        elif normalized_scope == 'state':
            if scope_value is None:
                return {vc: 0.0 for vc in var_list}
            state_fips = str(scope_value).zfill(2)
            conditions.append("cd.geo_state = %s")
            params.append(state_fips)
        elif normalized_scope == 'nation':
            # no extra condition
            pass
        else:
            raise ValueError(f"Unsupported scope '{scope}' for census aggregation")

        conditions.append("cd.year = %s")
        params.append(int(year))
        conditions.append("cd.census_code = %s")
        params.append(census_code)

        where_clause = " AND ".join(conditions) if conditions else "1=1"
        query = (
            "SELECT cd.var_code, SUM(cd.estimated_value) AS total "
            "FROM world_sim_census.census_data cd "
            f"{' '.join(joins)} "
            f"WHERE {where_clause} "
            f"AND cd.var_code IN ({placeholders}) "
            "GROUP BY cd.var_code"
        )

        params.extend(var_list)
        result = self.execute_query(query, tuple(params), fetch=True)
        if not result.success or not result.data:
            return {vc: 0.0 for vc in var_list}

        aggregates: Dict[str, float] = {vc: 0.0 for vc in var_list}
        for row in result.data:
            vc = row.get('var_code')
            total = row.get('total')
            if vc in aggregates and total is not None:
                try:
                    aggregates[vc] = float(total)
                except (TypeError, ValueError):
                    aggregates[vc] = 0.0
        return aggregates

    def fetch_census_aggregates_state(
        self,
        year: int,
        state_fips: str,
        census_code: str,
        var_codes: Iterable[str],
    ) -> Dict[str, float]:
        """Aggregate ACS values for a specific state (2-digit FIPS)."""
        return self.fetch_census_aggregates_by_scope(
            year=year,
            census_code=census_code,
            var_codes=var_codes,
            scope='state',
            scope_value=state_fips,
        )

    def fetch_census_aggregates_nationwide(
        self,
        year: int,
        census_code: str,
        var_codes: Iterable[str],
    ) -> Dict[str, float]:
        """Aggregate ACS values across all counties nationwide."""
        return self.fetch_census_aggregates_by_scope(
            year=year,
            census_code=census_code,
            var_codes=var_codes,
            scope='nation',
        )

    def get_cbsa_county_count(self, cbsa_code: int) -> int:
        """Return number of distinct counties mapped to a CBSA in the crosswalk."""
        query = (
            "SELECT COUNT(DISTINCT CONCAT("
            "  LPAD(fipsstatecode, 2, '0'), LPAD(fipscountycode, 3, '0')"
            ")) AS cnt "
            f"FROM {self._format_table('metro_county_info')} "
            "WHERE cbsa_code = %s"
        )
        result = self.execute_query(query, (int(cbsa_code),), fetch=True)
        if not result.success or not result.data:
            return 0
        try:
            cnt = result.data[0].get('cnt')
            return int(cnt) if cnt is not None else 0
        except (TypeError, ValueError):
            return 0

    def get_cbsa_observed_count(
        self,
        year: int,
        cbsa_code: int,
        census_code: str,
        var_codes: Iterable[str],
    ) -> int:
        """Return number of distinct counties with ACS data for the CBSA/vars."""
        var_list = list(dict.fromkeys(var_codes))
        if not var_list:
            return 0

        placeholders = ", ".join(["%s"] * len(var_list))
        query = (
            "SELECT COUNT(DISTINCT CONCAT(cd.geo_state, cd.geo_county)) AS coverage "
            "FROM world_sim_census.census_data cd "
            "JOIN world_sim_alternative_data.metro_county_info mci "
            "  ON LPAD(mci.fipsstatecode, 2, '0') = cd.geo_state "
            " AND LPAD(mci.fipscountycode, 3, '0') = cd.geo_county "
            "WHERE mci.cbsa_code = %s "
            "  AND cd.year = %s "
            "  AND cd.census_code = %s "
            f"  AND cd.var_code IN ({placeholders})"
        )
        params: List[Any] = [int(cbsa_code), int(year), census_code]
        params.extend(var_list)

        result = self.execute_query(query, tuple(params), fetch=True)
        if not result.success or not result.data:
            return 0
        try:
            coverage = result.data[0].get('coverage')
            return int(coverage) if coverage is not None else 0
        except (TypeError, ValueError):
            return 0

    def fetch_census_total(
        self,
        year: int,
        cbsa_code: int,
        census_code: str,
        var_code: str,
    ) -> float:
        """Convenience wrapper to fetch a single aggregated value."""
        values = self.fetch_census_aggregates(year, cbsa_code, census_code, [var_code])
        return float(values.get(var_code, 0.0))

    def fetch_income_distribution(
        self,
        year: int,
        cbsa_code: int,
        census_code: str,
        income_var_codes: Iterable[str],
    ) -> Dict[str, float]:
        """Fetch income distribution counts for requested var_codes."""
        return self.fetch_census_aggregates(year, cbsa_code, census_code, income_var_codes)

    # ---------------------------------------------------------------------
    # BLS support (world_sim_bls)
    # ---------------------------------------------------------------------
    def truncate_bls_ap_area(self) -> bool:
        """Delete all rows from world_sim_bls.ap_area."""
        query = "DELETE FROM world_sim_bls.ap_area"
        result = self.execute_query(query, fetch=False)
        return result.success

    def truncate_bls_ap_item(self) -> bool:
        """Delete all rows from world_sim_bls.ap_item."""
        query = "DELETE FROM world_sim_bls.ap_item"
        result = self.execute_query(query, fetch=False)
        return result.success

    def truncate_bls_ap_series(self) -> bool:
        """Delete all rows from world_sim_bls.ap_series."""
        query = "DELETE FROM world_sim_bls.ap_series"
        result = self.execute_query(query, fetch=False)
        return result.success

    def truncate_bls_ap_data(self) -> bool:
        """Delete all rows from world_sim_bls.ap_data."""
        query = "DELETE FROM world_sim_bls.ap_data"
        result = self.execute_query(query, fetch=False)
        return result.success
    def upsert_bls_areas(self, rows: List[Dict[str, Any]]) -> Tuple[bool, str]:
        """
        Upsert BLS area reference data into world_sim_bls.ap_area.
        
        Args:
            rows: List of dicts with keys: area_code, area_name
            
        Returns:
            (success, error_message)
        """
        if not rows:
            return True, ""
        
        query = """
            INSERT INTO world_sim_bls.ap_area (area_code, area_name)
            VALUES (%s, %s)
            ON DUPLICATE KEY UPDATE
                area_name = VALUES(area_name)
        """
        
        params_list: List[Tuple] = []
        for r in rows:
            area_code = r.get('area_code', '').strip()
            area_name = r.get('area_name', '').strip()
            
            if not area_code or not area_name:
                continue
                
            params_list.append((area_code, area_name))
        
        if not params_list:
            return True, "No valid area rows to insert"
        
        result = self.execute_many(query, params_list)
        if not result.success:
            return False, f"Failed to upsert BLS areas: {result.error}"
        
        return True, ""
    
    def upsert_bls_items(self, rows: List[Dict[str, Any]]) -> Tuple[bool, str]:
        """
        Upsert BLS item reference data into world_sim_bls.ap_item.
        
        Args:
            rows: List of dicts with keys: item_code, item_name
            
        Returns:
            (success, error_message)
        """
        if not rows:
            return True, ""
        
        query = """
            INSERT INTO world_sim_bls.ap_item (item_code, item_name)
            VALUES (%s, %s)
            ON DUPLICATE KEY UPDATE
                item_name = VALUES(item_name)
        """
        
        params_list: List[Tuple] = []
        for r in rows:
            item_code = r.get('item_code', '').strip()
            item_name = r.get('item_name', '').strip()
            
            if not item_code or not item_name:
                continue
                
            params_list.append((item_code, item_name))
        
        if not params_list:
            return True, "No valid item rows to insert"
        
        result = self.execute_many(query, params_list)
        if not result.success:
            return False, f"Failed to upsert BLS items: {result.error}"
        
        return True, ""

    def upsert_bls_series(self, rows: List[Dict[str, Any]]) -> Tuple[bool, str]:
        """
        Upsert BLS series reference data into world_sim_bls.ap_series.
        
        Args:
            rows: List of dicts with keys: series_id, area_code, item_code,
                  series_title, footnote_codes, begin_year, begin_period,
                  end_year, end_period
        """
        if not rows:
            return True, ""

        query = (
            "INSERT INTO world_sim_bls.ap_series ("
            "series_id, area_code, item_code, series_title, footnote_codes, "
            "begin_year, begin_period, end_year, end_period"
            ") VALUES ("
            "%s, %s, %s, %s, %s, %s, %s, %s, %s"
            ") ON DUPLICATE KEY UPDATE "
            "area_code = VALUES(area_code), "
            "item_code = VALUES(item_code), "
            "series_title = VALUES(series_title), "
            "footnote_codes = VALUES(footnote_codes), "
            "begin_year = VALUES(begin_year), "
            "begin_period = VALUES(begin_period), "
            "end_year = VALUES(end_year), "
            "end_period = VALUES(end_period)"
        )

        params_list: List[Tuple] = []
        for r in rows:
            series_id = (r.get('series_id') or '').strip()
            area_code = (r.get('area_code') or '').strip()
            item_code = (r.get('item_code') or '').strip()
            series_title = (r.get('series_title') or '').strip()
            footnote_codes = (r.get('footnote_codes') or '').strip()
            begin_year = r.get('begin_year')
            begin_period = (r.get('begin_period') or '').strip()
            end_year = r.get('end_year')
            end_period = (r.get('end_period') or '').strip()

            if not series_id or not area_code or not item_code:
                continue

            try:
                by = int(begin_year) if begin_year not in (None, '') else None
            except ValueError:
                by = None
            try:
                ey = int(end_year) if end_year not in (None, '') else None
            except ValueError:
                ey = None

            params_list.append((
                series_id, area_code, item_code, series_title, footnote_codes,
                by, begin_period, ey, end_period
            ))

        if not params_list:
            return True, "No valid series rows to insert"

        result = self.execute_many(query, params_list)
        if not result.success:
            return False, f"Failed to upsert BLS series: {result.error}"
        return True, ""

    def upsert_bls_ap_data(self, rows: List[Dict[str, Any]]) -> Tuple[bool, str]:
        """
        Upsert BLS data rows into world_sim_bls.ap_data.
        Expected keys per row: series_id, area_code, item_code, year, period, value, footnotes
        """
        if not rows:
            return True, ""

        query = (
            "INSERT INTO world_sim_bls.ap_data ("
            "series_id, area_code, item_code, year, period, value, footnotes"
            ") VALUES ("
            "%s, %s, %s, %s, %s, %s, %s"
            ") ON DUPLICATE KEY UPDATE "
            "value = VALUES(value), footnotes = VALUES(footnotes)"
        )

        params_list: List[Tuple] = []
        for r in rows:
            series_id = (r.get('series_id') or '').strip()
            area_code = (r.get('area_code') or '').strip()
            item_code = (r.get('item_code') or '').strip()
            year = r.get('year')
            period = (r.get('period') or '').strip()
            value = r.get('value')
            footnotes = (r.get('footnotes') or '').strip()

            if not series_id or not area_code or not item_code or year in (None, '') or not period:
                continue

            try:
                yr = int(year)
            except ValueError:
                continue
            try:
                val = float(value) if value not in (None, '') else None
            except ValueError:
                val = None

            params_list.append((series_id, area_code, item_code, yr, period, val, footnotes))

        if not params_list:
            return True, "No valid ap_data rows to insert"

        result = self.execute_many(query, params_list)
        if not result.success:
            return False, f"Failed to upsert BLS ap_data: {result.error}"
        return True, ""



def get_alternative_data_manager() -> AlternativeDataDatabaseManager:
    """Singleton accessor."""
    return AlternativeDataDatabaseManager.get_singleton()
