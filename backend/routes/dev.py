import os
from fastapi import APIRouter, HTTPException
from db_manager_unified import get_db_manager

router = APIRouter()

@router.delete("/clear-documents")
async def clear_all_documents():
    """
    Development-only endpoint to clear all document records from the database.
    This should only be accessible in development mode.
    """
    # ✅ Allow in development mode or when explicitly enabled
    if (os.getenv('NODE_ENV') != 'development' and 
        os.getenv('ENVIRONMENT') != 'development' and 
        os.getenv('ENABLE_DEV_ROUTES') != 'true'):
        raise HTTPException(status_code=403, detail="This endpoint is only available in development mode. Set ENABLE_DEV_ROUTES=true to enable.")
    
    try:
        db_manager = get_db_manager()
        with db_manager.get_connection() as conn:
            # ✅ Clear all document tables
            conn.execute("DELETE FROM invoices")
            conn.execute("DELETE FROM delivery_notes")
            conn.execute("DELETE FROM uploaded_files")
            conn.commit()
        
        return {
            "message": "Cleared all document records",
            "tables_cleared": ["invoices", "delivery_notes", "uploaded_files"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to clear documents: {str(e)}") 