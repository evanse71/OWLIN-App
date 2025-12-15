# Confidence Bands & Review Affordances - Verification Checklist

## ✅ 1. Backend Startup & Schema Migration

**Status**: ✅ PASSED
- Backend imports successfully
- Schema migration applied: `confidence_breakdown` column added to `invoices` table
- No startup exceptions

**Test Command**:
```powershell
cd C:\Users\tedev\FixPack_2025-11-02_133105
.\.venv311\Scripts\Activate.ps1
python -c "import backend.main; print('Import successful')"
```

---

## ✅ 2. Confidence Breakdown Storage & API Response

**Status**: ✅ IMPLEMENTED
- `confidence_breakdown` field added to invoices table
- `/api/invoices` endpoint now includes `confidence_breakdown` in response
- JSON parsing handles both string and dict formats

**Expected JSON from `/api/invoices`**:
```json
{
  "invoices": [
    {
      "id": "doc-123",
      "doc_id": "doc-123",
      "supplier": "Acme Foods Ltd",
      "confidence": 85.5,
      "confidence_breakdown": {
        "ocr_quality": 0.85,
        "extraction_quality": 0.72,
        "validation_quality": 0.90,
        "overall_confidence": 0.82,
        "band": "high",
        "action_required": "none",
        "primary_issue": null,
        "remediation_hints": []
      },
      "status": "ready",
      ...
    }
  ]
}
```

**Test Command**:
```powershell
curl "http://127.0.0.1:8000/api/invoices" | ConvertFrom-Json | ConvertTo-Json -Depth 10
```

---

## ✅ 3. Status Logic & Band Mapping

**Status**: ✅ IMPLEMENTED

**Band → Status Mapping**:
- **High (80-100%)** → `ready` (unless LLM flags review)
- **Medium (60-79%)** → `needs_review`
- **Low (40-59%)** → `needs_review`
- **Critical (<40%)** → `needs_review`

**Test Cases Needed**:

1. **High Band Test** (clean PDF):
   - Expected: `status: "ready"`, `band: "high"`
   - Upload a clean, text-based PDF invoice

2. **Medium Band Test** (slightly skewed scan):
   - Expected: `status: "needs_review"`, `band: "medium"`
   - Upload a scanned invoice with minor quality issues

3. **Low Band Test** (photo invoice):
   - Expected: `status: "needs_review"`, `band: "low"`
   - Upload a photo of an invoice with partial table extraction

4. **Critical Band Test** (bad scan):
   - Expected: `status: "needs_review"`, `band: "critical"`
   - Upload a very poor quality scan or empty extraction

**Test Command**:
```powershell
# After upload, check status
curl "http://127.0.0.1:8000/api/upload/status?doc_id=YOUR_DOC_ID"
```

**Expected Response**:
```json
{
  "status": "ok",
  "doc_id": "doc-123",
  "confidence": 85.5,
  "confidence_band": "high",
  "confidence_breakdown": {
    "ocr_quality": 0.85,
    "extraction_quality": 0.72,
    "validation_quality": 0.90,
    "overall_confidence": 0.82,
    "band": "high",
    "action_required": "none"
  },
  "status": "ready"
}
```

---

## ✅ 4. Confidence Calculator Safeguards

**Status**: ✅ IMPLEMENTED

**Safeguards Added**:
1. **Missing Line Items Penalty**: If total exists but no line items → validation quality capped at 0.5
2. **Unknown Supplier Penalty**: If supplier is "Unknown" AND total is 0 → extraction quality capped at 0.5
3. **Empty Data Detection**: Supplier=Unknown + Total=0 + No line items → Critical band

**Test Case - Missing Line Items**:
```json
{
  "supplier": "Acme Foods",
  "total": 150.00,
  "line_items": []  // Empty!
}
```
**Expected**: 
- `extraction_quality` < 0.5 (no line items = 0 points for 20% of score)
- `validation_quality` = 0.5 (penalty for missing line items when total exists)
- `band` should be **medium or low**, NOT high

