/**
 * Canonical Invoice Types
 * 
 * These types represent the normalized invoice structure used throughout the frontend.
 * All API responses should be mapped to these types via normalizeInvoice().
 * 
 * This is the SINGLE source of truth for invoice data shape in the UI.
 * All components should use these types, not ad-hoc interfaces or raw backend JSON.
 */

interface InvoiceLineItem {
  id: number
  docId: string | number
  invoiceId: number
  lineNumber: number
  description: string
  qty: number
  unitPrice: number
  total: number
  uom?: string | null
  sku?: string | null
  confidence?: number | null
  bbox?: number[]  // [x, y, w, h] in original image pixels
}

interface Invoice {
  id: number | string  // Can be UUID string (doc_id) or numeric ID
  docId: string | number
  supplier: string
  invoiceDate: string  // ISO date
  invoiceNumber?: string  // Invoice number (e.g., "INV 1", extracted from filename for manual invoices)
  totalValue: number
  currency?: string
  confidence?: number | null
  status: string
  venue?: string | null
  issuesCount?: number
  paired?: boolean
  pairingStatus?: string | null
  deliveryNoteId?: number | null
  lineItems: InvoiceLineItem[]
}

export type { Invoice, InvoiceLineItem }

