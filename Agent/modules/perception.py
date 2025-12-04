#!/usr/bin/env python3
"""
Perception Module for Agent Event Processing

Handles agent perception and interpretation of events in their environment.
"""

import os
import json
import time
import random
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple, Union
from dataclasses import dataclass, field

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

"""
Perception Module for Agent Context and Goal Management
Handles context synthesis and goal updates based on events and current state.

HOLLOWAY TEST ENHANCEMENTS:
- Enhanced memory retrieval with detailed parameter logging
- Comprehensive reflection generation using values, goals, and history
- Detailed action execution logging showing all decision factors
- Never shortens text output for holloway test mode
- Shows all memory scoring parameters, cutoff values, and math
- Ensures cosine similarity is used for vector comparisons
- Passes recent history, values, and goals to reflection
- Encourages deeper agent reflection and introspection
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import re
import json
from .intent import ContextFrame, Goal, GoalHorizon, IntentManager
from Utils.api_manager import APIManager

class Perception:
    """
    Handles agent perception, context synthesis, and goal updates.
    """
    
    def __init__(self, agent, api_key: Optional[str] = None):
        self.agent = agent
        
        # Automatically load API key from environment if not provided
        if api_key is None:
            import os
            api_key = os.getenv('OPENROUTER_KEY')
        
        self.api_manager = APIManager(api_key)
        
    def perceive_and_update(self, events: List["Event"]) -> None:
        """
        Main perception pipeline:
        1) Analyze events and detect triggers
        2) Store events with tags
        3) Synthesize context using LLM
        4) Generate personal reflection
        5) Plan action based on reflection
        6) Update goals based on new context
        """
        if not events:
            return
            
        # 1) Detect triggers (fast rules)
        flags = self._detect_triggers(events)
        
        # 2) Store events with tags
        self._store_events_with_tags(events, flags)
        
        # 3) Synthesize context using LLM
        new_context = self._synthesize_context(events, flags)
        if new_context:
            self.agent.intent_manager.set_context(new_context)
        else:
            # Fallback: create basic context from events
            print("LLM context synthesis failed, using fallback context")
            new_context = self._create_fallback_context(events, flags)
            if new_context:
                self.agent.intent_manager.set_context(new_context)
        
        # 4) Generate personal reflection for each event
        for event in events:
            # Get comprehensive context for reflection
            recent_history = self._get_recent_history(event)
            current_values = self._get_current_values()
            current_goals = self._get_current_goals()
            
            reflection = self._generate_personal_reflection(
                event, new_context, flags, recent_history, current_values, current_goals
            )
            print(f"Agent reflection: {reflection}")
            
            # 5) Update mood based on event and reflection
            if hasattr(self.agent, 'update_mood'):
                # Create a perception result for mood update
                perception_result = {
                    'perception': reflection,
                    'impact_score': 5,  # Default impact score
                    'should_analyze': True,
                    'analysis_type': 'event_reflection'
                }
                
                # Update mood with the event and reflection
                mood_updated = self.agent.update_mood(event, perception_result)
                if mood_updated:
                    print("Mood updated based on event reflection")
                else:
                    print("Mood update failed")
            else:
                print("No mood update system available")
            
            # 6) Plan action based on reflection
            if hasattr(self.agent, 'action_planner'):
                action = self.agent.action_planner.plan_action(
                    event=event,
                    reflection=reflection,
                    context=new_context,
                    recent_memories=self._get_recent_memories(event)
                )
                print(f"Agent action: {action}")
                
                # 7) Execute the action (print what agent will do)
                self._execute_action(event, action, reflection, new_context, recent_history, current_values, current_goals)
            else:
                print("No action planner available")
                # Still execute a basic action
                basic_action = "I need to assess the situation and determine my next steps."
                self._execute_action(event, basic_action, reflection, new_context, recent_history, current_values, current_goals)
        
        # 6) Update goals based on context
        self._update_goals_from_context(flags, new_context)
    
    def _detect_triggers(self, events: List["Event"]) -> Dict[str, Any]:
        """
        Detect triggers using fast rules before LLM processing.
        """
        flags = {
            'deadlines': [],
            'social_events': [],
            'academic_events': [],
            'health_events': [],
            'mood_shifts': []
        }
        
        for event in events:
            content_lower = event.content.lower()
            
            # Deadline detection
            deadline_keywords = ['due', 'deadline', 'by', 'until', 'before']
            if any(keyword in content_lower for keyword in deadline_keywords):
                flags['deadlines'].append({
                    'event': event,
                    'urgency': 'high' if any(word in content_lower for word in ['urgent', 'asap', 'immediately']) else 'normal'
                })
            
            # Social event detection
            social_keywords = ['friend', 'roommate', 'classmate', 'dinner', 'lunch', 'meeting', 'group']
            if any(keyword in content_lower for keyword in social_keywords):
                flags['social_events'].append(event)
            
            # Academic event detection
            academic_keywords = ['class', 'lecture', 'study', 'homework', 'assignment', 'exam', 'test', 'problem set']
            if any(keyword in content_lower for keyword in academic_keywords):
                flags['academic_events'].append(event)
            
            # Health event detection
            health_keywords = ['gym', 'workout', 'exercise', 'tired', 'fatigue', 'energy', 'health']
            if any(keyword in content_lower for keyword in health_keywords):
                flags['health_events'].append(event)
            
            # Mood shift detection
            mood_keywords = ['happy', 'sad', 'excited', 'worried', 'stressed', 'relaxed', 'frustrated']
            if any(keyword in content_lower for keyword in mood_keywords):
                flags['mood_shifts'].append(event)
        
        return flags
    
    def _store_events_with_tags(self, events: List["Event"], flags: Dict[str, Any]):
        """
        Store events with appropriate tags for memory management.
        """
        for event in events:
            # Add tags based on flags
            tags = []
            
            if event in [f['event'] for f in flags['deadlines']]:
                tags.append('deadline')
            
            if event in flags['social_events']:
                tags.append('social')
            
            if event in flags['academic_events']:
                tags.append('academic')
            
            if event in flags['health_events']:
                tags.append('health')
            
            if event in flags['mood_shifts']:
                tags.append('mood')
            
            # Store with tags if memory manager is available
            if hasattr(self.agent, 'memory_manager'):
                # TODO: integrate with memory manager
                print(f"Event tagged: {event.content[:50]}... -> {tags}")
    
    def _synthesize_context(self, events: List["Event"], flags: Dict[str, Any]) -> Optional[ContextFrame]:
        """
        Synthesize current context using LLM reasoning.
        """
        try:
            # Get recent events (last 3 hours worth)
            recent_events = events[-5:] if len(events) > 5 else events
            
            # Get current goals for context
            immediate_goals = self.agent.intent_manager.get_goals_by_horizon(GoalHorizon.IMMEDIATE)
            short_goals = self.agent.intent_manager.get_goals_by_horizon(GoalHorizon.SHORT)
            
            # Get current mood if available
            mood_context = ""
            if hasattr(self.agent, 'get_mood_context'):
                mood_context = self.agent.get_mood_context()
            
            # Format events for prompt
            events_text = "\n".join([f"- {event.content}" for event in recent_events])
            
            # Format goals for prompt
            goals_text = ""
            if immediate_goals:
                goals_text += "Immediate goals:\n" + "\n".join([f"- {g.description}" for g in immediate_goals[:3]])
            if short_goals:
                goals_text += "\nShort-term goals:\n" + "\n".join([f"- {g.description}" for g in short_goals[:3]])
            
            # Construct the context synthesis prompt
            prompt = f"""You are a context synthesis system for a college student agent. Your task is to analyze recent events and create a structured context summary.

