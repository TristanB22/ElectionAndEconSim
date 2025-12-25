#!/usr/bin/env python3
"""
Day Simulation Manager

Manages full-day simulations from midnight to midnight with proper event scheduling,
agent wake-up times, and tick-based execution.
"""

import random
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from Environment.simulation_time_manager import get_simulation_time_manager


@dataclass
class ScheduledEvent:
    """Represents a scheduled event in the simulation."""
    
    simulation_time: datetime
    agent_id: str
    action_name: str
    action_params: Dict[str, Any]
    location: str
    priority: int = 0  # Lower numbers = higher priority
    
    def __lt__(self, other):
        """Sort by time, then by priority."""
        if self.simulation_time != other.simulation_time:
            return self.simulation_time < other.simulation_time
        return self.priority < other.priority


@dataclass
class AgentSchedule:
    """Represents an agent's daily schedule."""
    
    agent_id: str
    wake_up_time: datetime
    daily_plan: List[ScheduledEvent]
    is_awake: bool = False
    
    def get_events_for_tick(self, tick_start: datetime, tick_end: datetime) -> List[ScheduledEvent]:
        """Get events that should occur within a specific time tick."""
        events = []
        for event in self.daily_plan:
            if tick_start <= event.simulation_time <= tick_end:
                events.append(event)
        return events


