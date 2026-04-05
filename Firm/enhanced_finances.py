#!/usr/bin/env python3
"""
Enhanced Financial Management System for World_Sim

This module provides comprehensive financial management capabilities including:
- Chart of accounts with standard accounting structure
- Period management and opening/closing balance tracking
- Automatic journal entry generation from transactions
- Real-time financial statement generation
- Double-entry accounting validation
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, date
from copy import deepcopy
import json
import logging

logger = logging.getLogger(__name__)

@dataclass
class Account:
    """Represents an account in the chart of accounts."""
    code: str
    name: str
    category: str  # asset, liability, equity, revenue, expense
    subcategory: str  # current_asset, long_term_asset, etc.
    normal_balance: str  # debit or credit
    description: str = ""
    parent_account: Optional[str] = None
    is_active: bool = True

@dataclass
class JournalEntry:
    """Represents a journal entry with multiple lines."""
    entry_id: str
    date: datetime
    description: str
    reference: str
    lines: List[Dict[str, Any]]  # List of {account_code, debit_amount, credit_amount, description}
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def validate(self) -> Tuple[bool, List[str]]:
        """Validate that debits equal credits."""
        total_debits = sum(line.get('debit_amount', 0) for line in self.lines)
        total_credits = sum(line.get('credit_amount', 0) for line in self.lines)
        
        if abs(total_debits - total_credits) > 0.01:
            return False, [f"Debits ({total_debits}) do not equal credits ({total_credits})"]
        
        return True, []
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert journal entry to dictionary for serialization."""
        return {
            'entry_id': self.entry_id,
            'date': self.date.isoformat(),
            'description': self.description,
            'reference': self.reference,
            'lines': self.lines,
            'metadata': self.metadata
        }

@dataclass
class FinancialPeriod:
    """Represents a financial reporting period."""
    period_id: str
    name: str
    start_date: date
    end_date: date
    period_type: str  # day, week, month, quarter, year
    is_closed: bool = False
    closing_date: Optional[datetime] = None

class ChartOfAccounts:
    """Manages the chart of accounts for financial reporting."""
    
    def __init__(self):
        self.accounts: Dict[str, Account] = {}
        self._initialize_standard_accounts()
    
    def _initialize_standard_accounts(self):
        """Initialize standard chart of accounts."""
        standard_accounts = [
            # Assets
            Account("1000", "Cash", "asset", "current_asset", "debit", "Cash and cash equivalents"),
            Account("1100", "Accounts Receivable", "asset", "current_asset", "debit", "Amounts owed by customers"),
            Account("1200", "Inventory", "asset", "current_asset", "debit", "Merchandise inventory"),
            Account("1300", "Prepaid Expenses", "asset", "current_asset", "debit", "Prepaid expenses and deposits"),
            Account("1500", "Fixed Assets", "asset", "long_term_asset", "debit", "Property, plant, and equipment"),
            Account("1510", "Accumulated Depreciation", "asset", "long_term_asset", "credit", "Accumulated depreciation"),
            
            # Liabilities
            Account("2000", "Accounts Payable", "liability", "current_liability", "credit", "Amounts owed to suppliers"),
            Account("2100", "Deferred Revenue", "liability", "current_liability", "credit", "Revenue received in advance"),
            Account("2200", "Taxes Payable", "liability", "current_liability", "credit", "Taxes owed to government"),
            Account("2500", "Long-term Debt", "liability", "long_term_liability", "credit", "Long-term debt obligations"),
            
            # Equity
            Account("3000", "Common Stock", "equity", "contributed_capital", "credit", "Common stock issued"),
            Account("3100", "Retained Earnings", "equity", "retained_earnings", "credit", "Accumulated earnings"),
            Account("3200", "Owner's Draw", "equity", "distributions", "debit", "Owner withdrawals"),
            
            # Revenue
            Account("4000", "Sales Revenue", "revenue", "operating_revenue", "credit", "Revenue from sales"),
            Account("4100", "Other Revenue", "revenue", "other_revenue", "credit", "Other income"),
            
            # Expenses
            Account("5000", "Cost of Goods Sold", "expense", "cost_of_sales", "debit", "Direct costs of goods sold"),
            Account("6000", "Operating Expenses", "expense", "operating_expense", "debit", "General operating expenses"),
            Account("6100", "Wages and Salaries", "expense", "operating_expense", "debit", "Employee compensation"),
            Account("6200", "Rent Expense", "expense", "operating_expense", "debit", "Facility rental costs"),
            Account("6300", "Utilities", "expense", "operating_expense", "debit", "Utility expenses"),
            Account("6400", "Depreciation", "expense", "operating_expense", "debit", "Depreciation expense"),
        ]
        
        for account in standard_accounts:
            self.accounts[account.code] = account
    
    def get_account(self, code: str) -> Optional[Account]:
        """Get account by code."""
        return self.accounts.get(code)
    
    def get_accounts_by_category(self, category: str) -> List[Account]:
        """Get all accounts in a specific category."""
        return [acc for acc in self.accounts.values() if acc.category == category]
    
    def get_accounts_by_subcategory(self, subcategory: str) -> List[Account]:
        """Get all accounts in a specific subcategory."""
        return [acc for acc in self.accounts.values() if acc.subcategory == subcategory]

