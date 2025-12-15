# Owlin Performance Monitoring

This document covers the performance monitoring and regression detection system for Owlin.

## Overview

The performance monitoring system provides:
- Automated benchmark execution
- Regression detection against baselines
- Performance history tracking
- System health dashboard
- Alert generation for performance issues

## Files and Locations

```
data/benchmarks/
├── baseline.json              # Performance baseline metrics
├── history.jsonl             # Rolling benchmark history
└── benchmark_run_*.json      # Individual benchmark results

scripts/
├── performance_benchmark.py   # Main benchmark runner
└── nightly_benchmark.py       # Automated nightly execution

backend/performance/
├── timing.py                 # Timing utilities
└── regression.py             # Regression detection

backend/api/performance_router.py  # Performance API endpoints
```

## Running Benchmarks

### Manual Benchmark Execution

```bash
# Run benchmark on 10 documents (default)
python scripts/performance_benchmark.py --n=10

# Run with custom parameters
python scripts/performance_benchmark.py --n=5 --db-path=data/owlin.db --benchmark-dir=data/benchmarks

# Set random seed for reproducible results
python scripts/performance_benchmark.py --n=10 --seed=42
```

### Nightly Automated Execution

```bash
# Run nightly benchmark (updates history.jsonl)
python scripts/nightly_benchmark.py --n=10

# Update baseline from latest benchmark
python scripts/nightly_benchmark.py --n=10 --update-baseline

# Show history summary only
python scripts/nightly_benchmark.py --history-only
```

## Baseline Management

### Creating Baselines

Baselines are automatically created from the first benchmark run. To manually create/update a baseline:

```bash
# Update baseline from latest benchmark
OWLIN_PERF_UPDATE_BASELINE=true python scripts/nightly_benchmark.py --n=10

# Or use the regression detector directly
python -c "from backend.performance.regression import PerformanceRegressionDetector; detector = PerformanceRegressionDetector(); detector.create_baseline_from_latest()"
```

### Baseline Structure

The baseline file (`data/benchmarks/baseline.json`) contains:

```json
{
  "avg_total_time": 2.5,
  "avg_ocr_time": 0.3,
  "avg_llm_time": 1.8,
  "avg_memory_mb": 12.5,
  "success_rate": 0.95,
  "created_at": "2025-10-20T21:00:00Z",
  "source_benchmark": "2025-10-20T21:00:00Z",
  "documents": 10
}
```

## Regression Detection

### Running Regression Checks

```bash
# Run regression check (pytest-style)
python -m pytest backend/performance/regression.py::test_performance_regression -v

# Run regression check directly
python backend/performance/regression.py

# Soft fail mode (warnings instead of failures)
OWLIN_PERF_SOFT_FAIL=true python backend/performance/regression.py
```

### Configuration

Environment variables for regression detection:

- `OWLIN_PERF_REGRESSION_PCT`: Regression threshold (default: 0.20 = 20%)
- `OWLIN_PERF_SOFT_FAIL`: Convert failures to warnings (default: false)
- `OWLIN_PERF_UPDATE_BASELINE`: Update baseline from latest run (default: false)

### Regression Criteria

The system detects regressions when:
- Total processing time increases by >20% (configurable)
- OCR processing time increases by >20%
- LLM processing time increases by >20%
- Memory usage increases by >20%
- Success rate drops by >10%

## API Endpoints

### Performance Summary
```
GET /api/system/perf_summary
```
Returns latest benchmark metrics and system status.

### Performance Alerts
```
GET /api/system/perf_alerts
```
Returns performance alerts and regression information.

### Performance History
```
GET /api/system/perf_history?limit=50
```
Returns recent benchmark history (default: 50 entries).

### System Status
```
GET /api/system/perf_status
```
Returns system health and directory status.

## System Health Dashboard

Access the system health dashboard at:
```
http://localhost:8000/system-health/
```

The dashboard shows:
- Performance metrics (avg total time, OCR time, LLM time)
- Performance alerts and regressions
- Performance trend chart
- Download latest benchmark data

## Interpreting Results

### Performance Metrics

- **Total Time**: End-to-end processing time per document
- **OCR Time**: Optical character recognition processing time
- **LLM Time**: Large language model processing time
- **Memory Usage**: Memory consumption during processing
- **Success Rate**: Percentage of successfully processed documents

