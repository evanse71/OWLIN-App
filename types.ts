export type InvoiceItem = {
  id?: number;
  description: string;
  qty: number;
  unit_price?: number;  // pence
  total?: number;       // pence (qty * unit_price)
  vat_rate?: number | null;
  confidence?: number | null;
  discrepancy?: 'qty'|'price'|'vat'|'missing'|'extra'|null;
};

export type InvoiceStatus = 'draft'|'processing'|'scanned'|'submitted'|'parsed'|'failed'|'timeout';

export type Invoice = {
  id: string;
  invoice_number?: string | null;
  invoice_date?: string | null; // ISO yyyy-mm-dd
  supplier_name?: string | null;
  venue?: string | null;
  filename?: string | null;     // Original uploaded filename
  status: InvoiceStatus;
  total_amount: number;   // pence (grand total incl. VAT)
  subtotal_p?: number | null;    // pence (subtotal excl. VAT)
  vat_total_p?: number | null;   // pence (VAT amount)
  total_p?: number | null;       // pence (grand total incl. VAT - alternative field)
  confidence: number;     // 0-100
  paired: 0|1;
  issues_count?: number;
  processing_progress?: number | null; // 0..100 while processing
  line_items?: LineItem[];  // Backward compatibility field
  items?: LineItem[];       // Legacy field
  error_message?: string | null; // Error message for failed/timeout invoices
  page_range?: string | null; // Page range for multi-page documents
  validation_flags?: string[]; // Validation flags for OCR quality
};

// Legacy types for backward compatibility
export type InvoiceSummary = Invoice;

export type LineItem = InvoiceItem;

export type InvoiceDetail = Invoice & {
  line_items: LineItem[]
}

export type DeliveryNote = {
  id: string
  note_number: string
  date: string
  supplier_name: string
  status: 'unmatched' | 'matched'
}

export type InvoiceDraft = {
  id: string
  invoice_number: string
  invoice_date: string
  supplier_name: string
  total_amount: number
  venue: string
  notes?: string
  line_items: (LineItem & { confidence?: number })[]
  attachments: { id: string; name: string; url: string }[]
  created_at: string
  updated_at: string
} 