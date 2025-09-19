// frontend/lib/api.ts
import type {
  InvoiceDTO,
  LineItemDTO,
  DeliveryNoteDTO,
  PairingSuggestionDTO,
} from "@/types/invoice";

const BASE =
  process.env.NEXT_PUBLIC_API_BASE ||
  process.env.NEXT_PUBLIC_API_BASE_URL ||
  "";

async function fetchJSON<T>(path: string, init?: RequestInit): Promise<T> {
  const r = await fetch(`${BASE}${path}`, init);
  const txt = await r.text();
  if (!r.ok) {
    const msg = (txt || r.statusText).replace(/<[^>]*>/g, "").slice(0, 300);
    throw new Error(`${r.status} ${msg}`.trim());
  }
  return (txt ? JSON.parse(txt) : {}) as T;
}

type ApiList<T> = { items: T[]; total?: number };

// Health
export const checkHealth = () => fetchJSON<{ status: string; service: string }>("/api/health");
export const checkOCRHealth = () => fetchJSON<any>("/api/health/ocr");

// Invoices
export const apiListInvoices = () => fetchJSON<ApiList<InvoiceDTO>>("/api/invoices");
export const apiGetInvoice = (id: string) => fetchJSON<InvoiceDTO>(`/api/invoices/${id}`);
export const apiInvoiceLineItems = (id: string) =>
  fetchJSON<ApiList<LineItemDTO>>(`/api/invoices/${id}/line-items`);
export const apiRescanInvoice = (id: string) =>
  fetchJSON<{ ok: true; status: string }>(`/api/invoices/${id}/rescan`, { method: "POST" });

export type CreateInvoiceRequest = {
  supplier: string;
  invoice_date?: string;
  reference?: string;
  currency?: string;
  line_items?: Array<{
    description?: string;
    quantity: number;
    unit_price: number;
    uom?: string;
    vat_rate: number;
  }>;
};

export const createManualInvoice = (body: CreateInvoiceRequest) =>
  fetchJSON<InvoiceDTO>("/api/invoices/manual", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

// alias kept for legacy imports
export const postManualInvoice = createManualInvoice;

export type UpdateLineItemRequest = {
  description?: string;
  quantity?: number;
  unit_price?: number;
  uom?: string;
  vat_rate?: number;
};

export const apiAddLineItems = (invoiceId: string, items: CreateInvoiceRequest["line_items"] = []) =>
  fetchJSON<ApiList<LineItemDTO>>(`/api/invoices/${invoiceId}/line-items`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(items),
  });

