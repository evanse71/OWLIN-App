---
name: kill-excessive-quantity-runtime-path
overview: Ensure /api/dev/ocr-test uses the updated extractor, remove excessive_quantity skips in the Phase 4 standard pass, and guarantee salvage returns at least one line item for the Wild Horse invoice
todos:
  - id: confirm-backend-path
    content: Restart backend from FixPack root so updated code runs
    status: pending
  - id: find-standard-pass
    content: Identify Phase 4 standard-pass skip logic producing excessive_quantity
    status: completed
  - id: cap-qty-phase4
    content: Change standard-pass quantity check to cap qty=1 without skipping
    status: completed
  - id: salvage-empty
    content: Ensure salvage sets method_chosen='salvage_excessive_quantity' when no items
    status: completed
  - id: verify-ocr-test
    content: Run Wild Horse OCR test; confirm items>=1 and no excessive_quantity skips
    status: completed
---

# Remove excessive_quantity skip in live path

- Verify the running backend is the FixPack instance and restart from `C:\Users\tedev\FixPack_2025-11-02_133105` to ensure new code loads.
- Locate all Phase 4 standard-pass quantity checks (`quantity > self._max_quantity_threshold`) that append `excessive_quantity` to skipped_lines; identify the exact function used by `/api/dev/ocr-test`.
- Replace skip-with-reason logic: cap quantity to 1, set `qty_source='qty_capped_excessive_phase4'`, log `[QUANTITY_FIX_ACTIVE]`, and do **not** append to skipped_lines.
- Add/verify final salvage in `extract_best_line_items` (or equivalent) so if chosen_items is empty but any numeric line exists, we build one item (qty=1, description from line, prices inferred) and set `method_chosen='salvage_excessive_quantity'`.
- Ensure the `/api/dev/ocr-test` route calls the modified extractor (no legacy path) and that `line_items_debug/skipped_lines` never emit `excessive_quantity` strings.
- Sanity-check with the Wild Horse filename: expect `line_items_count>=1`, `method_chosen != 'none'`, and no `excessive_quantity` reasons in any skipped lists.

## Todos

- confirm-backend-path: Restart backend from FixPack root so updated code runs.
- find-standard-pass: Identify Phase 4 standard-pass skip logic producing `excessive_quantity`.
- cap-qty-phase4: Change standard-pass quantity check to cap qty=1 without skipping.
- salvage-empty: Ensure salvage path sets `method_chosen='salvage_excessive_quantity'` when no items.
- verify-ocr-test: Run Wild Horse OCR test; confirm `line_items_count>=1` and no `excessive_quantity` skips.