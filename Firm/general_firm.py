#!/usr/bin/env python3
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from copy import deepcopy


@dataclass
class Finances:
    """
    Minimal 3-statement model that can be updated via journal lines.
    Accounts are tracked as a simple trial balance (ending balances).
    """
    opening_balances: Dict[str, float] = field(default_factory=dict)
    balances: Dict[str, float] = field(default_factory=dict)

    def snapshot_opening(self) -> None:
        self.opening_balances = deepcopy(self.balances)

    def post_journal_lines(self, lines: List[Dict[str, Any]]) -> None:
        for line in lines:
            account = str(line.get("account", ""))
            debit = float(line.get("debit", 0.0))
            credit = float(line.get("credit", 0.0))
            # Debit increases positive balance; credit decreases (for simplicity)
            # This mirrors a TB view where assets/expenses accumulate as positive via debits,
            # and liabilities/equity/revenue accumulate as positive via credits (we'll keep signed sums).
            self.balances[account] = float(self.balances.get(account, 0.0)) + debit - credit

    # Helpers for sums
    def _sum_accounts(self, prefix: str) -> float:
        return sum(v for k, v in self.balances.items() if k.startswith(prefix))

    def _get(self, name: str) -> float:
        return float(self.balances.get(name, 0.0))

    def income_statement(self) -> Dict[str, float]:
        revenue = self._get("4000 Revenue")
        cogs = self._get("5000 COGS")
        opex = self._get("6000 Operating Expenses")
        # In our TB convention: debits positive; revenue is credits -> negative number unless netted.
        # Normalize: treat revenue as positive number
        revenue_norm = -revenue if revenue < 0 else revenue
        cogs_norm = cogs
        opex_norm = opex
        gross_profit = revenue_norm - cogs_norm
        net_income = gross_profit - opex_norm
        return {
            "revenue": revenue_norm,
            "cogs": cogs_norm,
            "gross_profit": gross_profit,
            "operating_expenses": opex_norm,
            "net_income": net_income,
        }

    def balance_sheet(self) -> Dict[str, Any]:
        assets = {
            "cash": self._get("1000 Cash"),
            "accounts_receivable": self._get("1100 Accounts Receivable"),
            "inventory": self._get("1200 Inventory"),
            "prepaid_expenses": self._get("1300 Prepaid Expenses"),
            "fixed_assets_net": self._get("1500 Fixed Assets") + self._get("1510 Accumulated Depreciation"),
        }
        liabilities = {
            "accounts_payable": -self._get("2000 Accounts Payable"),  # credits as positive liability
            "deferred_revenue": -self._get("2100 Deferred Revenue"),
            "taxes_payable": -self._get("2200 Taxes Payable"),
        }
        total_assets = sum(assets.values())
        total_liabilities = sum(liabilities.values())
        # Equity as balancing item
        equity = total_assets - total_liabilities
        return {
            "assets": assets,
            "liabilities": liabilities,
            "equity": equity,
            "total_assets": total_assets,
            "total_liabilities": total_liabilities,
        }

    def cash_flow_statement(self) -> Dict[str, float]:
        # Indirect method approximation for the test horizon
        is_dict = self.income_statement()
        net_income = is_dict["net_income"]
        # Changes in working capital (use opening vs ending)
        def bal(name: str) -> float:
            return float(self.balances.get(name, 0.0))
        def open_bal(name: str) -> float:
            return float(self.opening_balances.get(name, 0.0))
        delta_ar = bal("1100 Accounts Receivable") - open_bal("1100 Accounts Receivable")
        delta_inv = bal("1200 Inventory") - open_bal("1200 Inventory")
        delta_ap = (-bal("2000 Accounts Payable")) - (-open_bal("2000 Accounts Payable"))
        cfo = net_income - delta_ar - delta_inv + delta_ap
        # From cash balance change
        delta_cash = bal("1000 Cash") - open_bal("1000 Cash")
        # Assume no CFI/ CFF in this simple test
        return {
            "cash_from_operations": cfo,
            "net_change_in_cash": delta_cash,
        }

    def to_dict(self) -> Dict[str, Any]:
        return {
            "balances": self.balances,
            "income_statement": self.income_statement(),
            "balance_sheet": self.balance_sheet(),
            "cash_flow": self.cash_flow_statement(),
        }