RECENT EVENTS:
{events_text}

CURRENT GOALS:
{goals_text if goals_text else "No specific goals"}

MOOD CONTEXT:
{mood_context if mood_context else "No mood information"}

INSTRUCTIONS:
1. Analyze the events and goals to understand the current situation
2. Create a concise context summary based on the events and goals provided
3. Return ONLY a valid JSON object with the exact structure shown below
4. Do not include any explanatory text, just the JSON
5. Make sure all required fields are filled with relevant information
6. Use the example format as a template, changing only the content values

REQUIRED OUTPUT FORMAT (copy this exactly and fill in the values):
{{
  "where": "brief location description (e.g., 'Yale Library, study carrel')",
  "what": "current activity summary (e.g., 'Studying economics, working on problem set')",
  "why": "immediate purpose/goal (e.g., 'Complete homework before deadline')",
  "with_whom": ["person1", "person2"],
  "constraints": ["constraint1", "constraint2"],
  "opportunities": ["opportunity1", "opportunity2"]
}}

EXAMPLE OUTPUT:
{{
  "where": "Yale Library, study carrel",
  "what": "Studying economics, working on problem set",
  "why": "Complete homework before deadline",
  "with_whom": ["alone"],
  "constraints": ["deadline in 2 hours", "tired after gym"],
  "opportunities": ["ask Samira for help", "take short break"]
}}

