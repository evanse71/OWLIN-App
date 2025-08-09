import os, json
from typing import Dict, Any
from backend.types.parsed_invoice import InvoiceParsingPayload, ParsedInvoice, LineItem
from backend.llm.qwen_vl_client import QwenVLClient

try:
    from backend.llm.llama_client import LlamaClient  # optional
except Exception:
    LlamaClient = None

def _get_backend():
    return (os.getenv("LLM_BACKEND") or "qwen-vl").strip().lower()

def parse_invoice(payload: InvoiceParsingPayload) -> ParsedInvoice:
    backend = _get_backend()
    if backend == "qwen-vl":
        client = QwenVLClient()
        return client.parse(payload)
    elif backend == "llama-surya":
        if not LlamaClient:
            raise RuntimeError("Llama backend selected, but adapter not installed.")
        client = LlamaClient()
        return client.parse(payload)
    else:
        raise RuntimeError(f"Unknown LLM_BACKEND: {backend}") 