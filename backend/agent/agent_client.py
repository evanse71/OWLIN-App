"""
Agent Client Module

Handles communication with AI models (OpenAI, HuggingFace, or local models) for the Owlin Agent.
This module provides a unified interface for calling different AI models and handling responses.
"""

import logging
import os
import json
import time
from typing import Dict, Any, Optional, List
import requests

logger = logging.getLogger(__name__)

# Configuration
DEFAULT_MODEL = "gpt-3.5-turbo"
DEFAULT_MAX_TOKENS = 1000
DEFAULT_TEMPERATURE = 0.7

class AgentClient:
    """Client for calling AI models."""
    
    def __init__(self, model_name: str = None, api_key: str = None):
        """
        Initialize the agent client.
        
        Args:
            model_name: Name of the model to use
            api_key: API key for the model service
        """
        self.model_name = model_name or os.getenv("OPENAI_MODEL", DEFAULT_MODEL)
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.max_tokens = int(os.getenv("AGENT_MAX_TOKENS", DEFAULT_MAX_TOKENS))
        self.temperature = float(os.getenv("AGENT_TEMPERATURE", DEFAULT_TEMPERATURE))
        
        logger.info(f"🤖 Initialized Agent Client with model: {self.model_name}")
    
    def call_agent_model(self, prompt: str) -> str:
        """
        Call the AI model with a prompt and return the response.
        
        Args:
            prompt: The prompt to send to the model
            
        Returns:
            The model's response as a string
            
        Raises:
            Exception: If the model call fails
        """
        try:
            logger.debug(f"📤 Sending prompt to {self.model_name} ({len(prompt)} chars)")
            
            if self.model_name.startswith("gpt-"):
                return self._call_openai(prompt)
            elif self.model_name.startswith("claude-"):
                return self._call_anthropic(prompt)
            elif "huggingface" in self.model_name.lower():
                return self._call_huggingface(prompt)
            else:
                # Fallback to OpenAI
                return self._call_openai(prompt)
                
        except Exception as e:
            logger.error(f"❌ Model call failed: {str(e)}")
            return self._generate_fallback_response(prompt)
    
    def _call_openai(self, prompt: str) -> str:
        """Call OpenAI API."""
        if not self.api_key:
            raise Exception("OpenAI API key not configured")
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": "You are a helpful AI assistant for hospitality invoice management."},
                {"role": "user", "content": prompt}
            ],
            "max_tokens": self.max_tokens,
            "temperature": self.temperature
        }
        
        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers=headers,
            json=data,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            return result["choices"][0]["message"]["content"]
        else:
            raise Exception(f"OpenAI API error: {response.status_code} - {response.text}")
    
    def _call_anthropic(self, prompt: str) -> str:
        """Call Anthropic Claude API."""
        if not self.api_key:
            raise Exception("Anthropic API key not configured")
        
        headers = {
            "x-api-key": self.api_key,
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01"
        }
        
        data = {
            "model": self.model_name,
            "max_tokens": self.max_tokens,
            "messages": [
                {"role": "user", "content": prompt}
            ]
        }
        
        response = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers=headers,
            json=data,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            return result["content"][0]["text"]
        else:
            raise Exception(f"Anthropic API error: {response.status_code} - {response.text}")
    
    def _call_huggingface(self, prompt: str) -> str:
        """Call HuggingFace API."""
        api_key = os.getenv("HUGGINGFACE_API_KEY")
        if not api_key:
            raise Exception("HuggingFace API key not configured")
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "inputs": prompt,
            "parameters": {
                "max_new_tokens": self.max_tokens,
                "temperature": self.temperature,
                "return_full_text": False
            }
        }
        
        response = requests.post(
            f"https://api-inference.huggingface.co/models/{self.model_name}",
            headers=headers,
            json=data,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            if isinstance(result, list) and len(result) > 0:
                return result[0].get("generated_text", "")
            else:
                return str(result)
        else:
            raise Exception(f"HuggingFace API error: {response.status_code} - {response.text}")
    
    def _generate_fallback_response(self, prompt: str) -> str:
        """Generate a fallback response when model call fails."""
        logger.warning("⚠️ Using fallback response due to model call failure")
        
        # Simple rule-based fallback
        prompt_lower = prompt.lower()
        
        if "credit" in prompt_lower or "refund" in prompt_lower:
            return "I understand you're asking about credit or refund options. Please provide more specific details about the invoice issue so I can give you a more accurate response."
        
        elif "email" in prompt_lower or "contact" in prompt_lower:
            return "I can help you draft an email to the supplier. Please share the specific issue you'd like to address in the email."
        
        elif "escalate" in prompt_lower or "urgent" in prompt_lower:
            return "For urgent issues that need escalation, please contact your manager or the finance team directly. They can help expedite the resolution process."
        
        elif "price" in prompt_lower or "cost" in prompt_lower:
            return "I can help analyze pricing and cost implications. Please provide more details about the specific pricing concern you have."
        
        else:
            return "I'm here to help with invoice management and related questions. Please let me know what specific assistance you need, and I'll do my best to help you."

# Global client instance
_agent_client = None

def get_agent_client() -> AgentClient:
    """Get or create the global agent client instance."""
    global _agent_client
    if _agent_client is None:
        _agent_client = AgentClient()
    return _agent_client

def call_agent_model(prompt: str) -> str:
    """
    Convenience function to call the agent model.
    
    Args:
        prompt: The prompt to send to the model
        
    Returns:
        The model's response as a string
    """
    client = get_agent_client()
    return client.call_agent_model(prompt)

def call_agent_model_with_retry(prompt: str, max_retries: int = 3) -> str:
    """
    Call the agent model with retry logic.
    
    Args:
        prompt: The prompt to send to the model
        max_retries: Maximum number of retry attempts
        
    Returns:
        The model's response as a string
    """
    client = get_agent_client()
    
    for attempt in range(max_retries):
        try:
            return client.call_agent_model(prompt)
        except Exception as e:
            logger.warning(f"⚠️ Model call attempt {attempt + 1} failed: {str(e)}")
            if attempt == max_retries - 1:
                logger.error(f"❌ All {max_retries} attempts failed, using fallback")
                return client._generate_fallback_response(prompt)
            time.sleep(2 ** attempt)  # Exponential backoff
    
    return client._generate_fallback_response(prompt) 