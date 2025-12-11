"""
Numerical Settings Configuration
Author: Tristan Brigham

This file contains all numerical parameters and configuration values
that were previously stored in environment variables. This makes the
system more maintainable and Python-native.
"""

import os
from typing import Dict, Any, Union

class NumericalSettings:
    """Centralized configuration for all numerical parameters and settings."""
    
    def __init__(self):
        """Initialize settings with default values."""
        self._load_settings()
    
    def _load_settings(self):
        """Load settings from environment variables with defaults."""
        
        # Memory System Configuration
        self.MEMORY_SALIENCE_PARAM = float(os.getenv('MEMORY_SALIENCE_PARAM', '1.0'))
        self.MEMORY_IMPORTANCE_PARAM = float(os.getenv('MEMORY_IMPORTANCE_PARAM', '0.5'))
        self.MEMORY_TIME_DECAY_PARAM = float(os.getenv('MEMORY_TIME_DECAY_PARAM', '1.0'))
        self.MEMORY_MAX_IMPORTANCE_TO_FORGET_MEAN = float(os.getenv('MEMORY_MAX_IMPORTANCE_TO_FORGET_MEAN', '3.0'))
        self.MEMORY_MAX_IMPORTANCE_TO_FORGET_STD = float(os.getenv('MEMORY_MAX_IMPORTANCE_TO_FORGET_STD', '0.4'))
        self.MIN_IMPORTANCE_TO_SAVE_MEMORY = int(os.getenv('MIN_IMPORTANCE_TO_SAVE_MEMORY', '4'))
        self.MEMORY_MIN_PERSIST_TIME = int(os.getenv('MEMORY_MIN_PERSIST_TIME', '604800'))  # 7 days in seconds
        self.MEMORY_TOP_M_TO_RETURN = int(os.getenv('MEMORY_TOP_M_TO_RETURN', '7'))
        
        # Memory Intensity Thresholds
        self.MEMORY_RETRIEVAL_THRESHOLD = int(os.getenv('MEMORY_RETRIEVAL_THRESHOLD', '3'))
        self.MEMORY_CREATION_THRESHOLD = int(os.getenv('MEMORY_CREATION_THRESHOLD', '4'))
        
        # LLM Configuration Parameters
        self.DEFAULT_INTELLIGENCE_LEVEL = int(os.getenv('DEFAULT_INTELLIGENCE_LEVEL', '3'))
        self.PERCEPTION_INTELLIGENCE_LEVEL = int(os.getenv('PERCEPTION_INTELLIGENCE_LEVEL', '3'))
        self.MEMORY_CREATION_INTELLIGENCE_LEVEL = int(os.getenv('MEMORY_CREATION_INTELLIGENCE_LEVEL', '3'))
        self.TEST_CONNECTION_INTELLIGENCE_LEVEL = int(os.getenv('TEST_CONNECTION_INTELLIGENCE_LEVEL', '3'))
        
        self.DEFAULT_MAX_TOKENS = int(os.getenv('DEFAULT_MAX_TOKENS', '1000'))
        self.PERCEPTION_MAX_TOKENS = int(os.getenv('PERCEPTION_MAX_TOKENS', '300'))
        self.MEMORY_CREATION_MAX_TOKENS = int(os.getenv('MEMORY_CREATION_MAX_TOKENS', '500'))
        self.TEST_CONNECTION_MAX_TOKENS = int(os.getenv('TEST_CONNECTION_MAX_TOKENS', '10'))
        
        self.DEFAULT_TEMPERATURE = float(os.getenv('DEFAULT_TEMPERATURE', '0.7'))
        self.PERCEPTION_TEMPERATURE = float(os.getenv('PERCEPTION_TEMPERATURE', '0.3'))
        self.MEMORY_CREATION_TEMPERATURE = float(os.getenv('MEMORY_CREATION_TEMPERATURE', '0.4'))
        
        self.PERCEPTION_HISTORY_LIMIT = int(os.getenv('PERCEPTION_HISTORY_LIMIT', '5'))
        self.MEMORY_CREATION_HISTORY_LIMIT = int(os.getenv('MEMORY_CREATION_HISTORY_LIMIT', '10'))

        # Personal Summary Generation Parameters
        # Primary attempt token cap (large to reduce truncation); can be overridden via env
        self.PERSONAL_SUMMARY_MAX_TOKENS = int(os.getenv('PERSONAL_SUMMARY_MAX_TOKENS', '10000'))
        # Retry attempt token cap for concise version if tag compliance fails
        self.PERSONAL_SUMMARY_RETRY_MAX_TOKENS = int(os.getenv('PERSONAL_SUMMARY_RETRY_MAX_TOKENS', '3000'))
        # Specific temperature/intelligence for personal summaries
        self.PERSONAL_SUMMARY_TEMPERATURE = float(os.getenv('PERSONAL_SUMMARY_TEMPERATURE', '0.7'))
        self.PERSONAL_SUMMARY_INTELLIGENCE_LEVEL = int(os.getenv('PERSONAL_SUMMARY_INTELLIGENCE_LEVEL', '3'))
        
        # Agent Configuration
        self.AGENT_MAX_RECENT_EVENTS = int(os.getenv('AGENT_MAX_RECENT_EVENTS', '100'))
        self.AGENT_ACTION_HISTORY_LIMIT = int(os.getenv('AGENT_ACTION_HISTORY_LIMIT', '20'))
        self.AGENT_MESSAGE_HISTORY_LIMIT = int(os.getenv('AGENT_MESSAGE_HISTORY_LIMIT', '10'))
        self.DEFAULT_MEMORY_IMPACT_SCORE = int(os.getenv('DEFAULT_MEMORY_IMPACT_SCORE', '5'))
        self.MEMORY_SIMILARITY_SEARCH_K = int(os.getenv('MEMORY_SIMILARITY_SEARCH_K', '3'))
        
        # Memory Retrieval Parameters
        self.MEMORY_RETRIEVAL_MAX_RESULTS = int(os.getenv('MEMORY_RETRIEVAL_MAX_RESULTS', '7'))
        self.MEMORY_RETRIEVAL_CUTOFF_SCORE = float(os.getenv('MEMORY_RETRIEVAL_CUTOFF_SCORE', '0.1'))
        self.MEMORY_RETRIEVAL_RECENCY_WEIGHT = float(os.getenv('MEMORY_RETRIEVAL_RECENCY_WEIGHT', '0.33'))
        self.MEMORY_RETRIEVAL_IMPORTANCE_WEIGHT = float(os.getenv('MEMORY_RETRIEVAL_IMPORTANCE_WEIGHT', '0.33'))
        self.MEMORY_RETRIEVAL_RELEVANCE_WEIGHT = float(os.getenv('MEMORY_RETRIEVAL_RELEVANCE_WEIGHT', '0.34'))
        
        # Demo and Testing Configuration
        self.DEMO_EVENTS_TO_PROCESS = int(os.getenv('DEMO_EVENTS_TO_PROCESS', '50'))
        self.TEST_EVENT_COUNT = int(os.getenv('TEST_EVENT_COUNT', '10'))
        
        # Mood System Configuration
        # Emotional momentum: Lower alpha/beta values create more polarized agents (very reactive vs very stable)
        self.EMOTIONAL_MOMENTUM_ALPHA = float(os.getenv('EMOTIONAL_MOMENTUM_ALPHA', '0.5'))
        self.EMOTIONAL_MOMENTUM_BETA = float(os.getenv('EMOTIONAL_MOMENTUM_BETA', '0.5'))
        # Mood decay: Lower alpha/beta values create more variation in decay rates
        # Decay rates now use absolute values: 0.04 to 0.12 points per hour (centered around 0.07)
        self.MOOD_DECAY_ALPHA = float(os.getenv('MOOD_DECAY_ALPHA', '0.5'))
        self.MOOD_DECAY_BETA = float(os.getenv('MOOD_DECAY_BETA', '0.5'))
        self.MOOD_UPDATE_INTELLIGENCE_LEVEL = int(os.getenv('MOOD_UPDATE_INTELLIGENCE_LEVEL', '3'))
        self.MOOD_INFLUENCE_ON_IMPACT = float(os.getenv('MOOD_INFLUENCE_ON_IMPACT', '0.5'))
        self.MOOD_UPDATE_FREQUENCY = int(os.getenv('MOOD_UPDATE_FREQUENCY', '1'))
        self.MOOD_LLM_IMPACT_THRESHOLD = int(os.getenv('MOOD_LLM_IMPACT_THRESHOLD', '3'))
        # Error handling: Whether to throw errors on mood update failures or fall back silently
        self.MOOD_THROW_ON_FAILURE = os.getenv('MOOD_THROW_ON_FAILURE', 'true').lower() == 'true'
    
    def get_memory_settings(self) -> Dict[str, Union[int, float]]:
        """Get all memory-related settings."""
        return {
            'salience_param': self.MEMORY_SALIENCE_PARAM,
            'importance_param': self.MEMORY_IMPORTANCE_PARAM,
            'time_decay_param': self.MEMORY_TIME_DECAY_PARAM,
            'max_importance_to_forget_mean': self.MEMORY_MAX_IMPORTANCE_TO_FORGET_MEAN,
            'max_importance_to_forget_std': self.MEMORY_MAX_IMPORTANCE_TO_FORGET_STD,
            'min_importance_to_save': self.MIN_IMPORTANCE_TO_SAVE_MEMORY,
            'min_persist_time': self.MEMORY_MIN_PERSIST_TIME,
            'top_m_to_return': self.MEMORY_TOP_M_TO_RETURN,
            'retrieval_threshold': self.MEMORY_RETRIEVAL_THRESHOLD,
            'creation_threshold': self.MEMORY_CREATION_THRESHOLD,
            'similarity_search_k': self.MEMORY_SIMILARITY_SEARCH_K,
            'max_results': self.MEMORY_RETRIEVAL_MAX_RESULTS,
            'cutoff_score': self.MEMORY_RETRIEVAL_CUTOFF_SCORE,
            'recency_weight': self.MEMORY_RETRIEVAL_RECENCY_WEIGHT,
            'importance_weight': self.MEMORY_RETRIEVAL_IMPORTANCE_WEIGHT,
            'relevance_weight': self.MEMORY_RETRIEVAL_RELEVANCE_WEIGHT
        }
    
    def get_llm_settings(self) -> Dict[str, Union[int, float]]:
        """Get all LLM-related settings."""
        return {
            'default_intelligence': self.DEFAULT_INTELLIGENCE_LEVEL,
            'perception_intelligence': self.PERCEPTION_INTELLIGENCE_LEVEL,
            'memory_creation_intelligence': self.MEMORY_CREATION_INTELLIGENCE_LEVEL,
            'test_connection_intelligence': self.TEST_CONNECTION_INTELLIGENCE_LEVEL,
            'default_max_tokens': self.DEFAULT_MAX_TOKENS,
            'perception_max_tokens': self.PERCEPTION_MAX_TOKENS,
            'memory_creation_max_tokens': self.MEMORY_CREATION_MAX_TOKENS,
            'test_connection_max_tokens': self.TEST_CONNECTION_MAX_TOKENS,
            'default_temperature': self.DEFAULT_TEMPERATURE,
            'perception_temperature': self.PERCEPTION_TEMPERATURE,
            'memory_creation_temperature': self.MEMORY_CREATION_TEMPERATURE,
            'perception_history_limit': self.PERCEPTION_HISTORY_LIMIT,
            'memory_creation_history_limit': self.MEMORY_CREATION_HISTORY_LIMIT,
            'personal_summary_max_tokens': self.PERSONAL_SUMMARY_MAX_TOKENS,
            'personal_summary_retry_max_tokens': self.PERSONAL_SUMMARY_RETRY_MAX_TOKENS,
            'personal_summary_temperature': self.PERSONAL_SUMMARY_TEMPERATURE,
            'personal_summary_intelligence_level': self.PERSONAL_SUMMARY_INTELLIGENCE_LEVEL
        }
    
    def get_agent_settings(self) -> Dict[str, Union[int, float]]:
        """Get all agent-related settings."""
        return {
            'max_recent_events': self.AGENT_MAX_RECENT_EVENTS,
            'action_history_limit': self.AGENT_ACTION_HISTORY_LIMIT,
            'message_history_limit': self.AGENT_MESSAGE_HISTORY_LIMIT,
            'default_memory_impact_score': self.DEFAULT_MEMORY_IMPACT_SCORE
        }
    
    def get_mood_settings(self) -> Dict[str, Union[int, float]]:
        """Get all mood-related settings."""
        return {
            'emotional_momentum_alpha': self.EMOTIONAL_MOMENTUM_ALPHA,
            'emotional_momentum_beta': self.EMOTIONAL_MOMENTUM_BETA,
            'mood_decay_alpha': self.MOOD_DECAY_ALPHA,
            'mood_decay_beta': self.MOOD_DECAY_BETA,
            'update_intelligence_level': self.MOOD_UPDATE_INTELLIGENCE_LEVEL,
            'influence_on_impact': self.MOOD_INFLUENCE_ON_IMPACT,
            'update_frequency': self.MOOD_UPDATE_FREQUENCY
        }
    
    def get_demo_settings(self) -> Dict[str, Union[int, float]]:
        """Get all demo and testing settings."""
        return {
            'demo_events_to_process': self.DEMO_EVENTS_TO_PROCESS,
            'test_event_count': self.TEST_EVENT_COUNT
        }
    
    def get_all_settings(self) -> Dict[str, Any]:
        """Get all settings as a single dictionary."""
        return {
            'memory': self.get_memory_settings(),
            'llm': self.get_llm_settings(),
            'agent': self.get_agent_settings(),
            'mood': self.get_mood_settings(),
            'demo': self.get_demo_settings()
        }
    
    def update_setting(self, setting_name: str, value: Union[int, float, str]):
        """Update a specific setting dynamically."""
        if hasattr(self, setting_name):
            setattr(self, setting_name, value)
        else:
            raise ValueError(f"Unknown setting: {setting_name}")
    
    def reload_from_env(self):
        """Reload all settings from environment variables."""
        self._load_settings()

# Global instance for easy access
numerical_settings = NumericalSettings()

# Convenience functions for backward compatibility
def get_memory_settings():
    """Get memory settings (backward compatibility)."""
    return numerical_settings.get_memory_settings()

def get_llm_settings():
    """Get LLM settings (backward compatibility)."""
    return numerical_settings.get_llm_settings()

def get_agent_settings():
    """Get agent settings (backward compatibility)."""
    return numerical_settings.get_agent_settings()

def get_mood_settings():
    """Get mood settings (backward compatibility)."""
    return numerical_settings.get_mood_settings()

def get_demo_settings():
    """Get demo settings (backward compatibility)."""
    return numerical_settings.get_demo_settings()
