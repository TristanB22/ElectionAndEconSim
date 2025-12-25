#!/usr/bin/env python3
"""
Time Management Module for Environment

Provides centralized time management for the simulation environment,
allowing control over the current time instead of using computer time.
"""

import time
from datetime import datetime, timedelta
from typing import Optional, Union
from dataclasses import dataclass, field


@dataclass
class SimulationTime:
    """Manages simulation time independently of computer time."""
    
    base_date: datetime = field(default_factory=lambda: datetime.now())
    current_time: datetime = field(default_factory=lambda: datetime.now())
    time_scale: float = 1.0  # 1.0 = real time, 2.0 = twice as fast, 0.5 = half speed
    is_paused: bool = False
    last_update: float = field(default_factory=time.time)
    
    def __post_init__(self):
        """Initialize the current time to the base date."""
        if self.current_time == datetime.now():
            self.current_time = self.base_date
    
    def set_current_time(self, clock_time_str: str, base_date: Optional[datetime] = None) -> None:
        """
        Set the current simulation time from a clock time string.
        
        Args:
            clock_time_str: Time string in format "HH:MM AM/PM"
            base_date: Base date to use (defaults to current base_date)
        """
        if base_date is None:
            base_date = self.base_date
        
        try:
            # Parse time string like "06:45 AM"
            time_obj = datetime.strptime(clock_time_str, "%I:%M %p").time()
            # Combine with base date
            self.current_time = datetime.combine(base_date.date(), time_obj)
            self.last_update = time.time()
        except ValueError as e:
            print(f"Warning: Could not parse clock time '{clock_time_str}': {e}")
            self.current_time = datetime.now()
    
    def advance_time(self, minutes: int = 0, hours: int = 0) -> None:
        """
        Advance the simulation time by the specified amount.
        
        Args:
            minutes: Minutes to advance
            hours: Hours to advance
        """
        if not self.is_paused:
            delta = timedelta(minutes=minutes, hours=hours)
            self.current_time += delta
            self.last_update = time.time()
    
    def get_current_timestamp(self) -> float:
        """Get the current simulation time as a Unix timestamp."""
        return self.current_time.timestamp()
    
    def get_current_datetime(self) -> datetime:
        """Get the current simulation time as a datetime object."""
        return self.current_time
    
    def get_time_difference(self, other_timestamp: float) -> float:
        """
        Get the time difference between current simulation time and another timestamp.
        
        Args:
            other_timestamp: Unix timestamp to compare against
            
        Returns:
            Time difference in seconds (positive if simulation time is later)
        """
        return self.current_time.timestamp() - other_timestamp
    
    def pause(self) -> None:
        """Pause time progression."""
        self.is_paused = True
    
    def resume(self) -> None:
        """Resume time progression."""
        self.is_paused = False
    
    def reset_to_base(self) -> None:
        """Reset current time to the base date."""
        self.current_time = self.base_date
        self.last_update = time.time()


# Global simulation time instance
_simulation_time: Optional[SimulationTime] = None


def get_simulation_time() -> SimulationTime:
    """Get the global simulation time instance."""
    global _simulation_time
    if _simulation_time is None:
        _simulation_time = SimulationTime()
    return _simulation_time


def set_simulation_time(clock_time_str: str, base_date: Optional[datetime] = None) -> None:
    """
    Set the current simulation time.
    
    Args:
        clock_time_str: Time string in format "HH:MM AM/PM"
        base_date: Base date to use
    """
    sim_time = get_simulation_time()
    sim_time.set_current_time(clock_time_str, base_date)


def get_current_simulation_timestamp() -> float:
    """Get the current simulation time as a Unix timestamp."""
    return get_simulation_time().get_current_timestamp()


def get_current_simulation_datetime() -> datetime:
    """Get the current simulation time as a datetime object."""
    return get_simulation_time().get_current_datetime()


def advance_simulation_time(minutes: int = 0, hours: int = 0) -> None:
    """
    Advance the simulation time.
    
    Args:
        minutes: Minutes to advance
        hours: Hours to advance
    """
    get_simulation_time().advance_time(minutes, hours)


def pause_simulation_time() -> None:
    """Pause simulation time progression."""
    get_simulation_time().pause()


def resume_simulation_time() -> None:
    """Resume simulation time progression."""
    get_simulation_time().resume()


def reset_simulation_time() -> None:
    """Reset simulation time to base date."""
    get_simulation_time().reset_to_base()


def get_time_difference_from_simulation(other_timestamp: float) -> float:
    """
    Get time difference between current simulation time and another timestamp.
    
    Args:
        other_timestamp: Unix timestamp to compare against
        
    Returns:
        Time difference in seconds
    """
    return get_simulation_time().get_time_difference(other_timestamp)
