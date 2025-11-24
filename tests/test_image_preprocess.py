# -*- coding: utf-8 -*-
import numpy as np
import cv2
from backend.image_preprocess import preprocess_bgr_page

def _synthetic_doc(angle_deg: float = 7.5) -> np.ndarray:
    # white canvas
    img = np.ones((800, 600, 3), dtype=np.uint8) * 255
    # draw dark lines (text-like)
    for i in range(8):
        y = 80 + i * 80
        cv2.line(img, (60, y), (540, y), (0, 0, 0), 2)
    # rotate
    h, w = img.shape[:2]
    M = cv2.getRotationMatrix2D((w//2, h//2), angle_deg, 1.0)
    rot = cv2.warpAffine(img, M, (w, h), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=(255,255,255))
    return rot

def test_preprocess_basic():
    bgr = _synthetic_doc()
    proc, meta = preprocess_bgr_page(bgr)
    assert proc is not None
    assert isinstance(proc, np.ndarray)
    assert len(meta.get("steps", [])) >= 3