class DaySimulationManager:
    """Manages a full day simulation with proper time progression and event execution."""
    
    def __init__(self, simulation_id: str, start_date: Optional[datetime] = None):
        self.simulation_id = simulation_id
        self.time_manager = get_simulation_time_manager(simulation_id)
        
        # Set start date to midnight of the specified date (or today)
        if start_date is None:
            start_date = datetime.now()
        
        # Start at midnight of the specified date
        self.day_start = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
        # Initialize simulation time capped to end-of-day to prevent rolling into future days
        day_end = self.day_start + timedelta(days=1)
        self.time_manager.initialize_simulation_time(self.day_start, "15m", end_datetime=day_end)
        
        # Agent schedules and events
        self.agent_schedules: Dict[str, AgentSchedule] = {}
        self.scheduled_events: List[ScheduledEvent] = []
        self.executed_events: List[ScheduledEvent] = []
        
        # Current tick information - sync with simulation time manager
        self.current_tick_start = self.time_manager.get_current_datetime()
        self.current_tick_end = self.current_tick_start + timedelta(minutes=15)
        # Caches for efficient location logging
        self._agent_home_coords: Dict[str, Tuple[float, float]] = {}
        self._poi_cache: Dict[int, Tuple[float, float]] = {}
        
    def add_agent_schedule(self, agent_id: str, wake_up_time: datetime, daily_plan: List[ScheduledEvent]) -> None:
        """Add an agent's schedule to the simulation."""
        schedule = AgentSchedule(
            agent_id=agent_id,
            wake_up_time=wake_up_time,
            daily_plan=daily_plan
        )
        self.agent_schedules[agent_id] = schedule
        
        # Add all events to the master schedule
        for event in daily_plan:
            self.scheduled_events.append(event)
        
        # Sort all events by time and priority
        self.scheduled_events.sort()
    
    def generate_realistic_wake_up_time(self, agent_age: int, agent_personality: str = "average") -> datetime:
        """Generate a realistic wake-up time based on agent characteristics."""
        # Base wake-up times by age group
        if agent_age < 18:  # Teenagers
            base_hour = random.randint(7, 9)
        elif agent_age < 30:  # Young adults
            base_hour = random.randint(6, 8)
        elif agent_age < 50:  # Middle-aged adults
            base_hour = random.randint(5, 7)
        else:  # Older adults
            base_hour = random.randint(5, 7)
        
        # Add some randomness
        base_hour += random.randint(-1, 1)
        base_hour = max(4, min(10, base_hour))  # Keep between 4 AM and 10 AM
        
        # Random minutes
        minutes = random.choice([0, 15, 30, 45])
        
        return self.day_start.replace(hour=base_hour, minute=minutes)
    
    def advance_to_next_tick(self) -> Tuple[datetime, datetime]:
        """Advance simulation time to the next tick and return tick boundaries."""
        # Advance time by one tick using the simulation time manager
        self.time_manager.advance_tick()
        
        # Get current simulation time from the manager
        current_time = self.time_manager.get_current_datetime()
        
        # Update tick boundaries based on current simulation time
        self.current_tick_start = current_time
        self.current_tick_end = current_time + timedelta(minutes=15)
        
        # Refresh agent budgets at the start of each new day (midnight)
        if current_time.hour == 0 and current_time.minute == 0:
            self._refresh_agent_budgets()
        
        return self.current_tick_start, self.current_tick_end
    
    def _refresh_agent_budgets(self) -> None:
        """Refresh attention and time budgets for all agents at the start of a new day."""
        if hasattr(self, '_agents_cache'):
            for agent in self._agents_cache:
                agent.attention_budget_minutes = 60 * 8  # 8 hours of attention
                agent.time_budget_minutes = 60 * 16  # 16 hours of active time
                print(f"   Refreshed budgets for agent {agent.agent_id}")
    
    def _trigger_conversations(self, world, conversation_manager) -> int:
        """Check for conversation triggers and run conversations if conditions are met."""
        conversations_triggered = 0
        
        # Check for DM events in the current tick
        for event in self.scheduled_events:
            if event.action_name.startswith("dm_on_"):
                # Find the sender and recipient agents
                sender = None
                recipient = None
                
                for agent in world._agents_cache:
                    if str(agent.agent_id) == event.agent_id:
                        sender = agent
                    elif str(agent.agent_id) == event.action_params.get("recipient_id"):
                        recipient = agent
                
                if sender and recipient:
                    # Run conversation
                    channel_id = event.action_name.replace("dm_on_", "")
                    context = f"Direct message from {sender.agent_id} to {recipient.agent_id}"
                    
                    try:
                        conversation_result = conversation_manager.run_conversation(
                            sender, recipient, channel_id, context, self.current_tick_start
                        )
                        if conversation_result:
                            conversations_triggered += 1
                            print(f"   Conversation triggered between {sender.agent_id} and {recipient.agent_id}")
                    except Exception as e:
                        print(f"   [ERROR] Conversation failed: {e}")
        
        # Check for proximity-based conversations (simplified)
        # In a real system, this would check agent locations and trigger conversations
        # when agents are in the same location
        
        return conversations_triggered
    
    def get_events_for_current_tick(self) -> List[ScheduledEvent]:
        """Get all events that should occur in the current time tick."""
        tick_events = []
        
        for event in self.scheduled_events:
            if self.current_tick_start <= event.simulation_time <= self.current_tick_end:
                tick_events.append(event)
        
        # Sort by priority within the tick
        tick_events.sort(key=lambda x: (x.simulation_time, x.priority))
        return tick_events
    
    def execute_tick_events(self, world, executor, conversation_manager=None) -> Dict[str, Any]:
        """Execute all events scheduled for the current tick."""
        tick_events = self.get_events_for_current_tick()
        execution_results = {
            'executed': [],
            'failed': [],
            'tick_start': self.current_tick_start,
            'tick_end': self.current_tick_end,
            'events_processed': len(tick_events),
            'conversations_triggered': 0
        }
        
        print(f"\nExecuting tick: {self.current_tick_start.strftime('%I:%M %p')} - {self.current_tick_end.strftime('%I:%M %p')}")
        print(f"   {self.current_tick_start.strftime('%A, %B %d, %Y')}")
        
        # Check for conversation triggers (DM events, proximity, etc.)
        if conversation_manager and hasattr(world, '_agents_cache'):
            conversations_triggered = self._trigger_conversations(world, conversation_manager)
            execution_results['conversations_triggered'] = conversations_triggered
        
        if not tick_events:
            print("   No events scheduled for this time period")
            return execution_results
        
        print(f"   {len(tick_events)} events to execute")
        
        # Execute events in chronological order within the tick
        for event in tick_events:
            try:
                print(f"   {event.agent_id}: {event.action_name} at {event.simulation_time.strftime('%I:%M %p')}")
                
                # Get the agent from the world state
                agent = None
                # Agents are stored in world.state.positions, but we need the actual agent objects
                # For now, we'll need to pass the agents list from the test
                if hasattr(world, '_agents_cache'):
                    for agent_obj in world._agents_cache:
                        if str(agent_obj.agent_id) == event.agent_id:
                            agent = agent_obj
                            break
                
                if not agent:
                    print(f"      [WARNING] Agent {event.agent_id} not found in world")
                    execution_results['failed'].append({
                        'agent_id': event.agent_id,
                        'action': event.action_name,
                        'time': event.simulation_time,
                        'error': 'Agent not found in world'
                    })
                    continue
                
                # Convert event to PlanStep and execute via PlanExecutor
                from Agent.cognitive_modules.structured_planning import PlanStep
                step = PlanStep(
                    target_time=event.simulation_time.strftime('%I:%M %p'),
                    action=event.action_name,
                    location=event.location,
                    parameters=event.action_params or {}
                )
                
                # Execute the step using the PlanExecutor
                step_result = executor.execute(agent, [step], default_firm_id="test_firm_001")  # Use the firm ID from the test
                
                if step_result.get('executed'):
                    execution_results['executed'].append({
                        'agent_id': event.agent_id,
                        'action': event.action_name,
                        'time': event.simulation_time,
                        'params': event.action_params,
                        'result': step_result
                    })
                    # Mark as executed and remove from scheduled events to prevent re-execution
                    self.executed_events.append(event)
                    self.scheduled_events.remove(event)
                else:
                    execution_results['failed'].append({
                        'agent_id': event.agent_id,
                        'action': event.action_name,
                        'time': event.simulation_time,
                        'error': 'Step execution failed',
                        'result': step_result
                    })
                    # Remove failed events to prevent re-execution
                    self.scheduled_events.remove(event)
                
            except Exception as e:
                print(f"   [ERROR] Failed to execute {event.action_name} for {event.agent_id}: {e}")
                execution_results['failed'].append({
                    'agent_id': event.agent_id,
                    'action': event.action_name,
                    'time': event.simulation_time,
                    'error': str(e)
                })
        
        return execution_results
    
    def run_full_day_simulation(self, world, executor) -> Dict[str, Any]:
        """Run the simulation until end-of-day or configured end time."""
        print(f"\nStarting full day simulation: {self.day_start.strftime('%A, %B %d, %Y')}")
        print(f"Simulation time: {self.time_manager.get_current_datetime().strftime('%I:%M %p')}")
        print(f"Agents scheduled: {len(self.agent_schedules)}")
        print(f"Total events planned: {len(self.scheduled_events)}")
        
        day_results = {
            'day_start': self.day_start,
            'day_end': self.day_start + timedelta(days=1),
            'total_ticks': 96,  # 24 hours * 4 ticks per hour (15-minute granularity)
            'ticks_executed': 0,
            'total_events': len(self.scheduled_events),
            'events_executed': 0,
            'events_failed': 0
        }
        
        # Seed starting locations if needed (ensures home lat/lon exists)
        try:
            from Database.managers import get_simulations_manager
            db = get_simulations_manager()
            db.seed_agent_start_locations(self.simulation_id)
            # Prefetch home coords for all scheduled agents
            agent_ids = list(self.agent_schedules.keys())
            if agent_ids:
                placeholders = ",".join(["%s"] * len(agent_ids))
                query = f"""
                    SELECT agent_id, latitude, longitude
                    FROM {db._format_table('agent_locations')}
                    WHERE simulation_id = %s AND agent_id IN ({placeholders})
                    GROUP BY agent_id
                """
                params = tuple([self.simulation_id] + agent_ids)
                res = db.execute_query(query, params, fetch=True)
                if res.success and res.data:
                    for row in res.data:
                        try:
                            self._agent_home_coords[str(row["agent_id"])]= (float(row["latitude"]), float(row["longitude"]))
                        except Exception:
                            continue
                else:
                    # Fallback: fetch lat/lon from agents.l2_geo
                    try:
                        from Database.managers import get_agents_manager
                        adb = get_agents_manager()
                        placeholders2 = ",".join(["%s"] * len(agent_ids))
                        q2 = f"""
                            SELECT LALVOTERID AS agent_id, latitude, longitude
                            FROM {adb._format_table('l2_geo')}
                            WHERE LALVOTERID IN ({placeholders2})
                        """
                        r2 = adb.execute_query(q2, tuple(agent_ids), fetch=True)
                        if r2.success and r2.data:
                            for row in r2.data:
                                try:
                                    self._agent_home_coords[str(row["agent_id"])]= (float(row["latitude"]), float(row["longitude"]))
                                except Exception:
                                    continue
                    except Exception:
                        pass
        except Exception:
            pass

        # Run simulation tick by tick until we reach configured end
        while not self.time_manager.is_end_of_day():
            # Execute current tick
            tick_results = self.execute_tick_events(world, executor)
            
            # Update day results
            day_results['ticks_executed'] += 1
            day_results['events_executed'] += len(tick_results['executed'])
            day_results['events_failed'] += len(tick_results['failed'])
            
            # After executing tick, log agent locations in batch
            try:
                self._log_agent_locations_batch(world)
            except Exception:
                pass

            # Advance to next tick
            self.advance_to_next_tick()
            
            # Check if we've reached the end of the day
            if self.time_manager.is_end_of_day():
                break
        
        print(f"\n[SUCCESS] Day simulation completed!")
        print(f"Results: {day_results['ticks_executed']} ticks, {day_results['events_executed']} events executed")
        
        return day_results

    def _resolve_coords(self, world, agent_id: str) -> Tuple[float, float]:
        """Resolve current coordinates for an agent based on world state and caches."""
        place_id = world.state.get_agent_position(agent_id)
        # Default to home
        lat, lon = self._agent_home_coords.get(agent_id, (None, None))
        if not place_id or place_id in ("home", "in_transit", None):
            return lat, lon
        # If world.locations has coordinates
        try:
            loc = getattr(world, "locations", {}).get(str(place_id))
            if loc and "lat" in loc and "lon" in loc:
                return float(loc["lat"]), float(loc["lon"])
        except Exception:
            pass
        # If place_id looks like OSM id, check cache/db
        try:
            pid = int(str(place_id))
            if pid in self._poi_cache:
                return self._poi_cache[pid]
            from Database.managers import get_simulations_manager
            db = get_simulations_manager()
            coords = db.get_poi_coords([pid])
            if pid in coords:
                self._poi_cache.update(coords)
                return coords[pid]
        except Exception:
            pass
        # Fallback to home
        return lat, lon

    def _log_agent_locations_batch(self, world) -> None:
        """Log all agent positions for current tick in a single batch insert."""
        from Database.managers import get_simulations_manager
        db = get_simulations_manager()
        sim_time = self.time_manager.get_current_datetime()
        rows = []
        for agent_id in self.agent_schedules.keys():
            lat, lon = self._resolve_coords(world, agent_id)
            if lat is None or lon is None:
                continue
            rows.append((self.simulation_id, agent_id, float(lat), float(lon), sim_time))
        if rows:
            db.insert_agent_locations_batch(rows)
    
    def get_simulation_summary(self) -> Dict[str, Any]:
        """Get a summary of the simulation state."""
        return {
            'current_time': self.time_manager.get_current_datetime(),
            'day_start': self.day_start,
            'ticks_completed': len(self.executed_events),
            'total_agents': len(self.agent_schedules),
            'total_events': len(self.scheduled_events),
            'executed_events': len(self.executed_events)
        }
