import { API_BASE_URL } from './config'
import type { Invoice, InvoiceLineItem } from '../types/invoice'

export interface HealthResponse {
  status: string
}

/**
 * Check backend health status
 */
export async function checkHealth(): Promise<HealthResponse> {
  const response = await fetch(`${API_BASE_URL}/api/health`)
  if (!response.ok) {
    throw new Error(`Health check failed: ${response.status} ${response.statusText}`)
  }
  return response.json()
}

/**
 * Retry OCR processing for a failed document
 */
export async function retryOCR(docId: string): Promise<{ status: string; doc_id: string; message: string }> {
  const response = await fetch(`${API_BASE_URL}/api/ocr/retry/${docId}`, {
    method: 'POST',
  })
  if (!response.ok) {
    const error = await response.json().catch(() => ({ message: 'Failed to retry OCR' }))
    throw new Error(error.detail || error.message || `Failed to retry OCR: ${response.status}`)
  }
  return response.json()
}

/**
 * Fetch recent documents (all documents, not just invoices)
 */
export async function fetchRecentDocuments(
  limit: number = 50,
  offset: number = 0,
  status?: string
): Promise<{
  documents: Array<{
    doc_id: string
    filename: string
    uploaded_at: string
    status: string
    doc_type: string | null
    doc_type_confidence: number
    confidence: number
    ocr_error: string | null
    error_code: string | null
    ocr_attempts?: Array<any>
    has_invoice_row: boolean
    invoice: {
      supplier: string | null
      total: number
      date: string | null
      invoice_number: string | null
      confidence: number
    } | null
  }>
  count: number
  total: number
  limit: number
  offset: number
}> {
  const params = new URLSearchParams()
  params.append('limit', String(limit))
  params.append('offset', String(offset))
  if (status) {
    params.append('status', status)
  }
  
  const response = await fetch(`${API_BASE_URL}/api/documents/recent?${params.toString()}`)
  if (!response.ok) {
    throw new Error(`Failed to fetch recent documents: ${response.status} ${response.statusText}`)
  }
  return response.json()
}

/**
 * Recursively converts snake_case keys to camelCase for nested objects/arrays
 * Low-level utility function for general object normalization
 */
export function normalizeSnakeToCamel(obj: any): any {
  if (obj === null || obj === undefined) {
    return obj
  }

  if (Array.isArray(obj)) {
    return obj.map(normalizeSnakeToCamel)
  }

  if (typeof obj !== 'object') {
    return obj
  }

  const normalized: any = {}
  for (const [key, value] of Object.entries(obj)) {
    // Convert snake_case to camelCase
    const camelKey = key.replace(/_([a-z])/g, (_, letter) => letter.toUpperCase())
    normalized[camelKey] = normalizeSnakeToCamel(value)
    // Keep original key too for backward compatibility
    if (camelKey !== key) {
      normalized[key] = value
    }
  }
  return normalized
}

/**
 * normalizeInvoice
 *
 * SINGLE source of truth for mapping backend invoice JSON (snake_case)
 * into the frontend Invoice type (camelCase).
 *
 * Any data coming from:
 *  - GET /api/invoices
 *  - GET /api/manual/invoices
 *  - GET /api/invoices/{id}
 *  - GET /api/upload/status (invoice field)
 * MUST pass through this function before being used in components.
 *
 * @param raw - Raw invoice object from backend API (snake_case fields)
 * @returns Normalized Invoice object (camelCase fields)
 */
export function normalizeInvoice(raw: any): Invoice {
  if (!raw || typeof raw !== 'object') {
    throw new Error('Invalid invoice data: expected object')
  }

  // Normalize line items
  const lineItems: InvoiceLineItem[] = []
  const lineItemsRaw = raw.line_items || raw.items || []
  if (Array.isArray(lineItemsRaw)) {
    for (const item of lineItemsRaw) {
      if (item && typeof item === 'object') {
        lineItems.push({
          id: item.id || 0,
          docId: item.doc_id || raw.doc_id || '',
          invoiceId: item.invoice_id || raw.id || 0,
          lineNumber: item.line_number || 0,
          description: item.description || item.desc || '',
          qty: item.qty || item.quantity || 0,
          unitPrice: item.unit_price || item.price || 0,
          total: item.total || item.line_total || 0,
          uom: item.uom || item.unit || null,
          sku: item.sku || null,
          confidence: item.confidence || null,
          bbox: item.bbox || undefined,  // Preserve bbox if present
        })
      }
    }
  }

  // Extract invoice number from various possible fields
  // For manual invoices, it's in invoice_number; for scanned, it might be in filename
  let invoiceNumber: string | undefined = undefined
  if (raw.invoice_number) {
    invoiceNumber = String(raw.invoice_number)
  } else if (raw.invoice_no) {
    invoiceNumber = String(raw.invoice_no)
  } else if (raw.filename) {
    // Extract from filename if it follows "Manual Invoice {number}" pattern
    const filename = String(raw.filename)
    if (filename.startsWith("Manual Invoice ")) {
      invoiceNumber = filename.replace("Manual Invoice ", "")
    }
  }

  // Map backend fields to frontend Invoice type
  return {
    id: raw.id || 0,
    docId: raw.doc_id || '',
    supplier: raw.supplier || raw.supplier_name || 'Unknown Supplier',
    invoiceDate: raw.invoice_date || raw.date || '',
    invoiceNumber: invoiceNumber,  // Include invoice number if available
    totalValue: raw.total_value || raw.value || raw.total || 0,
    currency: raw.currency || 'GBP',
    confidence: raw.confidence || raw.ocr_confidence || null,
    status: raw.status || 'scanned',
    venue: raw.venue || null,
    issuesCount: raw.issues_count || 0,
    paired: raw.paired || false,
    pairingStatus: raw.pairing_status || null,
    deliveryNoteId: raw.delivery_note_id || null,
    lineItems,
  }
}

