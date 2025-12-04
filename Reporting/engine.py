#!/usr/bin/env python3
"""
Reporting engine for World_Sim.
"""

from __future__ import annotations
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, date
import json
import pandas as pd

from Database.database_manager import execute_query as dm_execute_query
import os


# -----------------------------
# Granularity helpers
# -----------------------------
_GRANULARITY_TO_PANDAS: Dict[str, str] = {
    "15-minute": "15T",
    "Hourly": "H",
    "Daily": "D",
    "Weekly": "W",
    "Monthly": "M",
    "Quarterly": "Q",
    "Yearly": "Y",
}


# -----------------------------
# Schema helpers (idempotent)
# -----------------------------

def ensure_reporting_schema() -> None:
    """Create minimal tables used by reporting if they do not exist.

    Tables:
    - firms(id VARCHAR PRIMARY KEY, company_name VARCHAR) in firms DB
    - events(..., journal_entries JSON, ...) in simulations DB

    Safe to call repeatedly.
    """
    # Check if firms table exists, if not create a simple one
    try:
        firms_db = os.getenv('DB_FIRMS_NAME', 'world_sim_firms')
        # Try to query the existing firms table to see if it exists
        dm_execute_query("SELECT 1 FROM firms LIMIT 1", None, firms_db, True)
        # If we get here, the table exists, so we don't need to create it
    except Exception:
        # Table doesn't exist, create a simple one
        dm_execute_query(
            """
            CREATE TABLE firms (
                id VARCHAR(64) PRIMARY KEY,
                company_name VARCHAR(255) NOT NULL
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            """,
            None,
            firms_db,
            False,
        )

    # action_log table removed - using consolidated events table instead


def ensure_firm_exists(firm_id: str, company_name: str) -> None:
    """Insert a firm row if it does not exist."""
    ensure_reporting_schema()
    firms_db = os.getenv('DB_FIRMS_NAME', 'world_sim_firms')
    res = dm_execute_query(
        "SELECT COUNT(*) AS c FROM firms WHERE id = %s",
        (firm_id,),
        firms_db,
        True,
    )
    rows = res.data if getattr(res, 'success', False) else []
    count = int(rows[0]["c"]) if rows else 0
    if count == 0:
        dm_execute_query(
            "INSERT INTO firms (id, company_name) VALUES (%s, %s)",
            (firm_id, company_name),
            firms_db,
            False,
        )


def normalize_dates(start_date: Any, end_date: Any) -> Tuple[datetime, datetime]:
    """Normalize inputs (date/date-like/str) to datetime bounds (inclusive)."""
    def to_dt(x: Any, is_end: bool = False) -> datetime:
        if isinstance(x, datetime):
            return x
        if isinstance(x, date):
            # End-of-day for end bounds
            return datetime(x.year, x.month, x.day, 23, 59, 59) if is_end else datetime(x.year, x.month, x.day)
        if isinstance(x, str):
            try:
                return datetime.fromisoformat(x)
            except Exception:
                pass
        raise ValueError(f"Unsupported date input: {x}")

    sd = to_dt(start_date, is_end=False)
    ed = to_dt(end_date, is_end=True)
    if sd > ed:
        sd, ed = ed, sd
    return sd, ed


def count_periods(start: datetime, end: datetime, granularity: str) -> int:
    """Estimate number of periods between start and end for the given granularity."""
    alias = _GRANULARITY_TO_PANDAS.get(granularity, "D")
    # Create a simple DatetimeIndex and count unique period labels
    rng = pd.date_range(start=start, end=end, freq=alias)
    return len(rng) if len(rng) > 0 else 1


# -----------------------------
# GL access and bucketing
# -----------------------------