IMPORTANT: Return ONLY the JSON object, no other text.
Your response should look exactly like the example above, with only the content values changed."""

            # Get LLM response
            try:
                response, _, model_name, _ = self.api_manager.make_request(
                    prompt=prompt,
                    intelligence_level=3,  # Use highest intelligence for context synthesis
                    max_tokens=400,
                    temperature=0.3
                )
                
                if not response or response.strip() == "":
                    print("LLM returned empty response")
                    return None
                
                # Parse JSON response
                try:
                    # First try to parse the entire response as JSON
                    context_data = json.loads(response.strip())
                except json.JSONDecodeError:
                    # If that fails, try to extract JSON from the response
                    json_match = re.search(r'\{.*\}', response, re.DOTALL)
                    if json_match:
                        try:
                            context_data = json.loads(json_match.group())
                        except json.JSONDecodeError:
                            print(f"Failed to parse extracted JSON: {json_match.group()}")
                            return None
                    else:
                        print(f"Could not extract JSON from LLM response: {response[:200]}...")
                        return None
                
                # Validate required fields
                required_fields = ['where', 'what', 'why']
                missing_fields = [field for field in required_fields if field not in context_data]
                if missing_fields:
                    print(f"Missing required fields in LLM response: {missing_fields}")
                    return None
                
                # Create ContextFrame with defaults for optional fields
                context = ContextFrame(
                    when=get_current_datetime(),
                    where=context_data.get('where', 'Unknown location'),
                    what=context_data.get('what', 'Unknown activity'),
                    why=context_data.get('why', 'Unknown purpose'),
                    with_whom=context_data.get('with_whom', []),
                    constraints=context_data.get('constraints', []),
                    opportunities=context_data.get('opportunities', [])
                )
                
                print(f"✓ Context synthesized successfully using {model_name}")
                return context
                    
            except json.JSONDecodeError as e:
                print(f"Failed to parse JSON response: {e}")
                print(f"Response was: {response[:200]}...")
                return None
            except Exception as e:
                print(f"Error in LLM context synthesis: {e}")
                
                print(f"Full traceback:")
                import traceback
                traceback.print_exc()
                return None
                
        except Exception as e:
            print(f"Error in context synthesis: {e}")
            print(f"Full traceback:")
            import traceback
            traceback.print_exc()
            return None
    
    def _create_fallback_context(self, events: List["Event"], flags: Dict[str, Any]) -> Optional[ContextFrame]:
        """
        Create a basic context when LLM synthesis fails.
        """
        try:
            if not events:
                return None
            
            # Get the most recent event
            latest_event = events[-1]
            
            # Determine location from event
            if hasattr(latest_event, 'location') and latest_event.location:
                if len(latest_event.location) >= 2:
                    where = f"{latest_event.location[-2]}, {latest_event.location[-1]}"
                else:
                    where = latest_event.location[0] if latest_event.location else "Unknown location"
            else:
                where = "Unknown location"
            
            # Determine activity from event type and content
            event_type = getattr(latest_event, 'event_type', 'unknown')
            content = getattr(latest_event, 'content', '')
            
            if event_type == 'interaction':
                what = f"Interacting with others: {content[:50]}..."
            elif event_type == 'environmental_change':
                what = f"Experiencing environmental change: {content[:50]}..."
            elif event_type == 'message':
                what = f"Receiving message: {content[:50]}..."
            else:
                what = f"{event_type.replace('_', ' ').title()}: {content[:50]}..."
            
            # Determine purpose based on event type
            if 'study' in content.lower() or 'lecture' in content.lower():
                why = "Academic activities and learning"
            elif 'gym' in content.lower() or 'workout' in content.lower():
                why = "Physical health and fitness"
            elif 'social' in content.lower() or 'friend' in content.lower():
                why = "Social interaction and relationship building"
            else:
                why = "Daily activities and routine"
            
            # Create basic context
            context = ContextFrame(
                when=get_current_datetime(),
                where=where,
                what=what,
                why=why,
                with_whom=[],
                constraints=[],
                opportunities=[]
            )
            
            print("✓ Fallback context created from event analysis")
            return context
            
        except Exception as e:
            print(f"Error creating fallback context: {e}")
            print(f"Full traceback:")
            import traceback
            traceback.print_exc()
            return None
    
    def _update_goals_from_context(self, flags: Dict[str, Any], context: Optional[ContextFrame]):
        """
        Update goals based on new context and detected triggers.
        """
        try:
            # Handle deadline triggers
            for deadline_info in flags['deadlines']:
                event = deadline_info['event']
                urgency = deadline_info['urgency']
                
                # Create or update immediate goal for deadline
                goal_id = f"g_deadline_{event.event_id}"
                existing_goal = self.agent.intent_manager.get_goal(goal_id)
                
                if not existing_goal:
                    # Create new immediate goal focused on quality and efficiency
                    new_goal = Goal(
                        id=goal_id,
                        horizon=GoalHorizon.IMMEDIATE,
                        description=f"Complete deadline thoroughly: {event.content[:50]}...",
                        why="Meet obligation with quality (reliability) while using time efficiently (efficiency) to maintain balance (leisure)",
                        priority=0.8 if urgency == 'high' else 0.7,
                        confidence=0.8,
                        due=get_current_datetime() + timedelta(hours=24 if urgency == 'high' else 72),
                        review_after="PT60M",
                        value_links={"reliability": 0.4, "efficiency": 0.3, "leisure": 0.3}
                    )
                    self.agent.intent_manager.add_goal(new_goal)
                    print(f"Created new quality-focused deadline goal: {new_goal.description}")
            
            # Handle social event triggers
            if flags['social_events']:
                # Check if we need to create social goals
                social_goals = [g for g in self.agent.intent_manager.get_goals_by_horizon(GoalHorizon.IMMEDIATE) 
                               if 'social' in g.description.lower()]
                
                if not social_goals:
                    social_goal = Goal(
                        id="g_social_connections",
                        horizon=GoalHorizon.IMMEDIATE,
                        description="Maintain social connections with friends and classmates",
                        why="Build community relationships (community) while enjoying personal time (leisure) and managing time well (efficiency)",
                        priority=0.7,
                        confidence=0.8,
                        due=get_current_datetime() + timedelta(hours=6),
                        review_after="PT120M",
                        value_links={"community": 0.4, "leisure": 0.4, "efficiency": 0.2}
                    )
                    self.agent.intent_manager.add_goal(social_goal)
                    print(f"Created new community-focused social goal: {social_goal.description}")
            
            # Handle academic event triggers
            if flags['academic_events']:
                # Check if we need to create academic goals
                academic_goals = [g for g in self.agent.intent_manager.get_goals_by_horizon(GoalHorizon.IMMEDIATE) 
                                 if any(word in g.description.lower() for word in ['study', 'homework', 'assignment'])]
                
                if not academic_goals:
                    academic_goal = Goal(
                        id="g_academic_learning",
                        horizon=GoalHorizon.IMMEDIATE,
                        description="Complete academic work thoroughly to build knowledge and skills",
                        why="Advance learning (growth) through effective study methods (efficiency) while maintaining personal time (leisure)",
                        priority=0.7,
                        confidence=0.8,
                        due=get_current_datetime() + timedelta(hours=4),
                        review_after="PT90M",
                        value_links={"growth": 0.4, "efficiency": 0.3, "leisure": 0.3}
                    )
                    self.agent.intent_manager.add_goal(academic_goal)
                    print(f"Created new learning-focused academic goal: {academic_goal.description}")
            
            # Handle health event triggers
            if flags['health_events']:
                # Check if we need to create health goals
                health_goals = [g for g in self.agent.intent_manager.get_goals_by_horizon(GoalHorizon.IMMEDIATE) 
                               if 'health' in g.description.lower() or 'energy' in g.description.lower()]
                
                if not health_goals:
                    health_goal = Goal(
                        id="g_health_wellbeing",
                        horizon=GoalHorizon.IMMEDIATE,
                        description="Maintain health and energy for optimal performance and personal comfort",
                        why="Preserve wellbeing (health) and personal comfort (comfort) for sustained success and leisure",
                        priority=0.7,
                        confidence=0.7,
                        due=get_current_datetime() + timedelta(hours=2),
                        review_after="PT60M",
                        value_links={"health": 0.4, "comfort": 0.3, "leisure": 0.3}
                    )
                    self.agent.intent_manager.add_goal(health_goal)
                    print(f"Created new wellbeing-focused health goal: {health_goal.description}")
                    
        except Exception as e:
            print(f"Error updating goals from context: {e}")
            print(f"Full traceback:")
            import traceback
            traceback.print_exc()
    
    def review_goals(self, now: datetime):
        """
        Review goals based on their review cadence.
        """
        try:
            for horizon, goals in self.agent.intent_manager.goals.items():
                for goal in goals:
                    if goal.review_after and goal.start and goal.review_after:
                        # Parse review_after (simplified - TODO: use proper ISO duration parsing)
                        if self._should_review_goal(goal, now):
                            self._reconsider_goal(goal, horizon)
        except Exception as e:
            print(f"Error reviewing goals: {e}")
            print(f"Full traceback:")
            import traceback
            traceback.print_exc()
    
    def _should_review_goal(self, goal: Goal, now: datetime) -> bool:
        """
        Check if a goal should be reviewed based on its review_after setting.
        """
        if not goal.start or not goal.review_after:
            return False
            
        # Simple parsing of review_after (PT90M = 90 minutes, P1D = 1 day, etc.)
        review_after = goal.review_after
        
        if review_after.startswith('PT'):
            # Time duration (PT90M = 90 minutes)
            if 'H' in review_after:
                hours = int(review_after.replace('PT', '').replace('H', ''))
                review_time = goal.start + timedelta(hours=hours)
            elif 'M' in review_after:
                minutes = int(review_after.replace('PT', '').replace('M', ''))
                review_time = goal.start + timedelta(minutes=minutes)
            else:
                return False
        elif review_after.startswith('P'):
            # Date duration (P1D = 1 day, P30D = 30 days, etc.)
            if 'D' in review_after:
                days = int(review_after.replace('P', '').replace('D', ''))
                review_time = goal.start + timedelta(days=days)
            else:
                return False
        else:
            return False
            
        return now >= review_time
    
    def _reconsider_goal(self, goal: Goal, horizon: GoalHorizon):
        """
        Reconsider a goal using LLM reasoning.
        """
        try:
            # Create prompt for goal reconsideration
            prompt = f"""You are a goal review system. Analyze the following goal and decide what action to take.