/**
 * @deprecated Use normalizeInvoice() instead. This function is kept for backward compatibility.
 * Normalizes a single invoice record with field aliases and preferred naming
 */
export function normalizeInvoiceRecord(inv: any): any {
  if (!inv || typeof inv !== 'object') {
    return inv
  }

  const normalized = { ...inv }

  // Map total_value → total (keep both if present)
  if (normalized.total_value !== undefined && normalized.total_value !== null) {
    normalized.total = normalized.total_value
  }
  // Also handle if total is missing but value exists
  if ((normalized.total === undefined || normalized.total === null) && normalized.value !== undefined && normalized.value !== null) {
    normalized.total = normalized.value
  }

  // Map invoice_number → invoiceNo
  if (normalized.invoice_number !== undefined && normalized.invoice_number !== null) {
    normalized.invoiceNo = normalized.invoice_number
  }

  // Map supplier_name → supplier (keep both if present)
  if (normalized.supplier_name !== undefined && normalized.supplier_name !== null) {
    if (normalized.supplier === undefined || normalized.supplier === null) {
      normalized.supplier = normalized.supplier_name
    }
  }

  // Ensure lineItems array (from line_items or items)
  // Check both camelCase and snake_case variants (normalizeSnakeToCamel will add camelCase later)
  const lineItemsSource = normalized.lineItems || normalized.line_items || normalized.items || []
  if (lineItemsSource && Array.isArray(lineItemsSource)) {
    normalized.lineItems = lineItemsSource.map((item: any) => {
      if (!item || typeof item !== 'object') {
        return item
      }

      const normalizedItem = { ...item }

      // quantity → qty (prefer qty if both exist)
      if (normalizedItem.quantity !== undefined && normalizedItem.quantity !== null) {
        if (normalizedItem.qty === undefined || normalizedItem.qty === null) {
          normalizedItem.qty = normalizedItem.quantity
        }
      }

      // price → unitPrice (prefer unitPrice if both exist)
      if (normalizedItem.price !== undefined && normalizedItem.price !== null) {
        if (normalizedItem.unitPrice === undefined || normalizedItem.unitPrice === null) {
          normalizedItem.unitPrice = normalizedItem.price
        }
      }

      // total → lineTotal (prefer lineTotal if both exist)
      if (normalizedItem.total !== undefined && normalizedItem.total !== null) {
        if (normalizedItem.lineTotal === undefined || normalizedItem.lineTotal === null) {
          normalizedItem.lineTotal = normalizedItem.total
        }
      }

      // Also handle snake_case variants
      if (normalizedItem.line_total !== undefined && normalizedItem.line_total !== null) {
        if (normalizedItem.lineTotal === undefined || normalizedItem.lineTotal === null) {
          normalizedItem.lineTotal = normalizedItem.line_total
        }
      }

      if (normalizedItem.unit_price !== undefined && normalizedItem.unit_price !== null) {
        if (normalizedItem.unitPrice === undefined || normalizedItem.unitPrice === null) {
          normalizedItem.unitPrice = normalizedItem.unit_price
        }
      }

      return normalizedItem
    })
  } else if (!normalized.lineItems) {
    normalized.lineItems = []
  }

  // Apply snake_case normalization to the entire object
  return normalizeSnakeToCamel(normalized)
}

/**
 * @deprecated Use normalizeInvoice() for individual invoices. This function is kept for backward compatibility.
 * Normalizes invoices payload - handles invoices array or invoice single object
 */
export function normalizeInvoicesPayload(payload: any): any {
  if (!payload || typeof payload !== 'object') {
    return payload
  }

  const normalized: any = {}

  // Handle invoices array
  if (Array.isArray(payload.invoices)) {
    normalized.invoices = payload.invoices.map(normalizeInvoiceRecord)
  }

  // Handle single invoice
  if (payload.invoice && typeof payload.invoice === 'object') {
    normalized.invoice = normalizeInvoiceRecord(payload.invoice)
  }

  // Copy other metadata fields and normalize them
  for (const [key, value] of Object.entries(payload)) {
    if (key !== 'invoices' && key !== 'invoice') {
      normalized[key] = normalizeSnakeToCamel(value)
    }
  }

  return normalized
}

/**
 * Create a manual invoice
 */
