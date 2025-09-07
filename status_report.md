# OWLIN Full-App Status Audit Report

**Generated:** 2025-09-07T13:51:04.678961Z  
**Repository:** /Users/glennevans/owlin-app-clean/OWLIN-App-clean  
**Overall Score:** 41.6%

## Executive Summary

This audit was conducted in **Brutal Russian Judge Mode** with evidence-based scoring. Every claim is backed by concrete file paths, line numbers, and code excerpts.

### Overall Score Calculation

The weighted score is calculated as: Σ(module_score × weight_percent / 100)

| Module | Weight | Score | Weighted Contribution |
|--------|--------|-------|----------------------|
| Upload Ocr Pipeline | 20% | 46.8% | 9.4% |
| Invoice Data Model | 10% | 46.8% | 4.7% |
| Delivery Note Matching | 10% | 42.8% | 4.3% |
| Invoices Ui | 10% | 46.8% | 4.7% |
| Vat Totals Math | 8% | 42.8% | 3.4% |
| Flagged Issues | 8% | 38.8% | 3.1% |
| Supplier Module | 6% | 38.8% | 2.3% |
| Forecasting Module | 6% | 38.8% | 2.3% |
| Notes Shift Logs | 3% | 34.8% | 1.0% |
| Licensing Limited Mode | 5% | 30.8% | 1.5% |
| Rbac | 5% | 38.8% | 1.9% |
| Audit Log | 4% | 34.8% | 1.4% |
| Backups Recovery | 3% | 30.8% | 0.9% |
| Updates Rollback | 2% | 30.8% | 0.6% |

**Total Weighted Score: 41.6%**

## Module Details

### Upload Ocr Pipeline (20% weight)

**Score:** 46.8%

**Evidence:**
- **/Users/glennevans/owlin-app-clean/OWLIN-App-clean/scripts/audit_checks.yml** (L8-L13): Pattern 'upload|multipart|/upload|/api/upload' found in code
  ```
     8|      - "upload|multipart|/upload|/api/upload"
   9|      - "ocr|paddle|tesseract|confidence|psm|split|multi"
  10|      - "invoice.*upload|document.*upload"
  11|    key_files:
  12|      - "app...
  ```

### Invoice Data Model (10% weight)

**Score:** 46.8%

**Evidence:**
- **/Users/glennevans/owlin-app-clean/OWLIN-App-clean/scripts/audit_checks.yml** (L28-L33): Pattern 'invoice.*model|line.*item|VAT|tax|gross|net|currency|uom|unit' found in code
  ```
    28|      - "invoice.*model|line.*item|VAT|tax|gross|net|currency|uom|unit"
  29|      - "create.*table.*invoice|CREATE TABLE.*invoice"
  30|      - "invoice_number|supplier|amount|quantity"
  31|   ...
  ```
- **/Users/glennevans/owlin-app-clean/OWLIN-App-clean/scripts/audit_checks.yml** (L29-L34): Pattern 'create.*table.*invoice|CREATE TABLE.*invoice' found in code
  ```
    29|      - "create.*table.*invoice|CREATE TABLE.*invoice"
  30|      - "invoice_number|supplier|amount|quantity"
  31|    key_files:
  32|      - "app/database.py"
  33|      - "data/owlin.db"
  34|...
  ```
- **/Users/glennevans/owlin-app-clean/OWLIN-App-clean/scripts/audit_checks.yml** (L30-L35): Pattern 'invoice_number|supplier|amount|quantity' found in code
  ```
    30|      - "invoice_number|supplier|amount|quantity"
  31|    key_files:
  32|      - "app/database.py"
  33|      - "data/owlin.db"
  34|    schema_checks:
  35|      - "invoices table"...
  ```

### Delivery Note Matching (10% weight)

**Score:** 42.8%

**Evidence:**
- **/Users/glennevans/owlin-app-clean/OWLIN-App-clean/scripts/audit_checks.yml** (L43-L48): Pattern 'pair|match|similarity|levenshtein|dice|cosine|embeddings' found in code
  ```
    43|      - "pair|match|similarity|levenshtein|dice|cosine|embeddings"
  44|      - "delivery.*note|delivery_note"
  45|      - "confirm.*pair|reject.*pair|pairing.*suggestion"
  46|    key_files:
  ...
  ```
