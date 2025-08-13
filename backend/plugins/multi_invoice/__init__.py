"""
Multi-Invoice Detection Plugin System

This module provides a plugin architecture for extending multi-invoice detection
capabilities with custom logic and industry-specific rules.
"""

from typing import Dict, Any, List, Optional
from abc import ABC, abstractmethod
import logging

logger = logging.getLogger(__name__)

class MultiInvoicePlugin(ABC):
    """Base class for multi-invoice detection plugins"""
    
    def __init__(self, name: str, version: str = "1.0.0"):
        self.name = name
        self.version = version
        self.enabled = True
    
    @abstractmethod
    def detect(self, text: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Detect multi-invoice content using plugin-specific logic"""
        pass
    
    @abstractmethod
    def get_confidence(self, text: str, context: Dict[str, Any]) -> float:
        """Get confidence score for plugin detection"""
        pass
    
    def validate(self, text: str) -> bool:
        """Validate if plugin can process this text"""
        return True
    
    def get_metadata(self) -> Dict[str, Any]:
        """Get plugin metadata"""
        return {
            "name": self.name,
            "version": self.version,
            "enabled": self.enabled
        }

class PluginManager:
    """Manages multi-invoice detection plugins"""
    
    def __init__(self):
        self.plugins: Dict[str, MultiInvoicePlugin] = {}
    
    def register_plugin(self, plugin: MultiInvoicePlugin) -> None:
        """Register a new plugin"""
        if plugin.name in self.plugins:
            logger.warning(f"Plugin {plugin.name} already registered, overwriting")
        
        self.plugins[plugin.name] = plugin
        logger.info(f"✅ Registered plugin: {plugin.name} v{plugin.version}")
    
    def unregister_plugin(self, name: str) -> None:
        """Unregister a plugin"""
        if name in self.plugins:
            del self.plugins[name]
            logger.info(f"✅ Unregistered plugin: {name}")
    
    def get_plugin(self, name: str) -> Optional[MultiInvoicePlugin]:
        """Get a specific plugin"""
        return self.plugins.get(name)
    
    def get_all_plugins(self) -> List[MultiInvoicePlugin]:
        """Get all registered plugins"""
        return list(self.plugins.values())
    
    def execute_plugins(self, text: str, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Execute all enabled plugins"""
        results = []
        
        for plugin in self.plugins.values():
            if not plugin.enabled:
                continue
            
            try:
                if plugin.validate(text):
                    result = plugin.detect(text, context)
                    confidence = plugin.get_confidence(text, context)
                    
                    results.append({
                        "plugin": plugin.name,
                        "version": plugin.version,
                        "result": result,
                        "confidence": confidence,
                        "metadata": plugin.get_metadata()
                    })
                    
                    logger.debug(f"✅ Plugin {plugin.name} executed successfully")
                else:
                    logger.debug(f"⚠️ Plugin {plugin.name} skipped (validation failed)")
            except Exception as e:
                logger.error(f"❌ Plugin {plugin.name} failed: {e}")
                results.append({
                    "plugin": plugin.name,
                    "version": plugin.version,
                    "result": {},
                    "confidence": 0.0,
                    "error": str(e),
                    "metadata": plugin.get_metadata()
                })
        
        return results

# Global plugin manager instance
_plugin_manager = PluginManager()

def get_plugin_manager() -> PluginManager:
    """Get the global plugin manager instance"""
    return _plugin_manager

def register_plugin(plugin: MultiInvoicePlugin) -> None:
    """Register a plugin with the global manager"""
    _plugin_manager.register_plugin(plugin)

def unregister_plugin(name: str) -> None:
    """Unregister a plugin from the global manager"""
    _plugin_manager.unregister_plugin(name) 