GOAL INFORMATION:
- Description: {goal.description}
- Why: {goal.why}
- Current Progress: {goal.progress:.1%}
- Priority: {goal.priority:.2f}
- Confidence: {goal.confidence:.2f}

INSTRUCTIONS:
1. Review the goal based on progress and current context
2. Decide on one of these actions: keep, update, done, or remove
3. If updating, provide new values for priority, progress, and/or description
4. Return ONLY a valid JSON object with the exact structure shown below

REQUIRED OUTPUT FORMAT:
{{
  "action": "keep|update|done|remove",
  "updates": {{
    "priority": 0.5,
    "progress": 0.0,
    "description": "new description if updating"
  }}
}}

EXAMPLES:
- To keep goal unchanged: {{"action": "keep", "updates": {{}}}}
- To mark as done: {{"action": "done", "updates": {{}}}}
- To update priority: {{"action": "update", "updates": {{"priority": 0.8}}}}
- To update multiple fields: {{"action": "update", "updates": {{"priority": 0.7, "progress": 0.5}}}}

IMPORTANT: Return ONLY the JSON object, no other text or explanation."""

            # Get LLM response
            response, _, model_name, _ = self.api_manager.make_request(
                prompt=prompt,
                intelligence_level=3,  # Use highest intelligence for goal reconsideration
                max_tokens=200,
                temperature=0.3
            )
            
            # Parse response
            try:
                json_match = re.search(r'\{.*\}', response, re.DOTALL)
                if json_match:
                    decision = json.loads(json_match.group())
                    action = decision.get('action', 'keep')
                    
                    if action == 'done':
                        goal.done = True
                        print(f"Goal marked as done: {goal.description}")
                    elif action == 'update':
                        updates = decision.get('updates', {})
                        self.agent.intent_manager.update_goal(goal.id, updates)
                        print(f"Goal updated: {goal.description}")
                    elif action == 'remove':
                        self.agent.intent_manager.remove_goal(goal.id)
                        print(f"Goal removed: {goal.description}")
                    # If action is 'keep', do nothing
                        
            except json.JSONDecodeError:
                print(f"Could not parse goal reconsideration response: {response}")
                
        except Exception as e:
            print(f"Error reconsidering goal: {e}")
            print(f"Full traceback:")
            import traceback
            traceback.print_exc()

    def _generate_personal_reflection(self, event: "Event", context: ContextFrame, flags: Dict[str, Any], recent_history: List[str], current_values: Dict[str, float], current_goals: Dict[str, List[str]]) -> str:
        """
        Generate personal reflection on an event considering memories, goals, values, and context.
        """
        try:
            # Get relevant memories if available
            relevant_memories = self._get_relevant_memories(event)
            
            # Format goals for prompt
            goals_text = ""
            for horizon, goal_list in current_goals.items():
                if goal_list:
                    goals_text += f"\n{horizon.title()} goals:\n" + "\n".join([f"- {g}" for g in goal_list[:3]])
            
            # Format values for prompt
            values_text = ""
            if current_values:
                sorted_values = sorted(current_values.items(), key=lambda x: x[1], reverse=True)
                values_text = "\n".join([f"- {name}: {weight:.2f}" for name, weight in sorted_values[:5]])
            
            # Format memories for prompt
            memories_text = ""
            if relevant_memories:
                memories_text = "\n".join([f"- {memory}" for memory in relevant_memories[:3]])
            else:
                memories_text = "No relevant memories found"
            
            # Format recent history for prompt
            history_text = ""
            if recent_history:
                history_text = "\n".join([f"- {memory}" for memory in recent_history[:5]])
            else:
                history_text = "No recent history available"
            
            # Create enhanced reflection prompt
            prompt = f"""You are a college student agent reflecting deeply on an event that just happened. Give a comprehensive, introspective reflection on how this event affects you personally.

