#!/usr/bin/env python3
"""
Intent Management System for Agents

Handles goal setting, planning, and execution tracking.
"""

import os
import json
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum

# Try to import simulation time manager
try:
    from Environment.time_manager import get_current_simulation_datetime, get_current_simulation_timestamp
    SIMULATION_TIME_AVAILABLE = True
except ImportError:
    print("Warning: Simulation time manager not available, using computer time")
    SIMULATION_TIME_AVAILABLE = False


def get_current_timestamp() -> float:
    """Get current timestamp (simulation time if available, computer time as fallback)."""
    if SIMULATION_TIME_AVAILABLE:
        try:
            return get_current_simulation_timestamp()
        except Exception:
            return time.time()
    else:
        return time.time()


def get_current_datetime() -> datetime:
    """Get current datetime (simulation time if available, computer time as fallback)."""
    if SIMULATION_TIME_AVAILABLE:
        try:
            return get_current_simulation_datetime()
        except Exception:
            return datetime.now()
    else:
        return datetime.now()


class GoalHorizon(str, Enum):
    IMMEDIATE = "immediate"   # hours–1 day
    SHORT = "short"           # ~week
    MEDIUM = "medium"         # ~year
    LONG = "long"             # multi-year/decades

@dataclass
class Value:
    name: str
    weight: float                     # 0..1 relative importance
    plasticity: float = 0.05          # how fast weight can change (0..1)
    evidence: List[str] = field(default_factory=list)  # memory ids supporting this value
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'name': self.name,
            'weight': self.weight,
            'plasticity': self.plasticity,
            'evidence': self.evidence
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Value':
        return cls(
            name=data['name'],
            weight=data['weight'],
            plasticity=data.get('plasticity', 0.05),
            evidence=data.get('evidence', [])
        )

@dataclass
class Goal:
    id: str
    horizon: GoalHorizon
    description: str
    why: str                           # value-anchored rationale
    done: bool = False
    progress: float = 0.0              # 0..1
    priority: float = 0.5              # 0..1 (urgency * importance)
    confidence: float = 0.7            # belief the plan is right
    start: Optional[datetime] = None
    due: Optional[datetime] = None
    substeps: List[str] = field(default_factory=list)
    value_links: Dict[str, float] = field(default_factory=dict)  # {ValueName: weight}
    evidence: List[str] = field(default_factory=list)            # memory ids
    review_after: Optional[str] = None                     # ISO duration string
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'horizon': self.horizon.value,
            'description': self.description,
            'why': self.why,
            'done': self.done,
            'progress': self.progress,
            'priority': self.priority,
            'confidence': self.confidence,
            'start': self.start.isoformat() if self.start else None,
            'due': self.due.isoformat() if self.due else None,
            'substeps': self.substeps,
            'value_links': self.value_links,
            'evidence': self.evidence,
            'review_after': self.review_after
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Goal':
        return cls(
            id=data['id'],
            horizon=GoalHorizon(data['horizon']),
            description=data['description'],
            why=data['why'],
            done=data.get('done', False),
            progress=data.get('progress', 0.0),
            priority=data.get('priority', 0.5),
            confidence=data.get('confidence', 0.7),
            start=datetime.fromisoformat(data['start']) if data.get('start') else None,
            due=datetime.fromisoformat(data['due']) if data.get('due') else None,
            substeps=data.get('substeps', []),
            value_links=data.get('value_links', {}),
            evidence=data.get('evidence', []),
            review_after=data.get('review_after')
        )

@dataclass
class ContextFrame:
    when: datetime
    where: str
    what: str                       # current activity summary
    why: str                        # immediate purpose (LLM-derived)
    with_whom: List[str] = field(default_factory=list)
    constraints: List[str] = field(default_factory=list)  # deadlines, resources
    opportunities: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'when': self.when.isoformat(),
            'where': self.where,
            'what': self.what,
            'why': self.why,
            'with_whom': self.with_whom,
            'constraints': self.constraints,
            'opportunities': self.opportunities
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ContextFrame':
        return cls(
            when=datetime.fromisoformat(data['when']),
            where=data['where'],
            what=data['what'],
            why=data['why'],
            with_whom=data.get('with_whom', []),
            constraints=data.get('constraints', []),
            opportunities=data.get('opportunities', [])
        )

