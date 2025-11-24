# Service Level Objectives (SLOs)

## Overview

This document defines what "healthy" looks like for the Owlin Invoice OCR system in production.

---

## Health Metrics

### Database
| Metric | Target | Critical Threshold | Action |
|--------|--------|-------------------|--------|
| `db_wal` | `true` | `false` | **IMMEDIATE**: Stop backend, check DB init, restart |
| DB size growth | < 100MB/day | > 500MB/day | Review retention, check for duplicate uploads |
| WAL file size | < 10MB | > 50MB | Force checkpoint: `PRAGMA wal_checkpoint(TRUNCATE)` |

### OCR Pipeline
| Metric | Target | Warning | Critical | Action |
|--------|--------|---------|----------|--------|
| `ocr_inflight` | < `ocr_max_concurrency` | = max for >5 min | = max for >10 min | Check CPU/memory, investigate slow documents |
| `ocr_queue` | < 5 | ≥ 10 | ≥ 20 | Throttle uploads OR increase `OCR_MAX_CONCURRENCY` |
| Processing time (UPLOAD→DOC_READY) | ≤ 10s median | > 30s p95 | > 60s p95 | Check OCR service, review document complexity |
| Error rate | < 1% daily | ≥ 5% | ≥ 10% | Review logs for patterns, check file formats |

### System Resources
| Metric | Target | Warning | Critical | Action |
|--------|--------|---------|----------|--------|
| CPU usage | < 70% avg | ≥ 80% | ≥ 90% | Reduce `OCR_MAX_CONCURRENCY`, scale vertically |
| Memory usage | < 4GB | ≥ 6GB | ≥ 8GB | Restart backend, check for memory leaks |
| Disk space (data dir) | > 10GB free | < 5GB | < 1GB | Archive old uploads, rotate logs, purge old invoices |
| Log disk usage | < 20MB | ≥ 50MB | ≥ 100MB | Verify rotation, manually archive old logs |

---

## Latency Targets

### API Endpoints
| Endpoint | p50 | p95 | p99 | Notes |
|----------|-----|-----|-----|-------|
| `GET /api/health/details` | < 50ms | < 100ms | < 200ms | Lightweight, no heavy queries |
| `GET /api/invoices` (50 items) | < 200ms | < 500ms | < 1s | Includes DB query + line items |
| `POST /api/upload` | < 500ms | < 1s | < 2s | File save only; OCR is async |
| `GET /api/debug/lifecycle` | < 100ms | < 300ms | < 500ms | Log file read, limited to 2KB |
| `GET /api/audit/export` (30 days) | < 2s | < 5s | < 10s | CSV generation, size-dependent |

### OCR Processing
| Stage | p50 | p95 | p99 | Notes |
|-------|-----|-----|-----|-------|
| UPLOAD_SAVED → OCR_ENQUEUE | < 100ms | < 500ms | < 1s | Immediate if queue not full |
| OCR_ENQUEUE → OCR_START | < 1s | < 5s | < 30s | Depends on queue depth |
| OCR_START → OCR_DONE | < 5s | < 15s | < 30s | Depends on document size/complexity |
| PARSE_DONE → DOC_READY | < 500ms | < 2s | < 5s | Line item extraction + DB writes |
| **Total: UPLOAD → DOC_READY** | **< 10s** | **< 30s** | **< 60s** | End-to-end latency |

### Frontend
| Metric | Target | Warning | Action |
|--------|--------|---------|--------|
| Time to Interactive (TTI) on `/invoices` | < 1.5s | ≥ 2s | Optimize bundle size, review renders |
| Invoice card render (50 items) | < 200ms | ≥ 500ms | Add virtualization, optimize re-renders |
| Footer state update | < 50ms | ≥ 100ms | Review Zustand store performance |

---

## Availability

### Uptime Target
- **Target**: 99.5% monthly uptime (≈ 3.6 hours downtime/month)
- **Measurement**: Health endpoint availability
- **Excludes**: Planned maintenance windows (announced 24h in advance)

### Planned Maintenance
- **Window**: 02:00-04:00 local time (low-traffic period)
- **Frequency**: Monthly patches, quarterly upgrades
- **Notification**: 24 hours advance notice

---

## Data Integrity

### Backup & Recovery
| Metric | Target | Verification |
|--------|--------|--------------|
| Nightly snapshots | 100% success | Check `C:\Owlin_Snapshots` daily |
| Snapshot retention | 30 days | Automated cleanup via `NightlySnapshot.ps1` |
| Recovery Time Objective (RTO) | < 5 minutes | Test quarterly with `Rollback` procedure |
| Recovery Point Objective (RPO) | < 24 hours | Nightly snapshot at 02:00 |

### Database Consistency
| Check | Frequency | Action on Failure |
|-------|-----------|-------------------|
| WAL mode enabled | Every health check | Stop backend, reinitialize DB |
| Foreign key constraints | On DB init | Log error, prevent startup |
| No orphaned line items | Weekly audit | Run cleanup script, investigate |

---

## Error Budgets

### Monthly Error Budget
Based on 99.5% availability target:
- **Total requests/month**: ~2.5M (assuming 1 req/sec avg)
- **Allowed errors**: 12,500 (0.5%)
- **Tracking**: `total_errors / total_processed` from health endpoint

