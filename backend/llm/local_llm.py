"""
Local LLM Interface for Offline Inference

This module provides a unified interface for local LLM inference using
quantized models (GGUF format) with CPU/GPU support and fallback mechanisms.
"""

from __future__ import annotations
import logging
import time
import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from pathlib import Path

try:
    from llama_cpp import Llama
    LLAMA_CPP_AVAILABLE = True
except ImportError:
    LLAMA_CPP_AVAILABLE = False
    Llama = None

try:
    import torch
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    torch = None

LOGGER = logging.getLogger("owlin.llm.local_llm")


class LLMProvider(Enum):
    """Supported LLM providers."""
    LLAMA_CPP = "llama_cpp"
    TORCH = "torch"
    MOCK = "mock"  # For testing


class LLMDevice(Enum):
    """Supported inference devices."""
    CPU = "cpu"
    GPU = "gpu"
    AUTO = "auto"


@dataclass
class LLMConfig:
    """Configuration for local LLM inference."""
    model_path: str
    provider: LLMProvider = LLMProvider.LLAMA_CPP
    device: LLMDevice = LLMDevice.AUTO
    max_tokens: int = 2048
    temperature: float = 0.0  # Deterministic output
    top_p: float = 0.9
    top_k: int = 40
    repeat_penalty: float = 1.1
    context_length: int = 4096
    n_threads: int = 4
    n_gpu_layers: int = 0  # 0 = CPU only, -1 = all layers on GPU
    verbose: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "model_path": self.model_path,
            "provider": self.provider.value,
            "device": self.device.value,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "top_p": self.top_p,
            "top_k": self.top_k,
            "repeat_penalty": self.repeat_penalty,
            "context_length": self.context_length,
            "n_threads": self.n_threads,
            "n_gpu_layers": self.n_gpu_layers,
            "verbose": self.verbose
        }


@dataclass
class LLMResult:
    """Result of LLM inference."""
    text: str
    tokens_generated: int
    inference_time: float
    model_used: str
    provider: str
    device: str
    success: bool
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "text": self.text,
            "tokens_generated": self.tokens_generated,
            "inference_time": self.inference_time,
            "model_used": self.model_used,
            "provider": self.provider,
            "device": self.device,
            "success": self.success,
            "error_message": self.error_message,
            "metadata": self.metadata
        }