### Alert Severity Levels

- **High**: >50% performance degradation
- **Medium**: 20-50% performance degradation
- **Low**: <20% performance degradation

### Common Issues

1. **High Total Time**: Check OCR and LLM processing times
2. **Low Success Rate**: Check for model availability and configuration
3. **Memory Issues**: Monitor memory usage trends
4. **OCR Slowdown**: Check image preprocessing and OCR model status

## Rollback Procedures

### Soft Rollback (Recommended)

```bash
# Enable soft fail mode to prevent CI failures
export OWLIN_PERF_SOFT_FAIL=true

# Re-run benchmarks to verify
python scripts/performance_benchmark.py --n=10
```

### Hard Rollback

```bash
# Restore previous baseline
cp data/benchmarks/baseline.json.backup data/benchmarks/baseline.json

# Or reset baseline from a known good benchmark
python -c "
from backend.performance.regression import PerformanceRegressionDetector
detector = PerformanceRegressionDetector()
detector.create_baseline_from_latest()
"
```

### Emergency Procedures

```bash
# Disable performance monitoring temporarily
export OWLIN_PERF_SOFT_FAIL=true

# Clear problematic baseline
rm data/benchmarks/baseline.json

# Re-run to create new baseline
python scripts/nightly_benchmark.py --n=10 --update-baseline
```

## Monitoring and Maintenance

### Daily Checks

1. Review performance alerts in the dashboard
2. Check for regression trends
3. Verify benchmark execution success

### Weekly Tasks

1. Review performance history trends
2. Update baselines if needed
3. Clean up old benchmark files

### Monthly Tasks

1. Analyze performance trends
2. Review and adjust regression thresholds
3. Archive old benchmark data

## Troubleshooting

### Common Issues

**No benchmark data found**
- Ensure `data/benchmarks/` directory exists
- Run a benchmark first: `python scripts/performance_benchmark.py --n=3`

**Baseline creation failed**
- Check file permissions on `data/benchmarks/`
- Ensure latest benchmark file is valid JSON

**API endpoints return errors**
- Check FastAPI server is running
- Verify database connectivity
- Check file system permissions

**Dashboard shows no data**
- Verify API endpoints are accessible
- Check browser console for JavaScript errors
- Ensure benchmark data exists

### Debug Commands

```bash
# Check benchmark directory
ls -la data/benchmarks/

# Verify baseline file
cat data/benchmarks/baseline.json

# Check history file
tail -5 data/benchmarks/history.jsonl

# Test API endpoints
curl http://localhost:8000/api/system/perf_summary
curl http://localhost:8000/api/system/perf_alerts
```

## Integration with CI/CD

### GitHub Actions Example

```yaml
name: Performance Regression Check
on: [push, pull_request]

jobs:
  performance-check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Run performance benchmark
        run: python scripts/performance_benchmark.py --n=5
      - name: Check for regressions
        run: python backend/performance/regression.py
        env:
          OWLIN_PERF_SOFT_FAIL: true
```

### Jenkins Pipeline Example

```groovy
pipeline {
    agent any
    stages {
        stage('Performance Test') {
            steps {
                sh 'python scripts/performance_benchmark.py --n=10'
            }
        }
        stage('Regression Check') {
            steps {
                sh 'python backend/performance/regression.py'
            }
        }
    }
    post {
        always {
            archiveArtifacts artifacts: 'data/benchmarks/*.json'
        }
    }
}
```

## Best Practices

1. **Regular Baselines**: Update baselines monthly or after significant changes
2. **Monitor Trends**: Watch for gradual performance degradation
3. **Document Changes**: Note any system changes that might affect performance
4. **Backup Baselines**: Keep baseline backups before major updates
5. **Test Environment**: Run performance tests in production-like environments
6. **Resource Monitoring**: Monitor system resources during benchmark runs
7. **Alert Thresholds**: Adjust regression thresholds based on system requirements

## Support

For issues with performance monitoring:
1. Check this documentation first
2. Review system logs for errors
3. Verify file permissions and directory structure
4. Test with minimal benchmark runs (--n=3)
5. Contact system administrator if issues persist
