"""
Support Pack API Routes
"""
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pathlib import Path
from datetime import datetime

from backend.services.support_pack import get_support_pack_service

router = APIRouter(prefix="/api/support-packs", tags=["support-packs"])

@router.post("/invoices/{invoice_id}")
async def generate_invoice_support_pack(invoice_id: str):
    """Generate support pack for invoice"""
    try:
        service = get_support_pack_service()
        zip_path = service.generate_support_pack(invoice_id)
        
        return {
            "invoice_id": invoice_id,
            "pack_path": zip_path,
            "download_url": f"/api/support-packs/download/{Path(zip_path).name}"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate support pack: {e}")

@router.get("/download/{filename}")
async def download_support_pack(filename: str):
    """Download support pack zip file"""
    pack_path = Path("backups/support_packs") / filename
    
    if not pack_path.exists():
        raise HTTPException(status_code=404, detail="Support pack not found")
    
    return FileResponse(
        path=str(pack_path),
        filename=filename,
        media_type="application/zip"
    )

@router.get("/")
async def list_support_packs():
    """List available support packs"""
    packs_dir = Path("backups/support_packs")
    
    if not packs_dir.exists():
        return {"packs": []}
    
    packs = []
    for pack_file in packs_dir.glob("*.zip"):
        stat = pack_file.stat()
        packs.append({
            "filename": pack_file.name,
            "invoice_id": pack_file.stem,
            "size_bytes": stat.st_size,
            "created_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "download_url": f"/api/support-packs/download/{pack_file.name}"
        })
    
    return {"packs": sorted(packs, key=lambda x: x["created_at"], reverse=True)} 