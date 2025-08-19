from __future__ import annotations
import os, time, json, traceback, uuid
from dataclasses import dataclass, asdict
from typing import Any, Dict, Optional, Callable

LOG_DIR = os.path.join("data", "logs", "ocr")
os.makedirs(LOG_DIR, exist_ok=True)

@dataclass
class StageRecord:
    run_id: str
    doc_id: str
    stage: str
    ok: bool
    started_at_ms: int
    ended_at_ms: int
    duration_ms: int
    meta: Dict[str, Any]
    error: Optional[str] = None

def _now_ms() -> int:
    return int(time.time() * 1000)

def log_stage(record: StageRecord) -> None:
    path = os.path.join(LOG_DIR, f"{record.run_id}.jsonl")
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(asdict(record), ensure_ascii=False) + "\n")

def stage_probe(stage_name: str):
    def wrapper(fn: Callable):
        def inner(*args, **kwargs):
            run_id = kwargs.get("run_id") or (args[0].get("run_id") if args and isinstance(args[0], dict) else str(uuid.uuid4()))
            doc_id = kwargs.get("doc_id") or (args[0].get("doc_id") if args and isinstance(args[0], dict) else "unknown")
            started = _now_ms()
            try:
                result = fn(*args, **kwargs)
                meta_preview: Dict[str, Any] = {}
                if isinstance(result, dict):
                    for key in ("page_count","text_len","confidence","lines_extracted","doc_type","items_count","supplier_found","date_found","total_found","currency_found"):
                        if key in result:
                            meta_preview[key] = result[key]
                ended = _now_ms()
                log_stage(StageRecord(run_id, doc_id, stage_name, True, started, ended, ended-started, meta_preview, None))
                return result
            except Exception as e:
                ended = _now_ms()
                log_stage(StageRecord(run_id, doc_id, stage_name, False, started, ended, ended-started, {}, "".join(traceback.format_exception(type(e), e, e.__traceback__))))
                raise
        return inner
    return wrapper 