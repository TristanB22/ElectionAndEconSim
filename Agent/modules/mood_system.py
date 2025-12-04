#!/usr/bin/env python3
"""
Mood System for Agent-Based Modeling

Manages agent emotional states, temperament, and mood updates based on events.
"""

import os
import json
import random
import numpy as np
import traceback
from typing import Dict, Any, List, Optional, Tuple, TYPE_CHECKING, Union

if TYPE_CHECKING:
    from Environment.events import Event
from dataclasses import dataclass, asdict
from datetime import datetime
import time

# Import our new configuration system
try:
    from Setup.numerical_settings import numerical_settings
except ImportError:
    # Fallback for direct imports
    try:
        from numerical_settings import numerical_settings
    except ImportError:
        # Create a minimal fallback
        class FallbackSettings:
            EMOTIONAL_MOMENTUM_ALPHA = 2.0
            EMOTIONAL_MOMENTUM_BETA = 2.0
            MOOD_DECAY_ALPHA = 2.0
            MOOD_DECAY_BETA = 2.0
            MOOD_UPDATE_INTELLIGENCE_LEVEL = 3
            MOOD_INFLUENCE_ON_IMPACT = 0.3
            MOOD_UPDATE_FREQUENCY = 1
        numerical_settings = FallbackSettings()

# Try to import simulation time manager
try:
    from Environment.time_manager import get_current_simulation_timestamp, get_time_difference_from_simulation
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


def get_time_difference(current_timestamp: float, other_timestamp: float) -> float:
    """Get time difference between two timestamps."""
    if SIMULATION_TIME_AVAILABLE:
        try:
            return get_time_difference_from_simulation(other_timestamp)
        except Exception:
            return current_timestamp - other_timestamp
    else:
        return current_timestamp - other_timestamp

# Mood axes definition
MOOD_AXES = {
    'valence': 'unpleasant ↔ pleasant',           # 0 to 10
    'arousal': 'lethargic ↔ energized',         # 0 to 10  
    'agency': 'powerless ↔ in-control',          # 0 to 10
    'social_warmth': 'indifferent ↔ loving',    # 0 to 10
    'certainty': 'uncertain ↔ certain'           # 0 to 10
}

