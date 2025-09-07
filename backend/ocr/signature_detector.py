from typing import List, Dict, Any
from PIL import Image, ImageOps
import io
import base64

try:
    import numpy as np
    import cv2  # type: ignore
    CV_AVAILABLE = True
except Exception:
    CV_AVAILABLE = False

class SignatureDetector:
    def __init__(self, bottom_region_ratio: float = 0.35):
        self.bottom_region_ratio = bottom_region_ratio

    def _to_base64_png(self, img: Image.Image) -> str:
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return base64.b64encode(buf.getvalue()).decode("utf-8")

    def detect(self, page_img: Image.Image) -> List[Dict[str, Any]]:
        if not CV_AVAILABLE:
            return []

        try:
            img = page_img.convert("RGB")
            w, h = img.size
            # Focus bottom area where signatures commonly appear
            bottom_h = int(h * self.bottom_region_ratio)
            crop_box = (0, h - bottom_h, w, h)
            roi = img.crop(crop_box)

            arr = np.array(roi)
            gray = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)
            # Adaptive threshold to emphasize ink strokes
            th = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C,
                                       cv2.THRESH_BINARY_INV, 21, 15)
            # Dilate to connect strokes
            kernel = np.ones((3, 3), np.uint8)
            th = cv2.dilate(th, kernel, iterations=1)
            # Edge map as a cursive proxy
            edges = cv2.Canny(gray, 80, 180)

            # Connected components to find candidate blobs
            cnts, _ = cv2.findContours(th, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            results: List[Dict[str, Any]] = []
            for c in cnts:
                x, y, cw, ch = cv2.boundingRect(c)
                if cw < 40 or ch < 12:
                    continue  # too small
                aspect = cw / max(1, ch)
                if aspect < 2.2:  # wide-ish
                    continue
                # Stroke density score
                region = th[y:y+ch, x:x+cw]
                density = float(np.mean(region) / 255.0)
                # Edge density
                e_region = edges[y:y+ch, x:x+cw]
                e_density = float(np.mean(e_region) / 255.0)
                score = 0.5 * density + 0.5 * e_density
                # Map to conservative confidence 0.3-0.98
                conf = max(0.30, min(0.98, 0.30 + score * 0.68))

                # Map bbox back to full page coords
                abs_x, abs_y = x, (h - bottom_h) + y
                # Clamp
                abs_x = int(max(0, min(w - 1, abs_x)))
                abs_y = int(max(0, min(h - 1, abs_y)))
                cw = int(min(w - abs_x, cw))
                ch = int(min(h - abs_y, ch))

                crop = img.crop((abs_x, abs_y, abs_x + cw, abs_y + ch))
                b64 = self._to_base64_png(crop)
                results.append({
                    "bbox": [abs_x, abs_y, cw, ch],
                    "image_b64": b64,
                    "confidence": conf,
                    "label": "signature"
                })

            # Deduplicate overlapping boxes (simple IoU threshold)
            def iou(a, b) -> float:
                ax, ay, aw, ah = a
                bx, by, bw, bh = b
                ax2, ay2 = ax + aw, ay + ah
                bx2, by2 = bx + bw, by + bh
                inter_x1 = max(ax, bx)
                inter_y1 = max(ay, by)
                inter_x2 = min(ax2, bx2)
                inter_y2 = min(ay2, by2)
                inter = max(0, inter_x2 - inter_x1) * max(0, inter_y2 - inter_y1)
                union = aw * ah + bw * bh - inter
                return inter / union if union > 0 else 0.0

            deduped: List[Dict[str, Any]] = []
            for r in sorted(results, key=lambda x: -x["confidence"]):
                if all(iou(r["bbox"], d["bbox"]) < 0.3 for d in deduped):
                    deduped.append(r)

            return deduped[:5]
        except Exception:
            return [] 