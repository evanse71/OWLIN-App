from typing import List, Dict, Any

WEIGHTS = {
    "ingest": 10, "preprocess": 10, "ocr": 25, "parse": 25, "normalize": 10, "classify": 10, "persist": 10
}

def stage_percent(stage: str, meta: Dict[str, Any], ok: bool) -> int:
    if not ok:
        return 0
    if stage == "ocr":
        text_len = int(meta.get("text_len", 0))
        conf = float(meta.get("confidence", 0))
        if text_len > 400 and conf >= 65: return 100
        if text_len > 120 and conf >= 45: return 50
        return 20
    if stage == "parse":
        items = int(meta.get("items_count", 0))
        supplier_found = bool(meta.get("supplier_found", False))
        date_found = bool(meta.get("date_found", False))
        total_found = bool(meta.get("total_found", False))
        if items >= 3 and supplier_found and date_found and total_found: return 100
        if supplier_found or date_found: return 50
        return 20
    if stage == "normalize":
        return 100 if bool(meta.get("currency_found", False)) else 20
    if stage == "classify":
        doc_type = str(meta.get("doc_type", "")).lower()
        return 100 if doc_type in {"invoice","receipt","delivery_note","utility"} else 50 if doc_type else 20
    return 100

def compute_total(stages: List[Dict[str, Any]]) -> Dict[str, Any]:
    per_stage: Dict[str, int] = {}
    total = 0.0
    for s in stages:
        stg = s.get("stage")
        if not stg:
            continue
        pct = stage_percent(stg, s.get("meta", {}), s.get("ok", False))
        per_stage[stg] = pct
        total += (pct/100.0) * WEIGHTS.get(stg, 0)
    return {"per_stage": per_stage, "total_percent": round(total)} 