@dataclass
class MoodState:
    """Represents an agent's current mood state across 5 axes."""
    
    # Core mood values (0 to 10)
    valence: float = 5.0        # unpleasant ↔ pleasant
    arousal: float = 5.0        # lethargic ↔ energized
    agency: float = 5.0         # powerless ↔ in-control
    social_warmth: float = 5.0  # indifferent ↔ loving
    certainty: float = 5.0      # uncertain ↔ certain
    
    # Metadata
    timestamp: float = 0.0
    event_id: Optional[str] = None
    update_reason: str = ""
    
    def __post_init__(self):
        """Ensure mood values are within valid range."""
        self.valence = max(0.0, min(10.0, self.valence))
        self.arousal = max(0.0, min(10.0, self.arousal))
        self.agency = max(0.0, min(10.0, self.agency))
        self.social_warmth = max(0.0, min(10.0, self.social_warmth))
        self.certainty = max(0.0, min(10.0, self.certainty))
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)
    
    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), default=str)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MoodState':
        """Create from dictionary."""
        return cls(**data)
    
    @classmethod
    def from_json(cls, json_str: str) -> 'MoodState':
        """Create from JSON string."""
        data = json.loads(json_str)
        return cls.from_dict(data)
    
    def get_mood_summary(self) -> str:
        """Get a human-readable summary of the current mood."""
        summaries = []
        
        # Valence
        if self.valence >= 7:
            summaries.append("very pleasant")
        elif self.valence >= 5:
            summaries.append("pleasant")
        elif self.valence >= 3:
            summaries.append("neutral")
        else:
            summaries.append("unpleasant")
        
        # Arousal
        if self.arousal >= 7:
            summaries.append("very energized")
        elif self.arousal >= 5:
            summaries.append("energized")
        elif self.arousal >= 3:
            summaries.append("neutral")
        else:
            summaries.append("lethargic")
        
        # Agency
        if self.agency >= 7:
            summaries.append("very in-control")
        elif self.agency >= 5:
            summaries.append("in-control")
        elif self.agency >= 3:
            summaries.append("neutral")
        else:
            summaries.append("powerless")
        
        # Social Warmth
        if self.social_warmth >= 7:
            summaries.append("very loving")
        elif self.social_warmth >= 5:
            summaries.append("loving")
        elif self.social_warmth >= 3:
            summaries.append("neutral")
        else:
            summaries.append("indifferent")
        
        # Certainty
        if self.certainty >= 7:
            summaries.append("very certain")
        elif self.certainty >= 5:
            summaries.append("certain")
        elif self.certainty >= 3:
            summaries.append("neutral")
        else:
            summaries.append("uncertain")
        
        return ", ".join(summaries)
    
    def get_overall_mood(self) -> str:
        """Get overall mood classification."""
        # Calculate average across all axes
        avg_mood = (self.valence + self.arousal + self.agency + self.social_warmth + self.certainty) / 5.0
        
        if avg_mood >= 7.5:
            return "Excellent"
        elif avg_mood >= 6.5:
            return "Good"
        elif avg_mood >= 5.5:
            return "Neutral"
        elif avg_mood >= 4.5:
            return "Below Average"
        else:
            return "Poor"
    
    def to_json(self) -> str:
        """Get mood state as a JSON-formatted string."""
        mood_dict = {
            'valence': round(self.valence, 2),
            'arousal': round(self.arousal, 2),
            'agency': round(self.agency, 2),
            'social_warmth': round(self.social_warmth, 2),
            'certainty': round(self.certainty, 2),
            'timestamp': self.timestamp,
            'event_id': self.event_id,
            'update_reason': self.update_reason,
            'overall_mood': self.get_overall_mood(),
            'mood_summary': self.get_mood_summary()
        }
        return json.dumps(mood_dict, indent=2)
    
    def to_dict(self) -> Dict[str, Any]:
        """Get mood state as a dictionary."""
        return {
            'valence': round(self.valence, 2),
            'arousal': round(self.arousal, 2),
            'agency': round(self.agency, 2),
            'social_warmth': round(self.social_warmth, 2),
            'certainty': round(self.certainty, 2),
            'timestamp': self.timestamp,
            'event_id': self.event_id,
            'update_reason': self.update_reason,
            'overall_mood': self.get_overall_mood(),
            'mood_summary': self.get_mood_summary()
        }
    
    def apply_time_based_reversion(self, time_elapsed: float, time_unit: str = 'hours', decay_rate: float = None) -> 'MoodState':
        """
        Apply time-based reversion to the mean (5.0) based on the current time granularity.
        Applies decay every turn regardless of time elapsed.
        
        Args:
            time_elapsed: Time elapsed since last update (not used for calculation, kept for compatibility)
            time_unit: Unit of time (not used for calculation, kept for compatibility)
            decay_rate: Decay rate per turn (if None, uses default 0.07)
            
        Returns:
            New mood state with decay applied
        """
        if decay_rate is None:
            decay_rate = 0.07  # Default decay rate per turn
        
        # Apply the decay using the existing method (now turn-based)
        return self.apply_decay(time_elapsed, decay_rate)
    
    def apply_decay(self, hours_elapsed: float, decay_rate: float = 0.07) -> 'MoodState':
        """
        Apply decay to mood values, gradually returning them to the mean (5.0).
        Applies decay every turn regardless of time elapsed.
        
        Args:
            hours_elapsed: Time elapsed in hours (not used for calculation, kept for compatibility)
            decay_rate: Decay rate per turn (points per turn)
            
        Returns:
            New mood state with decay applied
        """
        print(f"\n=== MOOD DECAY APPLICATION (EVERY TURN) ===")
        print(f"Decay rate per turn: {decay_rate:.3f} points")
        print(f"Starting mood values:")
        print(f"  Valence: {self.valence:.3f}")
        print(f"  Arousal: {self.arousal:.3f}")
        print(f"  Agency: {self.agency:.3f}")
        print(f"  Social Warmth: {self.social_warmth:.3f}")
        print(f"  Certainty: {self.certainty:.3f}")
        
        # Create new mood state
        new_mood = MoodState(
            valence=self.valence,
            arousal=self.arousal,
            agency=self.agency,
            social_warmth=self.social_warmth,
            certainty=self.certainty
        )
        
        # Apply decay to each axis, ensuring we don't overshoot the mean (5.0)
        axes = ['valence', 'arousal', 'agency', 'social_warmth', 'certainty']
        starting_values = [self.valence, self.arousal, self.agency, self.social_warmth, self.certainty]
        
        print(f"\nApplying decay to each axis:")
        for i, axis in enumerate(axes):
            current_value = starting_values[i]
            target_value = 5.0  # Mean value
            
            if current_value > target_value:
                # Value is above mean, decay towards mean
                # Calculate how much we can decay without overshooting
                max_decay = current_value - target_value
                actual_decay = min(decay_rate, max_decay)
                new_value = current_value - actual_decay
                
                if actual_decay > 0:
                    print(f"  {axis.capitalize()}: {current_value:.3f} → {new_value:.3f} (decay: {actual_decay:.3f})")
                else:
                    print(f"  {axis.capitalize()}: {current_value:.3f} → {new_value:.3f} (already at mean)")
            elif current_value < target_value:
                # Value is below mean, increase towards mean
                # Calculate how much we can increase without overshooting
                max_increase = target_value - current_value
                actual_increase = min(decay_rate, max_increase)
                new_value = current_value + actual_increase
                
                if actual_increase > 0:
                    print(f"  {axis.capitalize()}: {current_value:.3f} → {new_value:.3f} (increase: {actual_increase:.3f})")
                else:
                    print(f"  {axis.capitalize()}: {current_value:.3f} → {new_value:.3f} (already at mean)")
            else:
                # Value is already at mean, no change
                new_value = current_value
                print(f"  {axis.capitalize()}: {current_value:.3f} → {new_value:.3f} (no change - already at mean)")
            
            # Set the new value
            setattr(new_mood, axis, new_value)
        
        # Copy metadata
        new_mood.timestamp = get_current_timestamp()
        new_mood.event_id = f"decay_{int(get_current_timestamp())}"
        new_mood.update_reason = f"Turn-based decay applied: {decay_rate:.3f} points per turn"
        
        print(f"\nFinal mood values:")
        print(f"  Valence: {new_mood.valence:.3f}")
        print(f"  Arousal: {new_mood.arousal:.3f}")
        print(f"  Agency: {new_mood.agency:.3f}")
        print(f"  Social Warmth: {new_mood.social_warmth:.3f}")
        print(f"  Certainty: {new_mood.certainty:.3f}")
        print(f"=== MOOD DECAY COMPLETE ===\n")
        
        return new_mood