export async function createManualInvoice(data: {
  supplier: string
  invoiceNumber: string
  date: string
  venue: string
  lineItems: Array<{
    description: string
    qty: number
    unit: string
    price: number
    total: number
  }>
  subtotal: number
  vat: number
  total: number
}) {
  // Transform frontend format to backend format
  const backendData = {
    supplier: data.supplier,
    invoice_number: data.invoiceNumber,
    invoice_date: data.date,
    venue: data.venue,
    subtotal: data.subtotal,
    tax_total: data.vat,
    grand_total: data.total,
    line_items: data.lineItems.map(item => ({
      description: item.description,
      quantity: item.qty,
      unit: item.unit,
      unit_price: item.price,
      line_total: item.total,
    })),
  }

  const url = `${API_BASE_URL}/api/manual/invoices`
  console.log('[createManualInvoice] Sending request to:', url)
  console.log('[createManualInvoice] Request data:', backendData)

  try {
    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(backendData),
    })

    if (!response.ok) {
      let errorMessage = `Failed to create invoice: ${response.status} ${response.statusText}`
      try {
        const error = await response.json()
        errorMessage = error.message || error.detail || errorMessage
      } catch (e) {
        // If response is not JSON, use status text
        const text = await response.text().catch(() => '')
        if (text) {
          errorMessage = `${errorMessage}. ${text}`
        }
      }
      console.error('[createManualInvoice] Server error:', errorMessage)
      throw new Error(errorMessage)
    }

    const result = await response.json()
    console.log('[createManualInvoice] Success:', result)
    return normalizeSnakeToCamel(result)
  } catch (err) {
    // Handle network errors (fetch failed, CORS, etc.)
    const isNetworkError = err instanceof TypeError && (
      err.message === 'Failed to fetch' || 
      err.message.includes('fetch') ||
      err.message.includes('network') ||
      err.message.includes('CORS')
    )
    
    if (isNetworkError) {
      const baseUrl = API_BASE_URL || (typeof window !== 'undefined' ? window.location.origin : 'unknown')
      const errorMsg = `Cannot connect to backend server at ${baseUrl}/api/manual/invoices. Please ensure:
1. The backend server is running
2. The backend is accessible at the configured URL
3. If using separate ports, check your API configuration (currently: ${baseUrl})`
      console.error('[createManualInvoice] Network error:', err)
      console.error('[createManualInvoice] Attempted URL:', `${baseUrl}/api/manual/invoices`)
      throw new Error(errorMsg)
    }
    // Re-throw other errors (including our custom errors from above)
    throw err
  }
}

/**
 * Create a manual delivery note
 */
export async function createManualDeliveryNote(data: {
  noteNumber: string
  date: string
  supplier: string
  lineItems: Array<{
    description: string
    qty: number
    unit: string
    weight?: number
  }>
  supervisor?: string
  driver?: string
  vehicle?: string
  timeWindow?: string
  venue?: string
}) {
  // Transform frontend format to backend format
  const notesParts: string[] = []
  if (data.supervisor) notesParts.push(`Supervisor: ${data.supervisor}`)
  if (data.driver) notesParts.push(`Driver: ${data.driver}`)
  if (data.vehicle) notesParts.push(`Vehicle: ${data.vehicle}`)
  if (data.timeWindow) notesParts.push(`Time Window: ${data.timeWindow}`)
  
  const backendData = {
    venue: data.venue || 'Waterloo', // Default venue if not provided
    supplier: data.supplier,
    delivery_note_number: data.noteNumber,
    delivery_date: data.date,
    supervisor: data.supervisor, // Include supervisor separately
    notes: notesParts.length > 0 ? notesParts.join('\n') : undefined,
    line_items: data.lineItems.map(item => ({
      description: item.description,
      quantity: item.qty,
      unit: item.unit,
      unit_price: undefined, // Delivery notes don't have prices
      line_total: undefined,
      weight: item.weight, // Include weight if provided
    })),
  }

  const url = `${API_BASE_URL}/api/manual/delivery-notes`
  console.log('[API] Creating delivery note:', { url, data: backendData })
  console.log('[API] Backend data details:', {
    supplier: backendData.supplier,
    delivery_note_number: backendData.delivery_note_number,
    delivery_date: backendData.delivery_date,
    venue: backendData.venue,
    line_items_count: backendData.line_items.length
  })
  
  const response = await fetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(backendData),
  })

  console.log('[API] Delivery note creation response:', { status: response.status, ok: response.ok })
  
  // Read response body only once
  let result
  try {
    result = await response.json()
  } catch (e) {
    // If JSON parsing fails, try to get text
    const text = await response.text()
    console.error('[API] Failed to parse JSON response:', text)
    throw new Error(`Failed to parse response: ${text}`)
  }
  
  if (!response.ok) {
    console.error('[API] Delivery note creation error:', result)
    throw new Error(result.message || result.detail || `Failed to create delivery note: ${response.status}`)
  }

  console.log('[API] Delivery note created successfully:', result)
  console.log('[API] Delivery note created successfully:', result)
  return normalizeSnakeToCamel(result)
}

/**
 * Validate a pair before linking (preview validation results)
 */
export interface ValidatePairResponse {
  isValid: boolean
  matchScore: number
  discrepancies: Array<{
    description: string
    invoiceQty: number
    deliveryQty: number
    difference: number
    severity: 'critical' | 'warning' | 'info'
  }>
  warnings: string[]
}

