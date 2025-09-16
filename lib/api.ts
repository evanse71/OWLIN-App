// Same-origin API calls only - no external base URLs
async function req(path: string, init?: RequestInit) {
  const r = await fetch(path, { credentials: "same-origin", ...init });
  if (!r.ok) throw new Error(`HTTP ${r.status} ${r.statusText}`);
  const ct = r.headers.get("content-type") || "";
  return ct.includes("application/json") ? r.json() : r.text();
}

export const api = {
  health: () => req("/api/health"),
  status: () => req("/api/status"),
  listInvoices: () => req("/api/invoices"),
  createInvoice: (body: any) =>
    req("/api/manual/invoices", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) }),
  suppliers: () => req("/api/suppliers")
};

// Legacy exports for backward compatibility
export const getUnmatchedNotes = () => req("/api/unmatched-notes");
export const uploadDocument = (file: File) => {
  const formData = new FormData();
  formData.append("file", file);
  return req("/api/upload", { method: "POST", body: formData });
};
export const getJob = (id: string) => req(`/api/jobs/${id}`);
export const pairNote = (invoiceId: string, noteId: string) => 
  req(`/api/pair-note`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ invoiceId, noteId }) });
export const clearAllDocuments = () => req("/api/clear-documents", { method: "POST" });
export const saveDraftDocuments = (data: any) => 
  req("/api/save-drafts", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(data) });
export const submitDocuments = (data: any) => 
  req("/api/submit-documents", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(data) });
export const getUnmatchedDNCount = () => req("/api/unmatched-dn-count");
export const getOpenIssuesCount = () => req("/api/open-issues-count");
export const createInvoice = api.createInvoice;
export const createDeliveryNote = (body: any) =>
  req("/api/manual/delivery-notes", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
export const getDeliveryNote = (id: string) => req(`/api/delivery-notes/${id}`);
export const compareDN = (a: any, b: any) => ({ match: false, score: 0 });
export const postManualInvoice = (body: any) => createInvoice(body);
export const postManualDN = (body: any) => createDeliveryNote(body);

export default api;

// Additional helper functions for the UI integration
export const getJSON = async <T>(path: string): Promise<T> => {
  const r = await fetch(path, { cache: 'no-store' });
  if (!r.ok) throw new Error(`${path} ${r.status}`);
  return r.json();
};

export const postForm = async <T>(path: string, form: FormData): Promise<T> => {
  const r = await fetch(path, { method: 'POST', body: form });
  if (!r.ok) throw new Error(`${path} ${r.status}`);
  return r.json();
};

export const postJSON = async <T>(path: string, body: any): Promise<T> => {
  const r = await fetch(path + (path.includes('?') ? '' : ''), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: body ? JSON.stringify(body) : undefined
  });
  if (!r.ok) throw new Error(`${path} ${r.status}`);
  return r.json();
};

// Enhanced types for the new API structure
export type Invoice = {
  id: string;
  document_id: string | null;
  supplier: string | null;
  invoice_date: string | null;
  total_value: number | null;
  matched_delivery_note_id: string | null;
  status: 'queued' | 'scanned' | 'matched' | 'manual' | null;
  filename?: string;
};

export type LineItem = {
  sku?: string;
  name?: string;
  description?: string;
  qty?: number;
  unit?: number;
  unit_price?: number;
  price?: number;
  total?: number;
};

export type DeliveryNote = {
  id: string;
  document_id?: string | null;
  supplier: string;
  delivery_date: string;
  total_value?: number | null;
  filename?: string;
};

// Canonical API functions
export const getInvoices = () => getJSON('/api/invoices');
export const getInvoiceLines = (id: string) => getJSON(`/api/invoices/${id}/line-items`);
export const getDeliveryNotes = () => getJSON('/api/delivery-notes');
export const getDeliveryNoteLines = (id: string) => getJSON(`/api/delivery-notes/${id}/line-items`);
export const createManualInvoice = (b: any) => postJSON('/api/invoices/manual', b);
export const createManualDN = (b: any) => postJSON('/api/delivery-notes/manual', b);
export const uploadInvoice = (file: File) => { const fd = new FormData(); fd.append('file', file); fd.append('doc_type', 'invoice'); return postForm('/api/uploads', fd); };
export const uploadDN = (file: File) => { const fd = new FormData(); fd.append('file', file); fd.append('doc_type', 'delivery_note'); return postForm('/api/uploads', fd); };
export const pairingSuggestions = (id: string) => getJSON(`/api/pairing/suggestions?invoice_id=${id}`);
export const pairingConfirm = (i: string, d: string) => postJSON(`/api/pairing/confirm?invoice_id=${i}&delivery_note_id=${d}`, {});

// Legacy aliases for backward compatibility
export const getDNs = getDeliveryNotes;