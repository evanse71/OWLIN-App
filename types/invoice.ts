// Frontend canonical DTOs used across components.
// If backend snake_case differs, map in lib/api.ts.

export interface InvoiceDTO {
  id: string;
  supplier?: string;
  invoice_date?: string;   // ISO
  status: string;          // 'ocr' | 'parsed' | 'scanned' | 'manual' | ...
  currency?: string;
  total_value?: number;
  pages?: number[];        // optional if not returned
  page_count?: number;
}

export interface LineItemDTO {
  id: string;
  description?: string;
  quantity: number;
  unit_price: number;
  total: number;
  uom?: string;
  vat_rate: number;
  source?: string;         // 'ocr' | 'manual' | ...
}

export interface DeliveryNoteDTO {
  id: string;
  supplier?: string;
  note_date?: string;
  total_amount?: number;
  matched_invoice_id?: string | null;
  status: string;          // 'unmatched' | 'matched' | ...
}

export interface PairingSuggestionDTO {
  delivery_note_id: string;
  invoice_id?: string;
  score: number;
  reason?: string;
}

// Request types for API calls
export interface UpdateLineItemRequest {
  description?: string;
  quantity?: number;
  unit_price?: number;
  uom?: string;
  vat_rate?: number;
}

// Additional types used by components
export interface InvoiceBundle {
  id: string;
  meta: Record<string, unknown>;
  lines: Array<{
    desc: string;
    qty: number;
    unit_price: number;
    line_total: number;
    flags: string[];
  }>;
  dn_candidates: Array<{
    id: string;
    supplier_name?: string;
    date?: string;
    score: number;
  }>;
  suggestions: Array<{
    invoice_line_idx: number;
    dn_line_idx: number;
    score: number;
  }>;
  doc_flags: string[];
}