export async function validatePair(invoiceId: string, deliveryNoteId: string): Promise<ValidatePairResponse> {
  const response = await fetch(`${API_BASE_URL}/api/manual/validate-pair`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ invoice_id: invoiceId, delivery_note_id: deliveryNoteId }),
  })

  if (!response.ok) {
    const error = await response.json().catch(() => ({ message: 'Failed to validate pair' }))
    throw new Error(error.message || `Failed to validate pair: ${response.status}`)
  }

  return normalizeSnakeToCamel(await response.json())
}

/**
 * Link a delivery note to an invoice
 */
export interface LinkDeliveryNoteResponse {
  invoiceId: string
  deliveryNoteId: string
  status: string
  issuesCount: number
  paired: boolean
  message: string
  warnings?: string[]
  quantityMatchScore?: number
}

export async function linkDeliveryNoteToInvoice(invoiceId: string, deliveryNoteId: string): Promise<LinkDeliveryNoteResponse> {
  const response = await fetch(`${API_BASE_URL}/api/manual/match`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ invoice_id: invoiceId, delivery_note_id: deliveryNoteId }),
  })

  if (!response.ok) {
    const error = await response.json().catch(() => ({ message: 'Failed to link delivery note' }))
    throw new Error(error.message || `Failed to link delivery note: ${response.status}`)
  }

  return normalizeSnakeToCamel(await response.json())
}

/**
 * Unpair a delivery note from an invoice
 */
export interface UnpairResponse {
  invoiceId: string
  success: boolean
  message: string
}

export async function unpairDeliveryNoteFromInvoice(invoiceId: string): Promise<UnpairResponse> {
  const response = await fetch(`${API_BASE_URL}/api/manual/invoices/${invoiceId}/unpair`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
  })

  if (!response.ok) {
    const error = await response.json().catch(() => ({ message: 'Failed to unpair delivery note' }))
    throw new Error(error.message || error.detail || `Failed to unpair delivery note: ${response.status}`)
  }

  return normalizeSnakeToCamel(await response.json())
}

export interface DeleteDeliveryNotesResponse {
  success: boolean
  deleted_count: number
  skipped_count: number
  message: string
}

export async function deleteDeliveryNotes(deliveryNoteIds: string[]): Promise<DeleteDeliveryNotesResponse> {
  const response = await fetch(`${API_BASE_URL}/api/delivery-notes/batch/delete`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ delivery_note_ids: deliveryNoteIds }),
  })

  if (!response.ok) {
    const error = await response.json().catch(() => ({ message: 'Failed to delete delivery notes' }))
    throw new Error(error.message || error.detail || `Failed to delete delivery notes: ${response.status}`)
  }

  return normalizeSnakeToCamel(await response.json())
}

/**
 * Update a manual invoice
 */
export async function updateManualInvoice(invoiceId: string, data: {
  supplier: string
  invoiceNumber: string
  date: string
  venue: string
  lineItems: Array<{
    description: string
    qty: number
    unit: string
    price: number
    total: number
  }>
  subtotal: number
  vat: number
  total: number
}) {
  const backendData = {
    venue: data.venue,
    supplier: data.supplier,
    invoice_number: data.invoiceNumber,
    invoice_date: data.date,
    currency: 'GBP',
    subtotal: data.subtotal,
    tax_total: data.vat,
    grand_total: data.total,
    line_items: data.lineItems.map(item => ({
      description: item.description,
      quantity: item.qty,
      unit: item.unit,
      unit_price: item.price,
      line_total: item.total,
    })),
  }

  const url = `${API_BASE_URL}/api/manual/invoices/${invoiceId}`
  console.log('[API] Updating invoice:', { url, data: backendData })
  
  const response = await fetch(url, {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(backendData),
  })

  if (!response.ok) {
    const error = await response.json().catch(() => ({ message: 'Failed to update invoice', detail: 'Unknown error' }))
    const errorMsg = error.detail || error.message || `Failed to update invoice: ${response.status}`
    console.error('[API] Update invoice error:', { status: response.status, error, requestData: backendData })
    throw new Error(errorMsg)
  }

  return normalizeSnakeToCamel(await response.json())
}

/**
 * Update a manual delivery note
 */
export async function updateManualDeliveryNote(dnId: string, data: {
  noteNumber: string
  date: string
  supplier: string
  lineItems: Array<{
    description: string
    qty: number
    unit: string
    weight?: number
  }>
  supervisor?: string
  driver?: string
  vehicle?: string
  timeWindow?: string
  venue?: string
}) {
  // Transform frontend format to backend format
  const notesParts: string[] = []
  if (data.supervisor) notesParts.push(`Supervisor: ${data.supervisor}`)
  if (data.driver) notesParts.push(`Driver: ${data.driver}`)
  if (data.vehicle) notesParts.push(`Vehicle: ${data.vehicle}`)
  if (data.timeWindow) notesParts.push(`Time Window: ${data.timeWindow}`)
  
  const backendData = {
    venue: data.venue || 'Waterloo',
    supplier: data.supplier,
    delivery_note_number: data.noteNumber,
    delivery_date: data.date,
    supervisor: data.supervisor,
    notes: notesParts.length > 0 ? notesParts.join('\n') : undefined,
    line_items: data.lineItems.map(item => ({
      description: item.description,
      quantity: item.qty,
      unit: item.unit,
      unit_price: undefined,
      line_total: undefined,
      weight: item.weight,
    })),
  }

  const url = `${API_BASE_URL}/api/manual/delivery-notes/${dnId}`
  console.log('[API] Updating delivery note:', { url, data: backendData })
  
  const response = await fetch(url, {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(backendData),
  })

  if (!response.ok) {
    const error = await response.json().catch(() => ({ message: 'Failed to update delivery note' }))
    throw new Error(error.message || `Failed to update delivery note: ${response.status}`)
  }

  return normalizeSnakeToCamel(await response.json())
}

