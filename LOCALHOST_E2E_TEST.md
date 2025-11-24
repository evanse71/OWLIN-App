# 🖥️ Localhost E2E Test Procedure

## Complete Step-by-Step Validation

This procedure validates that your localhost build works exactly like production, with all the hardening and guardrails we've implemented.

---

## 1. Start the Backend

### From your project root:

#### macOS/Linux
```bash
source .venv/bin/activate
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

#### Windows PowerShell
```powershell
. .\.venv\Scripts\Activate.ps1
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

#### Alternative (Simple Backend)
```bash
# If uvicorn not available, use our test backend
python test_backend_simple.py
```

### Check Health
```bash
curl http://127.0.0.1:8000/api/health
```

**✅ Should return:**
```json
{"status": "ok"}
```

**Expected Backend Output:**
```
INFO:     Started server process [12345]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Created uploads directory: data/uploads
```

---

## 2. Start the Frontend

### Open a new terminal:

```bash
cd frontend
npm install
npm run dev
```

### Go to:
👉 **http://localhost:5173** (Vite) or **http://localhost:3000** (Next.js)

**Expected Frontend Output:**
```
▲ Next.js 14.2.33
- Local:        http://localhost:3000
✓ Ready in 1165ms
```

---

## 3. Confirm Environment Config

### Check your frontend/.env.local:
```bash
VITE_API_BASE_URL=http://127.0.0.1:8000
```

**⚠️ Important:** Restart `npm run dev` if you edit this file.

### Alternative locations to check:
- `env.local` (project root)
- `frontend/.env.local`
- `frontend/.env`

---

## 4. Upload a Test File

### Open the app in the browser

#### ✅ Health Banner Check
- **Backend Health Banner** should be **green/healthy**
- Should show: "Backend is online and ready"
- If red: Check backend is running and `VITE_API_BASE_URL` is correct

#### ✅ Upload Test
1. **Drag or select** a small PDF (≤5 MB)
2. **Watch the invoice card** → Uploading… → Processed
3. **Check for specific error messages** (not generic "0% error")

#### ✅ Upload Button State
- **When backend online**: Upload button enabled
- **When backend offline**: Upload button disabled with tooltip

---

## 5. Check Results

### Browser DevTools → Network
1. **Find** `POST /api/upload` request
2. **Check status**: Should be `200/201 OK`
3. **Response JSON** should include:
   ```json
   {
     "ok": true,
     "filename": "test.pdf",
     "bytes": 12345,
     "saved_to": "data/uploads/test.pdf"
   }
   ```

### Backend Console Logs
**Should show:**
```
INFO: upload saved: data/uploads/invoice.pdf (12345 bytes)
```

### File on Disk
**Check** `data/uploads/` for your PDF:
```bash
ls -la data/uploads/
# or on Windows:
dir data\uploads\
```

---

## 6. Smoke Test Scripts (Optional)

### With backend running, in another terminal:

#### Linux/macOS
```bash
bash scripts/smoke_e2e.sh
```

#### Windows PowerShell
```powershell
powershell -ExecutionPolicy Bypass -File scripts/smoke_e2e_simple.ps1
```

#### Edge Case Testing
```powershell
powershell -ExecutionPolicy Bypass -File scripts/smoke_edge.ps1
```

**✅ All should report OK**

---

## 7. Advanced Validation

### Route Assertion
```bash
bash scripts/assert_routes.sh
```

**Should validate:**
- `/api/health` GET route exists
- `/api/upload` POST route exists
- OpenAPI spec is correct

### Support Pack Generation
```bash
bash scripts/make_support_pack.sh
```

**Should create:** `support_pack_YYYYMMDD_HHMMSS.zip`

---

## 8. Error Scenario Testing

### Test Backend Offline
1. **Stop backend** (Ctrl+C)
2. **Refresh frontend**
3. **Check banner** shows "Backend offline"
4. **Upload button** should be disabled
5. **Try upload** - should show specific error message

### Test Wrong API URL
1. **Change** `VITE_API_BASE_URL=http://localhost:9999`
2. **Restart frontend**
3. **Check banner** shows offline
4. **Upload button** disabled

### Test Large File (if limits exist)
1. **Upload** file > 10MB
2. **Check error message** is specific
3. **Should show** "File too large" or similar

---

## 9. Success Criteria

### ✅ All Tests Must Pass

#### Backend Validation
- [ ] `/api/health` returns `{"status":"ok"}`
- [ ] Backend logs show structured messages
- [ ] Uploads directory created automatically
- [ ] Files saved to `data/uploads/`

#### Frontend Validation
- [ ] Health banner shows backend status
- [ ] Upload button enabled when backend online
- [ ] Upload button disabled when backend offline
- [ ] Specific error messages (no generic "0% error")
- [ ] Progress display during upload
- [ ] "Copy error" button works

#### Integration Validation
- [ ] CORS configuration allows communication
- [ ] Environment variables properly configured
- [ ] Smoke tests pass
- [ ] Edge case tests pass
- [ ] Support pack generation works

---

## 10. Troubleshooting

### If Backend Won't Start
```bash
# Check dependencies
pip install fastapi uvicorn python-multipart

# Check port conflicts
netstat -ano | findstr :8000
# Kill process if needed
taskkill /PID <PID> /F
```

### If Frontend Won't Start
```bash
# Check dependencies
npm install

# Check environment
cat frontend/.env.local
# Should show: VITE_API_BASE_URL=http://127.0.0.1:8000
```

### If Upload Fails
1. **Check health banner** - should be green
2. **Check DevTools Network** - look for specific error
3. **Check backend logs** - should show file save
4. **Run smoke test** - `bash scripts/smoke_e2e.sh`

### If Health Banner Shows Offline
1. **Check backend** is running on port 8000
2. **Check environment** `VITE_API_BASE_URL=http://127.0.0.1:8000`
3. **Restart frontend** after env changes
4. **Check CORS** configuration in backend

---

## 11. Production Readiness Checklist

### ✅ System Ready When:
- [ ] All smoke tests pass
- [ ] Health banner shows online
- [ ] Uploads work end-to-end
- [ ] Files saved to disk
- [ ] Specific error messages displayed
- [ ] Support pack generation works
- [ ] Edge case handling works
- [ ] CORS configuration correct

### ❌ System Not Ready When:
- [ ] Health banner shows offline
- [ ] Upload button disabled
- [ ] Generic error messages
- [ ] Files not saved
- [ ] Smoke tests fail
- [ ] CORS errors in console

---

## 🎉 Success!

**If all tests pass, you've just proven the localhost build works exactly like production.**

### Key Validation Points:
- ✅ **Backend**: Health checks, upload endpoint, structured logging
- ✅ **Frontend**: Health monitoring, specific errors, progress display
- ✅ **Integration**: CORS, environment config, file persistence
- ✅ **Testing**: Smoke tests, edge cases, route assertions
- ✅ **Operations**: Support packs, rollback procedures, troubleshooting

### Next Steps:
1. **Deploy to production** with confidence
2. **Implement OCR integration** for real business value
3. **Add single-port demo mode** for cleaner presentations
4. **Enhance UX** with timeout handling and retry mechanisms

**The system is now bulletproof and ready for production deployment!** 🚀
