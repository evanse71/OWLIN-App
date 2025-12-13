# Invoice API Testing Guide

This guide will help you test the invoice API end-to-end to ensure it's working correctly.

## 🚀 Quick Start

### 1. Start the Test Server

```bash
cd backend
python3 test_server.py
```

The server will start on `http://localhost:8000`

### 2. Seed Test Data

In a new terminal:

```bash
cd backend
python3 seed_test_data.py
```

This will create:
- A test uploaded file
- A test invoice with ID `inv_seed_001` (£72.00 total)
- A test line item (6 x TIA MARIA 1L at £12.00 each)

### 3. Test the API

In another terminal:

```bash
cd backend
python3 test_invoice_api.py
```

Or test manually with curl:

```bash
# Health check
curl http://localhost:8000/health

# Database path
curl http://localhost:8000/api/debug/db-path

# Get invoice (should return proper data)
curl http://localhost:8000/api/invoices/inv_seed_001

# Debug raw data (before penny conversion)
curl http://localhost:8000/api/invoices/debug/raw/inv_seed_001
```

## 🔍 Expected Results

### Health Check
```json
{
  "status": "ok",
  "bulletproof_ingestion": true
}
```

### Database Path
```json
{
  "db_path": "/path/to/owlin.db",
  "exists": true,
  "size_bytes": 12345,
  "resolved": "/absolute/path/to/owlin.db"
}
```

### Invoice Response
```json
{
  "id": "inv_seed_001",
  "meta": {
    "supplier": "TIA MARIA SUPPLIERS",
    "invoice_no": "INV-001",
    "date_iso": "2024-01-15",
    "currency": "GBP",
    "ocr_avg_conf": 0.95,
    "ocr_min_conf": 0.95,
    "total_inc": 72.0
  },
  "lines": [
    {
      "id": 4001,
      "desc": "TIA MARIA 1L",
      "unit_price": 12.0,
      "line_total": 72.0,
      "quantity_each": 6.0,
      "flags": []
    }
  ]
}
```

## 🐛 Troubleshooting

### If you get `{"id": null, "meta": null, "firstLine": null}`

1. **Check database path**: Ensure the seed script and API are using the same database
2. **Verify data exists**: Check if the seed script ran successfully
3. **Check foreign keys**: Ensure the database has foreign key constraints enabled
4. **Check table schema**: Verify the tables match the expected schema

### If the server won't start

1. **Check dependencies**: Ensure FastAPI and uvicorn are installed
2. **Check port**: Ensure port 8000 is not already in use
3. **Check Python path**: Ensure the backend directory is in the Python path

### If seeding fails

1. **Check database permissions**: Ensure the script can write to the database directory
2. **Check schema**: Verify the table creation SQL is correct
3. **Check constraints**: Ensure the CHECK constraints use valid enum values

## 📊 Database Schema

The test uses these tables:

- `uploaded_files`: File metadata and processing status
- `invoices`: Invoice metadata with amounts stored in pennies
- `invoice_line_items`: Line items with prices stored in pennies

## 🔄 Data Flow

1. **Seed Script** → Creates test data in database
2. **fetch_invoice()** → Retrieves raw data with pennies
3. **API Endpoint** → Converts pennies to pounds at the edge
4. **Response** → Returns clean data in pounds

## 🎯 Next Steps

Once the basic API is working:

1. **Add more test data**: Create multiple invoices and line items
2. **Test edge cases**: Empty invoices, missing fields, etc.
3. **Add validation**: Test with invalid invoice IDs
4. **Performance testing**: Test with larger datasets
5. **Frontend integration**: Test the API from the React frontend 