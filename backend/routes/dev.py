import os
from fastapi import APIRouter, HTTPException
from db import get_db_connection

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
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # ✅ Clear all document tables
        cursor.execute("DELETE FROM invoices")
        cursor.execute("DELETE FROM delivery_notes")
        cursor.execute("DELETE FROM uploaded_files")
        
        conn.commit()
        conn.close()
        
        return {
            "message": "Cleared all document records",
            "tables_cleared": ["invoices", "delivery_notes", "uploaded_files"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to clear documents: {str(e)}") 