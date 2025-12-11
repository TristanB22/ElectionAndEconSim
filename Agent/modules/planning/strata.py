#!/usr/bin/env python3
"""
Shared helpers for computing agent strata used in planning distributions.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional


@dataclass(frozen=True)
class StratumFeatures:
	age_band: str
	sex: str
	employment: str
	hours_band: str
	children: str
	education: str
	income: str
	region: str
	metro: str

	def to_definition(self) -> Dict[str, str]:
		return {
			"age_band": self.age_band,
			"sex": self.sex,
			"employment": self.employment,
			"hours_band": self.hours_band,
			"children": self.children,
			"education": self.education,
			"income": self.income,
			"region": self.region,
			"metro": self.metro,
		}


def age_band(age: Optional[int]) -> str:
	if age is None:
		return "unknown"
	if age < 18:
		return "under_18"
	if age <= 24:
		return "18_24"
	if age <= 34:
		return "25_34"
	if age <= 44:
		return "35_44"
	if age <= 54:
		return "45_54"
	if age <= 64:
		return "55_64"
	if age <= 74:
		return "65_74"
	return "75_plus"


def sex_label(sex: Optional[int]) -> str:
	if sex == 1:
		return "male"
	if sex == 2:
		return "female"
	return "unknown"


def employment_label(telfs: Optional[int]) -> str:
	if telfs in {1, 2}:
		return "employed"
	if telfs == 3:
		return "unemployed"
	if telfs in {4, 5}:
		return "not_in_labor_force"
	return "unknown"


def hours_band(hours: Optional[int]) -> str:
	if hours is None or hours <= 0:
		return "unknown"
	if hours <= 20:
		return "up_to_20"
	if hours <= 34:
		return "21_34"
	if hours <= 44:
		return "35_44"
	return "45_plus"


def children_band(num_children: Optional[int]) -> str:
	if num_children is None or num_children <= 0:
		return "none"
	if num_children <= 2:
		return "with_children"
	return "many_children"


def education_band(peeduca: Optional[int]) -> str:
	if peeduca is None:
		return "unknown"
	if peeduca <= 38:
		return "less_than_hs"
	if peeduca <= 39:
		return "hs_grad"
	if peeduca <= 40:
		return "some_college"
	if peeduca <= 42:
		return "college_plus"
	return "unknown"


def income_band(trernwa: Optional[int]) -> str:
	if trernwa is None or trernwa <= 0:
		return "unknown"
	if trernwa < 500:
		return "low"
	if trernwa < 1000:
		return "mid"
	return "high"


def region_label(gereg: Optional[int]) -> str:
	if gereg is None:
		return "unknown"
	return f"region_{gereg}"


def metro_label(gemetsta: Optional[int]) -> str:
	if gemetsta == 1:
		return "metro"
	if gemetsta == 2:
		return "non_metro"
	return "unknown"


def build_stratum_features(
	age: Optional[int],
	sex: Optional[int],
	telfs: Optional[int],
	hrs: Optional[int],
	children: Optional[int],
	education: Optional[int],
	income: Optional[int],
	region: Optional[int],
	metro: Optional[int],
) -> StratumFeatures:
	return StratumFeatures(
		age_band=age_band(age),
		sex=sex_label(sex),
		employment=employment_label(telfs),
		hours_band=hours_band(hrs),
		children=children_band(children),
		education=education_band(education),
		income=income_band(income),
		region=region_label(region),
		metro=metro_label(metro),
	)
