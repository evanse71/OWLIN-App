"""
Explorer Configuration

Centralized configuration for code exploration features.
All limits and settings are configurable via environment variables or defaults.
"""

import os
from typing import Dict, Any
from backend.config import env_int, env_str, env_float

logger = None  # Will be set when logging is available


class ExplorerConfig:
    """Configuration for code exploration features."""
    
    def __init__(self):
        """Initialize configuration from environment variables or defaults."""
        # Performance settings - conservative defaults for performance
        self.max_search_results = env_int("EXPLORER_MAX_SEARCH_RESULTS", 10)  # Reduced from 20 to 10 for faster searches
        self.max_files_per_plan = env_int("EXPLORER_MAX_FILES_PER_PLAN", 20)  # Reduced from 100 to 20
        self.max_lines_per_file = env_int("EXPLORER_MAX_LINES_PER_FILE", 2500)  # Reduced from 50000 to 2500
        self.max_traces = env_int("EXPLORER_MAX_TRACES", 20)  # Was 2
        self.max_functions = env_int("EXPLORER_MAX_FUNCTIONS", 50)  # Was 3
        self.max_findings = env_int("EXPLORER_MAX_FINDINGS", 300)  # Reduced from 1000 to 300 (truncate by count)
        
        # Caching settings
        self.cache_ttl = env_int("EXPLORER_CACHE_TTL", 300)  # 5 minutes
        self.max_cache_size = env_int("EXPLORER_MAX_CACHE_SIZE", 100)
        self.file_cache_size = env_int("EXPLORER_FILE_CACHE_SIZE", 50)
        
        # Timeout settings - reduced for dev usage
        self.exploration_timeout = env_int("EXPLORER_TIMEOUT", 45)  # Reduced from 90 to 45 seconds for faster dev feedback
        self.per_step_timeout = env_int("EXPLORER_PER_STEP_TIMEOUT", 15)  # Reduced from 30 to 15 seconds
        
        # Token budget settings - disabled for local processing
        self.max_findings_tokens = env_int("EXPLORER_MAX_FINDINGS_TOKENS", 0)  # 0 = no limit (was 5000)
        
        # Retry settings
        self.max_retries = env_int("EXPLORER_MAX_RETRIES", 3)
        self.retry_initial_delay = env_float("EXPLORER_RETRY_INITIAL_DELAY", 1.0)
        self.retry_max_delay = env_float("EXPLORER_RETRY_MAX_DELAY", 10.0)
        
        # Circuit breaker settings
        self.circuit_breaker_threshold = env_int("EXPLORER_CB_THRESHOLD", 5)
        self.circuit_breaker_timeout = env_int("EXPLORER_CB_TIMEOUT", 60)
        
        # Multi-turn conversation settings
        self.max_conversation_turns = env_int("EXPLORER_MAX_TURNS", 20)  # Increased for deeper autonomous exploration
        
        # Parallel execution settings - conservative defaults
        self.max_parallel_searches = env_int("EXPLORER_MAX_PARALLEL_SEARCHES", 4)  # Number of searches to run concurrently
        self.max_parallel_file_reads = env_int("EXPLORER_MAX_PARALLEL_FILE_READS", 6)  # Increased from 3 to 6
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return {
            "max_search_results": self.max_search_results,
            "max_files_per_plan": self.max_files_per_plan,
            "max_lines_per_file": self.max_lines_per_file,
            "max_traces": self.max_traces,
            "max_functions": self.max_functions,
            "max_findings": self.max_findings,
            "cache_ttl": self.cache_ttl,
            "max_cache_size": self.max_cache_size,
            "file_cache_size": self.file_cache_size,
            "exploration_timeout": self.exploration_timeout,
            "per_step_timeout": self.per_step_timeout,
            "max_findings_tokens": self.max_findings_tokens,
            "max_retries": self.max_retries,
            "retry_initial_delay": self.retry_initial_delay,
            "retry_max_delay": self.retry_max_delay,
            "circuit_breaker_threshold": self.circuit_breaker_threshold,
            "circuit_breaker_timeout": self.circuit_breaker_timeout,
            "max_conversation_turns": self.max_conversation_turns,
            "max_parallel_searches": self.max_parallel_searches,
            "max_parallel_file_reads": self.max_parallel_file_reads,
        }
    
    def update(self, **kwargs):
        """Update configuration values."""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
            else:
                raise ValueError(f"Unknown configuration key: {key}")


# Global configuration instance
_config: ExplorerConfig = None


def get_config() -> ExplorerConfig:
    """Get global explorer configuration instance."""
    global _config
    if _config is None:
        _config = ExplorerConfig()
    return _config


def reset_config():
    """Reset global configuration (useful for testing)."""
    global _config
    _config = None

