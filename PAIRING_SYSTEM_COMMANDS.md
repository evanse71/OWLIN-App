# Pairing System - Complete Command Reference

## 🚀 Quick Start (All Commands)

### Step 1: Navigate to Project
```powershell
cd C:\Users\tedev\FixPack_2025-11-02_133105
```

### Step 2: Apply Database Migration (One-Time)
```powershell
python scripts\add_pairing_columns.py
```

### Step 3: Start Backend Server
```powershell
python -m uvicorn backend.main:app --port 8000
```
**Keep this terminal open** - backend must stay running.

### Step 4: Test Pairing System (New Terminal)
```powershell
cd C:\Users\tedev\FixPack_2025-11-02_133105
python scripts\test_pairing_system.py
```

---

## 📋 Complete Command List

### Database Setup

#### Apply Migration
```powershell
python scripts\add_pairing_columns.py
```

#### Verify Schema
```powershell
python scripts\debug_db_schema.py
```

---

### Backend Server

#### Start Backend
```powershell
python -m uvicorn backend.main:app --port 8000
```

#### Check if Backend is Running
```powershell
Invoke-RestMethod -Uri "http://localhost:8000/api/health"
```

---

### Testing & Development

#### Run Full Test Suite
```powershell
python scripts\test_pairing_system.py
```

#### Query Pairing Events
```powershell
python scripts\query_pairing_events.py
```

---

### API Endpoints (PowerShell)

#### Get Pairing Suggestions
```powershell
$invoiceId = "test-inv-1"
Invoke-RestMethod -Uri "http://localhost:8000/api/pairing/invoice/$invoiceId"
```

#### Confirm a Pairing
```powershell
$invoiceId = "test-inv-1"
$dnId = "test-dn-doc-1"
$body = @{delivery_note_id = $dnId} | ConvertTo-Json
Invoke-RestMethod -Uri "http://localhost:8000/api/pairing/invoice/$invoiceId/confirm" -Method POST -ContentType "application/json" -Body $body
```

#### Reject a Suggestion
```powershell
$invoiceId = "test-inv-1"
$dnId = "test-dn-doc-1"
$body = @{delivery_note_id = $dnId} | ConvertTo-Json
Invoke-RestMethod -Uri "http://localhost:8000/api/pairing/invoice/$invoiceId/reject" -Method POST -ContentType "application/json" -Body $body
```

#### Unpair an Invoice
```powershell
$invoiceId = "test-inv-1"
Invoke-RestMethod -Uri "http://localhost:8000/api/pairing/invoice/$invoiceId/unpair" -Method POST -ContentType "application/json" -Body "{}"
```

#### Reassign to Different Delivery Note
```powershell
$invoiceId = "test-inv-1"
$newDnId = "test-dn-doc-2"
$body = @{new_delivery_note_id = $newDnId} | ConvertTo-Json
Invoke-RestMethod -Uri "http://localhost:8000/api/pairing/invoice/$invoiceId/reassign" -Method POST -ContentType "application/json" -Body $body
```

---

### Database Queries

#### Query Pairing Events (Python Script)
```powershell
python scripts\query_pairing_events.py
```

#### Query Pairing Events (Direct SQL)
```powershell
python -c "import sqlite3; conn = sqlite3.connect('data/owlin.db'); cur = conn.cursor(); cur.execute('SELECT timestamp, invoice_id, delivery_note_id, action, actor_type FROM pairing_events ORDER BY timestamp DESC LIMIT 10'); [print(f'{r[0]} | {r[3]} | Invoice: {r[1]} | DN: {r[2] or \"N/A\"} | Actor: {r[4]}') for r in cur.fetchall()]; conn.close()"
```

#### Check Current Pairing Status
```powershell
python -c "import sqlite3; conn = sqlite3.connect('data/owlin.db'); cur = conn.cursor(); cur.execute('SELECT id, delivery_note_id, pairing_status, pairing_confidence FROM invoices WHERE pairing_status != \"unpaired\" LIMIT 10'); [print(f'Invoice: {r[0]} | DN: {r[1] or \"N/A\"} | Status: {r[2]} | Confidence: {r[3]}') for r in cur.fetchall()]; conn.close()"
```

---

### Model Training (Optional)

#### Install Required Packages
```powershell
pip install scikit-learn joblib
```

#### Train Pairing Model
```powershell
python backend\scripts\train_pairing_model.py
```

**Note**: Requires ≥50 historical pairing events to be useful.

---

## 🔧 Troubleshooting

### Backend Won't Start (Port 8000 in Use)

#### Find Process Using Port
```powershell
netstat -ano | findstr :8000
```

#### Kill Process
```powershell
taskkill /PID <PID_NUMBER> /F
```

### Database Locked Error

1. Stop the backend server (Ctrl+C)
2. Run migration again:
   ```powershell
   python scripts\add_pairing_columns.py
   ```
3. Restart backend

### Import Errors

Make sure you're in the project directory:
```powershell
cd C:\Users\tedev\FixPack_2025-11-02_133105
```

---

## 📊 Monitoring

### Check Pairing Statistics
```powershell
python -c "import sqlite3; conn = sqlite3.connect('data/owlin.db'); cur = conn.cursor(); cur.execute('SELECT pairing_status, COUNT(*) FROM invoices GROUP BY pairing_status'); [print(f'{r[0]}: {r[1]}') for r in cur.fetchall()]; conn.close()"
```

### View Recent Auto-Pairs
```powershell
python -c "import sqlite3; conn = sqlite3.connect('data/owlin.db'); cur = conn.cursor(); cur.execute('SELECT timestamp, invoice_id, delivery_note_id FROM pairing_events WHERE action = \"auto_paired\" ORDER BY timestamp DESC LIMIT 10'); [print(f'{r[0]} | Invoice: {r[1]} | DN: {r[2]}') for r in cur.fetchall()]; conn.close()"
```

---

## ✅ Verification Checklist

After setup, verify everything works:

- [ ] Database migration completed successfully
- [ ] Backend starts without errors
- [ ] Test script creates sample data
- [ ] Pairing endpoint returns suggestions
- [ ] Confirm endpoint pairs invoice to DN
- [ ] Reject endpoint sets status to unpaired
- [ ] Unpair endpoint clears relationship
- [ ] Reassign endpoint changes pairing
- [ ] Pairing events are logged to database

---

## 🎯 Quick Reference

**Most Common Commands:**

```powershell
# Setup (one-time)
cd C:\Users\tedev\FixPack_2025-11-02_133105
python scripts\add_pairing_columns.py

# Start backend
python -m uvicorn backend.main:app --port 8000

# Test system
python scripts\test_pairing_system.py

# View events
python scripts\query_pairing_events.py
```

---

**Last Updated**: 2025-12-01  
**Status**: ✅ All Commands Tested and Working

