import type { InvoiceSummary, InvoiceDetail, DeliveryNote, InvoiceDraft, LineItem } from '@/types'

const delay = (ms: number) => new Promise(resolve => setTimeout(resolve, ms))

// Mock data
let mockInvoices: InvoiceSummary[] = [
  {
    id: 'inv_001',
    invoice_number: 'INV-2024-001',
    invoice_date: '2024-01-15',
    supplier_name: 'ABC Supplies Ltd',
    total_amount: 125000,
    status: 'scanned',
    confidence: 85,
    venue: 'Main Venue',
    issues_count: 2,
    paired: 0,
  },
  {
    id: 'inv_002',
    invoice_number: 'INV-2024-002',
    invoice_date: '2024-01-16',
    supplier_name: 'XYZ Catering',
    total_amount: 89000,
    status: 'scanned',
    confidence: 92,
    venue: 'Secondary Venue',
    issues_count: 0,
    paired: 1,
  },
]

let mockDeliveryNotes: DeliveryNote[] = [
  {
    id: 'dn_001',
    note_number: 'DN-2024-001',
    date: '2024-01-15',
    supplier_name: 'ABC Supplies Ltd',
    status: 'unmatched',
  },
  {
    id: 'dn_002',
    note_number: 'DN-2024-002',
    date: '2024-01-16',
    supplier_name: 'XYZ Catering',
    status: 'matched',
  },
]

let mockDrafts: InvoiceDraft[] = []

// Mock job tracking
let mockJobs: Record<string, { status: string; progress: number; result_json?: string }> = {}

export const getInvoices = async (): Promise<InvoiceSummary[]> => {
  await delay(500)
  return [...mockInvoices]
}

export const getInvoice = async (id: string): Promise<InvoiceDetail | null> => {
  await delay(300)
  const invoice = mockInvoices.find(inv => inv.id === id)
  if (!invoice) return null
  
  return {
    ...invoice,
    line_items: [
      {
        description: 'Office Supplies',
        qty: 10,
        unit_price: 1250,
        total: 12500,
        confidence: 85,
      },
      {
        description: 'Cleaning Materials',
        qty: 5,
        unit_price: 2250,
        total: 11250,
        confidence: 78,
      },
    ]
  }
}

export const uploadDocument = async (file: File): Promise<{ job_id: string }> => {
  await delay(1000)
  const jobId = `job_${Date.now()}`
  
  // Simulate job processing
  mockJobs[jobId] = { status: 'queued', progress: 0 }
  
  // Simulate job completion after a delay
  setTimeout(() => {
    mockJobs[jobId] = { 
      status: 'done', 
      progress: 100, 
      result_json: JSON.stringify({ invoice_id: `inv_${Date.now()}` })
    }
  }, 3000)
  
  return { job_id: jobId }
}

export const getJob = async (jobId: string): Promise<{ status: string; progress: number; result_json?: string }> => {
  await delay(500)
  const job = mockJobs[jobId]
  if (!job) {
    return { status: 'error', progress: 0, result_json: undefined }
  }
  
  // Simulate progress updates
  if (job.status === 'queued' && job.progress < 90) {
    job.progress += 10
  }
  
  return job
}

export const getUnmatchedNotes = async (): Promise<DeliveryNote[]> => {
  await delay(300)
  return mockDeliveryNotes.filter(dn => dn.status === 'unmatched')
}

export const getDeliveryNote = async (id: string): Promise<any> => {
  await delay(300)
  const note = mockDeliveryNotes.find(dn => dn.id === id)
  return note ? { delivery_note: note, items: [] } : null
}

export const createInvoice = async (payload: any): Promise<InvoiceDetail> => {
  await delay(500)
  const newInvoice: InvoiceSummary = {
    id: `inv_${Date.now()}`,
    invoice_number: payload.invoice_number || 'INV-NEW',
    invoice_date: payload.invoice_date || new Date().toISOString().split('T')[0],
    supplier_name: payload.supplier_name || 'New Supplier',
    total_amount: payload.total_amount || 0,
    status: 'draft',
    confidence: 0,
    venue: payload.venue || '',
    issues_count: 0,
    paired: 0,
  }
  
  mockInvoices.unshift(newInvoice)
  
  return {
    ...newInvoice,
    line_items: payload.line_items || []
  }
}

