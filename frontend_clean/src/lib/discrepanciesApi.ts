/**
 * Discrepancy API Types and Functions
 */

import { API_BASE_URL } from './config'

export type DiscrepancySeverity = 'critical' | 'warning' | 'info'
export type DiscrepancyLevel = 'critical' | 'major' | 'minor'

export interface DiscrepancyContextRef {
  type: 'invoice' | 'delivery-note' | 'system' | 'venue'
  id?: string | number
}

export interface DiscrepancyAction {
  actionType: 'filter' | 'scroll' | 'navigate'
  target?: string
  label?: string
}

export interface DiscrepancyItem {
  id: string
  type: string
  severity: DiscrepancySeverity
  level?: DiscrepancyLevel
  title: string
  description?: string
  contextLabel?: string
  contextRef?: DiscrepancyContextRef
  actions?: DiscrepancyAction[]
  focusTarget?: 'invoice_header' | 'delivery_link' | 'line_items' | 'credits' | null
  createdAt?: string
  metadata?: Record<string, unknown>
}

export interface FetchDiscrepanciesResponse {
  items: DiscrepancyItem[]
  lastUpdated: string
}

/**
 * Fetch discrepancies from the backend API
 * @param scope - The scope to fetch discrepancies for ('dashboard', 'invoices', etc.)
 * @returns Promise resolving to discrepancies response
 */
export async function fetchDiscrepancies(scope: string): Promise<FetchDiscrepanciesResponse> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/discrepancies?scope=${scope}`)
    
    if (!response.ok) {
      // If endpoint doesn't exist (404), return empty response silently
      // This endpoint is optional - frontend can work without it
      if (response.status === 404) {
        // Don't log 404 errors - endpoint is optional
        return {
          items: [],
          lastUpdated: new Date().toISOString()
        }
      }
      // For other errors, log but don't throw
      console.warn(`Failed to fetch discrepancies (${response.status}):`, response.statusText)
      return {
        items: [],
        lastUpdated: new Date().toISOString()
      }
    }
    
    const data = await response.json()
    return {
      items: data.items || data.discrepancies || [],
      lastUpdated: data.lastUpdated || data.last_updated || new Date().toISOString()
    }
  } catch (error) {
    // If API call fails (network error, etc.), return empty response silently
    // This endpoint is optional - frontend can work without it
    // Only log if it's not a 404 (which we handle above)
    if (error instanceof Error && !error.message.includes('404')) {
      console.warn('Failed to fetch discrepancies from API, returning empty list:', error)
    }
    return {
      items: [],
      lastUpdated: new Date().toISOString()
    }
  }
}
