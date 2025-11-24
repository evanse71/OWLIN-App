# Backend Self-Test and Cleanup

## SQL Cleanup for Mock Data

If you need to manually purge old mock invoice data from the database:

```sql
-- Delete line items associated with mock invoices
DELETE FROM invoice_line_items 
WHERE invoice_id IN (
    SELECT id FROM invoices WHERE supplier LIKE 'Supplier-%'
);

-- Delete mock invoices
DELETE FROM invoices WHERE supplier LIKE 'Supplier-%';
```

**Note**: These commands remove invoices with supplier names matching the pattern `Supplier-xxxx` (created by the old mock pipeline that has been removed).

## Mock Pipeline Removal

The mock pipeline that generated "Supplier-xxxx", "Organic Produce", and "Fresh Dairy Products" has been completely removed. The system now:

- Always uses the real OCR v2 pipeline (or fails with clear error)
- Returns only real data from database in status endpoints
- No synthetic/fabricated invoice data

If `FEATURE_OCR_PIPELINE_V2` is disabled, the system will raise an error instead of falling back to mock data.

