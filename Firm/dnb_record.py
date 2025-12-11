#!/usr/bin/env python3
"""
DNB Record management for World_Sim.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
from datetime import datetime
import json

from Database.connection_manager import execute_firms_query
from Firm.general_firm import GeneralFirm

@dataclass
class DNBRecord:
    firm_id: str
    name: str
    address: str
    city: str
    state: str
    zip: str
    dnb_data: Dict[str, Any] = field(default_factory=dict)
    firm_state_data: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def load_by_id(cls, firm_id: str) -> "DNBRecord":
        """
        Loads a firm's DNB record and associated state data from the database by firm_id.
        Now works with the new database structure where DNB data is in separate columns.
        """
        # Get base firm data with all DNB columns
        rows = execute_firms_query(
            """
            SELECT 
                id, company_name, address, city, state, zip,
                dnb_year, dnb_national_code, dnb_county_code, dnb_state_code, dnb_city_code,
                dnb_street_address, dnb_zipcode4, dnb_mailing_address_code, dnb_mailing_address,
                dnb_mailing_city, dnb_mailing_state, dnb_mailing_zip, dnb_mailing_zipcode4,
                dnb_phone_number, dnb_principal, dnb_ddm, dnb_business_description,
                dnb_year_started, dnb_sales, dnb_sales_code, dnb_employees_this_site,
                dnb_employees_this_site_code, dnb_employees_all_sites, dnb_employees_all_sites_code,
                dnb_sic1, dnb_sic2, dnb_sic3, dnb_sic4, dnb_sic5, dnb_sic6,
                dnb_secondary_name, dnb_parent_city, dnb_parent_state, dnb_dnb_office,
                dnb_hq_dunsno, dnb_parent_dunsno, dnb_ult_dunsno, dnb_status,
                dnb_subsidiary_indicator, dnb_manufacturing, dnb_sales_growth, dnb_employment_growth,
                dnb_smsa_code, dnb_base_year_sales, dnb_base_year_employment,
                dnb_trend_year_sales, dnb_trend_year_employment, dnb_population_code,
                dnb_transaction_code, dnb_hier_code, dnb_dias_code, dnb_report_date
            FROM firms WHERE id = %s
            """,
            (firm_id,),
            fetch=True
        )
        
        if not rows:
            raise RuntimeError(f"No firm found with ID: {firm_id}")
        
        r = rows[0]
        
        # Build the address from components
        address_parts = []
        if r.get('address'):
            address_parts.append(str(r['address']))
        if r.get('city'):
            address_parts.append(str(r['city']))
        if r.get('state') and r.get('zip'):
            address_parts.append(f"{r['state']} {r['zip']}")
        elif r.get('state'):
            address_parts.append(str(r['state']))
        elif r.get('zip'):
            address_parts.append(str(r['zip']))
        
        address = ", ".join(address_parts) if address_parts else str(r.get('address', ''))
        
        # Build DNB data dictionary from separate columns
        dnb_data = {}
        dnb_fields = [
            'dnb_year', 'dnb_national_code', 'dnb_county_code', 'dnb_state_code', 'dnb_city_code',
            'dnb_street_address', 'dnb_zipcode4', 'dnb_mailing_address_code', 'dnb_mailing_address',
            'dnb_mailing_city', 'dnb_mailing_state', 'dnb_mailing_zip', 'dnb_mailing_zipcode4',
            'dnb_phone_number', 'dnb_principal', 'dnb_ddm', 'dnb_business_description',
            'dnb_year_started', 'dnb_sales', 'dnb_sales_code', 'dnb_employees_this_site',
            'dnb_employees_this_site_code', 'dnb_employees_all_sites', 'dnb_employees_all_sites_code',
            'dnb_sic1', 'dnb_sic2', 'dnb_sic3', 'dnb_sic4', 'dnb_sic5', 'dnb_sic6',
            'dnb_secondary_name', 'dnb_parent_city', 'dnb_parent_state', 'dnb_dnb_office',
            'dnb_hq_dunsno', 'dnb_parent_dunsno', 'dnb_ult_dunsno', 'dnb_status',
            'dnb_subsidiary_indicator', 'dnb_manufacturing', 'dnb_sales_growth', 'dnb_employment_growth',
            'dnb_smsa_code', 'dnb_base_year_sales', 'dnb_base_year_employment',
            'dnb_trend_year_sales', 'dnb_trend_year_employment', 'dnb_population_code',
            'dnb_transaction_code', 'dnb_hier_code', 'dnb_dias_code', 'dnb_report_date'
        ]
        
        for field in dnb_fields:
            if r.get(field) is not None:
                # Convert field name back to original DNB format
                original_name = field.replace('dnb_', '').upper()
                dnb_data[original_name] = r[field]
        
        # Add some legacy field names for compatibility
        if r.get('dnb_principal'):
            dnb_data['PRINCIPAL'] = r['dnb_principal']
        if r.get('dnb_business_description'):
            dnb_data['BUSINESSDESCRIPTION'] = r['dnb_business_description']
        if r.get('dnb_year_started'):
            dnb_data['YEARSTARTED'] = r['dnb_year_started']
        if r.get('dnb_sales'):
            dnb_data['SLS'] = r['dnb_sales']
        if r.get('dnb_employees_all_sites'):
            dnb_data['EMPLOYEESALLSITES'] = r['dnb_employees_all_sites']
        if r.get('dnb_employees_this_site'):
            dnb_data['EMPLOYEESTHISSITE'] = r['dnb_employees_this_site']
        if r.get('dnb_sales_growth'):
            dnb_data['SALESGROWTH'] = r['dnb_sales_growth']
        if r.get('dnb_employment_growth'):
            dnb_data['EMPLOYMENTGROWTH'] = r['dnb_employment_growth']
        
        # Get firm state data
        firm_state_data = {}
        try:
            firm_state_rows = execute_firms_query(
                "SELECT * FROM firm_states WHERE firm_id = %s ORDER BY id DESC LIMIT 1",
                (firm_id,),
                fetch=True
            )
            if firm_state_rows:
                firm_state_data = firm_state_rows[0]
                # Ensure inventory and prices are dicts
                for key in ["inventory", "prices", "costs", "orders"]:
                    if key in firm_state_data and isinstance(firm_state_data[key], str):
                        try:
                            firm_state_data[key] = json.loads(firm_state_data[key])
                        except json.JSONDecodeError:
                            firm_state_data[key] = {}
        except Exception:
            pass # Firm state table might not exist yet or query fails

        return cls(
            firm_id=str(r['id']),
            name=str(r['company_name']),
            address=address,
            city=str(r.get('city', '')),
            state=str(r.get('state', '')),
            zip=str(r.get('zip', '')),
            dnb_data=dnb_data,
            firm_state_data=firm_state_data
        )

    def to_general_firm(self) -> GeneralFirm:
        """Converts the DNBRecord into a GeneralFirm instance."""
        firm = GeneralFirm(
            firm_id=self.firm_id,
            name=self.name,
            address=self.address,
            city=self.city,
            state=self.state,
            zip=self.zip,
            dnb_record=self.dnb_data
        )
        
        # Initialize finances from firm_state_data if available
        if self.firm_state_data:
            firm.finances.balances["1000 Cash"] = float(self.firm_state_data.get("cash", 0.0))
            firm.finances.balances["1100 Accounts Receivable"] = float(self.firm_state_data.get("ar", 0.0))
            
            inv_total = 0.0
            inventory_items = self.firm_state_data.get("inventory", {})
            costs_items = self.firm_state_data.get("costs", {})
            for sku, qty in inventory_items.items():
                unit_cost = float(costs_items.get(sku, 0.0))
                inv_total += float(qty) * unit_cost
            firm.finances.balances["1200 Inventory"] = inv_total
            
            ap = float(self.firm_state_data.get("ap", 0.0))
            if ap:
                firm.finances.balances["2000 Accounts Payable"] = -ap
            
            firm.finances.snapshot_opening()
        

        if self.dnb_data.get("BUSINESSDESCRIPTION", "").lower().find("grocery") != -1:
            firm.org_chart.init_basic_grocery_org(principal_name=self.dnb_data.get("PRINCIPAL", "Owner"))

        return firm

    def get_firm_data(self) -> Dict[str, Any]:
        """Returns the raw firm data including DNB and firm state."""
        return {
            "id": self.firm_id,
            "name": self.name,
            "address": self.address,
            "city": self.city,
            "state": self.state,
            "zip": self.zip,
            "dnb": self.dnb_data,
            "firm_state": self.firm_state_data
        }
