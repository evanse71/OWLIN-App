# -*- coding: utf-8 -*-
"""
System Health Route

This module implements the GET /api/system/health/live endpoint that returns
live system health metrics from the health watchdog.
"""

from __future__ import annotations
import logging
from typing import Any, Dict
from fastapi import APIRouter

from backend.services.health_watchdog import get_health_status

LOGGER = logging.getLogger("owlin.routes.system_health")
router = APIRouter(prefix="/api/system", tags=["system"])


@router.get("/health/live")
async def get_live_health() -> Dict[str, Any]:
    """
    Get live system health status.
    
    Returns health metrics from the watchdog including:
    - Uploads folder monitoring status
    - Disk space availability
    - Process liveness
    """
    try:
        health_status = get_health_status()
        return health_status
        
    except Exception as e:
        LOGGER.error(f"Error getting live health: {e}")
        return {
            "status": "error",
            "error": str(e),
            "timestamp": None
        }

