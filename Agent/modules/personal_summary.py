#!/usr/bin/env python3
"""
Personal Summary Module

Generates comprehensive personal summaries for agents from L2 data.
"""

import os
import json
import re
import pandas as pd
from typing import Dict, Any, Optional, List
from Utils.api_manager import APIManager
from Utils.l2_data.l2_data_objects import L2DataRow

class PersonalSummaryGenerator:
    """Generates comprehensive personal summaries for agents."""
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize the generator with API access."""
        # Automatically load API key from environment if not provided
        if api_key is None:
            import os
            api_key = os.getenv('OPENROUTER_KEY')
        
        self.api_manager = APIManager(api_key) if api_key else None
        
    def create_comprehensive_l2_summary(self, agent) -> str:
        """Create a comprehensive summary using ALL L2 data fields."""
        if not agent.l2_data:
            return "No L2 data available"
        
        summary_parts = []
        
        # Personal Information
        personal_info = self._extract_personal_info(agent)
        if personal_info:
            summary_parts.append("PERSONAL INFORMATION:")
            summary_parts.extend(personal_info)
        
        # Address Information
        address_info = self._extract_address_info(agent)
        if address_info:
            summary_parts.append("\nADDRESS INFORMATION:")
            summary_parts.extend(address_info)
        
        # Political Information
        political_info = self._extract_political_info(agent)
        if political_info:
            summary_parts.append("\nPOLITICAL INFORMATION:")
            summary_parts.extend(political_info)
        
        # Economic Information
        economic_info = self._extract_economic_info(agent)
        if economic_info:
            summary_parts.append("\nECONOMIC INFORMATION:")
            summary_parts.extend(economic_info)
        
        # Family Information
        family_info = self._extract_family_info(agent)
        if family_info:
            summary_parts.append("\nFAMILY INFORMATION:")
            summary_parts.extend(family_info)
        
        # Work Information
        work_info = self._extract_work_info(agent)
        if work_info:
            summary_parts.append("\nWORK INFORMATION:")
            summary_parts.extend(work_info)
        
        # Consumer Information
        consumer_info = self._extract_consumer_info(agent)
        if consumer_info:
            summary_parts.append("\nCONSUMER INFORMATION:")
            summary_parts.extend(consumer_info)
        
        # Geographic Information
        geographic_info = self._extract_geographic_info(agent)
        if geographic_info:
            summary_parts.append("\nGEOGRAPHIC INFORMATION:")
            summary_parts.extend(geographic_info)
        
        # Election History Information
        election_history_info = self._extract_election_history(agent)
        if election_history_info:
            summary_parts.append("\nELECTION HISTORY:")
            summary_parts.extend(election_history_info)
        
        # FEC Donor Information
        fec_donor_info = self._extract_fec_donor_info(agent)
        if fec_donor_info:
            summary_parts.append("\nFEC DONOR INFORMATION:")
            summary_parts.extend(fec_donor_info)
        
        # Market Area Information
        market_area_info = self._extract_market_area_info(agent)
        if market_area_info:
            summary_parts.append("\nMARKET AREA INFORMATION:")
            summary_parts.extend(market_area_info)
        
        # Phone Information
        phone_info = self._extract_phone_info(agent)
        if phone_info:
            summary_parts.append("\nPHONE INFORMATION:")
            summary_parts.extend(phone_info)
        
        # Mobile Advertising Information
        mobile_advertising_info = self._extract_mobile_advertising_info(agent)
        if mobile_advertising_info:
            summary_parts.append("\nMOBILE ADVERTISING INFORMATION:")
            summary_parts.extend(mobile_advertising_info)
        
        # Judicial Districts Information
        judicial_districts_info = self._extract_judicial_districts_info(agent)
        if judicial_districts_info:
            summary_parts.append("\nJUDICIAL DISTRICTS:")
            summary_parts.extend(judicial_districts_info)
        
        # School Districts Information
        school_districts_info = self._extract_school_districts_info(agent)
        if school_districts_info:
            summary_parts.append("\nSCHOOL DISTRICTS:")
            summary_parts.extend(school_districts_info)
        
        # Special Districts Information
        special_districts_info = self._extract_special_districts_info(agent)
        if special_districts_info:
            summary_parts.append("\nSPECIAL DISTRICTS:")
            summary_parts.extend(special_districts_info)
        
        return "\n".join(str(part) for part in summary_parts)
    
    def _safe_int_convert(self, value) -> int:
        """Safely convert a value to integer, handling floats and strings."""
        if value is None or pd.isna(value):
            return None
        try:
            # Convert to float first, then to int to handle cases like "39872.0"
            return int(float(value))
        except (ValueError, TypeError):
            return None
    
    def _prune_for_prompt(self, value, parent_key: Optional[str] = None):
        """Recursively prune prompt data:
        - Drop None/NaN values
        - Drop empty strings and strings equal to 'null'/'none'/'nan'
        - Drop empty lists/dicts
        - For boolean availability-style keys (e.g., contains 'available', starts with 'has_', or equals 'do_not_call'),
          only keep if True; omit if False/None
        """
        # Handle pandas NA
        try:
            if pd.isna(value):
                return None
        except Exception:
            pass
        
        # Dict: prune children
        if isinstance(value, dict):
            pruned = {}
            for k, v in value.items():
                cleaned = self._prune_for_prompt(v, parent_key=str(k) if k is not None else None)
                if cleaned is not None:
                    pruned[k] = cleaned
            return pruned if len(pruned) > 0 else None
        
        # List/Tuple: prune items
        if isinstance(value, (list, tuple)):
            pruned_items = []
            for item in value:
                cleaned = self._prune_for_prompt(item, parent_key=parent_key)
                if cleaned is not None:
                    pruned_items.append(cleaned)
            return pruned_items if len(pruned_items) > 0 else None
        
        # Strings: drop empties and explicit null-like values
        if isinstance(value, str):
            s = value.strip()
            if s == "" or s.lower() in {"null", "none", "nan"}:
                return None
            return s
        
        # Booleans: special handling for availability-style keys
        if isinstance(value, bool):
            key = (parent_key or "").lower()
            if ("available" in key) or key.startswith("has_") or key == "do_not_call":
                return True if value is True else None
            return value
        
        # Numbers: keep unless NaN (handled earlier)
        return value
    
    def _extract_personal_info(self, agent) -> List[str]:
        """Extract comprehensive personal information."""
        info = []
        data = agent.l2_data.personal
        
        if data.first_name and data.last_name:
            name_parts = [str(data.first_name)]
            if data.middle_name:
                name_parts.append(str(data.middle_name))
            name_parts.append(str(data.last_name))
            if data.name_suffix:
                name_parts.append(str(data.name_suffix))
            info.append(f"Name: {' '.join(name_parts)}")
        
        if data.age is not None and not pd.isna(data.age):
            age_int = self._safe_int_convert(data.age)
            if age_int is not None:
                info.append(f"Age: {age_int}")
        
        if data.gender:
            gender_map = {'F': 'Female', 'M': 'Male'}
            gender = gender_map.get(str(data.gender), str(data.gender))
            info.append(f"Gender: {gender}")
        
        if data.birth_date:
            info.append(f"Birth Date: {str(data.birth_date)}")
        
        if data.birth_date_confidence:
            info.append(f"Birth Date Confidence: {str(data.birth_date_confidence)}")
        
        if data.place_of_birth:
            info.append(f"Place of Birth: {str(data.place_of_birth)}")
        
        if data.ethnicity:
            info.append(f"Ethnicity: {str(data.ethnicity)}")
        
        if data.ethnic_group_1_desc:
            info.append(f"Ethnic Group: {str(data.ethnic_group_1_desc)}")
        
        if data.hispanic_country_code:
            info.append(f"Hispanic Country Code: {str(data.hispanic_country_code)}")
        
        if data.language_code:
            info.append(f"Language: {str(data.language_code)}")
        
        if data.marital_status:
            info.append(f"Marital Status: {str(data.marital_status)}")
        
        if data.religion_code:
            info.append(f"Religion: {str(data.religion_code)}")
        
        if data.inferred_hh_rank:
            info.append(f"Household Rank: {str(data.inferred_hh_rank)}")
        
        # Additional voter identification fields
        if data.state_voter_id:
            info.append(f"State Voter ID: {str(data.state_voter_id)}")
        
        if data.county_voter_id:
            info.append(f"County Voter ID: {str(data.county_voter_id)}")
        
        if data.sequence_zigzag:
            info.append(f"Sequence ZigZag: {str(data.sequence_zigzag)}")
        
        if data.sequence_odd_even:
            info.append(f"Sequence Odd/Even: {str(data.sequence_odd_even)}")
        
        if data.fips:
            info.append(f"FIPS Code: {str(data.fips)}")
        
        # County ethnic information
        if data.county_ethnic_description:
            info.append(f"County Ethnic Description: {str(data.county_ethnic_description)}")
        
        if data.county_ethnic_lal_code:
            info.append(f"County Ethnic LAL Code: {str(data.county_ethnic_lal_code)}")
        
        # Moved from information
        if data.moved_from_date:
            info.append(f"Moved From Date: {str(data.moved_from_date)}")
        
        if data.moved_from_state:
            info.append(f"Moved From State: {str(data.moved_from_state)}")
        
        if data.moved_from_party:
            info.append(f"Moved From Party: {str(data.moved_from_party)}")
        
        if data.moved_from_voting_performance_combined:
            info.append(f"Moved From Voting Performance Combined: {str(data.moved_from_voting_performance_combined)}")
        
        if data.moved_from_voting_performance_general:
            info.append(f"Moved From Voting Performance General: {str(data.moved_from_voting_performance_general)}")
        
        if data.moved_from_voting_performance_primary:
            info.append(f"Moved From Voting Performance Primary: {str(data.moved_from_voting_performance_primary)}")
        
        if data.moved_from_voting_performance_minor:
            info.append(f"Moved From Voting Performance Minor: {str(data.moved_from_voting_performance_minor)}")
        
        return info
    
    def _extract_address_info(self, agent) -> List[str]:
        """Extract comprehensive address information."""
        info = []
        data = agent.l2_data.address
        
        # Residence address
        if data.residence_address_line:
            info.append(f"Residence: {str(data.residence_address_line)}")
        
        if data.residence_extra_address_line:
            info.append(f"Residence Extra: {str(data.residence_extra_address_line)}")
        
        if data.residence_city and data.residence_state:
            info.append(f"Residence City: {str(data.residence_city)}, {str(data.residence_state)}")
        
        if data.residence_zip:
            info.append(f"Residence ZIP: {str(data.residence_zip)}")
        
        if data.residence_zip_plus4:
            info.append(f"Residence ZIP+4: {str(data.residence_zip_plus4)}")
        
        if data.residence_dpbc:
            info.append(f"Residence DPBC: {str(data.residence_dpbc)}")
        
        if data.residence_check_digit:
            info.append(f"Residence Check Digit: {str(data.residence_check_digit)}")
        
        if data.residence_house_number:
            info.append(f"Residence House Number: {str(data.residence_house_number)}")
        
        if data.residence_prefix_direction:
            info.append(f"Residence Prefix Direction: {str(data.residence_prefix_direction)}")
        
        if data.residence_street_name:
            info.append(f"Residence Street Name: {str(data.residence_street_name)}")
        
        if data.residence_designator:
            info.append(f"Residence Designator: {str(data.residence_designator)}")
        
        if data.residence_suffix_direction:
            info.append(f"Residence Suffix Direction: {str(data.residence_suffix_direction)}")
        
        if data.residence_apartment_num:
            info.append(f"Residence Apartment Number: {str(data.residence_apartment_num)}")
        
        if data.residence_apartment_type:
            info.append(f"Residence Apartment Type: {str(data.residence_apartment_type)}")
        
        if data.residence_cass_err_stat_code:
            info.append(f"Residence CASS Error Status: {str(data.residence_cass_err_stat_code)}")
        
        if data.residence_county:
            info.append(f"Residence County: {str(data.residence_county)}")
        
        if data.residence_congressional_district:
            info.append(f"Residence Congressional District: {str(data.residence_congressional_district)}")
        
        if data.residence_census_tract:
            info.append(f"Census Tract: {str(data.residence_census_tract)}")
        
        if data.residence_census_block_group:
            info.append(f"Census Block Group: {str(data.residence_census_block_group)}")
        
        if data.residence_census_block:
            info.append(f"Census Block: {str(data.residence_census_block)}")
        
        if data.residence_complete_census_geocode:
            info.append(f"Complete Census Geocode: {str(data.residence_complete_census_geocode)}")
        
        if data.residence_latitude is not None and data.residence_longitude is not None:
            info.append(f"Residence Coordinates: {float(data.residence_latitude):.6f}, {float(data.residence_longitude):.6f}")
        
        if data.residence_lat_long_accuracy:
            info.append(f"Coordinate Accuracy: {str(data.residence_lat_long_accuracy)}")
        
        if data.residence_family_id:
            info.append(f"Residence Family ID: {str(data.residence_family_id)}")
        
        if data.residence_property_land_square_footage:
            info.append(f"Property Land Square Footage: {str(data.residence_property_land_square_footage)}")
        
        if data.residence_property_type:
            info.append(f"Property Type: {str(data.residence_property_type)}")
        
        if data.residence_density:
            info.append(f"Residence Density: {str(data.residence_density)}")
        
        # Mailing address (if different)
        if data.mailing_address_line and data.mailing_address_line != data.residence_address_line:
            info.append(f"Mailing Address: {str(data.mailing_address_line)}")
            if data.mailing_extra_address_line:
                info.append(f"Mailing Extra: {str(data.mailing_extra_address_line)}")
            if data.mailing_city and data.mailing_state:
                info.append(f"Mailing City: {str(data.mailing_city)}, {str(data.mailing_state)}")
            if data.mailing_zip:
                info.append(f"Mailing ZIP: {str(data.mailing_zip)}")
            if data.mailing_zip_plus4:
                info.append(f"Mailing ZIP+4: {str(data.mailing_zip_plus4)}")
            if data.mailing_dpbc:
                info.append(f"Mailing DPBC: {str(data.mailing_dpbc)}")
            if data.mailing_check_digit:
                info.append(f"Mailing Check Digit: {str(data.mailing_check_digit)}")
            if data.mailing_house_number:
                info.append(f"Mailing House Number: {str(data.mailing_house_number)}")
            if data.mailing_prefix_direction:
                info.append(f"Mailing Prefix Direction: {str(data.mailing_prefix_direction)}")
            if data.mailing_street_name:
                info.append(f"Mailing Street Name: {str(data.mailing_street_name)}")
            if data.mailing_designator:
                info.append(f"Mailing Designator: {str(data.mailing_designator)}")
            if data.mailing_suffix_direction:
                info.append(f"Mailing Suffix Direction: {str(data.mailing_suffix_direction)}")
            if data.mailing_apartment_num:
                info.append(f"Mailing Apartment Number: {str(data.mailing_apartment_num)}")
            if data.mailing_apartment_type:
                info.append(f"Mailing Apartment Type: {str(data.mailing_apartment_type)}")
            if data.mailing_cass_err_stat_code:
                info.append(f"Mailing CASS Error Status: {str(data.mailing_cass_err_stat_code)}")
            if data.mailing_family_id:
                info.append(f"Mailing Family ID: {str(data.mailing_family_id)}")
        
        return info
    
    def _extract_political_info(self, agent) -> List[str]:
        """Extract comprehensive political information."""
        info = []
        data = agent.l2_data.political
        
        if data.party:
            info.append(f"Political Party: {data.party}")
        
        if data.registration_date:
            info.append(f"Registration Date: {data.registration_date}")
        
        if data.calculated_registration_date:
            info.append(f"Calculated Registration: {data.calculated_registration_date}")
        
        info.append(f"Active Voter: {'Yes' if data.is_active else 'No'}")
        
        if data.absentee_type:
            info.append(f"Absentee Type: {data.absentee_type}")
        
        if data.party_change_date:
            info.append(f"Party Change Date: {data.party_change_date}")
        
        # Voting performance
        if data.voting_performance_general:
            info.append(f"General Election Performance: {data.voting_performance_general}")
        
        if data.voting_performance_primary:
            info.append(f"Primary Election Performance: {data.voting_performance_primary}")
        
        if data.voting_performance_combined:
            info.append(f"Combined Voting Performance: {data.voting_performance_combined}")
        
        # Political flags and scores
        political_flags = []
        if data.progressive_democrat_flag:
            political_flags.append("Progressive Democrat")
        if data.moderate_democrat_flag:
            political_flags.append("Moderate Democrat")
        if data.moderate_republican_flag:
            political_flags.append("Moderate Republican")
        if data.conservative_republican_flag:
            political_flags.append("Conservative Republican")
        if data.likely_to_vote_3rd_party_flag:
            political_flags.append("Likely 3rd Party Voter")
        
        if political_flags:
            info.append(f"Political Profile: {', '.join(political_flags)}")
        
        # Election history
        election_history = self._extract_election_history(agent)
        if election_history:
            info.extend(election_history)
        
        return info
    
    def _extract_election_history(self, agent) -> List[str]:
        """Extract detailed election participation history."""
        info = []
        data = agent.l2_data.election_history
        
        # Get voting statistics
        voting_stats = agent._compute_voting_statistics()
        
        info.append(f"Total Elections Available: {str(voting_stats['total_elections'])}")
        info.append(f"Total Elections Voted: {str(voting_stats['total_voted'])}")
        info.append(f"Presidential Election Rate: {float(voting_stats['presidential_rate']):.1f}%")
        info.append(f"General Election Rate: {float(voting_stats['general_rate']):.1f}%")
        info.append(f"Primary Election Rate: {float(voting_stats['primary_rate']):.1f}%")
        info.append(f"Recent Participation (2020-2024): {float(voting_stats['recent_participation']):.1f}%")
        
        # Specific election years
        election_years = []
        for field_name in dir(data):
            if field_name.startswith(('general_', 'primary_', 'presidential_primary_')):
                value = getattr(data, field_name)
                if value == 'Y':
                    year = field_name.split('_')[-1]
                    election_type = field_name.split('_')[0]
                    election_years.append(f"{election_type.title()} {year}")
        
        if election_years:
            info.append(f"Elections Voted In: {', '.join(election_years)}")
        
        return info
    
    def _extract_economic_info(self, agent) -> List[str]:
        """Extract comprehensive economic information."""
        info = []
        data = agent.l2_data.economic
        
        if data.estimated_income:
            info.append(f"Estimated Income: ${str(data.estimated_income)}")
        
        if data.household_net_worth:
            info.append(f"Household Net Worth: {str(data.household_net_worth)}")
        
        if data.credit_rating:
            info.append(f"Credit Rating: {str(data.credit_rating)}")
        
        if data.home_value:
            info.append(f"Home Value: {str(data.home_value)}")
        
        if data.home_purchase_price:
            info.append(f"Home Purchase Price: {str(data.home_purchase_price)}")
        
        if data.home_purchase_year:
            info.append(f"Home Purchase Year: {str(data.home_purchase_year)}")
        
        if data.dwelling_type:
            info.append(f"Dwelling Type: {str(data.dwelling_type)}")
        
        if data.home_square_footage is not None and not pd.isna(data.home_square_footage):
            sq_ft = self._safe_int_convert(data.home_square_footage)
            if sq_ft is not None:
                info.append(f"Home Square Footage: {sq_ft}")
        
        if data.bedrooms_count is not None and not pd.isna(data.bedrooms_count):
            bedrooms = self._safe_int_convert(data.bedrooms_count)
            if bedrooms is not None:
                info.append(f"Bedrooms: {bedrooms}")
        
        if data.home_swimming_pool:
            info.append("Has Swimming Pool: Yes")
        
        if data.soho_indicator:
            info.append("Home Office: Yes")
        
        # Vehicle information
        if data.auto_make_1 and data.auto_model_1:
            vehicle_info = f"Primary Vehicle: {str(data.auto_make_1)} {str(data.auto_model_1)}"
            if data.auto_year_1:
                vehicle_info += f" ({str(data.auto_year_1)})"
            info.append(vehicle_info)
        
        if data.auto_make_2 and data.auto_model_2:
            vehicle_info = f"Secondary Vehicle: {str(data.auto_make_2)} {str(data.auto_model_2)}"
            if data.auto_year_2:
                vehicle_info += f" ({str(data.auto_year_2)})"
            info.append(vehicle_info)
        
        # Credit information
        if data.household_number_lines_of_credit is not None and not pd.isna(data.household_number_lines_of_credit):
            lines_credit = self._safe_int_convert(data.household_number_lines_of_credit)
            if lines_credit is not None:
                info.append(f"Lines of Credit: {lines_credit}")
        
        if data.presence_of_cc:
            info.append("Has Credit Cards: Yes")
        
        if data.presence_of_gold_plat_cc:
            info.append("Has Gold/Platinum Cards: Yes")
        
        if data.presence_of_premium_cc:
            info.append("Has Premium Credit Cards: Yes")
        
        return info
    
    def _extract_family_info(self, agent) -> List[str]:
        """Extract comprehensive family information."""
        info = []
        data = agent.l2_data.family
        
        if data.total_persons is not None and not pd.isna(data.total_persons):
            total_persons = self._safe_int_convert(data.total_persons)
            if total_persons is not None:
                info.append(f"Total Household Members: {total_persons}")
        
        if data.number_of_adults is not None and not pd.isna(data.number_of_adults):
            num_adults = self._safe_int_convert(data.number_of_adults)
            if num_adults is not None:
                info.append(f"Adults in Household: {num_adults}")
        
        if data.number_of_children is not None and not pd.isna(data.number_of_children):
            num_children = self._safe_int_convert(data.number_of_children)
            if num_children is not None:
                info.append(f"Children in Household: {num_children}")
        
        if data.has_children:
            info.append("Has Children: Yes")
        
        if data.is_veteran:
            info.append("Veteran: Yes")
        
        if data.is_single_parent:
            info.append("Single Parent: Yes")
        
        if data.has_senior_adult:
            info.append("Has Senior Adult: Yes")
        
        if data.has_young_adult:
            info.append("Has Young Adult: Yes")
        
        if data.disabled_in_hh:
            info.append("Has Disabled Person: Yes")
        
        if data.generations_in_hh:
            info.append(f"Generations in Household: {str(data.generations_in_hh)}")
        
        if data.assimilation_status:
            info.append(f"Assimilation Status: {str(data.assimilation_status)}")
        
        # Household descriptors (safe access)
        if hasattr(data, 'hh_gender_description') and data.hh_gender_description:
            info.append(f"Household Gender: {str(data.hh_gender_description)}")
        
        if hasattr(data, 'hh_parties_description') and data.hh_parties_description:
            info.append(f"Household Party: {str(data.hh_parties_description)}")
        
        if data.household_voters_count is not None and not pd.isna(data.household_voters_count):
            household_voters = self._safe_int_convert(data.household_voters_count)
            if household_voters is not None:
                info.append(f"Household Voters: {household_voters}")
        
        # Children by age
        children_info = []
        if data.children_0_2 is not None and not pd.isna(data.children_0_2):
            count_0_2 = self._safe_int_convert(data.children_0_2)
            if count_0_2 is not None:
                children_info.append(f"{count_0_2} ages 0-2")
        if data.children_3_5 is not None and not pd.isna(data.children_3_5):
            count_3_5 = self._safe_int_convert(data.children_3_5)
            if count_3_5 is not None:
                children_info.append(f"{count_3_5} ages 3-5")
        if data.children_6_10 is not None and not pd.isna(data.children_6_10):
            count_6_10 = self._safe_int_convert(data.children_6_10)
            if count_6_10 is not None:
                children_info.append(f"{count_6_10} ages 6-10")
        if data.children_11_15 is not None and not pd.isna(data.children_11_15):
            count_11_15 = self._safe_int_convert(data.children_11_15)
            if count_11_15 is not None:
                children_info.append(f"{count_11_15} ages 11-15")
        if data.children_16_17 is not None and not pd.isna(data.children_16_17):
            count_16_17 = self._safe_int_convert(data.children_16_17)
            if count_16_17 is not None:
                children_info.append(f"{count_16_17} ages 16-17")
        
        if children_info:
            info.append(f"Children by Age: {', '.join(children_info)}")
        
        return info
    
    def _extract_work_info(self, agent) -> List[str]:
        """Extract comprehensive work information."""
        info = []
        data = agent.l2_data.work
        
        if data.occupation:
            info.append(f"Occupation: {str(data.occupation)}")
        
        if data.occupation_group:
            info.append(f"Occupation Group: {str(data.occupation_group)}")
        
        if data.education_level:
            info.append(f"Education Level: {str(data.education_level)}")
        
        if data.is_business_owner:
            info.append("Business Owner: Yes")
        
        if data.is_african_american_professional:
            info.append("African American Professional: Yes")
        
        # Recent employment
        if data.recent_employment_company:
            employment_info = f"Recent Employer: {str(data.recent_employment_company)}"
            if data.recent_employment_title:
                employment_info += f" - {str(data.recent_employment_title)}"
            info.append(employment_info)
        
        if data.recent_employment_department:
            info.append(f"Department: {str(data.recent_employment_department)}")
        
        if data.recent_employment_executive_level:
            info.append(f"Executive Level: {str(data.recent_employment_executive_level)}")
        
        return info
    
    def _extract_consumer_info(self, agent) -> List[str]:
        """Extract comprehensive consumer information."""
        info = []
        data = agent.l2_data.consumer
        
        if data.interests:
            interests = [str(interest) for interest in data.interests[:10]]
            info.append(f"Interests ({len(data.interests)}): {', '.join(interests)}")
            if len(data.interests) > 10:
                info.append(f"... and {len(data.interests) - 10} more interests")
        
        if data.donor_categories:
            categories = [str(cat) for cat in data.donor_categories[:5]]
            info.append(f"Donor Categories ({len(data.donor_categories)}): {', '.join(categories)}")
        
        if data.lifestyle_categories:
            categories = [str(cat) for cat in data.lifestyle_categories[:5]]
            info.append(f"Lifestyle Categories ({len(data.lifestyle_categories)}): {', '.join(categories)}")
        
        if data.shopping_preferences:
            prefs = [str(pref) for pref in data.shopping_preferences[:5]]
            info.append(f"Shopping Preferences ({len(data.shopping_preferences)}): {', '.join(prefs)}")
        
        if data.media_preferences:
            prefs = [str(pref) for pref in data.media_preferences[:5]]
            info.append(f"Media Preferences ({len(data.media_preferences)}): {', '.join(prefs)}")
        
        if data.technology_usage:
            usage = [str(use) for use in data.technology_usage[:5]]
            info.append(f"Technology Usage ({len(data.technology_usage)}): {', '.join(usage)}")
        
        if data.travel_preferences:
            prefs = [str(pref) for pref in data.travel_preferences[:5]]
            info.append(f"Travel Preferences ({len(data.travel_preferences)}): {', '.join(prefs)}")
        
        if data.health_interests:
            interests = [str(interest) for interest in data.health_interests[:5]]
            info.append(f"Health Interests ({len(data.health_interests)}): {', '.join(interests)}")
        
        if data.financial_interests:
            interests = [str(interest) for interest in data.financial_interests[:5]]
            info.append(f"Financial Interests ({len(data.financial_interests)}): {', '.join(interests)}")
        
        return info
    
    def _extract_geographic_info(self, agent) -> List[str]:
        """Extract comprehensive geographic information."""
        info = []
        data = agent.l2_data.geographic
        
        if data.county:
            info.append(f"County: {str(data.county)}")
        
        if data.precinct:
            info.append(f"Precinct: {str(data.precinct)}")
        
        if data.congressional_district:
            info.append(f"Congressional District: {str(data.congressional_district)}")
        
        if data.state_senate_district:
            info.append(f"State Senate District: {str(data.state_senate_district)}")
        
        if data.state_house_district:
            info.append(f"State House District: {str(data.state_house_district)}")
        
        if data.city:
            info.append(f"City: {str(data.city)}")
        
        if data.borough:
            info.append(f"Borough: {str(data.borough)}")
        
        if data.township:
            info.append(f"Township: {str(data.township)}")
        
        if data.village:
            info.append(f"Village: {str(data.village)}")
        
        return info
    
    def _extract_fec_donor_info(self, agent) -> List[str]:
        """Extract FEC donor information."""
        info = []
        if not hasattr(agent.l2_data, 'fec_donor') or not agent.l2_data.fec_donor:
            return info
            
        data = agent.l2_data.fec_donor
        
        if data.avg_donation:
            info.append(f"Average Donation: ${str(data.avg_donation)}")
        
        if data.avg_donation_range:
            info.append(f"Average Donation Range: {str(data.avg_donation_range)}")
        
        if data.last_donation_date:
            info.append(f"Last Donation Date: {str(data.last_donation_date)}")
        
        if data.number_of_donations is not None:
            num_donations = self._safe_int_convert(data.number_of_donations)
            if num_donations is not None:
                info.append(f"Number of Donations: {num_donations}")
        
        if data.primary_recipient:
            info.append(f"Primary Recipient: {str(data.primary_recipient)}")
        
        if data.total_donations_amount:
            info.append(f"Total Donations: ${str(data.total_donations_amount)}")
        
        if data.total_donations_range:
            info.append(f"Total Donations Range: {str(data.total_donations_range)}")
        
        return info
    
    def _extract_market_area_info(self, agent) -> List[str]:
        """Extract market area information."""
        info = []
        if not hasattr(agent.l2_data, 'market_area') or not agent.l2_data.market_area:
            return info
            
        data = agent.l2_data.market_area
        
        if data.designated_market_area_dma:
            info.append(f"Designated Market Area (DMA): {str(data.designated_market_area_dma)}")
        
        if data.consumerdata_csa:
            info.append(f"Combined Statistical Area: {str(data.consumerdata_csa)}")
        
        if data.consumerdata_cbsa:
            info.append(f"Core Based Statistical Area: {str(data.consumerdata_cbsa)}")
        
        if data.consumerdata_msa:
            info.append(f"Metropolitan Statistical Area: {str(data.consumerdata_msa)}")
        
        # Area demographics
        if data.area_pcnt_hh_with_children is not None:
            pct_children = self._safe_int_convert(data.area_pcnt_hh_with_children)
            if pct_children is not None:
                info.append(f"Area % Households with Children: {pct_children}%")
        
        if data.area_median_housing_value:
            info.append(f"Area Median Housing Value: ${str(data.area_median_housing_value)}")
        
        if data.area_median_hh_income:
            info.append(f"Area Median Household Income: ${str(data.area_median_hh_income)}")
        
        if data.area_median_education_years is not None:
            edu_years = self._safe_int_convert(data.area_median_education_years)
            if edu_years is not None:
                info.append(f"Area Median Education Years: {edu_years}")
        
        return info
    
    def _extract_phone_info(self, agent) -> List[str]:
        """Extract phone information."""
        info = []
        if not hasattr(agent.l2_data, 'phone') or not agent.l2_data.phone:
            return info
            
        data = agent.l2_data.phone
        
        if data.phone_number_available:
            info.append("Phone Number Available: Yes")
        
        if data.landline_phone_available:
            info.append("Landline Available: Yes")
            if data.landline_formatted:
                info.append(f"Landline: {str(data.landline_formatted)}")
        
        if data.cell_phone_available:
            info.append("Cell Phone Available: Yes")
            if data.cell_phone_formatted:
                info.append(f"Cell Phone: {str(data.cell_phone_formatted)}")
        
        if data.do_not_call:
            info.append("Do Not Call Registry: Yes")
        
        return info
    
    def _extract_mobile_advertising_info(self, agent) -> List[str]:
        """Extract mobile advertising information."""
        info = []
        if not hasattr(agent.l2_data, 'mobile_advertising') or not agent.l2_data.mobile_advertising:
            return info
            
        data = agent.l2_data.mobile_advertising
        
        if data.maid_available:
            info.append("Mobile Advertising ID Available: Yes")
        
        # Count non-null MAID IDs
        maid_ids = [data.maid_1, data.maid_2, data.maid_3, data.maid_4, data.maid_5]
        active_maids = [maid for maid in maid_ids if maid is not None]
        if active_maids:
            info.append(f"Active MAID Count: {len(active_maids)}")
        
        if data.maid_ip_available:
            info.append("IP Address Available: Yes")
            # Count non-null IP addresses
            ip_addresses = [data.maid_ip_1, data.maid_ip_2, data.maid_ip_3, data.maid_ip_4, data.maid_ip_5]
            active_ips = [ip for ip in ip_addresses if ip is not None]
            if active_ips:
                info.append(f"Active IP Count: {len(active_ips)}")
        
        return info
    
    def _extract_judicial_districts_info(self, agent) -> List[str]:
        """Extract judicial districts information."""
        info = []
        if not hasattr(agent.l2_data, 'judicial_districts') or not agent.l2_data.judicial_districts:
            return info
            
        data = agent.l2_data.judicial_districts
        districts = []
        
        # Get all non-None district values
        for attr_name in dir(data):
            if not attr_name.startswith('_'):
                try:
                    value = getattr(data, attr_name)
                    if value is not None and not callable(value):
                        districts.append(f"{attr_name.replace('_', ' ').title()}: {str(value)}")
                except Exception:
                    continue
        
        if districts:
            info.extend(districts)
        
        return info
    
    def _extract_school_districts_info(self, agent) -> List[str]:
        """Extract school districts information."""
        info = []
        if not hasattr(agent.l2_data, 'school_districts') or not agent.l2_data.school_districts:
            return info
            
        data = agent.l2_data.school_districts
        districts = []
        
        # Get all non-None district values
        for attr_name in dir(data):
            if not attr_name.startswith('_'):
                try:
                    value = getattr(data, attr_name)
                    if value is not None and not callable(value):
                        districts.append(f"{attr_name.replace('_', ' ').title()}: {str(value)}")
                except Exception:
                    continue
        
        if districts:
            info.extend(districts)
        
        return info
    
    def _extract_special_districts_info(self, agent) -> List[str]:
        """Extract special districts information."""
        info = []
        if not hasattr(agent.l2_data, 'special_districts') or not agent.l2_data.special_districts:
            return info
            
        data = agent.l2_data.special_districts
        districts = []
        
        # Get all non-None district values
        for attr_name in dir(data):
            if not attr_name.startswith('_'):
                try:
                    value = getattr(data, attr_name)
                    if value is not None and not callable(value):
                        districts.append(f"{attr_name.replace('_', ' ').title()}: {str(value)}")
                except Exception:
                    continue
        
        if districts:
            info.extend(districts)
        
        return info
    def create_llm_summary(self, agent) -> tuple[str, str, dict]:
        """Create a summary using LLM with all available data.

        Strategy: try a full-length summary first (up to 10k tokens by default).
        If strict profile tag validation fails, automatically retry with a
        shorter, concise prompt and a reduced token cap to improve compliance.

        Returns:
            tuple[str, str, dict]: (profile_content, reasoning, metadata)
        """
        import traceback
        import os

        if not self.api_manager:
            return ("LLM API not available", "", {})

        # Prepare comprehensive data for LLM
        llm_data = self._prepare_llm_data(agent)
        prompt = self._create_llm_prompt(llm_data)

        # Use centralized numerical settings
        try:
            from Setup.numerical_settings import numerical_settings
            primary_max_tokens = int(numerical_settings.PERSONAL_SUMMARY_MAX_TOKENS)
            secondary_max_tokens = int(numerical_settings.PERSONAL_SUMMARY_RETRY_MAX_TOKENS)
            temperature = float(numerical_settings.PERSONAL_SUMMARY_TEMPERATURE)
            intelligence = int(numerical_settings.PERSONAL_SUMMARY_INTELLIGENCE_LEVEL)
        except Exception:
            primary_max_tokens = int(os.getenv('PERSONAL_SUMMARY_MAX_TOKENS', '10000'))
            secondary_max_tokens = min(primary_max_tokens, 3000)
            temperature = 0.7
            intelligence = 3

        # Helper to call LLM
        def _call_llm(p: str, max_toks: int) -> tuple[str, str, dict]:
            try:
                response, reasoning, _model_name, metadata = self.api_manager.make_request(
                    prompt=p,
                    intelligence_level=intelligence,
                    max_tokens=max_toks,
                    temperature=temperature
                )
                return response, reasoning, metadata
            except Exception as e:
                print(f"[ERROR] Exception in _call_llm: {e}")
                print(f"[ERROR] Exception type: {type(e)}")
                traceback.print_exc()
                raise

        import re as _re

        # Define attempts (prompt, max_tokens)
        attempts = [
            (
                prompt,
                primary_max_tokens,
                None,  # fallback_metadata
            ),
            (
                prompt
                + "\n\nIMPORTANT CORRECTION: Your previous attempt did not include the required <profile> tags.\n"
                + "Now return a concise 1-2 paragraph personal profile. You MUST include <profile>...</profile> tags.",
                secondary_max_tokens,
                None,
            ),
            (
                prompt
                + "\n\nFINAL ATTEMPT: Return ONLY <profile>...</profile> blocks.\n"
                + "There must be EXACTLY ONE <profile> tag, with NO other text before or after.",
                min(secondary_max_tokens, 1500),
                None,
            ),
        ]

        last_responses = []  # to store (response, reasoning, metadata) tuples

        for idx, (attempt_prompt, max_toks, _) in enumerate(attempts):
            try:
                response, reasoning, metadata = _call_llm(attempt_prompt, max_toks)
                last_responses.append((response, reasoning, metadata))
                profile_content, reasoning_content = self._extract_profile_and_reasoning(response, reasoning)
                return (profile_content, reasoning_content, metadata)
            except Exception as e:
                verbosity = int(os.getenv('VERBOSITY_LEVEL', '1'))
                if verbosity >= 2:
                    print(f"[WARNING] Failed to extract profile and reasoning on attempt {idx+1}: {e}")
                    traceback.print_exc()

        # All attempts failed: Fallback to salvage text from last non-empty response
        for fallback_response_tuple in reversed(last_responses):
            response, reasoning, metadata = fallback_response_tuple
            try:
                text = (response or "").strip()
                text = _re.sub(r"\s+", " ", text).strip()
                if len(text) > 12000:
                    text = text[:12000]
                return (text, "Fallback: Unable to extract profile", metadata)
            except Exception:
                continue

        # If absolutely nothing usable, raise original error
        raise ValueError('Unable to generate or extract profile from LLM response.')
    
    def _extract_profile_content(self, response: str) -> str:
        """Extract content strictly between <profile> and </profile> tags.

        Requirements:
        - Exactly one opening and one closing tag must be present
        - No duplicate or mismatched tags
        - Return the content without the tags

        Raises:
        - ValueError if tags are missing, duplicated, or malformed
        """
        opens = [m.start() for m in re.finditer(r'<profile>', response)]
        closes = [m.start() for m in re.finditer(r'</profile>', response)]

        if not opens and not closes:
            raise ValueError("Personal summary missing required <profile>...</profile> tags")

        if len(opens) != 1 or len(closes) != 1:
            raise ValueError(f"Unexpected number of <profile> tags: opens={len(opens)}, closes={len(closes)}")

        open_pos = opens[0]
        close_pos = closes[0]
        if close_pos <= open_pos:
            raise ValueError("Malformed <profile> tags: closing tag appears before opening tag")

        start = open_pos + len('<profile>')
        content = response[start:close_pos]
        return content.strip()
    
    def _extract_profile_and_reasoning(self, response: str, reasoning: str) -> tuple[str, str]:
        """Extract both reasoning and profile content from LLM response.
        
        Requirements:
        - Exactly one <profile>...</profile> pair
        - Return (profile_content)
        
        Raises:
        - ValueError if tags are missing, duplicated, or malformed
        """
        # Extract profile
        profile_opens = [m.start() for m in re.finditer(r'<profile>', response)]
        profile_closes = [m.start() for m in re.finditer(r'</profile>', response)]
        
        # Validate profile tags
        if not profile_opens or not profile_closes:
            raise ValueError("Personal summary missing required <profile>...</profile> tags")
        if len(profile_opens) != 1 or len(profile_closes) != 1:
            raise ValueError(f"Unexpected number of <profile> tags: opens={len(profile_opens)}, closes={len(profile_closes)}")
        if profile_closes[0] <= profile_opens[0]:
            raise ValueError("Malformed <profile> tags: closing tag appears before opening tag")
        
        # Extract content
        profile_start = profile_opens[0] + len('<profile>')
        profile_content = response[profile_start:profile_closes[0]].strip()
        
        return (profile_content, reasoning)
    
    def _prepare_llm_data(self, agent) -> Dict[str, Any]:
        """Prepare all agent data for LLM processing."""
        data = {
            'personal': {},
            'address': {},
            'political': {},
            'economic': {},
            'family': {},
            'work': {},
            'consumer': {},
            'geographic': {},
            'election_history': {},
            'fec_donor': {},
            'market_area': {},
            'phone': {},
            'mobile_advertising': {},
            'judicial_districts': {},
            'school_districts': {},
            'special_districts': {},
            # Include full raw L2 row for completeness
            # 'raw_data': agent.l2_data.all_data() if hasattr(agent, 'l2_data') and agent.l2_data else {},
        }
        
        # Personal information
        if agent.l2_data.personal:
            personal = agent.l2_data.personal
            data['personal'] = {
                'name': f"{personal.first_name or ''} {personal.middle_name or ''} {personal.last_name or ''} {personal.name_suffix or ''}".strip(),
                'age': personal.age,
                'gender': personal.gender,
                'birth_date': personal.birth_date,
                # 'birth_date_confidence': personal.birth_date_confidence,
                'place_of_birth': personal.place_of_birth,
                'ethnicity': personal.ethnicity,
                'ethnic_group': personal.ethnic_group_1_desc,
                'language': personal.language_code,
                'marital_status': personal.marital_status,
                'religion': personal.religion_code,
                'inferred_hh_rank': personal.inferred_hh_rank,
                # 'state_voter_id': personal.state_voter_id,
                # 'county_voter_id': personal.county_voter_id,
                # 'sequence_zigzag': personal.sequence_zigzag,
                # 'sequence_odd_even': personal.sequence_odd_even,
                # 'fips': personal.fips,
                'county_ethnic_description': personal.county_ethnic_description,
                'county_ethnic_lal_code': personal.county_ethnic_lal_code,
                'moved_from_date': personal.moved_from_date,
                'moved_from_state': personal.moved_from_state,
                'moved_from_party': personal.moved_from_party,
                'moved_from_voting_performance_combined': personal.moved_from_voting_performance_combined,
                'moved_from_voting_performance_general': personal.moved_from_voting_performance_general,
                'moved_from_voting_performance_primary': personal.moved_from_voting_performance_primary,
                'moved_from_voting_performance_minor': personal.moved_from_voting_performance_minor
            }
        
        # Address information
        if agent.l2_data.address:
            addr = agent.l2_data.address
            data['address'] = {
                'residence': {
                    'address': addr.residence_address_line,
                    'extra_address': addr.residence_extra_address_line,
                    'city': addr.residence_city,
                    'state': addr.residence_state,
                    # 'zip': addr.residence_zip,
                    # 'zip_plus4': addr.residence_zip_plus4,
                    # 'dpbc': addr.residence_dpbc,
                    # 'check_digit': addr.residence_check_digit,
                    'house_number': addr.residence_house_number,
                    'prefix_direction': addr.residence_prefix_direction,
                    'street_name': addr.residence_street_name,
                    'designator': addr.residence_designator,
                    'suffix_direction': addr.residence_suffix_direction,
                    'apartment_num': addr.residence_apartment_num,
                    'apartment_type': addr.residence_apartment_type,
                    # 'cass_err_stat_code': addr.residence_cass_err_stat_code,
                    'county': addr.residence_county,
                    'congressional_district': addr.residence_congressional_district,
                    # 'census_tract': addr.residence_census_tract,
                    # 'census_block_group': addr.residence_census_block_group,
                    # 'census_block': addr.residence_census_block,
                    # 'complete_census_geocode': addr.residence_complete_census_geocode,
                    # 'latitude': addr.residence_latitude,
                    # 'longitude': addr.residence_longitude,
                    # 'lat_long_accuracy': addr.residence_lat_long_accuracy,
                    # 'family_id': addr.residence_family_id,
                    'property_land_square_footage': addr.residence_property_land_square_footage,
                    'property_type': addr.residence_property_type,
                    'residence_density': addr.residence_density
                },
                'mailing': {
                    'address': addr.mailing_address_line,
                    'extra_address': addr.mailing_extra_address_line,
                    'city': addr.mailing_city,
                    'state': addr.mailing_state,
                    'zip': addr.mailing_zip,
                    # 'zip_plus4': addr.mailing_zip_plus4,
                    # 'dpbc': addr.mailing_dpbc,
                    # 'check_digit': addr.mailing_check_digit,
                    'house_number': addr.mailing_house_number,
                    # 'prefix_direction': addr.mailing_prefix_direction,
                    'street_name': addr.mailing_street_name,
                    'designator': addr.mailing_designator,
                    # 'suffix_direction': addr.mailing_suffix_direction,
                    'apartment_num': addr.mailing_apartment_num,
                    'apartment_type': addr.mailing_apartment_type,
                    # 'cass_err_stat_code': addr.mailing_cass_err_stat_code,
                    # 'family_id': addr.mailing_family_id
                }
            }
        
        # Political information
        if agent.l2_data.political:
            pol = agent.l2_data.political
            data['political'] = {
                'party': pol.party,
                'registration_date': pol.registration_date,
                # 'calculated_registration_date': pol.calculated_registration_date,
                'is_active': pol.is_active,
                'absentee_type': pol.absentee_type,
                'party_change_date': pol.party_change_date,
                'voting_performance': {
                    'general': pol.voting_performance_general,
                    'primary': pol.voting_performance_primary,
                    'combined': pol.voting_performance_combined
                },
                'political_flags': {
                    'progressive_democrat': pol.progressive_democrat_flag,
                    'moderate_democrat': pol.moderate_democrat_flag,
                    'moderate_republican': pol.moderate_republican_flag,
                    'conservative_republican': pol.conservative_republican_flag,
                    'likely_3rd_party': pol.likely_to_vote_3rd_party_flag
                }
            }
        
        # Election history (include all non-empty fields)
        if agent.l2_data.election_history:
            elections = agent.l2_data.election_history
            election_data = {}
            for field_name in dir(elections):
                if field_name.startswith('_'):
                    continue
                try:
                    value = getattr(elections, field_name)
                except Exception:
                    continue
                if not callable(value) and value is not None:
                    election_data[field_name] = value

            data['election_history'] = election_data
            
            # Add computed voting statistics
            voting_stats = agent._compute_voting_statistics()
            data['voting_statistics'] = voting_stats
        
        # Economic information
        if agent.l2_data.economic:
            econ = agent.l2_data.economic
            data['economic'] = {
                'estimated_income': econ.estimated_income,
                'household_net_worth': econ.household_net_worth,
                'credit_rating': econ.credit_rating,
                'home_value': econ.home_value,
                'home_purchase_price': econ.home_purchase_price,
                'home_purchase_year': econ.home_purchase_year,
                'dwelling_type': econ.dwelling_type,
                'home_square_footage': econ.home_square_footage,
                'bedrooms_count': econ.bedrooms_count,
                'has_swimming_pool': econ.home_swimming_pool,
                'soho_indicator': econ.soho_indicator,
                'vehicles': {
                    'primary': {
                        'make': econ.auto_make_1,
                        'model': econ.auto_model_1,
                        'year': econ.auto_year_1
                    },
                    'secondary': {
                        'make': econ.auto_make_2,
                        'model': econ.auto_model_2,
                        'year': econ.auto_year_2
                    }
                },
                'credit': {
                    'lines_of_credit': econ.household_number_lines_of_credit,
                    'has_credit_cards': econ.presence_of_cc,
                    'has_premium_cards': econ.presence_of_premium_cc,
                    'has_gold_platinum': econ.presence_of_gold_plat_cc
                }
            }
        
        # Family information
        if agent.l2_data.family:
            fam = agent.l2_data.family
            data['family'] = {
                'total_persons': fam.total_persons,
                'adults': fam.number_of_adults,
                'children': fam.number_of_children,
                'has_children': fam.has_children,
                'is_veteran': fam.is_veteran,
                'is_single_parent': fam.is_single_parent,
                'has_senior_adult': fam.has_senior_adult,
                'has_young_adult': fam.has_young_adult,
                'has_disabled': fam.disabled_in_hh,
                'generations': fam.generations_in_hh,
                'household_gender': getattr(fam, 'hh_gender_description', None),
                'household_party': getattr(fam, 'hh_parties_description', None),
                'household_voters_count': fam.household_voters_count,
                'assimilation_status': fam.assimilation_status,
                'children_by_age': {
                    '0_2': fam.children_0_2,
                    '3_5': fam.children_3_5,
                    '6_10': fam.children_6_10,
                    '11_15': fam.children_11_15,
                    '16_17': fam.children_16_17
                }
            }
        
        # Work information
        if agent.l2_data.work:
            work = agent.l2_data.work
            data['work'] = {
                'occupation': work.occupation,
                'occupation_group': work.occupation_group,
                'education_level': work.education_level,
                'is_business_owner': work.is_business_owner,
                'is_african_american_professional': work.is_african_american_professional,
                'recent_employment': {
                    'company': work.recent_employment_company,
                    'title': work.recent_employment_title,
                    'department': work.recent_employment_department,
                    'executive_level': work.recent_employment_executive_level
                }
            }
        
        # Consumer information
        if agent.l2_data.consumer:
            consumer = agent.l2_data.consumer
            consumer_dict = {
                'interests': consumer.interests,
                'donor_categories': consumer.donor_categories,
                'lifestyle_categories': consumer.lifestyle_categories,
                'shopping_preferences': consumer.shopping_preferences,
                'media_preferences': consumer.media_preferences,
                'technology_usage': consumer.technology_usage,
                'travel_preferences': consumer.travel_preferences,
                'health_interests': consumer.health_interests,
                'financial_interests': consumer.financial_interests
            }
            consumer_pruned = self._prune_for_prompt(consumer_dict, parent_key='consumer')
            if consumer_pruned is not None:
                data['consumer'] = consumer_pruned
        
        # Geographic information
        if agent.l2_data.geographic:
            geo = agent.l2_data.geographic
            data['geographic'] = {
                'county': geo.county,
                # 'precinct': geo.precinct,
                # 'congressional_district': geo.congressional_district,
                # 'state_senate_district': geo.state_senate_district,
                # 'state_house_district': geo.state_house_district,
                'city': geo.city,
                'borough': geo.borough,
                'township': geo.township,
                'village': geo.village,
                'time_zone': getattr(geo, 'time_zone', None),
                'rus_code': getattr(geo, 'rus_code', None),
                # 'length_of_residence_code': getattr(geo, 'length_of_residence_code', None)
            }
        
        # FEC donor information
        if agent.l2_data.fec_donor:
            fec = agent.l2_data.fec_donor
            data['fec_donor'] = {
                'avg_donation': fec.avg_donation,
                'avg_donation_range': fec.avg_donation_range,
                'last_donation_date': fec.last_donation_date,
                'number_of_donations': fec.number_of_donations,
                'primary_recipient': fec.primary_recipient,
                'total_donations_amount': fec.total_donations_amount,
                'total_donations_range': fec.total_donations_range
            }
        
        # Market area information
        if agent.l2_data.market_area:
            market = agent.l2_data.market_area
            data['market_area'] = {
                'dma': market.designated_market_area_dma,
                'csa': market.consumerdata_csa,
                'cbsa': market.consumerdata_cbsa,
                'msa': market.consumerdata_msa,
                'area_demographics': {
                    'hh_with_children_pct': market.area_pcnt_hh_with_children,
                    'median_housing_value': market.area_median_housing_value,
                    'median_hh_income': market.area_median_hh_income,
                    'median_education_years': market.area_median_education_years
                }
            }
        
        # Phone information (availability flags only when explicitly True; omit when False/None)
        if agent.l2_data.phone:
            phone = agent.l2_data.phone
            phone_dict = {
                'has_phone': True if getattr(phone, 'phone_number_available', None) is True else None,
                'has_landline': True if getattr(phone, 'landline_phone_available', None) is True else None,
                # 'landline_area_code': getattr(phone, 'landline_area_code', None),
                # 'landline_unformatted': getattr(phone, 'landline_unformatted', None),
                # 'landline_confidence_code': getattr(phone, 'landline_confidence_code', None),
                # 'landline_7digit': getattr(phone, 'landline_7digit', None),
                # 'landline_formatted': getattr(phone, 'landline_formatted', None),
                'has_cell': True if getattr(phone, 'cell_phone_available', None) is True else None,
                # 'cell_phone_unformatted': getattr(phone, 'cell_phone_unformatted', None),
                # 'cell_confidence_code': getattr(phone, 'cell_confidence_code', None),
                # 'cell_phone_formatted': getattr(phone, 'cell_phone_formatted', None),
                'cell_phone_only': True if getattr(phone, 'cell_phone_only', None) is True else None,
                'do_not_call': True if getattr(phone, 'do_not_call', None) is True else None
            }
            phone_pruned = self._prune_for_prompt(phone_dict, parent_key='phone')
            if phone_pruned is not None:
                data['phone'] = phone_pruned

        # Mobile advertising (MAID/IP) information (availability flags only when explicitly True)
        if hasattr(agent.l2_data, 'mobile_advertising') and agent.l2_data.mobile_advertising:
            maid = agent.l2_data.mobile_advertising
            maid_dict = {
                'available': True if getattr(maid, 'maid_available', None) is True else None,
                # 'maid_ids': [getattr(maid, 'maid_1', None), getattr(maid, 'maid_2', None), getattr(maid, 'maid_3', None), getattr(maid, 'maid_4', None), getattr(maid, 'maid_5', None)],
                'maid_cell_systems': [getattr(maid, 'maid_1_cell_phone_system', None), getattr(maid, 'maid_2_cell_phone_system', None), getattr(maid, 'maid_3_cell_phone_system', None), getattr(maid, 'maid_4_cell_phone_system', None), getattr(maid, 'maid_5_cell_phone_system', None)],
                # 'ip_available': True if getattr(maid, 'maid_ip_available', None) is True else None,
                # 'ip_list': [getattr(maid, 'maid_ip_1', None), getattr(maid, 'maid_ip_2', None), getattr(maid, 'maid_ip_3', None), getattr(maid, 'maid_ip_4', None), getattr(maid, 'maid_ip_5', None)]
            }
            maid_pruned = self._prune_for_prompt(maid_dict, parent_key='mobile_advertising')
            if maid_pruned is not None:
                data['mobile_advertising'] = maid_pruned

        # Districts (serialize dataclasses if present)
        try:
            if hasattr(agent.l2_data, 'judicial_districts') and agent.l2_data.judicial_districts:
                data['judicial_districts'] = {k: v for k, v in vars(agent.l2_data.judicial_districts).items() if v is not None}
            if hasattr(agent.l2_data, 'school_districts') and agent.l2_data.school_districts:
                data['school_districts'] = {k: v for k, v in vars(agent.l2_data.school_districts).items() if v is not None}
            if hasattr(agent.l2_data, 'special_districts') and agent.l2_data.special_districts:
                data['special_districts'] = {k: v for k, v in vars(agent.l2_data.special_districts).items() if v is not None}
        except Exception:
            pass
        
        # Final prune: remove null-like values, false availability flags, and empty containers
        pruned_data = self._prune_for_prompt(data)
        return pruned_data if pruned_data is not None else {}
    
    def _create_llm_prompt(self, data: Dict[str, Any]) -> str:
        """Create a comprehensive prompt for the LLM."""
        prompt = """You are tasked with creating a comprehensive personal introduction for an individual based on their complete demographic, political, economic, and social data. This introduction will be used as the soul of a simulated person for the purposes of a simulation, so it's crucial that you include ALL available information in a way that mimics how a person might view themselves. You should include all statistics, numbers, and information in the result. Do not omit any information. If data is available, include it in the result that you create. 

