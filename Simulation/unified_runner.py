from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import logging
from .simulation_config import SimulationConfig
from .llm_parser import LLMSimulationParser
from .simulation_manager import create_simulation, init_world_for_simulation
import os
import sys
from pathlib import Path

from Utils.path_manager import initialize_paths
initialize_paths()

# Removed invalid import of SimulationManager (not used and not defined)

from Simulation.core.world import World
from Agent.modules.plan_executor import PlanExecutor
from Utils.agent_initializer import AgentInitializer
from Simulation.day_runner import run_full_day

logger = logging.getLogger(__name__)

class UnifiedSimulationRunner:
    """Unified runner that can handle any simulation type with proper validation"""
    
    def __init__(self, api_manager):
        self.parser = LLMSimulationParser(api_manager)
        self.api_manager = api_manager
    
    def run_from_natural_language(self, query: str) -> str:
        """Run simulation from natural language description"""
        try:
            logger.info(f"Parsing natural language query: {query}")
            
            # Parse query into configuration
            config = self.parser.parse_query(query)
            
            # Validate configuration
            self._validate_config(config)
            
            # Run the simulation
            simulation_id = self._execute_simulation(config)
            
            logger.info(f"Simulation '{config.name}' started successfully with ID: {simulation_id}")
            return f"[SUCCESS] Simulation '{config.name}' started successfully with ID: {simulation_id}"
            
        except Exception as e:
            error_msg = f"Failed to run simulation: {str(e)}"
            logger.error(error_msg)
            return f"[ERROR] {error_msg}"
    
    def run_from_config(self, config: SimulationConfig) -> str:
        """Run simulation from configuration object"""
        try:
            logger.info(f"Running simulation from config: {config.name}")
            
            # Validate configuration
            self._validate_config(config)
            
            simulation_id = self._execute_simulation(config)
            
            logger.info(f"Simulation '{config.name}' started successfully with ID: {simulation_id}")
            return f"[SUCCESS] Simulation '{config.name}' started successfully with ID: {simulation_id}"
            
        except Exception as e:
            error_msg = f"Failed to run simulation: {str(e)}"
            logger.error(error_msg)
            return f"[ERROR] {error_msg}"
    
    def _validate_config(self, config: SimulationConfig):
        """Validate simulation configuration"""
        logger.info(f"Validating simulation configuration: {config.name}")
        
        # Basic validation that doesn't require database
        if config.agent_count < 1:
            raise ValueError("Agent count must be at least 1")
        
        if config.agent_count > 1000:  # Reasonable upper limit
            raise ValueError("Agent count cannot exceed 1000")
        
        # Validate time parameters
        if config.start_datetime >= config.end_datetime:
            raise ValueError("Start datetime must be before end datetime")
        
        # Validate tick granularity
        valid_granularities = ["5m", "15m", "30m", "1h", "2h", "4h", "6h", "12h", "1d", "1w", "1M"]
        if config.tick_granularity not in valid_granularities:
            raise ValueError(f"Invalid tick granularity: {config.tick_granularity}. Valid options: {valid_granularities}")
        
        # Optional database validation (only if available)
        try:
            self._validate_against_database(config)
        except Exception as e:
            logger.warning(f"Database validation skipped: {e}")
            logger.info("Proceeding with basic validation only")
        
        logger.info("Configuration validation passed")
    
    def _validate_against_database(self, config: SimulationConfig):
        """Validate configuration against available database data"""
        logger.info("Performing database validation")
        
        # Validate agent count against available data
        max_agents = self._get_max_available_agents()
        if config.agent_count > max_agents:
            raise ValueError(f"Requested {config.agent_count} agents, but only {max_agents} are available in the database")
        
        # Validate firm IDs
        if config.firms_to_include:
            available_firms = self._get_available_firm_ids()
            invalid_firms = [fid for fid in config.firms_to_include if fid not in available_firms]
            if invalid_firms:
                raise ValueError(f"Invalid firm IDs: {invalid_firms}. Available firms: {available_firms}")
    
    def _get_max_available_agents(self) -> int:
        """Get maximum number of available agents from L2 data"""
        try:
            # Try to use the existing agent initializer
            initializer = AgentInitializer()
            available_ids = initializer.get_available_l2_voter_ids(limit=10000)  # Get a large number to count
            count = len(available_ids)
            logger.info(f"Found {count} available agents in L2 data")
            return count
        except Exception as e:
            logger.warning(f"Could not determine max agents from L2 data: {e}")
            # Fallback: try to get from database directly
            try:
                # Use absolute import path
                import sys
                from pathlib import Path
                
                # Add project root to path if not already there
                project_root = Path(__file__).resolve().parent.parent
                if str(project_root) not in sys.path:
                    sys.path.insert(0, str(project_root))
                
                from Database.database_manager import execute_query as dm_execute_query
                import os
                agents_db = os.getenv('DB_AGENTS_NAME', 'world_sim_agents')
                res = dm_execute_query("SELECT COUNT(*) as count FROM l2_voter_data", None, agents_db, True)
                rows = res.data if getattr(res, 'success', False) else []
                if rows:
                    count = rows[0].get('count', 0)
                    logger.info(f"Found {count} available agents in database")
                    return count
            except Exception as db_e:
                logger.warning(f"Could not get agent count from database: {db_e}")
            
            # Conservative default based on typical L2 data availability
            logger.warning("Using conservative default of 1000 available agents")
            return 1000
    
    def _get_available_firm_ids(self) -> List[str]:
        """Get list of available firm IDs"""
        try:
            # Use absolute import path
            import sys
            from pathlib import Path
            
            # Add project root to path if not already there
            project_root = Path(__file__).resolve().parent.parent
            if str(project_root) not in sys.path:
                sys.path.insert(0, str(project_root))
            
            from Database.database_manager import execute_query as dm_execute_query
            import os
            firms_db = os.getenv('DB_FIRMS_NAME', 'world_sim_firms')
            res = dm_execute_query("SELECT id FROM firms", None, firms_db, True)
            rows = res.data if getattr(res, 'success', False) else []
            firm_ids = [str(row["id"]) for row in rows]
            logger.info(f"Found {len(firm_ids)} available firms: {firm_ids}")
            return firm_ids
        except Exception as e:
            logger.warning(f"Could not get firm IDs from database: {e}")
            # Fallback to known firm ID
            logger.warning("Using fallback firm ID: 893427615")
            return ["893427615"]
    
    def _execute_simulation(self, config: SimulationConfig) -> str:
        """Execute simulation based on configuration"""
        logger.info(f"Executing simulation: {config.name}")
        
        # Try to create simulation in database, fallback to UUID if fails
        try:
            simulation_id = create_simulation(
                started_by="unified_runner",
                description=config.description,
                start_datetime=config.start_datetime,
                end_datetime=config.end_datetime,
                tick_granularity=config.tick_granularity
            )
            logger.info(f"Created simulation in database with ID: {simulation_id}")
        except Exception as e:
            logger.warning(f"Could not create simulation in database: {e}")
            logger.info("Creating fallback simulation ID")
            import uuid
            simulation_id = str(uuid.uuid4())
            logger.info(f"Using fallback simulation ID: {simulation_id}")
        
        # Initialize world
        world = init_world_for_simulation(simulation_id)
        
        # Set up firms
        self._setup_firms(world, config)
        
        # Set up agents
        agents = self._setup_agents(world, config)
        
        # Set up goals
        goals = self._setup_goals(agents, config)
        
        # Initialize financial system
        self._initialize_financial_system(world, config)
        
        # Run simulation based on type
        if config.simulation_type == "retail_day":
            return self._run_retail_simulation(world, agents, goals, config)
        elif config.simulation_type == "global_economy":
            return self._run_global_simulation(world, agents, goals, config)
        else:
            return self._run_custom_simulation(world, agents, goals, config)
    
    def _setup_firms(self, world: World, config: SimulationConfig):
        """Set up firms based on configuration using real database data"""
        logger.info("Setting up firms for simulation")
        
        firms_added = 0
        
        if config.firms_to_include:
            # Use specific firms from configuration
            for firm_id in config.firms_to_include:
                firm_data = self._load_firm_data(firm_id)
                if firm_data:
                    world.firms[firm_id] = firm_data
                    world.state.get_firm_state(firm_id).update(firm_data.get("state", {}))
                    firms_added += 1
                    logger.info(f"Added firm: {firm_id} - {firm_data.get('name', 'Unknown')}")
                else:
                    raise RuntimeError(f"Could not load firm {firm_id} from database. Please verify firm ID exists.")
        else:
            # Load default firms based on simulation type
            default_firms = self._get_default_firms_for_type(config.simulation_type)
            for firm_id in default_firms:
                firm_data = self._load_firm_data(firm_id)
                if firm_data:
                    world.firms[firm_id] = firm_data
                    world.state.get_firm_state(firm_id).update(firm_data.get("state", {}))
                    firms_added += 1
                    logger.info(f"Added default firm: {firm_id} - {firm_data.get('name', 'Unknown')}")
                else:
                    raise RuntimeError(f"Could not load default firm {firm_id} from database. Please verify firm data availability.")
        
        if firms_added == 0:
            raise RuntimeError("No firms could be loaded from database. Please check firm data availability.")
        
        logger.info(f"Successfully set up {firms_added} firms from database")
    
    def _load_firm_data(self, firm_id: str) -> Optional[Dict[str, Any]]:
        """Load firm data from database with proper error handling"""
        try:
            # Use absolute import path
            import sys
            from pathlib import Path
            
            # Add project root to path if not already there
            project_root = Path(__file__).resolve().parent.parent
            if str(project_root) not in sys.path:
                sys.path.insert(0, str(project_root))
            
            from Database.database_manager import execute_query as dm_execute_query
            import os
            firms_db = os.getenv('DB_FIRMS_NAME', 'world_sim_firms')
            
            # Query for comprehensive firm data
            res = dm_execute_query(
                """
                SELECT id, company_name, industry_code, address, city, state, zipcode,
                       sls, employeesallsites, yearstarted, 
                       businessdescription, principal, ddm,
                       sic1, sic2, sic3, sic4, sic5, sic6
                FROM firms WHERE id = %s
                """,
                (firm_id,),
                firms_db,
                True
            )
            rows = res.data if getattr(res, 'success', False) else []
            
            if not rows:
                logger.error(f"No firm found with ID: {firm_id}")
                return None
            
            row = rows[0]
            
            # Create comprehensive firm data structure
            firm_data = {
                "id": row["id"],
                "name": row["company_name"],
                "industry": row["industry_code"],
                "address": row["address"],
                "city": row["city"],
                "state": row["state"],
                "zipcode": row["zipcode"],
                "capabilities": self._get_capabilities_from_sic(row["sic1"]),
                "state": {
                    "cash": 10000.0,  # Default starting cash
                    "inventory": self._get_default_inventory_for_industry(row["sic1"]),
                    "inventory_prices": self._get_default_prices_for_industry(row["sic1"]),
                    "costs": {
                        "rent": 2000.0,
                        "utilities": 500.0,
                        "labor": 3000.0
                    }
                },
                "dnb_info": {
                    "year": 2025,
                    "sales": float(row["sls"]) if row["sls"] else 0.0,
                    "employees": row["employeesallsites"] if row["employeesallsites"] else 0,
                    "year_started": row["yearstarted"] if row["yearstarted"] else 0,
                    "business_description": row["businessdescription"] if row["businessdescription"] else "",
                    "city": row["city"] if row["city"] else "",
                    "state": row["state"] if row["state"] else "",
                    "zipcode": row["zipcode"] if row["zipcode"] else "",
                    "principal": row["principal"] if row["principal"] else "",
                    "ddm": row["ddm"] if row["ddm"] else "",
                    "sic_codes": [row["sic1"], row["sic2"], row["sic3"], row["sic4"], row["sic5"], row["sic6"]]
                }
            }
            
            logger.info(f"Loaded firm data for {firm_id}: {firm_data['name']} ({firm_data['industry']})")
            return firm_data
            
        except Exception as e:
            logger.error(f"Error loading firm data for {firm_id}: {e}")
            return None
    
    def _get_capabilities_from_sic(self, sic_code: str) -> List[str]:
        """Get firm capabilities based on SIC code or industry code"""
        if not sic_code:
            return ["general_business"]
        
        # Map both SIC codes and industry codes to capabilities
        sic_mapping = {
            # Industry Code 445110 (Grocery Stores) - matches our firm
            "445110": ["retail_grocery", "payment_processing", "inventory_management"],
            
            # SIC Code 5411 (Grocery Stores) - also matches our firm
            "5411": ["retail_grocery", "payment_processing", "inventory_management"],
            
            # Other industry codes
            "445120": ["retail_convenience", "payment_processing"],
            "445210": ["retail_meat", "food_processing"],
            "445220": ["retail_fish", "food_processing"],
            "445230": ["retail_fruit_vegetable", "food_processing"],
            "445291": ["retail_baked_goods", "food_processing"],
            "445292": ["retail_confectionery", "food_processing"],
            "445299": ["retail_other_food", "food_processing"],
            "445310": ["retail_beer_wine", "alcohol_sales"],
            "445320": ["retail_tobacco", "tobacco_sales"],
            "446110": ["retail_pharmacy", "healthcare_products"],
            "446120": ["retail_cosmetics", "beauty_products"],
            "446130": ["retail_optical", "healthcare_products"],
            "446190": ["retail_other_health", "healthcare_products"],
            "447110": ["retail_gas_station", "fuel_sales", "convenience_store"],
            "447190": ["retail_other_gas", "fuel_sales"],
            "448110": ["retail_men_clothing", "fashion_retail"],
            "448120": ["retail_women_clothing", "fashion_retail"],
            "448130": ["retail_children_clothing", "fashion_retail"],
            "448140": ["retail_family_clothing", "fashion_retail"],
            "448150": ["retail_clothing_accessories", "fashion_retail"],
            "448190": ["retail_other_clothing", "fashion_retail"],
            "448210": ["retail_shoes", "fashion_retail"],
            "448310": ["retail_jewelry", "luxury_retail"],
            "448320": ["retail_luggage", "travel_accessories"],
            "451110": ["retail_sporting_goods", "sports_equipment"],
            "451120": ["retail_hobby_games", "entertainment_retail"],
            "451130": ["retail_book_stores", "book_retail"],
            "451140": ["retail_music_stores", "entertainment_retail"],
            "451211": ["retail_computer_stores", "technology_retail"],
            "451212": ["retail_printer_stores", "technology_retail"],
            "452111": ["retail_department_stores", "general_merchandise"],
            "452112": ["retail_discount_stores", "general_merchandise"],
            "452910": ["retail_warehouse_clubs", "bulk_retail"],
            "452990": ["retail_other_general", "general_merchandise"],
            "453110": ["retail_florists", "floral_services"],
            "453210": ["retail_office_supplies", "business_supplies"],
            "453220": ["retail_gift_stores", "gift_retail"],
            "453310": ["retail_hardware_stores", "hardware_retail"],
            "453510": ["retail_antique_stores", "antique_retail"],
            "453520": ["retail_used_merchandise", "secondhand_retail"],
            "453910": ["retail_pet_stores", "pet_supplies"],
            "453920": ["retail_art_supplies", "art_supplies"],
            "453930": ["retail_mobile_homes", "mobile_home_sales"],
            "453991": ["retail_tobacco_stores", "tobacco_retail"],
            "453998": ["retail_miscellaneous", "general_retail"],
            "454110": ["retail_electronic_shopping", "ecommerce"],
            "454210": ["retail_vending_machines", "vending"],
            "454310": ["retail_fuel_dealers", "fuel_sales"],
            "454390": ["retail_other_direct_selling", "direct_sales"]
        }
        
        return sic_mapping.get(sic_code, ["general_business"])
    
    def _get_default_inventory_for_industry(self, sic_code: str) -> Dict[str, int]:
        """Get default inventory based on SIC code"""
        if not sic_code:
            return {"GENERAL_ITEM": 100}
        
        inventory_mapping = {
            "445110": {  # Grocery stores
                "MILK_GAL": 100,
                "EGGS_12": 50,
                "BREAD_WHT": 75,
                "BANANAS_LB": 200,
                "CHICKEN_BREAST_LB": 80,
                "RICE_WHITE_LB": 150,
                "PASTA_SPAGHETTI_LB": 120,
                "TOMATOES_LB": 100,
                "ONIONS_LB": 150,
                "POTATOES_LB": 200
            },
            "445120": {  # Convenience stores
                "SODA_12OZ": 200,
                "CHIPS_BAG": 150,
                "CANDY_BAR": 100,
                "CIGARETTES_PACK": 50,
                "GASOLINE_GAL": 1000
            },
            "448110": {  # Men's clothing
                "SHIRT_MENS_M": 50,
                "PANTS_MENS_32": 40,
                "JACKET_MENS_L": 30,
                "SHOES_MENS_10": 25
            },
            "448120": {  # Women's clothing
                "DRESS_WOMENS_8": 40,
                "BLOUSE_WOMENS_M": 60,
                "PANTS_WOMENS_8": 45,
                "SHOES_WOMENS_8": 30
            },
            "451110": {  # Sporting goods
                "BASKETBALL": 20,
                "SOCCER_BALL": 25,
                "TENNIS_RACKET": 15,
                "RUNNING_SHOES_MENS_10": 30
            },
            "451130": {  # Book stores
                "FICTION_NOVEL": 200,
                "COOKBOOK": 100,
                "CHILDRENS_BOOK": 150,
                "MAGAZINE": 300
            }
        }
        
        return inventory_mapping.get(sic_code, {"GENERAL_ITEM": 100})
    
    def _get_default_prices_for_industry(self, sic_code: str) -> Dict[str, float]:
        """Get default prices based on SIC code"""
        if not sic_code:
            return {"GENERAL_ITEM": 10.00}
        
        price_mapping = {
            "445110": {  # Grocery stores
                "MILK_GAL": 4.29,
                "EGGS_12": 3.49,
                "BREAD_WHT": 2.49,
                "BANANAS_LB": 0.59,
                "CHICKEN_BREAST_LB": 3.99,
                "RICE_WHITE_LB": 1.29,
                "PASTA_SPAGHETTI_LB": 1.49,
                "TOMATOES_LB": 2.99,
                "ONIONS_LB": 0.99,
                "POTATOES_LB": 1.49
            },
            "445120": {  # Convenience stores
                "SODA_12OZ": 1.99,
                "CHIPS_BAG": 3.49,
                "CANDY_BAR": 1.29,
                "CIGARETTES_PACK": 8.99,
                "GASOLINE_GAL": 3.49
            },
            "448110": {  # Men's clothing
                "SHIRT_MENS_M": 24.99,
                "PANTS_MENS_32": 39.99,
                "JACKET_MENS_L": 89.99,
                "SHOES_MENS_10": 79.99
            },
            "448120": {  # Women's clothing
                "DRESS_WOMENS_8": 59.99,
                "BLOUSE_WOMENS_M": 34.99,
                "PANTS_WOMENS_8": 44.99,
                "SHOES_WOMENS_8": 69.99
            },
            "451110": {  # Sporting goods
                "BASKETBALL": 29.99,
                "SOCCER_BALL": 24.99,
                "TENNIS_RACKET": 89.99,
                "RUNNING_SHOES_MENS_10": 119.99
            },
            "451130": {  # Book stores
                "FICTION_NOVEL": 16.99,
                "COOKBOOK": 24.99,
                "CHILDRENS_BOOK": 12.99,
                "MAGAZINE": 4.99
            }
        }
        
        return price_mapping.get(sic_code, {"GENERAL_ITEM": 10.00})
    
    def _get_default_firms_for_type(self, simulation_type: str) -> List[str]:
        """Get default firms for simulation type"""
        if simulation_type == "retail_day":
            return ["893427615"]  # Maple Market Grocery
        elif simulation_type == "global_economy":
            return ["893427615"]  # Start with your firm, expand later
        else:
            return ["893427615"]  # Default to your firm
    
    def _setup_agents(self, world: World, config: SimulationConfig) -> List[Any]:
        """Set up agents based on configuration with real L2 data - using standardized factory"""
        logger.info(f"Setting up {config.agent_count} agents using AgentFactory")
        
        try:
            # Import the standardized factory
            from Agent.factory import AgentFactory
            
            # Get available voter IDs directly using the initializer
            initializer = AgentInitializer()
            available_ids = initializer.get_available_l2_voter_ids(limit=config.agent_count)
            
            if not available_ids or len(available_ids) == 0:
                raise RuntimeError("No L2 voter IDs available in database. Please check database connection and L2 data availability.")
            
            if len(available_ids) < config.agent_count:
                logger.warning(f"Requested {config.agent_count} agents, but only {len(available_ids)} are available")
                config.agent_count = len(available_ids)
            
            logger.info(f"Creating {config.agent_count} agents from real L2 data")
            
            # Use batch creation from factory for efficiency
            agents = AgentFactory.batch_from_database(
                available_ids[:config.agent_count],
                simulation_id=world.simulation_id
            )
            
            # Register agents with world
            for agent in agents:
                world.state.add_agent(str(agent.agent_id), initial_position="home")
            
            logger.info(f"Successfully created and registered {len(agents)} agents.")
            
            return agents
            
        except Exception as e:
            logger.error(f"Failed to set up agents: {e}", exc_info=True)
            raise
    
    def _setup_goals(self, agents: List[Any], config: SimulationConfig) -> Dict[str, str]:
        """Set up agent goals based on configuration"""
        logger.info("Setting up agent goals")
        
        goals = {}
        default_goal = config.agent_goals.get("default_goal", "Perform daily activities")
        
        for agent in agents:
            agent_id = str(agent.agent_id)
            
            # Use specific goal if available, otherwise default
            if agent_id in config.agent_goals:
                goal = config.agent_goals[agent_id]
            else:
                goal = default_goal
            
            goals[agent_id] = goal
            
            # Add goal to agent's intent manager if available
            if hasattr(agent, 'intent_manager') and agent.intent_manager:
                try:
                    from Agent.modules.intent import Goal, GoalHorizon
                    goal_obj = Goal(
                        id=f"simulation_goal_{agent_id}",
                        description=goal,
                        horizon=GoalHorizon.SHORT,
                        priority=5,
                        why="Simulation objective"
                    )
                    agent.intent_manager.add_goal(goal_obj)
                    logger.info(f"Added goal to agent {agent_id}: {goal}")
                except Exception as e:
                    logger.warning(f"Could not add goal to agent {agent_id}: {e}")
        
        return goals
    
    def _initialize_financial_system(self, world: World, config: SimulationConfig):
        """Initialize financial system for firms"""
        logger.info("Initializing financial system")
        
        executor = PlanExecutor(world)
        
        for firm_id in world.firms.keys():
            firm_state = world.state.get_firm_state(firm_id)
            if firm_state:
                initial_cash = firm_state.get("cash", 1000.0)
                initial_inventory = firm_state.get("inventory", {})
                initial_costs = firm_state.get("costs", {})
                
                try:
                    executor.initialize_firm_finances(
                        firm_id=firm_id,
                        initial_cash=initial_cash,
                        initial_inventory=initial_inventory,
                        initial_costs=initial_costs
                    )
                    logger.info(f"Initialized financial system for firm {firm_id}")
                except Exception as e:
                    logger.error(f"Failed to initialize financial system for firm {firm_id}: {e}")
    
    def _run_retail_simulation(self, world: World, agents: List[Any], goals: Dict[str, str], config: SimulationConfig) -> str:
        """Run retail simulation using your existing day_runner"""
        logger.info("Running retail simulation with day_runner")
        
        try:
            # Call the actual day_runner to execute the full day simulation
            run_full_day(
                simulation_id=world.simulation_id,
                world=world,
                agents=agents,
                goals_by_agent_id=goals,
                world_context=config.world_context,
                base_date=config.start_datetime
            )
            
            logger.info(f"Retail day simulation for {world.simulation_id} completed successfully.")
            return world.simulation_id
            
        except Exception as e:
            logger.error(f"Error running retail simulation: {e}", exc_info=True)
            raise
    
    def _run_global_simulation(self, world: World, agents: List[Any], goals: Dict[str, str], config: SimulationConfig) -> str:
        """Run global economy simulation"""
        logger.info("Running global economy simulation")
        
        # For now, use the same approach as retail but with broader scope
        # This can be expanded later
        return self._run_retail_simulation(world, agents, goals, config)
    
    def _run_custom_simulation(self, world: World, agents: List[Any], goals: Dict[str, str], config: SimulationConfig) -> str:
        """Run custom simulation based on parameters"""
        logger.info("Running custom simulation")
        
        # For now, use the same approach as retail
        # This can be expanded later with custom logic
        return self._run_retail_simulation(world, agents, goals, config)
