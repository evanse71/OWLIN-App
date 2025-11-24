"""
Audit Export Router - CSV export of audit trail
"""
from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse
import sqlite3
import csv
from io import StringIO
from datetime import datetime

router = APIRouter(prefix="/api/audit", tags=["audit"])

@router.get("/export")
def export_audit(
    from_date: str = Query(None, description="Start date (YYYY-MM-DD)"),
    to_date: str = Query(None, description="End date (YYYY-MM-DD)")
):
    """
    Export audit log as CSV.
    Returns CSV with columns: ts, event, doc_id, invoice_id, stage, detail
    """
    try:
        conn = sqlite3.connect("data/owlin.db", check_same_thread=False)
        cursor = conn.cursor()
        
        # Build query
        query = "SELECT ts, action AS event, detail FROM audit_log WHERE 1=1"
        params = []
        
        if from_date:
            query += " AND ts >= ?"
            params.append(from_date)
        if to_date:
            query += " AND ts <= ?"
            params.append(f"{to_date} 23:59:59")  # Include full day
        
        query += " ORDER BY ts"
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        
        # Generate CSV
        output = StringIO()
        writer = csv.writer(output)
        
        # Header
        writer.writerow(["ts", "event", "doc_id", "invoice_id", "stage", "detail"])
        
        # Parse rows
        for row in rows:
            ts, event, detail = row
            
            # Try to extract doc_id from detail (JSON string)
            doc_id = ""
            invoice_id = ""
            stage = ""
            
            try:
                import json
                detail_obj = json.loads(detail)
                doc_id = detail_obj.get("doc_id", "")
                invoice_id = detail_obj.get("invoice_id", "")
                stage = detail_obj.get("stage", "")
            except:
                pass
            
            writer.writerow([ts, event, doc_id, invoice_id, stage, detail])
        
        csv_content = output.getvalue()
        output.close()
        
        # Generate filename with timestamp
        filename = f"audit_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        return StreamingResponse(
            iter([csv_content]),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    
    except Exception as e:
        # Return error as plain text CSV
        error_csv = f"error\n{str(e)}\n"
        return StreamingResponse(
            iter([error_csv]),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=audit_export_error.csv"}
        )
