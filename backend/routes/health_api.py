from fastapi import APIRouter
from paddleocr import PaddleOCR

router = APIRouter()

@router.get("/health")
def health():
    return {"status": "healthy"}

@router.get("/health/ocr")
def health_ocr():
    try:
        # Test PaddleOCR initialization
        ocr = PaddleOCR(use_textline_orientation=True, lang='en')
        return {
            "engine": "paddle",
            "status": "ok",
            "lang": "en",
            "angle_cls": True
        }
    except Exception as e:
        return {
            "engine": "paddle",
            "status": "error",
            "error": str(e)
        }
