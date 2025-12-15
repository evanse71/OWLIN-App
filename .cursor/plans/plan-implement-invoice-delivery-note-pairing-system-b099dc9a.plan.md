---
name: "Plan: Implement Invoice ↔ Delivery Note Pairing System"
overview: ""
todos: []
---

# Plan: Implement Invoice ↔ Delivery Note Pairing System

## 1. Database Schema Updates

I will use `sqlite3` in `backend/app/db.py` (or a new migration script) to:

- Create `delivery_notes` table:
- `id` (PK, likely same as `doc_id` for consistency with invoices)
- `doc_id` (FK to `documents`)
- `invoice_id` (FK to `invoices`, nullable)
- `supplier`, `date`, `total`, `venue` (extracted fields)
- Update `invoices` table:
- Add `delivery_note_id` (FK to `delivery_notes`)
- Add `pairing_status` (TEXT: 'unpaired', 'suggested', 'auto_paired', 'manual_paired')
- Add `pairing_confidence` (REAL)
- Add `pairing_model_version` (TEXT)
- Create `pairing_events` table:
- `id`, `timestamp`, `invoice_id`, `delivery_note_id`, `action`, `actor_type`, `user_id`, `previous_delivery_note_id`, `feature_vector_json`, `model_version`
- Create `supplier_stats` table:
- `supplier_id`, `venue_id`, `typical_delivery_weekdays`, `avg_days_between_deliveries`, `std_days_between_deliveries`, `updated_at`

## 2. Backend Models

- Create `backend/models/delivery_notes.py` (Pydantic models).
- Update `backend/models/invoices.py` to include new fields.

## 3. Pairing Service (`backend/services/pairing_service.py`)

Implement the core logic:

- `get_pairing_candidates(invoice_id)`: Logic to find potential DNs.
- `compute_pair_features(invoice, dn, stats)`: Feature extraction.
- `predict_pairing_probability(features)`: Logistic regression wrapper with fallback.
- `evaluate_pairing(invoice_id, mode)`: Decision engine (auto-pair vs suggest).

## 4. API Routes

- Create `backend/routers/pairing.py` (or similar) with endpoints:
- `GET /api/pairing/invoice/{invoice_id}`
- `POST /api/pairing/invoice/{invoice_id}/confirm`
- `POST /api/pairing/invoice/{invoice_id}/reject`
- `POST /api/pairing/invoice/{invoice_id}/unpair`
- `POST /api/pairing/invoice/{invoice_id}/reassign`
- Wire these routes into `backend/main.py`.

## 5. Integration & Cleanup

- Integrate `evaluate_pairing` into invoice creation flow (if requested, though user said "call... after successful invoice creation").
- Ensure `delivery_notes` are populated when DN documents are processed.
- I will effectively bypass/ignore the old `backend/matching/pairing.py` and `backend/services/auto_pairing.py` logic in favor of this new system.

## Questions to User

(I will proceed with the assumption that I should create a dedicated `delivery_notes` table and start fresh with pairing data as implied by "get rid of that old pairing code".)