import time
import json
import logging
import os
import requests
from typing import Dict, Any, Optional, List
import random
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables using centralized loader
try:
    from Utils.env_loader import load_environment
    # Load from World_Sim root (parent.parent.parent)
    env_path = Path(__file__).resolve().parent.parent.parent / '.env'
    load_environment(env_path)
except ImportError:
    # Fallback to basic dotenv loading if centralized loader not available
    BASE_DIR = Path(__file__).resolve().parent.parent.parent
    ENV_PATH = BASE_DIR / '.env'
    load_dotenv(dotenv_path=ENV_PATH)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class GPTRequest:
    """
    Handles safe GPT requests with rate limiting, retry logic, and error handling.
    Uses OpenRouter API with highest throughput models.
    """
    
    def __init__(self, api_key: Optional[str] = None, model: str = "cerebras/llama-3.1-8b-instruct"):
        """
        Initialize GPT request handler.
        
        Args:
            api_key (str): OpenRouter API key (if None, will try to get from environment)
            model (str): Model to use for requests
        """
        # Check USE_API environment variable first (after loading .env)
        self.use_api = os.getenv('USE_API', '1') != '0'
        
        # Get API key from environment if not provided
        self.api_key = api_key or os.getenv('OPENROUTER_KEY')
        if not self.api_key and self.use_api:
            raise ValueError("OpenRouter API key is required. Set OPENROUTER_KEY environment variable.")
        
        self.model = model
        self.base_url = os.getenv("OPEN_ROUTER_LINK", "https://openrouter.ai/api/v1/chat/completions")
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        } if self.api_key else {}
        
        self.request_count = 0
        self.last_request_time = 0
        self.min_request_interval = 0.1  # Minimum seconds between requests
        
    def safe_generate_response(self, 
                             messages: List[Dict[str, str]], 
                             max_tokens: int = 1000,
                             temperature: float = 0.7,
                             max_retries: int = 3) -> Optional[str]:
        """
        Safely generate a response with retry logic and rate limiting.
        
        Args:
            messages (List[Dict]): List of messages in ChatML format
            max_tokens (int): Maximum tokens to generate
            temperature (float): Temperature for generation
            max_retries (int): Maximum number of retries
            
        Returns:
            Optional[str]: Generated response or None if failed
        """
        # Check if API calls are disabled
        if not self.use_api:
            return self._generate_mock_response(messages)
        
        for attempt in range(max_retries):
            try:
                # Rate limiting
                current_time = time.time()
                time_since_last = current_time - self.last_request_time
                if time_since_last < self.min_request_interval:
                    time.sleep(self.min_request_interval - time_since_last)
                
                # Prepare payload for OpenRouter
                payload = {
                    "model": self.model,
                    "messages": messages,
                    "max_tokens": max_tokens,
                    "temperature": temperature
                }
                
                # Add provider configuration for highest throughput
                provider = os.getenv("OPEN_ROUTER_PROVIDER", "cerebras")
                if provider:
                    payload["provider"] = {
                        "sort": "throughput"  # Prioritize highest throughput provider
                    }
                
                # Make the request to OpenRouter
                response = requests.post(
                    self.base_url,
                    headers=self.headers,
                    json=payload,
                    timeout=30
                )
                
                response.raise_for_status()
                response_data = response.json()
                
                self.last_request_time = time.time()
                self.request_count += 1
                
                # Extract and return the response
                if 'choices' in response_data and len(response_data['choices']) > 0:
                    return response_data['choices'][0]['message']['content'].strip()
                
            except Exception as e:
                logger.warning(f"OpenRouter request failed (attempt {attempt + 1}/{max_retries}): {e}")
                
                # Exponential backoff
                if attempt < max_retries - 1:
                    wait_time = (2 ** attempt) + random.uniform(0, 1)
                    time.sleep(wait_time)
        
        logger.error(f"OpenRouter request failed after {max_retries} attempts")
        return None
    
    def _generate_mock_response(self, messages: List[Dict[str, str]]) -> str:
        """Generate a mock response when USE_API=0"""
        # Get the last user message to understand the request type
        user_message = ""
        system_message = ""
        
        for msg in messages:
            if msg["role"] == "user":
                user_message = msg["content"].lower()
            elif msg["role"] == "system":
                system_message = msg["content"].lower()
        
        # Generate appropriate mock responses based on content
        if "reflection" in user_message or "reflect" in user_message:
            return "Today was a productive day. I focused on my goals and made meaningful progress. I learned that consistent effort leads to better outcomes, and I should continue prioritizing my most important tasks."
        
        elif "daily plan" in user_message or "schedule" in user_message:
            return '''{"wake_up_hour": 7, "sleep_hour": 23, "schedule": [{"hour": 7, "activity": "Morning routine and breakfast", "priority": 8}, {"hour": 9, "activity": "Focus on main work tasks", "priority": 9}, {"hour": 13, "activity": "Lunch break", "priority": 6}, {"hour": 14, "activity": "Afternoon productivity", "priority": 8}, {"hour": 18, "activity": "Personal time and exercise", "priority": 7}, {"hour": 20, "activity": "Dinner and relaxation", "priority": 6}], "main_goals_today": ["Complete important work tasks", "Maintain healthy habits", "Make progress on personal goals"], "reflection_notes": "Today's plan balances productivity with self-care"}'''
        
        elif "weekly plan" in user_message:
            return '''{"weekly_theme": "Focused productivity and personal growth", "daily_plans": {"monday": {"theme": "Strong start", "main_goals": ["Set weekly priorities", "Complete high-impact tasks"], "focus_areas": ["planning", "productivity"]}, "tuesday": {"theme": "Deep work", "main_goals": ["Focus on complex projects", "Minimize distractions"], "focus_areas": ["concentration", "quality work"]}, "wednesday": {"theme": "Midweek momentum", "main_goals": ["Review progress", "Adjust plans if needed"], "focus_areas": ["adaptation", "progress check"]}}, "weekly_goals": ["Advance major projects", "Maintain work-life balance", "Build positive habits"], "challenges_to_address": ["Time management", "Staying motivated midweek"]}'''
        
        elif "importance" in user_message or "score" in user_message:
            return "6 - This is a moderately important memory that contributes to understanding daily patterns and personal growth."
        
        elif "goal" in user_message and ("update" in user_message or "setting" in user_message):
            return '''{"long_term_goals": ["Advance in career and develop expertise", "Maintain strong relationships with family and friends", "Stay healthy and maintain work-life balance", "Continue learning and personal growth", "Make positive contributions to community"], "core_principles": ["Treat others with respect and kindness", "Stay true to my values and beliefs", "Strive for excellence while accepting imperfection", "Value learning and growth over comfort"], "short_term_objectives": ["Complete current work projects successfully", "Establish consistent healthy routines", "Strengthen key relationships"], "areas_for_growth": ["Time management skills", "Emotional intelligence", "Technical expertise"], "goal_changes": "Refined goals to be more specific and actionable based on recent reflections"}'''
        
        elif "action" in user_message and "plan" in user_message:
            return "Focus on completing the most important task on my daily plan while staying mindful of my energy levels and taking breaks when needed."
        
        elif "synthesis" in user_message or "insight" in user_message:
            return "These experiences show a pattern of growth through consistent effort. I'm learning to balance ambition with patience, and I'm becoming more aware of what truly matters to me."
        
        else:
            return "I understand and will take appropriate action based on my current situation and goals."
    
    def generate_with_system_prompt(self,
                                  system_prompt: str,
                                  user_prompt: str,
                                  **kwargs) -> Optional[str]:
        """
        Generate response with system and user prompts.
        
        Args:
            system_prompt (str): System prompt to set context
            user_prompt (str): User prompt with the actual request
            **kwargs: Additional arguments for safe_generate_response
            
        Returns:
            Optional[str]: Generated response
        """
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        return self.safe_generate_response(messages, **kwargs)


