import pypdfium2 as pdfium
import numpy as np, cv2

def render_pdf_page_bgr(path: str, page_no: int):
    pdf = pdfium.PdfDocument(path)
    n = len(pdf)
    page_index = max(0, min(page_no, n-1))
    page = pdf.get_page(page_index)
    bitmap = page.render(scale=2.0).to_numpy()
    page.close(); pdf.close()
    # bitmap is RGBA; drop A and convert to BGR
    rgb = bitmap[:, :, :3]
    bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
    return bgr