class EmotionalMomentum:
    """Represents an agent's emotional stability and adaptability."""
    
    def __init__(self, momentum: float):
        """
        Initialize emotional momentum.
        
        Args:
            momentum: Momentum factor (0.0 = very reactive, 1.0 = very stable)
        """
        self.momentum = max(0.0, min(1.0, momentum))
    
    def get_stability_description(self) -> str:
        """Get human-readable description of emotional stability."""
        if self.momentum >= 0.8:
            return "Very emotionally stable - mood changes very slowly"
        elif self.momentum >= 0.6:
            return "Moderately emotionally stable - balanced adaptability"
        elif self.momentum >= 0.4:
            return "Moderately emotionally reactive - balanced adaptability"
        elif self.momentum >= 0.2:
            return "Very emotionally reactive - mood changes quickly"
        else:
            return "Extremely emotionally reactive - mood changes very quickly"
    
    def get_adaptability_factor(self) -> float:
        """Get adaptability factor (inverse of momentum)."""
        return 1.0 - self.momentum

class MoodDecay:
    """Controls how quickly mood values return to neutral."""
    
    def __init__(self, alpha: float = None, beta: float = None):
        """
        Initialize mood decay system.
        
        Args:
            alpha: Beta distribution alpha parameter
            beta: Beta distribution beta parameter
        """
        # Use dedicated decay shape parameters when available, otherwise sensible defaults
        if alpha is None:
            alpha = getattr(numerical_settings, 'MOOD_DECAY_ALPHA', 2.0)
        if beta is None:
            beta = getattr(numerical_settings, 'MOOD_DECAY_BETA', 2.0)
        
        self.alpha = alpha
        self.beta = beta
        self.decay_rate = self._sample_decay_rate()
    
    def _sample_decay_rate(self) -> float:
        """Sample decay rate from Beta distribution."""
        # Sample from Beta distribution
        sample = np.random.beta(self.alpha, self.beta)
        
        # Map to absolute decay rate range [0.04, 0.12] points per hour
        # This means mood will decay 0.04-0.12 points per hour towards neutral (5.0)
        decay_rate = 0.04 + (sample * 0.08)
        
        return decay_rate
    
    def get_decay_rate(self) -> float:
        """Get the current decay rate."""
        return self.decay_rate
    
    def get_decay_description(self) -> str:
        """Get human-readable description of decay rate."""
        if self.decay_rate >= 0.10:
            return f"High decay rate ({self.decay_rate:.3f} points per hour) - mood fades quickly"
        elif self.decay_rate >= 0.07:
            return f"Medium decay rate ({self.decay_rate:.3f} points per hour) - balanced mood persistence"
        else:
            return f"Low decay rate ({self.decay_rate:.3f} points per hour) - mood persists longer"

