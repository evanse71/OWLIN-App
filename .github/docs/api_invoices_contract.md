# API Invoices Contract

## Overview
This document defines the stable contract for the `/api/invoices` and `/api/invoices/{id}` endpoints. All client code must rely only on these documented fields and types.

## Status Enum
```typescript
type InvoiceStatus = 'pending' | 'scanned' | 'processed' | 'matched' | 'flagged' | 'error'
```

## Confidence Scale
- **Range**: 0.0 to 1.0 (inclusive)
- **Type**: number
- **Note**: Any values outside this range are invalid and should be normalized

## GET /api/invoices

### Request
```
GET /api/invoices?status=&limit=&offset=&sort=
```

### Response Schema
```typescript
interface InvoicesResponse {
  invoices: InvoiceSummary[]
  count: number        // Number of invoices in current page
  total: number       // Total invoices across all pages
  limit: number       // Page size limit
  offset: number      // Current page offset
}
```

### InvoiceSummary Schema
```typescript
interface InvoiceSummary {
  id: string                    // Unique invoice identifier
  filename: string             // Original filename
  supplier: string             // Supplier name
  date: string                 // Invoice date (YYYY-MM-DD format)
  total_value: number          // Invoice total amount
  status: InvoiceStatus         // Processing status
  confidence: number           // OCR confidence (0-1)
  venue: string                // Venue name
  issues_count: number         // Number of flagged issues
  paired: boolean              // Whether paired with delivery note
  delivery_note_ids: string[]  // Array of associated delivery note IDs
  source_filename?: string     // Original document filename (for grouping)
}
```

### Example Response
```json
{
  "invoices": [
    {
      "id": "inv_001",
      "filename": "invoice_001.pdf",
      "supplier": "ACME Corp",
      "date": "2024-01-15",
      "total_value": 150.50,
      "status": "scanned",
      "confidence": 0.95,
      "venue": "Royal Oak Hotel",
      "issues_count": 2,
      "paired": false,
      "delivery_note_ids": ["dn_001", "dn_002"],
      "source_filename": "multi_invoice_batch.pdf"
    }
  ],
  "count": 1,
  "total": 1,
  "limit": 50,
  "offset": 0
}
```

## GET /api/invoices/{id}

### Request
```
GET /api/invoices/{id}
```

### Response Schema
```typescript
interface InvoiceDetail extends InvoiceSummary {
  line_items: LineItem[]
  delivery_notes: DeliveryNote[]
}
```

### LineItem Schema
```typescript
interface LineItem {
  sku: string           // Product SKU
  desc: string          // Product description
  qty: number          // Quantity
  unit_price: number    // Unit price
  total: number         // Line total
  uom: string          // Unit of measure
}
```

### DeliveryNote Schema
```typescript
interface DeliveryNote {
  id: string           // Delivery note ID
  number: string       // Delivery note number
  date: string         // Delivery date
}
```

### Example Response
```json
{
  "id": "inv_001",
  "filename": "invoice_001.pdf",
  "supplier": "ACME Corp",
  "date": "2024-01-15",
  "total_value": 150.50,
  "status": "scanned",
  "confidence": 0.95,
  "venue": "Royal Oak Hotel",
  "issues_count": 2,
  "paired": false,
  "delivery_note_ids": ["dn_001", "dn_002"],
  "source_filename": "multi_invoice_batch.pdf",
  "line_items": [
    {
      "sku": "ITEM001",
      "desc": "Widget A",
      "qty": 2,
      "unit_price": 25.00,
      "total": 50.00,
      "uom": "each"
    }
  ],
  "delivery_notes": [
    {
      "id": "dn_001",
      "number": "DN-001",
      "date": "2024-01-14"
    }
  ]
}
```

## Error Responses

### 400 Bad Request
```json
{
  "detail": "Invalid status parameter. Must be one of: pending, scanned, processed, matched, flagged, error"
}
```

### 404 Not Found
```json
{
  "detail": "Invoice not found"
}
```

### 500 Internal Server Error
```json
{
  "detail": "Internal server error"
}
```

## Contract Stability Notes

1. **Field Names**: All field names are snake_case and will not change
2. **Confidence Scale**: Always 0-1, never 0-100 or other scales
3. **Status Values**: Only the documented enum values are valid
4. **Date Format**: Always YYYY-MM-DD for consistency
5. **Pagination**: limit/offset parameters are always supported
6. **Backward Compatibility**: New optional fields may be added, but existing fields will not change

## Version History

- **v1.0**: Initial contract with normalized fields and pagination support
- **v1.1**: Added source_filename for multi-invoice PDF grouping
- **v1.2**: Added delivery_note_ids array for pairing relationships
