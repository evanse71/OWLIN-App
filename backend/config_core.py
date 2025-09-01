# Core configuration constants - LOCKED, NO TUNING

# OCR Confidence thresholds
OCR_BLOCK = 50.0  # Block parsing if page avg < 50
OCR_WARN = 70.0   # Flag lines as OCR_LOW_CONF if 50-69

# Math guardrails
PRICE_TOL_PCT = 0.01      # ±1%
PRICE_TOL_PENNIES = 1     # ±1p
QTY_TOL = 0.01            # Quantity tolerance

# FOC (Free of Charge) terms
FOC_TERMS = ['foc', 'free', 'gratis', 'complimentary', 'sample']

# Pairing tolerances
PAIR_DATE_DAYS = 7        # ±7 days
PAIR_AMOUNT_TOL_PCT = 0.025  # 2.5%

# Assembly time window
ASSEMBLY_TIME_WINDOW_S = 60  # ≤60s

# File size caps
MAX_FILE_MB = 40
MAX_PAGES = 200
MAX_PIXELS = 40_000_000

# Units normalization constants
VOLUME_SYNONYMS = {
    'ml': 1.0,
    'cl': 10.0,
    'l': 1000.0
}

WEIGHT_SYNONYMS = {
    'g': 1.0,
    'kg': 1000.0
}

DOZEN_ALIASES = {
    'dozen': 12.0
}

KEG_LITRES = {
    'keg': 50.0,
    'cask': 40.9,
    'pin': 20.45
}

ML_PER_L = 1000.0 