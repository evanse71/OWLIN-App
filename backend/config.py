# backend/config.py — local-first, safe defaults used by the Owlin backend

from pathlib import Path
import os

# --- Feature flags (conservative defaults) ---
# MOCK REMOVED: Force v2 pipeline to be enabled by default (mock pipeline removed)
FEATURE_OCR_PIPELINE_V2 = True  # Changed from False - mock pipeline removed
ENABLE_PADDLE_OCR       = True  # ENABLED - Required for LLM extraction to get clean text
ENABLE_TESSERACT        = True

# OCR v2 feature flags
# ENABLED: Advanced preprocessing (dewarping, deskew, denoise, CLAHE) for photo invoices
# This enables perspective correction (dewarping) for skewed photos BEFORE OCR
# Safe to enable: Only affects photo detection and preprocessing, not scanned PDFs
FEATURE_OCR_V2_PREPROC = True  # ENABLED - Required for photo invoice dewarping
FEATURE_OCR_V2_LAYOUT = True   # Detect table blocks
CONF_FIELD_MIN = 0.5
CONF_PAGE_MIN = 0.5

# Dual-path OCR preprocessing
# When enabled, for image files (not PDFs), the system runs both minimal and enhanced
# preprocessing paths, compares OCR results, and automatically chooses the better one.
# This helps avoid over-processing good quality photos that are damaged by aggressive enhancement.
FEATURE_DUAL_OCR_PATH = True  # ENABLED - Automatic path selection for better OCR quality

# Minimum usable OCR confidence threshold
# If OCR confidence is below this threshold, the result is marked as unusable
# and line items extraction is skipped to avoid showing garbage data.
MIN_USABLE_OCR_CONFIDENCE = 0.25  # 25% - initial value, easy to change

# OCR Engine feature flags (System Bible Section 2.4)
ENABLE_DOCTR = True
ENABLE_CALAMARI = True

# OCR v3 feature flags
FEATURE_OCR_V3_TABLES = True   # Extract line_items from tables
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

# LLM Extraction feature flags (Invoice Reconstruction via Ollama)
# These flags control the LLM-first invoice parsing approach (replaces geometric/regex)
FEATURE_LLM_EXTRACTION = True  # FORCED ENABLED - LLM-first extraction is active (hardcoded to bypass env override)
LLM_OLLAMA_URL = env_str("LLM_OLLAMA_URL", "http://localhost:11434")

# Model name with fallback options (tries in order)
LLM_MODEL_NAME = "qwen2.5-coder:32b"  # Use 32B for best code understanding
LLM_MODEL_FALLBACK_LIST = [
    "qwen2.5-coder:32b",     # Best quality for code analysis
    "qwen2.5-coder:7b",      # Fast fallback for structured output
    "qwen2.5-coder:latest",  # Latest version
    "llama3.1:8b",           # Good accuracy
    "llama3:8b",             # Good accuracy
    "llama3:latest",         # Common install
    "mistral:latest",        # Fast and accurate
    "llama3.2:3b"            # Smaller/faster fallback
]

LLM_TIMEOUT_SECONDS = env_int("LLM_TIMEOUT_SECONDS", 120)  # INCREASED: 120s for slow local LLMs
LLM_MAX_RETRIES = env_int("LLM_MAX_RETRIES", 3)
LLM_BBOX_MATCH_THRESHOLD = env_float("LLM_BBOX_MATCH_THRESHOLD", 0.7)

# Hard validation threshold: If relative error between calculated and extracted totals exceeds this,
# the invoice will be marked as 'needs_review' instead of auto-saving
LLM_VALIDATION_ERROR_THRESHOLD = env_float("LLM_VALIDATION_ERROR_THRESHOLD", 0.10)  # 10% error threshold

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