/**
 * Fetch delivery note details
 */
export async function fetchDeliveryNoteDetails(id: string) {
  const response = await fetch(`${API_BASE_URL}/api/manual/delivery-notes/${id}`)

  if (!response.ok) {
    // Return null for 404 instead of throwing - delivery note might not exist
    if (response.status === 404) {
      return null
    }
    const error = await response.json().catch(() => ({ message: 'Failed to fetch delivery note' }))
    throw new Error(error.message || `Failed to fetch delivery note: ${response.status}`)
  }

  return normalizeSnakeToCamel(await response.json())
}

/**
 * Fetch all delivery notes (for linking)
 */
export async function fetchDeliveryNotes() {
  try {
    const response = await fetch(`${API_BASE_URL}/api/delivery-notes`)

    if (!response.ok) {
      // 404 means no delivery notes exist yet - return empty array
      if (response.status === 404) {
        return []
      }
      // For other errors, throw to indicate API failure
      const error = await response.json().catch(() => ({ message: 'Failed to fetch delivery notes' }))
      const errorMessage = error.message || error.detail || `Failed to fetch delivery notes: ${response.status}`
      console.error('Failed to fetch delivery notes:', errorMessage)
      throw new Error(errorMessage)
    }

    const data = await response.json()
    const normalized = normalizeSnakeToCamel(data)
    
    // Handle both array and object with array property
    if (Array.isArray(normalized)) {
      return normalized
    }
    if (Array.isArray(normalized.deliveryNotes)) {
      return normalized.deliveryNotes
    }
    if (Array.isArray(normalized.delivery_notes)) {
      return normalized.delivery_notes
    }
    
    return []
  } catch (err) {
    // Re-throw if it's already an Error we created
    if (err instanceof Error) {
      throw err
    }
    // For network errors, throw with context
    const errorMessage = err instanceof Error ? err.message : 'Network error while fetching delivery notes'
    console.error('Error fetching delivery notes:', errorMessage, err)
    throw new Error(errorMessage)
  }
}

/**
 * Fetch unpaired delivery notes (not currently paired with any invoice)
 */
export async function fetchUnpairedDeliveryNotes(filters?: {
  venue?: string
  supplier?: string
  from_date?: string
  to_date?: string
}): Promise<any[]> {
  try {
    const params = new URLSearchParams()
    if (filters?.venue) params.append('venue', filters.venue)
    if (filters?.supplier) params.append('supplier', filters.supplier)
    if (filters?.from_date) params.append('from_date', filters.from_date)
    if (filters?.to_date) params.append('to_date', filters.to_date)
    
    const url = `${API_BASE_URL}/api/delivery-notes/unpaired${params.toString() ? '?' + params.toString() : ''}`
    const response = await fetch(url)
    
    if (!response.ok) {
      // 404 or other errors - return empty array
      if (response.status === 404) {
        return []
      }
      const error = await response.json().catch(() => ({ message: 'Failed to fetch unpaired delivery notes' }))
      const errorMessage = error.message || error.detail || `Failed to fetch unpaired delivery notes: ${response.status}`
      console.error('Failed to fetch unpaired delivery notes:', errorMessage)
      throw new Error(errorMessage)
    }
    
    const data = await response.json()
    const normalized = normalizeSnakeToCamel(data)
    
    // Handle both array and object with array property
    if (Array.isArray(normalized)) {
      return normalized
    }
    if (Array.isArray(normalized.deliveryNotes)) {
      return normalized.deliveryNotes
    }
    
    return []
  } catch (err) {
    // Re-throw if it's already an Error we created
    if (err instanceof Error) {
      throw err
    }
    // For network errors, throw with context
    const errorMessage = err instanceof Error ? err.message : 'Network error while fetching unpaired delivery notes'
    console.error('Error fetching unpaired delivery notes:', errorMessage, err)
    throw new Error(errorMessage)
  }
}

/**
 * Fetch paired invoices for a delivery note
 */
export async function fetchPairedInvoicesForDeliveryNote(deliveryNoteId: string) {
  try {
    const response = await fetch(`${API_BASE_URL}/api/delivery-notes/${deliveryNoteId}/paired-invoices`)
    
    if (!response.ok) {
      // 404 means no paired invoices - return empty array
      if (response.status === 404) {
        return []
      }
      // For other errors, throw to indicate API failure
      const error = await response.json().catch(() => ({ message: 'Failed to fetch paired invoices' }))
      const errorMessage = error.message || error.detail || `Failed to fetch paired invoices: ${response.status}`
      console.error('Failed to fetch paired invoices for delivery note:', errorMessage)
      throw new Error(errorMessage)
    }
    
    const data = await response.json()
    const normalized = normalizeSnakeToCamel(data)
    
    // Handle both array and object with array property
    if (Array.isArray(normalized)) {
      return normalized
    }
    if (Array.isArray(normalized.invoices)) {
      return normalized.invoices
    }
    if (Array.isArray(normalized.pairedInvoices)) {
      return normalized.pairedInvoices
    }
    
    return []
  } catch (err) {
    // Re-throw if it's already an Error we created
    if (err instanceof Error) {
      throw err
    }
    // For network errors, throw with context
    const errorMessage = err instanceof Error ? err.message : 'Network error while fetching paired invoices'
    console.error('Error fetching paired invoices for delivery note:', errorMessage, err)
    throw new Error(errorMessage)
  }
}

