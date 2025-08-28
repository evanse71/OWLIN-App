#!/usr/bin/env python3
"""
LLM Runtime Wrapper

Local LLM runtime using llama.cpp/gguf models with no network calls
"""

import os
import time
import logging
from pathlib import Path
from typing import Optional, Dict, Any
from threading import Lock

logger = logging.getLogger(__name__)

class LlmUnavailable(Exception):
    """Raised when LLM model is not available"""
    pass

class LlmTimeout(Exception):
    """Raised when LLM generation times out"""
    pass

class LlmRuntime:
    """Local LLM runtime using llama.cpp/gguf models"""
    
    def __init__(self):
        self._model = None
        self._model_path = None
        self._lock = Lock()
        self._initialized = False
    
    def load_model(self, model_path: str) -> bool:
        """
        Load LLM model (singleton pattern)
        
        Args:
            model_path: Path to the GGUF model file
            
        Returns:
            True if model loaded successfully
        """
        model_path = Path(model_path)
        
        with self._lock:
            # Check if model already loaded
            if self._model is not None and self._model_path == str(model_path):
                return True
            
            # Check if model file exists
            if not model_path.exists():
                logger.warning(f"⚠️ LLM model not found: {model_path}")
                raise LlmUnavailable(f"Model file not found: {model_path}")
            
            try:
                # Try to import llama-cpp-python
                import llama_cpp
                
                # Load the model
                logger.info(f"🔄 Loading LLM model: {model_path}")
                
                self._model = llama_cpp.Llama(
                    model_path=str(model_path),
                    n_ctx=2048,  # Context window
                    n_threads=4,  # Number of CPU threads
                    n_gpu_layers=0,  # No GPU layers for now
                    verbose=False
                )
                
                self._model_path = str(model_path)
                self._initialized = True
                
                logger.info("✅ LLM model loaded successfully")
                return True
                
            except ImportError:
                logger.warning("⚠️ llama-cpp-python not installed. LLM features disabled.")
                raise LlmUnavailable("llama-cpp-python not installed")
                
            except Exception as e:
                logger.error(f"❌ Failed to load LLM model: {e}")
                raise LlmUnavailable(f"Model loading failed: {e}")
    
    def generate(self, prompt: str, max_tokens: int = 128, timeout_ms: int = 800) -> str:
        """
        Generate text using the loaded model
        
        Args:
            prompt: Input prompt
            max_tokens: Maximum tokens to generate
            timeout_ms: Timeout in milliseconds
            
        Returns:
            Generated text (trimmed)
        """
        if not self._initialized or self._model is None:
            raise LlmUnavailable("Model not loaded")
        
        try:
            start_time = time.time()
            timeout_seconds = timeout_ms / 1000.0
            
            # Generate response
            response = self._model(
                prompt,
                max_tokens=max_tokens,
                temperature=0.1,  # Low temperature for consistent results
                stop=["\n\n", "```", "---"],  # Stop sequences
                echo=False
            )
            
            generation_time = time.time() - start_time
            
            if generation_time > timeout_seconds:
                raise LlmTimeout(f"Generation timed out after {generation_time:.2f}s")
            
            # Extract and clean the generated text
            if hasattr(response, 'choices') and response.choices:
                generated_text = response.choices[0].text.strip()
            elif isinstance(response, str):
                generated_text = response.strip()
            else:
                generated_text = str(response).strip()
            
            logger.debug(f"🤖 LLM generated {len(generated_text)} chars in {generation_time:.2f}s")
            
            return generated_text
            
        except LlmTimeout:
            raise
        except Exception as e:
            logger.error(f"❌ LLM generation failed: {e}")
            raise LlmUnavailable(f"Generation failed: {e}")
    
    def is_available(self) -> bool:
        """Check if LLM is available and loaded"""
        return self._initialized and self._model is not None
    
    def get_model_info(self) -> Optional[Dict[str, Any]]:
        """Get information about the loaded model"""
        if not self.is_available():
            return None
        
        return {
            'model_path': self._model_path,
            'initialized': self._initialized,
            'context_size': getattr(self._model, 'n_ctx', 'unknown'),
            'threads': getattr(self._model, 'n_threads', 'unknown')
        }

# Global LLM runtime instance
_llm_runtime: Optional[LlmRuntime] = None

def get_llm_runtime() -> LlmRuntime:
    """Get global LLM runtime instance"""
    global _llm_runtime
    if _llm_runtime is None:
        _llm_runtime = LlmRuntime()
    return _llm_runtime 