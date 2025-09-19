"""
Annotations API Router

This module provides API endpoints for managing document annotations including
viewing, creating, updating, and deleting annotations on invoices and delivery notes.
"""

from __future__ import annotations
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, Query, Path
from pydantic import BaseModel, Field
import sqlite3
import json

router = APIRouter(prefix="/api/annotations", tags=["annotations"])


class AnnotationResponse(BaseModel):
    """Response model for annotation data"""
    id: str
    invoice_id: Optional[str] = None
    delivery_note_id: Optional[str] = None
    line_item_id: Optional[int] = None
    kind: str
    text: Optional[str] = None
    x: float = Field(..., ge=0.0, le=1.0)
    y: float = Field(..., ge=0.0, le=1.0)
    w: float = Field(..., ge=0.0, le=1.0)
    h: float = Field(..., ge=0.0, le=1.0)
    confidence: float = Field(..., ge=0.0, le=1.0)
    color: Optional[str] = None
    page_number: int = 1
    created_at: str


class AnnotationCreate(BaseModel):
    """Model for creating new annotations"""
    invoice_id: Optional[str] = None
    delivery_note_id: Optional[str] = None
    line_item_id: Optional[int] = None
    kind: str = Field(..., regex="^(TICK|CROSS|CIRCLE|MARK|NOTE|HIGHLIGHT)$")
    text: Optional[str] = None
    x: float = Field(..., ge=0.0, le=1.0)
    y: float = Field(..., ge=0.0, le=1.0)
    w: float = Field(..., ge=0.0, le=1.0)
    h: float = Field(..., ge=0.0, le=1.0)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    color: Optional[str] = None
    page_number: int = 1


class AnnotationUpdate(BaseModel):
    """Model for updating annotations"""
    kind: Optional[str] = Field(None, regex="^(TICK|CROSS|CIRCLE|MARK|NOTE|HIGHLIGHT)$")
    text: Optional[str] = None
    x: Optional[float] = Field(None, ge=0.0, le=1.0)
    y: Optional[float] = Field(None, ge=0.0, le=1.0)
    w: Optional[float] = Field(None, ge=0.0, le=1.0)
    h: Optional[float] = Field(None, ge=0.0, le=1.0)
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    color: Optional[str] = None


def get_db_connection():
    """Get database connection"""
    return sqlite3.connect('data/owlin.db')


@router.get("/", response_model=List[AnnotationResponse])
async def get_annotations(
    invoice_id: Optional[str] = Query(None, description="Filter by invoice ID"),
    delivery_note_id: Optional[str] = Query(None, description="Filter by delivery note ID"),
    kind: Optional[str] = Query(None, description="Filter by annotation kind"),
    page_number: Optional[int] = Query(None, description="Filter by page number"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of annotations to return"),
    offset: int = Query(0, ge=0, description="Number of annotations to skip")
):
    """Get annotations with optional filtering"""
    db = get_db_connection()
    cursor = db.cursor()
    
    # Build query with filters
    query = "SELECT * FROM annotations WHERE 1=1"
    params = []
    
    if invoice_id:
        query += " AND invoice_id = ?"
        params.append(invoice_id)
    
    if delivery_note_id:
        query += " AND delivery_note_id = ?"
        params.append(delivery_note_id)
    
    if kind:
        query += " AND kind = ?"
        params.append(kind)
    
    if page_number is not None:
        query += " AND page_number = ?"
        params.append(page_number)
    
    query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])
    
    cursor.execute(query, params)
    rows = cursor.fetchall()
    
    # Get column names
    columns = [description[0] for description in cursor.description]
    
    annotations = []
    for row in rows:
        annotation_dict = dict(zip(columns, row))
        annotations.append(AnnotationResponse(**annotation_dict))
    
    db.close()
    return annotations


@router.get("/{annotation_id}", response_model=AnnotationResponse)
async def get_annotation(
    annotation_id: str = Path(..., description="Annotation ID")
):
    """Get a specific annotation by ID"""
    db = get_db_connection()
    cursor = db.cursor()
    
    cursor.execute("SELECT * FROM annotations WHERE id = ?", (annotation_id,))
    row = cursor.fetchone()
    
    if not row:
        db.close()
        raise HTTPException(status_code=404, detail="Annotation not found")
    
    # Get column names
    columns = [description[0] for description in cursor.description]
    annotation_dict = dict(zip(columns, row))
    
    db.close()
    return AnnotationResponse(**annotation_dict)