class IntentManager:
    """
    Manages agent values, goals, and context.
    """
    
    def __init__(self):
        self.values: Dict[str, Value] = {}
        self.goals: Dict[GoalHorizon, List[Goal]] = {
            GoalHorizon.IMMEDIATE: [],
            GoalHorizon.SHORT: [],
            GoalHorizon.MEDIUM: [],
            GoalHorizon.LONG: [],
        }
        self.context: Optional[ContextFrame] = None
        
    def add_value(self, value: Value):
        """Add or update a value."""
        self.values[value.name] = value
    
    def add_goal(self, goal: Goal):
        """Add a goal to the appropriate horizon."""
        self.goals[goal.horizon].append(goal)
    
    def get_goal(self, goal_id: str) -> Optional[Goal]:
        """Get a goal by ID across all horizons."""
        for goals in self.goals.values():
            for goal in goals:
                if goal.id == goal_id:
                    return goal
        return None
    
    def update_goal(self, goal_id: str, updates: Dict[str, Any]) -> bool:
        """Update a goal with new values."""
        goal = self.get_goal(goal_id)
        if goal:
            for key, value in updates.items():
                if hasattr(goal, key):
                    setattr(goal, key, value)
            return True
        return False
    
    def remove_goal(self, goal_id: str) -> bool:
        """Remove a goal by ID."""
        for horizon, goals in self.goals.items():
            for i, goal in enumerate(goals):
                if goal.id == goal_id:
                    goals.pop(i)
                    return True
        return False
    
    def get_goals_by_horizon(self, horizon: GoalHorizon) -> List[Goal]:
        """Get all goals for a specific horizon."""
        return self.goals.get(horizon, [])
    
    def get_active_goals(self, horizon: Optional[GoalHorizon] = None) -> List[Goal]:
        """Get active (not done) goals, optionally filtered by horizon."""
        if horizon:
            return [g for g in self.goals[horizon] if not g.done]
        else:
            active = []
            for goals in self.goals.values():
                active.extend([g for g in goals if not g.done])
            return active
    
    def update_value_from_evidence(self, value_name: str, valence: float, mem_id: str):
        """Update a value's weight based on new evidence."""
        if value_name in self.values:
            v = self.values[value_name]
            v.evidence.append(mem_id)
            v.weight = max(0.0, min(1.0, (1-v.plasticity)*v.weight + v.plasticity*valence))
    
    def set_context(self, context: ContextFrame):
        """Set the current context."""
        self.context = context
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the entire intent manager to a dictionary."""
        return {
            'values': [v.to_dict() for v in self.values.values()],
            'goals': {
                horizon.value: [g.to_dict() for g in goals]
                for horizon, goals in self.goals.items()
            },
            'context': self.context.to_dict() if self.context else None
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'IntentManager':
        """Create an intent manager from a dictionary."""
        manager = cls()
        
        # Load values
        for value_data in data.get('values', []):
            value = Value.from_dict(value_data)
            manager.add_value(value)
        
        # Load goals
        for horizon_str, goals_data in data.get('goals', {}).items():
            horizon = GoalHorizon(horizon_str)
            for goal_data in goals_data:
                goal = Goal.from_dict(goal_data)
                manager.add_goal(goal)
        
        # Load context
        if data.get('context'):
            context = ContextFrame.from_dict(data['context'])
            manager.set_context(context)
        
        return manager
    
    def save_to_file(self, filepath: str):
        """Save the intent manager to a JSON file."""
        with open(filepath, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)
    
    @classmethod
    def load_from_file(cls, filepath: str) -> 'IntentManager':
        """Load an intent manager from a JSON file."""
        with open(filepath, 'r') as f:
            data = json.load(f)
        return cls.from_dict(data)
    
    def get_default_yale_student_intent(self) -> 'IntentManager':
        """Get a default intent configuration for a Yale student."""
        # Create default values
        values = [
            Value("growth", 0.70, 0.08),
            Value("reliability", 0.65, 0.06),
            Value("health", 0.70, 0.10),
            Value("community", 0.45, 0.08),
            Value("integrity", 0.60, 0.04),
            Value("curiosity", 0.65, 0.10),
            Value("efficiency", 0.65, 0.10),
            Value("leisure", 0.70, 0.12),
            Value("self_interest", 0.65, 0.08),
            Value("comfort", 0.60, 0.10),
            Value("autonomy", 0.65, 0.08)
        ]
        
        for value in values:
            self.add_value(value)
        
        # Create default goals
        now = get_current_datetime()
        
        # Immediate goals
        immediate_goals = [
            Goal(
                id="g_econ_ps_quality",
                horizon=GoalHorizon.IMMEDIATE,
                description="Complete elasticity problems 1–3 thoroughly and efficiently",
                why="Master academic content (growth) while using time wisely (efficiency) to maintain work-life balance (leisure)",
                priority=0.75,
                confidence=0.8,
                due=now.replace(hour=22, minute=0, second=0, microsecond=0),
                review_after="PT90M",
                value_links={"growth": 0.4, "efficiency": 0.3, "leisure": 0.3},
                substeps=["understand concepts", "solve Q1–Q3", "check work", "submit"]
            ),
            Goal(
                id="g_ra_sync_professional",
                horizon=GoalHorizon.IMMEDIATE,
                description="Communicate clearly with RA supervisor about dataset requirements",
                why="Maintain professional relationships (reliability) while being efficient (efficiency) with time",
                priority=0.70,
                confidence=0.9,
                due=now.replace(hour=20, minute=0, second=0, microsecond=0),
                review_after="PT60M",
                value_links={"reliability": 0.4, "efficiency": 0.3, "integrity": 0.3},
                substeps=["clarify requirements", "draft message", "send professionally", "follow up if needed"]
            ),
            Goal(
                id="g_balance_work_quality",
                horizon=GoalHorizon.IMMEDIATE,
                description="Plan today's schedule to balance quality work with free time",
                why="Complete tasks well (growth) while maintaining personal time (leisure) through smart planning (efficiency)",
                priority=0.70,
                confidence=0.8,
                due=now.replace(hour=18, minute=0, second=0, microsecond=0),
                review_after="PT120M",
                value_links={"efficiency": 0.3, "leisure": 0.4, "growth": 0.3},
                substeps=["prioritize important tasks", "estimate time needed", "schedule breaks", "leave buffer time"]
            )
        ]
        
        for goal in immediate_goals:
            self.add_goal(goal)
        
        # Short term goals
        short_goals = [
            Goal(
                id="g_ra_dataset_quality",
                horizon=GoalHorizon.SHORT,
                description="Deliver high-quality dataset update by Monday deadline",
                why="Meet professional standards (reliability) while working efficiently (efficiency) to maintain work-life balance (leisure)",
                priority=0.80,
                confidence=0.75,
                due=now + timedelta(days=4),
                review_after="P1D",
                value_links={"reliability": 0.4, "efficiency": 0.3, "integrity": 0.3},
                substeps=["understand requirements", "implement properly", "validate quality", "deliver on time"]
            ),
            Goal(
                id="g_work_life_balance",
                horizon=GoalHorizon.SHORT,
                description="Establish sustainable balance between academic work and personal time",
                why="Maintain academic performance (growth) while preserving personal wellbeing (leisure) through smart time management (efficiency)",
                priority=0.75,
                confidence=0.7,
                due=now + timedelta(days=14),
                review_after="P7D",
                value_links={"leisure": 0.4, "growth": 0.3, "efficiency": 0.3},
                substeps=["assess current workload", "identify priorities", "optimize study methods", "schedule personal time"]
            )
        ]
        
        for goal in short_goals:
            self.add_goal(goal)
        
        # Medium term goals
        medium_goals = [
            Goal(
                id="g_summer_internship_development",
                horizon=GoalHorizon.MEDIUM,
                description="Secure summer internship that offers good learning and career opportunities",
                why="Advance career prospects (growth) while maintaining work-life balance (leisure) and personal benefit (self_interest)",
                priority=0.65,
                confidence=0.6,
                due=now + timedelta(days=150),
                review_after="P30D",
                value_links={"growth": 0.4, "self_interest": 0.3, "leisure": 0.3},
                substeps=["research opportunities", "prepare applications", "network effectively", "evaluate offers"]
            ),
            Goal(
                id="g_develop_effective_systems",
                horizon=GoalHorizon.MEDIUM,
                description="Develop personal systems for better productivity and time management",
                why="Improve academic performance (growth) while creating more free time (leisure) through better organization (efficiency)",
                priority=0.65,
                confidence=0.7,
                due=now + timedelta(days=120),
                review_after="P30D",
                value_links={"growth": 0.4, "efficiency": 0.3, "leisure": 0.3},
                substeps=["identify improvement areas", "research methods", "implement systems", "measure effectiveness"]
            )
        ]
        
        for goal in medium_goals:
            self.add_goal(goal)
        
        # Long term goals
        long_goals = [
            Goal(
                id="g_career_fulfillment_balance",
                horizon=GoalHorizon.LONG,
                description="Build a fulfilling career that provides financial security and work-life balance over next 10–15 years",
                why="Achieve professional success (growth) while maintaining personal happiness (leisure) and avoiding burnout (comfort)",
                priority=0.60,
                confidence=0.6,
                due=now + timedelta(days=3650),
                review_after="P365D",
                value_links={"growth": 0.4, "leisure": 0.3, "comfort": 0.3}
            ),
            Goal(
                id="g_life_effectiveness",
                horizon=GoalHorizon.LONG,
                description="Create life systems that support both achievement and personal wellbeing",
                why="Build sustainable success (growth) while maintaining personal fulfillment (leisure) through effective living (efficiency)",
                priority=0.65,
                confidence=0.7,
                due=now + timedelta(days=3650),
                review_after="P365D",
                value_links={"growth": 0.4, "leisure": 0.3, "efficiency": 0.3}
            )
        ]
        
        for goal in long_goals:
            self.add_goal(goal)
        
        # Set default context
        default_context = ContextFrame(
            when=now,
            where="Yale University, New Haven — rotating between Bass/Sterling, classrooms, apartment",
            what="Student day with classes, focused study sessions, gym, dinner with friends, balancing work and personal time",
            why="Complete academic work thoroughly while maintaining personal wellbeing and efficient time management",
            with_whom=["Miguel (roommate)", "Samira (classmate)", "Elise (classmate)", "RA Supervisor", "Prof. Chen"],
            constraints=[
                "RA dataset update due Monday 11:59 PM (quality work required)",
                "Econ problem set due tomorrow 5 PM (thorough completion needed)",
                "Energy dips after gym (schedule planning important)",
                "Budget-conscious but prioritize quality and personal comfort"
            ],
            opportunities=[
                "Improve study methods for better learning outcomes",
                "Plan time effectively to reduce stress",
                "Maintain social connections and personal activities",
                "Develop systems for better academic performance"
            ]
        )
        
        self.set_context(default_context)
        
        return self