# Global instance for easy access
_gpt_client = None

def get_gpt_client(api_key: Optional[str] = None) -> GPTRequest:
    """Get or create a global GPT client instance"""
    global _gpt_client
    if _gpt_client is None:
        _gpt_client = GPTRequest(api_key=api_key)
    return _gpt_client

def safe_generate_response(messages: List[Dict[str, str]], **kwargs) -> Optional[str]:
    """
    Convenience function for safe response generation.
    
    Args:
        messages (List[Dict]): Messages in ChatML format
        **kwargs: Additional arguments
        
    Returns:
        Optional[str]: Generated response
    """
    client = get_gpt_client()
    return client.safe_generate_response(messages, **kwargs)

def generate_with_system_prompt(system_prompt: str, user_prompt: str, **kwargs) -> Optional[str]:
    """
    Convenience function for generation with system prompt.
    
    Args:
        system_prompt (str): System prompt
        user_prompt (str): User prompt
        **kwargs: Additional arguments
        
    Returns:
        Optional[str]: Generated response
    """
    client = get_gpt_client()
    return client.generate_with_system_prompt(system_prompt, user_prompt, **kwargs)

def parse_json_response(response: str) -> Optional[Dict[str, Any]]:
    """
    Parse a JSON response from the LLM.
    
    Args:
        response (str): Raw response from LLM
        
    Returns:
        Optional[Dict]: Parsed JSON or None if invalid
    """
    if not response:
        return None
    
    # Try to extract JSON from the response
    try:
        # Sometimes the response includes extra text, try to find JSON
        start = response.find('{')
        end = response.rfind('}') + 1
        
        if start != -1 and end > start:
            json_str = response[start:end]
            return json.loads(json_str)
        else:
            # Try parsing the entire response
            return json.loads(response)
            
    except json.JSONDecodeError as e:
        logger.warning(f"Failed to parse JSON response: {e}")
        logger.warning(f"Response was: {response}")
        return None

def parse_list_response(response: str, delimiter: str = '\n') -> List[str]:
    """
    Parse a list response from the LLM.
    
    Args:
        response (str): Raw response from LLM
        delimiter (str): Delimiter to split on
        
    Returns:
        List[str]: Parsed list items
    """
    if not response:
        return []
    
    # Split by delimiter and clean up
    items = []
    for line in response.split(delimiter):
        line = line.strip()
        # Remove common list markers
        line = line.lstrip('- •*1234567890. ')
        if line:
            items.append(line)
    
    return items

def extract_importance_score(response: str) -> float:
    """
    Extract an importance score (1-10) from the LLM response.
    
    Args:
        response (str): Raw response from LLM
        
    Returns:
        float: Importance score between 1-10
    """
    if not response:
        return 5.0
    
    # Look for numbers in the response
    import re
    numbers = re.findall(r'\b([1-9]|10)\b', response)
    
    if numbers:
        try:
            score = float(numbers[0])
            return max(1.0, min(10.0, score))
        except ValueError:
            pass
    
    # Default to middle importance
    return 5.0 