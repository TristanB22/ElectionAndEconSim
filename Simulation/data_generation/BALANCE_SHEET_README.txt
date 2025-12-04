================================================================================
HOUSEHOLD BALANCE SHEET GENERATION - IMPLEMENTATION SUMMARY
================================================================================

OVERVIEW
--------
This module generates realistic household balance sheets at simulation start
based on L2 voter data, economic indicators (HPI), and statistical distributions
calibrated to U.S. household survey data.

Key Features:
- Household-level modeling (not per-agent)
- Single sampled balance sheet per household at simulation start
- Idempotent (won't duplicate if run multiple times)
- Deterministic (same household always gets same balance sheet for a simulation)
- Integrated into existing bulk agent initialization flow


INTEGRATION POINTS
------------------

1. AUTOMATIC INTEGRATION (Recommended)
   When creating a simulation with agent_ids:

   from Database.managers import get_simulations_manager
   
   sim_mgr = get_simulations_manager()
   sim_id = sim_mgr.register_simulation(
       started_by="user",
       description="My simulation",
       sim_start=datetime.now(),
       tick_granularity="15m",
       agent_ids=["agent1", "agent2", ...]  # Triggers balance sheet generation
   )
   
   Balance sheets are automatically created during bulk_initialize_agents().

2. MANUAL INTEGRATION (For custom flows)
   If you need to generate balance sheets separately:

   from Simulation.data_generation import ensure_initial_household_balance_sheet_for_agent
   
   for agent_id in agent_list:
       ensure_initial_household_balance_sheet_for_agent(
           simulation_id=sim_id,
           lalvoterid=agent_id,
           rng_seed=None  # Uses deterministic seed
       )


DATABASE SCHEMA
---------------

Target Table: world_sim_simulations.household_balance_sheet_samples

Primary Key: (simulation_id, household_id, sim_clock_datetime)

Columns:
  Identifiers:
    - simulation_id (VARCHAR 64)
    - household_id (VARCHAR 32) 
    - sim_clock_datetime (TIMESTAMP)
  
  Provenance:
    - net_worth_bucket (VARCHAR 64) - from L2 data
    - hpi_level (VARCHAR 32) - CBSA/MSA/STATE
    - hpi_place_id (VARCHAR 32) - geographic identifier
    - vehicle_lambda_decay (DECIMAL 6,5) - household depreciation rate
  
  Assets:
    - primaryHomeValue (DECIMAL 18,2)
    - secondaryREValue (DECIMAL 18,2)
    - retirementAccounts (DECIMAL 18,2)
    - taxableInvestments (DECIMAL 18,2)
    - liquidSavings (DECIMAL 18,2)
    - vehiclesValue (DECIMAL 18,2)
    - durablesOther (DECIMAL 18,2)
  
  Liabilities:
    - mortgageBalance (DECIMAL 18,2)
    - autoLoans (DECIMAL 18,2)
    - creditCardRevolving (DECIMAL 18,2)
    - studentLoans (DECIMAL 18,2)
    - otherDebt (DECIMAL 18,2)
  
  Totals:
    - assetsTotal (DECIMAL 18,2)
    - liabilitiesTotal (DECIMAL 18,2)
    - netWorth (DECIMAL 18,2)


HOUSEHOLD RESOLUTION
--------------------

Households are resolved from L2 data with this priority:
1. Residence_Families_FamilyID (preferred)
2. Mailing_Families_FamilyID (fallback)
3. SYNTH_{LALVOTERID} (synthetic single-member household)

Multiple agents in the same family will share one household balance sheet.


DATA SOURCES
------------

L2 Voter Data (world_sim_agents):
  - l2_agent_core: age, gender
  - l2_other_part_1: household size, education, marital status
  - l2_other_part_2: income estimates, area medians, CBSA/MSA codes
  - l2_other_part_3: home purchase data, credit rating, vehicles
  - l2_location: address, square footage
  - l2_geo: latitude/longitude
  - l2_political_part_3: net worth bucket

HPI Data (world_sim_alternative_data):
  - hpi_data: FHFA house price indices (quarterly, by geography)

Simulation Data (world_sim_simulations):
  - simulations: simulation_start_datetime


SAMPLING METHODOLOGY
--------------------

Primary Home Value:
  - LogNormal distribution
  - Parameters derived from HPI growth factor, square footage, income quantile
  - Purchase price estimated from HPI data or area median

Mortgage Balance:
  - Standard amortization calculation
  - Initial LTV sampled from Beta distribution (varies by credit tier)
  - Interest rate: TruncNormal(5%, 1.5%, [2%, 9%])
  - Term: {15, 20, 30} years with probs {0.1, 0.2, 0.7}

Retirement Accounts:
  - Gamma distribution
  - Shape parameter based on log(income) and age
  - Capped at 8x annual income

Taxable Investments & Liquid Savings:
  - LogNormal distributions
  - Parameters vary by income quantile, credit tier, household size

Vehicles:
  - Exponential depreciation: value = MSRP * exp(-λ * age)
  - Household-specific decay rate λ ~ TruncNormal(0.18, 0.05, [0.08, 0.35])
  - MSRP ~ LogNormal(10.8, 0.5)

Liabilities:
  - Auto loans: LogNormal, conditional on vehicle count
  - Credit cards: income fraction × Beta, conditional on CC presence
  - Student loans: Gamma, conditional on education level
  - Other debt: LogNormal

Net Worth Constraint:
  - If L2 net worth bucket specifies a minimum (e.g., ">$499,999")
  - System boosts taxable investments and liquid savings to meet constraint


HPI RESOLUTION PRIORITY
-----------------------

Geographic level selected in this order:
1. CBSA (Core-Based Statistical Area) - if ConsumerData_CBSA_Code present
2. MSA (Metropolitan Statistical Area) - if ConsumerData_MSA_Code present
3. STATE (Two-letter state code) - from Residence_Addresses_State

HPI growth factor computed from:
  - Purchase quarter (inferred from purchase year/date)
  - Current quarter (from simulation_start_datetime)
  - Growth = index(current) / index(purchase)


TESTING & VALIDATION
--------------------

Test Script: World_Sim/Examples/test_household_balance_sheet_generation.py

Run:
  python3 Examples/test_household_balance_sheet_generation.py
  
With cleanup:
  python3 Examples/test_household_balance_sheet_generation.py --cleanup

The test script:
  1. Creates a simulation with 5 test agents
  2. Verifies balance sheets are generated
  3. Tests idempotency (re-running doesn't duplicate)
  4. Tests household resolution
  5. Displays summary statistics


IDEMPOTENCY & PERFORMANCE
--------------------------

Idempotency:
  - Function checks for existing (simulation_id, household_id, sim_clock_datetime)
  - If exists, returns immediately without re-sampling
  - Safe to call multiple times for same household

Performance:
  - Balance sheets generated during bulk_initialize_agents()
  - One balance sheet per household (not per agent)
  - Typical: 3-5 agents → 2-3 households → 2-3 balance sheets
  - Uses deterministic RNG seed (hash of simulation_id + household_id)


DETERMINISTIC SAMPLING
----------------------

Reproducibility:
  - Each (simulation_id, household_id) pair gets a deterministic seed
  - Seed = SHA256(simulation_id:household_id)[:8] as int
  - Same household in same simulation always gets same balance sheet
  - Different simulations will get different balance sheets for same household


ERROR HANDLING
--------------

The system gracefully handles:
  - Missing L2 data (uses defaults)
  - Missing HPI data (growth factor = 1.0)
  - Invalid credit ratings (infers from CC presence)
  - Missing home purchase dates (assumes 8 years)
  - Agents without family IDs (creates synthetic household)

Errors are logged with warnings; balance sheet generation continues for other agents.


DEPENDENCIES
------------

Python Packages (add to requirements.txt if not present):
  - numpy
  - scipy

Existing Infrastructure:
  - Database.managers.simulations (SimulationsDatabaseManager)
  - Database.managers.alternative_data (AlternativeDataDatabaseManager)
  - All L2 voter data tables
  - HPI data table (world_sim_alternative_data.hpi_data)


EXAMPLE QUERY: Retrieve Balance Sheets
---------------------------------------

SELECT 
    household_id,
    hpi_level,
    hpi_place_id,
    primaryHomeValue,
    mortgageBalance,
    retirementAccounts,
    liquidSavings,
    vehiclesValue,
    assetsTotal,
    liabilitiesTotal,
    netWorth,
    net_worth_bucket
FROM world_sim_simulations.household_balance_sheet_samples
WHERE simulation_id = 'your-sim-id'
  AND sim_clock_datetime = (
      SELECT simulation_start_datetime 
      FROM world_sim_simulations.simulations 
      WHERE simulation_id = 'your-sim-id'
  )
ORDER BY netWorth DESC;


EXAMPLE QUERY: Household-Agent Mapping
---------------------------------------

SELECT 
    ia.agent_id,
    bs.household_id,
    bs.netWorth,
    bs.primaryHomeValue
FROM world_sim_simulations.initialized_agents ia
JOIN world_sim_simulations.household_balance_sheet_samples bs
  ON bs.simulation_id = ia.simulation_id
WHERE ia.simulation_id = 'your-sim-id'
  AND bs.sim_clock_datetime = (
      SELECT simulation_start_datetime 
      FROM world_sim_simulations.simulations 
      WHERE simulation_id = 'your-sim-id'
  );


FUTURE ENHANCEMENTS (Not Implemented)
--------------------------------------

1. Distributional sampling (multiple draws per household)
2. Time-varying balance sheets (periodic updates during simulation)
3. Correlation structure across asset classes
4. Household formation/dissolution dynamics
5. Inheritance and wealth transfer events
6. Alternative data sources (credit bureau, property records)
7. Machine learning calibration to Survey of Consumer Finances


CONTACT & SUPPORT
-----------------

Module Location: World_Sim/Simulation/data_generation/agent_balance_sheet_generation.py
Test Script: World_Sim/Examples/test_household_balance_sheet_generation.py
Documentation: This file

For questions or issues, check the test script first to see working examples.


================================================================================
END OF DOCUMENTATION
================================================================================

