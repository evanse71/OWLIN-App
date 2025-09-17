const BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8081';

// Helper function for API calls
async function apiCall(endpoint: string, options: any = {}) {
  const url = `${BASE_URL}${endpoint}`;
  const response = await fetch(url, {
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
    ...options,
  });

  if (!response.ok) {
    throw new Error(`API call failed: ${response.status} ${response.statusText}`);
  }

  return response.json();
}

// Helper function for form data
async function postForm(endpoint: string, formData: FormData) {
  const url = `${BASE_URL}${endpoint}`;
  const response = await fetch(url, {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    throw new Error(`Form submission failed: ${response.status} ${response.statusText}`);
  }

  return response.json();
}

// Health check
export const checkHealth = () => apiCall('/api/health');
export const checkOCRHealth = () => apiCall('/api/health/ocr');

// Upload operations (new endpoints)
export async function apiUpload(file: File, docType?: "invoice"|"delivery_note") {
  const fd = new FormData();
  fd.append("file", file);
  if (docType) fd.append("doc_type", docType);
  const res = await fetch(`${BASE_URL}/api/uploads`, { method: "POST", body: fd });
  if (!res.ok) throw new Error(`upload failed: ${res.status}`);
  return res.json(); // {job_id, document_id, items, stored_path}
}

export async function apiUploadLegacy(file: File, kind: "invoice"|"delivery_note") {
  const fd = new FormData(); fd.append("file", file);
  const res = await fetch(`${BASE_URL}/api/upload?kind=${encodeURIComponent(kind)}`, { method: "POST", body: fd });
  if (!res.ok) throw new Error(`upload failed: ${res.status}`);
  return res.json();
}

export async function apiJob(jobId: string) {
  const res = await fetch(`${BASE_URL}/api/uploads/jobs/${jobId}`);
  if (!res.ok) throw new Error("job not found");
  return res.json();
}

// Invoice operations
export const getInvoices = () => apiCall('/api/invoices');
export const getInvoice = (id: string) => apiCall(`/api/invoices/${id}`);

// Manual invoice creation
export const createManualInvoice = (invoice: any) => apiCall('/api/invoices/manual', {
  method: 'POST',
  body: JSON.stringify(invoice),
});

// Line items
export const getInvoiceLineItems = (invoiceId: string) => apiCall(`/api/invoices/${invoiceId}/line-items`);
export const addLineItems = (invoiceId: string, items: any[]) => apiCall(`/api/invoices/${invoiceId}/line-items`, {
  method: 'POST',
  body: JSON.stringify(items),
});

export async function apiInvoiceLineItems(id: string) {
  const res = await fetch(`${BASE_URL}/api/invoices/${id}/line-items`);
  if (!res.ok) throw new Error("line items load failed");
  return res.json(); // {items:[...]}
}

export async function apiRescanInvoice(id: string) {
  const res = await fetch(`${BASE_URL}/api/invoices/${id}/rescan`, { method: "POST" });
  if (!res.ok) throw new Error("rescan failed");
  return res.json();
}

export async function apiUpdateLineItem(invoiceId: string, lineId: number | string, body: any) {
  const res = await fetch(`${BASE_URL}/api/invoices/${invoiceId}/line-items/${lineId}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error("update line item failed");
  return res.json();
}

export async function apiDeleteLineItem(invoiceId: string, lineId: number | string) {
  const res = await fetch(`${BASE_URL}/api/invoices/${invoiceId}/line-items/${lineId}`, {
    method: "DELETE",
  });
  if (!res.ok) throw new Error("delete line item failed");
  return res.json();
}

export async function apiListInvoices() {
  const r = await fetch(`${BASE_URL}/api/invoices`);
  if (!r.ok) throw new Error("list invoices failed");
  return r.json(); // {items:[{id,supplier,...,pages, page_count}]}
}

export async function apiGetInvoice(id: string) {
  const r = await fetch(`${BASE_URL}/api/invoices/${id}`);
  if (!r.ok) throw new Error("get invoice failed");
  return r.json();
}

export async function apiExportInvoices(ids: string[]) {
  const r = await fetch(`${BASE_URL}/api/exports/invoices`, {
    method: "POST",
    headers: {"Content-Type":"application/json"},
    body: JSON.stringify({ invoice_ids: ids })
  });
  if (!r.ok) throw new Error("export failed");
  return r.json(); // {ok, zip_path}
}

// Legacy upload operations (for backward compatibility)
export const uploadInvoice = (file: File) => {
  const fd = new FormData();
  fd.append('file', file);
  return postForm('/api/upload?kind=invoice', fd);
};

export const uploadDN = (file: File) => {
  const fd = new FormData();
  fd.append('file', file);
  return postForm('/api/upload?kind=delivery_note', fd);
};

// Delivery note operations
export const getDeliveryNotes = () => apiCall('/api/delivery-notes');
export const getDeliveryNote = (id: string) => apiCall(`/api/delivery-notes/${id}`);

// Pairing suggestions
export const getPairingSuggestions = (invoiceId: string) => apiCall(`/api/pairing/suggestions?invoice_id=${invoiceId}`);

// Supplier operations
export const getSuppliers = () => apiCall('/api/suppliers');
export const getSupplierScorecards = () => apiCall('/api/suppliers/scorecards');