export const createDeliveryNote = async (payload: any): Promise<DeliveryNote> => {
  await delay(500)
  const newNote: DeliveryNote = {
    id: `dn_${Date.now()}`,
    note_number: payload.note_number || 'DN-NEW',
    date: payload.date || new Date().toISOString().split('T')[0],
    supplier_name: payload.supplier_name || 'New Supplier',
    status: 'unmatched',
  }
  
  mockDeliveryNotes.unshift(newNote)
  return newNote
}

export const pairNote = async (invoiceId: string, noteId: string): Promise<boolean> => {
  await delay(500)
  
  const invoice = mockInvoices.find(inv => inv.id === invoiceId)
  const note = mockDeliveryNotes.find(dn => dn.id === noteId)
  
  if (invoice && note) {
    invoice.paired = 1
    note.status = 'matched'
    return true
  }
  
  return false
}

export const unpairDN = async (dnId: string): Promise<boolean> => {
  await delay(500)
  
  const note = mockDeliveryNotes.find(dn => dn.id === dnId)
  if (note) {
    note.status = 'unmatched'
    return true
  }
  
  return false
}

export const compareDN = async (dnId: string, invoiceId: string): Promise<{ diffs: any[] }> => {
  await delay(300)
  return { diffs: [] }
}

export const submitDocuments = async (): Promise<{ success: boolean; errors?: string[] }> => {
  await delay(1000)
  return { success: true }
}

export const clearAllDocuments = async (): Promise<void> => {
  await delay(500)
  mockInvoices = []
  mockDeliveryNotes = []
}

export const saveDraftDocuments = async (): Promise<void> => {
  await delay(300)
  // Mock implementation
}

export const getUnmatchedDNCount = async (): Promise<number> => {
  await delay(200)
  return mockDeliveryNotes.filter(dn => dn.status === 'unmatched').length
}

export const getOpenIssuesCount = async (): Promise<number> => {
  await delay(200)
  return mockInvoices.reduce((sum, inv) => sum + (inv.issues_count || 0), 0)
}

export const getLicenseInfo = async (): Promise<{ mode: 'limited' | 'licensed', expires?: string, version: string }> => {
  await delay(200)
  return {
    mode: 'licensed',
    expires: '2025-12-31',
    version: '1.0.0',
  }
}

export const runBackup = async (): Promise<{ ok: boolean }> => {
  await delay(1000)
  return { ok: true }
}

// Mock implementations for missing functions
export const createInvoiceDraft = async (_seed?: Partial<InvoiceDetail>): Promise<InvoiceDraft> => {
  throw new Error("Not implemented in fake API");
}

export const updateInvoiceDraft = async (_id: string, _patch: Partial<InvoiceDetail>): Promise<InvoiceDraft> => {
  throw new Error("Not implemented in fake API");
}

export const addDraftItem = async (_id: string, _item: Omit<LineItem,'total'> & { total?: number; confidence?: number }): Promise<InvoiceDraft> => {
  throw new Error("Not implemented in fake API");
}

export const updateDraftItem = async (_id: string, _index: number, _patch: Partial<LineItem>): Promise<InvoiceDraft> => {
  throw new Error("Not implemented in fake API");
}

export const removeDraftItem = async (_id: string, _index: number): Promise<InvoiceDraft> => {
  throw new Error("Not implemented in fake API");
}

export const attachToDraft = async (_id: string, _file: File): Promise<{ attachment_id: string }> => {
  throw new Error("Not implemented in fake API");
}

export const finalizeInvoice = async (_id: string): Promise<InvoiceDetail> => {
  throw new Error("Not implemented in fake API");
}

export const discardDraft = async (_id: string): Promise<{ ok: true }> => {
  throw new Error("Not implemented in fake API");
}

export const suggestInvoicesForDN = async (_dnId: string): Promise<InvoiceSummary[]> => {
  return [];
}

export const pairDNtoInvoice = async (dnId: string, invoiceId: string): Promise<boolean> => {
  return pairNote(invoiceId, dnId);
}

export const createInvoiceFromDN = async (_dnId: string): Promise<InvoiceDetail> => {
  throw new Error("Not implemented in fake API");
}

export const compareDNtoInvoice = async (dnId: string, invoiceId: string): Promise<any> => {
  return compareDN(dnId, invoiceId);
} 