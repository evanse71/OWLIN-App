import { API_BASE_URL } from './config'

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
 * Recursively converts snake_case keys to camelCase for nested objects/arrays
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