/**
 * Mark invoice as reviewed
 */
export async function markInvoiceReviewed(invoiceId: string) {
  const response = await fetch(`${API_BASE_URL}/api/invoices/${invoiceId}/mark-reviewed`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
  })

  if (!response.ok) {
    const error = await response.json().catch(() => ({ message: 'Failed to mark as reviewed' }))
    throw new Error(error.message || `Failed to mark as reviewed: ${response.status}`)
  }

  return normalizeSnakeToCamel(await response.json())
}

/**
 * Submit invoices (mark as complete/submitted)
 */
export interface SubmitInvoicesResponse {
  success: boolean
  submitted_count: number
  invoice_ids: string[]
  message: string
}

export async function submitInvoices(invoiceIds: string[]): Promise<SubmitInvoicesResponse> {
  const response = await fetch(`${API_BASE_URL}/api/invoices/submit`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ invoice_ids: invoiceIds }),
  })

  if (!response.ok) {
    const error = await response.json().catch(() => ({ message: 'Failed to submit invoices' }))
    throw new Error(error.message || `Failed to submit invoices: ${response.status}`)
  }

  return normalizeSnakeToCamel(await response.json())
}

/**
 * Escalate invoice to supplier
 */
export async function escalateToSupplier(invoiceId: string, message?: string) {
  const response = await fetch(`${API_BASE_URL}/api/invoices/${invoiceId}/escalate`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ message: message || '' }),
  })

  if (!response.ok) {
    const error = await response.json().catch(() => ({ message: 'Failed to escalate' }))
    throw new Error(error.message || `Failed to escalate: ${response.status}`)
  }

  return normalizeSnakeToCamel(await response.json())
}

/**
 * Save a note/comment on an invoice
 */
export async function saveInvoiceNote(invoiceId: string, note: string) {
  const response = await fetch(`${API_BASE_URL}/api/invoices/${invoiceId}/notes`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ note }),
  })

  if (!response.ok) {
    const error = await response.json().catch(() => ({ message: 'Failed to save note' }))
    throw new Error(error.message || `Failed to save note: ${response.status}`)
  }

  return normalizeSnakeToCamel(await response.json())
}

/**
 * Fetch invoice PDF file
 */
export async function fetchInvoicePDF(invoiceId: string): Promise<string> {
  const response = await fetch(`${API_BASE_URL}/api/invoices/${invoiceId}/pdf`)

  if (!response.ok) {
    const error = await response.json().catch(() => ({ message: 'Failed to fetch PDF' }))
    throw new Error(error.message || `Failed to fetch PDF: ${response.status}`)
  }

  const blob = await response.blob()
  return URL.createObjectURL(blob)
}

/**
 * Fetch OCR details for an invoice
 */
export async function fetchOCRDetails(invoiceId: string) {
  const response = await fetch(`${API_BASE_URL}/api/invoices/${invoiceId}/ocr-details`)

  if (!response.ok) {
    // If endpoint doesn't exist, return empty object instead of throwing
    if (response.status === 404) {
      return {}
    }
    const error = await response.json().catch(() => ({ message: 'Failed to fetch OCR details' }))
    throw new Error(error.message || `Failed to fetch OCR details: ${response.status}`)
  }

  return normalizeSnakeToCamel(await response.json())
}

/**
 * Fetch pairing suggestions for an invoice
 */
export interface QuantityDifference {
  description: string
  invoiceQty: number
  dnQty: number
  difference: number
}

export interface PairingSuggestion {
  id: string
  deliveryNoteId: string
  deliveryNoteNumber?: string
  deliveryDate?: string
  supplier?: string
  totalAmount?: number
  similarity?: number
  confidence?: number
  valueDelta?: number
  dateDeltaDays?: number
  reason?: string
  quantityMatchScore?: number
  quantityWarnings?: string[]
  quantityDifferences?: QuantityDifference[]
  hasQuantityMismatch?: boolean
  llmExplanation?: string
  probability?: number
  featuresSummary?: {
    amountDiffPct?: number
    dateDiffDays?: number
    proportionInvoiceValueExplained?: number
    supplierNameSimilarity?: number
    ocrConfidenceTotal?: number
  }
}

export interface PairingSuggestionsResponse {
  suggestions: PairingSuggestion[]
}

/**
 * Fetch pairing status and suggestions from the new pairing API
 */
export interface PairingResult {
  invoiceId: string
  status: 'auto_paired' | 'suggested' | 'unpaired'
  pairingConfidence?: number
  pairingModelVersion?: string
  bestCandidate?: PairingCandidate
  candidates: PairingCandidate[]
  llmExplanation?: string
}