EVENT THAT OCCURRED:
{event.content}

CURRENT CONTEXT:
- Where: {context.where}
- What: {context.what}
- Why: {context.why}
- Constraints: {', '.join(context.constraints) if context.constraints else 'none'}
- Opportunities: {', '.join(context.opportunities) if context.opportunities else 'none'}

CURRENT VALUES (in order of importance):
{values_text if values_text else "No values defined"}

CURRENT GOALS:
{goals_text if goals_text else "No specific goals"}

RELEVANT MEMORIES:
{memories_text}

RECENT HISTORY:
{history_text}

TASK: Reflect deeply and personally on this event. Consider:

1. **Personal Impact**: How does this event affect you emotionally, mentally, and physically?
2. **Value Alignment**: How does this event align with or challenge your core values?
3. **Goal Relevance**: How does this event relate to your current goals and aspirations?
4. **Memory Connections**: What does this remind you of from your past experiences?
5. **Future Implications**: How might this event influence your future decisions and plans?
6. **Personal Growth**: What can you learn from this situation about yourself?
7. **Value Conflicts**: Are there any internal conflicts between your values in this situation?
8. **Personal Patterns**: Does this reveal any recurring patterns in your behavior or thinking?

Write this as a deep, introspective reflection in first person, as if you're having a thoughtful conversation with yourself about what just happened and what it means for you personally.

EXAMPLE OUTPUT:
"This deadline reminder triggers a complex mix of emotions in me. On one hand, I feel the familiar pressure to perform well academically, which aligns with my value of growth. But I also notice a rising anxiety that reminds me of past experiences where I've sacrificed my personal wellbeing for academic achievement. This reveals a tension between my values of growth and leisure - I want to learn and succeed, but I also need to maintain balance. Looking at my recent history, I see I've been working very hard and might be approaching burnout. This event is a wake-up call that I need to reassess how I'm balancing my various values and goals."