class MoodUpdater:
    """Handles mood updates based on events and perception results."""
    
    def __init__(self, api_manager=None, agent=None):
        """Initialize mood updater."""
        self.api_manager = api_manager
        self.agent = agent  # Store reference to agent to access mood decay rate
        
        # Import numerical settings for threshold and error handling
        try:
            from Setup.numerical_settings import numerical_settings
            self.mood_llm_threshold = numerical_settings.MOOD_LLM_IMPACT_THRESHOLD
            self.throw_on_failure = numerical_settings.MOOD_THROW_ON_FAILURE
        except ImportError:
            try:
                from numerical_settings import numerical_settings
                self.mood_llm_threshold = numerical_settings.MOOD_LLM_IMPACT_THRESHOLD
                self.throw_on_failure = numerical_settings.MOOD_THROW_ON_FAILURE
            except ImportError:
                self.mood_llm_threshold = 3  # Default fallback
                self.throw_on_failure = True  # Default to throwing errors
    
    def update_mood(self, 
                   current_mood: MoodState, 
                   event: 'Event', 
                   perception_result: Dict[str, Any],
                   agent_context: str = "",
                   recent_events: List['Event'] = None,
                   emotional_momentum: float = None) -> MoodState:
        """
        Update mood based on event and perception.
        
        Args:
            current_mood: Current mood state
            event: Event that occurred
            perception_result: Result from event perception
            agent_context: Agent context information
            recent_events: List of recent events for context
            emotional_momentum: Emotional momentum factor (0.0 = reactive, 1.0 = stable)
            
        Returns:
            Updated mood state
        """
        try:
            # Extract event information
            event_type = getattr(event, 'event_type', 'unknown')
            event_id = getattr(event, 'event_id', 'unknown')
            
            # Print full event details for debugging
            print("  Event Details:")
            print(f"    Type: {event_type}")
            print(f"    ID: {event_id}")
            print(f"    Content: {getattr(event, 'content', 'No content')}")
            print(f"    Environment: {getattr(event, 'environment', 'Unknown')}")
            print(f"    Source: {getattr(event, 'source', 'Unknown')}")
            print(f"    Target: {getattr(event, 'target', 'Unknown')}")
            
            # Handle case where perception_result might be an integer (fallback)
            if isinstance(perception_result, dict):
                impact_score = perception_result.get('impact_score', 1)
                perception_text = perception_result.get('perception', 'No perception')
                analysis_type = perception_result.get('analysis_type', 'Unknown')
                should_analyze = perception_result.get('should_analyze', False)
                print("  Perception Details:")
                print(f"    Impact Score: {impact_score}/10")
                print(f"    Analysis Type: {analysis_type}")
                print(f"    Should Analyze: {should_analyze}")
                print(f"    Perception: {perception_text}")
            else:
                impact_score = int(perception_result) if isinstance(perception_result, (int, float)) else 1
                print("  Perception Details:")
                print(f"    Impact Score: {impact_score}/10 (fallback)")
                print("    Analysis Type: Unknown (fallback)")
                print("    Should Analyze: False (fallback)")
                print(f"    Perception: {perception_result}")
            
            print("  Current Mood State:")
            print(f"    Valence: {current_mood.valence:.2f}/10")
            print(f"    Arousal: {current_mood.arousal:.2f}/10")
            print(f"    Agency: {current_mood.agency:.2f}/10")
            print(f"    Social Warmth: {current_mood.social_warmth:.2f}/10")
            print(f"    Certainty: {current_mood.certainty:.2f}/10")
            
            # Create new mood state
            new_mood = MoodState(
                valence=current_mood.valence,
                arousal=current_mood.arousal,
                agency=current_mood.agency,
                social_warmth=current_mood.social_warmth,
                certainty=current_mood.certainty
            )
            
            # Use LLM for mood updates only if impact score meets threshold
            if impact_score >= self.mood_llm_threshold and self.api_manager:
                try:
                    new_mood = self._update_mood_with_llm(
                        current_mood, event, perception_result, agent_context
                    )
                    
                except Exception as e:
                    if self.throw_on_failure:
                        print(f"LLM mood update failed completely: {e}")
                        print("   Full traceback:")
                        traceback.print_exc()
                        print("   Throwing error instead of falling back to simple mood update")
                        raise  # Re-raise the error to be handled by caller
                    else:
                        print(f"LLM mood update failed, falling back to simple update: {e}")
                        print("   Full traceback:")
                        traceback.print_exc()
                        print(f"   Falling back to simple mood update for event: {event_type}")
                        new_mood = self._simple_mood_update(current_mood, event_type, impact_score)
                
                # Apply emotional momentum if provided (single application)
                if emotional_momentum is not None:
                    new_mood = self._apply_momentum_update(current_mood, new_mood, emotional_momentum)
                    print(f"  Applied emotional momentum: {emotional_momentum:.2f}")
            else:
                # Use simple mood adjustments for low-impact events
                new_mood = self._simple_mood_update(current_mood, event_type, impact_score)
                
                # Apply emotional momentum if provided (even for simple updates)
                if emotional_momentum is not None:
                    new_mood = self._apply_momentum_update(current_mood, new_mood, emotional_momentum)
                    print(f"  Applied emotional momentum: {emotional_momentum:.2f}")
            
            # Apply time-based reversion to the mean based on time elapsed since last update
            if current_mood.timestamp > 0:
                time_elapsed = get_current_timestamp() - current_mood.timestamp
                
                # Always apply decay every turn, regardless of time elapsed
                # Get the decay rate from the agent's mood decay system
                if self.agent and hasattr(self.agent, 'mood_decay') and self.agent.mood_decay:
                    decay_rate = self.agent.mood_decay.decay_rate
                    print(f"  Using agent's decay rate: {decay_rate:.3f} points per turn")
                else:
                    decay_rate = 0.07  # Fallback default decay rate per turn
                    print(f"  Using fallback decay rate: {decay_rate:.3f} points per turn")
                
                # Apply decay to move mood toward mean (5.0)
                new_mood = new_mood.apply_decay(time_elapsed, decay_rate)
                print(f"  Applied turn-based decay: {decay_rate:.3f} points per turn")
            else:
                print(f"  Skipped turn-based decay: no previous timestamp available")
            
            # Add timestamp and metadata
            new_mood.timestamp = get_current_timestamp()
            new_mood.event_id = event_id
            new_mood.update_reason = f"Mood update based on {event_type} event (impact: {impact_score})"
            
            # Print final mood state and JSON representation
            print("  New Mood State After Update:")
            print(f"    Valence: {new_mood.valence:.2f}/10")
            print(f"    Arousal: {new_mood.arousal:.2f}/10")
            print(f"    Agency: {new_mood.agency:.2f}/10")
            print(f"    Social Warmth: {new_mood.social_warmth:.2f}/10")
            print(f"    Certainty: {new_mood.certainty:.2f}/10")
            print(f"    Update Reason: {new_mood.update_reason}")
            
            # Print JSON-formatted mood information
            print("  JSON Mood Information:")
            print(new_mood.to_json())
            
            return new_mood
            
        except Exception as e:
            print(f"Error in mood update: {e}")
            print(f"Full traceback:")
            import traceback
            traceback.print_exc()
            return current_mood
    
    def _update_mood_with_llm(self, 
                              current_mood: MoodState,
                              event: 'Event',
                              perception_result: Dict[str, Any],
                              agent_context: str,
                              recent_events: List[Dict[str, Any]] = None) -> MoodState:
        """Update mood using LLM analysis with validation and retry logic."""
        
        # Create mood update prompt with strict formatting requirements
        prompt = f"""You are analyzing how an event affects an agent's mood.

CURRENT MOOD STATE:
- Valence (pleasant ↔ unpleasant): {current_mood.valence:.1f}
- Arousal (energized ↔ lethargic): {current_mood.arousal:.1f}
- Agency (in-control ↔ powerless): {current_mood.agency:.1f}
- Social Warmth (loving ↔ indifferent): {current_mood.social_warmth:.1f}
- Certainty (certain ↔ uncertain): {current_mood.certainty:.1f}

CURRENT EVENT:
Type: {event.event_type}
Content: {event.content}
Environment: {event.environment}

AGENT'S PERCEPTION:
{perception_result.get('perception', 'No perception available') if isinstance(perception_result, dict) else 'No perception available'}
Impact Score: {perception_result.get('impact_score', 1) if isinstance(perception_result, dict) else perception_result}/10

RECENT EVENT HISTORY (Last 5 events):
{self._format_recent_events(recent_events) if recent_events else "No recent events"}

AGENT CONTEXT:
{agent_context}

TASK:
Analyze how this event affects the agent's mood on each of the 5 axes.
Consider the event type, content, impact score, current mood state, AND recent event history.
Recent events provide important context for understanding emotional patterns and cumulative effects.

Provide new mood values for each axis on a 0-10 scale where:
- 0 = extreme negative emotion on that axis
- 5 = neutral/balanced emotion on that axis  
- 10 = extreme positive emotion on that axis

CRITICAL INSTRUCTIONS:
1. You MUST respond with EXACTLY this format, with numeric values from 0-10 only
2. Each value must be a number (can be decimal like 5.5)
3. You MUST include ALL 5 mood axes in the exact order shown below
4. You MUST include a brief reasoning that explains your mood changes
5. Do NOT include any other text, explanations, or formatting
6. Do NOT use bullet points, dashes, or other symbols
7. Do NOT leave any fields empty or incomplete
8. Each line must start with the exact field name followed by a colon and space
9. The reasoning must be a single sentence explaining the mood changes
10. You MUST copy the format exactly as shown below
11. Do NOT add any extra lines or text

REQUIRED FORMAT (copy exactly):
VALENCE: <number>
AROUSAL: <number>
AGENCY: <number>
SOCIAL_WARMTH: <number>
CERTAINTY: <number>
REASONING: <brief explanation>

Example of valid response (copy this exact format):
VALENCE: 7.5
AROUSAL: 6.0
AGENCY: 4.0
SOCIAL_WARMTH: 8.0
CERTAINTY: 3.5
REASONING: This event was positive and energizing, improving social connections.

REMEMBER: You MUST respond with the exact format above. NO OTHER TEXT ALLOWED.
Your response should look exactly like the example above, with only the numbers and reasoning changed."""

        # Try up to 3 times to get a valid response
        max_retries = 3
        last_error = None
        
        for attempt in range(max_retries):
            try:
                # Get LLM response
                response, _, model_name, _ = self.api_manager.make_request(
                    prompt=prompt,
                    intelligence_level=3,  # Use highest intelligence for mood updates
                    max_tokens=400,  # Increased tokens to ensure complete response
                    temperature=0.1  # Lower temperature for more consistent formatting
                )
                
                # Log the response for debugging
                print(f"  LLM Response (attempt {attempt + 1}): {repr(response)}")
                
                # Check if response is empty or too short
                if not response or len(response.strip()) < 50:
                    last_error = f"Response too short or empty (length: {len(response) if response else 0})"
                    print(f"  Response validation failed: {last_error}")
                    if attempt < max_retries - 1:
                        # Add more explicit instructions for retry
                        prompt += f"\n\nCRITICAL: Your previous response was too short or empty. You MUST respond with the exact format requested."
                        prompt += "\n\nREQUIRED FORMAT (copy exactly):"
                        prompt += "\nVALENCE: <number>"
                        prompt += "\nAROUSAL: <number>"
                        prompt += "\nAGENCY: <number>"
                        prompt += "\nSOCIAL_WARMTH: <number>"
                        prompt += "\nCERTAINTY: <number>"
                        prompt += "\nREASONING: <brief explanation>"
                        continue
                    else:
                        break
                
                # Validate and parse response
                validation_result = self._validate_mood_response(response)
                if validation_result['is_valid']:
                    # Parse response
                    new_mood = self._parse_mood_response(response, current_mood)
                    new_mood.timestamp = get_current_timestamp()
                    new_mood.event_id = getattr(event, 'event_id', 'unknown')
                    new_mood.update_reason = self._extract_reasoning(response)
                    
                    return new_mood
                else:
                    # Response is invalid, prepare retry
                    last_error = validation_result['errors']
                    if attempt < max_retries - 1:
                        print(f"Mood response validation failed (attempt {attempt + 1}/{max_retries}): {last_error}")
                        # Add correction instruction to prompt for retry
                        prompt += f"\n\nCORRECTION NEEDED: Your previous response was invalid. {last_error}"
                        prompt += "\nPlease fix the format and try again."
                        prompt += "\n\nREQUIRED FORMAT (copy exactly):"
                        prompt += "\nVALENCE: <number>"
                        prompt += "\nAROUSAL: <number>"
                        prompt += "\nAGENCY: <number>"
                        prompt += "\nSOCIAL_WARMTH: <number>"
                        prompt += "\nCERTAINTY: <number>"
                        prompt += "\nREASONING: <brief explanation>"
                    else:
                        print(f"Mood response validation failed after {max_retries} attempts: {last_error}")
                        
            except Exception as e:
                last_error = f"API call failed: {e}"
                print("Full traceback:")
                import traceback
                traceback.print_exc()
                if attempt < max_retries - 1:
                    print(f"Mood update API call failed (attempt {attempt + 1}/{max_retries}): {e}")
                else:
                    print(f"Mood update failed after {max_retries} attempts: {e}")
        
        # All retries failed, fall back to simple update
        print("Falling back to simple mood update due to LLM failures")
        # Extract event_type from the event object
        event_type = getattr(event, 'event_type', 'unknown')
        return self._simple_mood_update(current_mood, event_type, impact_score)
    
    def _validate_mood_response(self, response: str) -> Dict[str, Any]:
        """
        Validate that the LLM response contains all required mood values on 0-10 scale.
        
        Args:
            response: LLM response string
            
        Returns:
            Dict with 'is_valid' boolean and 'errors' list
        """
        errors = []
        required_fields = ['VALENCE', 'AROUSAL', 'AGENCY', 'SOCIAL_WARMTH', 'CERTAINTY']
        
        # Check if response is empty or None
        if not response or not response.strip():
            errors.append("Response is empty or None")
            return {'is_valid': False, 'errors': errors}
        
        # Split into lines and check each required field
        lines = [line.strip() for line in response.strip().split('\n') if line.strip()]
        
        # Debug: log the lines we're processing
        print(f"    Processing response lines: {lines}")
        
        for field in required_fields:
            field_found = False
            field_value = None
            
            for line in lines:
                if line.startswith(f'{field}:'):
                    field_found = True
                    try:
                        # Extract value after colon
                        value_str = line.split(':', 1)[1].strip()
                        if not value_str:
                            errors.append(f"{field} has empty value")
                            continue
                        
                        # Try to parse as float
                        field_value = float(value_str)
                        
                        # Check range for 0-10 scale
                        if field_value < 0 or field_value > 10:
                            errors.append(f"{field} value {field_value} is outside valid range [0, 10]")
                        
                    except ValueError:
                        errors.append(f"{field} value '{value_str}' is not a valid number")
                    break
            
            if not field_found:
                errors.append(f"Missing required field: {field}")
            elif field_value is None:
                errors.append(f"Could not parse {field} value")
        
        # Check if we have any errors
        is_valid = len(errors) == 0
        
        if not is_valid:
            print(f"    Validation errors: {errors}")
        
        return {
            'is_valid': is_valid,
            'errors': errors
        }
    
    def _extract_reasoning(self, response: str) -> str:
        """Extract reasoning from LLM response."""
        try:
            lines = [line.strip() for line in response.strip().split('\n') if line.strip()]
            for line in lines:
                if line.startswith('REASONING:'):
                    return line.split(':', 1)[1].strip()
        except Exception:
            pass
        return "LLM mood update"
    
    def _apply_momentum_update(self, current_mood: MoodState, new_mood: MoodState, momentum: float) -> MoodState:
        """
        Apply momentum-based mood update using the correct formula:
        final_mood = momentum * old_mood + (1 - momentum) * new_mood
        
        Args:
            current_mood: Current mood state
            new_mood: New mood state from LLM (raw values on 0-10 scale)
            momentum: Momentum factor (0.0 = very reactive, 1.0 = very stable)
            
        Returns:
            Updated mood state with momentum applied
        """
        # Ensure momentum is bounded to [0, 1]
        momentum = max(0.0, min(1.0, momentum))
        adaptability = 1.0 - momentum
        
        # Apply momentum formula to each mood axis
        # Creates a weighted average between old and new values
        updated_mood = MoodState(
            valence=current_mood.valence * momentum + new_mood.valence * adaptability,
            arousal=current_mood.arousal * momentum + new_mood.arousal * adaptability,
            agency=current_mood.agency * momentum + new_mood.agency * adaptability,
            social_warmth=current_mood.social_warmth * momentum + new_mood.social_warmth * adaptability,
            certainty=current_mood.certainty * momentum + new_mood.certainty * adaptability
        )
        
        # Copy metadata
        updated_mood.timestamp = new_mood.timestamp
        updated_mood.event_id = new_mood.event_id
        updated_mood.update_reason = f"Mood updated with momentum {momentum:.2f} (adaptability {adaptability:.2f})"
        
        return updated_mood
    
    def _format_recent_events(self, recent_events: List[Dict[str, Any]]) -> str:
        """Format recent events for inclusion in mood update prompt."""
        if not recent_events:
            return "No recent events"
        
        formatted = []
        for i, event_data in enumerate(recent_events[-5:], 1):  # Get last 5 events
            event = event_data.get('event', {})
            perception = event_data.get('perception_result', {})
            
            formatted.append(f"{i}. {event.get('event_type', 'Unknown')}: {event.get('content', 'No content')[:100]}...")
            formatted.append(f"   Impact: {perception.get('impact_score', 'Unknown')}/10")
            formatted.append(f"   Analysis: {perception.get('analysis_type', 'Unknown')}")
            formatted.append("")
        
        return "\n".join(formatted)
    
    def _parse_mood_response(self, response: str, current_mood: MoodState) -> MoodState:
        """Parse LLM response to extract new mood values."""
        # Default to current mood
        new_mood = MoodState(
            valence=current_mood.valence,
            arousal=current_mood.arousal,
            agency=current_mood.agency,
            social_warmth=current_mood.social_warmth,
            certainty=current_mood.certainty
        )
        
        try:
            lines = [line.strip() for line in response.strip().split('\n') if line.strip()]
            
            for line in lines:
                try:
                    if line.startswith('VALENCE:'):
                        value_str = line.split(':', 1)[1].strip()
                        if value_str:
                            new_mood.valence = float(value_str)
                    elif line.startswith('AROUSAL:'):
                        value_str = line.split(':', 1)[1].strip()
                        if value_str:
                            new_mood.arousal = float(value_str)
                    elif line.startswith('AGENCY:'):
                        value_str = line.split(':', 1)[1].strip()
                        if value_str:
                            new_mood.agency = float(value_str)
                    elif line.startswith('SOCIAL_WARMTH:'):
                        value_str = line.split(':', 1)[1].strip()
                        if value_str:
                            new_mood.social_warmth = float(value_str)
                    elif line.startswith('CERTAINTY:'):
                        value_str = line.split(':', 1)[1].strip()
                        if value_str:
                            new_mood.certainty = float(value_str)
                except ValueError as ve:
                    print(f"Warning: Could not parse value in line '{line}': {ve}")
                    continue
                    
        except Exception as e:
            print(f"Warning: Failed to parse mood response: {e}")
            print(f"Full traceback:")
            import traceback
            traceback.print_exc()
        
        return new_mood
    
    def _extract_reasoning(self, response: str) -> str:
        """Extract reasoning from LLM response."""
        try:
            for line in response.strip().split('\n'):
                if line.startswith('REASONING:'):
                    return line.split(':', 1)[1].strip()
        except:
            pass
        return "Mood updated based on event"
    
    def _simple_mood_update(self, 
                           current_mood: MoodState,
                           event_type: str,
                           impact_score: Union[int, float]) -> MoodState:
        """Simple mood update without LLM."""
        
        # We now receive event_type and impact_score directly
        # No need for complex type checking
        
        # Create new mood with small changes based on event
        new_mood = MoodState(
            valence=current_mood.valence,
            arousal=current_mood.arousal,
            agency=current_mood.agency,
            social_warmth=current_mood.social_warmth,
            certainty=current_mood.certainty
        )
        
        # Simple mood adjustments based on event type and impact (0-10 scale)
        if event_type == 'interaction':
            if impact_score >= 5:
                new_mood.social_warmth = min(10.0, current_mood.social_warmth + 0.5)
                new_mood.valence = min(10.0, current_mood.valence + 0.3)
            else:
                new_mood.social_warmth = max(0.0, current_mood.social_warmth - 0.3)
        
        elif event_type == 'message':
            if impact_score >= 4:
                new_mood.certainty = min(10.0, current_mood.certainty + 0.4)
                new_mood.arousal = min(10.0, current_mood.arousal + 0.3)
        
        elif event_type == 'environmental_change':
            if impact_score >= 6:
                new_mood.agency = max(0.0, current_mood.agency - 0.4)
                new_mood.certainty = max(0.0, current_mood.certainty - 0.3)
        
        # Add timestamp and metadata
        new_mood.timestamp = get_current_timestamp()
        new_mood.event_id = f"simple_{int(get_current_timestamp())}"  # Generate a simple event ID
        new_mood.update_reason = f"Simple update based on {event_type} event (impact: {impact_score})"
        
        return new_mood

