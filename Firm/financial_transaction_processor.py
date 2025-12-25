#!/usr/bin/env python3
"""
Financial Transaction Processor for World_Sim

This module processes transactions and automatically generates proper journal entries
for the enhanced financial management system.
"""

from __future__ import annotations
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, date
import uuid
import logging

from .enhanced_finances import EnhancedFinances, JournalEntry

logger = logging.getLogger(__name__)

class FinancialTransactionProcessor:
    """
    Processes transactions and automatically generates journal entries.
    Integrates with the existing PlanExecutor transaction logging.
    """
    
    def __init__(self, firm_id: str):
        self.firm_id = firm_id
        self.enhanced_finances = EnhancedFinances(firm_id)
        self.transaction_counter = 0
    
    def _generate_transaction_id(self) -> str:
        """Generate a unique transaction ID."""
        self.transaction_counter += 1
        return f"txn_{self.firm_id}_{self.transaction_counter}_{uuid.uuid4().hex[:8]}"
    
    def process_retail_sale(self, transaction_data: Dict[str, Any]) -> Tuple[bool, List[str], List[JournalEntry]]:
        """
        Process a retail sale transaction and generate appropriate journal entries.
        
        Args:
            transaction_data: Transaction data from PlanExecutor
            
        Returns:
            Tuple of (success, errors, journal_entries)
        """
        try:
            # Generate transaction ID if not present
            if 'transaction_id' not in transaction_data:
                transaction_data['transaction_id'] = self._generate_transaction_id()
            
            # Generate journal entries
            journal_entries = self.enhanced_finances.generate_retail_sale_journal_entries(transaction_data)
            
            # Post all journal entries
            errors = []
            for entry in journal_entries:
                success, entry_errors = self.enhanced_finances.post_journal_entry(entry)
                if not success:
                    errors.extend(entry_errors)
            
            if errors:
                return False, errors, journal_entries
            
            logger.info(f"Successfully processed retail sale transaction {transaction_data['transaction_id']}")
            return True, [], journal_entries
            
        except Exception as e:
            error_msg = f"Error processing retail sale transaction: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return False, [error_msg], []
    
    def process_inventory_purchase(self, transaction_data: Dict[str, Any]) -> Tuple[bool, List[str], List[JournalEntry]]:
        """
        Process an inventory purchase transaction.
        
        Args:
            transaction_data: Transaction data with inventory purchase details
            
        Returns:
            Tuple of (success, errors, journal_entries)
        """
        try:
            # Generate transaction ID if not present
            if 'transaction_id' not in transaction_data:
                transaction_data['transaction_id'] = self._generate_transaction_id()
            
            # Extract transaction details
            amount = float(transaction_data.get('amount', 0))
            items = transaction_data.get('metadata', {}).get('items', {})
            
            # Create journal entry for inventory purchase
            purchase_entry = JournalEntry(
                entry_id=f"purchase_{transaction_data['transaction_id']}",
                date=datetime.now(),
                description=f"Inventory purchase from {transaction_data.get('from_entity', 'supplier')}",
                reference=transaction_data['transaction_id'],
                lines=[
                    {
                        'account_code': '1200',  # Inventory
                        'debit_amount': amount,
                        'credit_amount': 0,
                        'description': 'Inventory purchased'
                    },
                    {
                        'account_code': '1000',  # Cash
                        'debit_amount': 0,
                        'credit_amount': amount,
                        'description': 'Cash paid for inventory'
                    }
                ],
                metadata=transaction_data
            )
            
            # Post the journal entry
            success, errors = self.enhanced_finances.post_journal_entry(purchase_entry)
            
            if success:
                logger.info(f"Successfully processed inventory purchase transaction {transaction_data['transaction_id']}")
                return True, [], [purchase_entry]
            else:
                return False, errors, [purchase_entry]
                
        except Exception as e:
            error_msg = f"Error processing inventory purchase transaction: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return False, [error_msg], []
    
    def process_expense_payment(self, transaction_data: Dict[str, Any]) -> Tuple[bool, List[str], List[JournalEntry]]:
        """
        Process an expense payment transaction.
        
        Args:
            transaction_data: Transaction data with expense details
            
        Returns:
            Tuple of (success, errors, journal_entries)
        """
        try:
            # Generate transaction ID if not present
            if 'transaction_id' not in transaction_data:
                transaction_data['transaction_id'] = self._generate_transaction_id()
            
            # Extract transaction details
            amount = float(transaction_data.get('amount', 0))
            expense_type = transaction_data.get('metadata', {}).get('expense_type', 'operating_expense')
            
            # Map expense type to account code
            expense_account_map = {
                'wages': '6100',      # Wages and Salaries
                'rent': '6200',       # Rent Expense
                'utilities': '6300',  # Utilities
                'depreciation': '6400', # Depreciation
                'general': '6000'     # Operating Expenses
            }
            
            expense_account = expense_account_map.get(expense_type, '6000')
            
            # Create journal entry for expense payment
            expense_entry = JournalEntry(
                entry_id=f"expense_{transaction_data['transaction_id']}",
                date=datetime.now(),
                description=f"Expense payment: {expense_type}",
                reference=transaction_data['transaction_id'],
                lines=[
                    {
                        'account_code': expense_account,
                        'debit_amount': amount,
                        'credit_amount': 0,
                        'description': f'Expense: {expense_type}'
                    },
                    {
                        'account_code': '1000',  # Cash
                        'debit_amount': 0,
                        'credit_amount': amount,
                        'description': 'Cash paid for expense'
                    }
                ],
                metadata=transaction_data
            )
            
            # Post the journal entry
            success, errors = self.enhanced_finances.post_journal_entry(expense_entry)
            
            if success:
                logger.info(f"Successfully processed expense payment transaction {transaction_data['transaction_id']}")
                return True, [], [expense_entry]
            else:
                return False, errors, [expense_entry]
                
        except Exception as e:
            error_msg = f"Error processing expense payment transaction: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return False, [error_msg], []
    
    def initialize_firm_finances(self, initial_cash: float, initial_inventory: Dict[str, int], 
                               initial_costs: Dict[str, float], initial_equity: float = 0.0) -> None:
        """
        Initialize firm finances with opening balances.
        
        Args:
            initial_cash: Initial cash balance
            initial_inventory: Initial inventory levels by SKU
            initial_costs: Unit costs by SKU
            initial_equity: Initial equity (if not provided, will be calculated)
        """
        try:
            # Create a daily period for the current day
            today = date.today()
            period_id = f"day_{today.strftime('%Y%m%d')}"
            
            self.enhanced_finances.create_period(
                period_id=period_id,
                name=f"Day {today.strftime('%B %d, %Y')}",
                start_date=today,
                end_date=today,
                period_type="day"
            )
            
            self.enhanced_finances.set_current_period(period_id)
            
            # Set initial balances
            self.enhanced_finances.current_balances['1000'] = initial_cash  # Cash
            
            # Calculate initial inventory value
            total_inventory_value = 0.0
            for sku, qty in initial_inventory.items():
                unit_cost = float(initial_costs.get(sku, 0))
                total_inventory_value += unit_cost * qty
            
            self.enhanced_finances.current_balances['1200'] = total_inventory_value  # Inventory
            
            # Set initial equity (either provided or calculated)
            if initial_equity == 0.0:
                initial_equity = initial_cash + total_inventory_value
            
            self.enhanced_finances.current_balances['3100'] = initial_equity  # Retained Earnings
            
            # Snapshot opening balances
            self.enhanced_finances.snapshot_opening_balances(period_id)
            
            logger.info(f"Initialized firm finances for {self.firm_id} with period {period_id}")
            logger.info(f"Initial balances: Cash=${initial_cash:.2f}, Inventory=${total_inventory_value:.2f}, Equity=${initial_equity:.2f}")
            
        except Exception as e:
            error_msg = f"Error initializing firm finances: {str(e)}"
            logger.error(error_msg, exc_info=True)
            raise
    
    def close_current_period(self) -> bool:
        """Close the current period by transferring net income to retained earnings."""
        try:
            if self.enhanced_finances.current_period:
                success = self.enhanced_finances.close_period(self.enhanced_finances.current_period)
                if success:
                    logger.info(f"Successfully closed period {self.enhanced_finances.current_period}")
                return success
            else:
                logger.warning("No current period set to close")
                return False
        except Exception as e:
            error_msg = f"Error closing current period: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return False

    def get_financial_statements(self) -> Dict[str, Any]:
        """Get current financial statements."""
        # Close the current period before generating statements
        self.close_current_period()
        return self.enhanced_finances.to_dict()
    
    def get_firm_financial_statements(self, firm_id: str) -> Dict[str, Any]:
        """Get financial statements for a firm (alias for get_financial_statements)."""
        return self.get_financial_statements()
    
    def get_account_balance(self, account_code: str) -> float:
        """Get current balance for a specific account."""
        return self.enhanced_finances.get_account_balance(account_code)
    
    def get_chart_of_accounts(self) -> Dict[str, Any]:
        """Get the chart of accounts structure."""
        return {
            code: {
                'name': acc.name,
                'category': acc.category,
                'subcategory': acc.subcategory,
                'normal_balance': acc.normal_balance,
                'description': acc.description
            }
            for code, acc in self.enhanced_finances.chart_of_accounts.accounts.items()
        }
