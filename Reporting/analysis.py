#!/usr/bin/env python3
"""
LLM Analysis Adapter for Financial Statements

This module defines a simple function that accepts pandas DataFrames for the
Income Statement, Balance Sheet, and Cash Flow, and returns a text analysis.
It's intentionally simple and swappable.
"""

from __future__ import annotations

from typing import Optional
import pandas as pd


def analyze_financials(income: pd.DataFrame, balance: pd.DataFrame, cash: pd.DataFrame) -> str:
    """Return a concise text analysis of provided statements.

    In production, this would call an LLM. For now, provide heuristic analysis.
    """
    lines = []
    try:
        if income is not None and not income.empty:
            net_row = income.loc["Net Income"] if "Net Income" in income.index else None
            if net_row is not None is not False:
                last_period = net_row.index[-1]
                ni = float(net_row.iloc[-1])
                lines.append(f"Net income in the latest period ({last_period}): {ni:,.2f}.")
        if balance is not None and not balance.empty:
            assets = balance.loc["Assets"].iloc[-1] if "Assets" in balance.index else 0.0
            liab = balance.loc["Liabilities"].iloc[-1] if "Liabilities" in balance.index else 0.0
            eq = balance.loc["Equity"].iloc[-1] if "Equity" in balance.index else 0.0
            lines.append(f"Balance sheet totals (latest): Assets={assets:,.2f}, Liabilities={liab:,.2f}, Equity={eq:,.2f}.")
        if cash is not None and not cash.empty:
            last_cf = cash.loc["Net Cash Change"].iloc[-1] if "Net Cash Change" in cash.index else 0.0
            lines.append(f"Net cash change in the latest period: {last_cf:,.2f}.")
    except Exception:
        lines.append("Analysis unavailable due to data formatting issues.")
    if not lines:
        lines.append("No financial activity found for the selected period.")
    return "\n".join(lines)
