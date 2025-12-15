# Owlin Forensic Report — 2025-10-19 19:22:00Z

## Summary
- Backend: 127.0.0.1:8000 — HEALTH OK; CORS verified
- Frontend: 127.0.0.1:5173 — servedFrom: dist — SPA routing OK
- Uploads: PDF validation & processing OK (dedup true)
- API: invoices list/details OK
- Cursor: .cursorignore applied; slim workspace validated

## Evidence (files)
- .backend.log (head/tail)
- .devlog.txt (head/tail)
- .netstat_8000.txt / .netstat_5173.txt
- .api_invoices_list.json
- .upload_response_test.pdf

## Next recommended actions
1. Tag & release (done)
2. Add E2E Playwright tests
3. Schedule nightly backup of data/
4. Add automated support-pack creation to release pipeline
