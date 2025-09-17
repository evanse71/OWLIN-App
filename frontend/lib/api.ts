const BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || "http://127.0.0.1:8081";

export async function fetchJSON<T>(path: string, init?: RequestInit): Promise<T> {
  const r = await fetch(`${BASE_URL}${path}`, init);
  const text = await r.text();
  if (!r.ok) {
    const msg = text.replace(/<[^>]*>/g, "").slice(0, 200).trim() || r.statusText;
    throw new Error(`${r.status} ${msg}`);
  }
  return text ? JSON.parse(text) : ({} as T);
}

// Health check
export const checkHealth = () => fetchJSON('/api/health');
export const checkOCRHealth = () => fetchJSON('/api/health/ocr');


export async function apiUploadLegacy(file: File, kind: "invoice"|"delivery_note") {
  const fd = new FormData(); fd.append("file", file);
  return fetchJSON(`/api/upload?kind=${encodeURIComponent(kind)}`, { method: "POST", body: fd });
}

export async function apiJob(jobId: string) {
  return fetchJSON(`/api/uploads/jobs/${jobId}`);
}

// Absolute helpers (use these everywhere)
export const apiListInvoices = () => fetchJSON<{items:any[]}>("/api/invoices");
export const apiGetInvoice = (id:string) => fetchJSON(`/api/invoices/${id}`);
export const apiInvoiceLineItems = (id:string) => fetchJSON(`/api/invoices/${id}/line-items`);
export const apiRescanInvoice = (id:string) => fetchJSON(`/api/invoices/${id}/rescan`, { method:"POST" });
export const apiExportInvoices = (ids:string[]) =>
  fetchJSON("/api/exports/invoices", { method:"POST", headers:{ "Content-Type":"application/json" }, body: JSON.stringify({ invoice_ids: ids }) });

export async function apiUpload(file: File, docType?: "invoice"|"delivery_note") {
  const fd = new FormData(); fd.append("file", file); if (docType) fd.append("doc_type", docType);
  return fetchJSON<{items:any[]}>("/api/uploads", { method:"POST", body: fd });
}

export const apiUpdateLineItem = (invId:string, lineId:string, body:any) =>
  fetchJSON(`/api/invoices/${invId}/line-items/${lineId}`, { method:"PUT", headers:{ "Content-Type":"application/json" }, body: JSON.stringify(body) });

export const apiDeleteLineItem = (invId:string, lineId:string) =>
  fetchJSON(`/api/invoices/${invId}/line-items/${lineId}`, { method:"DELETE" });

// Legacy functions for backward compatibility
export const getInvoices = () => fetchJSON('/api/invoices');
export const getInvoice = (id: string) => fetchJSON(`/api/invoices/${id}`);
export const createManualInvoice = (invoice: any) => fetchJSON('/api/invoices/manual', {
  method: 'POST',
  body: JSON.stringify(invoice),
});
export const getInvoiceLineItems = (invoiceId: string) => fetchJSON(`/api/invoices/${invoiceId}/line-items`);
export const addLineItems = (invoiceId: string, items: any[]) => fetchJSON(`/api/invoices/${invoiceId}/line-items`, {
  method: 'POST',
  body: JSON.stringify(items),
});

export const getPageThumbnailUrl = (invoiceId: string, pageNo: number) =>
  `${BASE_URL}/api/invoices/${invoiceId}/pages/${pageNo}/thumb`;

// Legacy upload operations (for backward compatibility)
export const uploadInvoice = (file: File) => {
  const fd = new FormData();
  fd.append('file', file);
  return fetchJSON('/api/upload?kind=invoice', { method: 'POST', body: fd });
};

export const uploadDN = (file: File) => {
  const fd = new FormData();
  fd.append('file', file);
  return fetchJSON('/api/upload?kind=delivery_note', { method: 'POST', body: fd });
};

// Delivery note operations
export const getDeliveryNotes = () => fetchJSON('/api/delivery-notes');
export const getDeliveryNote = (id: string) => fetchJSON(`/api/delivery-notes/${id}`);

// Enhanced delivery notes API with filtering and pairing
export async function fetchDeliveryNotes(params: {
  q?: string;
  supplier?: string;
  from?: string; // ISO date (YYYY-MM-DD)
  to?: string;   // ISO date
  matched?: boolean;
  only_with_issues?: boolean;
  site_id?: string | null;
  limit?: number;
  offset?: number;
}) {
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

  const res = await fetchJSON(`/api/delivery-notes?${qs.toString()}`);
  return res; // { items: DeliveryNote[], total: number }
}

export async function pairDeliveryNoteToInvoice(body: { delivery_note_id: string; invoice_id: string }) {
  const res = await fetchJSON(`/api/delivery-notes/pair`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  return res; // { ok: true }
}

export async function unpairDeliveryNote(body: { delivery_note_id: string }) {
  const res = await fetchJSON(`/api/delivery-notes/unpair`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  return res; // { ok: true }
}

export async function fetchDeliveryNoteSuggestions(params: { delivery_note_id: string }) {
  const qs = new URLSearchParams({ id: params.delivery_note_id });
  const res = await fetchJSON(`/api/delivery-notes/suggestions?${qs.toString()}`);
  return res; // { suggestions: Array<{invoice_id: string, score: number, reason?: string}> }
}

// Pairing suggestions
export const getPairingSuggestions = (invoiceId: string) => fetchJSON(`/api/pairing/suggestions?invoice_id=${invoiceId}`);

// Supplier operations
export const getSuppliers = () => fetchJSON('/api/suppliers');
export const getSupplierScorecards = () => fetchJSON('/api/suppliers/scorecards');
