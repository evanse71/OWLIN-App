# -*- coding: utf-8 -*-
"""
Health Watchdog Service

This module monitors system health including uploads folder, disk space, and process
liveness, as specified in Appendix B.2 (line 635).

Features:
- Monitor uploads folder for new files
- Check disk space (warn if <10% free)
- Monitor process liveness
- Expose /api/system/health/live endpoint
"""

from __future__ import annotations
import logging
import os
import shutil
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime

# Optional import for file watching
try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
    WATCHDOG_AVAILABLE = True
except ImportError:
    WATCHDOG_AVAILABLE = False
    Observer = None
    FileSystemEventHandler = None

LOGGER = logging.getLogger("owlin.services.health_watchdog")
LOGGER.setLevel(logging.INFO)


# Only define UploadsFolderHandler if watchdog is available
if WATCHDOG_AVAILABLE:
    class UploadsFolderHandler(FileSystemEventHandler):
        """Handler for uploads folder file system events."""
        
        def __init__(self, callback):
            self.callback = callback
        
        def on_created(self, event):
            if not event.is_directory:
                LOGGER.debug(f"New file detected in uploads: {event.src_path}")
                if self.callback:
                    self.callback(event.src_path)
else:
    # Dummy class when watchdog is not available
    class UploadsFolderHandler:
        """Dummy handler when watchdog is not available."""
        
        def __init__(self, callback):
            self.callback = callback


class HealthWatchdog:
    """Monitors system health and exposes health metrics."""
    
    def __init__(self, uploads_path: str = "data/uploads"):
        """
        Initialize health watchdog.
        
        Args:
            uploads_path: Path to uploads folder to monitor
        """
        self.uploads_path = Path(uploads_path)
        self.observer = None
        self._file_count = 0
        self._last_check = None
        self._health_status = {
            "uploads_folder": {"monitored": False, "file_count": 0},
            "disk_space": {"free_gb": 0.0, "free_percent": 0.0, "status": "ok"},
            "process_liveness": {"status": "ok"},
            "last_check": None
        }
    
    def start_monitoring(self):
        """Start monitoring uploads folder."""
        if not WATCHDOG_AVAILABLE:
            LOGGER.warning("watchdog not available. Install with: pip install watchdog")
            return False
        
        if not self.uploads_path.exists():
            self.uploads_path.mkdir(parents=True, exist_ok=True)
        
        try:
            event_handler = UploadsFolderHandler(self._on_file_created)
            self.observer = Observer()
            self.observer.schedule(event_handler, str(self.uploads_path), recursive=False)
            self.observer.start()
            
            self._health_status["uploads_folder"]["monitored"] = True
            LOGGER.info(f"Started monitoring uploads folder: {self.uploads_path}")
            return True
            
        except Exception as e:
            LOGGER.error(f"Error starting uploads folder monitoring: {e}")
            return False
    
    def stop_monitoring(self):
        """Stop monitoring uploads folder."""
        if self.observer:
            self.observer.stop()
            self.observer.join()
            self.observer = None
            self._health_status["uploads_folder"]["monitored"] = False
            LOGGER.info("Stopped monitoring uploads folder")
    
    def _on_file_created(self, file_path: str):
        """Callback when new file is created in uploads folder."""
        self._file_count += 1
        self._health_status["uploads_folder"]["file_count"] = self._file_count
        LOGGER.debug(f"New file detected: {file_path} (total: {self._file_count})")
    
    def check_disk_space(self) -> Dict[str, Any]:
        """
        Check disk space availability.
        
        Returns:
            Dictionary with disk space information
        """
        try:
            total, used, free = shutil.disk_usage(self.uploads_path)
            
            free_gb = free / (1024 ** 3)
            total_gb = total / (1024 ** 3)
            free_percent = (free / total * 100) if total > 0 else 0
            
            status = "ok"
            if free_percent < 10:
                status = "critical"
            elif free_percent < 20:
                status = "warning"
            
            self._health_status["disk_space"] = {
                "free_gb": round(free_gb, 2),
                "total_gb": round(total_gb, 2),
                "free_percent": round(free_percent, 1),
                "status": status
            }
            
            if status != "ok":
                LOGGER.warning(f"Disk space {status}: {free_percent:.1f}% free ({free_gb:.2f} GB)")
            
            return self._health_status["disk_space"]
            
        except Exception as e:
            LOGGER.error(f"Error checking disk space: {e}")
            return {"error": str(e), "status": "unknown"}
    
    def check_process_liveness(self) -> Dict[str, Any]:
        """
        Check if main process is alive.
        
        Returns:
            Dictionary with process liveness information
        """
        try:
            import os
            import psutil
            
            current_process = psutil.Process(os.getpid())
            
            self._health_status["process_liveness"] = {
                "status": "ok",
                "pid": current_process.pid,
                "memory_mb": round(current_process.memory_info().rss / (1024 ** 2), 2),
                "cpu_percent": current_process.cpu_percent(interval=0.1),
                "uptime_seconds": time.time() - current_process.create_time()
            }
            
            return self._health_status["process_liveness"]
            
        except ImportError:
            # psutil not available, use basic check
            self._health_status["process_liveness"] = {
                "status": "ok",
                "note": "psutil not available for detailed metrics"
            }
            return self._health_status["process_liveness"]
        except Exception as e:
            LOGGER.error(f"Error checking process liveness: {e}")
            return {"status": "unknown", "error": str(e)}
    
    def get_health_status(self) -> Dict[str, Any]:
        """
        Get comprehensive health status.
        
        Returns:
            Dictionary with all health metrics
        """
        self._last_check = datetime.now().isoformat()
        
        # Check all components
        disk_status = self.check_disk_space()
        process_status = self.check_process_liveness()
        
        # Count files in uploads folder
        try:
            file_count = len(list(self.uploads_path.glob("*")))
            self._health_status["uploads_folder"]["file_count"] = file_count
        except Exception as e:
            LOGGER.warning(f"Error counting uploads files: {e}")
        
        return {
            "status": "ok",
            "uploads_folder": self._health_status["uploads_folder"],
            "disk_space": disk_status,
            "process_liveness": process_status,
            "last_check": self._last_check,
            "timestamp": datetime.now().isoformat()
        }


# Singleton instance
_watchdog: Optional[HealthWatchdog] = None


def get_watchdog() -> HealthWatchdog:
    """Get or create singleton watchdog instance."""
    global _watchdog
    if _watchdog is None:
        _watchdog = HealthWatchdog()
    return _watchdog


def start_watchdog() -> bool:
    """Start the health watchdog."""
    watchdog = get_watchdog()
    return watchdog.start_monitoring()


def get_health_status() -> Dict[str, Any]:
    """Get current health status."""
    watchdog = get_watchdog()
    return watchdog.get_health_status()

