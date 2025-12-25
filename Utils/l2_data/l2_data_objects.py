#!/usr/bin/env python3
"""
L2 Data Objects Module
Provides data structures for L2 voter data processing.
Based on actual field names from the test data file.
"""

import pandas as pd
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from datetime import datetime

@dataclass
class PersonalInfo:
    """Personal information for an L2 voter."""
    first_name: Optional[str] = None
    middle_name: Optional[str] = None
    last_name: Optional[str] = None
    name_suffix: Optional[str] = None
    age: Optional[int] = None
    gender: Optional[str] = None
    birth_date: Optional[str] = None
    birth_date_confidence: Optional[str] = None
    county_ethnic_description: Optional[str] = None
    county_ethnic_lal_code: Optional[str] = None
    ethnicity: Optional[str] = None
    place_of_birth: Optional[str] = None
    marital_status: Optional[str] = None
    ethnic_group_1_desc: Optional[str] = None
    hispanic_country_code: Optional[str] = None
    language_code: Optional[str] = None
    religion_code: Optional[str] = None
    inferred_hh_rank: Optional[str] = None
    # Additional voter identification
    state_voter_id: Optional[str] = None
    county_voter_id: Optional[str] = None
    sequence_zigzag: Optional[str] = None
    sequence_odd_even: Optional[str] = None
    fips: Optional[str] = None
    # Moved from data
    moved_from_date: Optional[str] = None
    moved_from_state: Optional[str] = None
    moved_from_party: Optional[str] = None
    moved_from_voting_performance_combined: Optional[str] = None
    moved_from_voting_performance_general: Optional[str] = None
    moved_from_voting_performance_primary: Optional[str] = None
    moved_from_voting_performance_minor: Optional[str] = None

@dataclass
class AddressInfo:
    """Address information for an L2 voter."""
    # Residence address fields
    residence_address_line: Optional[str] = None
    residence_extra_address_line: Optional[str] = None
    residence_city: Optional[str] = None
    residence_state: Optional[str] = None
    residence_zip: Optional[str] = None
    residence_zip_plus4: Optional[str] = None
    residence_dpbc: Optional[str] = None
    residence_check_digit: Optional[str] = None
    residence_house_number: Optional[str] = None
    residence_prefix_direction: Optional[str] = None
    residence_street_name: Optional[str] = None
    residence_designator: Optional[str] = None
    residence_suffix_direction: Optional[str] = None
    residence_apartment_num: Optional[str] = None
    residence_apartment_type: Optional[str] = None
    residence_cass_err_stat_code: Optional[str] = None
    residence_county: Optional[str] = None
    residence_congressional_district: Optional[str] = None
    residence_census_tract: Optional[str] = None
    residence_census_block_group: Optional[str] = None
    residence_census_block: Optional[str] = None
    residence_complete_census_geocode: Optional[str] = None
    residence_latitude: Optional[float] = None
    residence_longitude: Optional[float] = None
    residence_lat_long_accuracy: Optional[str] = None
    residence_family_id: Optional[str] = None
    residence_property_land_square_footage: Optional[str] = None
    residence_property_type: Optional[str] = None
    residence_density: Optional[str] = None
    
    # Mailing address fields
    mailing_address_line: Optional[str] = None
    mailing_extra_address_line: Optional[str] = None
    mailing_city: Optional[str] = None
    mailing_state: Optional[str] = None
    mailing_zip: Optional[str] = None
    mailing_zip_plus4: Optional[str] = None
    mailing_dpbc: Optional[str] = None
    mailing_check_digit: Optional[str] = None
    mailing_house_number: Optional[str] = None
    mailing_prefix_direction: Optional[str] = None
    mailing_street_name: Optional[str] = None
    mailing_designator: Optional[str] = None
    mailing_suffix_direction: Optional[str] = None
    mailing_apartment_num: Optional[str] = None
    mailing_apartment_type: Optional[str] = None
    mailing_cass_err_stat_code: Optional[str] = None
    mailing_family_id: Optional[str] = None

@dataclass
class PoliticalInfo:
    """Political information for an L2 voter."""
    party: Optional[str] = None
    registration_date: Optional[str] = None
    is_active: bool = True
    voting_performance: Optional[str] = None
    voting_performance_even_year_general: Optional[str] = None
    voting_performance_even_year_primary: Optional[str] = None
    voting_performance_even_year_general_and_primary: Optional[str] = None
    voting_performance_minor_election: Optional[str] = None
    voting_performance_combined: Optional[str] = None
    absentee_type: Optional[str] = None
    calculated_registration_date: Optional[str] = None
    party_change_date: Optional[str] = None
    voting_performance_general: Optional[str] = None
    voting_performance_primary: Optional[str] = None
    progressive_democrat_flag: Optional[str] = None
    moderate_democrat_flag: Optional[str] = None
    moderate_republican_flag: Optional[str] = None
    conservative_republican_flag: Optional[str] = None
    for_liberal_democrats_flag: Optional[str] = None
    for_moderate_democrats_flag: Optional[str] = None
    for_trump_but_moderate_flag: Optional[str] = None
    for_trump_not_rinos_flag: Optional[str] = None
    likely_to_vote_3rd_party_flag: Optional[str] = None
    likely_to_vote_for_3rd_party_or_democrat_flag: Optional[str] = None
    likely_to_vote_for_3rd_party_or_republican_flag: Optional[str] = None
    # Political scores
    progressive_democrat_score: Optional[str] = None
    moderate_democrat_score: Optional[str] = None
    moderate_republican_score: Optional[str] = None
    conservative_republican_score: Optional[str] = None
    for_liberal_democrats_score: Optional[str] = None
    for_moderate_democrats_score: Optional[str] = None
    for_trump_but_moderate_score: Optional[str] = None
    for_trump_not_rinos_score: Optional[str] = None
    likely_to_vote_3rd_party_score: Optional[str] = None
    likely_to_vote_for_3rd_party_or_democrat_score: Optional[str] = None
    likely_to_vote_for_3rd_party_or_republican_score: Optional[str] = None

@dataclass
class EconomicInfo:
    """Economic information for an L2 voter."""
    estimated_income: Optional[str] = None
    home_value: Optional[str] = None
    home_purchase_price: Optional[str] = None
    home_purchase_year: Optional[str] = None
    dwelling_type: Optional[str] = None
    credit_rating: Optional[str] = None
    home_square_footage: Optional[str] = None
    bedrooms_count: Optional[int] = None
    rooms_count: Optional[int] = None
    home_swimming_pool: bool = False
    soho_indicator: bool = False
    auto_make_1: Optional[str] = None
    auto_model_1: Optional[str] = None
    auto_year_1: Optional[str] = None
    auto_make_2: Optional[str] = None
    auto_model_2: Optional[str] = None
    auto_year_2: Optional[str] = None
    motorcycle_make_1: Optional[str] = None
    motorcycle_model_1: Optional[str] = None
    household_net_worth: Optional[str] = None
    household_number_lines_of_credit: Optional[int] = None
    presence_of_cc: bool = False
    presence_of_gold_plat_cc: bool = False
    presence_of_premium_cc: bool = False
    presence_of_upscale_retail_cc: bool = False
    # Additional economic fields
    home_purchase_date: Optional[str] = None
    pass_prospector_home_value_mortgage_file: Optional[str] = None
    tax_assessed_value_total: Optional[str] = None
    home_mortgage_amount: Optional[str] = None
    home_mortgage_amount_code: Optional[str] = None
    home_purchase_price_code: Optional[str] = None
    tax_market_value_total: Optional[str] = None
    accessibility_handicap_flag: bool = False
    homeowner_probability_model: Optional[str] = None
    rooms_office_flag: bool = False
    cra_income_classification_code: Optional[str] = None
    # Area economic indicators
    area_pcnt_hh_married_couple_with_child: Optional[str] = None
    area_pcnt_hh_married_couple_no_child: Optional[str] = None
    area_pcnt_hh_spanish_speaking: Optional[str] = None
    state_income_decile: Optional[str] = None
    likely_income_ranking_by_area: Optional[str] = None
    likely_educational_attainment_ranking_by_area: Optional[str] = None
    social_ranking_index_by_area: Optional[str] = None
    social_ranking_index_by_individual: Optional[str] = None

@dataclass
class FamilyInfo:
    """Family information for an L2 voter."""
    household_size: Optional[int] = None
    adults_count: Optional[int] = None
    children_count: Optional[int] = None
    marital_status: Optional[str] = None
    single_parent_in_household: bool = False
    veteran_in_household: bool = False
    senior_adult_in_household: bool = False
    young_adult_in_household: bool = False
    # Alias for household_size to match agent code expectations
    total_persons: Optional[int] = None
    # Alias for adults_count to match agent code expectations
    number_of_adults: Optional[int] = None
    # Alias for children_count to match agent code expectations
    number_of_children: Optional[int] = None
    # Computed field for whether household has children
    has_children: bool = False
    # Aliases for fields expected by personal_summary.py
    is_veteran: bool = False  # Alias for veteran_in_household
    is_single_parent: bool = False  # Alias for single_parent_in_household
    has_senior_adult: bool = False  # Alias for senior_adult_in_household
    has_young_adult: bool = False  # Alias for young_adult_in_household
    # Additional missing fields
    disabled_in_hh: bool = False
    generations_in_hh: Optional[int] = None
    household_voters_count: Optional[int] = None
    presence_of_children_in_hh: bool = False
    assimilation_status: Optional[str] = None
    
    # Detailed household demographics by gender and age
    females_in_hh_18_24: Optional[int] = None
    females_in_hh_25_34: Optional[int] = None
    females_in_hh_35_44: Optional[int] = None
    females_in_hh_45_54: Optional[int] = None
    females_in_hh_55_64: Optional[int] = None
    females_in_hh_65_74: Optional[int] = None
    females_in_hh_75_plus: Optional[int] = None
    males_in_hh_18_24: Optional[int] = None
    males_in_hh_25_34: Optional[int] = None
    males_in_hh_35_44: Optional[int] = None
    males_in_hh_45_54: Optional[int] = None
    males_in_hh_55_64: Optional[int] = None
    males_in_hh_65_74: Optional[int] = None
    males_in_hh_75_plus: Optional[int] = None
    unknown_gender_in_hh_18_24: Optional[int] = None
    unknown_gender_in_hh_25_34: Optional[int] = None
    unknown_gender_in_hh_35_44: Optional[int] = None
    unknown_gender_in_hh_45_54: Optional[int] = None
    unknown_gender_in_hh_55_64: Optional[int] = None
    unknown_gender_in_hh_65_74: Optional[int] = None
    unknown_gender_in_hh_75_plus: Optional[int] = None
    
    # Children by age groups with detailed breakdowns
    children_0_2: Optional[int] = None
    children_0_2_female: Optional[int] = None
    children_0_2_male: Optional[int] = None
    children_0_2_unknown: Optional[int] = None
    children_3_5: Optional[int] = None
    children_3_5_female: Optional[int] = None
    children_3_5_male: Optional[int] = None
    children_3_5_unknown: Optional[int] = None
    children_6_10: Optional[int] = None
    children_6_10_female: Optional[int] = None
    children_6_10_male: Optional[int] = None
    children_6_10_unknown: Optional[int] = None
    children_11_15: Optional[int] = None
    children_11_15_female: Optional[int] = None
    children_11_15_male: Optional[int] = None
    children_11_15_unknown: Optional[int] = None
    children_16_17: Optional[int] = None
    children_16_17_female: Optional[int] = None
    children_16_17_male: Optional[int] = None
    children_16_17_unknown: Optional[int] = None
    
    # Household descriptions
    hh_gender_description: Optional[str] = None
    hh_parties_description: Optional[str] = None

@dataclass
class WorkInfo:
    """Work and education information for an L2 voter."""
    education_level: Optional[str] = None
    occupation: Optional[str] = None
    occupation_group: Optional[str] = None
    is_business_owner: bool = False
    is_african_american_professional: bool = False
    career_improvement: bool = False
    career_int: bool = False
    # Recent employment fields
    recent_employment_company: Optional[str] = None
    recent_employment_title: Optional[str] = None
    recent_employment_department: Optional[str] = None
    recent_employment_executive_level: Optional[str] = None

@dataclass
class ConsumerInfo:
    """Consumer behavior information for an L2 voter."""
    interests: Optional[List[str]] = None
    donor_categories: Optional[List[str]] = None
    lifestyle_categories: Optional[List[str]] = None
    shopping_preferences: Optional[List[str]] = None
    media_preferences: Optional[List[str]] = None
    technology_usage: Optional[List[str]] = None
    travel_preferences: Optional[List[str]] = None
    health_interests: Optional[List[str]] = None
    financial_interests: Optional[List[str]] = None
    do_not_call: bool = False
    language_code: Optional[str] = None
    religion_code: Optional[str] = None