### Error Categories
| Category | Budget Allocation | Example Errors |
|----------|-------------------|----------------|
| User errors (4xx) | 50% (6,250) | Invalid file format, missing required fields |
| System errors (5xx) | 30% (3,750) | DB connection failures, OCR crashes |
| Timeout errors | 20% (2,500) | OCR processing timeout, API timeout |

### Burn Rate Alerts
- **Fast burn**: >5% error rate sustained for >1 hour → Page operator
- **Slow burn**: >1% error rate sustained for >12 hours → Email alert

---

## Monitoring & Alerting

### Alert Levels

#### **P0 - Critical (Page Immediately)**
- `db_wal: false`
- Error rate > 10% for > 5 minutes
- Backend unavailable for > 2 minutes
- Disk space < 1GB

#### **P1 - Urgent (Page During Business Hours)**
- `ocr_queue` ≥ 20 for > 10 minutes
- Error rate > 5% for > 30 minutes
- Memory usage > 8GB
- CPU usage > 90% for > 10 minutes

#### **P2 - Warning (Email Alert)**
- `ocr_queue` ≥ 10 for > 5 minutes
- Error rate > 1% for > 1 hour
- Disk space < 5GB
- Snapshot failure

### Monitor Script (`Monitor-Production.ps1`)
**Usage:**
```powershell
.\Monitor-Production.ps1 -IntervalSeconds 10 -QueueWarning 10 -QueueCritical 20
```

**Output:**
```
TIME       WAL        QUEUE      INFLIGHT   ERRORS     STATUS
14:35:00   ✓          0          0/4        0          OK
14:35:10   ✓          3          2/4        0          OK
14:35:20   ✓          12         4/4        0          WARN:Q
```

**Alert Colors:**
- **Green**: All metrics within target
- **Yellow**: Warning threshold exceeded
- **Red**: Critical threshold exceeded

---

## Capacity Planning

### Current Baseline
- **OCR Concurrency**: 4 tasks
- **Expected throughput**: ~240 documents/hour (1 doc/10s × 4 workers)
- **System**: 8GB RAM, 4 CPU cores

### Scale-Up Triggers
| Condition | Action | Expected Improvement |
|-----------|--------|---------------------|
| Queue sustained >10 for >1 hour | Increase `OCR_MAX_CONCURRENCY` to 6 | +50% throughput |
| CPU >80% with queue growing | Add 2 more cores | +30% throughput |
| Memory >6GB sustained | Increase to 16GB RAM | Support 8 concurrent tasks |

### Scale-Down Triggers
| Condition | Action | Expected Savings |
|-----------|--------|------------------|
| Queue always 0, inflight <2 | Decrease `OCR_MAX_CONCURRENCY` to 2 | -50% CPU usage |
| Memory <2GB for >7 days | Acceptable with current load | No action needed |

---

## Performance Budgets

### Frontend
| Asset | Size Limit | Current | Action if Exceeded |
|-------|------------|---------|-------------------|
| Main JS bundle | < 500KB gzip | ~200KB | Code-split, lazy load routes |
| CSS bundle | < 50KB gzip | ~30KB | Remove unused styles |
| Total page load | < 1MB | ~500KB | Optimize images, defer non-critical JS |

### Backend
| Metric | Limit | Current | Action if Exceeded |
|--------|-------|---------|-------------------|
| DB query time | < 100ms | ~20ms | Add indexes, optimize queries |
| Log file size | < 5MB | Rotates at 5MB | No action needed |
| Snapshot size | < 500MB | ~300MB | Compress, exclude temp files |

---

## Known Limits

### Hard Limits
| Resource | Limit | Rationale |
|----------|-------|-----------|
| Line items per invoice | 500 | UI performance, memory |
| Lifecycle log payload | 2KB | API response size |
| Upload file size | 100MB | FastAPI default |
| OCR concurrent tasks | Configurable (default 4) | CPU/memory constraints |

### Soft Limits (Configurable)
| Resource | Default | Config |
|----------|---------|--------|
| Log file size | 5MB | `RotatingFileHandler(maxBytes=...)` |
| Log backups | 3 files | `RotatingFileHandler(backupCount=...)` |
| Snapshot retention | 30 days | `NightlySnapshot.ps1 -RetentionDays` |
| API request timeout | 30s | FastAPI/Uvicorn config |

---

## Runbook Links

- **Health Check**: [OPERATIONS.md - Monitoring](./OPERATIONS.md#monitoring)
- **Rollback**: [BRJ_RELEASE_LOCK.md - Rollback Procedure](../BRJ_RELEASE_LOCK.md#instant-rollback-30s-deterministic)
- **Scaling**: [OPERATIONS.md - Configuration](./OPERATIONS.md#configuration)
- **Troubleshooting**: [RELEASE_CHECKLIST.md - Troubleshooting](../RELEASE_CHECKLIST.md#troubleshooting)

---

## Review & Updates

- **Owner**: Operations Team
- **Review Frequency**: Quarterly
- **Last Updated**: 2025-11-02
- **Next Review**: 2026-02-02

**Change Log:**
- 2025-11-02: Initial SLO document (v1.0)