- **/Users/glennevans/owlin-app-clean/OWLIN-App-clean/scripts/audit_checks.yml** (L44-L49): Pattern 'delivery.*note|delivery_note' found in code
  ```
    44|      - "delivery.*note|delivery_note"
  45|      - "confirm.*pair|reject.*pair|pairing.*suggestion"
  46|    key_files:
  47|      - "app/database.py"
  48|    components:
  49|      - "Document...
  ```
- **/Users/glennevans/owlin-app-clean/OWLIN-App-clean/scripts/audit_checks.yml** (L45-L50): Pattern 'confirm.*pair|reject.*pair|pairing.*suggestion' found in code
  ```
    45|      - "confirm.*pair|reject.*pair|pairing.*suggestion"
  46|    key_files:
  47|      - "app/database.py"
  48|    components:
  49|      - "DocumentPairingSuggestionCard"
  50|      - "Pairing...
  ```

### Invoices Ui (10% weight)

**Score:** 46.8%

**Evidence:**
- **/Users/glennevans/owlin-app-clean/OWLIN-App-clean/scripts/audit_checks.yml** (L55-L60): Pattern 'InvoiceCard|InvoiceCardsPanel|InvoiceDetail|accordion' found in code
  ```
    55|      - "InvoiceCard|InvoiceCardsPanel|InvoiceDetail|accordion"
  56|      - "progress.*state|badge.*status|matched|unmatched|flagged"
  57|      - "responsive.*layout|left.*column|right.*detail"...
  ```
- **/Users/glennevans/owlin-app-clean/OWLIN-App-clean/scripts/audit_checks.yml** (L56-L61): Pattern 'progress.*state|badge.*status|matched|unmatched|flagged' found in code
  ```
    56|      - "progress.*state|badge.*status|matched|unmatched|flagged"
  57|      - "responsive.*layout|left.*column|right.*detail"
  58|    key_files:
  59|      - "app/invoices_page.py"
  60|      -...
  ```
- **/Users/glennevans/owlin-app-clean/OWLIN-App-clean/scripts/audit_checks.yml** (L57-L62): Pattern 'responsive.*layout|left.*column|right.*detail' found in code
  ```
    57|      - "responsive.*layout|left.*column|right.*detail"
  58|    key_files:
  59|      - "app/invoices_page.py"
  60|      - "app/ui_progress.py"
  61|    components:
  62|      - "InvoiceCardsPa...
  ```

### Vat Totals Math (8% weight)

**Score:** 42.8%

**Evidence:**
- **/Users/glennevans/owlin-app-clean/OWLIN-App-clean/scripts/audit_checks.yml** (L71-L76): Pattern 'VAT.*calc|gross.*net|net.*gross|vat.*rate' found in code
  ```
    71|      - "VAT.*calc|gross.*net|net.*gross|vat.*rate"
  72|      - "pack.*math|crate.*math|unit.*price|extended.*total"
  73|      - "rounding|banker.*round|ROUND_HALF"
  74|      - "\\d+\\s*[x×]\\...
  ```
- **/Users/glennevans/owlin-app-clean/OWLIN-App-clean/scripts/audit_checks.yml** (L72-L77): Pattern 'pack.*math|crate.*math|unit.*price|extended.*total' found in code
  ```
    72|      - "pack.*math|crate.*math|unit.*price|extended.*total"
  73|      - "rounding|banker.*round|ROUND_HALF"
  74|      - "\\d+\\s*[x×]\\s*\\d+"
  75|    key_files:
  76|      - "app/invoices_pa...
  ```
- **/Users/glennevans/owlin-app-clean/OWLIN-App-clean/scripts/audit_checks.yml** (L73-L78): Pattern 'rounding|banker.*round|ROUND_HALF' found in code
  ```
    73|      - "rounding|banker.*round|ROUND_HALF"
  74|      - "\\d+\\s*[x×]\\s*\\d+"
  75|    key_files:
  76|      - "app/invoices_page.py"
  77|    math_checks:
  78|      - "VAT calculation formula...
  ```

**Gaps:**
- No evidence found for pattern: \d+\s*[x×]\s*\d+

### Flagged Issues (8% weight)

**Score:** 38.8%

