"""
Model Registry

Manages available Ollama models, their capabilities, and intelligent selection.
"""

import logging
import requests
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta

logger = logging.getLogger("owlin.services.model_registry")


# Model capabilities database
MODEL_CAPABILITIES = {
    "qwen2.5-coder:7b": {
        "max_context": 128000,
        "specialty": "code",
        "speed": "medium",
        "description": "Best for large codebases and complex analysis"
    },
    "deepseek-coder:6.7b": {
        "max_context": 32000,
        "specialty": "code",
        "speed": "fast",
        "description": "Fast code analysis and debugging"
    },
    "codellama:7b": {
        "max_context": 16000,
        "specialty": "code",
        "speed": "medium",
        "description": "Legacy code support"
    },
    "llama3.2:3b": {
        "max_context": 128000,
        "specialty": "general",
        "speed": "very_fast",
        "description": "Quick questions and general assistance"
    },
    "llama3:8b": {
        "max_context": 128000,
        "specialty": "general",
        "speed": "fast",
        "description": "General purpose"
    },
}


@dataclass
class ModelInfo:
    """Information about an available model."""
    name: str
    max_context: int
    specialty: str  # "code", "general"
    speed: str  # "very_fast", "fast", "medium", "slow"
    description: str
    size_bytes: int = 0
    modified_at: Optional[str] = None
    available: bool = True