@dataclass
class Role:
    title: str
    department: str
    level: int
    can_hire: bool = False
    can_fire_roles: List[str] = field(default_factory=list)


@dataclass
class Person:
    person_id: str
    name: str
    roles: List[Role] = field(default_factory=list)
    manager_id: Optional[str] = None


@dataclass
class OrgChart:
    people: Dict[str, Person] = field(default_factory=dict)

    def add_person(self, person_id: str, name: str, roles: List[Role], manager_id: Optional[str] = None) -> None:
        self.people[person_id] = Person(person_id=person_id, name=name, roles=roles, manager_id=manager_id)

    def get_person(self, person_id: str) -> Optional[Person]:
        return self.people.get(person_id)

    def get_chain_of_command(self, person_id: str) -> List[str]:
        chain: List[str] = []
        cur = self.people.get(person_id)
        while cur and cur.manager_id:
            chain.append(cur.manager_id)
            cur = self.people.get(cur.manager_id)
        return chain

    def init_basic_grocery_org(self, principal_name: str = "Owner") -> None:
        # Owner/CEO
        self.add_person(
            person_id="owner",
            name=principal_name or "Owner",
            roles=[Role(title="Owner/CEO", department="Executive", level=0, can_hire=True, can_fire_roles=["Store Manager", "Assistant Manager", "Cashier", "Stocker", "Clerk"])],
        )
        # Store manager
        self.add_person(
            person_id="mgr",
            name="Store Manager",
            roles=[Role(title="Store Manager", department="Operations", level=1, can_hire=True, can_fire_roles=["Assistant Manager", "Cashier", "Stocker", "Clerk"])],
            manager_id="owner",
        )
        # Assistant manager
        self.add_person(
            person_id="amgr",
            name="Assistant Manager",
            roles=[Role(title="Assistant Manager", department="Operations", level=2)],
            manager_id="mgr",
        )
        # Cashiers
        for i in range(1, 4):
            self.add_person(
                person_id=f"cash{i}",
                name=f"Cashier {i}",
                roles=[Role(title="Cashier", department="Front End", level=4)],
                manager_id="amgr",
            )
        # Stockers
        for i in range(1, 3):
            self.add_person(
                person_id=f"stock{i}",
                name=f"Stocker {i}",
                roles=[Role(title="Stocker", department="Operations", level=4)],
                manager_id="amgr",
            )
        # Deli clerk
        self.add_person(
            person_id="deli1",
            name="Deli Clerk",
            roles=[Role(title="Clerk", department="Deli", level=4)],
            manager_id="amgr",
        )


