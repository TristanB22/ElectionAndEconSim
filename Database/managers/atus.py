#!/usr/bin/env python3
"""
ATUS (American Time Use Survey) Database Manager

Provides helpers for inserting ATUS data into world_sim_atus tables.
"""

from __future__ import annotations

import logging
import os
from typing import Dict, List, Any, Tuple
import json

from .base import BaseDatabaseManager

logger = logging.getLogger(__name__)


class ATUSDatabaseManager(BaseDatabaseManager):
    """
    Specialized manager for the ATUS database (world_sim_atus).
    """

    _db_name = os.getenv('DB_ATUS_NAME', 'world_sim_atus')

    # =========================================================================
    # TRUNCATE methods
    # =========================================================================
    
    def truncate_case_id(self) -> bool:
        """Clear case_id table."""
        query = "DELETE FROM world_sim_atus.case_id"
        result = self.execute_query(query, fetch=False)
        return result.success

    def truncate_atuscase(self) -> bool:
        """Clear atuscase table."""
        query = "DELETE FROM world_sim_atus.atuscase"
        result = self.execute_query(query, fetch=False)
        return result.success

    def truncate_cps(self) -> bool:
        """Clear cps table."""
        query = "DELETE FROM world_sim_atus.cps"
        result = self.execute_query(query, fetch=False)
        return result.success

    def truncate_resp(self) -> bool:
        """Clear resp table."""
        query = "DELETE FROM world_sim_atus.resp"
        result = self.execute_query(query, fetch=False)
        return result.success

    def truncate_rost(self) -> bool:
        """Clear rost table."""
        query = "DELETE FROM world_sim_atus.rost"
        result = self.execute_query(query, fetch=False)
        return result.success

    def truncate_rostec(self) -> bool:
        """Clear rostec table."""
        query = "DELETE FROM world_sim_atus.rostec"
        result = self.execute_query(query, fetch=False)
        return result.success

    def truncate_atusact(self) -> bool:
        """Clear atusact table."""
        query = "DELETE FROM world_sim_atus.atusact"
        result = self.execute_query(query, fetch=False)
        return result.success

    def truncate_who(self) -> bool:
        """Clear who table."""
        query = "DELETE FROM world_sim_atus.who"
        result = self.execute_query(query, fetch=False)
        return result.success

    def truncate_weights(self) -> bool:
        """Clear weights table."""
        query = "DELETE FROM world_sim_atus.weights"
        result = self.execute_query(query, fetch=False)
        return result.success

    def truncate_sum(self) -> bool:
        """Clear sum table."""
        query = "DELETE FROM world_sim_atus.sum"
        result = self.execute_query(query, fetch=False)
        return result.success

    def clear_model_tables(self) -> None:
        """
        Clear derived model tables that support activity planning.
        """
        tables = [
            "weekly_presence",
            "social_where",
            "transitions",
            "duration_stats",
            "hourly_mix",
            "operator_map",
            "case_stratum",
            "strata_def",
        ]
        for table in tables:
            self.execute_query(f"DELETE FROM world_sim_atus.{table}", fetch=False)

    # =========================================================================
    # INSERT methods
    # =========================================================================

    def _execute_many_adaptive(self, query: str, params_list: List[Tuple[Any, ...]], table_name: str) -> Tuple[bool, str]:
        """
        Execute many with adaptive batch sizing to avoid max_allowed_packet errors.

        Strategy:
        - Start with DB_INSERT_BATCH_SIZE (or len(params_list) if smaller)
        - On MySQL error 1153 (packet too big), halve batch size and retry the current chunk
        - Continue until success or batch size < 10_000, then fail
        """
        if not params_list:
            return True, ""

        # Determine initial batch size from environment or default
        try:
            env_batch = int(os.getenv('DB_INSERT_BATCH_SIZE', '50000'))
        except Exception:
            env_batch = 50000
        batch_size = max(1, min(env_batch, len(params_list)))

        i = 0
        while i < len(params_list):
            # Ensure we don't overshoot the list
            current_batch = params_list[i:i + batch_size]

            result = self.execute_many(query, current_batch)
            if result.success:
                i += batch_size
                continue

            error_msg = (result.error or "").lower()
            # Detect max_allowed_packet error (1153) and adapt
            if 'max_allowed_packet' in error_msg or '1153' in error_msg:
                # Halve the batch size and retry the same range
                new_batch_size = batch_size // 2
                logger.warning(
                    f"Batch insert into {table_name} failed due to max_allowed_packet with size={batch_size}. "
                    f"Retrying with size={new_batch_size}"
                )
                # Lower threshold for wide tables - weights has 161 columns, needs smaller batches
                min_threshold = 100 if 'weights' in table_name.lower() else 1000
                if new_batch_size < min_threshold:
                    return False, result.error or f"Batch size fell below {min_threshold} while adapting to max_allowed_packet"
                batch_size = new_batch_size
                continue  # retry with smaller batch at same index

            # For other errors, fail fast
            return False, result.error or "Unknown error during batch insert"

        return True, ""

    def insert_case_id_rows(self, rows: List[Dict[str, Any]]) -> Tuple[bool, str]:
        """
        Bulk insert case_id rows.
        Expected keys: TUCASEID, GEMETSTA, GTMETSTA, PEEDUCA, PEHSPNON, PTDTRACE,
                       TEAGE, TELFS, TEMJOT, TESCHENR, TESCHLVL, TESEX, TESPEMPNOT,
                       TRCHILDNUM, TRDPFTPT, TRERNWA, TRHOLIDAY, TRSPFTPT, TRSPPRES,
                       TRYHHCHILD, TUDIARYDAY, TUFNWGTP, TEHRUSLT, TUYEAR, TU20FWGT
        """
        if not rows:
            return True, ""

        query = """
            INSERT IGNORE INTO world_sim_atus.case_id (
                TUCASEID, GEMETSTA, GTMETSTA, PEEDUCA, PEHSPNON, PTDTRACE,
                TEAGE, TELFS, TEMJOT, TESCHENR, TESCHLVL, TESEX, TESPEMPNOT,
                TRCHILDNUM, TRDPFTPT, TRERNWA, TRHOLIDAY, TRSPFTPT, TRSPPRES,
                TRYHHCHILD, TUDIARYDAY, TUFNWGTP, TEHRUSLT, TUYEAR, TU20FWGT
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
        """

        params_list = []
        for r in rows:
            params_list.append((
                r.get('TUCASEID'),
                r.get('GEMETSTA'), r.get('GTMETSTA'), r.get('PEEDUCA'), r.get('PEHSPNON'),
                r.get('PTDTRACE'), r.get('TEAGE'), r.get('TELFS'), r.get('TEMJOT'),
                r.get('TESCHENR'), r.get('TESCHLVL'), r.get('TESEX'), r.get('TESPEMPNOT'),
                r.get('TRCHILDNUM'), r.get('TRDPFTPT'), r.get('TRERNWA'), r.get('TRHOLIDAY'),
                r.get('TRSPFTPT'), r.get('TRSPPRES'), r.get('TRYHHCHILD'), r.get('TUDIARYDAY'),
                r.get('TUFNWGTP'), r.get('TEHRUSLT'), r.get('TUYEAR'), r.get('TU20FWGT')
            ))

        return self._execute_many_adaptive(query, params_list, table_name='case_id')

    def insert_atuscase_rows(self, rows: List[Dict[str, Any]]) -> Tuple[bool, str]:
        """Bulk insert atuscase rows."""
        if not rows:
            return True, ""

        query = """
            INSERT IGNORE INTO world_sim_atus.atuscase (
                TUCASEID, TR1INTST, TR2INTST, TRFNLOUT, TRINCEN2, TUAVGDUR,
                TUA_ID, TUCPSDP, TUC_ID, TUDQUAL2, TUINCENT, TUINTDQUAL,
                TUINTID, TUINTRODATE, TUINTROPANMONTH, TUINTROPANYEAR,
                TULNGSKL, TUTOTACTNO, TUV_ID
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
        """

        params_list = []
        for r in rows:
            params_list.append((
                r.get('TUCASEID'), r.get('TR1INTST'), r.get('TR2INTST'), r.get('TRFNLOUT'),
                r.get('TRINCEN2'), r.get('TUAVGDUR'), r.get('TUA_ID'), r.get('TUCPSDP'),
                r.get('TUC_ID'), r.get('TUDQUAL2'), r.get('TUINCENT'), r.get('TUINTDQUAL'),
                r.get('TUINTID'), r.get('TUINTRODATE'), r.get('TUINTROPANMONTH'),
                r.get('TUINTROPANYEAR'), r.get('TULNGSKL'), r.get('TUTOTACTNO'), r.get('TUV_ID')
            ))

        return self._execute_many_adaptive(query, params_list, table_name='atuscase')

    def insert_rost_rows(self, rows: List[Dict[str, Any]]) -> Tuple[bool, str]:
        """Bulk insert rost (household roster) rows."""
        if not rows:
            return True, ""

        query = """
            INSERT IGNORE INTO world_sim_atus.rost (
                TUCASEID, TULINENO, TERRP, TEAGE, TESEX
            ) VALUES (%s, %s, %s, %s, %s)
        """

        params_list = []
        for r in rows:
            params_list.append((
                r.get('TUCASEID'), r.get('TULINENO'), r.get('TERRP'),
                r.get('TEAGE'), r.get('TESEX')
            ))

        return self._execute_many_adaptive(query, params_list, table_name='rost')

    def insert_rostec_rows(self, rows: List[Dict[str, Any]]) -> Tuple[bool, str]:
        """Bulk insert rostec (elder care roster) rows."""
        if not rows:
            return True, ""

        query = """
            INSERT IGNORE INTO world_sim_atus.rostec (
                TUCASEID, TUECLNO, TULINENO, TEAGE_EC, TEELDUR,
                TEELWHO, TEELYRS, TRELHH
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """

        params_list = []
        for r in rows:
            params_list.append((
                r.get('TUCASEID'), r.get('TUECLNO'), r.get('TULINENO'),
                r.get('TEAGE_EC'), r.get('TEELDUR'), r.get('TEELWHO'),
                r.get('TEELYRS'), r.get('TRELHH')
            ))

        return self._execute_many_adaptive(query, params_list, table_name='rostec')

    def insert_atusact_rows(self, rows: List[Dict[str, Any]]) -> Tuple[bool, str]:
        """Bulk insert atusact (activity) rows."""
        if not rows:
            return True, ""

        query = """
            INSERT IGNORE INTO world_sim_atus.atusact (
                TUCASEID, TUACTIVITY_N, TUACTDUR24, TUCC5, TUCC5B, TRTCCTOT_LN,
                TRTCC_LN, TRTCOC_LN, TUSTARTTIM, TUSTOPTIME, TRCODEP, TRTIER1P,
                TRTIER2P, TUCC8, TUCUMDUR, TUCUMDUR24, TUACTDUR, TR_03CC57,
                TRTO_LN, TRTONHH_LN, TRTOHH_LN, TRTHH_LN, TRTNOHH_LN, TEWHERE,
                TUCC7, TRWBELIG, TRTEC_LN, TUEC24, TUDURSTOP
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
        """

        params_list = []
        for r in rows:
            params_list.append((
                r.get('TUCASEID'), r.get('TUACTIVITY_N'), r.get('TUACTDUR24'),
                r.get('TUCC5'), r.get('TUCC5B'), r.get('TRTCCTOT_LN'), r.get('TRTCC_LN'),
                r.get('TRTCOC_LN'), r.get('TUSTARTTIM'), r.get('TUSTOPTIME'),
                r.get('TRCODEP'), r.get('TRTIER1P'), r.get('TRTIER2P'), r.get('TUCC8'),
                r.get('TUCUMDUR'), r.get('TUCUMDUR24'), r.get('TUACTDUR'), r.get('TR_03CC57'),
                r.get('TRTO_LN'), r.get('TRTONHH_LN'), r.get('TRTOHH_LN'), r.get('TRTHH_LN'),
                r.get('TRTNOHH_LN'), r.get('TEWHERE'), r.get('TUCC7'), r.get('TRWBELIG'),
                r.get('TRTEC_LN'), r.get('TUEC24'), r.get('TUDURSTOP')
            ))

        return self._execute_many_adaptive(query, params_list, table_name='atusact')

    def insert_who_rows(self, rows: List[Dict[str, Any]]) -> Tuple[bool, str]:
        """Bulk insert who ("who was with you") rows."""
        if not rows:
            return True, ""

        query = """
            INSERT IGNORE INTO world_sim_atus.who (
                TUCASEID, TULINENO, TUACTIVITY_N, TRWHONA, TUWHO_CODE
            ) VALUES (%s, %s, %s, %s, %s)
        """

        params_list = []
        for r in rows:
            params_list.append((
                r.get('TUCASEID'), r.get('TULINENO'), r.get('TUACTIVITY_N'),
                r.get('TRWHONA'), r.get('TUWHO_CODE')
            ))

        return self._execute_many_adaptive(query, params_list, table_name='who')

    def insert_weights_rows(self, rows: List[Dict[str, Any]]) -> Tuple[bool, str]:
        """
        Bulk insert weights rows (wide format).
        Expects a TUCASEID and 160 weight columns (TUFNWGTP001 to TUFNWGTP160).
        """
        if not rows:
            return True, ""

        # Dynamically generate column names and placeholders
        columns = ['TUCASEID'] + [f'TUFNWGTP{i:03d}' for i in range(1, 161)]
        column_names = ', '.join(columns)
        placeholders = ', '.join(['%s'] * len(columns))

        query = f"""
            INSERT IGNORE INTO world_sim_atus.weights ({column_names})
            VALUES ({placeholders})
        """

        params_list = []
        for r in rows:
            params_list.append(tuple(r.get(col) for col in columns))

        return self._execute_many_adaptive(query, params_list, table_name='weights')

    def insert_sum_rows(self, rows: List[Dict[str, Any]]) -> Tuple[bool, str]:
        """
        Bulk insert sum rows (normalized format).
        Expected keys: TUCASEID, activity_code, minutes
        """
        if not rows:
            return True, ""

        query = """
            INSERT IGNORE INTO world_sim_atus.sum (
                TUCASEID, activity_code, minutes
            ) VALUES (%s, %s, %s)
        """

        params_list = []
        for r in rows:
            params_list.append((
                r.get('TUCASEID'), r.get('activity_code'), r.get('minutes')
            ))

        return self._execute_many_adaptive(query, params_list, table_name='sum')

    def insert_cps_rows(self, rows: List[Dict[str, Any]]) -> Tuple[bool, str]:
        """
        Bulk insert CPS rows. Due to 265 columns, this uses dynamic field mapping.
        """
        if not rows:
            return True, ""
        
        columns = list(rows[0].keys())
        placeholders = ', '.join(['%s'] * len(columns))
        column_names = ', '.join(columns)

        query = f"""
            INSERT IGNORE INTO world_sim_atus.cps ({column_names})
            VALUES ({placeholders})
        """

        params_list = []
        for r in rows:
            params_list.append(tuple(r.get(col) for col in columns))

        return self._execute_many_adaptive(query, params_list, table_name='cps')

    def insert_resp_rows(self, rows: List[Dict[str, Any]]) -> Tuple[bool, str]:
        """
        Bulk insert resp rows. Due to 133 columns, this uses dynamic field mapping.
        """
        if not rows:
            return True, ""

        columns = list(rows[0].keys())
        placeholders = ', '.join(['%s'] * len(columns))
        column_names = ', '.join(columns)

        query = f"""
            INSERT IGNORE INTO world_sim_atus.resp ({column_names})
            VALUES ({placeholders})
        """

        params_list = []
        for r in rows:
            params_list.append(tuple(r.get(col) for col in columns))

        return self._execute_many_adaptive(query, params_list, table_name='resp')

    # =========================================================================
    # MODEL TABLE UPSERTS
    # =========================================================================

    def upsert_strata_def(self, rows: List[Dict[str, Any]]) -> Tuple[bool, str]:
        if not rows:
            return True, ""

        query = """
            INSERT INTO world_sim_atus.strata_def (id, name, definition)
            VALUES (%s, %s, %s)
            ON DUPLICATE KEY UPDATE
                name = VALUES(name),
                definition = VALUES(definition)
        """

        params_list: List[Tuple[Any, ...]] = []
        for r in rows:
            definition = r.get("definition")
            if definition is not None and not isinstance(definition, str):
                definition = json.dumps(definition)
            params_list.append((
                r.get("id"),
                r.get("name"),
                definition,
            ))

        return self._execute_many_adaptive(query, params_list, table_name='strata_def')

    def upsert_case_stratum(self, rows: List[Dict[str, Any]]) -> Tuple[bool, str]:
        if not rows:
            return True, ""

        query = """
            INSERT INTO world_sim_atus.case_stratum (TUCASEID, stratum_id)
            VALUES (%s, %s)
            ON DUPLICATE KEY UPDATE
                stratum_id = VALUES(stratum_id)
        """

        params_list = [
            (r.get("TUCASEID"), r.get("stratum_id"))
            for r in rows
        ]
        return self._execute_many_adaptive(query, params_list, table_name='case_stratum')

    def upsert_operator_map(self, rows: List[Dict[str, Any]]) -> Tuple[bool, str]:
        if not rows:
            return True, ""

        query = """
            INSERT INTO world_sim_atus.operator_map (
                six_digit_activity_code,
                operator_group,
                default_location,
                typical_minutes_p50,
                cooldown_days,
                weekly_quota,
                prereq_flags
            ) VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                operator_group = VALUES(operator_group),
                default_location = VALUES(default_location),
                typical_minutes_p50 = VALUES(typical_minutes_p50),
                cooldown_days = VALUES(cooldown_days),
                weekly_quota = VALUES(weekly_quota),
                prereq_flags = VALUES(prereq_flags)
        """

        params_list: List[Tuple[Any, ...]] = []
        for r in rows:
            prereq = r.get("prereq_flags")
            if prereq is not None and not isinstance(prereq, str):
                prereq = json.dumps(prereq)
            params_list.append((
                r.get("six_digit_activity_code"),
                r.get("operator_group"),
                r.get("default_location"),
                r.get("typical_minutes_p50"),
                r.get("cooldown_days"),
                r.get("weekly_quota"),
                prereq,
            ))

        return self._execute_many_adaptive(query, params_list, table_name='operator_map')

    def upsert_hourly_mix(self, rows: List[Dict[str, Any]]) -> Tuple[bool, str]:
        if not rows:
            return True, ""

        query = """
            INSERT INTO world_sim_atus.hourly_mix (
                stratum_id,
                dow,
                hour,
                operator_group,
                probability,
                sample_n,
                weight_sum
            ) VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                probability = VALUES(probability),
                sample_n = VALUES(sample_n),
                weight_sum = VALUES(weight_sum)
        """

        params_list = [
            (
                r.get("stratum_id"),
                r.get("dow"),
                r.get("hour"),
                r.get("operator_group"),
                r.get("probability"),
                r.get("sample_n"),
                r.get("weight_sum"),
            )
            for r in rows
        ]

        return self._execute_many_adaptive(query, params_list, table_name='hourly_mix')

    def upsert_duration_stats(self, rows: List[Dict[str, Any]]) -> Tuple[bool, str]:
        if not rows:
            return True, ""

        query = """
            INSERT INTO world_sim_atus.duration_stats (
                stratum_id,
                dow,
                operator_group,
                mean_minutes,
                sd_minutes,
                p10_minutes,
                p50_minutes,
                p90_minutes,
                sample_n,
                weight_sum
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                mean_minutes = VALUES(mean_minutes),
                sd_minutes = VALUES(sd_minutes),
                p10_minutes = VALUES(p10_minutes),
                p50_minutes = VALUES(p50_minutes),
                p90_minutes = VALUES(p90_minutes),
                sample_n = VALUES(sample_n),
                weight_sum = VALUES(weight_sum)
        """

        params_list = [
            (
                r.get("stratum_id"),
                r.get("dow"),
                r.get("operator_group"),
                r.get("mean_minutes"),
                r.get("sd_minutes"),
                r.get("p10_minutes"),
                r.get("p50_minutes"),
                r.get("p90_minutes"),
                r.get("sample_n"),
                r.get("weight_sum"),
            )
            for r in rows
        ]

        return self._execute_many_adaptive(query, params_list, table_name='duration_stats')

    def upsert_transitions(self, rows: List[Dict[str, Any]]) -> Tuple[bool, str]:
        if not rows:
            return True, ""

        query = """
            INSERT INTO world_sim_atus.transitions (
                stratum_id,
                hour,
                from_operator,
                to_operator,
                probability,
                sample_n
            ) VALUES (%s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                probability = VALUES(probability),
                sample_n = VALUES(sample_n)
        """

        params_list = [
            (
                r.get("stratum_id"),
                r.get("hour"),
                r.get("from_operator"),
                r.get("to_operator"),
                r.get("probability"),
                r.get("sample_n"),
            )
            for r in rows
        ]

        return self._execute_many_adaptive(query, params_list, table_name='transitions')

    def upsert_social_where(self, rows: List[Dict[str, Any]]) -> Tuple[bool, str]:
        if not rows:
            return True, ""

        query = """
            INSERT INTO world_sim_atus.social_where (
                stratum_id,
                hour,
                operator_group,
                home_prob,
                with_spouse,
                with_child,
                with_friend,
                alone_prob,
                sample_n,
                weight_sum
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                home_prob = VALUES(home_prob),
                with_spouse = VALUES(with_spouse),
                with_child = VALUES(with_child),
                with_friend = VALUES(with_friend),
                alone_prob = VALUES(alone_prob),
                sample_n = VALUES(sample_n),
                weight_sum = VALUES(weight_sum)
        """

        params_list = [
            (
                r.get("stratum_id"),
                r.get("hour"),
                r.get("operator_group"),
                r.get("home_prob"),
                r.get("with_spouse"),
                r.get("with_child"),
                r.get("with_friend"),
                r.get("alone_prob"),
                r.get("sample_n"),
                r.get("weight_sum"),
            )
            for r in rows
        ]

        return self._execute_many_adaptive(query, params_list, table_name='social_where')

    def upsert_weekly_presence(self, rows: List[Dict[str, Any]]) -> Tuple[bool, str]:
        if not rows:
            return True, ""

        query = """
            INSERT INTO world_sim_atus.weekly_presence (
                stratum_id,
                operator_group,
                presence_rate,
                mean_minutes_per_week,
                sample_n,
                weight_sum
            ) VALUES (%s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                presence_rate = VALUES(presence_rate),
                mean_minutes_per_week = VALUES(mean_minutes_per_week),
                sample_n = VALUES(sample_n),
                weight_sum = VALUES(weight_sum)
        """

        params_list = [
            (
                r.get("stratum_id"),
                r.get("operator_group"),
                r.get("presence_rate"),
                r.get("mean_minutes_per_week"),
                r.get("sample_n"),
                r.get("weight_sum"),
            )
            for r in rows
        ]

        return self._execute_many_adaptive(query, params_list, table_name='weekly_presence')


# Singleton instance accessor
_atus_manager_instance: ATUSDatabaseManager | None = None


def get_atus_database_manager() -> ATUSDatabaseManager:
    """Get or create the singleton ATUS database manager."""
    global _atus_manager_instance
    if _atus_manager_instance is None:
        _atus_manager_instance = ATUSDatabaseManager()
    return _atus_manager_instance
