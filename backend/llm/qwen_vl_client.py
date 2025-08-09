import os, base64, json, requests
from typing import Dict, Any, List
from backend.types.parsed_invoice import InvoiceParsingPayload, ParsedInvoice, LineItem

SYSTEM_PROMPT = (
    "You are a deterministic invoice parser. Output ONLY valid JSON matching this schema:\n"
    "{supplier_name, invoice_number, invoice_date, currency, subtotal, tax, total_amount,"
    " line_items:[{description, quantity, unit, unit_price, line_total, page, row_idx, confidence}],"
    " warnings:[], field_confidence:{}, raw_extraction:{}}.\n"
    "Never invent values; use null if unknown. Numbers are plain (no symbols)."
)

def _user_prompt(hints: Dict[str, Any]) -> str:
    return (
        "Parse the following invoice/receipt page images into the schema. "
        "Merge rows across wraps; keep page and row indices. Validate totals≈sum(lines)±tax. "
        f"Hints: {json.dumps(hints or {}, ensure_ascii=False)}"
    )

class QwenVLClient:
    def __init__(self):
        self.base = os.getenv("MODEL_HOST_URL", "http://localhost:11434")
        self.model = os.getenv("QWEN_VL_MODEL_NAME", "qwen2.5-vl:latest")

    def parse(self, payload: InvoiceParsingPayload) -> ParsedInvoice:
        if not payload.page_images:
            raise ValueError("Qwen-VL path requires page_images.")
        # Ollama multimodal format
        msgs = [
            {"role":"system","content":SYSTEM_PROMPT},
            {"role":"user","content":[
                {"type":"text","text":_user_prompt(payload.hints)},
                *[
                    {"type":"image","image":pi["image_b64"],"mime_type":"image/png","name":f"page_{pi['page']}.png"}
                    for pi in payload.page_images
                ]
            ]}
        ]
        resp = requests.post(
            f"{self.base}/api/chat",
            json={"model": self.model, "messages": msgs, "stream": False, "options":{"temperature":0}}
        )
        resp.raise_for_status()
        txt = resp.json().get("message", {}).get("content", "")
        data = json.loads(txt)  # raise if invalid
        # Coerce to ParsedInvoice
        line_items = [
            LineItem(
                description=li.get("description",""),
                quantity=li.get("quantity"),
                unit=li.get("unit"),
                unit_price=li.get("unit_price"),
                line_total=li.get("line_total"),
                page=li.get("page"),
                row_idx=li.get("row_idx"),
                confidence=float(li.get("confidence", 0.0) or 0.0),
            ) for li in (data.get("line_items") or [])
        ]
        return ParsedInvoice(
            supplier_name=data.get("supplier_name"),
            invoice_number=data.get("invoice_number"),
            invoice_date=data.get("invoice_date"),
            currency=data.get("currency"),
            subtotal=data.get("subtotal"),
            tax=data.get("tax"),
            total_amount=data.get("total_amount"),
            line_items=line_items,
            warnings=data.get("warnings") or [],
            field_confidence=data.get("field_confidence") or {},
            raw_extraction=data.get("raw_extraction") or {}
        ) 