class MoodInfluence:
    """Handles how mood influences event processing."""
    
    def __init__(self):
        """Initialize mood influence system."""
        self.mood_influence = float(os.getenv('MOOD_INFLUENCE_ON_IMPACT', '0.3'))
    
    def adjust_impact_score(self, base_impact: int, current_mood: MoodState) -> int:
        """
        Adjust impact score based on current mood.
        
        Args:
            base_impact: Base impact score (1-10)
            current_mood: Current mood state
            
        Returns:
            Adjusted impact score (1-10)
        """
        # Calculate mood factor (0 to 1, where 5 is neutral)
        # Convert from 0-10 scale to -1 to +1 scale for calculations
        valence_factor = (current_mood.valence - 5.0) / 5.0  # -1 to +1
        arousal_factor = (current_mood.arousal - 5.0) / 5.0  # -1 to +1
        agency_factor = (current_mood.agency - 5.0) / 5.0    # -1 to +1
        
        # Average the factors
        mood_factor = (valence_factor + arousal_factor + agency_factor) / 3.0
        
        # Apply mood influence
        adjustment = mood_factor * self.mood_influence * 2  # Scale to reasonable range
        
        # Calculate new impact score
        new_impact = base_impact + adjustment
        
        # Clamp to valid range
        return max(1, min(10, int(round(new_impact))))
    
    def get_mood_context_prompt(self, current_mood: MoodState) -> str:
        """
        Get mood context for LLM prompts.
        
        Args:
            current_mood: Current mood state
            
        Returns:
            Formatted mood context string
        """
        return f"""CURRENT MOOD CONTEXT:
You are currently feeling {current_mood.get_mood_summary()}.
Overall mood: {current_mood.get_overall_mood()}
- Valence: {current_mood.valence:.1f} (pleasant ↔ unpleasant)
- Arousal: {current_mood.arousal:.1f} (energized ↔ lethargic)
- Agency: {current_mood.agency:.1f} (in-control ↔ powerless)
- Social Warmth: {current_mood.social_warmth:.1f} (loving ↔ indifferent)
- Certainty: {current_mood.certainty:.1f} (certain ↔ uncertain)

Consider this emotional state when analyzing events."""

