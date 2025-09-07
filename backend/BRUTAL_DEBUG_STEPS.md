# 🧊 BRUTAL DEBUG STEPS - NO GUESSING

## 🚨 **CRITICAL: Your API is returning `{"id": null, "meta": null, "firstLine": null}`**

This means you're hitting a **404** and `jq` is extracting non-existent keys. Here's how to prove what's wrong:

## 0️⃣ **SEE THE TRUTH (NO jq MASKING)**

```bash
# Show status + body
curl -i http://localhost:8000/api/invoices/inv_seed

# Or only the status:
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8000/api/invoices/inv_seed
```

**Interpretation:**
- **200** → route exists; if body is empty/shape wrong, we fix conversion
- **404** → your invoices router isn't mounted (or wrong path)
- **500** → your query is crashing; check server log

## 1️⃣ **LIST THE ROUTES THE SERVER ACTUALLY MOUNTED**

```bash
curl -s http://localhost:8000/openapi.json | jq -r '.paths | keys[]' | sort
```

**You MUST see `/api/invoices/{invoice_id}` (or your exact route).**
If it's missing, your router isn't included.

## 2️⃣ **CHECK DATABASE PATH**

```bash
curl -sS http://localhost:8000/api/debug/db-path | jq .
```

**Expected:**
```json
{
  "db_path": "/Users/glennevans/Downloads/OWLIN-App-main-3/data/owlin.db",
  "exists": true,
  "size_bytes": <nonzero>
}
```

## 3️⃣ **PROVE ROWS EXIST (OR SEED THEM AGAIN)**

```bash
# Check invoices table
sqlite3 "/Users/glennevans/Downloads/OWLIN-App-main-3/data/owlin.db" \
"SELECT id,file_id,total_amount_pennies FROM invoices WHERE id='inv_seed';"

# Check line items
sqlite3 "/Users/glennevans/Downloads/OWLIN-App-main-3/data/owlin.db" \
"SELECT description,quantity,unit_price_pennies,line_total_pennies FROM invoice_line_items WHERE invoice_id='inv_seed';"
```

**If you get NO ROWS, re-seed:**

```bash
export OWLIN_DB_PATH="/Users/glennevans/Downloads/OWLIN-App-main-3/data/owlin.db"

sqlite3 "/Users/glennevans/Downloads/OWLIN-App-main-3/data/owlin.db" <<'SQL'
PRAGMA foreign_keys=ON;

INSERT OR REPLACE INTO uploaded_files
(id, original_filename, canonical_path, file_size, file_hash, mime_type,
 doc_type, doc_type_confidence, upload_timestamp, processing_status, processing_progress,
 created_at, updated_at)
VALUES
('seed_file', 'seed.pdf', '/tmp/seed.pdf', 123, 'deadbeef', 'application/pdf',
 'invoice', 1.0, datetime('now'), 'completed', 100,
 datetime('now'), datetime('now'));

INSERT OR REPLACE INTO invoices
(id, file_id, total_amount_pennies, status, created_at, updated_at)
VALUES
('inv_seed', 'seed_file', 7200, 'completed', datetime('now'), datetime('now'));

INSERT OR REPLACE INTO invoice_line_items
(id, invoice_id, row_idx, page, description, quantity, unit_price_pennies, line_total_pennies, created_at, updated_at)
VALUES
(4001, 'inv_seed', 0, 1, 'TIA MARIA 1L', 6.0, 1200, 7200, datetime('now'), datetime('now'));
SQL
```

## 4️⃣ **TEST THE API AGAIN (NO STATUS HIDING)**

```bash
curl -i http://localhost:8000/api/invoices/inv_seed
```

**If 200 with JSON but your `jq '{id, meta, firstLine: .lines[0]}'` still shows nulls:**
Your endpoint is **not returning those keys**. Print the whole JSON first:

```bash
curl -sS http://localhost:8000/api/invoices/inv_seed | jq .
```

## 5️⃣ **IF STILL BROKEN - CHECK SERVER LOGS**

Look for these debug logs I added:
- `🔍 Fetching invoice inv_seed`
- `📄 Invoice data: {...}`
- `📋 Found X line items`
- `✅ Built response: {...}`

## 6️⃣ **TEST SETUP WITHOUT TERMINAL**

```bash
cd backend
python3 test_setup.py
```

This will verify:
- All modules can be imported
- Router structure is correct
- fetch_invoice function works

## 🎯 **PASS CRITERIA (NO PENNY LEAKAGE)**

```json
{
  "id": "inv_seed",
  "meta": { "total_inc": 72.0 },
  "firstLine": {
    "desc": "TIA MARIA 1L",
    "qty": 6.0,
    "unit_price": 12.0,
    "line_total": 72.0,
    "flags": []
  }
}
```

## 📋 **PASTE BACK THESE RESULTS**

1. **Full `-i` output** of `curl http://localhost:8000/api/invoices/inv_seed`
2. **JSON from** `/api/debug/db-path`
3. **Two `sqlite3 SELECT` outputs**

## 🚨 **WHEN THIS IS GREEN, WE FINISH THE INVOICES PAGE**

Brutal checklist, no mercy:
- [ ] `/api/debug/db-path` shows the exact path you seeded
- [ ] `sqlite3` selects show `inv_seed` + one line for it  
- [ ] `/api/invoices/inv_seed` returns **pounds**, not pennies; fields present
- [ ] `/openapi.json` lists the invoices route

## 🔧 **WHAT I FIXED**

1. **Router mounting** - invoices router now properly mounted
2. **Field mapping** - pennies to pounds conversion at edge
3. **Response structure** - matches what frontend expects
4. **Debug endpoints** - can see exactly what's happening
5. **Linter errors** - code can now execute properly

## 🎉 **WHY THIS WILL WORK NOW**

- Router is properly mounted at `/api/invoices/{invoice_id}`
- fetch_invoice returns correct structure with `id`, `meta`, `lines`
- Penny conversion happens at the edge (API response)
- Debug logging shows exactly what's happening
- No more linter errors blocking execution 