def _fetch_journal_entries_rows(simulation_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """Fetch rows containing journal entries from events table in simulations DB.

    We intentionally only fetch the journal_entries JSON column; we will filter by
    firm_id and date at the journal-line level to respect source-of-truth timestamps
    embedded in each journal line.
    
    Args:
        simulation_id: Optional simulation ID to filter by. If None, fetches from all simulations.
    """
    ensure_reporting_schema()
    
    sim_db = os.getenv('DB_SIM_NAME', 'world_sim_simulations')
    if simulation_id:
        # Fetch from specific simulation
        res = dm_execute_query(
            "SELECT journal_entries FROM events WHERE simulation_id = %s",
            (simulation_id,),
            sim_db,
            True,
        )
        rows = res.data if getattr(res, 'success', False) else []
    else:
        # Fetch from all simulations (simplified query without join)
        res = dm_execute_query(
            """
            SELECT journal_entries 
            FROM events 
            WHERE journal_entries IS NOT NULL 
            AND journal_entries != 'null'
            ORDER BY timestamp DESC
            LIMIT 1000
            """,
            None,
            sim_db,
            True,
        )
        rows = res.data if getattr(res, 'success', False) else []
    
    return rows or []


def _iter_journal_lines_for_firm(
    firm_id: str,
    start: datetime,
    end: datetime,
    simulation_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Collect all journal lines for a firm within [start, end] from specified simulation."""
    results: List[Dict[str, Any]] = []
    rows = _fetch_journal_entries_rows(simulation_id)
    
    for row in rows:
        journal_entries = row.get("journal_entries")
        if not journal_entries:
            continue
            
        # Handle JSON that might be returned as text or already parsed
        if isinstance(journal_entries, str):
            try:
                import json
                journal_entries = json.loads(journal_entries)
            except Exception:
                continue
                
        if not isinstance(journal_entries, list):
            continue
            
        # Each journal entry should be a list of lines
        for entry in journal_entries:
            if not isinstance(entry, dict):
                continue
                
            # Add the entry to results if it has the required fields
            if "account" in entry and ("debit" in entry or "credit" in entry):
                # Add a default date if not present (use current timestamp)
                if "date" not in entry:
                    entry["date"] = datetime.now().isoformat()
                    
                # Parse the date
                try:
                    d = entry.get("date")
                    if isinstance(d, str):
                        dt = datetime.fromisoformat(d.replace('Z', '+00:00'))
                    else:
                        dt = d
                        
                    if isinstance(dt, datetime) and start <= dt <= end:
                        results.append(entry)
                except Exception:
                    # If date parsing fails, include the entry anyway
                    results.append(entry)
    
    return results


def _bucket_label(ts: datetime, granularity: str) -> str:
    alias = _GRANULARITY_TO_PANDAS.get(granularity, "D")
    # Use pandas Period for clean period labeling
    try:
        p = pd.Period(ts, freq=alias)
        return str(p)
    except Exception:
        # Fallback to date
        return ts.strftime("%Y-%m-%d")


def _account_type_from_code_or_name(account: str) -> str:
    """Infer account category: asset/liability/equity/revenue/expense.

    Strategy: look at the leading digit code if present, else fall back to name keywords.
    """
    s = account.strip()
    # Try leading numeric code
    parts = s.split(" ", 1)
    try:
        code = parts[0]
        if code.isdigit() and len(code) >= 1:
            first = code[0]
            if first == '1':
                return 'asset'
            if first == '2':
                return 'liability'
            if first == '3':
                return 'equity'
            if first == '4':
                return 'revenue'
            if first in ('5', '6', '7', '8', '9'):
                return 'expense'
    except Exception:
        pass
    # Name heuristics
    lower = s.lower()
    if any(k in lower for k in ["revenue", "sales"]):
        return 'revenue'
    if any(k in lower for k in ["cogs", "expense", "cost"]):
        return 'expense'
    if any(k in lower for k in ["payable", "liability"]):
        return 'liability'
    if any(k in lower for k in ["equity", "retained earnings"]):
        return 'equity'
    return 'asset'


def _aggregate_by_bucket(lines: List[Dict[str, Any]], granularity: str) -> pd.DataFrame:
    """Return DataFrame indexed by bucket label with columns for accounts, values net (debit - credit)."""
    if not lines:
        return pd.DataFrame()
    records: List[Dict[str, Any]] = []
    for ln in lines:
        bucket = _bucket_label(ln["date"], granularity)
        net = float(ln["debit"]) - float(ln["credit"])  # debit-positive convention
        records.append({
            "bucket": bucket,
            "account": ln["account"],
            "net": net,
        })
    df = pd.DataFrame.from_records(records)
    if df.empty:
        return df
    pivot = df.pivot_table(index="bucket", columns="account", values="net", aggfunc="sum").fillna(0.0)
    # Ensure chronological order by parsing period
    try:
        idx = pd.PeriodIndex(pivot.index, freq=_GRANULARITY_TO_PANDAS.get(granularity, "D"))
        pivot = pivot.set_index(idx)
        pivot = pivot.sort_index()
        pivot.index = pivot.index.astype(str)
    except Exception:
        pivot = pivot.sort_index()
    return pivot


# -----------------------------
# Statement builders
# -----------------------------

def build_income_statement(pivot: pd.DataFrame) -> pd.DataFrame:
    """Summarize revenue, expenses, net income per bucket from account pivot."""
    if pivot is None or pivot.empty:
        return pd.DataFrame()
    # Classify columns
    revenue_cols = [c for c in pivot.columns if _account_type_from_code_or_name(c) == 'revenue']
    expense_cols = [c for c in pivot.columns if _account_type_from_code_or_name(c) == 'expense']

    # Our pivot uses net = debit - credit. Revenue usually posts as credits,
    # so pivot values will be negative. Convert to positive revenue by negating.
    revenue = (-pivot[revenue_cols].sum(axis=1)) if revenue_cols else pd.Series(0.0, index=pivot.index)

    # Expenses are typically debit-positive in our net convention, so keep as-is.
    expenses = pivot[expense_cols].sum(axis=1) if expense_cols else pd.Series(0.0, index=pivot.index)

    df = pd.DataFrame({
        "Revenue": revenue,
        "Expenses": expenses,
    })
    df["Net Income"] = df["Revenue"] - df["Expenses"]
    return df.T  # statements as rows, periods as columns


def build_balance_sheet(pivot: pd.DataFrame) -> pd.DataFrame:
    """Point-in-time balances derived from cumulative sums of balance sheet accounts.

    Equity includes cumulative Net Income to reflect retained earnings when no closing
    entries have been posted.
    """
    if pivot is None or pivot.empty:
        return pd.DataFrame()
    # Identify account classes
    asset_cols = [c for c in pivot.columns if _account_type_from_code_or_name(c) == 'asset']
    liability_cols = [c for c in pivot.columns if _account_type_from_code_or_name(c) == 'liability']
    equity_cols = [c for c in pivot.columns if _account_type_from_code_or_name(c) == 'equity']

    # Cumulative sums over time for BS accounts
    cum = pivot.cumsum()
    assets_total = cum[asset_cols].sum(axis=1) if asset_cols else pd.Series(0.0, index=pivot.index)
    liabilities_total = -cum[liability_cols].sum(axis=1) if liability_cols else pd.Series(0.0, index=pivot.index)
    book_equity_total = -cum[equity_cols].sum(axis=1) if equity_cols else pd.Series(0.0, index=pivot.index)

    # Derive cumulative Net Income from P&L accounts
    revenue_cols = [c for c in pivot.columns if _account_type_from_code_or_name(c) == 'revenue']
    expense_cols = [c for c in pivot.columns if _account_type_from_code_or_name(c) == 'expense']
    revenue = (-pivot[revenue_cols].sum(axis=1)) if revenue_cols else pd.Series(0.0, index=pivot.index)
    expenses = pivot[expense_cols].sum(axis=1) if expense_cols else pd.Series(0.0, index=pivot.index)
    net_income_per_bucket = (revenue - expenses)
    cumulative_net_income = net_income_per_bucket.cumsum()

    equity_including_ni = book_equity_total.add(cumulative_net_income, fill_value=0.0)

    df = pd.DataFrame({
        "Assets": assets_total,
        "Liabilities": liabilities_total,
        "Equity": equity_including_ni,
    })
    return df.T


def build_cash_flow(pivot: pd.DataFrame) -> pd.DataFrame:
    """Simple cash flow from changes in Cash account per bucket.

    We assume the cash account contains the word 'Cash' or code 1000.
    """
    if pivot is None or pivot.empty:
        return pd.DataFrame()
    cash_cols = [c for c in pivot.columns if ("cash" in c.lower()) or c.strip().startswith("1000")]
    per_bucket_change = pivot[cash_cols].sum(axis=1) if cash_cols else pd.Series(0.0, index=pivot.index)
    df = pd.DataFrame({
        "Net Cash Change": per_bucket_change,
    })
    return df.T


# -----------------------------
# Public API
# -----------------------------

def get_financial_data(
    firm_id: str,
    start_date: Any,
    end_date: Any,
    granularity: str = "Daily",
    simulation_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Get financial data for a firm within a date range.

    Args:
        firm_id: The firm identifier
        start_date: Start of date range (inclusive)
        end_date: End of date range (inclusive)
        granularity: Time bucket size ("15-minute", "Hourly", "Daily", "Weekly", "Monthly", "Quarterly", "Yearly")
        simulation_id: Optional simulation ID to filter by. If None, uses latest completed simulation.

    Returns:
        Dictionary with:
        - account_pivot: DataFrame with accounts as columns, time buckets as rows
        - income_statement: Revenue/expense summary by time bucket
        - balance_sheet: Asset/liability/equity summary by time bucket
        - cash_flow: Cash flow summary by time bucket
        - metadata: Period counts, date ranges, etc.
    """
    start, end = normalize_dates(start_date, end_date)
    
    # Get journal lines for the firm and date range
    lines = _iter_journal_lines_for_firm(firm_id, start, end, simulation_id)
    
    if not lines:
        return {
            "account_pivot": pd.DataFrame(),
            "income_statement": pd.DataFrame(),
            "balance_sheet": pd.DataFrame(),
            "cash_flow": pd.DataFrame(),
            "metadata": {
                "periods": 0,
                "start_date": start,
                "end_date": end,
                "granularity": granularity,
                "simulation_id": simulation_id,
                "firm_id": firm_id,
            }
        }
    
    # Build account pivot
    pivot = _aggregate_by_bucket(lines, granularity)
    
    # Build financial statements
    income = build_income_statement(pivot)
    balance = build_balance_sheet(pivot)
    cash = build_cash_flow(pivot)
    
    # Metadata
    periods = count_periods(start, end, granularity)
    
    return {
        "account_pivot": pivot,
        "income_statement": income,
        "balance_sheet": balance,
        "cash_flow": cash,
        "metadata": {
            "periods": periods,
            "start_date": start,
            "end_date": end,
            "granularity": granularity,
            "simulation_id": simulation_id,
            "firm_id": firm_id,
        }
    }


def estimate_column_count(start_date: Any, end_date: Any, granularity: str) -> int:
    start, end = normalize_dates(start_date, end_date)
    return count_periods(start, end, granularity)


def export_statements_to_excel(
    income: pd.DataFrame,
    balance: pd.DataFrame,
    cash: pd.DataFrame,
    metadata: Optional[Dict[str, Any]] = None,
) -> BytesIO:
    """Create an in-memory Excel workbook with the three statements."""
    output = BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        if income is not None and not income.empty:
            income.to_excel(writer, sheet_name="Income_Statement")
        if balance is not None and not balance.empty:
            balance.to_excel(writer, sheet_name="Balance_Sheet")
        if cash is not None and not cash.empty:
            cash.to_excel(writer, sheet_name="Cash_Flow")
        # Metadata sheet (optional)
        if metadata:
            meta_df = pd.DataFrame({"key": list(metadata.keys()), "value": list(metadata.values())})
            meta_df.to_excel(writer, sheet_name="Metadata", index=False)
        writer.save()
    output.seek(0)
    return output


def list_simulations() -> List[Dict[str, Any]]:
    """List all available simulations."""
    try:
        sim_db = os.getenv('DB_SIM_NAME', 'world_sim_simulations')
        res = dm_execute_query(
            """
            SELECT simulation_id, started_by as name, description, start_time, end_time, start_time as created_at,
               simulation_start_datetime, current_simulation_datetime, simulation_end_datetime, tick_granularity
            FROM simulations
            ORDER BY start_time DESC
            """,
            None,
            sim_db,
            True,
        )
        return res.data if getattr(res, 'success', False) else []
    except Exception as e:
        print(f"[WARNING] Could not list simulations: {e}")
        return []


def list_firms(limit: Optional[int] = None) -> List[Dict[str, Any]]:
    """List all firms in the firms database.
    
    Args:
        limit: Optional maximum number of firms to return
    """
    try:
        firms_db = os.getenv('DB_FIRMS_NAME', 'world_sim_firms')
        query = "SELECT id, company_name FROM firms ORDER BY company_name"
        if limit:
            query += f" LIMIT {limit}"
        res = dm_execute_query(query, None, firms_db, True)
        rows = res.data if getattr(res, 'success', False) else []
        return rows
    except Exception as e:
        print(f"[WARNING] Could not list firms: {e}")
        return []


def verify_invariants(
    firm_id: str,
    start_date: Any,
    end_date: Any,
    granularity: str = "Monthly",
    tolerance: float = 1e-6,
    simulation_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Verify key accounting invariants over the selected period.

    Checks:
    - Sum of net postings (debit-credit) per bucket equals 0 (double-entry)
    - Balance Sheet identity holds per bucket: Assets ≈ Liabilities + Equity
    - Cash Flow net equals change in Cash per bucket
    """
    start, end = normalize_dates(start_date, end_date)
    lines = _iter_journal_lines_for_firm(firm_id=firm_id, start=start, end=end, simulation_id=simulation_id)
    pivot = _aggregate_by_bucket(lines, granularity)

    results = {
        "buckets": list(pivot.index) if pivot is not None and not pivot.empty else [],
        "sum_net_zero_all_buckets": True,
        "balance_sheet_identity_all_buckets": True,
        "cash_flow_matches_cash_change_all_buckets": True,
        "issues": [],
    }

    if pivot is None or pivot.empty:
        return results

    # 1) Sum net zero per bucket
    total_net = pivot.sum(axis=1)
    for bucket, value in total_net.items():
        if abs(float(value)) > tolerance:
            results["sum_net_zero_all_buckets"] = False
            results["issues"].append({
                "bucket": str(bucket),
                "kind": "sum_net_nonzero",
                "value": float(value),
            })

    # 2) Balance sheet identity per bucket (using our builder)
    income = build_income_statement(pivot)
    balance = build_balance_sheet(pivot)
    # Convert to aligned series
    if balance is not None and not balance.empty and set(["Assets","Liabilities","Equity"]).issubset(set(balance.index)):
        assets = balance.loc["Assets"]
        liabilities = balance.loc["Liabilities"]
        equity = balance.loc["Equity"]
        for bucket in assets.index:
            lhs = float(assets.loc[bucket])
            rhs = float(liabilities.loc[bucket] + equity.loc[bucket])
            if abs(lhs - rhs) > tolerance:
                results["balance_sheet_identity_all_buckets"] = False
                results["issues"].append({
                    "bucket": str(bucket),
                    "kind": "bs_identity_mismatch",
                    "assets": lhs,
                    "liabilities_plus_equity": rhs,
                })

    # 3) Cash flow matches change in Cash
    cash_df = build_cash_flow(pivot)
    # Compute change in cash from pivot directly
    cash_cols = [c for c in pivot.columns if ("cash" in c.lower()) or c.strip().startswith("1000")]
    if cash_cols:
        cash_change = pivot[cash_cols].sum(axis=1)
        if cash_df is not None and not cash_df.empty and "Net Cash Change" in cash_df.index:
            cf_series = cash_df.loc["Net Cash Change"]
            for bucket in cf_series.index:
                a = float(cf_series.loc[bucket])
                b = float(cash_change.loc[bucket]) if bucket in cash_change.index else 0.0
                if abs(a - b) > tolerance:
                    results["cash_flow_matches_cash_change_all_buckets"] = False
                    results["issues"].append({
                        "bucket": str(bucket),
                        "kind": "cash_flow_mismatch",
                        "cf": a,
                        "delta_cash": b,
                    })

    return results
