// API switch between fake and real implementations
const BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8001";
const USE_FAKE = (process.env.NEXT_PUBLIC_USE_FAKE_BACKEND ?? "false") === "true";

import * as apiFake from './api.fake'
import * as apiReal from './api.real'

export const api = USE_FAKE ? apiFake : apiReal;

// Re-export all functions
export const {
  getInvoices,
  getInvoice,
  getUnmatchedNotes,
  getDeliveryNote,
  pairNote,
  uploadDocument,
  getJob,
  createInvoice,
  createDeliveryNote,
  compareDN,
  unpairDN,
  createInvoiceDraft,
  updateInvoiceDraft,
  addDraftItem,
  updateDraftItem,
  removeDraftItem,
  attachToDraft,
  finalizeInvoice,
  discardDraft,
  suggestInvoicesForDN,
  pairDNtoInvoice,
  createInvoiceFromDN,
  compareDNtoInvoice,
  clearAllDocuments,
  saveDraftDocuments,
  submitDocuments,
  getUnmatchedDNCount,
  getOpenIssuesCount,
  getLicenseInfo,
  runBackup,
} = api 