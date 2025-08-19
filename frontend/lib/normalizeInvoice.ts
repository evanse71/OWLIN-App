export type ApiInvoice = {
  id: string | number;
  supplier_name?: string;
  invoice_number?: string;
  invoice_date?: string;
  total_amount?: number;
  total_gross?: number;
  status?: string;
  confidence?: number;
  matched_delivery_note_id?: string | number | null;
};

export type UiInvoice = {
  id: string;                  // canonical string id
  supplierName: string;
  invoiceNumber: string;
  invoiceDate: string;
  totalAmount: number;
  confidence?: number;
  status: "scanning"|"parsed"|"paired"|"unmatched"|"flagged"|"error";
  matchedDeliveryNoteId?: string | null;
};

export function normalizeInvoice(raw: ApiInvoice): UiInvoice {
  const id = String(raw.id ?? "");
  const total = typeof raw.total_amount === "number"
    ? raw.total_amount
    : (typeof raw.total_gross === "number" ? raw.total_gross : 0);
  return {
    id,
    supplierName: raw.supplier_name ?? "",
    invoiceNumber: raw.invoice_number ?? "",
    invoiceDate: raw.invoice_date ?? "",
    totalAmount: total,
    confidence: raw.confidence,
    status: (raw.status as UiInvoice["status"]) ?? "parsed",
    matchedDeliveryNoteId:
      raw.matched_delivery_note_id != null ? String(raw.matched_delivery_note_id) : null,
  };
} 