export const apiUpdateLineItem = (
  invoiceId: string,
  lineId: string,
  body: UpdateLineItemRequest
) =>
  fetchJSON<LineItemDTO>(`/api/invoices/${invoiceId}/line-items/${lineId}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

export const apiDeleteLineItem = (invoiceId: string, lineId: string) =>
  fetchJSON<{ ok: true }>(`/api/invoices/${invoiceId}/line-items/${lineId}`, {
    method: "DELETE",
  });

export const getPageThumbnailUrl = (invoiceId: string, pageNo: number) =>
  `${BASE}/api/invoices/${invoiceId}/pages/${pageNo}/thumb`;

// Uploads (unified + legacy)
export const apiUpload = (file: File, docType?: "invoice" | "delivery_note") => {
  const fd = new FormData();
  fd.append("file", file);
  if (docType) fd.append("doc_type", docType);
  return fetchJSON<{ document_id: string; items: any[]; stored_path: string }>(
    "/api/uploads",
    { method: "POST", body: fd }
  );
};

export const uploadInvoice = (file: File) => {
  const fd = new FormData();
  fd.append("file", file);
  return fetchJSON(`/api/upload?kind=invoice`, { method: "POST", body: fd });
};
export const uploadDN = (file: File) => {
  const fd = new FormData();
  fd.append("file", file);
  return fetchJSON(`/api/upload?kind=delivery_note`, { method: "POST", body: fd });
};

// Delivery Notes + pairing
export const getDeliveryNotes = () =>
  fetchJSON<ApiList<DeliveryNoteDTO>>("/api/delivery-notes");
export const getDeliveryNote = (id: string) =>
  fetchJSON<DeliveryNoteDTO>(`/api/delivery-notes/${id}`);

export const fetchDeliveryNotes = (params: {
  q?: string;
  supplier?: string;
  from?: string;
  to?: string;
  matched?: boolean;
  only_with_issues?: boolean;
  site_id?: string | null;
  limit?: number;
  offset?: number;
}) => {
  const qs = new URLSearchParams();
  if (params.q) qs.set("q", params.q);
  if (params.supplier) qs.set("supplier", params.supplier);
  if (params.from) qs.set("from", params.from);
  if (params.to) qs.set("to", params.to);
  if (typeof params.matched === "boolean") qs.set("matched", String(params.matched));
  if (params.only_with_issues) qs.set("only_with_issues", "true");
  if (params.site_id) qs.set("site_id", params.site_id);
  if (params.limit) qs.set("limit", String(params.limit));
  if (params.offset) qs.set("offset", String(params.offset));
  return fetchJSON<ApiList<DeliveryNoteDTO>>(`/api/delivery-notes?${qs.toString()}`);
};

export const pairDeliveryNoteToInvoice = (body: { delivery_note_id: string; invoice_id: string }) =>
  fetchJSON<{ ok: true }>(`/api/delivery-notes/pair`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

export const unpairDeliveryNote = (body: { delivery_note_id: string }) =>
  fetchJSON<{ ok: true }>(`/api/delivery-notes/unpair`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

export const getPairingSuggestions = (invoiceId: string) =>
  fetchJSON<{ suggestions: PairingSuggestionDTO[] }>(
    `/api/pairing/suggestions?invoice_id=${encodeURIComponent(invoiceId)}`
  );

// Suppliers / Exports (compat)
export const getSuppliers = () => fetchJSON<ApiList<{ id: string; name: string }>>("/api/suppliers");
export const getSupplierScorecards = () => fetchJSON<ApiList<any>>("/api/suppliers/scorecards");
export const apiExportInvoices = (invoiceIds: string[]) =>
  fetchJSON(`/api/exports/invoices`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ invoice_ids: invoiceIds }),
  });

// Delivery note manual (compat)
export type CreateDNRequest = {
  supplier?: string;
  note_date?: string;
  line_items?: Array<{
    description?: string;
    quantity: number;
    unit_price: number;
    uom?: string;
    vat_rate: number;
  }>;
};
export const createManualDN = (body: CreateDNRequest) =>
  fetchJSON<DeliveryNoteDTO>("/api/delivery-notes/manual", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

// Legacy aliases for backward compatibility
export const getInvoices = apiListInvoices;
export const getInvoice = apiGetInvoice;
export const getInvoiceLineItems = apiInvoiceLineItems;
export const addLineItems = apiAddLineItems;
export const getJSON = fetchJSON;
export const apiCall = fetchJSON;

// Additional missing functions that components expect
export const postManualDN = createManualDN;
export const compareDN = () => Promise.resolve({});
export const getUnpaired = () => fetchJSON<ApiList<DeliveryNoteDTO>>("/api/delivery-notes?matched=false");
export const postPair = pairDeliveryNoteToInvoice;
export const getUnmatchedNotes = getUnpaired;
export const uploadDocument = apiUpload;
export const getJob = () => Promise.resolve({});
export const pairNote = pairDeliveryNoteToInvoice;
export const clearAllDocuments = () => Promise.resolve({});
export const saveDraftDocuments = () => Promise.resolve({});
export const submitDocuments = () => Promise.resolve({});
export const getUnmatchedDNCount = () => fetchJSON<{ count: number }>("/api/delivery-notes/count?matched=false");
export const getOpenIssuesCount = () => fetchJSON<{ count: number }>("/api/issues/count");
export const createInvoice = createManualInvoice;
export const createDeliveryNote = createManualDN;