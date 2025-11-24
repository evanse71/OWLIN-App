# backend/config.py — local-first, safe defaults used by the Owlin backend

from pathlib import Path
import os

# --- Feature flags (conservative defaults) ---
# MOCK REMOVED: Force v2 pipeline to be enabled by default (mock pipeline removed)
FEATURE_OCR_PIPELINE_V2 = True  # Changed from False - mock pipeline removed
ENABLE_PADDLE_OCR       = False
ENABLE_TESSERACT        = True

# OCR v2 feature flags
FEATURE_OCR_V2_PREPROC = False
FEATURE_OCR_V2_LAYOUT = False
CONF_FIELD_MIN = 0.5
CONF_PAGE_MIN = 0.5

# OCR Engine feature flags (System Bible Section 2.4)
ENABLE_DOCTR = True
ENABLE_CALAMARI = True

# OCR v3 feature flags
FEATURE_OCR_V3_TABLES = False
FEATURE_OCR_V3_TEMPLATES = False
FEATURE_OCR_V3_DONUT = False
FEATURE_OCR_V3_LLM = False
CONF_FALLBACK_PAGE = 0.3
CONF_FALLBACK_OVERALL = 0.3

# HTR (Handwriting) feature flags
FEATURE_HTR_ENABLED = False
HTR_CONFIDENCE_THRESHOLD = 0.7
HTR_MODEL_TYPE = "kraken"
HTR_SAVE_SAMPLES = False
HTR_REVIEW_QUEUE_ENABLED = False

# Donut fallback feature flags
FEATURE_DONUT_FALLBACK = False
DONUT_CONFIDENCE_THRESHOLD = 0.6
DONUT_MODEL_PATH = ""
DONUT_ENABLE_WHEN_NO_LINE_ITEMS = False

# --- Helper readers ---
def env_bool(name: str, default: bool=False) -> bool:
    v = os.getenv(name)
    if v is None:
        return default
    return v.strip().lower() in ("1","true","yes","on")

def env_str(name: str, default: str = "") -> str:
    v = os.getenv(name)
    return v if v is not None else default

def env_int(name: str, default: int = 0) -> int:
    v = os.getenv(name)
    if v is None:
        return default
    try:
        return int(v.strip())
    except Exception:
        return default

def env_float(name: str, default: float = 0.0) -> float:
    v = os.getenv(name)
    if v is None:
        return default
    try:
        return float(v.strip())
    except Exception:
        return default

def env_path(name: str, default: str = "") -> Path:
    v = env_str(name, default)
    return Path(v).expanduser().resolve() if v else Path(default).expanduser().resolve()

# Agent mode force flag (must be after env_bool definition)
AGENT_FORCE_ON = env_bool("AGENT_FORCE_ON", False)

# --- Paths (resolve relative to repository root) ---
# <repo>/backend/config.py → repo_root = parent of this file's parent
_REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR   = _REPO_ROOT / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

OCR_ARTIFACT_ROOT = DATA_DIR / "ocr_artifacts"
OCR_ARTIFACT_ROOT.mkdir(parents=True, exist_ok=True)

DB_PATH      = DATA_DIR / "owlin.db"
UPLOADS_DIR  = DATA_DIR / "uploads"
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