# Factory functions for creating mood system components
def create_initial_mood() -> MoodState:
    """Create initial mood state with neutral values."""
    return MoodState()

def sample_emotional_momentum(
    alpha: float = None,
    beta: float = None,
    min_momentum: float = None,
    max_momentum: float = None
) -> EmotionalMomentum:
    """Sample emotional momentum mapped to [min_momentum, max_momentum] with center most likely.

    - Draw from a symmetric Beta(α, β) to get a normal-like shape centered at 0.5
    - Map from [0, 1] to [min_momentum, max_momentum]
    - Defaults: α=β=4.0 (peaked near center), min=0.3, max=0.7
    """
    if alpha is None:
        alpha = getattr(numerical_settings, 'EMOTIONAL_MOMENTUM_ALPHA', 4.0)
    if beta is None:
        beta = getattr(numerical_settings, 'EMOTIONAL_MOMENTUM_BETA', 4.0)

    if min_momentum is None:
        min_momentum = getattr(numerical_settings, 'EMOTIONAL_MOMENTUM_MIN', 0.3)
    if max_momentum is None:
        max_momentum = getattr(numerical_settings, 'EMOTIONAL_MOMENTUM_MAX', 0.7)

    # Safety: ensure bounds are sensible
    if max_momentum < min_momentum:
        min_momentum, max_momentum = max_momentum, min_momentum

    # Sample in [0,1]
    raw = np.random.beta(alpha, beta)
    # Map to [min_momentum, max_momentum]
    momentum = min_momentum + (max_momentum - min_momentum) * raw

    return EmotionalMomentum(momentum)