@dataclass
class GeneralFirm:
    """
    General firm structure with D&B identity, location, and finances.
    """
    firm_id: str
    name: str
    address: str
    city: str
    state: str
    zip: str
    dnb_record: Dict[str, Any] = field(default_factory=dict)
    finances: Finances = field(default_factory=Finances)
    org_chart: OrgChart = field(default_factory=OrgChart)

    @classmethod
    def from_dnb(cls, row: Dict[str, Any]) -> "GeneralFirm":
        return cls(
            firm_id=str(row.get("DUNSNO", "")),
            name=str(row.get("COMPANYNAME", "")),
            address=str(row.get("STREETADDRESS", "")),
            city=str(row.get("CITY", "")),
            state=str(row.get("STATE", "")),
            zip=str(row.get("ZIPCODE", "")),
            dnb_record=row,
        )

    def snapshot_opening_balances(self, world_state_firm: Dict[str, Any]) -> None:
        # Initialize balances from world state shard
        self.finances.balances["1000 Cash"] = float(world_state_firm.get("cash", 0.0))
        self.finances.balances["1100 Accounts Receivable"] = float(world_state_firm.get("ar", 0.0))
        # Inventory total: sum per-SKU
        inv_total = 0.0
        for sku, qty in (world_state_firm.get("inventory", {}) or {}).items():
            # Use costs if available to approximate inventory valuation
            unit_cost = float((world_state_firm.get("costs", {}) or {}).get(sku, 0.0))
            inv_total += float(qty) * unit_cost
        self.finances.balances["1200 Inventory"] = inv_total
        # Optional AP in world state (credit balance)
        ap = float(world_state_firm.get("ap", 0.0))
        if ap:
            self.finances.balances["2000 Accounts Payable"] = -ap
        # Zero out revenue/COGS/expenses at opening
        self.finances.balances.setdefault("4000 Revenue", 0.0)
        self.finances.balances.setdefault("5000 COGS", 0.0)
        self.finances.balances.setdefault("6000 Operating Expenses", 0.0)
        self.finances.snapshot_opening()

    def print_firm_context(self, include_financials: bool = True, include_org: bool = True, include_dnb: bool = True) -> None:
        """
        Print comprehensive firm context and information.
        
        Args:
            include_financials: Whether to include financial statements
            include_org: Whether to include organizational chart
            include_dnb: Whether to include D&B record details
        """
        print(f"\n{'='*60}")
        print(f"FIRM CONTEXT: {self.name}")
        print(f"{'='*60}")
        
        # Basic Information
        print(f"\nLOCATION:")
        print(f"   Address: {self.address}")
        print(f"   City: {self.city}")
        print(f"   State: {self.state}")
        print(f"   ZIP: {self.zip}")
        print(f"   Firm ID: {self.firm_id}")
        
        # D&B Record Information
        if include_dnb and self.dnb_record:
            print(f"\nD&B RECORD SUMMARY:")
            # Key business metrics
            if "SALESGROWTH" in self.dnb_record:
                print(f"   Sales Growth: {self.dnb_record.get('SALESGROWTH', 'N/A')}")
            if "EMPLOYMENTGROWTH" in self.dnb_record:
                print(f"   Employment Growth: {self.dnb_record.get('EMPLOYMENTGROWTH', 'N/A')}")
            if "YEARSTARTED" in self.dnb_record:
                print(f"   Year Started: {self.dnb_record.get('YEARSTARTED', 'N/A')}")
            if "EMPLOYEESALLSITES" in self.dnb_record:
                print(f"   Total Employees: {self.dnb_record.get('EMPLOYEESALLSITES', 'N/A')}")
            if "EMPLOYEESTHISSITE" in self.dnb_record:
                print(f"   This Site Employees: {self.dnb_record.get('EMPLOYEESTHISSITE', 'N/A')}")
            
            # Industry classification
            sic_codes = []
            for i in range(1, 7):
                sic_key = f"SIC{i}"
                if sic_key in self.dnb_record and self.dnb_record[sic_key]:
                    sic_codes.append(str(self.dnb_record[sic_key]))
            if sic_codes:
                print(f"   SIC Codes: {', '.join(sic_codes)}")
            
            # Business description
            if "BUSINESSDESCRIPTION" in self.dnb_record and self.dnb_record["BUSINESSDESCRIPTION"]:
                desc = str(self.dnb_record["BUSINESSDESCRIPTION"])
                if len(desc) > 100:
                    desc = desc[:100] + "..."
                print(f"   Business: {desc}")
        
        # Financial Information
        if include_financials and self.finances:
            print(f"\nFINANCIAL STATUS:")
            if self.finances.balances:
                # Key balance sheet items
                cash = self.finances.balances.get("1000 Cash", 0.0)
                ar = self.finances.balances.get("1100 Accounts Receivable", 0.0)
                inventory = self.finances.balances.get("1200 Inventory", 0.0)
                ap = -self.finances.balances.get("2000 Accounts Payable", 0.0)
                
                print(f"   Cash: ${cash:,.2f}")
                print(f"   Accounts Receivable: ${ar:,.2f}")
                print(f"   Inventory: ${inventory:,.2f}")
                print(f"   Accounts Payable: ${ap:,.2f}")
                
                # Income statement if available
                revenue = -self.finances.balances.get("4000 Revenue", 0.0)
                cogs = self.finances.balances.get("5000 COGS", 0.0)
                opex = self.finances.balances.get("6000 Operating Expenses", 0.0)
                
                if revenue != 0 or cogs != 0 or opex != 0:
                    print(f"   Revenue: ${revenue:,.2f}")
                    print(f"   COGS: ${cogs:,.2f}")
                    print(f"   Operating Expenses: ${opex:,.2f}")
                    gross_profit = revenue - cogs
                    net_income = gross_profit - opex
                    print(f"   Gross Profit: ${gross_profit:,.2f}")
                    print(f"   Net Income: ${net_income:,.2f}")
            else:
                print("   No financial data available")
        
        # Organizational Information
        if include_org and self.org_chart and self.org_chart.people:
            print(f"\nORGANIZATIONAL STRUCTURE:")
            print(f"   Total People: {len(self.org_chart.people)}")
            
            # Group by department
            dept_counts = {}
            for person in self.org_chart.people.values():
                for role in person.roles:
                    dept = role.department
                    dept_counts[dept] = dept_counts.get(dept, 0) + 1
            
            for dept, count in dept_counts.items():
                print(f"   {dept}: {count} people")
            
            # Show top-level positions
            print(f"\n   Key Positions:")
            for person in self.org_chart.people.values():
                if not person.manager_id:  # Top level
                    roles = [r.title for r in person.roles]
                    print(f"     {person.name}: {', '.join(roles)}")
        
        print(f"\n{'='*60}")

    def get_firm_summary(self) -> Dict[str, Any]:
        """
        Get a summary of key firm information as a dictionary.
        Useful for logging or API responses.
        """
        summary = {
            "firm_id": self.firm_id,
            "name": self.name,
            "location": {
                "address": self.address,
                "city": self.city,
                "state": self.state,
                "zip": self.zip
            },
            "dnb_metrics": {}
        }
        
        # Extract key D&B metrics
        if self.dnb_record:
            summary["dnb_metrics"] = {
                "sales_growth": self.dnb_record.get("SALESGROWTH"),
                "employment_growth": self.dnb_record.get("EMPLOYMENTGROWTH"),
                "year_started": self.dnb_record.get("YEARSTARTED"),
                "total_employees": self.dnb_record.get("EMPLOYEESALLSITES"),
                "site_employees": self.dnb_record.get("EMPLOYEESTHISSITE"),
                "business_description": self.dnb_record.get("BUSINESSDESCRIPTION")
            }
        
        # Add financial summary if available
        if self.finances and self.finances.balances:
            summary["financials"] = {
                "cash": self.finances.balances.get("1000 Cash", 0.0),
                "accounts_receivable": self.finances.balances.get("1100 Accounts Receivable", 0.0),
                "inventory": self.finances.balances.get("1200 Inventory", 0.0),
                "accounts_payable": -self.finances.balances.get("2000 Accounts Payable", 0.0)
            }
        
        # Add org summary if available
        if self.org_chart and self.org_chart.people:
            summary["organization"] = {
                "total_people": len(self.org_chart.people),
                "departments": {}
            }
            
            for person in self.org_chart.people.values():
                for role in person.roles:
                    dept = role.department
                    if dept not in summary["organization"]["departments"]:
                        summary["organization"]["departments"][dept] = 0
                    summary["organization"]["departments"][dept] += 1
        
        return summary


