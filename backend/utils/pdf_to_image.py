import fitz
import numpy as np
import cv2

def render_pdf_page_bgr(path: str, page_no: int):
    doc = fitz.open(path)
    page = doc.load_page(page_no)
    pix = page.get_pixmap(alpha=False)
    img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, 3)
    img_bgr = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
    doc.close()
    return img_bgr
