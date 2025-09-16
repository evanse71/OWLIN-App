import type { InvoiceSummary, InvoiceDetail, DeliveryNote, InvoiceDraft, LineItem } from '@/types'

// Same-origin API calls only

async function j<T>(r: Response): Promise<T> {
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

export async function getInvoices(): Promise<InvoiceSummary[]> {
  return j(await fetch(`/api/invoices`));
}

export async function getInvoice(id: string): Promise<InvoiceDetail | null> {
  const response = await fetch(`/api/invoices/${id}`);
  if (!response.ok) return null;
  const data = await j<{invoice: any, line_items: any[]}>(response);
  if (!data.invoice) return null;
  
  return {
    ...data.invoice,
    line_items: data.line_items.map((item: any) => ({
      description: item.description,
      qty: item.qty,
      unit_price: item.unit_price,
      total: item.total,
      confidence: item.confidence,
    }))
  };
}

export async function createInvoice(payload: any): Promise<InvoiceDetail> {
  return j(await fetch(`/api/invoices`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload)
  }));
}

export async function uploadDocument(file: File): Promise<{ job_id: string }> {
  const form = new FormData();
  form.append("file", file);
  return j<{job_id:string}>(await fetch(`/api/upload`, {
    method: "POST",
    body: form
  }));
}

export async function getJob(job_id: string): Promise<any> {
  return j(await fetch(`/api/jobs/${job_id}`));
}

export async function reprocessInvoice(id: string): Promise<{ job_id: string }> {
  const res = await fetch(`/api/invoices/${id}/reprocess`, { method: "POST" });
  if (!res.ok) throw new Error("Reprocess failed");
  return res.json(); // { job_id }
}

export async function getUnmatchedNotes(): Promise<DeliveryNote[]> {
  return j(await fetch(`/api/delivery-notes/unmatched`));
}

export async function getDeliveryNote(id: string): Promise<any> {
  return j(await fetch(`/api/delivery-notes/${id}`));
}

export async function createDeliveryNote(payload: any): Promise<DeliveryNote> {
  return j(await fetch(`/api/delivery-notes`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload)
  }));
}

export async function pairNote(invoice_id: string, dn_id: string): Promise<boolean> {
  const form = new FormData();
  form.append("invoice_id", invoice_id);
  form.append("dn_id", dn_id);
  const response = await fetch(`/api/pair`, {
    method: "POST",
    body: form
  });
  return response.ok;
}

export async function unpairDN(dn_id: string): Promise<boolean> {
  const form = new FormData();
  form.append("dn_id", dn_id);
  const response = await fetch(`/api/unpair`, {
    method: "POST",
    body: form
  });
  return response.ok;
}

export async function compareDN(dn_id: string, invoice_id: string): Promise<{diffs:any[]}> {
  return j<{diffs:any[]}>(await fetch(`/api/compare?dn_id=${dn_id}&invoice_id=${invoice_id}`));
}

export async function submitDocuments(): Promise<{ success: boolean; errors?: string[] }> {
  await j(await fetch(`/api/submit`, {
    method: "POST"
  }));
  return { success: true };
}

// Mock implementations for missing functions
export async function createInvoiceDraft(_seed?: Partial<InvoiceDetail>): Promise<InvoiceDraft> {
  throw new Error("Not implemented in real API");
}

export async function updateInvoiceDraft(_id: string, _patch: Partial<InvoiceDetail>): Promise<InvoiceDraft> {
  throw new Error("Not implemented in real API");
}

export async function addDraftItem(_id: string, _item: Omit<LineItem,'total'> & { total?: number; confidence?: number }): Promise<InvoiceDraft> {
  throw new Error("Not implemented in real API");
}

export async function updateDraftItem(_id: string, _index: number, _patch: Partial<LineItem>): Promise<InvoiceDraft> {
  throw new Error("Not implemented in real API");
}

export async function removeDraftItem(_id: string, _index: number): Promise<InvoiceDraft> {
  throw new Error("Not implemented in real API");
}

export async function attachToDraft(_id: string, _file: File): Promise<{ attachment_id: string }> {
  throw new Error("Not implemented in real API");
}

export async function finalizeInvoice(_id: string): Promise<InvoiceDetail> {
  throw new Error("Not implemented in real API");
}

export async function discardDraft(_id: string): Promise<{ ok: true }> {
  throw new Error("Not implemented in real API");
}

export async function suggestInvoicesForDN(_dnId: string): Promise<InvoiceSummary[]> {
  return [];
}

export async function pairDNtoInvoice(dnId: string, invoiceId: string): Promise<boolean> {
  return pairNote(invoiceId, dnId);
}

export async function createInvoiceFromDN(_dnId: string): Promise<InvoiceDetail> {
  throw new Error("Not implemented in real API");
}

export async function compareDNtoInvoice(dnId: string, invoiceId: string): Promise<any> {
  return compareDN(dnId, invoiceId);
}

export async function clearAllDocuments(): Promise<void> {
  // Mock implementation
}

export async function saveDraftDocuments(): Promise<void> {
  // Mock implementation
}

export async function getUnmatchedDNCount(): Promise<number> {
  const notes = await getUnmatchedNotes();
  return notes.length;
}

export async function getOpenIssuesCount(): Promise<number> {
  const invoices = await getInvoices();
  return invoices.reduce((sum, inv) => sum + (inv.issues_count || 0), 0);
}

export async function getLicenseInfo(): Promise<{ mode: 'limited' | 'licensed', expires?: string, version: string }> {
  return {
    mode: 'licensed',
    expires: '2025-12-31',
    version: '1.0.0',
  };
}

export async function runBackup(): Promise<{ ok: boolean }> {
  return { ok: true };
} 