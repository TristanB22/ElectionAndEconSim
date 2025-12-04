#!/usr/bin/env python3
"""
Populate database with sample financial transactions for testing the dashboard.

Creates realistic journal entries for a grocery store over several months.
"""

import json
from datetime import datetime, timedelta
import random

from Database.database_manager import execute_query as dm_execute_query
import os
from .engine import ensure_reporting_schema, ensure_firm_exists


def populate_sample_data():
    """Insert sample financial transactions for testing."""
    
    # Sample firm ID (should match one in the database)
    firm_id = "893427615"  # Maple Market Grocery
    firm_name = "Maple Market Grocery"
    
    # Ensure schema and firm row exist
    ensure_reporting_schema()
    ensure_firm_exists(firm_id, firm_name)
    
    # Generate 6 months of data
    start_date = datetime.now() - timedelta(days=180)
    end_date = datetime.now()
    
    # Sample transactions
    transactions = []
    
    # Monthly recurring transactions
    current_date = start_date
    while current_date <= end_date:
        # Sales revenue
        daily_sales = random.randint(8000, 12000)
        transactions.append({
            "date": current_date.strftime("%Y-%m-%d"),
            "description": f"Daily sales for {current_date.strftime('%B %Y')}",
            "entries": [
                {"account": "1000 Cash", "debit": daily_sales, "credit": 0},
                {"account": "4000 Revenue", "debit": 0, "credit": daily_sales}
            ]
        })
        
        # COGS
        cogs = int(daily_sales * 0.65)  # 65% COGS ratio
        transactions.append({
            "date": current_date.strftime("%Y-%m-%d"),
            "description": f"COGS for {current_date.strftime('%B %Y')}",
            "entries": [
                {"account": "5000 COGS", "debit": cogs, "credit": 0},
                {"account": "1200 Inventory", "debit": 0, "credit": cogs}
            ]
        })
        
        # Operating expenses (every 2 weeks)
        if current_date.day in [1, 15]:
            rent = 5000
            utilities = random.randint(800, 1200)
            payroll = random.randint(12000, 15000)
            
            transactions.append({
                "date": current_date.strftime("%Y-%m-%d"),
                "description": f"Monthly expenses for {current_date.strftime('%B %Y')}",
                "entries": [
                    {"account": "6000 Rent Expense", "debit": rent, "credit": 0},
                    {"account": "6100 Utilities Expense", "debit": utilities, "credit": 0},
                    {"account": "6200 Payroll Expense", "debit": payroll, "credit": 0},
                    {"account": "1000 Cash", "debit": 0, "credit": rent + utilities + payroll}
                ]
            })
        
        # Inventory purchases (weekly)
        if current_date.weekday() == 0:  # Monday
            inventory_purchase = random.randint(3000, 5000)
            transactions.append({
                "date": current_date.strftime("%Y-%m-%d"),
                "description": f"Weekly inventory purchase for {current_date.strftime('%B %Y')}",
                "entries": [
                    {"account": "1200 Inventory", "debit": inventory_purchase, "credit": 0},
                    {"account": "1000 Cash", "debit": 0, "credit": inventory_purchase}
                ]
            })
        
        current_date += timedelta(days=1)
    
    # Insert transactions
    inserted_count = 0
    for i, transaction in enumerate(transactions):
        try:
            # Create journal entries
            journal_entries = []
            for entry in transaction["entries"]:
                journal_entries.append({
                    "account": entry["account"],
                    "debit": entry["debit"],
                    "credit": entry["credit"],
                    "description": transaction["description"]
                })
            
            # Insert into action_log table in simulations database
            execute_sim_query(
                """
                INSERT INTO action_log (
                    simulation_id, agent_id, action_name, action_params, 
                    events_generated, journal_entries, status, timestamp
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                params=(
                    "sample_simulation",  # simulation_id
                    "system",  # agent_id
                    "financial_transaction",  # action_name
                    json.dumps({"transaction_date": transaction["date"]}),  # action_params
                    json.dumps([{"type": "transaction", "amount": sum(e["debit"] + e["credit"] for e in transaction["entries"])}]),  # events_generated
                    json.dumps(journal_entries),  # journal_entries
                    "success",  # status
                    transaction["date"] + " 12:00:00"  # timestamp
                ),
                fetch=False
            )
            
            inserted_count += 1
            
        except Exception as e:
            print(f"Failed to insert transaction {i}: {e}")
            continue
    
    print(f"Inserted {inserted_count} sample transactions")
    return inserted_count


if __name__ == "__main__":
    print("Populating database with sample financial data...")
    count = populate_sample_data()
    print(f"Completed! Inserted {count} transactions.")