@dataclass
class GeographicInfo:
    """Geographic and demographic information for an L2 voter."""
    # Basic geographic info
    census_tract: Optional[str] = None
    block_group: Optional[str] = None
    urban_rural: Optional[str] = None
    population_density: Optional[str] = None
    time_zone: Optional[str] = None
    rus_code: Optional[str] = None
    length_of_residence_code: Optional[str] = None
    
    # County and precinct
    county: Optional[str] = None
    precinct: Optional[str] = None
    fips: Optional[str] = None
    
    # Major political districts
    congressional_district: Optional[str] = None
    state_senate_district: Optional[str] = None
    state_house_district: Optional[str] = None
    state_legislative_district: Optional[str] = None
    
    # Cities and municipalities
    city: Optional[str] = None
    borough: Optional[str] = None
    borough_ward: Optional[str] = None
    township: Optional[str] = None
    township_ward: Optional[str] = None
    village: Optional[str] = None
    village_ward: Optional[str] = None
    hamlet_community_area: Optional[str] = None
    proposed_city: Optional[str] = None
    proposed_city_commissioner_district: Optional[str] = None
    
    # County level districts
    county_commissioner_district: Optional[str] = None
    county_supervisorial_district: Optional[str] = None
    
    # City level districts
    city_council_commissioner_district: Optional[str] = None
    city_mayoral_district: Optional[str] = None
    city_ward: Optional[str] = None
    town_council: Optional[str] = None
    town_district: Optional[str] = None
    town_ward: Optional[str] = None
    
    # Proposed/historical districts
    proposed_2024_congressional_district: Optional[str] = None
    proposed_2024_state_senate_district: Optional[str] = None
    proposed_2024_state_house_district: Optional[str] = None
    proposed_2024_state_legislative_district: Optional[str] = None
    
    # Historical districts (2001)
    district_2001_us_congressional: Optional[str] = None
    district_2001_state_house: Optional[str] = None
    district_2001_state_legislative: Optional[str] = None
    district_2001_state_senate: Optional[str] = None
    
    # Historical districts (2010)
    district_2010_us_congressional: Optional[str] = None
    district_2010_state_house: Optional[str] = None
    district_2010_state_legislative: Optional[str] = None
    district_2010_state_senate: Optional[str] = None
    
    # Address change tracking
    address_change_changed_cd: Optional[str] = None
    address_change_changed_county: Optional[str] = None
    address_change_changed_hd: Optional[str] = None
    address_change_changed_ld: Optional[str] = None
    address_change_changed_sd: Optional[str] = None

@dataclass
class JudicialDistrictInfo:
    """Judicial district information for an L2 voter."""
    judicial_appellate_district: Optional[str] = None
    judicial_chancery_court: Optional[str] = None
    judicial_circuit_court_district: Optional[str] = None
    judicial_county_board_of_review_district: Optional[str] = None
    judicial_county_court_district: Optional[str] = None
    judicial_district: Optional[str] = None
    judicial_district_court_district: Optional[str] = None
    judicial_family_court_district: Optional[str] = None
    judicial_jury_district: Optional[str] = None
    judicial_justice_of_the_peace: Optional[str] = None
    judicial_juvenile_court_district: Optional[str] = None
    judicial_magistrate_division: Optional[str] = None
    judicial_municipal_court_district: Optional[str] = None
    judicial_sub_circuit_district: Optional[str] = None
    judicial_superior_court_district: Optional[str] = None
    judicial_supreme_court_district: Optional[str] = None

@dataclass
class SchoolDistrictInfo:
    """School district information for an L2 voter."""
    city_school_district: Optional[str] = None
    college_board_district: Optional[str] = None
    community_college: Optional[str] = None
    community_college_at_large: Optional[str] = None
    community_college_commissioner_district: Optional[str] = None
    community_college_subdistrict: Optional[str] = None
    county_board_of_education_district: Optional[str] = None
    county_board_of_education_subdistrict: Optional[str] = None
    county_community_college_district: Optional[str] = None
    county_superintendent_of_schools_district: Optional[str] = None
    county_unified_school_district: Optional[str] = None
    education_commission_district: Optional[str] = None
    educational_service_district: Optional[str] = None
    educational_service_subdistrict: Optional[str] = None
    elementary_school_district: Optional[str] = None
    elementary_school_subdistrict: Optional[str] = None
    exempted_village_school_district: Optional[str] = None
    high_school_district: Optional[str] = None
    high_school_subdistrict: Optional[str] = None
    proposed_community_college: Optional[str] = None
    proposed_elementary_school_district: Optional[str] = None
    proposed_unified_school_district: Optional[str] = None
    regional_office_of_education_district: Optional[str] = None
    school_board_district: Optional[str] = None
    school_district: Optional[str] = None
    school_district_vocational: Optional[str] = None
    school_facilities_improvement_district: Optional[str] = None
    school_subdistrict: Optional[str] = None
    superintendent_of_schools_district: Optional[str] = None
    unified_school_district: Optional[str] = None
    unified_school_subdistrict: Optional[str] = None

@dataclass
class SpecialDistrictInfo:
    """Special district information for an L2 voter."""
    # Many special district types - comprehensive list
    district_4h_livestock: Optional[str] = None
    district_airport: Optional[str] = None
    district_annexation: Optional[str] = None
    district_aquatic_center: Optional[str] = None
    district_aquatic: Optional[str] = None
    district_assessment: Optional[str] = None
    district_bay_area_rapid_transit: Optional[str] = None
    district_board_of_education: Optional[str] = None
    district_board_of_education_sub: Optional[str] = None
    district_bonds: Optional[str] = None
    district_career_center: Optional[str] = None
    district_cemetery: Optional[str] = None
    district_central_committee: Optional[str] = None
    district_chemical_control: Optional[str] = None
    district_coast_water: Optional[str] = None
    district_committee_super: Optional[str] = None
    district_communications: Optional[str] = None
    district_community_council: Optional[str] = None
    district_community_council_sub: Optional[str] = None
    district_community_facilities: Optional[str] = None
    district_community_facilities_sub: Optional[str] = None
    district_community_hospital: Optional[str] = None
    district_community_planning_area: Optional[str] = None
    district_community_service: Optional[str] = None
    district_community_service_sub: Optional[str] = None
    district_congressional_township: Optional[str] = None
    district_conservation: Optional[str] = None
    district_conservation_sub: Optional[str] = None
    district_consolidated_water: Optional[str] = None
    district_control_zone: Optional[str] = None
    district_corrections: Optional[str] = None
    district_county_fire: Optional[str] = None
    district_county_hospital: Optional[str] = None
    district_county_legislative: Optional[str] = None
    district_county_library: Optional[str] = None
    district_county_memorial: Optional[str] = None
    district_county_paramedic: Optional[str] = None
    district_county_service_area: Optional[str] = None
    district_county_service_area_sub: Optional[str] = None
    district_county_sewer: Optional[str] = None
    district_county_water: Optional[str] = None
    district_county_water_landowner: Optional[str] = None
    district_county_water_sub: Optional[str] = None
    district_democratic_convention_member: Optional[str] = None
    district_democratic_zone: Optional[str] = None
    district_attorney: Optional[str] = None
    district_drainage: Optional[str] = None
    district_election_commissioner: Optional[str] = None
    district_emergency_communication_911: Optional[str] = None
    district_emergency_communication_911_sub: Optional[str] = None
    district_enterprise_zone: Optional[str] = None
    district_ext: Optional[str] = None
    district_facilities_improvement: Optional[str] = None
    district_fire: Optional[str] = None
    district_fire_maintenance: Optional[str] = None
    district_fire_protection: Optional[str] = None
    district_fire_protection_sub: Optional[str] = None
    district_fire_protection_tax_measure: Optional[str] = None
    district_fire_service_area: Optional[str] = None
    district_fire_sub: Optional[str] = None
    district_flood_control_zone: Optional[str] = None
    district_forest_preserve: Optional[str] = None
    district_garbage: Optional[str] = None
    district_geological_hazard_abatement: Optional[str] = None
    district_health: Optional[str] = None
    district_hospital: Optional[str] = None
    district_hospital_sub: Optional[str] = None
    district_improvement_landowner: Optional[str] = None
    district_independent_fire: Optional[str] = None
    district_irrigation: Optional[str] = None
    district_irrigation_sub: Optional[str] = None
    district_island: Optional[str] = None
    district_land_commission: Optional[str] = None
    district_landscaping_and_lighting_assessment: Optional[str] = None
    district_law_enforcement: Optional[str] = None
    district_learning_community_coordinating_council: Optional[str] = None
    district_levee: Optional[str] = None
    district_levee_reconstruction_assessment: Optional[str] = None
    district_library: Optional[str] = None
    district_library_services: Optional[str] = None
    district_library_sub: Optional[str] = None
    district_lighting: Optional[str] = None
    district_local_hospital: Optional[str] = None
    district_local_park: Optional[str] = None
    district_maintenance: Optional[str] = None
    district_master_plan: Optional[str] = None
    district_memorial: Optional[str] = None
    district_metro_service: Optional[str] = None
    district_metro_service_sub: Optional[str] = None
    district_metro_transit: Optional[str] = None
    district_metropolitan_water: Optional[str] = None
    district_middle_school: Optional[str] = None
    district_mosquito_abatement: Optional[str] = None
    district_mountain_water: Optional[str] = None
    district_multi_township_assessor: Optional[str] = None
    district_municipal_advisory_council: Optional[str] = None
    district_municipal_utility: Optional[str] = None
    district_municipal_utility_sub: Optional[str] = None
    district_municipal_water: Optional[str] = None
    district_municipal_water_sub: Optional[str] = None
    district_museum: Optional[str] = None
    district_northeast_soil_and_water: Optional[str] = None
    district_open_space: Optional[str] = None
    district_open_space_sub: Optional[str] = None
    district_other: Optional[str] = None
    district_paramedic: Optional[str] = None
    district_park_commissioner: Optional[str] = None
    district_park: Optional[str] = None
    district_park_sub: Optional[str] = None
    district_planning_area: Optional[str] = None
    district_police: Optional[str] = None
    district_port: Optional[str] = None
    district_port_sub: Optional[str] = None
    district_power: Optional[str] = None
    district_proposed: Optional[str] = None
    district_proposed_fire: Optional[str] = None
    district_public_airport: Optional[str] = None
    district_public_regulation_commission: Optional[str] = None
    district_public_service_commission: Optional[str] = None
    district_public_utility: Optional[str] = None
    district_public_utility_sub: Optional[str] = None
    district_rapid_transit: Optional[str] = None
    district_rapid_transit_sub: Optional[str] = None
    district_reclamation: Optional[str] = None
    district_recreation: Optional[str] = None
    district_recreational_sub: Optional[str] = None
    district_republican_area: Optional[str] = None
    district_republican_convention_member: Optional[str] = None
    district_resort_improvement: Optional[str] = None
    district_resource_conservation: Optional[str] = None
    district_river_water: Optional[str] = None
    district_road_maintenance: Optional[str] = None
    district_rural_service: Optional[str] = None
    district_sanitary: Optional[str] = None
    district_sanitary_sub: Optional[str] = None
    district_service_area: Optional[str] = None
    district_sewer: Optional[str] = None
    district_sewer_maintenance: Optional[str] = None
    district_sewer_sub: Optional[str] = None
    district_snow_removal: Optional[str] = None
    district_soil_and_water: Optional[str] = None
    district_soil_and_water_at_large: Optional[str] = None
    district_special_reporting: Optional[str] = None
    district_special_tax: Optional[str] = None
    district_state_board_of_equalization: Optional[str] = None
    district_storm_water: Optional[str] = None
    district_street_lighting: Optional[str] = None
    district_transit: Optional[str] = None
    district_transit_sub: Optional[str] = None
    district_tricity_service: Optional[str] = None
    district_tv_translator: Optional[str] = None
    district_unincorporated: Optional[str] = None
    district_unincorporated_park: Optional[str] = None
    district_unprotected_fire: Optional[str] = None
    district_ute_creek_soil: Optional[str] = None
    district_vector_control: Optional[str] = None
    district_vote_by_mail_area: Optional[str] = None
    district_wastewater: Optional[str] = None
    district_water_agency: Optional[str] = None
    district_water_agency_sub: Optional[str] = None
    district_water_conservation: Optional[str] = None
    district_water_conservation_sub: Optional[str] = None
    district_water_control_water_conservation: Optional[str] = None
    district_water_control_water_conservation_sub: Optional[str] = None
    district_water: Optional[str] = None
    district_water_public_utility: Optional[str] = None
    district_water_public_utility_sub: Optional[str] = None
    district_water_replacement: Optional[str] = None
    district_water_replacement_sub: Optional[str] = None
    district_water_sub: Optional[str] = None
    district_weed: Optional[str] = None

