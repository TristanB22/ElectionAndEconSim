#!/usr/bin/env python3
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class AgentTraits:
    risk_aversion: float
    curiosity: float
    loss_aversion: float
    sharing_propensity: float
    trust_update_rate: float

    @staticmethod
    def _bounded(x: float) -> float:
        return max(0.0, min(1.0, float(x)))

    @classmethod
    def from_l2(cls, l2: Any) -> "AgentTraits":
        """
        derive base traits from l2 fields. simple heuristics; fail if required l2 object missing.
        comments are lowercase.
        """
        if l2 is None:
            raise ValueError("l2 data required to derive traits")

        # simple mappings with fallbacks to mid values
        income = getattr(getattr(l2, 'economic', None), 'estimated_income', None)
        credit = getattr(getattr(l2, 'economic', None), 'credit_rating', None)
        education = getattr(getattr(l2, 'work', None), 'education_level', None)

        # risk_aversion: higher income and higher credit -> lower risk aversion; else higher
        base_risk = 0.6
        try:
            inc_num = float(str(income).replace(',', '')) if income else None
            if inc_num is not None:
                if inc_num >= 100000:
                    base_risk = 0.4
                elif inc_num <= 30000:
                    base_risk = 0.7
        except Exception:
            pass
        if credit and isinstance(credit, str):
            if credit.lower().startswith('excellent'):
                base_risk -= 0.1
            elif credit.lower().startswith('poor'):
                base_risk += 0.1

        # curiosity: higher education tends to correlate with curiosity
        base_curiosity = 0.5
        if education and isinstance(education, str):
            e = education.lower()
            if 'grad' in e or 'master' in e or 'phd' in e:
                base_curiosity = 0.7
            elif 'high school' in e:
                base_curiosity = 0.45

        # loss aversion: inverse of risk tolerance
        loss_aversion = 1.0 - base_risk

        # sharing propensity: mild function of curiosity
        sharing_propensity = 0.4 + 0.4 * (base_curiosity - 0.5)

        # trust update rate: moderate default
        trust_update_rate = 0.5

        return cls(
            risk_aversion=cls._bounded(base_risk),
            curiosity=cls._bounded(base_curiosity),
            loss_aversion=cls._bounded(loss_aversion),
            sharing_propensity=cls._bounded(sharing_propensity),
            trust_update_rate=cls._bounded(trust_update_rate),
        )



