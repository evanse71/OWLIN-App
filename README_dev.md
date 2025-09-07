# Owlin OCR - Development Guide

## Quick Start

### Environment Setup
```bash
# Required environment variables
export OWLIN_DB=owlin.db
export OWLIN_STORAGE=storage/uploads

# Optional environment variables
export OWLIN_OCR_DELAY_MS=0        # Inject delay for testing timeouts
export OWLIN_JOB_CAP_S=60          # Job timeout in seconds
export OWLIN_DIAG_DIR=backups/diagnostics  # Diagnostic logs directory
```

### Backend Startup
```bash
# From backend/ directory
export OWLIN_DB=owlin.db
export OWLIN_STORAGE=storage/uploads
python3 -m uvicorn app:app --port 8001 --log-level debug
```

### Frontend Startup
```bash
# From project root
npm run dev
```

## Health Checks

### Basic Health
```bash
curl -s http://localhost:8001/health
```

### Post-OCR Pipeline Health
```bash
curl -s http://localhost:8001/api/health/post_ocr | python3 -m json.tool
```

### Database Health
```bash
# Job status summary
sqlite3 $OWLIN_DB "SELECT status, COUNT(*) FROM jobs GROUP BY status;"

# Missing file records
sqlite3 $OWLIN_DB "SELECT COUNT(*) FROM invoices i LEFT JOIN uploaded_files u ON u.file_hash=i.file_hash WHERE u.absolute_path IS NULL;"

# High-confidence zero-line invoices
sqlite3 $OWLIN_DB "SELECT COUNT(*) FROM invoices WHERE confidence >= 80 AND (line_items IS NULL OR line_items = '' OR line_items = '[]');"
```

## File Management

### Rebuild Uploaded Files Table
```bash
# Scan storage and rebuild uploaded_files table
python3 scripts/rebuild_uploaded_files.py
```

### Test Startup Migrations
```bash
# Verify migrations work correctly
python3 test_startup_migrations.py
```

## Features

### Retry Functionality
- Failed/timeout invoices show retry button
- Reprocess endpoint: `/invoices/{id}/reprocess`
- Robust file path resolution with 4-tier fallback

### Diagnostics
- JSONL diagnostics: `backups/diagnostics/diagnostics_YYYYMMDD.jsonl`
- 14-day retention with automatic cleanup
- Comprehensive job lifecycle logging

### Progress Tracking
- 0-60%: Upload/ingest
- 60-95%: OCR/parse/persist
- 95-100%: Complete

### Quality Indicators
- "Needs review" chip for low confidence (<70%) or weak stages
- Confidence badges with color coding
- Validation flags for header/lines/totals issues

## Troubleshooting

### Backend Won't Start
1. Check environment variables are set
2. Verify database path is writable
3. Check for import errors in logs

### Missing Files on Reprocess
1. Run `python3 scripts/rebuild_uploaded_files.py`
2. Check `OWLIN_STORAGE` environment variable
3. Verify file permissions

### Stuck Processing Jobs
1. Check job status: `sqlite3 $OWLIN_DB "SELECT * FROM jobs WHERE status='processing';"`
2. Verify watchdog timeout: `OWLIN_JOB_CAP_S=60`
3. Check logs for error details 