class ModelRegistry:
    """Registry of available Ollama models with capability management."""
    
    def __init__(self, ollama_url: str = "http://localhost:11434"):
        """
        Initialize model registry.
        
        Args:
            ollama_url: Base URL for Ollama API
        """
        self.ollama_url = ollama_url
        self._models: Dict[str, ModelInfo] = {}
        self._cache_time: Optional[datetime] = None
        self._cache_ttl = timedelta(minutes=5)
        
        # Try initial model discovery
        try:
            self.refresh()
            logger.info(f"Model registry initialized with {len(self._models)} models")
        except Exception as e:
            logger.warning(f"Initial model discovery failed: {e}")
    
    def refresh(self) -> None:
        """Refresh available models from Ollama."""
        try:
            response = requests.get(f"{self.ollama_url}/api/tags", timeout=5)
            if response.status_code == 200:
                data = response.json()
                self._parse_models(data.get("models", []))
                self._cache_time = datetime.now()
                logger.info(f"Refreshed model registry: {len(self._models)} models available")
            else:
                logger.warning(f"Failed to refresh models: HTTP {response.status_code}")
        except Exception as e:
            logger.error(f"Error refreshing models: {e}")
    
    def _parse_models(self, models_data: List[Dict]) -> None:
        """Parse model data from Ollama API."""
        self._models.clear()
        
        for model_data in models_data:
            name = model_data.get("name", "")
            
            # Get capabilities from database, or use defaults
            capabilities = MODEL_CAPABILITIES.get(name, {
                "max_context": 16000,  # Conservative default
                "specialty": "general",
                "speed": "medium",
                "description": "Unknown model"
            })
            
            model_info = ModelInfo(
                name=name,
                max_context=capabilities["max_context"],
                specialty=capabilities["specialty"],
                speed=capabilities["speed"],
                description=capabilities["description"],
                size_bytes=model_data.get("size", 0),
                modified_at=model_data.get("modified_at"),
                available=True
            )
            
            self._models[name] = model_info
            logger.debug(f"Registered model: {name} (context: {model_info.max_context}, specialty: {model_info.specialty})")
    
    def get_available_models(self, refresh_if_stale: bool = True) -> List[ModelInfo]:
        """
        Get list of available models.
        
        Args:
            refresh_if_stale: Whether to refresh if cache is stale
            
        Returns:
            List of available model info
        """
        if refresh_if_stale and self._is_cache_stale():
            self.refresh()
        
        return list(self._models.values())
    
    def get_model(self, name: str) -> Optional[ModelInfo]:
        """Get info for a specific model."""
        return self._models.get(name)
    
    def is_model_available(self, name: str) -> bool:
        """Check if a specific model is available."""
        if self._is_cache_stale():
            self.refresh()
        return name in self._models
    
    def select_best_model(
        self,
        question_type: str,
        context_size: int,
        code_files_count: int,
        preferred_models: Optional[List[str]] = None
    ) -> Tuple[Optional[str], int]:
        """
        Select best model for the request.
        
        Args:
            question_type: Type of question ("debugging", "code_flow", "general")
            context_size: Requested context size
            code_files_count: Number of code files to include
            preferred_models: Preferred model names in priority order
            
        Returns:
            Tuple of (selected_model_name, effective_context_size)
        """
        if self._is_cache_stale():
            self.refresh()
        
        if not self._models:
            logger.warning("No models available for selection")
            return None, min(context_size, 16000)
        
        # Filter to preferred models if specified
        candidates = []
        if preferred_models:
            for model_name in preferred_models:
                if model_name in self._models:
                    candidates.append(self._models[model_name])
        
        if not candidates:
            # Use all available models
            candidates = list(self._models.values())
        
        # Score each model
        scored_models = []
        for model in candidates:
            score = self._score_model(model, question_type, context_size, code_files_count)
            scored_models.append((score, model))
        
        # Sort by score (highest first)
        scored_models.sort(key=lambda x: x[0], reverse=True)
        
        if scored_models:
            best_model = scored_models[0][1]
            effective_context = min(context_size, best_model.max_context)
            
            logger.info(
                f"Selected model: {best_model.name} "
                f"(context: {effective_context}/{best_model.max_context}, "
                f"type: {question_type}, files: {code_files_count})"
            )
            
            return best_model.name, effective_context
        
        return None, min(context_size, 16000)
    
    def _score_model(
        self,
        model: ModelInfo,
        question_type: str,
        context_size: int,
        code_files_count: int
    ) -> float:
        """Score a model for selection."""
        score = 0.0
        
        # Context window scoring (very important for large requests)
        if context_size > 64000:
            # Large context needed
            if model.max_context >= 128000:
                score += 50.0
            elif model.max_context >= 64000:
                score += 30.0
            elif model.max_context >= 32000:
                score += 15.0
            else:
                score += 5.0
        elif context_size > 32000:
            # Medium-large context
            if model.max_context >= 64000:
                score += 40.0
            elif model.max_context >= 32000:
                score += 35.0
            elif model.max_context >= 16000:
                score += 20.0
            else:
                score += 10.0
        else:
            # Small context - any model works
            score += 25.0
        
        # Specialty scoring
        if question_type in ["debugging", "code_flow"] and model.specialty == "code":
            score += 30.0
        elif question_type == "general" and model.specialty == "general":
            score += 20.0
        elif model.specialty == "code":
            # Code models are good for everything
            score += 15.0
        
        # Speed scoring (matters for quick questions)
        if code_files_count <= 2:
            # Quick question - prefer fast models
            if model.speed == "very_fast":
                score += 20.0
            elif model.speed == "fast":
                score += 15.0
            elif model.speed == "medium":
                score += 10.0
        else:
            # Complex question - speed less important
            if model.speed == "very_fast":
                score += 5.0
            elif model.speed == "fast":
                score += 8.0
            elif model.speed == "medium":
                score += 10.0
        
        # Penalty if context size exceeds model capability
        if context_size > model.max_context:
            score -= 20.0
        
        return score
    
    def _is_cache_stale(self) -> bool:
        """Check if model cache is stale."""
        if self._cache_time is None:
            return True
        return datetime.now() - self._cache_time > self._cache_ttl
    
    def get_model_stats(self) -> Dict:
        """Get statistics about available models."""
        if self._is_cache_stale():
            self.refresh()
        
        code_models = [m for m in self._models.values() if m.specialty == "code"]
        general_models = [m for m in self._models.values() if m.specialty == "general"]
        
        max_context = max([m.max_context for m in self._models.values()]) if self._models else 0
        
        return {
            "total_models": len(self._models),
            "code_models": len(code_models),
            "general_models": len(general_models),
            "max_context_available": max_context,
            "models": {name: {
                "max_context": model.max_context,
                "specialty": model.specialty,
                "speed": model.speed,
                "size_mb": round(model.size_bytes / (1024 * 1024), 1)
            } for name, model in self._models.items()},
            "cache_age_seconds": (datetime.now() - self._cache_time).total_seconds() if self._cache_time else None
        }


# Global registry instance
_registry: Optional[ModelRegistry] = None


def get_registry(ollama_url: str = "http://localhost:11434") -> ModelRegistry:
    """Get or create global model registry."""
    global _registry
    if _registry is None:
        _registry = ModelRegistry(ollama_url)
    return _registry


def refresh_registry() -> None:
    """Refresh the global registry."""
    if _registry:
        _registry.refresh()

