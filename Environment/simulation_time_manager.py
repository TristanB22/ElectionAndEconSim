#!/usr/bin/env python3
"""
Simulation Time Manager

Provides centralized time management for simulations with database integration.
Manages simulation time progression, tick granularity, and time-based events.
"""

import time
from datetime import datetime, timedelta
from typing import Optional, Union, Dict, Any
from dataclasses import dataclass, field
import mysql.connector


@dataclass
class SimulationTimeState:
    """Represents the current state of simulation time."""
    
    simulation_id: str
    start_datetime: datetime
    current_datetime: datetime
    tick_granularity: str  # e.g., "15m", "1h", "1d"
    end_datetime: Optional[datetime] = None
    is_paused: bool = False
    last_tick: datetime = field(default_factory=datetime.now)
    
    def __post_init__(self):
        """Initialize current time to start time."""
        if self.current_datetime == datetime.now():
            self.current_datetime = self.start_datetime
        self.last_tick = self.start_datetime
    
    def get_tick_delta(self) -> timedelta:
        """Get the time delta for one tick based on granularity."""
        granularity_map = {
            "1m": timedelta(minutes=1),
            "5m": timedelta(minutes=5),
            "15m": timedelta(minutes=15),
            "30m": timedelta(minutes=30),
            "1h": timedelta(hours=1),
            "2h": timedelta(hours=2),
            "4h": timedelta(hours=4),
            "6h": timedelta(hours=6),
            "12h": timedelta(hours=12),
            "1d": timedelta(days=1),
        }
        return granularity_map.get(self.tick_granularity, timedelta(minutes=15))
    
    def advance_tick(self) -> datetime:
        """Advance simulation time by one tick."""
        if not self.is_paused:
            tick_delta = self.get_tick_delta()
            next_time = self.current_datetime + tick_delta
            if self.end_datetime and next_time > self.end_datetime:
                self.current_datetime = self.end_datetime
            else:
                self.current_datetime = next_time
            self.last_tick = self.current_datetime
            
            # Check if we've passed midnight and need to wrap to next day
            if self.current_datetime.hour == 0 and self.current_datetime.minute == 0:
                # We're at midnight, this is the end of the simulation day
                pass
                
        return self.current_datetime
    
    def advance_to_time(self, target_time: datetime) -> datetime:
        """Advance simulation time to a specific target time."""
        if not self.is_paused and target_time > self.current_datetime:
            self.current_datetime = target_time
            self.last_tick = target_time
        return self.current_datetime
    
    def get_current_timestamp(self) -> float:
        """Get current simulation time as Unix timestamp."""
        return self.current_datetime.timestamp()
    
    def get_current_datetime(self) -> datetime:
        """Get current simulation time as datetime object."""
        return self.current_datetime
    
    def get_current_day_start(self) -> datetime:
        """Get the start of the current simulation day (midnight)."""
        return self.current_datetime.replace(hour=0, minute=0, second=0, microsecond=0)
    
    def get_current_day_end(self) -> datetime:
        """Get the end of the current simulation day (11:59 PM)."""
        return self.current_datetime.replace(hour=23, minute=59, second=59, microsecond=999999)
    
    def is_end_of_day(self) -> bool:
        """Check if we've reached the end of the simulation day or overall end time."""
        if self.end_datetime and self.current_datetime >= self.end_datetime:
            return True
        # Check if we've reached 11:59:59 PM (end of day)
        return (self.current_datetime.hour == 23 and 
                self.current_datetime.minute == 59 and 
                self.current_datetime.second >= 59)
    
    def get_time_difference(self, other_datetime: datetime) -> timedelta:
        """Get time difference between current simulation time and another datetime."""
        return self.current_datetime - other_datetime
    
    def pause(self) -> None:
        """Pause time progression."""
        self.is_paused = True
    
    def resume(self) -> None:
        """Resume time progression."""
        self.is_paused = False
    
    def reset_to_start(self) -> None:
        """Reset current time to start time."""
        self.current_datetime = self.start_datetime
        self.last_tick = self.start_datetime


