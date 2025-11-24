# Operations Guide - Owlin OCR Pipeline

Production operations manual for monitoring, debugging, and configuring the OCR invoice processing system.

---

## Table of Contents

1. [Configuration](#configuration)
2. [Monitoring](#monitoring)
3. [Debugging](#debugging)
4. [Logs](#logs)
5. [Database](#database)
6. [Known Limits](#known-limits)
7. [Troubleshooting](#troubleshooting)

---

## Configuration

### OCR Concurrency

Control the maximum number of simultaneous OCR processing tasks:

```bash
# Set environment variable (default: 4)
export OCR_MAX_CONCURRENCY=8

# Start backend
python -m uvicorn backend.main:app --port 8000
```

**Recommendations**:
- **Low memory systems** (< 8GB RAM): Set to `2-3`
- **Standard systems** (8-16GB RAM): Set to `4-6` (default: 4)
- **High performance** (> 16GB RAM): Set to `8-12`

**Effect**: Limits concurrent OCR tasks. When limit is reached, new uploads queue until slots free up.

### OCR Pipeline Version

Enable advanced OCR v2 pipeline (PaddleOCR + Tesseract):

```bash
# Enable v2 (requires PaddleOCR installed)
export FEATURE_OCR_PIPELINE_V2=true

# Disable v2 (uses simple mock pipeline)
export FEATURE_OCR_PIPELINE_V2=false  # Default
```

**V2 Requirements**:
```bash
pip install paddleocr paddlepaddle
```

---

## Monitoring

### Health Endpoint

**GET** `/api/health/details`

Returns comprehensive system status and metrics:

```json
{
  "status": "ok",
  "db_wal": true,
  "ocr_v2_enabled": false,
  "ocr_max_concurrency": 4,
  "ocr_inflight": 2,
  "ocr_queue": 5,
  "total_processed": 127,
  "total_errors": 3,
  "build_sha": "a3f2e1b",
  "last_doc_id": "abc123-...",
  "timestamp": "2025-11-02T14:30:00"
}
```

**Key Metrics**:

| Field | Description | Action If |
|-------|-------------|-----------|
| `db_wal` | SQLite WAL mode enabled | `false` → Check DB initialization |
| `ocr_inflight` | Currently processing | High + slow → Check CPU/memory |
| `ocr_queue` | Waiting to process | Growing → Increase `OCR_MAX_CONCURRENCY` |
| `total_errors` | Lifetime error count | Increasing → Check logs for patterns |
| `build_sha` | Git commit hash | Verify correct deployment |

**Usage**:
```bash
# PowerShell
$health = Invoke-RestMethod http://127.0.0.1:8000/api/health/details
$health | ConvertTo-Json

# Bash
curl http://127.0.0.1:8000/api/health/details | jq

# Monitor queue depth (alert if > 10)
curl -s http://127.0.0.1:8000/api/health/details | jq .ocr_queue
```

---

## Debugging

### Lifecycle Tracing

**GET** `/api/debug/lifecycle?doc_id=<doc_id>`

Returns ordered lifecycle markers for a specific document:

```json
{
  "doc_id": "abc123",
  "markers": [
    "[OCR_LIFECYCLE] stage=UPLOAD_SAVED doc_id=abc123 file=data/uploads/...",
    "[OCR_LIFECYCLE] stage=OCR_ENQUEUE doc_id=abc123",
    "[OCR_LIFECYCLE] stage=OCR_PICK doc_id=abc123 pipeline=simple",
    "[OCR_LIFECYCLE] stage=OCR_START doc_id=abc123",
    "[OCR_LIFECYCLE] stage=OCR_DONE doc_id=abc123 confidence=0.85",
    "[OCR_LIFECYCLE] stage=PARSE_START doc_id=abc123",
    "[OCR_LIFECYCLE] stage=PARSE_DONE doc_id=abc123 items=2",
    "[OCR_LIFECYCLE] stage=DOC_READY doc_id=abc123 supplier=... total=245.67 items=2 confidence=0.85"
  ],
  "truncated": false,
  "count": 8
}
```

**Lifecycle Stages**:

| Stage | Meaning | Next Expected |
|-------|---------|---------------|
| `UPLOAD_SAVED` | File saved to disk | `OCR_ENQUEUE` |
| `OCR_ENQUEUE` | Added to processing queue | `OCR_PICK` (may be delayed if queue full) |
| `OCR_PICK` | Worker picked up task | `OCR_START` |
| `OCR_START` | OCR processing began | `OCR_DONE` (2-10s typical) |
| `OCR_DONE` | OCR extraction complete | `PARSE_START` |
| `PARSE_START` | Parsing extracted text | `PARSE_DONE` |
| `PARSE_DONE` | Line items extracted | `DOC_READY` |
| `DOC_READY` | Invoice ready for UI | N/A (success) |
| `OCR_ERROR` | Processing failed | Manual retry needed |

**Usage**:
```bash
# PowerShell (get most recent upload)
$inv = Invoke-RestMethod http://127.0.0.1:8000/api/invoices
$docId = $inv.invoices[0].id
Invoke-RestMethod "http://127.0.0.1:8000/api/debug/lifecycle?doc_id=$docId"

# Bash
DOC_ID=$(curl -s http://127.0.0.1:8000/api/invoices | jq -r '.invoices[0].id')
curl "http://127.0.0.1:8000/api/debug/lifecycle?doc_id=$DOC_ID" | jq
```

**Troubleshooting**:
- **Stuck at OCR_ENQUEUE**: Queue full, wait or increase `OCR_MAX_CONCURRENCY`
- **OCR_START but no OCR_DONE**: OCR crashed, check logs for exceptions
- **Missing PARSE_DONE**: Extraction failed, check file format
- **OCR_ERROR**: See logs for specific error message

---

## Logs

### Location & Rotation

**Log Files**:
```
backend_stdout.log       # Current log
backend_stdout.log.1     # Previous rotation
backend_stdout.log.2     # 2 rotations ago
backend_stdout.log.3     # Oldest backup
```

**Rotation**:
- **Size**: 5MB per file
- **Backups**: 3 files kept
- **Encoding**: UTF-8

**Manual Rotation** (if needed):
```bash
# PowerShell
Move-Item backend_stdout.log backend_stdout.log.manual
# Backend will create new file automatically

# Bash
mv backend_stdout.log backend_stdout.log.manual
```

### Log Format

**Lifecycle Markers**:
```
[OCR_LIFECYCLE] stage=<STAGE> doc_id=<id> [key=value ...]
```

**Error Markers**:
```
[ITEMS_TRUNCATED] doc_id=<id> count=<n> limit=500
```

### Searching Logs

```powershell
# PowerShell: Find all lifecycle events for a doc
Select-String backend_stdout.log* -Pattern "doc_id=abc123" | Select-Object -First 20

# PowerShell: Find truncation events
Select-String backend_stdout.log* -Pattern "ITEMS_TRUNCATED"

# PowerShell: Count errors in last 24h
$since = (Get-Date).AddDays(-1)
Get-Content backend_stdout.log | Select-String "ERROR|FAIL" | Measure-Object -Line
```

```bash
# Bash: Find all lifecycle events for a doc
grep "doc_id=abc123" backend_stdout.log* | head -20

# Bash: Find truncation events
grep "ITEMS_TRUNCATED" backend_stdout.log*

# Bash: Tail real-time
tail -f backend_stdout.log | grep OCR_LIFECYCLE
```

---

## Database

### WAL Mode Verification

**Check Status**:
```bash
# Via health endpoint
curl http://127.0.0.1:8000/api/health/details | jq .db_wal
# Should return: true

# Via SQLite CLI (if available)
sqlite3 data/owlin.db "PRAGMA journal_mode;"
# Should return: wal
```

**Why WAL Matters**:
- **Concurrency**: Allows simultaneous reads during writes
- **Performance**: Faster writes (append-only)
- **Safety**: Better crash recovery than DELETE or TRUNCATE modes

**Manual Enable** (if disabled):
```bash
sqlite3 data/owlin.db "PRAGMA journal_mode=WAL; PRAGMA synchronous=NORMAL; PRAGMA foreign_keys=ON;"
```

### Database Size

```bash
# PowerShell
Get-Item data\owlin.db | Select-Object Name, @{N='SizeMB';E={[math]::Round($_.Length/1MB,2)}}

# Bash
du -h data/owlin.db
```

**Maintenance** (if > 1GB):
```bash
# Vacuum to reclaim space (safe, but locks DB briefly)
sqlite3 data/owlin.db "VACUUM;"
```

---

## Known Limits

### Hard Limits

| Resource | Limit | Rationale |
|----------|-------|-----------|
| **Line items per invoice** | 500 | UI performance, memory |
| **Lifecycle log payload** | 2KB | API response size |
| **Upload file size** | 100MB | Default FastAPI limit |
| **Concurrent OCR tasks** | `OCR_MAX_CONCURRENCY` (default 4) | CPU/memory |

### Soft Limits (Configurable)

| Resource | Default | Config |
|----------|---------|--------|
| Log file size | 5MB | `RotatingFileHandler(maxBytes=...)` |
| Log backups | 3 files | `RotatingFileHandler(backupCount=...)` |

### HTTP Return Codes

| Code | Endpoint | Meaning | Action |
|------|----------|---------|--------|
| **200** | All | Success | N/A |
| **404** | `/api/ocr/retry/{doc_id}` | Document not found | Check doc_id |
| **404** | `/api/invoices/{id}` | Invoice not found | Check invoice_id |
| **500** | `/api/upload` | Upload failed | Check disk space, logs |
| **500** | `/api/ocr/retry/{doc_id}` | File missing on disk | File was deleted |

---

## Troubleshooting

### Scenario 1: Uploads Queuing Up

**Symptoms**:
- `ocr_queue` growing (> 10)
- Slow processing times

**Check**:
```bash
curl http://127.0.0.1:8000/api/health/details | jq '{queue: .ocr_queue, inflight: .ocr_inflight, max: .ocr_max_concurrency}'
```

**Fix**:
1. Increase concurrency:
   ```bash
   export OCR_MAX_CONCURRENCY=8
   # Restart backend
   ```
2. Check CPU/memory usage:
   ```bash
   # PowerShell
   Get-Process python | Select-Object CPU, WorkingSet

   # Bash
   top -p $(pgrep python)
   ```

### Scenario 2: Document Stuck "Processing"

**Symptoms**:
- Invoice status stays `processing` > 30s
- No `DOC_READY` in lifecycle

**Debug**:
```bash
# Get lifecycle markers
curl "http://127.0.0.1:8000/api/debug/lifecycle?doc_id=<doc_id>" | jq .markers

# Check logs for errors
grep "<doc_id>" backend_stdout.log | grep ERROR
```

**Common Causes**:
- OCR crashed (check logs for exception)
- File format unsupported (check file extension)
- Queue full (check `ocr_queue`)

**Fix**:
```bash
# Retry OCR
curl -X POST http://127.0.0.1:8000/api/ocr/retry/<doc_id>
```

### Scenario 3: Line Items Truncated

**Symptoms**:
- Invoice has exactly 500 line items
- Log shows `[ITEMS_TRUNCATED]`

**Check**:
```bash
grep "ITEMS_TRUNCATED" backend_stdout.log*
```

**Expected Behavior**:
- Limit protects UI from rendering > 500 rows
- First 500 items are kept (ordered by line number)

**Fix** (if limit too low):
1. Edit `backend/services/ocr_service.py`:
   ```python
   MAX_LINE_ITEMS = 1000  # Increase from 500
   ```
2. Restart backend
3. Retry affected documents

### Scenario 4: WAL Mode Disabled

**Symptoms**:
- `db_wal: false` in health endpoint
- Slow concurrent access

**Fix**:
```bash
# Stop backend
# Enable WAL
sqlite3 data/owlin.db "PRAGMA journal_mode=WAL;"
# Restart backend
```

**Verify**:
```bash
curl http://127.0.0.1:8000/api/health/details | jq .db_wal
# Should return: true
```

---

## Audit Export

**GET** `/api/audit/export?from=YYYY-MM-DD&to=YYYY-MM-DD`

Export audit trail as CSV:

```bash
# PowerShell
$from = (Get-Date).AddDays(-7).ToString('yyyy-MM-dd')
$to = (Get-Date).ToString('yyyy-MM-dd')
Invoke-WebRequest "http://127.0.0.1:8000/api/audit/export?from=$from&to=$to" -OutFile audit_export.csv

# Bash
FROM=$(date -d '7 days ago' +%Y-%m-%d)
TO=$(date +%Y-%m-%d)
curl "http://127.0.0.1:8000/api/audit/export?from=$FROM&to=$TO" > audit_export.csv
```

**CSV Columns**:
- `ts`: Timestamp (ISO 8601)
- `event`: Event name (e.g., `upload`, `ocr_run`, `SESSION_CLEAR`)
- `doc_id`: Document ID (if applicable)
- `invoice_id`: Invoice ID (if applicable)
- `stage`: OCR stage (if applicable)
- `detail`: JSON detail object

---

## Alerting Recommendations

### Critical Alerts

```bash
# Queue depth > 20
curl -s http://127.0.0.1:8000/api/health/details | jq -e '.ocr_queue > 20'

# Error rate > 10%
curl -s http://127.0.0.1:8000/api/health/details | jq -e '(.total_errors / .total_processed) > 0.1'

# DB not in WAL mode
curl -s http://127.0.0.1:8000/api/health/details | jq -e '.db_wal == false'
```

### Warning Alerts

```bash
# Queue depth > 10
curl -s http://127.0.0.1:8000/api/health/details | jq -e '.ocr_queue > 10'

# High inflight (all workers busy)
curl -s http://127.0.0.1:8000/api/health/details | jq -e '.ocr_inflight >= .ocr_max_concurrency'
```

---

## Next Steps

**Production Enhancements**:
1. **Prometheus Metrics**: Add `/metrics` endpoint for Grafana dashboards
2. **Performance Budgets**: Monitor Time To Interactive (TTI) < 2s on `/invoices`
3. **Health Checks**: Add liveness (`/health`) and readiness (`/health/ready`) probes
4. **Distributed Tracing**: Add OpenTelemetry spans for lifecycle visibility
5. **Auto-scaling**: Scale `OCR_MAX_CONCURRENCY` based on queue depth

---

**Last Updated**: 2025-11-02  
**Version**: 1.2.0