@dataclass
class PhoneInfo:
    """Phone information for an L2 voter."""
    phone_number_available: bool = False
    landline_phone_available: bool = False
    landline_area_code: Optional[str] = None
    landline_unformatted: Optional[str] = None
    landline_confidence_code: Optional[str] = None
    landline_7digit: Optional[str] = None
    landline_formatted: Optional[str] = None
    cell_phone_available: bool = False
    cell_phone_unformatted: Optional[str] = None
    cell_confidence_code: Optional[str] = None
    cell_phone_formatted: Optional[str] = None
    cell_phone_only: bool = False
    do_not_call: bool = False

@dataclass
class MarketAreaInfo:
    """Market area information for an L2 voter."""
    designated_market_area_dma: Optional[str] = None
    consumerdata_csa: Optional[str] = None
    consumerdata_cbsa: Optional[str] = None
    consumerdata_msa: Optional[str] = None
    # Area demographics
    area_pcnt_hh_with_children: Optional[str] = None
    area_median_housing_value: Optional[str] = None
    area_median_hh_income: Optional[str] = None
    area_median_education_years: Optional[str] = None

@dataclass
class FECDonorInfo:
    """FEC donor information for an L2 voter."""
    avg_donation: Optional[str] = None
    avg_donation_range: Optional[str] = None
    last_donation_date: Optional[str] = None
    number_of_donations: Optional[int] = None
    primary_recipient: Optional[str] = None
    total_donations_amount: Optional[str] = None
    total_donations_amount_range: Optional[str] = None
    # Alias for personal_summary.py compatibility
    total_donations_range: Optional[str] = None

@dataclass
class ElectionHistory:
    """Election participation history for an L2 voter."""
    # Future elections
    any_election_2027: Optional[str] = None
    general_2026: Optional[str] = None
    primary_2026: Optional[str] = None
    other_election_2026: Optional[str] = None
    any_election_2025: Optional[str] = None
    
    # Recent elections
    general_2024: Optional[str] = None
    primary_2024: Optional[str] = None
    presidential_primary_2024: Optional[str] = None
    other_election_2024: Optional[str] = None
    any_election_2023: Optional[str] = None
    general_2022: Optional[str] = None
    primary_2022: Optional[str] = None
    other_election_2022: Optional[str] = None
    any_election_2021: Optional[str] = None
    general_2020: Optional[str] = None
    primary_2020: Optional[str] = None
    presidential_primary_2020: Optional[str] = None
    other_election_2020: Optional[str] = None
    any_election_2019: Optional[str] = None
    
    # Historical elections
    general_2018: Optional[str] = None
    primary_2018: Optional[str] = None
    other_election_2018: Optional[str] = None
    any_election_2017: Optional[str] = None
    general_2016: Optional[str] = None
    primary_2016: Optional[str] = None
    presidential_primary_2016: Optional[str] = None
    other_election_2016: Optional[str] = None
    any_election_2015: Optional[str] = None
    general_2014: Optional[str] = None
    primary_2014: Optional[str] = None
    other_election_2014: Optional[str] = None
    any_election_2013: Optional[str] = None
    general_2012: Optional[str] = None
    primary_2012: Optional[str] = None
    presidential_primary_2012: Optional[str] = None
    other_election_2012: Optional[str] = None
    any_election_2011: Optional[str] = None
    general_2010: Optional[str] = None
    primary_2010: Optional[str] = None
    other_election_2010: Optional[str] = None
    any_election_2009: Optional[str] = None
    general_2008: Optional[str] = None
    primary_2008: Optional[str] = None
    presidential_primary_2008: Optional[str] = None
    other_election_2008: Optional[str] = None
    any_election_2007: Optional[str] = None
    general_2006: Optional[str] = None
    primary_2006: Optional[str] = None
    other_election_2006: Optional[str] = None
    any_election_2005: Optional[str] = None
    general_2004: Optional[str] = None
    primary_2004: Optional[str] = None
    presidential_primary_2004: Optional[str] = None
    other_election_2004: Optional[str] = None
    any_election_2003: Optional[str] = None
    general_2002: Optional[str] = None
    primary_2002: Optional[str] = None
    other_election_2002: Optional[str] = None
    any_election_2001: Optional[str] = None
    general_2000: Optional[str] = None
    primary_2000: Optional[str] = None
    presidential_primary_2000: Optional[str] = None
    other_election_2000: Optional[str] = None
    
    # Primary ballot request history (PRI_BLT)
    pri_blt_2022: Optional[str] = None
    pri_blt_2021: Optional[str] = None
    pri_blt_2020: Optional[str] = None
    pri_blt_2019: Optional[str] = None
    pri_blt_2018: Optional[str] = None
    pri_blt_2017: Optional[str] = None
    pri_blt_2016: Optional[str] = None
    pri_blt_2015: Optional[str] = None
    pri_blt_2014: Optional[str] = None
    pri_blt_2013: Optional[str] = None
    pri_blt_2012: Optional[str] = None
    pri_blt_2011: Optional[str] = None
    pri_blt_2010: Optional[str] = None
    pri_blt_2009: Optional[str] = None
    pri_blt_2008: Optional[str] = None
    pri_blt_2007: Optional[str] = None
    pri_blt_2006: Optional[str] = None
    pri_blt_2005: Optional[str] = None
    pri_blt_2004: Optional[str] = None
    pri_blt_2003: Optional[str] = None
    pri_blt_2002: Optional[str] = None
    pri_blt_2001: Optional[str] = None
    pri_blt_2000: Optional[str] = None

@dataclass
class MobileAdvertisingInfo:
    """Mobile Advertising ID (MAID) information for an L2 voter."""
    maid_available: bool = False
    maid_1: Optional[str] = None
    maid_1_cell_phone_system: Optional[str] = None
    maid_2: Optional[str] = None
    maid_2_cell_phone_system: Optional[str] = None
    maid_3: Optional[str] = None
    maid_3_cell_phone_system: Optional[str] = None
    maid_4: Optional[str] = None
    maid_4_cell_phone_system: Optional[str] = None
    maid_5: Optional[str] = None
    maid_5_cell_phone_system: Optional[str] = None
    maid_ip_available: bool = False
    maid_ip_1: Optional[str] = None
    maid_ip_2: Optional[str] = None
    maid_ip_3: Optional[str] = None
    maid_ip_4: Optional[str] = None
    maid_ip_5: Optional[str] = None

