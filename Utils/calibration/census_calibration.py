"""Utilities for deriving ACS-based calibration priors by CBSA."""

from __future__ import annotations

from dataclasses import dataclass
import logging
import re
from typing import Any, Dict, Iterable, List, Optional, Tuple, Set

from Database.managers.alternative_data import (
    get_alternative_data_manager,
    AlternativeDataDatabaseManager,
)


logger = logging.getLogger(__name__)

STATE_ABBR_TO_FIPS: Dict[str, str] = {
    'AL': '01',
    'AK': '02',
    'AZ': '04',
    'AR': '05',
    'CA': '06',
    'CO': '08',
    'CT': '09',
    'DE': '10',
    'DC': '11',
    'FL': '12',
    'GA': '13',
    'HI': '15',
    'ID': '16',
    'IL': '17',
    'IN': '18',
    'IA': '19',
    'KS': '20',
    'KY': '21',
    'LA': '22',
    'ME': '23',
    'MD': '24',
    'MA': '25',
    'MI': '26',
    'MN': '27',
    'MS': '28',
    'MO': '29',
    'MT': '30',
    'NE': '31',
    'NV': '32',
    'NH': '33',
    'NJ': '34',
    'NM': '35',
    'NY': '36',
    'NC': '37',
    'ND': '38',
    'OH': '39',
    'OK': '40',
    'OR': '41',
    'PA': '42',
    'RI': '44',
    'SC': '45',
    'SD': '46',
    'TN': '47',
    'TX': '48',
    'UT': '49',
    'VT': '50',
    'VA': '51',
    'WA': '53',
    'WV': '54',
    'WI': '55',
    'WY': '56',
    'PR': '72',
}

DEFAULT_OWNER_SHARE = 0.64
DEFAULT_WITH_MORTGAGE_SHARE = 0.63
DEFAULT_HELOC_SHARE = 0.10
DEFAULT_ANY_EQUITY_LOAN_SHARE = 0.17
DEFAULT_VEHICLE_PROBS = (0.08, 0.38, 0.34, 0.20)


def _safe_div(numerator: float, denominator: float) -> float:
    if denominator == 0:
        return 0.0
    return numerator / denominator


@dataclass(frozen=True)
class OwnerStats:
    owner_units: float
    renter_units: float
    total_units: float
    p_owner: float
    p_renter: float


@dataclass(frozen=True)
class MortgageStats:
    with_mortgage: float
    without_mortgage: float
    total_owner_units: float
    p_with_mortgage: float
    p_without_mortgage: float


@dataclass(frozen=True)
class HelocStats:
    second_only: float
    heloc_only: float
    both_second_and_heloc: float
    none: float
    total_owner_units: float
    p_any_equity_loan: float
    p_heloc: float
    p_second_mortgage: float


@dataclass(frozen=True)
class VehicleStats:
    households_no_vehicle: float
    households_one_vehicle: float
    households_two_vehicles: float
    households_three_plus: float
    total_households: float
    p_no_vehicle: float
    p_one_vehicle: float
    p_two_vehicles: float
    p_three_plus: float


@dataclass(frozen=True)
class HomeValueStats:
    total_units: float
    quantiles: Dict[str, float]
    mean_midpoint: float


@dataclass(frozen=True)
class IncomeDistribution:
    bucket_counts: Dict[str, float]
    total_households: float