**Evidence:**
- **/Users/glennevans/owlin-app-clean/OWLIN-App-clean/scripts/audit_checks.yml** (L86-L91): Pattern 'flagged.*issue|discrepancy.*detection|resolution.*flow' found in code
  ```
    86|      - "flagged.*issue|discrepancy.*detection|resolution.*flow"
  87|      - "escalation|role.*aware.*resolution"
  88|    key_files:
  89|      - "app/flagged_issues_page.py"
  90|    component...
  ```
- **/Users/glennevans/owlin-app-clean/OWLIN-App-clean/scripts/audit_checks.yml** (L87-L92): Pattern 'escalation|role.*aware.*resolution' found in code
  ```
    87|      - "escalation|role.*aware.*resolution"
  88|    key_files:
  89|      - "app/flagged_issues_page.py"
  90|    components:
  91|      - "FlaggedIssuesTable"
  92|      - "ResolutionWorkflow"...
  ```

### Supplier Module (6% weight)

**Score:** 38.8%

**Evidence:**
- **/Users/glennevans/owlin-app-clean/OWLIN-App-clean/scripts/audit_checks.yml** (L97-L102): Pattern 'supplier.*scorecard|mismatch.*rate|volatility|delays' found in code
  ```
    97|      - "supplier.*scorecard|mismatch.*rate|volatility|delays"
  98|      - "supplier.*export|supplier.*metrics"
  99|    key_files:
 100|      - "app/suppliers_page.py"
 101|    components:
 102...
  ```
- **/Users/glennevans/owlin-app-clean/OWLIN-App-clean/scripts/audit_checks.yml** (L98-L103): Pattern 'supplier.*export|supplier.*metrics' found in code
  ```
    98|      - "supplier.*export|supplier.*metrics"
  99|    key_files:
 100|      - "app/suppliers_page.py"
 101|    components:
 102|      - "SupplierScorecard"
 103|      - "SupplierMetrics"...
  ```

### Forecasting Module (6% weight)

**Score:** 38.8%

**Evidence:**
- **/Users/glennevans/owlin-app-clean/OWLIN-App-clean/scripts/audit_checks.yml** (L108-L113): Pattern 'forecast|trend|linear|regress|confidence.*band' found in code
  ```
   108|      - "forecast|trend|linear|regress|confidence.*band"
 109|      - "recharts|UniversalTrendGraph|item.*level.*trend"
 110|    key_files:
 111|      - "app/forecast_page.py"
 112|    components...
  ```
- **/Users/glennevans/owlin-app-clean/OWLIN-App-clean/scripts/audit_checks.yml** (L109-L114): Pattern 'recharts|UniversalTrendGraph|item.*level.*trend' found in code
  ```
   109|      - "recharts|UniversalTrendGraph|item.*level.*trend"
 110|    key_files:
 111|      - "app/forecast_page.py"
 112|    components:
 113|      - "UniversalTrendGraph"
 114|      - "ForecastCha...
  ```

### Notes Shift Logs (3% weight)

**Score:** 34.8%

**Evidence:**
- **/Users/glennevans/owlin-app-clean/OWLIN-App-clean/scripts/audit_checks.yml** (L119-L124): Pattern 'notes|shift.*log|write.*lock|accountability.*trail' found in code
  ```
   119|      - "notes|shift.*log|write.*lock|accountability.*trail"
 120|    key_files:
 121|      - "app/notes_page.py"
 122|
 123|  licensing_limited_mode:
 124|    weight_percent: 5...
  ```

### Licensing Limited Mode (5% weight)

**Score:** 30.8%

**Evidence:**
- **/Users/glennevans/owlin-app-clean/OWLIN-App-clean/scripts/audit_checks.yml** (L127-L132): Pattern 'HMAC|RSA|ECDSA|signed.*hash' found in code
  ```
   127|      - "HMAC|RSA|ECDSA|signed.*hash"
 128|    key_files:
 129|      - "license/*.lic"
 130|    components:
 131|      - "LimitedModeUI"
 132|      - "LicenseVerification"...
  ```

