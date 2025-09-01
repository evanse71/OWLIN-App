"""
OCR pipeline: orchestrates preprocess → OCR → confidence → persist
"""
import subprocess
import json
import tempfile
from pathlib import Path
from typing import List, Dict, Any, Tuple
from PIL import Image

from .preprocess import preprocess_image
from .confidence import page_confidence, calculate_invoice_confidence
from services.ocr_writer import (
    persist_page_confidence, persist_invoice_confidence, 
    get_invoice_pages, mark_page_blocked
)

def run_tesseract(image_path: str) -> List[Tuple[str, float]]:
    """Run Tesseract OCR on image, return [(text, confidence)]."""
    try:
        # Run tesseract with confidence output
        result = subprocess.run([
            'tesseract', image_path, 'stdout', 
            '--oem', '1', '--psm', '6',
            '--dpi', '300'
        ], capture_output=True, text=True, check=True)
        
        # For now, return dummy confidence data
        # In production, this would parse Tesseract's confidence output
        lines = result.stdout.strip().split('\n')
        words_with_conf = []
        
        for line in lines:
            if line.strip():
                # Simulate confidence scores (in real implementation, parse from Tesseract)
                words = line.split()
                for word in words:
                    if word.strip():
                        # Simulate confidence based on word length and complexity
                        conf = min(95.0, 70.0 + len(word) * 2.0)
                        words_with_conf.append((word, conf))
        
        return words_with_conf
    except subprocess.CalledProcessError:
        return []

def ocr_pages(invoice_id: str) -> None:
    """
    1) fetch invoice pages (document_pages or invoice_pages)
    2) preprocess each, run OCR (tesseract), compute confidences
    3) persist page-level and roll-up to invoices. Apply gating:
       - page avg < 50 → mark blocked page (skip parse)
       - 50–69 → tag lines later as OCR_LOW_CONF
    """
    # Get invoice pages
    pages = get_invoice_pages(invoice_id)
    
    if not pages:
        # Try to get from document_pages if invoice_pages is empty
        pages = get_document_pages(invoice_id)
    
    if not pages:
        return
    
    page_confidences = []
    
    for page in pages:
        page_id = page['id']
        
        # Get image path (this would come from your asset management)
        image_path = get_image_path_for_page(page_id)
        
        if not image_path or not Path(image_path).exists():
            continue
        
        # Preprocess image
        img = Image.open(image_path)
        processed_img = preprocess_image(img)
        
        # Save processed image temporarily
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
            processed_img.save(tmp.name)
            temp_path = tmp.name
        
        try:
            # Run OCR
            words_with_conf = run_tesseract(temp_path)
            
            # Calculate confidence
            avg_conf, min_conf = page_confidence(words_with_conf)
            
            # Apply gating
            gating_decision = apply_confidence_gating(avg_conf)
            
            if gating_decision == "BLOCKED":
                # Mark page as blocked
                mark_page_blocked(page_id)
                page_confidences.append({
                    'page_id': page_id,
                    'avg_conf': 0.0,
                    'min_conf': 0.0,
                    'blocked': True
                })
            else:
                # Persist confidence
                persist_page_confidence(page_id, avg_conf, min_conf)
                page_confidences.append({
                    'page_id': page_id,
                    'avg_conf': avg_conf,
                    'min_conf': min_conf,
                    'blocked': False
                })
        
        finally:
            # Clean up temp file
            Path(temp_path).unlink(missing_ok=True)
    
    # Calculate invoice-level confidence (roll-up)
    if page_confidences:
        invoice_avg, invoice_min = calculate_invoice_confidence(page_confidences)
        persist_invoice_confidence(invoice_id, invoice_avg, invoice_min)

def get_document_pages(invoice_id: str) -> List[Dict[str, Any]]:
    """Get pages from document_pages table if invoice_pages is empty."""
    # This would query your document_pages table
    # For now, return empty list
    return []

def get_image_path_for_page(page_id: str) -> str:
    """Get the image file path for a given page ID."""
    # This would query your asset management system
    # For now, return a placeholder
    return f"data/previews/page_{page_id}.jpg"

def apply_confidence_gating(avg_conf: float) -> str:
    """Apply confidence gating rules."""
    if avg_conf < 50.0:
        return "BLOCKED"
    elif avg_conf < 70.0:
        return "WARN"
    else:
        return "PASS" 