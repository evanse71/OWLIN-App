# -*- coding: utf-8 -*-
"""
Vault Lock System

This module implements single-writer token enforcement to prevent concurrent write
corruption, as specified in Appendix B.2 (line 631).

Features:
- Acquire/release edit tokens
- Lockfile mechanism (lockfile.sha256)
- Prevent simultaneous write sessions
"""

from __future__ import annotations
import logging
import os
import hashlib
import time
from pathlib import Path
from typing import Optional
from datetime import datetime

LOGGER = logging.getLogger("owlin.services.vault_lock")
LOGGER.setLevel(logging.INFO)


class VaultLock:
    """Manages vault lockfile for single-writer token enforcement."""
    
    def __init__(self, venue_id: str, shepherd_path: str = "data/shepherd"):
        """
        Initialize vault lock manager.
        
        Args:
            venue_id: Venue identifier
            shepherd_path: Base path for Shepherd vaults
        """
        self.venue_id = venue_id
        self.shepherd_path = Path(shepherd_path)
        self.vault_path = self.shepherd_path / venue_id
        self.lockfile_path = self.vault_path / "lockfile.sha256"
        self._token = None
    
    def acquire_edit_token(self, timeout_seconds: int = 30) -> bool:
        """
        Acquire edit token (create/check lockfile).
        
        Args:
            timeout_seconds: Maximum time to wait for lock (default 30s)
        
        Returns:
            True if token acquired, False otherwise
        """
        # Ensure vault directory exists
        self.vault_path.mkdir(parents=True, exist_ok=True)
        
        # Check if lockfile exists and is valid
        if self.lockfile_path.exists():
            try:
                # Read lockfile
                with open(self.lockfile_path, 'r') as f:
                    lock_data = f.read().strip()
                
                # Parse lockfile (format: timestamp|process_id|token_hash)
                parts = lock_data.split('|')
                if len(parts) >= 2:
                    lock_timestamp = float(parts[0])
                    lock_process_id = parts[1]
                    
                    # Check if lock is stale (older than timeout)
                    age_seconds = time.time() - lock_timestamp
                    if age_seconds > timeout_seconds:
                        LOGGER.warning(f"Stale lockfile detected (age={age_seconds:.1f}s), removing")
                        self.lockfile_path.unlink()
                    else:
                        # Check if process is still alive
                        if self._is_process_alive(lock_process_id):
                            LOGGER.warning(f"Vault is locked by process {lock_process_id}")
                            return False
                        else:
                            LOGGER.info(f"Lockfile exists but process {lock_process_id} is dead, removing")
                            self.lockfile_path.unlink()
            
            except Exception as e:
                LOGGER.warning(f"Error reading lockfile: {e}, removing")
                self.lockfile_path.unlink()
        
        # Create new lockfile
        try:
            import os
            process_id = str(os.getpid())
            token_hash = hashlib.sha256(f"{process_id}{time.time()}".encode()).hexdigest()[:16]
            timestamp = time.time()
            
            lock_data = f"{timestamp}|{process_id}|{token_hash}"
            
            with open(self.lockfile_path, 'w') as f:
                f.write(lock_data)
            
            self._token = token_hash
            LOGGER.info(f"Edit token acquired for venue {self.venue_id} (token={token_hash})")
            return True
            
        except Exception as e:
            LOGGER.error(f"Error acquiring edit token: {e}")
            return False
    
    def release_edit_token(self) -> bool:
        """
        Release edit token (remove lockfile).
        
        Returns:
            True if released successfully
        """
        if not self.lockfile_path.exists():
            return True
        
        try:
            # Verify we own the lockfile
            if self._token:
                with open(self.lockfile_path, 'r') as f:
                    lock_data = f.read().strip()
                
                if self._token not in lock_data:
                    LOGGER.warning("Lockfile token mismatch, not releasing")
                    return False
            
            self.lockfile_path.unlink()
            self._token = None
            LOGGER.info(f"Edit token released for venue {self.venue_id}")
            return True
            
        except Exception as e:
            LOGGER.error(f"Error releasing edit token: {e}")
            return False
    
    def check_vault_lock(self) -> Dict[str, Any]:
        """
        Check vault lock status.
        
        Returns:
            Dictionary with lock status information
        """
        if not self.lockfile_path.exists():
            return {
                "locked": False,
                "venue_id": self.venue_id,
                "message": "Vault is unlocked"
            }
        
        try:
            with open(self.lockfile_path, 'r') as f:
                lock_data = f.read().strip()
            
            parts = lock_data.split('|')
            if len(parts) >= 3:
                timestamp = float(parts[0])
                process_id = parts[1]
                token_hash = parts[2]
                
                age_seconds = time.time() - timestamp
                process_alive = self._is_process_alive(process_id)
                
                return {
                    "locked": True,
                    "venue_id": self.venue_id,
                    "process_id": process_id,
                    "process_alive": process_alive,
                    "age_seconds": age_seconds,
                    "token": token_hash,
                    "locked_at": datetime.fromtimestamp(timestamp).isoformat(),
                    "message": f"Vault is locked by process {process_id}" + (" (stale)" if not process_alive else "")
                }
            
            return {
                "locked": True,
                "venue_id": self.venue_id,
                "message": "Vault is locked (invalid lockfile format)"
            }
            
        except Exception as e:
            LOGGER.error(f"Error checking vault lock: {e}")
            return {
                "locked": False,
                "venue_id": self.venue_id,
                "error": str(e)
            }
    
    def _is_process_alive(self, process_id: str) -> bool:
        """Check if a process is still alive."""
        try:
            import os
            pid = int(process_id)
            # Try to send signal 0 (doesn't kill, just checks if process exists)
            os.kill(pid, 0)
            return True
        except (OSError, ValueError):
            return False


def acquire_edit_token(venue_id: str, shepherd_path: str = "data/shepherd") -> Optional[VaultLock]:
    """
    Acquire edit token for a venue.
    
    Args:
        venue_id: Venue identifier
        shepherd_path: Base path for Shepherd vaults
    
    Returns:
        VaultLock instance if acquired, None otherwise
    """
    vault_lock = VaultLock(venue_id, shepherd_path)
    
    if vault_lock.acquire_edit_token():
        return vault_lock
    
    return None


def check_vault_lock(venue_id: str, shepherd_path: str = "data/shepherd") -> Dict[str, Any]:
    """
    Check vault lock status for a venue.
    
    Args:
        venue_id: Venue identifier
        shepherd_path: Base path for Shepherd vaults
    
    Returns:
        Dictionary with lock status
    """
    vault_lock = VaultLock(venue_id, shepherd_path)
    return vault_lock.check_vault_lock()