def sample_mood_decay(alpha: float = None, beta: float = None) -> MoodDecay:
    """Sample mood decay rate from Beta distribution using decay parameters."""
    if alpha is None:
        alpha = getattr(numerical_settings, 'MOOD_DECAY_ALPHA', 2.0)
    if beta is None:
        beta = getattr(numerical_settings, 'MOOD_DECAY_BETA', 2.0)
    
    return MoodDecay(alpha, beta)

def apply_time_based_reversion(current_mood: MoodState, time_elapsed: float, time_unit: str = 'hours') -> MoodState:
    """
    Apply time-based reversion to the mean based on the current time granularity.
    
    Args:
        current_mood: Current mood state
        time_elapsed: Time elapsed since last update
        time_unit: Unit of time ('seconds', 'minutes', 'hours', 'days')
        
    Returns:
        New mood state with time-based reversion applied
    """
    # Apply time-based reversion
    return current_mood.apply_time_based_reversion(time_elapsed, time_unit)

def apply_momentum_update(current_mood: MoodState, new_mood: MoodState, momentum: float) -> MoodState:
    """
    Apply momentum-based mood update using the correct formula:
    final_mood = momentum * old_mood + (1 - momentum) * new_mood
    
    Args:
        current_mood: Current mood state
        new_mood: New mood state from LLM (raw values on 0-10 scale)
        momentum: Momentum factor (0.0 = very reactive, 1.0 = very stable)
        
    Returns:
        Updated mood state with momentum applied
    """
    # Ensure momentum is bounded to [0, 1]
    momentum = max(0.0, min(1.0, momentum))
    adaptability = 1.0 - momentum
    
    # Apply momentum formula to each mood axis
    # Creates a weighted average between old and new values
    updated_mood = MoodState(
        valence=current_mood.valence * momentum + new_mood.valence * adaptability,
        arousal=current_mood.arousal * momentum + new_mood.arousal * adaptability,
        agency=current_mood.agency * momentum + new_mood.agency * adaptability,
        social_warmth=current_mood.social_warmth * momentum + new_mood.social_warmth * adaptability,
        certainty=current_mood.certainty * momentum + new_mood.certainty * adaptability
    )
    
    # Copy metadata
    updated_mood.timestamp = new_mood.timestamp
    updated_mood.event_id = new_mood.event_id
    updated_mood.update_reason = f"Mood updated with momentum {momentum:.2f} (adaptability {adaptability:.2f})"
    
    return updated_mood