@router.post("/", response_model=AnnotationResponse)
async def create_annotation(annotation: AnnotationCreate):
    """Create a new annotation"""
    import uuid
    
    db = get_db_connection()
    cursor = db.cursor()
    
    annotation_id = str(uuid.uuid4())
    
    cursor.execute("""
        INSERT INTO annotations (
            id, invoice_id, delivery_note_id, line_item_id, kind, text,
            x, y, w, h, confidence, color, page_number, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
    """, (
        annotation_id,
        annotation.invoice_id,
        annotation.delivery_note_id,
        annotation.line_item_id,
        annotation.kind,
        annotation.text,
        annotation.x,
        annotation.y,
        annotation.w,
        annotation.h,
        annotation.confidence,
        annotation.color,
        annotation.page_number
    ))
    
    db.commit()
    db.close()
    
    # Return the created annotation
    return await get_annotation(annotation_id)


@router.put("/{annotation_id}", response_model=AnnotationResponse)
async def update_annotation(
    annotation_id: str = Path(..., description="Annotation ID"),
    annotation_update: AnnotationUpdate = None
):
    """Update an existing annotation"""
    db = get_db_connection()
    cursor = db.cursor()
    
    # Check if annotation exists
    cursor.execute("SELECT id FROM annotations WHERE id = ?", (annotation_id,))
    if not cursor.fetchone():
        db.close()
        raise HTTPException(status_code=404, detail="Annotation not found")
    
    # Build update query
    update_fields = []
    params = []
    
    for field, value in annotation_update.dict(exclude_unset=True).items():
        update_fields.append(f"{field} = ?")
        params.append(value)
    
    if not update_fields:
        db.close()
        raise HTTPException(status_code=400, detail="No fields to update")
    
    update_fields.append("updated_at = datetime('now')")
    params.append(annotation_id)
    
    query = f"UPDATE annotations SET {', '.join(update_fields)} WHERE id = ?"
    cursor.execute(query, params)
    
    db.commit()
    db.close()
    
    # Return the updated annotation
    return await get_annotation(annotation_id)


@router.delete("/{annotation_id}")
async def delete_annotation(
    annotation_id: str = Path(..., description="Annotation ID")
):
    """Delete an annotation"""
    db = get_db_connection()
    cursor = db.cursor()
    
    cursor.execute("DELETE FROM annotations WHERE id = ?", (annotation_id,))
    
    if cursor.rowcount == 0:
        db.close()
        raise HTTPException(status_code=404, detail="Annotation not found")
    
    db.commit()
    db.close()
    
    return {"message": "Annotation deleted successfully"}


@router.get("/invoice/{invoice_id}/line-items", response_model=List[Dict[str, Any]])
async def get_annotations_by_line_item(
    invoice_id: str = Path(..., description="Invoice ID")
):
    """Get annotations grouped by line item for an invoice"""
    db = get_db_connection()
    cursor = db.cursor()
    
    cursor.execute("""
        SELECT 
            a.line_item_id,
            a.kind,
            COUNT(*) as count,
            GROUP_CONCAT(a.id) as annotation_ids,
            GROUP_CONCAT(a.text) as texts
        FROM annotations a
        WHERE a.invoice_id = ? AND a.line_item_id IS NOT NULL
        GROUP BY a.line_item_id, a.kind
        ORDER BY a.line_item_id, a.kind
    """, (invoice_id,))
    
    rows = cursor.fetchall()
    
    result = []
    for row in rows:
        line_item_id, kind, count, annotation_ids, texts = row
        result.append({
            "line_item_id": line_item_id,
            "kind": kind,
            "count": count,
            "annotation_ids": annotation_ids.split(',') if annotation_ids else [],
            "texts": texts.split(',') if texts else []
        })
    
    db.close()
    return result


@router.get("/stats/summary")
async def get_annotation_stats():
    """Get annotation statistics"""
    db = get_db_connection()
    cursor = db.cursor()
    
    # Total annotations
    cursor.execute("SELECT COUNT(*) FROM annotations")
    total_annotations = cursor.fetchone()[0]
    
    # Annotations by kind
    cursor.execute("""
        SELECT kind, COUNT(*) as count
        FROM annotations
        GROUP BY kind
        ORDER BY count DESC
    """)
    by_kind = dict(cursor.fetchall())
    
    # Annotations by color
    cursor.execute("""
        SELECT color, COUNT(*) as count
        FROM annotations
        WHERE color IS NOT NULL
        GROUP BY color
        ORDER BY count DESC
    """)
    by_color = dict(cursor.fetchall())
    
    # Annotations with text
    cursor.execute("SELECT COUNT(*) FROM annotations WHERE text IS NOT NULL AND text != ''")
    with_text = cursor.fetchone()[0]
    
    # Recent annotations (last 7 days)
    cursor.execute("""
        SELECT COUNT(*) FROM annotations 
        WHERE created_at >= datetime('now', '-7 days')
    """)
    recent = cursor.fetchone()[0]
    
    db.close()
    
    return {
        "total_annotations": total_annotations,
        "by_kind": by_kind,
        "by_color": by_color,
        "with_text": with_text,
        "recent_7_days": recent
    }
