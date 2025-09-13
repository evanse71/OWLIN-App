from fastapi import APIRouter
from db_manager_unified import get_db_manager

router = APIRouter(prefix="/api/debug", tags=["debug"])

@router.get("/db-path")
def db_path():
    """Debug endpoint to show database path and status"""
    m = get_db_manager()
    p = getattr(m, "db_path", None)
    p_str = str(p) if p else "unknown"
    try:
        size = p.stat().st_size if p and p.exists() else 0
        exists = bool(p and p.exists())
    except Exception:
        size, exists = 0, False
    return {"db_path": p_str, "exists": exists, "size_bytes": size} 