**Gaps:**
- Missing key file: license/*.lic
- No evidence found for pattern: license|\.lic|Limited.*Mode|limited|signature|verify|hash

**Risks:**
- Critical files missing: ['license/*.lic']

**Critical TODOs:**
- **CRITICAL:** Implement missing key files: ['license/*.lic']

### Rbac (5% weight)

**Score:** 38.8%

**Evidence:**
- **/Users/glennevans/owlin-app-clean/OWLIN-App-clean/scripts/audit_checks.yml** (L137-L142): Pattern 'role|RBAC|permission|GM|Finance|Shift|authorize' found in code
  ```
   137|      - "role|RBAC|permission|GM|Finance|Shift|authorize"
 138|      - "Depends|get_current_user|@login_required"
 139|    key_files:
 140|      - "app/sidebar.py"
 141|    roles:
 142|      - "G...
  ```
- **/Users/glennevans/owlin-app-clean/OWLIN-App-clean/scripts/audit_checks.yml** (L138-L143): Pattern 'Depends|get_current_user|@login_required' found in code
  ```
   138|      - "Depends|get_current_user|@login_required"
 139|    key_files:
 140|      - "app/sidebar.py"
 141|    roles:
 142|      - "GM"
 143|      - "Finance"...
  ```

### Audit Log (4% weight)

**Score:** 34.8%

**Evidence:**
- **/Users/glennevans/owlin-app-clean/OWLIN-App-clean/scripts/audit_checks.yml** (L149-L154): Pattern 'audit.*log|append.*only|export.*csv|timestamps|user.*ID' found in code
  ```
   149|      - "audit.*log|append.*only|export.*csv|timestamps|user.*ID"
 150|    key_files:
 151|      - "app/database.py"
 152|
 153|  backups_recovery:
 154|    weight_percent: 3...
  ```

### Backups Recovery (3% weight)

**Score:** 30.8%

**Evidence:**
- **/Users/glennevans/owlin-app-clean/OWLIN-App-clean/scripts/audit_checks.yml** (L156-L161): Pattern 'backup|zipfile|restore|rollback|conflict.*resolver' found in code
  ```
   156|      - "backup|zipfile|restore|rollback|conflict.*resolver"
 157|    key_files:
 158|      - "data/"
 159|
 160|  updates_rollback:
 161|    weight_percent: 2...
  ```

**Gaps:**
- Missing key file: data/

**Risks:**
- Critical files missing: ['data/']

**Critical TODOs:**
- **CRITICAL:** Implement missing key files: ['data/']

### Updates Rollback (2% weight)

**Score:** 30.8%

**Evidence:**
- **/Users/glennevans/owlin-app-clean/OWLIN-App-clean/scripts/audit_checks.yml** (L163-L168): Pattern 'update.*bundle|rollback|signature.*check|changelog' found in code
  ```
   163|      - "update.*bundle|rollback|signature.*check|changelog"
 164|    key_files:
 165|      - "scripts/"
 166|
 167|# Scoring rubric weights
 168|scoring_weights:...
  ```

**Gaps:**
- Missing key file: scripts/

**Risks:**
- Critical files missing: ['scripts/']

**Critical TODOs:**
- **CRITICAL:** Implement missing key files: ['scripts/']

## RBAC Matrix

| Action | GM | Finance | Shift Lead | Evidence |
|--------|----|---------|------------|----------|
| general_access | ✓ | ✗ | ✗ | /Users/glennevans/owlin-app-clean/OWLIN-App-clean/allfileshas.txt |
| general_access | ✗ | ✓ | ✗ | /Users/glennevans/owlin-app-clean/OWLIN-App-clean/scripts/audit_repo.py |
| general_access | ✗ | ✗ | ✓ | /Users/glennevans/owlin-app-clean/OWLIN-App-clean/app/invoices_page_backup.py |

## UI Component Inventory

| Component | File | States | Status |
|-----------|------|--------|--------|
| unknown | /Users/glennevans/owlin-app-clean/OWLIN-App-clean/scripts/audit_checks.yml | unknown | wired |
| unknown | /Users/glennevans/owlin-app-clean/OWLIN-App-clean/scripts/audit_checks.yml | unknown | wired |
| unknown | /Users/glennevans/owlin-app-clean/OWLIN-App-clean/scripts/audit_checks.yml | unknown | wired |

## VAT/Math Forensic Analysis

### VAT Calculation Examples

- **Source:** /Users/glennevans/owlin-app-clean/OWLIN-App-clean/scripts/audit_repo.py
- **Formula:** Found in code excerpt
- **Sample:** {'net': 10.0, 'vat_rate': 0.2, 'gross': 12.0}
- **Rounding:** Unknown from code