class L2DataRow:
    """
    Comprehensive L2 data row containing all voter information.
    Based on actual field names from the test data.
    """
    
    def __init__(self, data: Dict[str, Any]):
        """
        Initialize with raw L2 data dictionary.
        
        Args:
            data (Dict[str, Any]): Raw L2 data from CSV
        """
        self.raw_data = data
        self.sequence = data.get('SEQUENCE', None)
        self.lalvoterid = data.get('LALVOTERID', None)
        
        # Parse data into structured components
        self.personal = self._parse_personal_info(data)
        self.address = self._parse_address_info(data)
        self.political = self._parse_political_info(data)
        self.economic = self._parse_economic_info(data)
        self.family = self._parse_family_info(data)
        self.work = self._parse_work_info(data)
        self.consumer = self._parse_consumer_info(data)
        self.geographic = self._parse_geographic_info(data)
        self.judicial_districts = self._parse_judicial_district_info(data)
        self.school_districts = self._parse_school_district_info(data)
        self.special_districts = self._parse_special_district_info(data)
        self.election_history = self._parse_election_history(data)
        self.fec_donor = self._parse_fec_donor_info(data)
        self.market_area = self._parse_market_area_info(data)
        self.phone = self._parse_phone_info(data)
        self.mobile_advertising = self._parse_mobile_advertising_info(data)
    
    def _parse_personal_info(self, data: Dict[str, Any]) -> PersonalInfo:
        """Parse personal information from raw data."""
        return PersonalInfo(
            first_name=data.get('Voters_FirstName', None),
            middle_name=data.get('Voters_MiddleName', None),
            last_name=data.get('Voters_LastName', None),
            name_suffix=data.get('Voters_NameSuffix', None),
            age=self._safe_int(data.get('Voters_Age', None)),
            gender=data.get('Voters_Gender', None),
            birth_date=data.get('Voters_BirthDate', None),
            birth_date_confidence=data.get('BirthDateConfidence_Description', None),
            county_ethnic_description=data.get('CountyEthnic_Description', None),
            county_ethnic_lal_code=data.get('CountyEthnic_LALEthnicCode', None),
            ethnicity=data.get('Ethnic_Description', None),
            place_of_birth=data.get('Voters_PlaceOfBirth', None),
            marital_status=data.get('ConsumerData_Marital_Status', None),
            ethnic_group_1_desc=data.get('EthnicGroups_EthnicGroup1Desc', None),
            hispanic_country_code=data.get('ConsumerData_Hispanic_Country_Code', None),
            language_code=data.get('ConsumerData_Language_Code', None),
            religion_code=data.get('ConsumerData_Religion_Code', None),
            inferred_hh_rank=data.get('ConsumerData_Inferred_HH_Rank', None),
            # Additional voter identification
            state_voter_id=data.get('Voters_StateVoterID', None),
            county_voter_id=data.get('Voters_CountyVoterID', None),
            sequence_zigzag=data.get('Voters_SequenceZigZag', None),
            sequence_odd_even=data.get('Voters_SequenceOddEven', None),
            fips=data.get('Voters_FIPS', None),
            # Moved from data
            moved_from_date=data.get('Voters_MovedFrom_Date', None),
            moved_from_state=data.get('Voters_MovedFrom_State', None),
            moved_from_party=data.get('Voters_MovedFrom_Party_Description', None),
            moved_from_voting_performance_combined=data.get('Voters_MovedFrom_VotingPerformanceEvenYearGeneralAndPrimary', None),
            moved_from_voting_performance_general=data.get('Voters_MovedFrom_VotingPerformanceEvenYearGeneral', None),
            moved_from_voting_performance_primary=data.get('Voters_MovedFrom_VotingPerformanceEvenYearPrimary', None),
            moved_from_voting_performance_minor=data.get('Voters_MovedFrom_VotingPerformanceMinorElection', None)
        )
    
    def _parse_address_info(self, data: Dict[str, Any]) -> AddressInfo:
        """Parse address information from raw data."""
        return AddressInfo(
            # Residence address fields
            residence_address_line=data.get('Residence_Addresses_AddressLine', None),
            residence_extra_address_line=data.get('Residence_Addresses_ExtraAddressLine', None),
            residence_city=data.get('Residence_Addresses_City', None),
            residence_state=data.get('Residence_Addresses_State', None),
            residence_zip=data.get('Residence_Addresses_Zip', None),
            residence_zip_plus4=data.get('Residence_Addresses_ZipPlus4', None),
            residence_dpbc=data.get('Residence_Addresses_DPBC', None),
            residence_check_digit=data.get('Residence_Addresses_CheckDigit', None),
            residence_house_number=data.get('Residence_Addresses_HouseNumber', None),
            residence_prefix_direction=data.get('Residence_Addresses_PrefixDirection', None),
            residence_street_name=data.get('Residence_Addresses_StreetName', None),
            residence_designator=data.get('Residence_Addresses_Designator', None),
            residence_suffix_direction=data.get('Residence_Addresses_SuffixDirection', None),
            residence_apartment_num=data.get('Residence_Addresses_ApartmentNum', None),
            residence_apartment_type=data.get('Residence_Addresses_ApartmentType', None),
            residence_cass_err_stat_code=data.get('Residence_Addresses_CassErrStatCode', None),
            residence_county=data.get('Residence_Addresses_County', None),
            residence_congressional_district=data.get('Residence_Addresses_CongressionalDistrict', None),
            residence_census_tract=data.get('Residence_Addresses_CensusTract', None),
            residence_census_block_group=data.get('Residence_Addresses_CensusBlockGroup', None),
            residence_census_block=data.get('Residence_Addresses_CensusBlock', None),
            residence_complete_census_geocode=data.get('Residence_Addresses_Complete_Census_Geocode', None),
            residence_latitude=self._safe_float(data.get('Residence_Addresses_Latitude', None)),
            residence_longitude=self._safe_float(data.get('Residence_Addresses_Longitude', None)),
            residence_lat_long_accuracy=data.get('Residence_Addresses_LatLongAccuracy', None),
            residence_family_id=data.get('Residence_Families_FamilyID', None),
            residence_property_land_square_footage=data.get('Residence_Addresses_Property_Land_Square_Footage', None),
            residence_property_type=data.get('Residence_Addresses_Property_Type', None),
            residence_density=data.get('Residence_Addresses_Density', None),
            
            # Mailing address fields
            mailing_address_line=data.get('Mailing_Addresses_AddressLine', None),
            mailing_extra_address_line=data.get('Mailing_Addresses_ExtraAddressLine', None),
            mailing_city=data.get('Mailing_Addresses_City', None),
            mailing_state=data.get('Mailing_Addresses_State', None),
            mailing_zip=data.get('Mailing_Addresses_Zip', None),
            mailing_zip_plus4=data.get('Mailing_Addresses_ZipPlus4', None),
            mailing_dpbc=data.get('Mailing_Addresses_DPBC', None),
            mailing_check_digit=data.get('Mailing_Addresses_CheckDigit', None),
            mailing_house_number=data.get('Mailing_Addresses_HouseNumber', None),
            mailing_prefix_direction=data.get('Mailing_Addresses_PrefixDirection', None),
            mailing_street_name=data.get('Mailing_Addresses_StreetName', None),
            mailing_designator=data.get('Mailing_Addresses_Designator', None),
            mailing_suffix_direction=data.get('Mailing_Addresses_SuffixDirection', None),
            mailing_apartment_num=data.get('Mailing_Addresses_ApartmentNum', None),
            mailing_apartment_type=data.get('Mailing_Addresses_ApartmentType', None),
            mailing_cass_err_stat_code=data.get('Mailing_Addresses_CassErrStatCode', None),
            mailing_family_id=data.get('Mailing_Families_FamilyID', None)
        )
    
    def _parse_political_info(self, data: Dict[str, Any]) -> PoliticalInfo:
        """Parse political information from raw data."""
        voting_performance = data.get('Voters_VotingPerformanceEvenYearGeneralAndPrimary', None)
        return PoliticalInfo(
            party=data.get('Parties_Description', None),
            registration_date=data.get('Voters_OfficialRegDate', None),
            is_active=data.get('Voters_Active', 'Y') == 'Y',
            voting_performance=voting_performance,
            voting_performance_even_year_general=data.get('Voters_VotingPerformanceEvenYearGeneral', None),
            voting_performance_even_year_primary=data.get('Voters_VotingPerformanceEvenYearPrimary', None),
            voting_performance_even_year_general_and_primary=voting_performance,
            voting_performance_minor_election=data.get('Voters_VotingPerformanceMinorElection', None),
            voting_performance_combined=voting_performance,
            absentee_type=data.get('AbsenteeTypes_Description', None),
            calculated_registration_date=data.get('Voters_CalculatedRegDate', None),
            party_change_date=data.get('VoterParties_Change_Changed_Party', None),
            voting_performance_general=data.get('Voters_VotingPerformanceEvenYearGeneral', None),
            voting_performance_primary=data.get('Voters_VotingPerformanceEvenYearPrimary', None),
            progressive_democrat_flag=data.get('ConsumerData_Progressive_Democrat_Flag', None),
            moderate_democrat_flag=data.get('ConsumerData_Moderate_Democrat_Flag', None),
            moderate_republican_flag=data.get('ConsumerData_Moderate_Republican_Flag', None),
            conservative_republican_flag=data.get('ConsumerData_Conservative_Republican_Flag', None),
            likely_to_vote_3rd_party_flag=data.get('ConsumerData_Likely_to_Vote_3rd_Party_Flag', None),
            for_liberal_democrats_flag=data.get('ConsumerData_For_Liberal_Democrats_Flag', None),
            for_moderate_democrats_flag=data.get('ConsumerData_For_Moderate_Democrats_Flag', None),
            for_trump_but_moderate_flag=data.get('ConsumerData_For_Trump_But_Moderate_Flag', None),
            for_trump_not_rinos_flag=data.get('ConsumerData_For_Trump_not_RINOs_Flag', None),
            likely_to_vote_for_3rd_party_or_democrat_flag=data.get('ConsumerData_Likely_to_Vote_for_3rd_Party_or_Democrat_Flag', None),
            likely_to_vote_for_3rd_party_or_republican_flag=data.get('ConsumerData_Likely_to_Vote_for_3rd_Party_or_Republican_Flag', None),
            # Political scores
            progressive_democrat_score=data.get('ConsumerData_Progressive_Democrat_Score', None),
            moderate_democrat_score=data.get('ConsumerData_Moderate_Democrat_Score', None),
            moderate_republican_score=data.get('ConsumerData_Moderate_Republican_Score', None),
            conservative_republican_score=data.get('ConsumerData_Conservative_Republican_Score', None),
            for_liberal_democrats_score=data.get('ConsumerData_For_Liberal_Democrats_Score', None),
            for_moderate_democrats_score=data.get('ConsumerData_For_Moderate_Democrats_Score', None),
            for_trump_but_moderate_score=data.get('ConsumerData_For_Trump_But_Moderate_Score', None),
            for_trump_not_rinos_score=data.get('ConsumerData_For_Trump_not_RINOs_Score', None),
            likely_to_vote_3rd_party_score=data.get('ConsumerData_Likely_to_Vote_3rd_Party_Score', None),
            likely_to_vote_for_3rd_party_or_democrat_score=data.get('ConsumerData_Likely_to_Vote_for_3rd_Party_or_Democrat_Score', None),
            likely_to_vote_for_3rd_party_or_republican_score=data.get('ConsumerData_Likely_to_Vote_for_3rd_Party_or_Republican_Score', None)
        )
    
    def _parse_economic_info(self, data: Dict[str, Any]) -> EconomicInfo:
        """Parse economic information from raw data."""
        return EconomicInfo(
            estimated_income=data.get('ConsumerData_Estimated_Income_Amount', None),
            home_value=data.get('ConsumerData_Home_Est_Current_Value_Code', None),
            home_purchase_price=data.get('ConsumerData_Home_Purchase_Price', None),
            home_purchase_year=data.get('ConsumerData_Home_Purchase_Year', None),
            dwelling_type=data.get('ConsumerData_Dwelling_Type', None),
            credit_rating=data.get('ConsumerData_Credit_Rating', None),
            home_square_footage=data.get('Residence_Addresses_Property_Home_Square_Footage', None),
            bedrooms_count=self._safe_int(data.get('ConsumerData_BedroomsCount', None)),
            rooms_count=self._safe_int(data.get('ConsumerData_RoomsCount', None)),
            home_swimming_pool=data.get('ConsumerData_Home_Swimming_Pool', 'N') == 'Y',
            soho_indicator=data.get('ConsumerData_SOHO_Indicator', 'N') == 'Y',
            auto_make_1=data.get('ConsumerData_Auto_Make_1', None),
            auto_model_1=data.get('ConsumerData_Auto_Model_1', None),
            auto_year_1=data.get('ConsumerData_Auto_Year_1', None),
            auto_make_2=data.get('ConsumerData_Auto_Make_2', None),
            auto_model_2=data.get('ConsumerData_Auto_Model_2', None),
            auto_year_2=data.get('ConsumerData_Auto_Year_2', None),
            motorcycle_make_1=data.get('ConsumerData_Motorcycle_Make_1', None),
            motorcycle_model_1=data.get('ConsumerData_Motorcycle_Model_1', None),
            household_net_worth=data.get('ConsumerData_Household_Net_Worth', None),
            household_number_lines_of_credit=self._safe_int(data.get('ConsumerData_Household_Number_Lines_Of_Credit', None)),
            presence_of_cc=data.get('ConsumerData_Presence_Of_CC', 'N') == 'Y',
            presence_of_gold_plat_cc=data.get('ConsumerData_Presence_Of_Gold_Plat_CC', 'N') == 'Y',
            presence_of_premium_cc=data.get('ConsumerData_Presence_Of_Premium_CC', 'N') == 'Y',
            presence_of_upscale_retail_cc=data.get('ConsumerData_Presence_Of_Upscale_Retail_CC', 'N') == 'Y',
            # Additional economic fields
            home_purchase_date=data.get('ConsumerData_Home_Purchase_Date', None),
            pass_prospector_home_value_mortgage_file=data.get('ConsumerData_PASS_Prospector_Home_Value_Mortgage_File', None),
            tax_assessed_value_total=data.get('ConsumerData_TaxAssessedValueTotal', None),
            home_mortgage_amount=data.get('ConsumerData_Home_Mortgage_Amount', None),
            home_mortgage_amount_code=data.get('ConsumerData_Home_Mortgage_Amount_Code', None),
            home_purchase_price_code=data.get('ConsumerData_Home_Purchase_Price_Code', None),
            tax_market_value_total=data.get('ConsumerData_TaxMarketValueTotal', None),
            accessibility_handicap_flag=data.get('ConsumerData_AccessibilityHandicapFlag', 'N') == 'Y',
            homeowner_probability_model=data.get('ConsumerData_Homeowner_Probability_Model', None),
            rooms_office_flag=data.get('ConsumerData_RoomsOfficeFlag', 'N') == 'Y',
            cra_income_classification_code=data.get('ConsumerData_CRA_Income_Classification_Code', None),
            # Area economic indicators
            area_pcnt_hh_married_couple_with_child=data.get('ConsumerData_AreaPcntHHMarriedCoupleWithChild', None),
            area_pcnt_hh_married_couple_no_child=data.get('ConsumerData_AreaPcntHHMarriedCoupleNoChild', None),
            area_pcnt_hh_spanish_speaking=data.get('ConsumerData_AreaPcntHHSpanishSpeaking', None),
            state_income_decile=data.get('ConsumerData_StateIncomeDecile', None),
            likely_income_ranking_by_area=data.get('ConsumerData_Likely_Income_Ranking_by_Area', None),
            likely_educational_attainment_ranking_by_area=data.get('ConsumerData_Likely_Educational_Attainment_Ranking_by_Area', None),
            social_ranking_index_by_area=data.get('ConsumerData_Social_Ranking_Index_by_Area', None),
            social_ranking_index_by_individual=data.get('ConsumerData_Social_Ranking_Index_by_Individual', None)
        )
    
    def _parse_family_info(self, data: Dict[str, Any]) -> FamilyInfo:
        """Parse family information from raw data."""
        household_size = self._safe_int(data.get('ConsumerData_Number_Of_Persons_in_HH', None))
        adults_count = self._safe_int(data.get('ConsumerData_Number_Of_Adults_in_HH', None))
        children_count = self._safe_int(data.get('ConsumerData_Number_Of_Children_in_HH', None))
        single_parent = data.get('ConsumerData_Single_Parent_in_Household', 'N') == 'Y'
        veteran = data.get('ConsumerDataLL_Veteran', 'N') == 'Y'
        senior_adult = data.get('ConsumerData_Senior_Adult_In_HH', 'N') == 'Y'
        young_adult = data.get('ConsumerData_Young_Adult_In_HH', 'N') == 'Y'
        disabled = data.get('ConsumerData_Disabled_In_HH', 'N') == 'Y'
        presence_of_children = data.get('ConsumerData_Presence_Of_Children_in_HH', 'N') == 'Y'
        
        return FamilyInfo(
            household_size=household_size,
            adults_count=adults_count,
            children_count=children_count,
            marital_status=data.get('ConsumerData_Marital_Status', None),
            single_parent_in_household=single_parent,
            veteran_in_household=veteran,
            senior_adult_in_household=senior_adult,
            young_adult_in_household=young_adult,
            total_persons=household_size,
            number_of_adults=adults_count,
            number_of_children=children_count,
            has_children=children_count > 0 if children_count is not None else False,
            # Alias fields for personal_summary.py
            is_veteran=veteran,
            is_single_parent=single_parent,
            has_senior_adult=senior_adult,
            has_young_adult=young_adult,
            disabled_in_hh=disabled,
            generations_in_hh=self._safe_int(data.get('ConsumerData_Generations_In_HH', None)),
            household_voters_count=self._safe_int(data.get('Residence_Families_HHVotersCount', None)),
            presence_of_children_in_hh=presence_of_children,
            assimilation_status=data.get('ConsumerData_Assimilation_Status', None),
            
            # Detailed household demographics by gender and age
            females_in_hh_18_24=self._safe_int(data.get('ConsumerData_Females_in_HH_18_24', None)),
            females_in_hh_25_34=self._safe_int(data.get('ConsumerData_Females_in_HH_25_34', None)),
            females_in_hh_35_44=self._safe_int(data.get('ConsumerData_Females_in_HH_35_44', None)),
            females_in_hh_45_54=self._safe_int(data.get('ConsumerData_Females_in_HH_45_54', None)),
            females_in_hh_55_64=self._safe_int(data.get('ConsumerData_Females_in_HH_55_64', None)),
            females_in_hh_65_74=self._safe_int(data.get('ConsumerData_Females_in_HH_65_74', None)),
            females_in_hh_75_plus=self._safe_int(data.get('ConsumerData_Females_in_HH_75_Plus', None)),
            males_in_hh_18_24=self._safe_int(data.get('ConsumerData_Males_in_HH_18_24', None)),
            males_in_hh_25_34=self._safe_int(data.get('ConsumerData_Males_in_HH_25_34', None)),
            males_in_hh_35_44=self._safe_int(data.get('ConsumerData_Males_in_HH_35_44', None)),
            males_in_hh_45_54=self._safe_int(data.get('ConsumerData_Males_in_HH_45_54', None)),
            males_in_hh_55_64=self._safe_int(data.get('ConsumerData_Males_in_HH_55_64', None)),
            males_in_hh_65_74=self._safe_int(data.get('ConsumerData_Males_in_HH_65_74', None)),
            males_in_hh_75_plus=self._safe_int(data.get('ConsumerData_Males_in_HH_75_Plus', None)),
            unknown_gender_in_hh_18_24=self._safe_int(data.get('ConsumerData_Unknown_Gender_in_HH_18_24', None)),
            unknown_gender_in_hh_25_34=self._safe_int(data.get('ConsumerData_Unknown_Gender_in_HH_25_34', None)),
            unknown_gender_in_hh_35_44=self._safe_int(data.get('ConsumerData_Unknown_Gender_in_HH_35_44', None)),
            unknown_gender_in_hh_45_54=self._safe_int(data.get('ConsumerData_Unknown_Gender_in_HH_45_54', None)),
            unknown_gender_in_hh_55_64=self._safe_int(data.get('ConsumerData_Unknown_Gender_in_HH_55_64', None)),
            unknown_gender_in_hh_65_74=self._safe_int(data.get('ConsumerData_Unknown_Gender_in_HH_65_74', None)),
            unknown_gender_in_hh_75_plus=self._safe_int(data.get('ConsumerData_Unknown_Gender_in_HH_75_Plus', None)),
            
            # Children by age groups with detailed breakdowns
            children_0_2=self._safe_int(data.get('ConsumerData_Children_in_HH_Age_00_02', None)),
            children_0_2_female=self._safe_int(data.get('ConsumerData_Children_in_HH_Age_00_02_Female', None)),
            children_0_2_male=self._safe_int(data.get('ConsumerData_Children_in_HH_Age_00_02_Male', None)),
            children_0_2_unknown=self._safe_int(data.get('ConsumerData_Children_in_HH_Age_00_02_Unknown', None)),
            children_3_5=self._safe_int(data.get('ConsumerData_Children_in_HH_Age_03_05', None)),
            children_3_5_female=self._safe_int(data.get('ConsumerData_Children_in_HH_Age_03_05_Female', None)),
            children_3_5_male=self._safe_int(data.get('ConsumerData_Children_in_HH_Age_03_05_Male', None)),
            children_3_5_unknown=self._safe_int(data.get('ConsumerData_Children_in_HH_Age_03_05_Unknown', None)),
            children_6_10=self._safe_int(data.get('ConsumerData_Children_in_HH_Age_06_10', None)),
            children_6_10_female=self._safe_int(data.get('ConsumerData_Children_in_HH_Age_06_10_Female', None)),
            children_6_10_male=self._safe_int(data.get('ConsumerData_Children_in_HH_Age_06_10_Male', None)),
            children_6_10_unknown=self._safe_int(data.get('ConsumerData_Children_in_HH_Age_06_10_Unknown', None)),
            children_11_15=self._safe_int(data.get('ConsumerData_Children_in_HH_Age_11_15', None)),
            children_11_15_female=self._safe_int(data.get('ConsumerData_Children_in_HH_Age_11_15_Female', None)),
            children_11_15_male=self._safe_int(data.get('ConsumerData_Children_in_HH_Age_11_15_Male', None)),
            children_11_15_unknown=self._safe_int(data.get('ConsumerData_Children_in_HH_Age_11_15_Unknown', None)),
            children_16_17=self._safe_int(data.get('ConsumerData_Children_in_HH_Age_16_17', None)),
            children_16_17_female=self._safe_int(data.get('ConsumerData_Children_in_HH_Age_16_17_Female', None)),
            children_16_17_male=self._safe_int(data.get('ConsumerData_Children_in_HH_Age_16_17_Male', None)),
            children_16_17_unknown=self._safe_int(data.get('ConsumerData_Children_in_HH_Age_16_17_Unknown', None)),
            
            # Household descriptions
            hh_gender_description=data.get('Residence_HHGender_Description', None),
            hh_parties_description=data.get('Residence_HHParties_Description', None)
        )
    
    def _parse_work_info(self, data: Dict[str, Any]) -> WorkInfo:
        """Parse work and education information from raw data."""
        return WorkInfo(
            education_level=data.get('ConsumerData_Education_of_Person', None),
            occupation=data.get('ConsumerData_Occupation_of_Person', None),
            occupation_group=data.get('ConsumerData_Occupation_Group', None),
            is_business_owner=data.get('ConsumerData_Business_Owner', 'N') == 'Y',
            is_african_american_professional=data.get('ConsumerData_African_American_Professional_in_Household', 'N') == 'Y',
            career_improvement=data.get('ConsumerData_Career_Improvement', 'N') == 'Y',
            career_int=data.get('ConsumerData_Career_Int', 'N') == 'Y',
            # Recent employment fields
            recent_employment_company=data.get('ConsumerData_LikelyRecentEmployment_Company_Name', None),
            recent_employment_title=data.get('ConsumerData_LikelyRecentEmployment_Standardized_Title', None),
            recent_employment_department=data.get('ConsumerData_LikelyRecentEmployment_Executive_Department', None),
            recent_employment_executive_level=data.get('ConsumerData_LikelyRecentEmployment_Executive_Level', None)
        )
    
    def _parse_consumer_info(self, data: Dict[str, Any]) -> ConsumerInfo:
        """Parse consumer behavior information from raw data."""
        # Parse individual interest flags from the data
        interests = self._parse_interest_flags(data)
        
        return ConsumerInfo(
            interests=interests,
            donor_categories=self._parse_donor_categories(data),
            lifestyle_categories=self._parse_lifestyle_categories(data),
            shopping_preferences=self._parse_shopping_preferences(data),
            media_preferences=self._parse_media_preferences(data),
            technology_usage=self._parse_technology_usage(data),
            travel_preferences=self._parse_travel_preferences(data),
            health_interests=self._parse_health_interests(data),
            financial_interests=self._parse_financial_interests(data),
            do_not_call=data.get('ConsumerData_Do_Not_Call', 'N') == 'Y',
            language_code=data.get('ConsumerData_Language_Code', None),
            religion_code=data.get('ConsumerData_Religion_Code', None)
        )
    
    def _parse_geographic_info(self, data: Dict[str, Any]) -> GeographicInfo:
        """Parse geographic information from raw data."""
        return GeographicInfo(
            census_tract=data.get('Residence_Addresses_CensusTract', None),
            block_group=data.get('Residence_Addresses_CensusBlockGroup', None),
            urban_rural=data.get('ConsumerData_Urban_Rural', None),
            population_density=data.get('ConsumerData_Population_Density', None),
            time_zone=data.get('ConsumerData_Time_Zone', None),
            rus_code=data.get('ConsumerData_RUS_Code', None),
            length_of_residence_code=data.get('ConsumerData_Length_Of_Residence_Code', None),
            county=data.get('County', None),
            precinct=data.get('Precinct', None),
            fips=data.get('Voters_FIPS', None),
            congressional_district=data.get('US_Congressional_District', None),
            state_senate_district=data.get('State_Senate_District', None),
            state_house_district=data.get('State_House_District', None),
            state_legislative_district=data.get('State_Legislative_District', None),
            city=data.get('City', None),
            borough=data.get('Borough', None),
            borough_ward=data.get('Borough_Ward', None),
            township=data.get('Township', None),
            township_ward=data.get('Township_Ward', None),
            village=data.get('Village', None),
            village_ward=data.get('Village_Ward', None),
            hamlet_community_area=data.get('Hamlet_Community_Area', None),
            proposed_city=data.get('Proposed_City', None),
            proposed_city_commissioner_district=data.get('Proposed_City_Commissioner_District', None),
            county_commissioner_district=data.get('County_Commissioner_District', None),
            county_supervisorial_district=data.get('County_Supervisorial_District', None),
            city_council_commissioner_district=data.get('City_Council_Commissioner_District', None),
            city_mayoral_district=data.get('City_Mayoral_District', None),
            city_ward=data.get('City_Ward', None),
            town_council=data.get('Town_Council', None),
            town_district=data.get('Town_District', None),
            town_ward=data.get('Town_Ward', None),
            proposed_2024_congressional_district=data.get('2024_Proposed_Congressional_District', None),
            proposed_2024_state_senate_district=data.get('2024_Proposed_State_Senate_District', None),
            proposed_2024_state_house_district=data.get('2024_Proposed_State_House_District', None),
            proposed_2024_state_legislative_district=data.get('2024_Proposed_State_Legislative_District', None),
            district_2001_us_congressional=data.get('2001_US_Congressional_District', None),
            district_2001_state_house=data.get('2001_State_House_District', None),
            district_2001_state_legislative=data.get('2001_State_Legislative_District', None),
            district_2001_state_senate=data.get('2001_State_Senate_District', None),
            district_2010_us_congressional=data.get('2010_US_Congressional_District', None),
            district_2010_state_house=data.get('2010_State_House_District', None),
            district_2010_state_legislative=data.get('2010_State_Legislative_District', None),
            district_2010_state_senate=data.get('2010_State_Senate_District', None),
            address_change_changed_cd=data.get('AddressDistricts_Change_Changed_CD', None),
            address_change_changed_county=data.get('AddressDistricts_Change_Changed_County', None),
            address_change_changed_hd=data.get('AddressDistricts_Change_Changed_HD', None),
            address_change_changed_ld=data.get('AddressDistricts_Change_Changed_LD', None),
            address_change_changed_sd=data.get('AddressDistricts_Change_Changed_SD', None)
        )
    
    def _parse_election_history(self, data: Dict[str, Any]) -> ElectionHistory:
        """Parse election history from raw data."""
        return ElectionHistory(
            # Future elections
            any_election_2027=data.get('AnyElection_2027', None),
            general_2026=data.get('General_2026', None),
            primary_2026=data.get('Primary_2026', None),
            other_election_2026=data.get('OtherElection_2026', None),
            any_election_2025=data.get('AnyElection_2025', None),
            
            # Recent elections
            general_2024=data.get('General_2024', None),
            primary_2024=data.get('Primary_2024', None),
            presidential_primary_2024=data.get('PresidentialPrimary_2024', None),
            other_election_2024=data.get('OtherElection_2024', None),
            any_election_2023=data.get('AnyElection_2023', None),
            general_2022=data.get('General_2022', None),
            primary_2022=data.get('Primary_2022', None),
            other_election_2022=data.get('OtherElection_2022', None),
            any_election_2021=data.get('AnyElection_2021', None),
            general_2020=data.get('General_2020', None),
            primary_2020=data.get('Primary_2020', None),
            presidential_primary_2020=data.get('PresidentialPrimary_2020', None),
            other_election_2020=data.get('OtherElection_2020', None),
            any_election_2019=data.get('AnyElection_2019', None),
            
            # Historical elections
            general_2018=data.get('General_2018', None),
            primary_2018=data.get('Primary_2018', None),
            other_election_2018=data.get('OtherElection_2018', None),
            any_election_2017=data.get('AnyElection_2017', None),
            general_2016=data.get('General_2016', None),
            primary_2016=data.get('Primary_2016', None),
            presidential_primary_2016=data.get('PresidentialPrimary_2016', None),
            other_election_2016=data.get('OtherElection_2016', None),
            any_election_2015=data.get('AnyElection_2015', None),
            general_2014=data.get('General_2014', None),
            primary_2014=data.get('Primary_2014', None),
            other_election_2014=data.get('OtherElection_2014', None),
            any_election_2013=data.get('AnyElection_2013', None),
            general_2012=data.get('General_2012', None),
            primary_2012=data.get('Primary_2012', None),
            presidential_primary_2012=data.get('PresidentialPrimary_2012', None),
            other_election_2012=data.get('OtherElection_2012', None),
            any_election_2011=data.get('AnyElection_2011', None),
            general_2010=data.get('General_2010', None),
            primary_2010=data.get('Primary_2010', None),
            other_election_2010=data.get('OtherElection_2010', None),
            any_election_2009=data.get('AnyElection_2009', None),
            general_2008=data.get('General_2008', None),
            primary_2008=data.get('Primary_2008', None),
            presidential_primary_2008=data.get('PresidentialPrimary_2008', None),
            other_election_2008=data.get('OtherElection_2008', None),
            any_election_2007=data.get('AnyElection_2007', None),
            general_2006=data.get('General_2006', None),
            primary_2006=data.get('Primary_2006', None),
            other_election_2006=data.get('OtherElection_2006', None),
            any_election_2005=data.get('AnyElection_2005', None),
            general_2004=data.get('General_2004', None),
            primary_2004=data.get('Primary_2004', None),
            presidential_primary_2004=data.get('PresidentialPrimary_2004', None),
            other_election_2004=data.get('OtherElection_2004', None),
            any_election_2003=data.get('AnyElection_2003', None),
            general_2002=data.get('General_2002', None),
            primary_2002=data.get('Primary_2002', None),
            other_election_2002=data.get('OtherElection_2002', None),
            any_election_2001=data.get('AnyElection_2001', None),
            general_2000=data.get('General_2000', None),
            primary_2000=data.get('Primary_2000', None),
            presidential_primary_2000=data.get('PresidentialPrimary_2000', None),
            other_election_2000=data.get('OtherElection_2000', None),
            
            # Primary ballot request history (PRI_BLT)
            pri_blt_2022=data.get('PRI_BLT_2022', None),
            pri_blt_2021=data.get('PRI_BLT_2021', None),
            pri_blt_2020=data.get('PRI_BLT_2020', None),
            pri_blt_2019=data.get('PRI_BLT_2019', None),
            pri_blt_2018=data.get('PRI_BLT_2018', None),
            pri_blt_2017=data.get('PRI_BLT_2017', None),
            pri_blt_2016=data.get('PRI_BLT_2016', None),
            pri_blt_2015=data.get('PRI_BLT_2015', None),
            pri_blt_2014=data.get('PRI_BLT_2014', None),
            pri_blt_2013=data.get('PRI_BLT_2013', None),
            pri_blt_2012=data.get('PRI_BLT_2012', None),
            pri_blt_2011=data.get('PRI_BLT_2011', None),
            pri_blt_2010=data.get('PRI_BLT_2010', None),
            pri_blt_2009=data.get('PRI_BLT_2009', None),
            pri_blt_2008=data.get('PRI_BLT_2008', None),
            pri_blt_2007=data.get('PRI_BLT_2007', None),
            pri_blt_2006=data.get('PRI_BLT_2006', None),
            pri_blt_2005=data.get('PRI_BLT_2005', None),
            pri_blt_2004=data.get('PRI_BLT_2004', None),
            pri_blt_2003=data.get('PRI_BLT_2003', None),
            pri_blt_2002=data.get('PRI_BLT_2002', None),
            pri_blt_2001=data.get('PRI_BLT_2001', None),
            pri_blt_2000=data.get('PRI_BLT_2000', None)
        )
    
    def _parse_interest_flags(self, data: Dict[str, Any]) -> List[str]:
        """Parse individual interest flags from raw data."""
        interests = []
        
        # Check for various interest flags in the data
        interest_fields = [
            'ConsumerData_Arts_And_Antiques', 'ConsumerData_Arts_Int', 'ConsumerData_Collectibles_Antiques',
            'ConsumerData_Collectibles_Arts', 'ConsumerData_Cultural_Arts_Living', 'ConsumerData_Arts_Art',
            'ConsumerData_Theater_Performing_Arts', 'ConsumerData_Collect_Special_Foods_Buyer',
            'ConsumerData_Food_Wines', 'ConsumerData_Foods_Natural', 'ConsumerData_Movie_Collector',
            'ConsumerData_Music_Collector', 'ConsumerData_Music_Avid_Listener', 'ConsumerData_Music_Home_Stereo',
            'ConsumerData_Musical_Instruments', 'ConsumerData_Photography_Video_Equip', 'ConsumerData_Photography_Int',
            'ConsumerData_Collectibles_Stamps', 'ConsumerData_Book_Buyer', 'ConsumerData_Book_Reader',
            'ConsumerData_Reading_Audio_Books', 'ConsumerData_Books_Music_Audio', 'ConsumerData_Books_Magazines',
            'ConsumerData_Books_Music_Books', 'ConsumerData_Reading_General', 'ConsumerData_Reading_Mags',
            'ConsumerData_Reading_Sci_Fi', 'ConsumerData_Religious_Mags', 'ConsumerData_Current_Affairs_Politics',
            'ConsumerData_Education_Online', 'ConsumerData_History_Military', 'ConsumerData_News_Financial',
            'ConsumerData_Childrens_Babycare', 'ConsumerData_Apparel_Childrens', 'ConsumerData_Childrens_Back_To_School',
            'ConsumerData_Childrens_Learning_Toys', 'ConsumerData_Childrens_General', 'ConsumerData_Grandchildren_Int',
            'ConsumerData_Apparel_Infant_Toddlers', 'ConsumerData_Parenting_Int', 'ConsumerData_Apparel_Mens',
            'ConsumerData_Apparel_Mens_Big_Tall', 'ConsumerData_Apparel_Womens', 'ConsumerData_Apparel_Petite',
            'ConsumerData_Apparel_Womens_Plus_Size', 'ConsumerData_Apparel_Young_Mens', 'ConsumerData_Apparel_Young_Womens',
            'ConsumerData_Female_Merch_Buyer', 'ConsumerData_Male_Merch_Buyer', 'ConsumerData_Invest_Active',
            'ConsumerData_Invest_Stock_Securities', 'ConsumerData_Investing_Finance_Grouping', 'ConsumerData_Investments_Foreign',
            'ConsumerData_Investments', 'ConsumerData_Investments_Personal', 'ConsumerData_Investments_Realestate',
            'ConsumerData_Sweepstakes_Int', 'ConsumerDataLL_Gun_Owner_Concealed_Permit', 'ConsumerDataLL_Gun_Owner',
            'ConsumerData_Cosmetics_Beauty', 'ConsumerData_Jewelry_Buyer', 'ConsumerData_Dieting_Weightloss',
            'ConsumerData_Exercise_Aerobic', 'ConsumerData_Exercise_Running_Jogging', 'ConsumerData_Exercise_Walking',
            'ConsumerData_Exercise_Health_Grouping', 'ConsumerData_Exercise_Enthusiast', 'ConsumerData_Health_And_Beauty',
            'ConsumerData_Health_Medical', 'ConsumerData_Smoking', 'ConsumerData_Collectibles_General',
            'ConsumerData_Collectibles_Coins', 'ConsumerData_Lifestyle_Passion_Collectibles', 'ConsumerData_Military_Memorabilia_Weapons',
            'ConsumerData_Collectibles_Sports_Memorabilia', 'ConsumerData_Collector_Avid', 'ConsumerData_Craft_Int',
            'ConsumerData_Crafts_Hobbies_Buyer', 'ConsumerData_Sewing_Knitting_Needlework', 'ConsumerData_Woodwork',
            'ConsumerData_Games_Board_Puzzles', 'ConsumerData_Games_PC_Games', 'ConsumerData_Games_Video',
            'ConsumerData_Gaming_Int', 'ConsumerData_Gaming_Casino', 'ConsumerData_Automotive_Buff',
            'ConsumerData_Auto_Work', 'ConsumerData_Autoparts_Accessories', 'ConsumerData_Cooking_General',
            'ConsumerData_Cooking_Enthusiast', 'ConsumerData_Gardening_Farming_Buyer', 'ConsumerData_Home_And_Garden',
            'ConsumerData_Gardening', 'ConsumerData_House_Plants', 'ConsumerData_High_End_Appliances',
            'ConsumerData_Home_Decor_Enthusiast', 'ConsumerData_Home_Furnishings_Decor', 'ConsumerData_Home_Improvement',
            'ConsumerData_Mail_Order_Buyer', 'ConsumerData_Mail_Responder', 'ConsumerData_Online_Buyer',
            'ConsumerData_Pets_Cats', 'ConsumerData_Pets_Dogs', 'ConsumerData_Pets_Multi',
            'ConsumerData_Equestrian_Int', 'ConsumerData_Outdoor_Enthusiast', 'ConsumerData_Outdoor_Grouping',
            'ConsumerData_Outdoor_Sports_Lover', 'ConsumerData_Camping_Hiking', 'ConsumerData_Hunter',
            'ConsumerData_Hunting_Shooting', 'ConsumerData_Boating_Sailing', 'ConsumerData_Fisher',
            'ConsumerData_Scuba_Diving', 'ConsumerData_Sports_Baseball', 'ConsumerData_Sports_Basketball',
            'ConsumerData_Sports_Football', 'ConsumerData_Sports_Leisure', 'ConsumerData_Sports_Grouping',
            'ConsumerData_Sports_TV_Sports', 'ConsumerData_Golf_Enthusiast', 'ConsumerData_Sports_Hockey',
            'ConsumerData_Sports_Auto_Motorcycle_Racing', 'ConsumerData_Active_Motorcycle', 'ConsumerData_Active_Nascar',
            'ConsumerData_Active_Snow_Skiing', 'ConsumerData_Sports_Soccer', 'ConsumerData_Active_Tennis',
            'ConsumerData_Aviation_Int', 'ConsumerData_Electronics_Computers', 'ConsumerData_Computer_Home_Office',
            'ConsumerData_Consumer_Electronics', 'ConsumerData_Electronics_Movies_Int', 'ConsumerData_Science_Space',
            'ConsumerData_Travel_Cruises', 'ConsumerData_Travel_Domestic', 'ConsumerData_Travel_Int',
            'ConsumerData_Travel_Intl', 'ConsumerData_Luggage_Buyer', 'ConsumerData_Travel_Grouping',
            'ConsumerData_Auto_Buy_Interest'
        ]
        
        for field in interest_fields:
            if field in data and data[field] == 'Y':
                # Convert field name to readable interest name
                interest_name = field.replace('ConsumerData_', '').replace('_', ' ').title()
                interests.append(interest_name)
        
        return interests if interests else []
    
    def _parse_lifestyle_categories(self, data: Dict[str, Any]) -> List[str]:
        """Parse lifestyle categories from raw data."""
        categories = []
        
        # Check for lifestyle-related flags
        lifestyle_fields = [
            'ConsumerData_Do_It_Yourselfers_Typical_Choice', 'ConsumerData_Do_It_Yourself_Lifestyle_Committed_Choice',
            'ConsumerData_Home_Living', 'ConsumerData_Opportunity_Seekers', 'ConsumerData_Professional_Living',
            'ConsumerData_Self_Improvement', 'ConsumerData_Highbrow_Living', 'ConsumerData_High_Tech_Leader',
            'ConsumerData_Common_Living', 'ConsumerData_Religious_Inspiration', 'ConsumerData_Sporty_Living',
            'ConsumerData_Upscale_Living', 'ConsumerData_Value_Hunter', 'ConsumerData_Working_Woman',
            'ConsumerData_Christian_Families', 'ConsumerData_Membership_Club', 'ConsumerData_Broader_Living'
        ]
        
        for field in lifestyle_fields:
            if field in data and data[field] == 'Y':
                category_name = field.replace('ConsumerData_', '').replace('_', ' ').title()
                categories.append(category_name)
        
        return categories if categories else []
    
    def _parse_technology_usage(self, data: Dict[str, Any]) -> List[str]:
        """Parse technology usage from raw data."""
        tech_usage = []
        
        # Check for technology-related flags
        tech_fields = [
            'ConsumerData_Computer_Home_Office', 'ConsumerData_Consumer_Electronics', 'ConsumerData_Electronics_Computers',
            'ConsumerData_Electronics_Movies_Int', 'ConsumerData_Science_Space', 'ConsumerData_Online_Buyer',
            'ConsumerData_Mail_Order_Buyer', 'ConsumerData_Mail_Responder'
        ]
        
        for field in tech_fields:
            if field in data and data[field] == 'Y':
                tech_name = field.replace('ConsumerData_', '').replace('_', ' ').title()
                tech_usage.append(tech_name)
        
        return tech_usage if tech_usage else []
    
    def _parse_donor_categories(self, data: Dict[str, Any]) -> List[str]:
        """Parse donor category flags into a list of readable strings."""
        donor_categories = []
        
        donor_fields = [
            'ConsumerData_Donor_Animal_Welfare', 'ConsumerData_Donor_Arts_Cultural',
            'ConsumerData_Donor_By_Mail', 'ConsumerData_Donor_Charitable_Causes',
            'ConsumerData_Donor_Childrens_Causes', 'ConsumerData_Donor_Community_Charity',
            'ConsumerData_Donor_Environmental', 'ConsumerData_Donor_Environmental_Issues',
            'ConsumerData_Donor_Health_Institution', 'ConsumerData_Donor_International_Aid',
            'ConsumerData_Donor_Political_Conservative', 'ConsumerData_Donor_Political_Liberal',
            'ConsumerData_Political_Donor_State_Level', 'ConsumerData_Religious_Contributor',
            'ConsumerData_Donor_Veterans'
        ]
        
        for field in donor_fields:
            if field in data and data[field] == 'Y':
                donor_name = field.replace('ConsumerData_Donor_', '').replace('ConsumerData_', '').replace('_', ' ').title()
                donor_categories.append(donor_name)
        
        return donor_categories if donor_categories else []
    
    def _parse_shopping_preferences(self, data: Dict[str, Any]) -> List[str]:
        """Parse shopping preference flags into a list of readable strings."""
        shopping_prefs = []
        
        shopping_fields = [
            'ConsumerData_Mail_Order_Buyer', 'ConsumerData_Mail_Responder',
            'ConsumerData_Online_Buyer', 'ConsumerData_Female_Merch_Buyer',
            'ConsumerData_Male_Merch_Buyer'
        ]
        
        for field in shopping_fields:
            if field in data and data[field] == 'Y':
                pref_name = field.replace('ConsumerData_', '').replace('_', ' ').title()
                shopping_prefs.append(pref_name)
        
        return shopping_prefs if shopping_prefs else []
    
    def _parse_media_preferences(self, data: Dict[str, Any]) -> List[str]:
        """Parse media preference flags into a list of readable strings."""
        media_prefs = []
        
        media_fields = [
            'ConsumerData_Reading_General', 'ConsumerData_Reading_Mags',
            'ConsumerData_Reading_Sci_Fi', 'ConsumerData_Religious_Mags',
            'ConsumerData_Current_Affairs_Politics', 'ConsumerData_News_Financial',
            'ConsumerData_Sports_TV_Sports', 'ConsumerData_Movie_Collector',
            'ConsumerData_Music_Collector', 'ConsumerData_Music_Avid_Listener'
        ]
        
        for field in media_fields:
            if field in data and data[field] == 'Y':
                media_name = field.replace('ConsumerData_', '').replace('_', ' ').title()
                media_prefs.append(media_name)
        
        return media_prefs if media_prefs else []
    
    def _parse_travel_preferences(self, data: Dict[str, Any]) -> List[str]:
        """Parse travel preference flags into a list of readable strings."""
        travel_prefs = []
        
        travel_fields = [
            'ConsumerData_Travel_Cruises', 'ConsumerData_Travel_Domestic',
            'ConsumerData_Travel_Int', 'ConsumerData_Travel_Intl',
            'ConsumerData_Luggage_Buyer', 'ConsumerData_Travel_Grouping'
        ]
        
        for field in travel_fields:
            if field in data and data[field] == 'Y':
                travel_name = field.replace('ConsumerData_Travel_', '').replace('ConsumerData_', '').replace('_', ' ').title()
                travel_prefs.append(travel_name)
        
        return travel_prefs if travel_prefs else []
    
    def _parse_health_interests(self, data: Dict[str, Any]) -> List[str]:
        """Parse health interest flags into a list of readable strings."""
        health_interests = []
        
        health_fields = [
            'ConsumerData_Exercise_Aerobic', 'ConsumerData_Exercise_Running_Jogging',
            'ConsumerData_Exercise_Walking', 'ConsumerData_Exercise_Health_Grouping',
            'ConsumerData_Exercise_Enthusiast', 'ConsumerData_Health_And_Beauty',
            'ConsumerData_Health_Medical', 'ConsumerData_Dieting_Weightloss',
            'ConsumerData_Smoking'
        ]
        
        for field in health_fields:
            if field in data and data[field] == 'Y':
                health_name = field.replace('ConsumerData_', '').replace('_', ' ').title()
                health_interests.append(health_name)
        
        return health_interests if health_interests else []
    
    def _parse_financial_interests(self, data: Dict[str, Any]) -> List[str]:
        """Parse financial interest flags into a list of readable strings."""
        financial_interests = []
        
        financial_fields = [
            'ConsumerData_Invest_Active', 'ConsumerData_Invest_Stock_Securities',
            'ConsumerData_Investing_Finance_Grouping', 'ConsumerData_Investments_Foreign',
            'ConsumerData_Investments', 'ConsumerData_Investments_Personal',
            'ConsumerData_Investments_Realestate', 'ConsumerData_News_Financial'
        ]
        
        for field in financial_fields:
            if field in data and data[field] == 'Y':
                financial_name = field.replace('ConsumerData_', '').replace('_', ' ').title()
                financial_interests.append(financial_name)
        
        return financial_interests if financial_interests else []
    
    def _parse_fec_donor_info(self, data: Dict[str, Any]) -> FECDonorInfo:
        """Parse FEC donor information from raw data."""
        total_donations_range = data.get('FECDonors_TotalDonationsAmt_Range', None)
        return FECDonorInfo(
            avg_donation=data.get('FECDonors_AvgDonation', None),
            avg_donation_range=data.get('FECDonors_AvgDonation_Range', None),
            last_donation_date=data.get('FECDonors_LastDonationDate', None),
            number_of_donations=self._safe_int(data.get('FECDonors_NumberOfDonations', None)),
            primary_recipient=data.get('FECDonors_PrimaryRecipientOfContributions', None),
            total_donations_amount=data.get('FECDonors_TotalDonationsAmount', None),
            total_donations_amount_range=total_donations_range,
            total_donations_range=total_donations_range  # Alias
        )
    
    def _parse_market_area_info(self, data: Dict[str, Any]) -> MarketAreaInfo:
        """Parse market area information from raw data."""
        return MarketAreaInfo(
            designated_market_area_dma=data.get('Designated_Market_Area_DMA', None),
            consumerdata_csa=data.get('ConsumerData_CSA', None),
            consumerdata_cbsa=data.get('ConsumerData_CBSA', None),
            consumerdata_msa=data.get('ConsumerData_MSA', None),
            area_pcnt_hh_with_children=data.get('ConsumerData_AreaPcntHHWithChildren', None),
            area_median_housing_value=data.get('ConsumerData_AreaMedianHousingValue', None),
            area_median_hh_income=data.get('ConsumerData_EstimatedAreaMedianHHIncome', None),
            area_median_education_years=data.get('ConsumerData_AreaMedianEducationYears', None)
        )
    
    def _parse_phone_info(self, data: Dict[str, Any]) -> PhoneInfo:
        """Parse phone information from raw data."""
        return PhoneInfo(
            phone_number_available=data.get('Phone_Number_Available', 'N') == 'Y',
            landline_phone_available=data.get('Landline_Phone_Number_Available', 'N') == 'Y',
            landline_area_code=data.get('VoterTelephones_LandlineAreaCode', None),
            landline_unformatted=data.get('VoterTelephones_LandlineUnformatted', None),
            landline_confidence_code=data.get('VoterTelephones_LandlineConfidenceCode', None),
            landline_7digit=data.get('VoterTelephones_Landline7Digit', None),
            landline_formatted=data.get('VoterTelephones_LandlineFormatted', None),
            cell_phone_available=data.get('Cell_Phone_Number_Available', 'N') == 'Y',
            cell_phone_unformatted=data.get('VoterTelephones_CellPhoneUnformatted', None),
            cell_confidence_code=data.get('VoterTelephones_CellConfidenceCode', None),
            cell_phone_formatted=data.get('VoterTelephones_CellPhoneFormatted', None),
            cell_phone_only=data.get('VoterTelephones_CellPhoneOnly', 'N') == 'Y',
            do_not_call=data.get('ConsumerData_Do_Not_Call', 'N') == 'Y'
        )
    
    def _parse_judicial_district_info(self, data: Dict[str, Any]) -> JudicialDistrictInfo:
        """Parse judicial district information from raw data."""
        return JudicialDistrictInfo(
            judicial_appellate_district=data.get('Judicial_Appellate_District', None),
            judicial_chancery_court=data.get('Judicial_Chancery_Court', None),
            judicial_circuit_court_district=data.get('Judicial_Circuit_Court_District', None),
            judicial_county_board_of_review_district=data.get('Judicial_County_Board_of_Review_District', None),
            judicial_county_court_district=data.get('Judicial_County_Court_District', None),
            judicial_district=data.get('Judicial_District', None),
            judicial_district_court_district=data.get('Judicial_District_Court_District', None),
            judicial_family_court_district=data.get('Judicial_Family_Court_District', None),
            judicial_jury_district=data.get('Judicial_Jury_District', None),
            judicial_justice_of_the_peace=data.get('Judicial_Justice_of_the_Peace', None),
            judicial_juvenile_court_district=data.get('Judicial_Juvenile_Court_District', None),
            judicial_magistrate_division=data.get('Judicial_Magistrate_Division', None),
            judicial_municipal_court_district=data.get('Judicial_Municipal_Court_District', None),
            judicial_sub_circuit_district=data.get('Judicial_Sub_Circuit_District', None),
            judicial_superior_court_district=data.get('Judicial_Superior_Court_District', None),
            judicial_supreme_court_district=data.get('Judicial_Supreme_Court_District', None)
        )
    
    def _parse_school_district_info(self, data: Dict[str, Any]) -> SchoolDistrictInfo:
        """Parse school district information from raw data."""
        return SchoolDistrictInfo(
            city_school_district=data.get('City_School_District', None),
            college_board_district=data.get('College_Board_District', None),
            community_college=data.get('Community_College', None),
            community_college_at_large=data.get('Community_College_At_Large', None),
            community_college_commissioner_district=data.get('Community_College_Commissioner_District', None),
            community_college_subdistrict=data.get('Community_College_SubDistrict', None),
            county_board_of_education_district=data.get('County_Board_of_Education_District', None),
            county_board_of_education_subdistrict=data.get('County_Board_of_Education_SubDistrict', None),
            county_community_college_district=data.get('County_Community_College_District', None),
            county_superintendent_of_schools_district=data.get('County_Superintendent_of_Schools_District', None),
            county_unified_school_district=data.get('County_Unified_School_District', None),
            education_commission_district=data.get('Education_Commission_District', None),
            educational_service_district=data.get('Educational_Service_District', None),
            educational_service_subdistrict=data.get('Educational_Service_Subdistrict', None),
            elementary_school_district=data.get('Elementary_School_District', None),
            elementary_school_subdistrict=data.get('Elementary_School_SubDistrict', None),
            exempted_village_school_district=data.get('Exempted_Village_School_District', None),
            high_school_district=data.get('High_School_District', None),
            high_school_subdistrict=data.get('High_School_SubDistrict', None),
            proposed_community_college=data.get('Proposed_Community_College', None),
            proposed_elementary_school_district=data.get('Proposed_Elementary_School_District', None),
            proposed_unified_school_district=data.get('Proposed_Unified_School_District', None),
            regional_office_of_education_district=data.get('Regional_Office_of_Education_District', None),
            school_board_district=data.get('School_Board_District', None),
            school_district=data.get('School_District', None),
            school_district_vocational=data.get('School_District_Vocational', None),
            school_facilities_improvement_district=data.get('School_Facilities_Improvement_District', None),
            school_subdistrict=data.get('School_Subdistrict', None),
            superintendent_of_schools_district=data.get('Superintendent_of_Schools_District', None),
            unified_school_district=data.get('Unified_School_District', None),
            unified_school_subdistrict=data.get('Unified_School_SubDistrict', None)
        )
    
    def _parse_special_district_info(self, data: Dict[str, Any]) -> SpecialDistrictInfo:
        """Parse special district information from raw data."""
        return SpecialDistrictInfo(
            district_4h_livestock=data.get('4H_Livestock_District', None),
            district_airport=data.get('Airport_District', None),
            district_annexation=data.get('Annexation_District', None),
            district_aquatic_center=data.get('Aquatic_Center_District', None),
            district_aquatic=data.get('Aquatic_District', None),
            district_assessment=data.get('Assessment_District', None),
            district_bay_area_rapid_transit=data.get('Bay_Area_Rapid_Transit', None),
            district_board_of_education=data.get('Board_of_Education_District', None),
            district_board_of_education_sub=data.get('Board_of_Education_SubDistrict', None),
            district_bonds=data.get('Bonds_District', None),
            district_career_center=data.get('Career_Center', None),
            district_cemetery=data.get('Cemetery_District', None),
            district_central_committee=data.get('Central_Committee_District', None),
            district_chemical_control=data.get('Chemical_Control_District', None),
            district_coast_water=data.get('Coast_Water_District', None),
            district_committee_super=data.get('Committee_Super_District', None),
            district_communications=data.get('Communications_District', None),
            district_community_council=data.get('Community_Council_District', None),
            district_community_council_sub=data.get('Community_Council_SubDistrict', None),
            district_community_facilities=data.get('Community_Facilities_District', None),
            district_community_facilities_sub=data.get('Community_Facilities_SubDistrict', None),
            district_community_hospital=data.get('Community_Hospital_District', None),
            district_community_planning_area=data.get('Community_Planning_Area', None),
            district_community_service=data.get('Community_Service_District', None),
            district_community_service_sub=data.get('Community_Service_SubDistrict', None),
            district_congressional_township=data.get('Congressional_Township', None),
            district_conservation=data.get('Conservation_District', None),
            district_conservation_sub=data.get('Conservation_SubDistrict', None),
            district_consolidated_water=data.get('Consolidated_Water_District', None),
            district_control_zone=data.get('Control_Zone_District', None),
            district_corrections=data.get('Corrections_District', None),
            district_county_fire=data.get('County_Fire_District', None),
            district_county_hospital=data.get('County_Hospital_District', None),
            district_county_legislative=data.get('County_Legislative_District', None),
            district_county_library=data.get('County_Library_District', None),
            district_county_memorial=data.get('County_Memorial_District', None),
            district_county_paramedic=data.get('County_Paramedic_District', None),
            district_county_service_area=data.get('County_Service_Area', None),
            district_county_service_area_sub=data.get('County_Service_Area_SubDistrict', None),
            district_county_sewer=data.get('County_Sewer_District', None),
            district_county_water=data.get('County_Water_District', None),
            district_county_water_landowner=data.get('County_Water_Landowner_District', None),
            district_county_water_sub=data.get('County_Water_SubDistrict', None),
            district_democratic_convention_member=data.get('Democratic_Convention_Member', None),
            district_democratic_zone=data.get('Democratic_Zone', None),
            district_attorney=data.get('District_Attorney', None),
            district_drainage=data.get('Drainage_District', None),
            district_election_commissioner=data.get('Election_Commissioner_District', None),
            district_emergency_communication_911=data.get('Emergency_Communication_911_District', None),
            district_emergency_communication_911_sub=data.get('Emergency_Communication_911_SubDistrict', None),
            district_enterprise_zone=data.get('Enterprise_Zone_District', None),
            district_ext=data.get('EXT_District', None),
            district_facilities_improvement=data.get('Facilities_Improvement_District', None),
            district_fire=data.get('Fire_District', None),
            district_fire_maintenance=data.get('Fire_Maintenance_District', None),
            district_fire_protection=data.get('Fire_Protection_District', None),
            district_fire_protection_sub=data.get('Fire_Protection_SubDistrict', None),
            district_fire_protection_tax_measure=data.get('Fire_Protection_Tax_Measure_District', None),
            district_fire_service_area=data.get('Fire_Service_Area_District', None),
            district_fire_sub=data.get('Fire_SubDistrict', None),
            district_flood_control_zone=data.get('Flood_Control_Zone', None),
            district_forest_preserve=data.get('Forest_Preserve', None),
            district_garbage=data.get('Garbage_District', None),
            district_geological_hazard_abatement=data.get('Geological_Hazard_Abatement_District', None),
            district_health=data.get('Health_District', None),
            district_hospital=data.get('Hospital_District', None),
            district_hospital_sub=data.get('Hospital_SubDistrict', None),
            district_improvement_landowner=data.get('Improvement_Landowner_District', None),
            district_independent_fire=data.get('Independent_Fire_District', None),
            district_irrigation=data.get('Irrigation_District', None),
            district_irrigation_sub=data.get('Irrigation_SubDistrict', None),
            district_island=data.get('Island', None),
            district_land_commission=data.get('Land_Commission', None),
            district_landscaping_and_lighting_assessment=data.get('Landscaping_and_Lighting_Assessment_District', None),
            district_law_enforcement=data.get('Law_Enforcement_District', None),
            district_learning_community_coordinating_council=data.get('Learning_Community_Coordinating_Council_District', None),
            district_levee=data.get('Levee_District', None),
            district_levee_reconstruction_assessment=data.get('Levee_Reconstruction_Assesment_District', None),
            district_library=data.get('Library_District', None),
            district_library_services=data.get('Library_Services_District', None),
            district_library_sub=data.get('Library_SubDistrict', None),
            district_lighting=data.get('Lighting_District', None),
            district_local_hospital=data.get('Local_Hospital_District', None),
            district_local_park=data.get('Local_Park_District', None),
            district_maintenance=data.get('Maintenance_District', None),
            district_master_plan=data.get('Master_Plan_District', None),
            district_memorial=data.get('Memorial_District', None),
            district_metro_service=data.get('Metro_Service_District', None),
            district_metro_service_sub=data.get('Metro_Service_Subdistrict', None),
            district_metro_transit=data.get('Metro_Transit_District', None),
            district_metropolitan_water=data.get('Metropolitan_Water_District', None),
            district_middle_school=data.get('Middle_School_District', None),
            district_mosquito_abatement=data.get('Mosquito_Abatement_District', None),
            district_mountain_water=data.get('Mountain_Water_District', None),
            district_multi_township_assessor=data.get('Multi_township_Assessor', None),
            district_municipal_advisory_council=data.get('Municipal_Advisory_Council_District', None),
            district_municipal_utility=data.get('Municipal_Utility_District', None),
            district_municipal_utility_sub=data.get('Municipal_Utility_SubDistrict', None),
            district_municipal_water=data.get('Municipal_Water_District', None),
            district_municipal_water_sub=data.get('Municipal_Water_SubDistrict', None),
            district_museum=data.get('Museum_District', None),
            district_northeast_soil_and_water=data.get('Northeast_Soil_and_Water_District', None),
            district_open_space=data.get('Open_Space_District', None),
            district_open_space_sub=data.get('Open_Space_SubDistrict', None),
            district_other=data.get('Other', None),
            district_paramedic=data.get('Paramedic_District', None),
            district_park_commissioner=data.get('Park_Commissioner_District', None),
            district_park=data.get('Park_District', None),
            district_park_sub=data.get('Park_SubDistrict', None),
            district_planning_area=data.get('Planning_Area_District', None),
            district_police=data.get('Police_District', None),
            district_port=data.get('Port_District', None),
            district_port_sub=data.get('Port_SubDistrict', None),
            district_power=data.get('Power_District', None),
            district_proposed=data.get('Proposed_District', None),
            district_proposed_fire=data.get('Proposed_Fire_District', None),
            district_public_airport=data.get('Public_Airport_District', None),
            district_public_regulation_commission=data.get('Public_Regulation_Commission', None),
            district_public_service_commission=data.get('Public_Service_Commission_District', None),
            district_public_utility=data.get('Public_Utility_District', None),
            district_public_utility_sub=data.get('Public_Utility_SubDistrict', None),
            district_rapid_transit=data.get('Rapid_Transit_District', None),
            district_rapid_transit_sub=data.get('Rapid_Transit_SubDistrict', None),
            district_reclamation=data.get('Reclamation_District', None),
            district_recreation=data.get('Recreation_District', None),
            district_recreational_sub=data.get('Recreational_SubDistrict', None),
            district_republican_area=data.get('Republican_Area', None),
            district_republican_convention_member=data.get('Republican_Convention_Member', None),
            district_resort_improvement=data.get('Resort_Improvement_District', None),
            district_resource_conservation=data.get('Resource_Conservation_District', None),
            district_river_water=data.get('River_Water_District', None),
            district_road_maintenance=data.get('Road_Maintenance_District', None),
            district_rural_service=data.get('Rural_Service_District', None),
            district_sanitary=data.get('Sanitary_District', None),
            district_sanitary_sub=data.get('Sanitary_SubDistrict', None),
            district_service_area=data.get('Service_Area_District', None),
            district_sewer=data.get('Sewer_District', None),
            district_sewer_maintenance=data.get('Sewer_Maintenance_District', None),
            district_sewer_sub=data.get('Sewer_SubDistrict', None),
            district_snow_removal=data.get('Snow_Removal_District', None),
            district_soil_and_water=data.get('Soil_and_Water_District', None),
            district_soil_and_water_at_large=data.get('Soil_and_Water_District_At_Large', None),
            district_special_reporting=data.get('Special_Reporting_District', None),
            district_special_tax=data.get('Special_Tax_District', None),
            district_state_board_of_equalization=data.get('State_Board_of_Equalization', None),
            district_storm_water=data.get('Storm_Water_District', None),
            district_street_lighting=data.get('Street_Lighting_District', None),
            district_transit=data.get('Transit_District', None),
            district_transit_sub=data.get('Transit_SubDistrict', None),
            district_tricity_service=data.get('TriCity_Service_District', None),
            district_tv_translator=data.get('TV_Translator_District', None),
            district_unincorporated=data.get('Unincorporated_District', None),
            district_unincorporated_park=data.get('Unincorporated_Park_District', None),
            district_unprotected_fire=data.get('Unprotected_Fire_District', None),
            district_ute_creek_soil=data.get('Ute_Creek_Soil_District', None),
            district_vector_control=data.get('Vector_Control_District', None),
            district_vote_by_mail_area=data.get('Vote_By_Mail_Area', None),
            district_wastewater=data.get('Wastewater_District', None),
            district_water_agency=data.get('Water_Agency', None),
            district_water_agency_sub=data.get('Water_Agency_SubDistrict', None),
            district_water_conservation=data.get('Water_Conservation_District', None),
            district_water_conservation_sub=data.get('Water_Conservation_SubDistrict', None),
            district_water_control_water_conservation=data.get('Water_Control_Water_Conservation', None),
            district_water_control_water_conservation_sub=data.get('Water_Control_Water_Conservation_SubDistrict', None),
            district_water=data.get('Water_District', None),
            district_water_public_utility=data.get('Water_Public_Utility_District', None),
            district_water_public_utility_sub=data.get('Water_Public_Utility_Subdistrict', None),
            district_water_replacement=data.get('Water_Replacement_District', None),
            district_water_replacement_sub=data.get('Water_Replacement_SubDistrict', None),
            district_water_sub=data.get('Water_SubDistrict', None),
            district_weed=data.get('Weed_District', None)
        )
    
    def _parse_mobile_advertising_info(self, data: Dict[str, Any]) -> MobileAdvertisingInfo:
        """Parse mobile advertising ID information from raw data."""
        return MobileAdvertisingInfo(
            maid_available=data.get('ConsumerData_MAID_Available', 'N') == 'Y',
            maid_1=data.get('ConsumerData_MAID_MAID1', None),
            maid_1_cell_phone_system=data.get('ConsumerData_MAID_MAID1_Cell_Phone_System', None),
            maid_2=data.get('ConsumerData_MAID_MAID2', None),
            maid_2_cell_phone_system=data.get('ConsumerData_MAID_MAID2_Cell_Phone_System', None),
            maid_3=data.get('ConsumerData_MAID_MAID3', None),
            maid_3_cell_phone_system=data.get('ConsumerData_MAID_MAID3_Cell_Phone_System', None),
            maid_4=data.get('ConsumerData_MAID_MAID4', None),
            maid_4_cell_phone_system=data.get('ConsumerData_MAID_MAID4_Cell_Phone_System', None),
            maid_5=data.get('ConsumerData_MAID_MAID5', None),
            maid_5_cell_phone_system=data.get('ConsumerData_MAID_MAID5_Cell_Phone_System', None),
            maid_ip_available=data.get('ConsumerData_MAID_IP_Available', 'N') == 'Y',
            maid_ip_1=data.get('ConsumerData_MAID_IP1', None),
            maid_ip_2=data.get('ConsumerData_MAID_IP2', None),
            maid_ip_3=data.get('ConsumerData_MAID_IP3', None),
            maid_ip_4=data.get('ConsumerData_MAID_IP4', None),
            maid_ip_5=data.get('ConsumerData_MAID_IP5', None)
        )
    
    def _safe_int(self, value: Any) -> Optional[int]:
        """Safely convert value to integer."""
        if value is None or pd.isna(value):
            return None
        try:
            return int(float(value))
        except (ValueError, TypeError):
            return None
    
    def _safe_float(self, value: Any) -> Optional[float]:
        """Safely convert value to float."""
        if value is None or pd.isna(value):
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None
    
    def _parse_list_field(self, value: Any) -> Optional[List[str]]:
        """Parse list fields from raw data."""
        if not value or pd.isna(value):
            return None
        if isinstance(value, str):
            return [item.strip() for item in value.split(';') if item.strip()]
        return None
    
    def get_data_point(self, key: str) -> Any:
        """Get a specific data point from raw data."""
        return self.raw_data.get(key, None)
    
    def all_data(self) -> Dict[str, Any]:
        """Return all raw data."""
        return self.raw_data.copy()
    
    def __str__(self) -> str:
        """String representation of L2 data row."""
        name = f"{self.personal.first_name or ''} {self.personal.last_name or ''}".strip()
        return f"L2DataRow for {name} (ID: {self.lalvoterid}, Sequence: {self.sequence})"
    
    def __repr__(self) -> str:
        """Detailed representation of L2 data row."""
        return f"L2DataRow(sequence={self.sequence}, lalvoterid={self.lalvoterid})"