export interface PairingCandidate {
  deliveryNoteId: string
  probability: number
  features?: Record<string, number>
  featuresSummary?: {
    amountDiffPct?: number
    dateDiffDays?: number
    proportionInvoiceValueExplained?: number
    supplierNameSimilarity?: number
    ocrConfidenceTotal?: number
  }
  deliveryDate?: string
  deliveryTotal?: number
  venue?: string
  supplier?: string
  modelVersion?: string
}

export async function fetchPairingStatus(invoiceId: string, mode: 'normal' | 'review' = 'normal'): Promise<PairingResult> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/pairing/invoice/${invoiceId}?mode=${mode}`)

    if (!response.ok) {
      const error = await response.json().catch(() => ({ message: 'Failed to fetch pairing status' }))
      const errorMessage = error.message || error.detail || `Failed to fetch pairing status: ${response.status}`
      throw new Error(errorMessage)
    }

    return normalizeSnakeToCamel(await response.json())
  } catch (err) {
    const errorMessage = err instanceof Error ? err.message : 'Network error while fetching pairing status'
    console.error(`Error fetching pairing status for invoice ${invoiceId}:`, errorMessage, err)
    throw new Error(errorMessage)
  }
}

/**
 * Fetch pairing statistics and metrics
 */
export interface PairingStats {
  totalInvoices: number
  pairedCount: number
  unpairedCount: number
  suggestedCount: number
  autoPairedCount: number
  manualPairedCount: number
  avgConfidence?: number
  pairingRate7d: number
  pairingRate30d: number
  recentActivity: Array<{
    timestamp: string
    invoiceId: string
    deliveryNoteId?: string
    action: string
    actorType: string
    modelVersion?: string
  }>
}

export async function fetchPairingStats(): Promise<PairingStats> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/pairing/stats`)

    if (!response.ok) {
      const error = await response.json().catch(() => ({ message: 'Failed to fetch pairing stats' }))
      const errorMessage = error.message || error.detail || `Failed to fetch pairing stats: ${response.status}`
      throw new Error(errorMessage)
    }

    return normalizeSnakeToCamel(await response.json())
  } catch (err) {
    const errorMessage = err instanceof Error ? err.message : 'Network error while fetching pairing stats'
    console.error('Error fetching pairing stats:', errorMessage, err)
    throw new Error(errorMessage)
  }
}

export async function fetchPairingSuggestions(invoiceId: string): Promise<PairingSuggestionsResponse> {
  try {
    // Try new pairing API first
    const pairingResult = await fetchPairingStatus(invoiceId, 'review')
    
    // Convert PairingResult to PairingSuggestionsResponse format
    const suggestions: PairingSuggestion[] = pairingResult.candidates.map((candidate, idx) => ({
      id: `suggestion-${idx}`,
      deliveryNoteId: candidate.deliveryNoteId,
      deliveryDate: candidate.deliveryDate,
      supplier: candidate.supplier,
      totalAmount: candidate.deliveryTotal,
      confidence: candidate.probability,
      probability: candidate.probability,
      valueDelta: candidate.featuresSummary?.amountDiffPct,
      dateDeltaDays: candidate.featuresSummary?.dateDiffDays,
      reason: pairingResult.llmExplanation || undefined,
      llmExplanation: pairingResult.llmExplanation,
      featuresSummary: candidate.featuresSummary,
    }))
    
    return { suggestions }
  } catch (err) {
    // Fallback to old endpoint if new one fails
    try {
      const response = await fetch(`${API_BASE_URL}/api/invoices/${invoiceId}/suggestions`)

      if (!response.ok) {
        if (response.status === 404) {
          return { suggestions: [] }
        }
        const error = await response.json().catch(() => ({ message: 'Failed to fetch pairing suggestions' }))
        const errorMessage = error.message || error.detail || `Failed to fetch pairing suggestions: ${response.status}`
        throw new Error(errorMessage)
      }

      return normalizeSnakeToCamel(await response.json())
    } catch (fallbackErr) {
      if (fallbackErr instanceof Error) {
        throw fallbackErr
      }
      const errorMessage = err instanceof Error ? err.message : 'Network error while fetching pairing suggestions'
      console.error(`Error fetching pairing suggestions for invoice ${invoiceId}:`, errorMessage, err)
      throw new Error(errorMessage)
    }
  }
}

/**
 * Fetch unmatched delivery notes
 */
export interface UnmatchedDeliveryNote {
  id: string
  noteNumber?: string
  supplier?: string
  date?: string
  total?: number
  venue?: string
  deliveryNo?: string
  docDate?: string
}