class DatabaseSimulationTimeManager:
    """Manages simulation time with database persistence."""
    
    def __init__(self, simulation_id: str, db_config: Dict[str, Any]):
        self.simulation_id = simulation_id
        self.db_config = db_config
        self.time_state: Optional[SimulationTimeState] = None
        self._load_from_database()
    
    def _load_from_database(self) -> None:
        """Load simulation time state from database."""
        try:
            from Database.connection_manager import execute_sim_query
            
            rows = execute_sim_query("""
                SELECT simulation_start_datetime, current_simulation_datetime, simulation_end_datetime, tick_granularity
                FROM simulations WHERE simulation_id = %s
            """, (self.simulation_id,), fetch=True)
            
            if rows:
                row = rows[0]
                start_dt = row['simulation_start_datetime']
                current_dt = row['current_simulation_datetime']
                granularity = row['tick_granularity']
                end_dt = row.get('simulation_end_datetime')
                
                self.time_state = SimulationTimeState(
                    simulation_id=self.simulation_id,
                    start_datetime=start_dt,
                    current_datetime=current_dt,
                    tick_granularity=granularity,
                    end_datetime=end_dt
                )
            else:
                # Create default time state
                now = datetime.now()
                self.time_state = SimulationTimeState(
                    simulation_id=self.simulation_id,
                    start_datetime=now.replace(hour=6, minute=0, second=0, microsecond=0),  # 6:00 AM
                    current_datetime=now.replace(hour=6, minute=0, second=0, microsecond=0),
                    tick_granularity="15m"
                )
                self._save_to_database()
            
        except ImportError as e:
            # Silently ignore import errors - database might not be available
            now = datetime.now()
            self.time_state = SimulationTimeState(
                simulation_id=self.simulation_id,
                start_datetime=now.replace(hour=6, minute=0, second=0, microsecond=0),
                current_datetime=now.replace(hour=6, minute=0, second=0, microsecond=0),
                tick_granularity="15m"
            )
        except Exception as e:
            print(f"Warning: Could not load simulation time from database: {e}")
            # Fallback to default
            now = datetime.now()
            self.time_state = SimulationTimeState(
                simulation_id=self.simulation_id,
                start_datetime=now.replace(hour=6, minute=0, second=0, microsecond=0),
                current_datetime=now.replace(hour=6, minute=0, second=0, microsecond=0),
                tick_granularity="15m"
            )
    
    def _save_to_database(self) -> None:
        """Save current simulation time state to database."""
        if not self.time_state:
            return
            
        try:
            from Database.connection_manager import execute_sim_query
            execute_sim_query("""
                UPDATE simulations 
                SET current_simulation_datetime = %s
                WHERE simulation_id = %s
            """, (self.time_state.current_datetime, self.simulation_id), fetch=False)
            
        except ImportError as e:
            # Silently ignore import errors - database might not be available
            pass
        except Exception as e:
            print(f"Warning: Could not save simulation time to database: {e}")
    
    def initialize_simulation_time(self, start_datetime: datetime, tick_granularity: str = "15m", end_datetime: Optional[datetime] = None) -> None:
        """Initialize simulation time with specific start, end and granularity.
        If end_datetime is None and an existing time_state is present, preserve its end_datetime.
        """
        preserved_end = end_datetime
        if preserved_end is None and self.time_state is not None:
            preserved_end = self.time_state.end_datetime
        self.time_state = SimulationTimeState(
            simulation_id=self.simulation_id,
            start_datetime=start_datetime,
            current_datetime=start_datetime,
            tick_granularity=tick_granularity,
            end_datetime=preserved_end
        )
        self._save_to_database()
    
    def advance_tick(self) -> datetime:
        """Advance simulation time by one tick and save to database."""
        if self.time_state:
            new_time = self.time_state.advance_tick()
            self._save_to_database()
            return new_time
        return datetime.now()
    
    def advance_to_time(self, target_time: datetime) -> datetime:
        """Advance simulation time to specific time and save to database."""
        if self.time_state:
            new_time = self.time_state.advance_to_time(target_time)
            self._save_to_database()
            return new_time
        return datetime.now()
    
    def get_current_datetime(self) -> datetime:
        """Get current simulation datetime."""
        if self.time_state:
            return self.time_state.get_current_datetime()
        return datetime.now()
    
    def get_current_timestamp(self) -> float:
        """Get current simulation timestamp."""
        if self.time_state:
            return self.time_state.get_current_timestamp()
        return time.time()
    
    def get_tick_delta(self) -> timedelta:
        """Get the time delta for one tick."""
        if self.time_state:
            return self.time_state.get_tick_delta()
        return timedelta(minutes=15)
    
    def get_current_day_start(self) -> datetime:
        """Get the start of the current simulation day (midnight)."""
        if self.time_state:
            return self.time_state.get_current_day_start()
        return datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    
    def get_current_day_end(self) -> datetime:
        """Get the end of the current simulation day (11:59 PM)."""
        if self.time_state:
            return self.time_state.get_current_day_end()
        return datetime.now().replace(hour=23, minute=59, second=59, microsecond=999999)
    
    def is_end_of_day(self) -> bool:
        """Check if we've reached the end of the simulation day."""
        if self.time_state:
            return self.time_state.is_end_of_day()
        return False
    
    def pause(self) -> None:
        """Pause simulation time."""
        if self.time_state:
            self.time_state.pause()
    
    def resume(self) -> None:
        """Resume simulation time."""
        if self.time_state:
            self.time_state.resume()
    
    def get_time_state(self) -> Optional[SimulationTimeState]:
        """Get the current time state object."""
        return self.time_state


# Global manager instance
_simulation_time_manager: Optional[DatabaseSimulationTimeManager] = None


def get_simulation_time_manager(simulation_id: str, db_config: Optional[Dict[str, Any]] = None) -> DatabaseSimulationTimeManager:
    """Get or create the global simulation time manager."""
    global _simulation_time_manager
    
    if _simulation_time_manager is None or _simulation_time_manager.simulation_id != simulation_id:
        if db_config is None:
            # Use the proper database configuration that respects DATABASE_TARGET
            from Utils.environment_config import EnvironmentConfig
            env_config = EnvironmentConfig()
            db_config = env_config.get_database_config()
            db_config['database'] = 'world_sim_simulations'
            db_config['autocommit'] = True
        _simulation_time_manager = DatabaseSimulationTimeManager(simulation_id, db_config)
    
    return _simulation_time_manager


def set_simulation_time(simulation_id: str, start_datetime: datetime, tick_granularity: str = "15m") -> None:
    """Set the simulation time parameters."""
    manager = get_simulation_time_manager(simulation_id)
    manager.initialize_simulation_time(start_datetime, tick_granularity)


def advance_simulation_time(simulation_id: str, minutes: int = 0, hours: int = 0) -> datetime:
    """Advance simulation time by specified amount."""
    manager = get_simulation_time_manager(simulation_id)
    current = manager.get_current_datetime()
    target = current + timedelta(minutes=minutes, hours=hours)
    return manager.advance_to_time(target)


def get_current_simulation_datetime(simulation_id: str) -> datetime:
    """Get current simulation datetime."""
    manager = get_simulation_time_manager(simulation_id)
    return manager.get_current_datetime()


def get_current_simulation_timestamp(simulation_id: str) -> float:
    """Get current simulation timestamp."""
    manager = get_simulation_time_manager(simulation_id)
    return manager.get_current_timestamp()
