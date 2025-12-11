#!/usr/bin/env python3
"""
API Manager for OpenRouter API interactions.

Handles model selection, API requests, and response processing.
"""

import os
import json
import requests
import time
import threading
from typing import Dict, Any, Optional, List
# Load environment variables using centralized loader
try:
    from Utils.env_loader import load_environment
    load_environment()
except ImportError:
    # Fallback to basic dotenv loading if centralized loader not available
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        print("Warning: python-dotenv not available. Environment variables may not be loaded from .env file.")

from pathlib import Path

class APIManager:
    """
    Centralized API manager for all external API calls.
    Uses singleton pattern to ensure consistent configuration across the application.
    
    This is the SINGLE SOURCE OF TRUTH for all API-related configuration and operations.
    """
    
    _instance: Optional['APIManager'] = None
    _lock = threading.Lock()
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Private constructor. Use get_instance() instead.
        
        Args:
            api_key (str, optional): OpenRouter API key. If not provided, will try to get from environment.
        """
        # Try both OPENROUTER_KEY and OPENROUTER_API_KEY for compatibility
        self.api_key = api_key or os.getenv('OPENROUTER_KEY') or os.getenv('OPENROUTER_API_KEY')
        if not self.api_key:
            raise ValueError("OpenRouter API key is required. Set OPENROUTER_KEY environment variable in .env file or pass it to constructor.")
        
        # Load API config from environment variables, fallback to defaults if not set
        self.base_url = os.getenv("OPEN_ROUTER_LINK", "https://openrouter.ai/api/v1/chat/completions")
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        # optional but recommended for openrouter ranking/diagnostics
        http_referer = os.getenv("OPENROUTER_HTTP_REFERER") or os.getenv("HTTP_REFERER")
        x_title = os.getenv("OPENROUTER_X_TITLE") or os.getenv("X_TITLE")
        if http_referer:
            self.headers["HTTP-Referer"] = http_referer
        if x_title:
            self.headers["X-Title"] = x_title
        
        # Model mapping based on intelligence level, loaded from .env if available
        # default to openai models unless overridden in .env
        self.model_mapping = {
            1: os.getenv("OPEN_ROUTER_STUPID_MODEL", "openai/gpt-oss-20b"),
            2: os.getenv("OPEN_ROUTER_NONREASONING_MODEL", "openai/gpt-oss-120b"),
            3: os.getenv("OPEN_ROUTER_REASONING_MODEL", "openai/gpt-oss-120b"),
            4: os.getenv("OPEN_ROUTER_SEARCH_MODEL", "openai/gpt-oss-20b"),  # For intelligent search
        }
        
        # Provider debugging - enable to print provider info for each request
        self.debug_provider = os.getenv("DEBUG_PROVIDER_INFO", "false").lower() == "true"
        
        # LLM Response Logging Configuration
        self.enable_llm_logging = os.getenv('ENABLE_LLM_LOGGING', 'false').lower() == 'true'
        self.llm_log_dir = os.getenv('LLM_LOG_DIR', 'logs/llm_responses')
        
        # LLM Model Reporting Configuration
        # Set REPORT_LLM_MODEL_CONFIG=true in .env to enable detailed console output
        # showing model selection, configuration, and token usage for each API call
        self.report_model_config = os.getenv('REPORT_LLM_MODEL_CONFIG', 'false').lower() == 'true'
        
        # Embedding configuration
        self.openai_api_key = os.getenv('OPENAI_API_KEY')
        self.use_mock_embeddings = os.getenv('USE_MOCK_EMBEDDINGS', 'false').lower() in ('true', '1', 'yes')
        
        if self.enable_llm_logging:
            self._setup_logging_directory()
    
    @classmethod
    def get_instance(cls, api_key: Optional[str] = None) -> 'APIManager':
        """
        Get the singleton instance of APIManager.
        This is the ONLY way to access the API manager.
        """
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls(api_key)
        return cls._instance
    
    @classmethod
    def reset_instance(cls) -> None:
        """Reset the singleton instance. Useful for testing."""
        with cls._lock:
            cls._instance = None
    
    def _setup_logging_directory(self):
        """Set up the logging directory for LLM responses."""
        log_path = Path(self.llm_log_dir)
        log_path.mkdir(parents=True, exist_ok=True)
        print(f"LLM Response logging enabled. Logs will be saved to: {log_path.absolute()}")
    
    def _log_llm_response(self, prompt: str, response: str, model_name: str, intelligence_level: int, 
                          max_tokens: int, temperature: float, metadata: Dict[str, Any] = None):
        """
        Log LLM request and response to a file.
        
        Args:
            prompt: The input prompt
            response: The LLM response
            model_name: The model used
            intelligence_level: Intelligence level used
            max_tokens: Max tokens requested
            temperature: Temperature setting
            metadata: Additional metadata to log
        """
        if not self.enable_llm_logging:
            return
            
        try:
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            filename = f"llm_response_{timestamp}_{intelligence_level}_{model_name.replace('/', '_')}.txt"
            filepath = Path(self.llm_log_dir) / filename
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write("=" * 80 + "\n")
                f.write("LLM REQUEST/RESPONSE LOG\n")
                f.write("=" * 80 + "\n\n")
                
                f.write(f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Model: {model_name}\n")
                f.write(f"Intelligence Level: {intelligence_level}\n")
                f.write(f"Max Tokens: {max_tokens}\n")
                f.write(f"Temperature: {temperature}\n")
                
                if metadata:
                    f.write(f"Metadata: {json.dumps(metadata, indent=2)}\n")
                
                f.write("\n" + "=" * 40 + "\n")
                f.write("PROMPT\n")
                f.write("=" * 40 + "\n")
                f.write(prompt)
                f.write("\n\n" + "=" * 40 + "\n")
                f.write("RESPONSE\n")
                f.write("=" * 40 + "\n")
                f.write(response)
                f.write("\n\n" + "=" * 80 + "\n")
                
            print(f"LLM response logged to: {filepath}")
            
        except Exception as e:
            print(f"Warning: Failed to log LLM response: {e}")

    def get_model_name(self, intelligence_level: int) -> str:
        """
        Get the model name based on intelligence level.
        
        Args:
            intelligence_level (int): Intelligence level (1, 2, 3, or 4)
            
        Returns:
            str: Model name for the given intelligence level
            
        Raises:
            ValueError: If intelligence level is not 1, 2, 3, or 4
        """
        if intelligence_level not in self.model_mapping:
            raise ValueError(f"Intelligence level must be 1, 2, 3, or 4. Got: {intelligence_level}")
        
        return self.model_mapping[intelligence_level]
    
    def make_request(self, 
                        prompt: str, 
                        intelligence_level: int = None,
                        max_tokens: int = None,
                        temperature: float = None
                    ) -> tuple[str, str]:
        """
        Make a request to OpenRouter API, ensuring the provider is set if specified.
        
        Args:
            prompt (str): The prompt to send to the model
            intelligence_level (int): Intelligence level (1, 2, or 3) to determine model (defaults to env setting)
            max_tokens (int): Maximum number of tokens to generate (defaults to env setting)
            temperature (float): Sampling temperature (0.0 to 2.0) (defaults to env setting)
            
        Returns:
            tuple[str, str, str, dict]: A tuple containing (response_text, reasoning_text, model_name, metadata)
            
        Raises:
            Exception: If the API request fails
        """
        # Use environment defaults if not specified
        if intelligence_level is None:
            intelligence_level = int(os.getenv('DEFAULT_INTELLIGENCE_LEVEL', '2'))
        if max_tokens is None:
            max_tokens = int(os.getenv('DEFAULT_MAX_TOKENS', '1000'))
        if temperature is None:
            temperature = float(os.getenv('DEFAULT_TEMPERATURE', '0.7'))

        # the model that we are going to use for the intelligence level that we care about
        # Use the fastest model for better throughput
        model_name = self.get_model_name(intelligence_level)
        
        # Report model configuration if enabled
        if self.report_model_config:
            print(f"\n{'='*80}")
            print("LLM API REQUEST CONFIGURATION")
            print(f"{'='*80}")
            print(f"Model: {model_name}")
            print(f"Intelligence Level: {intelligence_level}")
            print(f"Max Tokens: {max_tokens}")
            print(f"Temperature: {temperature}")
            print(f"API Endpoint: {self.base_url}")
            print(f"{'='*80}\n")

        # the payload that we are going to send to the api
        payload: Dict[str, Any] = {
            "model": model_name,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "max_tokens": max_tokens,
            "temperature": temperature,
            'provider': {
                'sort': 'throughput'
            }
        }

        # send the request to the api
        try:
            # make the request to the api
            response = requests.post(
                self.base_url,
                headers=self.headers,
                json=payload,
                timeout=30
            )

            # raise an error if the request fails
            response.raise_for_status()

            # get the response from the api
            response_data = response.json()
            # print(json.dumps(response_data, indent=2))

            # check if the response is valid
            if 'choices' in response_data and len(response_data['choices']) > 0:
                response_text = response_data['choices'][0]['message']['content']
                reasoning_text = response_data['choices'][0]['message']['reasoning']

                # Extract metadata from response
                usage = response_data.get('usage', {})
                actual_model = response_data.get('model', model_name)
                provider = response_data.get('provider', None)
                finish_reason = response_data['choices'][0].get('finish_reason', 'unknown')
                
                # Report response details if enabled
                if self.report_model_config:
                    print(f"\n{'='*80}")
                    print("LLM API RESPONSE RECEIVED")
                    print(f"{'='*80}")
                    print(f"Actual Model Used: {actual_model}")
                    print(f"Finish Reason: {finish_reason}")
                    print(f"Prompt Tokens: {usage.get('prompt_tokens', 'unknown')}")
                    print(f"Completion Tokens: {usage.get('completion_tokens', 'unknown')}")
                    print(f"Total Tokens: {usage.get('total_tokens', 'unknown')}")
                    print(f"Response Length: {len(response_text)} characters")
                    print(f"{'='*80}\n")

                
                # Log the LLM response if logging is enabled
                metadata = {
                    'api_url': self.base_url,
                    'provider': provider,
                    'provider_sort': 'throughput',
                    'actual_model_used': actual_model,
                    'requested_model': model_name,
                    'intelligence_level': intelligence_level,
                    'max_tokens': max_tokens,
                    'temperature': temperature,
                    'prompt_tokens': usage.get('prompt_tokens', 'unknown'),
                    'completion_tokens': usage.get('completion_tokens', 'unknown'),
                    'total_tokens': usage.get('total_tokens', 'unknown'),
                    'finish_reason': finish_reason
                }
                self._log_llm_response(prompt, response_text, model_name, intelligence_level, 
                                     max_tokens, temperature, metadata)
                
                return response_text, reasoning_text, model_name, metadata
            else:
                raise Exception("No response content found in API response")

        # raise an error if the request fails
        except requests.exceptions.RequestException as e:
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_detail = e.response.json()
                    raise Exception(f"API request failed: {str(e)} - Details: {error_detail}")
                except:
                    raise Exception(f"API request failed: {str(e)} - Status: {e.response.status_code}")
            else:
                raise Exception(f"API request failed: {str(e)}")
        
        # raise an error if the response is not valid
        except json.JSONDecodeError as e:
            raise Exception(f"Failed to parse API response: {str(e)}")
        
        # raise an error if the request fails
        except Exception as e:
            import traceback
            print(f"[ERROR] Unexpected error in API request: {str(e)}")
            print(f"[ERROR] Exception type: {type(e)}")
            traceback.print_exc()
            raise Exception(f"Unexpected error in API request: {str(e)}")
    
    
    # === TASK-SPECIFIC METHODS ===
    # These methods provide high-level interfaces for specific tasks,
    # abstracting away model selection and prompt engineering details.
    
    def generate_agent_summary(self, agent_data: Dict[str, Any], max_tokens: int = 1000) -> str:
        """
        Generate a comprehensive personal summary for an agent.
        
        Args:
            agent_data: Dictionary containing agent information (L2 data, traits, etc.)
            max_tokens: Maximum tokens for the response
            
        Returns:
            Generated summary text
        """
        # Use reasoning model for comprehensive summaries
        prompt = self._build_summary_prompt(agent_data)
        response, reasoning, _, _ = self.make_request(
            prompt=prompt,
            intelligence_level=3,  # Reasoning model
            max_tokens=max_tokens,
            temperature=0.7
        )
        return response, reasoning
    
    def perceive_event(self, event_data: Dict[str, Any], agent_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze an event from an agent's perspective.
        
        Args:
            event_data: Dictionary containing event information
            agent_context: Dictionary containing agent state and context
            
        Returns:
            Dictionary with perception, impact_score, and analysis_type
        """
        # Use reasoning model for perception
        prompt = self._build_perception_prompt(event_data, agent_context)
        response, *_ = self.make_request(
            prompt=prompt,
            intelligence_level=3,  # Reasoning model
            max_tokens=300,
            temperature=0.3
        )
        return self._parse_perception_response(response)
    
    def get_text_embedding(self, text: str) -> List[float]:
        """
        Get embedding for a text string.
        
        Args:
            text: Text to embed
            
        Returns:
            List of float values representing the embedding
        """
        if self.use_mock_embeddings:
            return self._get_mock_embedding(text)
        else:
            return self._get_openai_embedding(text)
    
    def _build_summary_prompt(self, agent_data: Dict[str, Any]) -> str:
        """Build prompt for agent summary generation."""
        # Extract key information from agent data
        name = agent_data.get('name', 'Unknown')
        age = agent_data.get('age', 'Unknown')
        location = agent_data.get('location', 'Unknown')
        occupation = agent_data.get('occupation', 'Unknown')
        education = agent_data.get('education', 'Unknown')
        
        prompt = f"""Create a comprehensive personal summary for the following individual:

Name: {name}
Age: {age}
Location: {location}
Occupation: {occupation}
Education: {education}

Additional Information:
{json.dumps(agent_data, indent=2)}

Generate a narrative summary that captures their personality, values, lifestyle, and key characteristics.
Write in third person, as if you're describing this person to someone who has never met them."""
        
        return prompt
    
    def _build_perception_prompt(self, event_data: Dict[str, Any], agent_context: Dict[str, Any]) -> str:
        """Build prompt for event perception."""
        event_content = event_data.get('content', '')
        event_type = event_data.get('event_type', 'unknown')
        
        prompt = f"""You are an intelligent agent analyzing an event in a simulation. Respond as if you are personally experiencing this event.

EVENT TO ANALYZE:
Type: {event_type}
Content: {event_content}

YOUR CURRENT STATE:
{json.dumps(agent_context, indent=2)}

ANALYSIS TASK:
1. Determine if this event should be analyzed in historical context or as an immediate reaction
2. Score the personal impact of this event on a scale of 1-10

RESPOND WITH ONLY:
ANALYSIS_TYPE: <historical_context|immediate_reaction>
IMPACT_SCORE: <1-10>
REASONING: <brief explanation in first person>"""
        
        return prompt
    
    def _parse_perception_response(self, response: str) -> Dict[str, Any]:
        """Parse the LLM perception response."""
        result = {
            'perception': '',
            'impact_score': 5,
            'analysis_type': 'immediate_reaction'
        }
        
        for line in response.split('\n'):
            if line.startswith('ANALYSIS_TYPE:'):
                result['analysis_type'] = line.split(':', 1)[1].strip()
            elif line.startswith('IMPACT_SCORE:'):
                try:
                    result['impact_score'] = int(line.split(':', 1)[1].strip())
                except ValueError:
                    pass
            elif line.startswith('REASONING:'):
                result['perception'] = line.split(':', 1)[1].strip()
        
        return result
    
    def _get_mock_embedding(self, text: str) -> List[float]:
        """Generate a simple hash-based embedding for testing."""
        import hashlib
        import struct
        
        # Create a hash of the text
        text_hash = hashlib.sha256(text.encode('utf-8')).digest()
        
        # Convert to float values
        embedding = []
        for i in range(0, len(text_hash), 4):
            if i + 4 <= len(text_hash):
                # Convert 4 bytes to float
                value = struct.unpack('>f', text_hash[i:i+4])[0]
                embedding.append(value)
        
        # Pad to 384 dimensions (standard embedding size)
        target_size = 384
        if len(embedding) < target_size:
            embedding.extend([0.0] * (target_size - len(embedding)))
        elif len(embedding) > target_size:
            embedding = embedding[:target_size]
        
        return embedding
    
    def _get_openai_embedding(self, text: str) -> List[float]:
        """Get embedding using OpenAI API."""
        if not self.openai_api_key:
            raise ValueError("OPENAI_API_KEY not set. Cannot generate embeddings.")
        
        try:
            import openai
            client = openai.OpenAI(api_key=self.openai_api_key)
            response = client.embeddings.create(
                model="text-embedding-ada-002",
                input=text
            )
            return response.data[0].embedding
        except ImportError:
            raise ImportError("openai package not installed. Install with: pip install openai")
        except Exception as e:
            raise Exception(f"Failed to get OpenAI embedding: {e}")
    
    def test_connection(self, intelligence_level: int = None) -> bool:
        """
        Test the API connection with a simple prompt.
        
        Args:
            intelligence_level (int): Intelligence level to test with (defaults to env setting)
            
        Returns:
            bool: True if connection successful, False otherwise
        """
        if intelligence_level is None:
            intelligence_level = int(os.getenv('TEST_CONNECTION_INTELLIGENCE_LEVEL', '2'))
        
        try:
            test_prompt = "Hello, this is a test message. Please respond with 'Test successful.'"
            max_tokens = int(os.getenv('TEST_CONNECTION_MAX_TOKENS', '10'))
            response, *_ = self.make_request(test_prompt, intelligence_level, max_tokens=max_tokens)
            return "Test successful" in response
        except Exception as e:
            print(f"Connection test failed: {e}")
            return False
