#!/usr/bin/env python3
"""
Testing Configuration
Provides testing utilities and configuration for the World_Sim system.
"""

import os
from typing import Any, Dict

def is_testing_mode() -> bool:
    """Check if the system is running in testing mode."""
    return os.getenv('TESTING_MODE', 'false').lower() == 'true'

def should_mock_llm() -> bool:
    """Check if LLM should be mocked for testing."""
    return os.getenv('MOCK_LLM', 'false').lower() == 'true'

class MockEvent:
    """Mock event class for testing purposes."""
    
    def __init__(self, event_id: int, event_type: str, **kwargs):
        self.event_id = event_id
        self.event_type = event_type
        for key, value in kwargs.items():
            setattr(self, key, value)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert mock event to dictionary."""
        return {
            'event_id': self.event_id,
            'event_type': self.event_type,
            **{k: v for k, v in self.__dict__.items() if not k.startswith('_')}
        }

# Set testing mode for this session
os.environ['TESTING_MODE'] = 'true'
os.environ['MOCK_LLM'] = 'true'

