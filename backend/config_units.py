"""
UK Engine Configuration - Deterministic Constants
All tolerances, weights, and mathematical constants for the pricing engine.
"""

# Price tolerances (British spelling; money stored as pennies for compatibility)
PRICE_TOL_PCT = 0.01          # 1% tolerance on (price*qty) vs line_total
PRICE_TOL_PENNIES = 1         # ±1p tolerance on totals
QTY_TOL = 1e-6

# Base unit conversions
ML_PER_L = 1000
G_PER_KG = 1000

# Volume synonyms (UK)
VOLUME_SYNONYMS = {
    "ml": 1, "millilitre": 1, "milliliter": 1,
    "cl": 10, "centilitre": 10, "centiliter": 10,
    "l": ML_PER_L, "litre": ML_PER_L, "liter": ML_PER_L
}

# Weight synonyms (UK)
WEIGHT_SYNONYMS = {
    "g": 1, "gram": 1, "grams": 1,
    "kg": G_PER_KG, "kilogram": G_PER_KG
}

# Pack terminology
PACK_WORDS = {"pack", "case", "crate", "tray", "dozen", "12pk", "24pk"}
DOZEN_ALIASES = {"dozen": 12}

# UK beverage packaging (approximate where noted)
KEG_LITRES = {"keg": 50.0, "cask": 40.9, "pin": 20.45}  # 11g ≈ 50L

# Pairing thresholds
PAIR_DATE_DAYS = 7
PAIR_AMOUNT_TOL_PCT = 0.025

# Category tolerances (heteroscedastic)
CATEGORY_TOL = {
    "spirits": 0.015,
    "wine": 0.030,
    "beer_keg": 0.010,
    "softs_nrb": 0.025,
    "default": 0.025
}
NEW_SKU_TOL_BONUS = 0.015      # widen tolerance for new/low-history SKUs

# Price ladder weights & staleness penalties (per day)
LADDER_CONF = {
    "contract_book": {"w": 1.00, "penalty_per_day": 0.0},
    "supplier_master": {"w": 0.85, "penalty_per_day": 0.001},
    "venue_memory_90d": {"w": 0.70, "penalty_per_day": 0.002},
    "invoice_unit_column": {"w": 0.40, "penalty_per_day": 0.0},
    "peer_sibling_sites": {"w": 0.55, "penalty_per_day": 0.003}
}
REF_CONFLICT_THRESHOLD = 0.10  # 10% disagreement

# Engine version for fingerprinting
ENGINE_VERSION = "1.0.0"

# Verdict priorities (strict order)
VERDICT_PRIORITIES = [
    "math_mismatch",
    "reference_conflict", 
    "uom_mismatch_suspected",
    "off_contract_discount",
    "unusual_vs_history",
    "ocr_suspected_error",
    "ok_on_contract",
    "needs_user_rule",
    "pricing_anomaly_unmodelled"
]

# FOC/Free terminology
FOC_TERMS = {"foc", "free", "complimentary", "gratis", "no charge", "n/c"} 