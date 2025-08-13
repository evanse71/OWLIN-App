import sys, base64
from pathlib import Path
from backend.types.parsed_invoice import InvoiceParsingPayload
from backend.llm.llm_client import parse_invoice
from backend.ocr.validators import validate_invoice

def render_pages_as_png_b64(pdf_path:str):
    # implement or reuse existing PDF->PNG function (300dpi)
    # return [{"page":i,"image_b64":...}, ...]
    raise NotImplementedError

if __name__ == "__main__":
    pdf = Path(sys.argv[1]).resolve()
    pages = render_pages_as_png_b64(str(pdf))
    payload = InvoiceParsingPayload(text=None, tables=None, page_images=pages, hints={"likely_currency":"GBP"})
    parsed = parse_invoice(payload)
    parsed = validate_invoice(parsed)
    import json
    print(json.dumps(parsed.__dict__, default=lambda o:o.__dict__, indent=2)) 