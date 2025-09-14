export const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "";

async function req(path: string, init?: RequestInit) {
  const url = (API_BASE ? API_BASE : "") + path; // supports same-origin or absolute
  const r = await fetch(url, { credentials: "same-origin", ...init });
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

// Export all the functions that are imported elsewhere
export const getInvoices = api.listInvoices;
export const getUnmatchedNotes = () => req("/api/unmatched-notes");
export const uploadDocument = (file: File) => {
  const formData = new FormData();
  formData.append("file", file);
  return req("/api/upload", { method: "POST", body: formData });
};
export const getJob = (id: string) => req(`/api/jobs/${id}`);
export const getInvoice = (id: string) => req(`/api/invoices/${id}`);
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

export default api;