class LocalLLMInterface:
    """Interface for local LLM inference with multiple backends."""
    
    def __init__(self, config: LLMConfig):
        """Initialize the LLM interface with configuration."""
        self.config = config
        self.model = None
        self.provider = None
        self.device = None
        self._initialize_provider()
        
        LOGGER.info(f"LLM Interface initialized with {self.provider} on {self.device}")
    
    def _initialize_provider(self):
        """Initialize the LLM provider based on configuration."""
        try:
            if self.config.provider == LLMProvider.LLAMA_CPP:
                self._initialize_llama_cpp()
            elif self.config.provider == LLMProvider.TORCH:
                self._initialize_torch()
            elif self.config.provider == LLMProvider.MOCK:
                self._initialize_mock()
            else:
                raise ValueError(f"Unsupported provider: {self.config.provider}")
                
        except Exception as e:
            LOGGER.error(f"Failed to initialize {self.config.provider}: {e}")
            # Fallback to mock provider
            self._initialize_mock()
    
    def _initialize_llama_cpp(self):
        """Initialize llama-cpp-python backend."""
        if not LLAMA_CPP_AVAILABLE:
            raise ImportError("llama-cpp-python not available")
        
        if not Path(self.config.model_path).exists():
            raise FileNotFoundError(f"Model file not found: {self.config.model_path}")
        
        # Determine device
        if self.config.device == LLMDevice.AUTO:
            self.device = LLMDevice.GPU if TORCH_AVAILABLE and torch.cuda.is_available() else LLMDevice.CPU
        else:
            self.device = self.config.device
        
        # Configure GPU layers
        n_gpu_layers = self.config.n_gpu_layers
        if self.device == LLMDevice.CPU:
            n_gpu_layers = 0
        
        # Initialize model
        self.model = Llama(
            model_path=self.config.model_path,
            n_ctx=self.config.context_length,
            n_threads=self.config.n_threads,
            n_gpu_layers=n_gpu_layers,
            verbose=self.config.verbose
        )
        
        self.provider = LLMProvider.LLAMA_CPP
        LOGGER.info(f"llama-cpp-python initialized with {self.config.model_path}")
    
    def _initialize_torch(self):
        """Initialize PyTorch backend (placeholder for future implementation)."""
        if not TORCH_AVAILABLE:
            raise ImportError("PyTorch not available")
        
        # This would be implemented for specific model formats
        raise NotImplementedError("PyTorch backend not yet implemented")
    
    def _initialize_mock(self):
        """Initialize mock backend for testing."""
        self.model = "mock_model"
        self.provider = LLMProvider.MOCK
        self.device = LLMDevice.CPU
        LOGGER.info("Mock LLM backend initialized for testing")
    
    def generate(self, prompt: str, **kwargs) -> LLMResult:
        """
        Generate text from a prompt.
        
        Args:
            prompt: Input prompt text
            **kwargs: Additional generation parameters
            
        Returns:
            LLMResult with generated text and metadata
        """
        start_time = time.time()
        
        try:
            if self.provider == LLMProvider.MOCK:
                return self._generate_mock(prompt, start_time)
            elif self.provider == LLMProvider.LLAMA_CPP:
                return self._generate_llama_cpp(prompt, start_time, **kwargs)
            else:
                raise ValueError(f"Unsupported provider: {self.provider}")
                
        except Exception as e:
            LOGGER.error(f"LLM generation failed: {e}")
            return LLMResult(
                text="",
                tokens_generated=0,
                inference_time=time.time() - start_time,
                model_used=self.config.model_path,
                provider=self.provider.value,
                device=self.device.value,
                success=False,
                error_message=str(e)
            )
    
    def _generate_mock(self, prompt: str, start_time: float) -> LLMResult:
        """Generate mock response for testing."""
        # Simple mock responses based on prompt content
        if "invoice" in prompt.lower():
            mock_response = """{
    "supplier_name": "ACME Corporation Ltd",
    "invoice_number": "INV-2024-001",
    "invoice_date": "2024-01-15",
    "currency": "GBP",
    "subtotal": 100.00,
    "tax_amount": 20.00,
    "total_amount": 120.00,
    "line_items": [
        {
            "description": "Professional Services",
            "quantity": 10,
            "unit": "hours",
            "unit_price": 10.00,
            "line_total": 100.00
        }
    ],
    "confidence": 0.95,
    "needs_review": false
}"""
        elif "credit" in prompt.lower():
            mock_response = """Subject: Credit Request - Invoice INV-2024-001

Dear Accounts Team,

I am writing to request a credit for the following invoice:

Invoice Number: INV-2024-001
Amount: £120.00
Issue: Duplicate charge for services already paid

Please process this credit request at your earliest convenience.

Best regards,
Finance Team"""
        else:
            mock_response = "Mock LLM response generated successfully."
        
        return LLMResult(
            text=mock_response,
            tokens_generated=len(mock_response.split()),
            inference_time=time.time() - start_time,
            model_used="mock_model",
            provider=self.provider.value,
            device=self.device.value,
            success=True
        )
    
    def _generate_llama_cpp(self, prompt: str, start_time: float, **kwargs) -> LLMResult:
        """Generate using llama-cpp-python."""
        try:
            # Merge generation parameters
            generation_params = {
                "max_tokens": kwargs.get("max_tokens", self.config.max_tokens),
                "temperature": kwargs.get("temperature", self.config.temperature),
                "top_p": kwargs.get("top_p", self.config.top_p),
                "top_k": kwargs.get("top_k", self.config.top_k),
                "repeat_penalty": kwargs.get("repeat_penalty", self.config.repeat_penalty),
                "stop": kwargs.get("stop", ["</s>", "\n\n\n"]),
            }
            
            # Generate response
            response = self.model(prompt, **generation_params)
            
            # Extract text and metadata
            generated_text = response["choices"][0]["text"]
            tokens_generated = len(generated_text.split())
            
            return LLMResult(
                text=generated_text,
                tokens_generated=tokens_generated,
                inference_time=time.time() - start_time,
                model_used=self.config.model_path,
                provider=self.provider.value,
                device=self.device.value,
                success=True,
                metadata={
                    "finish_reason": response["choices"][0].get("finish_reason", "unknown"),
                    "usage": response.get("usage", {}),
                    "generation_params": generation_params
                }
            )
            
        except Exception as e:
            LOGGER.error(f"llama-cpp-python generation failed: {e}")
            return LLMResult(
                text="",
                tokens_generated=0,
                inference_time=time.time() - start_time,
                model_used=self.config.model_path,
                provider=self.provider.value,
                device=self.device.value,
                success=False,
                error_message=str(e)
            )
    
    def is_available(self) -> bool:
        """Check if the LLM interface is available and ready."""
        return self.model is not None and self.provider is not None
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the loaded model."""
        return {
            "provider": self.provider.value if self.provider else None,
            "device": self.device.value if self.device else None,
            "model_path": self.config.model_path,
            "config": self.config.to_dict(),
            "available": self.is_available()
        }
    
    def cleanup(self):
        """Clean up resources."""
        if self.model and hasattr(self.model, 'close'):
            self.model.close()
        self.model = None
        LOGGER.info("LLM interface cleaned up")


class LLMManager:
    """Manager for multiple LLM instances with fallback support."""
    
    def __init__(self, configs: List[LLMConfig]):
        """Initialize with multiple LLM configurations."""
        self.configs = configs
        self.llms = []
        self.active_llm = None
        self._initialize_llms()
    
    def _initialize_llms(self):
        """Initialize all configured LLMs."""
        for config in self.configs:
            try:
                llm = LocalLLMInterface(config)
                if llm.is_available():
                    self.llms.append(llm)
                    if self.active_llm is None:
                        self.active_llm = llm
                    LOGGER.info(f"LLM initialized: {config.provider.value}")
                else:
                    LOGGER.warning(f"LLM not available: {config.provider.value}")
            except Exception as e:
                LOGGER.error(f"Failed to initialize LLM {config.provider.value}: {e}")
        
        if not self.llms:
            LOGGER.error("No LLMs available, falling back to mock")
            mock_config = LLMConfig(
                model_path="mock",
                provider=LLMProvider.MOCK
            )
            self.active_llm = LocalLLMInterface(mock_config)
            self.llms.append(self.active_llm)
    
    def generate(self, prompt: str, **kwargs) -> LLMResult:
        """Generate text using the active LLM with fallback support."""
        if not self.active_llm:
            raise RuntimeError("No LLM available")
        
        try:
            return self.active_llm.generate(prompt, **kwargs)
        except Exception as e:
            LOGGER.error(f"Active LLM failed: {e}")
            # Try fallback LLMs
            for llm in self.llms:
                if llm != self.active_llm:
                    try:
                        LOGGER.info(f"Trying fallback LLM: {llm.provider.value}")
                        result = llm.generate(prompt, **kwargs)
                        if result.success:
                            self.active_llm = llm
                            return result
                    except Exception as fallback_error:
                        LOGGER.error(f"Fallback LLM failed: {fallback_error}")
                        continue
            
            # All LLMs failed, return error result
            return LLMResult(
                text="",
                tokens_generated=0,
                inference_time=0.0,
                model_used="none",
                provider="none",
                device="none",
                success=False,
                error_message=f"All LLMs failed: {e}"
            )
    
    def get_available_llms(self) -> List[Dict[str, Any]]:
        """Get information about all available LLMs."""
        return [llm.get_model_info() for llm in self.llms]
    
    def cleanup(self):
        """Clean up all LLM instances."""
        for llm in self.llms:
            llm.cleanup()
        self.llms.clear()
        self.active_llm = None
