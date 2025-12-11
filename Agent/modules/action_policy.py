#!/usr/bin/env python3
"""
Action Policy Module
Provides action planning functionality for agents based on their goals and values.
"""

import random
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta

class ActionPolicy:
    """
    Manages action planning for agents based on their current goals, values, and context.
    """
    
    def __init__(self, agent):
        """
        Initialize the action policy module.
        
        Args:
            agent: The agent instance this policy belongs to
        """
        self.agent = agent
        self.last_action_time = datetime.now()
        self.action_history = []
        
        # Default action templates
        self.default_actions = [
            {
                'name': 'study_session',
                'description': 'Focus on academic work and study',
                'time': 120,  # minutes
                'cost': 0.0,
                'risk': 0.1,
                'category': 'academic'
            },
            {
                'name': 'social_interaction',
                'description': 'Engage with peers and build relationships',
                'time': 60,
                'cost': 5.0,
                'risk': 0.2,
                'category': 'social'
            },
            {
                'name': 'physical_activity',
                'description': 'Exercise or participate in sports',
                'time': 90,
                'cost': 0.0,
                'risk': 0.1,
                'category': 'health'
            },
            {
                'name': 'personal_reflection',
                'description': 'Time for self-reflection and goal setting',
                'time': 30,
                'cost': 0.0,
                'risk': 0.0,
                'category': 'personal'
            },
            {
                'name': 'leisure_activity',
                'description': 'Engage in recreational activities',
                'time': 60,
                'cost': 10.0,
                'risk': 0.1,
                'category': 'leisure'
            }
        ]
    
    def get_action_plan(self) -> Optional[Dict[str, Any]]:
        """
        Get the best action plan based on current goals and values.
        
        Returns:
            Dict[str, Any]: Action plan with name, description, time, cost, risk, and score
        """
        try:
            # Check if agent has intent manager
            if not hasattr(self.agent, 'intent_manager') or not self.agent.intent_manager:
                return self._get_default_action_plan()
            
            # Get current goals and values
            current_goals = self._get_current_goals()
            current_values = self._get_current_values()
            current_context = self._get_current_context()
            
            # Score available actions
            scored_actions = self._score_actions(current_goals, current_values, current_context)
            
            if not scored_actions:
                return self._get_default_action_plan()
            
            # Select best action
            best_action = max(scored_actions, key=lambda x: x['score'])
            
            # Update action history
            self.action_history.append({
                'action': best_action['name'],
                'timestamp': datetime.now(),
                'score': best_action['score']
            })
            
            # Keep only last 10 actions
            if len(self.action_history) > 10:
                self.action_history = self.action_history[-10:]
            
            return best_action
            
        except Exception as e:
            print(f"Error generating action plan: {e}")
            return self._get_default_action_plan()
    
    def _get_current_goals(self) -> List[Dict[str, Any]]:
        """Get current active goals from intent manager."""
        try:
            if not self.agent.intent_manager:
                return []
            
            goals = []
            for horizon, horizon_goals in self.agent.intent_manager.goals.items():
                for goal in horizon_goals:
                    if not goal.done:
                        goals.append({
                            'description': goal.description,
                            'priority': goal.priority,
                            'progress': goal.progress,
                            'horizon': horizon.value
                        })
            
            return goals
        except Exception:
            return []
    
    def _get_current_values(self) -> Dict[str, float]:
        """Get current values from intent manager."""
        try:
            if not self.agent.intent_manager:
                return {}
            
            return {value.name: value.weight for value in self.agent.intent_manager.values.values()}
        except Exception:
            return {}
    
    def _get_current_context(self) -> Optional[Dict[str, Any]]:
        """Get current context from intent manager."""
        try:
            if not self.agent.intent_manager or not self.agent.intent_manager.context:
                return None
            
            context = self.agent.intent_manager.context
            return {
                'where': context.where,
                'what': context.what,
                'why': context.why,
                'constraints': context.constraints,
                'opportunities': context.opportunities
            }
        except Exception:
            return None
    
    def _score_actions(self, goals: List[Dict[str, Any]], values: Dict[str, float], context: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Score available actions based on goals, values, and context."""
        scored_actions = []
        
        for action in self.default_actions:
            score = 0.0
            
            # Base score from action category
            score += self._get_category_score(action['category'], values)
            
            # Goal alignment score
            score += self._get_goal_alignment_score(action, goals)
            
            # Context appropriateness score
            score += self._get_context_score(action, context)
            
            # Time availability score
            score += self._get_time_score(action)
            
            # Cost and risk adjustment
            score -= action['cost'] * 0.1  # Reduce score for higher cost
            score -= action['risk'] * 0.5  # Reduce score for higher risk
            
            # Add some randomness to avoid always choosing the same action
            score += random.uniform(-0.1, 0.1)
            
            scored_action = action.copy()
            scored_action['score'] = max(0.0, score)  # Ensure non-negative score
            scored_actions.append(scored_action)
        
        return scored_actions
    
    def _get_category_score(self, category: str, values: Dict[str, float]) -> float:
        """Get score based on how well action category aligns with values."""
        category_value_mapping = {
            'academic': ['academic_excellence', 'learning', 'intellectual_growth'],
            'social': ['social_connection', 'community', 'relationships'],
            'health': ['physical_wellbeing', 'health', 'fitness'],
            'personal': ['self_improvement', 'reflection', 'personal_growth'],
            'leisure': ['enjoyment', 'recreation', 'balance']
        }
        
        if category not in category_value_mapping:
            return 0.0
        
        relevant_values = category_value_mapping[category]
        score = 0.0
        
        for value_name in relevant_values:
            if value_name in values:
                score += values[value_name] * 0.3
        
        return score
    
    def _get_goal_alignment_score(self, action: Dict[str, Any], goals: List[Dict[str, Any]]) -> float:
        """Get score based on how well action aligns with current goals."""
        if not goals:
            return 0.0
        
        score = 0.0
        
        for goal in goals:
            goal_text = goal['description'].lower()
            action_text = action['description'].lower()
            
            # Simple keyword matching
            if any(word in goal_text for word in action_text.split()):
                score += goal['priority'] * 0.2
            
            # Check for academic alignment
            if goal['horizon'] == 'academic' and action['category'] == 'academic':
                score += goal['priority'] * 0.3
        
        return score
    
    def _get_context_score(self, action: Dict[str, Any], context: Optional[Dict[str, Any]]) -> float:
        """Get score based on context appropriateness."""
        if not context:
            return 0.0
        
        score = 0.0
        
        # Location-based scoring
        where = context.get('where', '').lower()
        if 'library' in where and action['category'] == 'academic':
            score += 0.5
        elif 'gym' in where and action['category'] == 'health':
            score += 0.5
        elif 'dorm' in where and action['category'] == 'personal':
            score += 0.3
        
        # Constraint-based scoring
        constraints = context.get('constraints', [])
        if 'time_limited' in constraints and action['time'] <= 60:
            score += 0.3
        if 'low_cost' in constraints and action['cost'] <= 5.0:
            score += 0.3
        
        return score
    
    def _get_time_score(self, action: Dict[str, Any]) -> float:
        """Get score based on time availability."""
        # Prefer actions that don't take too long
        if action['time'] <= 60:
            return 0.2
        elif action['time'] <= 120:
            return 0.1
        else:
            return 0.0
    
    def _get_default_action_plan(self) -> Dict[str, Any]:
        """Get a default action plan when intent system is not available."""
        # Randomly select a default action
        action = random.choice(self.default_actions)
        
        # Add a default score
        action_with_score = action.copy()
        action_with_score['score'] = random.uniform(0.5, 1.0)
        
        return action_with_score
    
    def get_action_history(self) -> List[Dict[str, Any]]:
        """Get recent action history."""
        return self.action_history.copy()
    
    def get_action_statistics(self) -> Dict[str, Any]:
        """Get statistics about action choices."""
        if not self.action_history:
            return {}
        
        action_counts = {}
        total_score = 0.0
        
        for entry in self.action_history:
            action_name = entry['action']
            action_counts[action_name] = action_counts.get(action_name, 0) + 1
            total_score += entry['score']
        
        return {
            'total_actions': len(self.action_history),
            'action_counts': action_counts,
            'average_score': total_score / len(self.action_history) if self.action_history else 0.0,
            'most_common_action': max(action_counts.items(), key=lambda x: x[1])[0] if action_counts else None
        }