class CensusCalibration:
    """High-level facade for ACS-derived priors."""

    def __init__(
        self,
        manager: Optional[AlternativeDataDatabaseManager] = None,
        year: int = 2024,
    ) -> None:
        self.manager = manager or get_alternative_data_manager()
        self.year = year
        self._column_cache: Dict[str, Dict[str, str]] = {}
        self._owner_cache: Dict[Tuple[Optional[int], Optional[str]], OwnerStats] = {}
        self._mortgage_cache: Dict[Tuple[Optional[int], Optional[str]], MortgageStats] = {}
        self._heloc_cache: Dict[Tuple[Optional[int], Optional[str]], HelocStats] = {}
        self._vehicle_cache: Dict[Tuple[Optional[int], Optional[str]], VehicleStats] = {}
        self._home_value_cache: Dict[Tuple[Optional[int], Optional[str]], HomeValueStats] = {}
        self._income_cache: Dict[Tuple[Optional[int], Optional[str]], IncomeDistribution] = {}
        self._heloc_warning_keys: set[Tuple[Optional[int], Optional[str]]] = set()
        self._vehicle_warning_keys: Set[Tuple[Optional[int], Optional[str]]] = set()

    # ------------------------------------------------------------------
    # Column metadata helpers
    # ------------------------------------------------------------------
    def _get_columns(self, census_code: str) -> Dict[str, str]:
        if census_code not in self._column_cache:
            self._column_cache[census_code] = self.manager.get_census_columns_map(census_code)
        return self._column_cache[census_code]

    @staticmethod
    def _normalize_state_fips(state: Optional[str]) -> Optional[str]:
        if state is None:
            return None
        state_str = str(state).strip()
        if not state_str:
            return None
        if state_str.isdigit():
            return state_str.zfill(2)[:2]
        upper = state_str.upper()
        return STATE_ABBR_TO_FIPS.get(upper)

    def _cache_key(self, cbsa_code: Optional[int], state_fips: Optional[str]) -> Tuple[Optional[int], Optional[str]]:
        normalized_state = self._normalize_state_fips(state_fips)
        return (int(cbsa_code) if cbsa_code is not None else None, normalized_state)

    def _fetch_with_fallback(
        self,
        cbsa_code: Optional[int],
        census_code: str,
        var_codes: Iterable[str],
        state_fips: Optional[str] = None,
    ) -> Tuple[Dict[str, float], str]:

        var_list = list(dict.fromkeys(var_codes))
        scopes: List[Tuple[str, Optional[Any]]] = []

        if cbsa_code is not None:
            scopes.append(('cbsa', int(cbsa_code)))
        normalized_state = self._normalize_state_fips(state_fips)
        if normalized_state:
            scopes.append(('state', normalized_state))
        scopes.append(('nation', None))

        last_scope = 'nation'
        last_data: Dict[str, float] = {vc: 0.0 for vc in var_list}

        for scope, value in scopes:
            if scope == 'cbsa':
                data = self.manager.fetch_census_aggregates(
                    year=self.year,
                    cbsa_code=int(cbsa_code),  # type: ignore[arg-type]
                    census_code=census_code,
                    var_codes=var_list,
                    require_full_coverage=True,
                )
            elif scope == 'state':
                data = self.manager.fetch_census_aggregates_state(
                    year=self.year,
                    state_fips=value,  # type: ignore[arg-type]
                    census_code=census_code,
                    var_codes=var_list,
                )
            else:
                data = self.manager.fetch_census_aggregates_nationwide(
                    year=self.year,
                    census_code=census_code,
                    var_codes=var_list,
                )

            last_scope = scope
            last_data = data

            if any(v > 0 for v in data.values()):
                if scope != 'cbsa':
                    logger.debug(
                        "Falling back to %s scope for %s (cbsa=%s, state=%s)",
                        scope,
                        census_code,
                        cbsa_code,
                        normalized_state,
                    )
                return data, scope

        logger.debug(
            "All scopes returned zero for %s (cbsa=%s, state=%s); using %s result",
            census_code,
            cbsa_code,
            normalized_state,
            last_scope,
        )
        return last_data, last_scope

    @staticmethod
    def _derive_vehicle_categories(label_map: Dict[str, str]) -> Dict[str, str]:
        """
        Derive vehicle availability categories from ACS B08201 metadata.

        Prefers the shallowest hierarchy (fewest segments) that still maps to the
        canonical bucket labels, so we capture total household counts rather than
        race/tenure breakdowns when available.
        """
        category_aliases = {
            'none': ('no vehicle available',),
            'one': ('1 vehicle available', 'one vehicle available'),
            'two': ('2 vehicles available',),
            'three_plus': ('3 or more vehicles available', '3+ vehicles available'),
        }

        def detect_category(segment: str) -> Optional[str]:
            lower = segment.lower()
            for category, aliases in category_aliases.items():
                if any(alias in lower for alias in aliases):
                    return category
            return None

        category_candidates: Dict[str, Tuple[Tuple[int, int], str]] = {}

        for var_code, label in label_map.items():
            if not var_code.endswith('E') or var_code.endswith('_001E'):
                continue
            segments = [seg.strip() for seg in label.split('!!') if seg.strip()]
            if not segments:
                continue
            category = detect_category(segments[-1])
            if not category:
                continue

            depth = len(segments)
            penalty = sum(
                1
                for seg in segments[:-1]
                if 'total' not in seg.lower() and 'occupied housing units' not in seg.lower()
            )
            score = (depth, penalty)

            current = category_candidates.get(category)
            if current is None or score < current[0]:
                category_candidates[category] = (score, var_code)

        return {category: var_code for category, (_, var_code) in category_candidates.items()}

    # ------------------------------------------------------------------
    # Owner / renter priors
    # ------------------------------------------------------------------
    def get_owner_stats(
        self,
        cbsa_code: Optional[int],
        state_fips: Optional[str] = None,
    ) -> OwnerStats:
        key = self._cache_key(cbsa_code, state_fips)
        if key in self._owner_cache:
            return self._owner_cache[key]

        var_codes = ['B25003_002E', 'B25003_003E']
        data, scope_used = self._fetch_with_fallback(
            cbsa_code=cbsa_code,
            census_code='B25003',
            var_codes=var_codes,
            state_fips=state_fips,
        )
        owner_units = float(data.get('B25003_002E', 0.0))
        renter_units = float(data.get('B25003_003E', 0.0))
        total_units = owner_units + renter_units

        if total_units <= 0:
            logger.warning(
                "Owner stats fallback produced zero total units (scope=%s, cbsa=%s, state=%s); using defaults",
                scope_used,
                cbsa_code,
                state_fips,
            )
            p_owner = DEFAULT_OWNER_SHARE
            p_renter = 1.0 - DEFAULT_OWNER_SHARE
        else:
            p_owner = _safe_div(owner_units, total_units)
            p_renter = _safe_div(renter_units, total_units)

        stats = OwnerStats(
            owner_units=owner_units,
            renter_units=renter_units,
            total_units=total_units,
            p_owner=p_owner,
            p_renter=p_renter,
        )
        self._owner_cache[key] = stats
        return stats

    # ------------------------------------------------------------------
    # Mortgage prevalence
    # ------------------------------------------------------------------
    def get_mortgage_stats(
        self,
        cbsa_code: Optional[int],
        state_fips: Optional[str] = None,
    ) -> MortgageStats:
        key = self._cache_key(cbsa_code, state_fips)
        if key in self._mortgage_cache:
            return self._mortgage_cache[key]

        var_codes = ['B25081_002E', 'B25081_003E']
        data, scope_used = self._fetch_with_fallback(
            cbsa_code=cbsa_code,
            census_code='B25081',
            var_codes=var_codes,
            state_fips=state_fips,
        )
        with_mortgage = float(data.get('B25081_002E', 0.0))
        without_mortgage = float(data.get('B25081_003E', 0.0))
        total = with_mortgage + without_mortgage

        if total <= 0:
            logger.warning(
                "Mortgage stats fallback produced zero owner units (scope=%s, cbsa=%s, state=%s); using defaults",
                scope_used,
                cbsa_code,
                state_fips,
            )
            p_with = DEFAULT_WITH_MORTGAGE_SHARE
            p_without = 1.0 - DEFAULT_WITH_MORTGAGE_SHARE
        else:
            p_with = _safe_div(with_mortgage, total)
            p_without = _safe_div(without_mortgage, total)

        stats = MortgageStats(
            with_mortgage=with_mortgage,
            without_mortgage=without_mortgage,
            total_owner_units=total,
            p_with_mortgage=p_with,
            p_without_mortgage=p_without,
        )
        self._mortgage_cache[key] = stats
        return stats

    # ------------------------------------------------------------------
    # HELOC / second mortgage
    # ------------------------------------------------------------------
    def get_heloc_stats(
        self,
        cbsa_code: Optional[int],
        state_fips: Optional[str] = None,
    ) -> HelocStats:
        key = self._cache_key(cbsa_code, state_fips)
        normalized_state = key[1]
        if key in self._heloc_cache:
            return self._heloc_cache[key]

        vars_needed = ['B25085_002E', 'B25085_003E', 'B25085_004E', 'B25085_005E']
        data, scope_used = self._fetch_with_fallback(
            cbsa_code=cbsa_code,
            census_code='B25085',
            var_codes=vars_needed,
            state_fips=state_fips,
        )
        second_only = float(data.get('B25085_002E', 0.0))
        heloc_only = float(data.get('B25085_003E', 0.0))
        both = float(data.get('B25085_004E', 0.0))
        none = float(data.get('B25085_005E', 0.0))
        total = second_only + heloc_only + both + none

        if total <= 0:
            if key not in self._heloc_warning_keys:
                logger.warning(
                    "HELOC stats fallback produced zero owner units (scope=%s, cbsa=%s, state=%s); using defaults",
                    scope_used,
                    cbsa_code,
                    normalized_state,
                )
                self._heloc_warning_keys.add(key)
            p_any_equity = DEFAULT_ANY_EQUITY_LOAN_SHARE
            p_heloc = DEFAULT_HELOC_SHARE
            p_second = max(p_any_equity - p_heloc, 0.05)
        else:
            p_any_equity = _safe_div(second_only + heloc_only + both, total)
            p_heloc = _safe_div(heloc_only + both, total)
            p_second = _safe_div(second_only + both, total)

        stats = HelocStats(
            second_only=second_only,
            heloc_only=heloc_only,
            both_second_and_heloc=both,
            none=none,
            total_owner_units=total,
            p_any_equity_loan=p_any_equity,
            p_heloc=p_heloc,
            p_second_mortgage=p_second,
        )
        self._heloc_cache[key] = stats
        return stats

    # ------------------------------------------------------------------
    # Vehicle priors
    # ------------------------------------------------------------------
    def get_vehicle_stats(
        self,
        cbsa_code: Optional[int],
        state_fips: Optional[str] = None,
    ) -> VehicleStats:
        key = self._cache_key(cbsa_code, state_fips)
        if key in self._vehicle_cache:
            return self._vehicle_cache[key]

        label_map = self._get_columns('B08201')
        category_map = self._derive_vehicle_categories(label_map)
        required_keys = {'none', 'one', 'two', 'three_plus'}
        if not required_keys.issubset(category_map.keys()):
            fallback_map = {
                'none': 'B08201_002E',
                'one': 'B08201_003E',
                'two': 'B08201_004E',
                'three_plus': 'B08201_005E',
            }
            missing = required_keys.difference(category_map.keys())
            for key_missing in missing:
                category_map[key_missing] = fallback_map[key_missing]
            cache_key = self._cache_key(cbsa_code, state_fips)
            if cache_key not in self._vehicle_warning_keys:
                logger.debug(
                    "Vehicle metadata incomplete for B08201 (cbsa=%s, state=%s); applied canonical fallback codes %s",
                    cbsa_code,
                    cache_key[1],
                    sorted(missing),
                )
                self._vehicle_warning_keys.add(cache_key)

        var_codes = [category_map[k] for k in ['none', 'one', 'two', 'three_plus']] + ['B08201_001E']
        data, scope_used = self._fetch_with_fallback(
            cbsa_code=cbsa_code,
            census_code='B08201',
            var_codes=var_codes,
            state_fips=state_fips,
        )
        households_no_vehicle = float(data.get(category_map['none'], 0.0))
        households_one_vehicle = float(data.get(category_map['one'], 0.0))
        households_two_vehicles = float(data.get(category_map['two'], 0.0))
        households_three_plus = float(data.get(category_map['three_plus'], 0.0))
        total_households = float(data.get('B08201_001E', households_no_vehicle + households_one_vehicle + households_two_vehicles + households_three_plus))

        if total_households <= 0:
            logger.warning(
                "Vehicle stats fallback produced zero households (scope=%s, cbsa=%s, state=%s); using defaults",
                scope_used,
                cbsa_code,
                state_fips,
            )
            probs = DEFAULT_VEHICLE_PROBS
            households_no_vehicle = probs[0]
            households_one_vehicle = probs[1]
            households_two_vehicles = probs[2]
            households_three_plus = probs[3]
            total_households = sum(probs)

        stats = VehicleStats(
            households_no_vehicle=households_no_vehicle,
            households_one_vehicle=households_one_vehicle,
            households_two_vehicles=households_two_vehicles,
            households_three_plus=households_three_plus,
            total_households=total_households,
            p_no_vehicle=_safe_div(households_no_vehicle, total_households),
            p_one_vehicle=_safe_div(households_one_vehicle, total_households),
            p_two_vehicles=_safe_div(households_two_vehicles, total_households),
            p_three_plus=_safe_div(households_three_plus, total_households),
        )
        self._vehicle_cache[cbsa_code] = stats
        return stats

    # ------------------------------------------------------------------
    # Home value quantiles
    # ------------------------------------------------------------------
    def get_home_value_stats(
        self,
        cbsa_code: Optional[int],
        state_fips: Optional[str] = None,
    ) -> HomeValueStats:
        key = self._cache_key(cbsa_code, state_fips)
        if key in self._home_value_cache:
            return self._home_value_cache[key]

        label_map = self._get_columns('B25075')
        bins: List[Dict[str, float]] = []
        for var_code, label in label_map.items():
            if not var_code.endswith('E') or var_code.endswith('_001E'):
                continue
            range_label = label.split('!!')[-1].replace(',', '').strip()
            lower, upper, midpoint = self._parse_value_range(range_label)
            bins.append({'code': var_code, 'lower': lower, 'upper': upper, 'midpoint': midpoint})
        if not bins:
            raise ValueError('No value bins parsed for B25075')
        bins.sort(key=lambda x: x['midpoint'])

        var_codes = [b['code'] for b in bins] + ['B25075_001E']
        data, scope_used = self._fetch_with_fallback(
            cbsa_code=cbsa_code,
            census_code='B25075',
            var_codes=var_codes,
            state_fips=state_fips,
        )
        total_units = float(data.get('B25075_001E', 0.0))
        if total_units <= 0:
            total_units = sum(float(data.get(b['code'], 0.0)) for b in bins)
            if total_units <= 0:
                logger.warning(
                    "Home value stats fallback produced zero units (scope=%s, cbsa=%s, state=%s); approximating from bins",
                    scope_used,
                    cbsa_code,
                    state_fips,
                )
                total_units = 1.0

        cumulative = 0.0
        quantile_targets = {'q10': 0.10, 'q25': 0.25, 'q50': 0.50, 'q75': 0.75, 'q90': 0.90}
        quantile_values: Dict[str, float] = {}
        bin_midpoint_weighted_sum = 0.0

        for b in bins:
            count = float(data.get(b['code'], 0.0))
            if count <= 0:
                continue
            bin_midpoint_weighted_sum += b['midpoint'] * count
            prev_cumulative = cumulative
            cumulative += count
            for key, target in quantile_targets.items():
                if key in quantile_values:
                    continue
                if cumulative >= target * total_units and total_units > 0:
                    quantile_values[key] = b['midpoint']
        for key in quantile_targets.keys():
            quantile_values.setdefault(key, bins[-1]['midpoint'])

        mean_midpoint = _safe_div(bin_midpoint_weighted_sum, total_units)
        stats = HomeValueStats(
            total_units=total_units,
            quantiles=quantile_values,
            mean_midpoint=mean_midpoint,
        )
        self._home_value_cache[cbsa_code] = stats
        return stats

    def _parse_value_range(self, label: str) -> Tuple[float, Optional[float], float]:
        clean = label.replace('$', '').replace('+', '').replace('and over', 'or more').lower()
        if clean.startswith('less than'):
            upper = self._extract_number(clean)
            lower = 0.0
            midpoint = upper * 0.5 if upper else 0.0
            return lower, upper, midpoint
        if 'to' in clean:
            parts = clean.split('to')
            lower = self._extract_number(parts[0])
            upper = self._extract_number(parts[1])
            if lower is None:
                lower = 0.0
            if upper is None:
                upper = lower
            midpoint = (lower + upper) / 2.0 if upper is not None else lower * 1.15
            return lower, upper, midpoint
        if 'or more' in clean:
            lower = self._extract_number(clean)
            midpoint = lower * 1.25 if lower else 0.0
            return lower or 0.0, None, midpoint
        # Fallback: treat as point value
        value = self._extract_number(clean) or 0.0
        return value, value, value

    @staticmethod
    def _extract_number(fragment: str) -> Optional[float]:
        cleaned = fragment.replace(',', '')
        match = re.search(r"(\d+[\d]*)", cleaned)
        if not match:
            return None
        try:
            return float(match.group(1))
        except ValueError:
            return None

    # ------------------------------------------------------------------
    # Income distribution
    # ------------------------------------------------------------------
    def get_income_distribution(
        self,
        cbsa_code: Optional[int],
        state_fips: Optional[str] = None,
    ) -> IncomeDistribution:
        key = self._cache_key(cbsa_code, state_fips)
        if key in self._income_cache:
            return self._income_cache[key]

        label_map = self._get_columns('B19001')
        var_codes = [vc for vc in label_map if vc.endswith('E') and not vc.endswith('_001E')]
        data, scope_used = self._fetch_with_fallback(
            cbsa_code=cbsa_code,
            census_code='B19001',
            var_codes=var_codes + ['B19001_001E'],
            state_fips=state_fips,
        )
        counts = {vc: float(data.get(vc, 0.0)) for vc in var_codes}
        total = float(data.get('B19001_001E', sum(counts.values())))
        if total <= 0:
            logger.warning(
                "Income distribution fallback produced zero households (scope=%s, cbsa=%s, state=%s)",
                scope_used,
                cbsa_code,
                state_fips,
            )
        distribution = IncomeDistribution(bucket_counts=counts, total_households=total)
        self._income_cache[key] = distribution
        return distribution
