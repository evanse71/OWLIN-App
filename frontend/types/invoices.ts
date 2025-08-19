export type InvoiceStatus = "scanning" | "parsed" | "paired" | "flagged" | "error";

export interface InvoiceListItem {
  id: number;
  supplier_name: string;
  invoice_number: string;
  invoice_date: string; // ISO
  total_gross: number;
  status: InvoiceStatus;
  confidence: number;
  page_range?: string;
  parent_pdf_filename?: string;
  issues_count?: number;
  matched_delivery_note_id?: number | null;
  upload_id?: string;
}

export interface InvoiceLine {
  id: number;
  sku?: string | null;
  desc: string;
  qty: number;
  uom: string;
  unit_price: number;
  net: number;
  tax?: number;
}

export interface DeliveryNoteLine extends InvoiceLine {}

export interface InvoiceDetail extends InvoiceListItem {
  lines: InvoiceLine[];
  matched_delivery_note?: {
    id: number;
    number: string;
    date: string;
    lines: DeliveryNoteLine[];
  } | null;
  issues?: Array<{
    type: "qty_mismatch" | "price_mismatch" | "missing_on_dn" | "missing_on_inv";
    line_id?: number;
    expected?: number | string;
    actual?: number | string;
  }>;
}

export interface FilterState {
  venues: string[];
  dateFrom?: string;
  dateTo?: string;
  supplierQuery: string;
  statusSet: Set<InvoiceStatus>;
  sort: "newest" | "oldest" | "value_desc" | "flagged";
}

export interface UploadProgress {
  upload_id: string;
  percent: number;
  discovered_invoices?: number;
  state: "uploading" | "ocr_split" | "parsing" | "complete" | "error";
} 