IMPORTANT: This data represents the COMPLETE L2 voter database record for this individual, containing over 780 data fields across multiple categories. Every piece of information provided should be incorporated into the personal profile. This is not a summary - it is a comprehensive personal introduction that includes every available detail.

Feel free to add some personal reflection on the data that you are given. For instance, it would be good to include how the given agent might view parts of their own information -- whether that be proud or ashamed of it -- and context as to why they might feel that way. Do not make up stories or information. Ensure that your response is grounded in the information that I give you. But, you might want to comment on specific attributes that feel unnatural or would make sense to have personal reflection on in the context of the person. 

Think through what each piece of information might mean. For instance, if someone has a specific interest code, then try to think through what the interest code might mean and include it in prose form. Adapt this approach to other underexplained fields. 

This is NOT going to be used in conversation or for anyone else, so it is critical that you present the information in a way that a person might view themselves HONESTLY.

Do not add special formatting to this. Just write it in prose paragraph form. Do not include anything special like paragraph headers or titles. 

The comprehensive data provided includes ALL of the following categories with every available field:
- Personal demographics (age, gender, ethnicity, education, birth details, voter IDs, move history, etc.)
- Geographic location and address information (residence, mailing, coordinates, census data, property details)
- Political affiliation and voting history (party, registration, performance, political flags, election participation)
- Economic status and financial information (income, net worth, credit, home details, vehicles)
- Family composition and household details (members, children by age, veteran status, assimilation)
- Employment and professional background (occupation, education, business ownership, recent employment)
- Consumer interests and lifestyle preferences (interests, donor categories, shopping, media, technology, travel, health, financial)
- Geographic and market area information (districts, DMA, CSA, CBSA, MSA, area demographics)
- Phone and contact information (landline, cell, confidence codes, do not call status)
- FEC donor information (donation amounts, frequency, recipients, ranges)
- Mobile advertising information (MAID IDs, cell systems, IP addresses)
- Judicial districts (all available judicial district assignments)
- School districts (all available school district assignments)
- Special districts (all available special district assignments including water, sewer, fire, etc.)

Please create a comprehensive personal introduction that:
1. Includes ALL available information from the data (this is critical - do not omit anything)
2. Presents it in a natural tone in a way that someone might view themselves
3. Organizes information logically and coherently
4. Highlights unique characteristics and patterns
5. Provides context for their background and interests
6. Does not include information that is not available in the data, and does not comment on the lack of information
7. Does not include direct references to field names or data labels; instead, integrate the data naturally into the prose
8. Incorporates every single piece of provided information (except for that which is None or not available)
9. Makes this person feel like a complete, three-dimensional individual with a rich personal history

IMPORTANT: This is their complete personal profile that the agent will maintain internally and draw on for interactions. Every detail matters and should be included. This is not a summary - it is their full personal story.

Here is the complete data for this individual:

"""
        
        # Add the data as JSON for the LLM to process
        prompt += json.dumps(data, indent=2, default=str)
        
        prompt += """

Please write a complete personal profile that incorporates ALL of the information with self-reflection. This should be a comprehensive personal introduction that includes every available detail about this person. Return the profile in between the <profile> and </profile> tags in your output."""

        return prompt 