class EnhancedFinances:
    """
    Enhanced financial management system with comprehensive 3-statement support.
    """
    
    def __init__(self, firm_id: str):
        self.firm_id = firm_id
        self.chart_of_accounts = ChartOfAccounts()
        
        # Account balances by period
        self.opening_balances: Dict[str, Dict[str, float]] = {}  # period -> account_code -> balance
        self.current_balances: Dict[str, float] = {}  # account_code -> current_balance
        
        # Period management
        self.current_period: Optional[str] = None
        self.periods: Dict[str, FinancialPeriod] = {}
        
        # Journal entries
        self.journal_entries: List[JournalEntry] = []
        
        # Initialize with zero balances
        self._initialize_zero_balances()
    
    def _initialize_zero_balances(self):
        """Initialize all accounts with zero balances."""
        for account_code in self.chart_of_accounts.accounts:
            self.current_balances[account_code] = 0.0
    
    def create_period(self, period_id: str, name: str, start_date: date, 
                     end_date: date, period_type: str = "day") -> str:
        """Create a new financial period."""
        period = FinancialPeriod(
            period_id=period_id,
            name=name,
            start_date=start_date,
            end_date=end_date,
            period_type=period_type
        )
        self.periods[period_id] = period
        return period_id
    
    def set_current_period(self, period_id: str):
        """Set the current financial period."""
        if period_id not in self.periods:
            raise ValueError(f"Period {period_id} not found")
        self.current_period = period_id
    
    def snapshot_opening_balances(self, period_id: str):
        """Snapshot current balances as opening balances for a period."""
        if period_id not in self.periods:
            raise ValueError(f"Period {period_id} not found")
        
        self.opening_balances[period_id] = deepcopy(self.current_balances)
        logger.info(f"Snapshotted opening balances for period {period_id}")
    
    def post_journal_entry(self, entry: JournalEntry) -> Tuple[bool, List[str]]:
        """Post a journal entry to the accounts."""
        # Validate the entry
        is_valid, errors = entry.validate()
        if not is_valid:
            return False, errors
        
        # Post each line
        for line in entry.lines:
            account_code = line.get('account_code')
            debit_amount = float(line.get('debit_amount', 0))
            credit_amount = float(line.get('credit_amount', 0))
            
            if account_code not in self.chart_of_accounts.accounts:
                errors.append(f"Invalid account code: {account_code}")
                continue
            
            # Update account balance
            net_change = debit_amount - credit_amount
            self.current_balances[account_code] = self.current_balances.get(account_code, 0) + net_change
        
        if not errors:
            self.journal_entries.append(entry)
            logger.info(f"Posted journal entry {entry.entry_id}")
        
        return len(errors) == 0, errors
    
    def generate_retail_sale_journal_entries(self, transaction_data: Dict[str, Any]) -> List[JournalEntry]:
        """Generate journal entries for a retail sale transaction."""
        entries = []
        
        # Extract transaction details
        amount = float(transaction_data.get('amount', 0))
        items = transaction_data.get('metadata', {}).get('items', {})
        costs = transaction_data.get('metadata', {}).get('costs', {})
        
        # Calculate COGS
        total_cogs = 0.0
        for sku, qty in items.items():
            unit_cost = float(costs.get(sku, 0))
            total_cogs += unit_cost * float(qty)
        
        # Create journal entry for the sale
        sale_entry = JournalEntry(
            entry_id=f"sale_{transaction_data.get('transaction_id', 'unknown')}",
            date=datetime.now(),
            description=f"Retail sale to {transaction_data.get('from_entity', 'customer')}",
            reference=transaction_data.get('transaction_id', ''),
            lines=[
                {
                    'account_code': '1000',  # Cash
                    'debit_amount': amount,
                    'credit_amount': 0,
                    'description': 'Cash received from sale'
                },
                {
                    'account_code': '4000',  # Sales Revenue
                    'debit_amount': 0,
                    'credit_amount': amount,
                    'description': 'Revenue from retail sale'
                }
            ],
            metadata=transaction_data
        )
        entries.append(sale_entry)
        
        # Create journal entry for COGS and inventory reduction
        if total_cogs > 0:
            cogs_entry = JournalEntry(
                entry_id=f"cogs_{transaction_data.get('transaction_id', 'unknown')}",
                date=datetime.now(),
                description=f"Cost of goods sold for sale {transaction_data.get('transaction_id', 'unknown')}",
                reference=transaction_data.get('transaction_id', ''),
                lines=[
                    {
                        'account_code': '5000',  # COGS
                        'debit_amount': total_cogs,
                        'credit_amount': 0,
                        'description': 'Cost of goods sold'
                    },
                    {
                        'account_code': '1200',  # Inventory
                        'debit_amount': 0,
                        'credit_amount': total_cogs,
                        'description': 'Inventory reduction'
                    }
                ],
                metadata={'cogs_calculation': {'items': items, 'costs': costs}}
            )
            entries.append(cogs_entry)
        
        return entries
    
    def get_account_balance(self, account_code: str) -> float:
        """Get current balance for an account."""
        return self.current_balances.get(account_code, 0.0)
    
    def get_period_balance(self, period_id: str, account_code: str) -> float:
        """Get balance for an account at the start of a period."""
        return self.opening_balances.get(period_id, {}).get(account_code, 0.0)
    
    def generate_income_statement(self, period_id: str) -> Dict[str, Any]:
        """Generate income statement for a specific period."""
        if period_id not in self.periods:
            raise ValueError(f"Period {period_id} not found")
        
        # Calculate period activity from journal entries (not current balances)
        total_revenue = 0.0
        total_expenses = 0.0
        
        # Get revenue and expense accounts
        revenue_accounts = self.chart_of_accounts.get_accounts_by_category('revenue')
        expense_accounts = self.chart_of_accounts.get_accounts_by_category('expense')
        
        # Calculate period activity from journal entries
        for entry in self.journal_entries:
            # Skip closing entries to avoid double-counting
            if entry.metadata and entry.metadata.get('period_closing'):
                continue
                
            for line in entry.lines:
                account_code = line.get('account_code')
                debit_amount = float(line.get('debit_amount', 0))
                credit_amount = float(line.get('credit_amount', 0))
                
                # Check if this is a revenue account
                if any(acc.code == account_code for acc in revenue_accounts):
                    total_revenue += credit_amount  # Revenue increases with credits
                
                # Check if this is an expense account
                if any(acc.code == account_code for acc in expense_accounts):
                    total_expenses += debit_amount  # Expenses increase with debits
        
        # Calculate net income
        net_income = total_revenue - total_expenses
        
        return {
            'period': period_id,
            'revenue': {
                'total': total_revenue,
                'breakdown': {acc.code: total_revenue if acc.code == '4000' else 0.0 for acc in revenue_accounts}
            },
            'expenses': {
                'total': total_expenses,
                'breakdown': {acc.code: total_expenses if acc.code == '5000' else 0.0 for acc in expense_accounts}
            },
            'net_income': net_income
        }
    
    def generate_balance_sheet(self, as_of_date: datetime = None) -> Dict[str, Any]:
        """Generate balance sheet as of a specific date."""
        if as_of_date is None:
            as_of_date = datetime.now()
        
        # Assets
        assets = {
            'current_assets': {
                'cash': self.get_account_balance('1000'),
                'accounts_receivable': self.get_account_balance('1100'),
                'inventory': self.get_account_balance('1200'),
                'prepaid_expenses': self.get_account_balance('1300')
            },
            'long_term_assets': {
                'fixed_assets': self.get_account_balance('1500'),
                'accumulated_depreciation': self.get_account_balance('1510')
            }
        }
        
        # Liabilities
        liabilities = {
            'current_liabilities': {
                'accounts_payable': abs(self.get_account_balance('2000')),  # Convert negative to positive
                'deferred_revenue': abs(self.get_account_balance('2100')),  # Convert negative to positive
                'taxes_payable': abs(self.get_account_balance('2200'))     # Convert negative to positive
            },
            'long_term_liabilities': {
                'long_term_debt': abs(self.get_account_balance('2500'))    # Convert negative to positive
            }
        }
        
        # Equity
        equity = {
            'common_stock': self.get_account_balance('3000'),
            'retained_earnings': self.get_account_balance('3100'),
            'owners_draw': self.get_account_balance('3200')
        }
        
        # Calculate totals
        total_current_assets = sum(assets['current_assets'].values())
        total_long_term_assets = sum(assets['long_term_assets'].values())
        total_assets = total_current_assets + total_long_term_assets
        
        total_current_liabilities = sum(liabilities['current_liabilities'].values())
        total_long_term_liabilities = sum(liabilities['long_term_liabilities'].values())
        total_liabilities = total_current_liabilities + total_long_term_liabilities
        
        total_equity = sum(equity.values())
        
        return {
            'as_of_date': as_of_date,
            'assets': assets,
            'liabilities': liabilities,
            'equity': equity,
            'totals': {
                'total_assets': total_assets,
                'total_liabilities': total_liabilities,
                'total_equity': total_equity
            }
        }
    
    def generate_cash_flow_statement(self, period_id: str) -> Dict[str, Any]:
        """Generate cash flow statement for a specific period."""
        if period_id not in self.periods:
            raise ValueError(f"Period {period_id} not found")
        
        # Get income statement
        income_stmt = self.generate_income_statement(period_id)
        net_income = income_stmt['net_income']
        
        # Calculate changes in working capital
        opening_balances = self.opening_balances.get(period_id, {})
        
        delta_ar = self.get_account_balance('1100') - opening_balances.get('1100', 0)
        delta_inventory = self.get_account_balance('1200') - opening_balances.get('1200', 0)
        delta_ap = self.get_account_balance('2000') - opening_balances.get('2000', 0)
        
        # Operating cash flow
        operating_cash_flow = net_income - delta_ar - delta_inventory + delta_ap
        
        # Investing and financing (simplified for now)
        investing_cash_flow = 0.0  # No capex in current model
        financing_cash_flow = 0.0  # No debt/equity transactions in current model
        
        # Net change in cash
        net_change_in_cash = operating_cash_flow + investing_cash_flow + financing_cash_flow
        
        return {
            'period': period_id,
            'operating_activities': {
                'net_income': net_income,
                'changes_in_working_capital': {
                    'accounts_receivable': -delta_ar,
                    'inventory': -delta_inventory,
                    'accounts_payable': delta_ap
                },
                'net_cash_from_operating': operating_cash_flow
            },
            'investing_activities': {
                'net_cash_from_investing': investing_cash_flow
            },
            'financing_activities': {
                'net_cash_from_financing': financing_cash_flow
            },
            'net_change_in_cash': net_change_in_cash
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert financial data to dictionary for serialization."""
        return {
            'firm_id': self.firm_id,
            'current_period': self.current_period,
            'current_balances': self.current_balances,
            'opening_balances': self.opening_balances,
            'periods': {pid: {
                'name': p.name,
                'start_date': p.start_date.isoformat(),
                'end_date': p.end_date.isoformat(),
                'period_type': p.period_type,
                'is_closed': p.is_closed
            } for pid, p in self.periods.items()},
            'income_statement': self.generate_income_statement(self.current_period) if self.current_period else None,
            'balance_sheet': self.generate_balance_sheet(),
            'cash_flow': self.generate_cash_flow_statement(self.current_period) if self.current_period else None
        }

    def close_period(self, period_id: str) -> bool:
        """Close a period by transferring net income to retained earnings."""
        if period_id not in self.periods:
            return False
        
        try:
            # Get income statement for the period
            income_stmt = self.generate_income_statement(period_id)
            net_income = income_stmt['net_income']
            
            if net_income != 0:
                # Create closing entry to transfer net income to retained earnings
                closing_entry = JournalEntry(
                    entry_id=f"closing_{period_id}",
                    date=datetime.now(),
                    description=f"Period closing entry for {period_id}",
                    reference=period_id,
                    lines=[
                        {
                            'account_code': '4000',  # Sales Revenue
                            'debit_amount': abs(self.get_account_balance('4000')),
                            'credit_amount': 0,
                            'description': 'Close revenue to retained earnings'
                        },
                        {
                            'account_code': '5000',  # COGS
                            'debit_amount': 0,
                            'credit_amount': abs(self.get_account_balance('5000')),
                            'description': 'Close COGS to retained earnings'
                        },
                        {
                            'account_code': '3100',  # Retained Earnings
                            'debit_amount': 0,
                            'credit_amount': net_income,
                            'description': 'Net income transferred to retained earnings'
                        }
                    ],
                    metadata={'period_closing': True, 'net_income': net_income}
                )
                
                # Post the closing entry
                success, errors = self.post_journal_entry(closing_entry)
                if success:
                    logger.info(f"Successfully closed period {period_id} with net income ${net_income:.2f}")
                    return True
                else:
                    logger.error(f"Failed to close period {period_id}: {errors}")
                    return False
            else:
                logger.info(f"Period {period_id} has no net income to close")
                return True
                
        except Exception as e:
            logger.error(f"Error closing period {period_id}: {str(e)}")
            return False