IMPORTANT: Return ONLY the personal reflection, no other text or explanation. Make this reflection comprehensive and deeply personal."""

            # Get LLM response
            try:
                response, _, model_name, _ = self.api_manager.make_request(
                    prompt=prompt,
                    intelligence_level=3,  # Use highest intelligence for deep personal reflection
                    max_tokens=500,  # Increased for more comprehensive reflection
                    temperature=0.7  # Higher temperature for more personal, creative reflection
                )
                
                if not response or response.strip() == "":
                    return "I need to think about this event more deeply to understand how it affects me personally and what it means for my values and goals."
                
                # Clean the response
                reflection = response.strip()
                # Remove quotes if present
                if reflection.startswith('"') and reflection.endswith('"'):
                    reflection = reflection[1:-1]
                if reflection.startswith("'") and reflection.endswith("'"):
                    reflection = reflection[1:-1]
                
                return reflection
                
            except Exception as e:
                print(f"Warning: LLM reflection generation failed: {e}")
                print(f"Full traceback:")
                import traceback
                traceback.print_exc()
                # Fallback to enhanced reflection
                return self._get_enhanced_fallback_reflection(event, context, current_values, current_goals)
                
        except Exception as e:
            print(f"Error in reflection generation: {e}")
            print(f"Full traceback:")
            import traceback
            traceback.print_exc()
            return "I need to process this event more deeply to understand how it affects me personally and what it means for my values and goals."
    
    def _get_enhanced_fallback_reflection(self, event: "Event", context: ContextFrame, current_values: Dict[str, float], current_goals: Dict[str, List[str]]) -> str:
        """Generate an enhanced fallback reflection when LLM fails."""
        event_type = getattr(event, 'event_type', 'unknown')
        
        # Create reflection based on values and goals
        reflection_parts = []
        
        if event_type == 'deadline':
            reflection_parts.append("This deadline is important and I need to plan my time carefully to meet it.")
            if current_values.get('efficiency', 0) > 0.5:
                reflection_parts.append("My value of efficiency suggests I should approach this systematically.")
            if current_values.get('growth', 0) > 0.5:
                reflection_parts.append("This aligns with my growth value - an opportunity to improve my skills.")
        elif event_type == 'social':
            reflection_parts.append("This social interaction is valuable for building relationships and community.")
            if current_values.get('community', 0) > 0.5:
                reflection_parts.append("This connects to my community value and desire to build connections.")
        elif event_type == 'academic':
            reflection_parts.append("This academic task will help me learn and progress toward my goals.")
            if current_values.get('growth', 0) > 0.5:
                reflection_parts.append("This directly supports my growth value and learning objectives.")
        elif event_type == 'health':
            reflection_parts.append("I need to pay attention to my health and energy levels.")
            if current_values.get('health', 0) > 0.5:
                reflection_parts.append("This reminds me of my health value and the importance of self-care.")
        else:
            reflection_parts.append("This event requires my attention and I should consider how to respond appropriately.")
        
        # Add goal-related reflection
        if current_goals.get('immediate'):
            reflection_parts.append(f"I should consider how this relates to my immediate goals: {', '.join(current_goals['immediate'][:2])}.")
        
        return " ".join(reflection_parts)
    
    def _get_relevant_memories(self, event: "Event") -> List[str]:
        """Get memories relevant to the current event with detailed logging."""
        if not hasattr(self.agent, 'memory_manager'):
            print("HOLLOWAY TEST: No memory manager available for memory retrieval")
            return []
        
        try:
            print(f"\n=== HOLLOWAY TEST: MEMORY RETRIEVAL DETAILS ===")
            print(f"Event: {event.content}")
            print(f"Event type: {event.event_type}")
            print(f"Environment: {event.environment}")
            print(f"Location: {event.location}")
            
            # Memory retrieval parameters
            k = 3  # Number of similar memories to retrieve
            salience_param = 0.5  # Weight for semantic similarity
            importance_param = 0.5  # Weight for importance
            time_decay_param = 0.8  # Weight for recency decay
            
            print(f"\nMEMORY RETRIEVAL PARAMETERS:")
            print(f"- k (number of memories): {k}")
            print(f"- Salience parameter (semantic similarity weight): {salience_param}")
            print(f"- Importance parameter (importance weight): {importance_param}")
            print(f"- Time decay parameter (recency weight): {time_decay_param}")
            
            # Get similar memories for context
            print(f"\nSEARCHING FOR SIMILAR MEMORIES...")
            similar_memories = self.agent.memory_manager.get_similar_memories_for_context(event, k=k)
            
            if similar_memories:
                print(f"Found {len(similar_memories)} similar memories")
                
                # Extract memory content and show detailed scoring
                memory_contents = []
                for i, (memory, score) in enumerate(similar_memories, 1):
                    if isinstance(memory, str):
                        content = memory
                    elif hasattr(memory, 'content'):
                        content = memory.content
                    else:
                        content = str(memory)
                    
                    print(f"\nMEMORY {i}:")
                    print(f"- Content: {content}")
                    print(f"- Similarity Score: {score:.6f}")
                    
                    # Show the math behind the score (if available)
                    if hasattr(memory, 'impact_score'):
                        importance = memory.impact_score / 10.0
                        print(f"- Impact Score: {memory.impact_score}/10")
                        print(f"- Normalized Importance: {importance:.3f}")
                        
                        # Calculate time decay if timestamp is available
                        if hasattr(memory, 'timestamp'):
                            from datetime import datetime
                            current_time = get_current_datetime()
                            time_diff = (current_time - memory.timestamp).total_seconds()
                            recency_decay = 1.0 / (1.0 + time_diff / time_decay_param)
                            print(f"- Time Difference: {time_diff:.1f} seconds")
                            print(f"- Recency Decay: {recency_decay:.6f}")
                            
                            # Show the scoring equation
                            print(f"- SCORING EQUATION:")
                            print(f"  Score = {salience_param:.1f} × {score:.6f} + {time_decay_param:.1f} × {recency_decay:.6f} + {importance_param:.1f} × {importance:.3f}")
                            calculated_score = salience_param * score + time_decay_param * recency_decay + importance_param * importance
                            print(f"  Calculated Score = {calculated_score:.6f}")
                    
                    memory_contents.append(content)
                
                print(f"\n=== MEMORY RETRIEVAL COMPLETE ===")
                return memory_contents
            else:
                print("No similar memories found")
                print("This could mean:")
                print("- No memories exist yet")
                print("- Memory similarity threshold not met")
                print("- Memory system not properly configured")
                print("=== MEMORY RETRIEVAL COMPLETE ===")
                return []
                
        except Exception as e:
            print(f"HOLLOWAY TEST: Error retrieving relevant memories: {e}")
            print(f"Full traceback:")
            import traceback
            traceback.print_exc()
            print("=== MEMORY RETRIEVAL FAILED ===")
            return []
    
    def _get_recent_memories(self, event: "Event") -> List[str]:
        """Get recent memories for action planning context with detailed logging."""
        if not hasattr(self.agent, 'memory_manager'):
            print("HOLLOWAY TEST: No memory manager available for recent memory retrieval")
            return []
        
        try:
            print(f"\n=== HOLLOWAY TEST: RECENT MEMORY RETRIEVAL DETAILS ===")
            
            # Memory retrieval parameters for recent memories
            k = 5  # Number of recent memories to retrieve
            salience_param = 0.5  # Weight for semantic similarity
            importance_param = 0.5  # Weight for importance
            time_decay_param = 0.8  # Weight for recency decay
            
            print(f"RECENT MEMORY RETRIEVAL PARAMETERS:")
            print(f"- k (number of memories): {k}")
            print(f"- Salience parameter (semantic similarity weight): {salience_param}")
            print(f"- Importance parameter (importance weight): {importance_param}")
            print(f"- Time decay parameter (recency weight): {time_decay_param}")
            
            print(f"\nSEARCHING FOR RECENT MEMORIES...")
            # Get recent memories (last 5)
            recent_memories = self.agent.memory_manager.get_scored_memories(
                current_context="recent events",
                k=k,
                salience_param=salience_param,
                importance_param=importance_param,
                time_decay_param=time_decay_param
            )
            
            if recent_memories:
                print(f"✓ Found {len(recent_memories)} recent memories")
                
                # Extract memory content and show detailed scoring
                memory_contents = []
                for i, (memory, score) in enumerate(recent_memories, 1):
                    if hasattr(memory, 'content'):
                        content = memory.content
                    else:
                        content = str(memory)
                    
                    print(f"\nRECENT MEMORY {i}:")
                    print(f"- Content: {content}")
                    print(f"- Final Score: {score:.6f}")
                    
                    # Show the math behind the score (if available)
                    if hasattr(memory, 'impact_score'):
                        importance = memory.impact_score / 10.0
                        print(f"- Impact Score: {memory.impact_score}/10")
                        print(f"- Normalized Importance: {importance:.3f}")
                        
                        # Calculate time decay if timestamp is available
                        if hasattr(memory, 'timestamp'):
                            from datetime import datetime
                            current_time = get_current_datetime()
                            time_diff = (current_time - memory.timestamp).total_seconds()
                            recency_decay = 1.0 / (1.0 + time_diff / time_decay_param)
                            print(f"- Time Difference: {time_diff:.1f} seconds")
                            print(f"- Recency Decay: {recency_decay:.6f}")
                            
                            # Show the scoring equation
                            print(f"- SCORING EQUATION:")
                            print(f"  Score = {salience_param:.1f} × semantic_similarity + {time_decay_param:.1f} × {recency_decay:.6f} + {importance_param:.1f} × {importance:.3f}")
                            print(f"  Note: semantic_similarity calculated using cosine similarity between vectors")
                    
                    memory_contents.append(content)
                
                print(f"\n=== RECENT MEMORY RETRIEVAL COMPLETE ===")
                return memory_contents
            else:
                print("No recent memories found")
                print("This could mean:")
                print("- No memories exist yet")
                print("- Memory scoring threshold not met")
                print("- Memory system not properly configured")
                print("=== RECENT MEMORY RETRIEVAL COMPLETE ===")
                return []
                
        except Exception as e:
            print(f"HOLLOWAY TEST: Error retrieving recent memories: {e}")
            print(f"Full traceback:")
            import traceback
            traceback.print_exc()
            print("=== RECENT MEMORY RETRIEVAL FAILED ===")
            return []

    def _get_recent_history(self, event: "Event") -> List[str]:
        """Get recent history for enhanced reflection context."""
        try:
            if hasattr(self.agent, 'memory_manager'):
                # Get recent memories (last 10)
                recent_memories = self.agent.memory_manager.get_scored_memories(
                    current_context="recent events",
                    k=10,
                    salience_param=0.5,
                    importance_param=0.5,
                    time_decay_param=0.8
                )
                
                if recent_memories:
                    return [memory.content if hasattr(memory, 'content') else str(memory) 
                           for memory, _ in recent_memories]
            return []
        except Exception as e:
            print(f"Warning: Failed to retrieve recent history: {e}")
            print(f"Full traceback:")
            import traceback
            traceback.print_exc()
            return []
    
    def _get_current_values(self) -> Dict[str, float]:
        """Get current agent values for reflection context."""
        try:
            if hasattr(self.agent, 'intent_manager'):
                return {name: value.weight for name, value in self.agent.intent_manager.values.items()}
            return {}
        except Exception as e:
            print(f"Warning: Failed to retrieve current values: {e}")
            print(f"Full traceback:")
            import traceback
            traceback.print_exc()
            return {}
    
    def _get_current_goals(self) -> Dict[str, List[str]]:
        """Get current agent goals for reflection context."""
        try:
            if hasattr(self.agent, 'intent_manager'):
                goals = {}
                for horizon in self.agent.intent_manager.goals:
                    goals[horizon.value] = [g.description for g in self.agent.intent_manager.goals[horizon]]
                return goals
            return {}
        except Exception as e:
            print(f"Warning: Failed to retrieve current goals: {e}")
            print(f"Full traceback:")
            import traceback
            traceback.print_exc()
            return {}

    def _execute_action(self, event: "Event", action: str, reflection: str, context: ContextFrame, recent_history: List[str], current_values: Dict[str, float], current_goals: Dict[str, List[str]]):
        """
        Execute the agent's action by printing detailed information about what the agent will do.
        Shows all the context and reasoning behind the action decision.
        """
        print(f"\n=== HOLLOWAY TEST: AGENT ACTION EXECUTION ===")
        print(f"EVENT PROCESSED:")
        print(f"- Content: {event.content}")
        print(f"- Type: {event.event_type}")
        print(f"- Environment: {event.environment}")
        print(f"- Location: {event.location}")
        print(f"- Timestamp: {event.timestamp}")
        
        print(f"\nAGENT'S REFLECTION:")
        print(f"{reflection}")
        
        print(f"\nPLANNED ACTION:")
        print(f"{action}")
        
        print(f"\nCONTEXT FOR ACTION:")
        print(f"- Where: {context.where}")
        print(f"- What: {context.what}")
        print(f"- Why: {context.why}")
        print(f"- With whom: {', '.join(context.with_whom) if context.with_whom else 'alone'}")
        print(f"- Constraints: {', '.join(context.constraints) if context.constraints else 'none'}")
        print(f"- Opportunities: {', '.join(context.opportunities) if context.opportunities else 'none'}")
        
        print(f"\nCURRENT VALUES (influencing decision):")
        if current_values:
            sorted_values = sorted(current_values.items(), key=lambda x: x[1], reverse=True)
            for name, weight in sorted_values:
                print(f"- {name}: {weight:.3f}")
        else:
            print("- No values defined")
        
        print(f"\nCURRENT GOALS (influencing decision):")
        for horizon, goal_list in current_goals.items():
            if goal_list:
                print(f"- {horizon.title()}:")
                for goal in goal_list[:3]:  # Show top 3 goals per horizon
                    print(f"  * {goal}")
        
        print(f"\nRECENT HISTORY (influencing decision):")
        if recent_history:
            for i, memory in enumerate(recent_history[:5], 1):  # Show top 5 recent memories
                print(f"- {i}. {memory}")  # Show full memory content, no truncation
        else:
            print("- No recent history available")
        
        print(f"\nACTION RATIONALE:")
        print(f"The agent decided to: {action}")
        print(f"This decision was based on:")
        print(f"1. Personal reflection on the event")
        print(f"2. Current context and situation")
        print(f"3. Personal values and priorities")
        print(f"4. Current goals and objectives")
        print(f"5. Relevant memories and past experiences")
        
        print(f"\nNEXT STEPS:")
        print(f"The agent will now proceed to: {action}")
        print(f"This action aligns with the agent's values and goals as reflected in the decision-making process above.")
        
        # Actually take the action
        action_result = self.take_action(event, action, context)
        
        print(f"\nACTION RESULT: {action_result}")
        print(f"\n=== ACTION EXECUTION COMPLETE ===\n")
    
    def take_action(self, event: "Event", action: str, context: ContextFrame) -> str:
        """
        Take an action based on the agent's decision.
        
        Args:
            event: The event that triggered the action
            action: The action the agent decided to take
            context: Current context for the action
            
        Returns:
            String describing the result of the action
        """
        print(f"\n=== AGENT TAKING ACTION ===")
        print(f"Event: {event.content}")
        print(f"Action: {action}")
        print(f"Context: {context.where} - {context.what}")
        
        # TODO: implement actual action execution logic
        action_result = f"Agent performed action: {action}"
        print(f"Action Result: {action_result}")
        print(f"=== ACTION COMPLETED ===\n")
        
        return action_result
    
    def get_action_outline(self) -> Dict[str, Any]:
        """
        Get an outline of available actions the agent can take.
        
        Returns:
            Dictionary outlining available action categories and types
        """
        action_outline = {
            "movement": {
                "description": "Physical movement and location changes",
                "actions": [
                    "move_to_location",
                    "change_environment", 
                    "travel_between_places"
                ]
            },
            "interaction": {
                "description": "Social and communication actions",
                "actions": [
                    "speak_with_person",
                    "send_message",
                    "join_conversation",
                    "leave_conversation"
                ]
            },
            "task_execution": {
                "description": "Performing specific tasks and activities",
                "actions": [
                    "start_activity",
                    "continue_activity",
                    "complete_activity",
                    "switch_activities"
                ]
            },
            "planning": {
                "description": "Planning and decision-making actions",
                "actions": [
                    "create_plan",
                    "modify_plan",
                    "prioritize_tasks",
                    "schedule_activities"
                ]
            },
            "self_management": {
                "description": "Personal and health-related actions",
                "actions": [
                    "take_break",
                    "eat_meal",
                    "exercise",
                    "rest"
                ]
            },
            "learning": {
                "description": "Educational and skill-building actions",
                "actions": [
                    "study_topic",
                    "practice_skill",
                    "ask_question",
                    "research_subject"
                ]
            }
        }
        
        return action_outline