export async function fetchUnmatchedDeliveryNotes(): Promise<UnmatchedDeliveryNote[]> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/dashboard/unmatched-dns`)
    
    if (!response.ok) {
      // 404 means no unmatched delivery notes - return empty array
      if (response.status === 404) {
        return []
      }
      // For other errors, throw to indicate API failure
      const error = await response.json().catch(() => ({ message: 'Failed to fetch unmatched delivery notes' }))
      const errorMessage = error.message || error.detail || `Failed to fetch unmatched delivery notes: ${response.status}`
      console.error('Failed to fetch unmatched delivery notes:', errorMessage)
      throw new Error(errorMessage)
    }

    const data = await response.json()
    const normalized = normalizeSnakeToCamel(data)
    
    // Handle both array and object with array property
    if (Array.isArray(normalized)) {
      return normalized
    }
    if (Array.isArray(normalized.deliveryNotes)) {
      return normalized.deliveryNotes
    }
    if (Array.isArray(normalized.delivery_notes)) {
      return normalized.delivery_notes
    }
    
    return []
  } catch (err) {
    // Re-throw if it's already an Error we created
    if (err instanceof Error) {
      throw err
    }
    // For network errors, throw with context
    const errorMessage = err instanceof Error ? err.message : 'Network error while fetching unmatched delivery notes'
    console.error('Error fetching unmatched delivery notes:', errorMessage, err)
    throw new Error(errorMessage)
  }
}

/**
 * Fetch invoice suggestions for a delivery note (reverse of invoice suggestions)
 */
export interface InvoiceSuggestionForDN {
  id: string
  invoiceId: string
  invoiceNumber?: string
  invoiceDate?: string
  supplier?: string
  totalAmount?: number
  similarity?: number
  confidence?: number
  valueDelta?: number
  dateDeltaDays?: number
  reason?: string
  quantityDifferences?: QuantityDifference[]
  hasQuantityMismatch?: boolean
  quantityMatchScore?: number
  quantityWarnings?: string[]
}

export interface InvoiceSuggestionsForDNResponse {
  suggestions: InvoiceSuggestionForDN[]
}

export async function fetchInvoiceSuggestionsForDN(deliveryNoteId: string): Promise<InvoiceSuggestionsForDNResponse> {
  try {
    // Try the reverse endpoint - if it doesn't exist, we'll use the pairs endpoint
    const response = await fetch(`${API_BASE_URL}/api/delivery-notes/${deliveryNoteId}/suggestions`)
    
    if (!response.ok) {
      // If endpoint doesn't exist, try to get suggestions from pairs endpoint
      if (response.status === 404) {
        // Fallback: try to get from pairs endpoint
        try {
          const pairsResponse = await fetch(`${API_BASE_URL}/api/pairs/suggestions?delivery_note_id=${deliveryNoteId}`)
          if (pairsResponse.ok) {
            const pairsData = await pairsResponse.json()
            const normalized = normalizeSnakeToCamel(pairsData)
            const suggestions = Array.isArray(normalized) ? normalized : (normalized.suggestions || [])
            return { suggestions: suggestions.filter((s: any) => s.deliveryNoteId === deliveryNoteId || s.delivery_id === deliveryNoteId) }
          }
          // If pairs endpoint also fails, return empty (no suggestions available)
          return { suggestions: [] }
        } catch (pairsErr) {
          // If pairs endpoint fails, return empty (no suggestions available)
          return { suggestions: [] }
        }
      }
      // For other errors, throw to indicate API failure
      const error = await response.json().catch(() => ({ message: 'Failed to fetch invoice suggestions' }))
      const errorMessage = error.message || error.detail || `Failed to fetch invoice suggestions: ${response.status}`
      console.error('Failed to fetch invoice suggestions for delivery note:', errorMessage)
      throw new Error(errorMessage)
    }

    return normalizeSnakeToCamel(await response.json())
  } catch (err) {
    // Re-throw if it's already an Error we created
    if (err instanceof Error && err.message !== 'Failed to fetch invoice suggestions') {
      throw err
    }
    // For network errors or our own errors, throw with context
    const errorMessage = err instanceof Error ? err.message : 'Network error while fetching invoice suggestions'
    console.error('Error fetching invoice suggestions for delivery note:', errorMessage, err)
    throw new Error(errorMessage)
  }
}

/**
 * Delete invoices that haven't been submitted (removes invoices and associated data)
 */
export async function deleteInvoices(invoiceIds: string[]): Promise<{ success: boolean; deleted_count: number; skipped_count?: number; message: string }> {
  const response = await fetch(`${API_BASE_URL}/api/invoices/batch/delete`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ invoice_ids: invoiceIds }),
  })

  if (!response.ok) {
    // Try to get error details from response
    let errorMessage = `Failed to delete invoices: ${response.status}`
    try {
      const errorData = await response.json()
      errorMessage = errorData.detail || errorData.message || errorMessage
    } catch {
      // If response is not JSON, use status-based message
      if (response.status === 405) {
        errorMessage = 'Method not allowed. The delete endpoint may not be properly configured.'
      } else if (response.status === 403) {
        errorMessage = 'Forbidden. This operation is not allowed.'
      } else if (response.status === 404) {
        errorMessage = 'Endpoint not found. The delete endpoint may not be available.'
      }
    }
    throw new Error(errorMessage)
  }

  return normalizeSnakeToCamel(await response.json())
}

/**
 * Fetch item description suggestions from the database
 * @param query - Search query string
 * @param limit - Maximum number of suggestions to return (default: 20)
 * @returns Array of suggestion strings
 */
export async function fetchItemSuggestions(query: string, limit: number = 20): Promise<string[]> {
  try {
    const params = new URLSearchParams({
      q: query || '',
      limit: limit.toString()
    })
    
    const response = await fetch(`${API_BASE_URL}/api/items/suggestions?${params}`)
    
    if (!response.ok) {
      throw new Error(`Failed to fetch item suggestions: ${response.status} ${response.statusText}`)
    }
    
    const data = await response.json()
    return data.suggestions || []
  } catch (error) {
    console.error('Error fetching item suggestions:', error)
    return []
  }
}

