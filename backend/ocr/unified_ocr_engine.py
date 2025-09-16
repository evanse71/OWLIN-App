from __future__ import annotations
import threading
from typing import Any, Dict, Optional

try:
    from paddleocr import PaddleOCR
    _PADDLE_OK = True
except Exception:
    _PADDLE_OK = False

import pytesseract
import cv2

class UnifiedOCREngine:
    _instance = None
    _lock = threading.Lock()

    def __init__(self) -> None:
        self._paddle: Optional[PaddleOCR] = None
        self._ready = False

    @classmethod
    def instance(cls) -> "UnifiedOCREngine":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = UnifiedOCREngine()
        return cls._instance

    def _init_paddle(self) -> None:
        if not _PADDLE_OK:
            return
        self._paddle = PaddleOCR(use_angle_cls=True, lang="en")
        self._ready = True

    def ensure_ready(self) -> None:
        if self._ready:
            return
        if _PADDLE_OK:
            self._init_paddle()
        else:
            self._ready = True

    def health(self) -> Dict[str, Any]:
        return {
            "engine": "paddle" if _PADDLE_OK else "tesseract",
            "status": "ok" if (self._ready or _PADDLE_OK) else "degraded",
            "paddle_available": _PADDLE_OK,
            "paddle_loaded": self._ready and _PADDLE_OK
        }

    def run_ocr(self, image_bgr):
        self.ensure_ready()
        if _PADDLE_OK and self._paddle is not None:
            result = self._paddle.ocr(image_bgr, cls=True)
            lines = []
            for page in result:
                for box, (text, conf) in [(it[0], it[1]) for it in page]:
                    lines.append({"text": text, "conf": float(conf), "box": box})
            return {"lines": lines}
        # fallback (rare)
        text = pytesseract.image_to_string(image_bgr)
        return {"lines": [{"text": t, "conf": 0.5, "box": None} for t in text.splitlines() if t.strip()]}