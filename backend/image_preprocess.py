# -*- coding: utf-8 -*-
"""Image preprocessing utilities for Owlin OCR.
- Deskew (Hough)
- Denoise (bilateral)
- Contrast enhance (CLAHE)
- Adaptive threshold
- Optional perspective correction for photos
All functions are pure and safe for CPU-only environments."""
from __future__ import annotations
import os
from typing import Any, Dict, Tuple
import cv2
import numpy as np

MAX_LONG_EDGE = 2200

def _to_gray(img: np.ndarray) -> np.ndarray:
    return cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape) == 3 else img

def _downscale(img: np.ndarray, max_long_edge: int = MAX_LONG_EDGE) -> np.ndarray:
    h, w = img.shape[:2]
    scale = min(1.0, float(max_long_edge) / max(h, w))
    if scale >= 1.0:
        return img
    new_w, new_h = int(w * scale), int(h * scale)
    return cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)

def _is_photo(img_bgr: np.ndarray) -> bool:
    gray = _to_gray(img_bgr)
    lap_var = cv2.Laplacian(gray, cv2.CV_64F).var()
    mean, std = cv2.meanStdDev(gray)
    return (lap_var < 250) or (std[0][0] > 55)

def _order_points(pts: np.ndarray) -> np.ndarray:
    x_sorted = pts[np.argsort(pts[:, 0]), :]
    left = x_sorted[:2, :]
    right = x_sorted[2:, :]
    left = left[np.argsort(left[:, 1]), :]
    (tl, bl) = left
    D = [np.linalg.norm(tl - x) for x in right]
    br = right[np.argmax(D)]
    tr = right[np.argmin(D)]
    return np.array([tl, tr, br, bl], dtype="float32")

def _perspective_correction(gray: np.ndarray) -> np.ndarray:
    try:
        thr = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C,
                                    cv2.THRESH_BINARY, 21, 10)
        contours, _ = cv2.findContours(thr, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            return gray
        cnt = max(contours, key=cv2.contourArea)
        peri = cv2.arcLength(cnt, True)
        approx = cv2.approxPolyDP(cnt, 0.02 * peri, True)
        if len(approx) != 4:
            return gray
        pts = approx.reshape(4, 2).astype("float32")
        rect = _order_points(pts)
        (tl, tr, br, bl) = rect
        widthA = np.linalg.norm(br - bl)
        widthB = np.linalg.norm(tr - tl)
        maxW = int(max(widthA, widthB))
        heightA = np.linalg.norm(tr - br)
        heightB = np.linalg.norm(tl - bl)
        maxH = int(max(heightA, heightB))
        dst = np.array([[0, 0],[maxW - 1, 0],[maxW - 1, maxH - 1],[0, maxH - 1]], dtype="float32")
        M = cv2.getPerspectiveTransform(rect, dst)
        return cv2.warpPerspective(gray, M, (maxW, maxH))
    except Exception:
        return gray

def _deskew(gray: np.ndarray) -> Tuple[np.ndarray, float]:
    blur = cv2.GaussianBlur(gray, (3, 3), 0)
    edges = cv2.Canny(blur, 50, 150, apertureSize=3)
    lines = cv2.HoughLines(edges, 1, np.pi / 180.0, 140)
    angles = []
    if lines is not None:
        for rho, theta in lines[:, 0]:
            ang = (theta * 180.0 / np.pi) - 90.0
            if -45 <= ang <= 45:
                angles.append(ang)
    angle = float(np.median(angles)) if len(angles) > 0 else 0.0
    h, w = gray.shape[:2]
    M = cv2.getRotationMatrix2D((w // 2, h // 2), angle, 1.0)
    rotated = cv2.warpAffine(gray, M, (w, h), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
    return rotated, angle

def preprocess_bgr_page(img_bgr: np.ndarray) -> Tuple[np.ndarray, Dict[str, Any]]:
    """Preprocess a single page image (BGR) -> (grayscale/binary image, metadata)."""
    meta: Dict[str, Any] = {"steps": [], "warnings": []}
    try:
        img = _downscale(img_bgr)
        meta["steps"].append({"op": "downscale", "shape": list(img.shape)})
        gray = _to_gray(img)
        meta["steps"].append({"op": "to_gray"})

        if _is_photo(img):
            gray = _perspective_correction(gray)
            meta["steps"].append({"op": "perspective_correction"})

        deskewed, angle = _deskew(gray)
        meta["steps"].append({"op": "deskew", "angle_deg": angle})

        den = cv2.bilateralFilter(deskewed, 5, 75, 75)
        meta["steps"].append({"op": "denoise_bilateral"})

        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(den)
        meta["steps"].append({"op": "clahe"})

        bw = cv2.adaptiveThreshold(enhanced, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                   cv2.THRESH_BINARY, 31, 9)
        meta["steps"].append({"op": "adaptive_threshold"})
        return bw, meta
    except Exception as e:
        meta["warnings"].append(f"preprocess_error:{e}")
        # Safe fallback: grayscale only
        return _to_gray(img_bgr), meta

def save_preprocessed_artifact(bw_or_gray: np.ndarray, artifact_dir: str, basename: str) -> str:
    os.makedirs(artifact_dir, exist_ok=True)
    out_path = os.path.join(artifact_dir, f"{basename}.png")
    cv2.imwrite(out_path, bw_or_gray)
    return out_path