---

## ✅ 5. Review Workflow Endpoints

**Status**: ✅ IMPLEMENTED

**Endpoints**:
- `GET /api/review/queue` - List documents needing review
- `GET /api/review/{doc_id}/details` - Get detailed review info
- `POST /api/review/{doc_id}/quick-fix` - Apply quick fixes
- `POST /api/review/{doc_id}/approve` - Approve after review
- `POST /api/review/{doc_id}/escalate` - Escalate for external review

**Test Commands**:
```powershell
# Get review queue
curl "http://127.0.0.1:8000/api/review/queue"

# Get review details
curl "http://127.0.0.1:8000/api/review/YOUR_DOC_ID/details"

# Approve a document
curl -X POST "http://127.0.0.1:8000/api/review/YOUR_DOC_ID/approve" `
  -H "Content-Type: application/json" `
  -d '{"notes": "Verified manually"}'
```

**Expected Response from `/api/review/{doc_id}/details`**:
```json
{
  "status": "ok",
  "doc_id": "doc-123",
  "document": {
    "id": "doc-123",
    "supplier": "Acme Foods",
    "total": 150.00,
    "confidence": 65.0,
    "status": "needs_review",
    "line_items_count": 3
  },
  "confidence_breakdown": {
    "ocr_quality": 0.70,
    "extraction_quality": 0.55,
    "validation_quality": 0.75,
    "overall_confidence": 0.66,
    "band": "medium",
    "action_required": "quick_review",
    "primary_issue": "Some fields may need verification",
    "remediation_hints": ["Verify extracted fields match document"]
  },
  "review_metadata": {
    "review_reason": "confidence_below_threshold",
    "review_priority": "low",
    "fixable_fields": [],
    "suggested_actions": ["Verify extracted fields match document"]
  }
}
```

---

## ⚠️ 6. Critical Warnings - Confidence Doesn't Lie

**Status**: ✅ SAFEGUARDS IMPLEMENTED

**Rules Enforced**:
1. ✅ Missing line items when total exists → validation quality penalty (0.5 max)
2. ✅ Unknown supplier + zero total → extraction quality capped at 0.5
3. ✅ Empty data (supplier=Unknown, total=0, no items) → Critical band
4. ✅ Band classification checks line_items_count explicitly

**Test Case - False Confidence Prevention**:
```json
{
  "supplier": "Acme Foods",
  "total": 150.00,
  "line_items": [],  // Missing!
  "ocr_quality": 0.90  // High OCR
}
```

**Expected Result**:
- `extraction_quality`: ~0.55 (30% supplier + 25% total = 55%, missing 20% for line items)
- `validation_quality`: 0.5 (penalty for missing line items)
- `overall_confidence`: ~0.70 (weighted: 0.90*0.4 + 0.55*0.35 + 0.5*0.25 = 0.70)
- `band`: **medium** (not high, despite good OCR)

---

## 📋 Next Steps for Full Verification

1. **Start Backend Server**:
   ```powershell
   uvicorn backend.main:app --reload
   ```

2. **Upload Test Documents**:
   - Upload 4 test documents (high/medium/low/critical bands)
   - Verify each gets correct band and status

3. **Check API Responses**:
   - Verify `confidence_breakdown` appears in `/api/invoices`
   - Verify status matches band (high→ready, others→needs_review)

4. **Test Review Workflow**:
   - Use `/api/review/queue` to see documents needing review
   - Test approve/quick-fix endpoints

5. **Verify UI Integration**:
   - Check that confidence bands display correctly
   - Verify review cards show for needs_review documents

---

## 🐛 Known Issues / Edge Cases

1. **Backward Compatibility**: Old invoices without `confidence_breakdown` will have `null` - UI should handle gracefully
2. **Migration**: Existing databases will auto-migrate on first startup
3. **API Response**: `confidence_breakdown` is optional in response (may be null for old invoices)

