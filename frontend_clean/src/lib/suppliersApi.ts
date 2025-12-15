/**
 * Suppliers API Client
 * Centralized API calls for supplier data with error handling
 */

import { API_BASE_URL } from './config'
import type { DateRange } from './dashboardApi'

export type SupplierStatus = 'Active' | 'On Watch' | 'Blocked'
export type SupplierCategory = 'Food' | 'Beverage' | 'Utilities' | 'Other'
export type SupplierRiskLevel = 'High' | 'Medium' | 'Low'
export type IssueType = 'Overcharge' | 'Short delivery' | 'Late' | 'Quality issue'
export type IssueStatus = 'Open' | 'In Review' | 'Resolved' | 'Escalated'

export interface SupplierListItem {
  id: string
  name: string
  category?: SupplierCategory
  score: 'A' | 'B' | 'C' | 'D' | 'E'
  mismatchRate: number
  lateDeliveries: number
  priceVolatility: number
  totalSpend: number
  status: SupplierStatus
  lastInvoiceDate?: string
  lastInvoiceValue?: number
  flagsCount?: number
  matchRate?: number
}

export interface SupplierDetail extends SupplierListItem {
  accuracy: number // match rate percentage
  reliability: number // on-time delivery percentage
  priceBehaviour: 'stable' | 'rising' | 'volatile'
  disputeHistory: {
    totalCredits: number
    totalEscalations: number
    avgResolutionDays: number
  }
  timeline: Array<{
    date: string
    event: string
    type: 'invoice' | 'spike' | 'blocked' | 'contract' | 'flag'
  }>
  contact?: {
    name?: string
    email?: string
    phone?: string
  }
  terms?: {
    paymentTerms?: string
    deliveryDays?: string[]
    contractEndDate?: string
  }
}

export interface SupplierIssue {
  id: string
  type: IssueType
  count: number
  latestOccurrence: string
  monetaryImpact: number
  status: IssueStatus
  affectedInvoices?: string[]
  suggestedCredit?: number
  recommendedAction?: string
  emailTemplate?: string
}

export interface SupplierPricingData {
  itemId: string
  itemName: string
  prices: Array<{
    date: string
    price: number
    forecast?: number
    confidence?: number
  }>
  averagePrice?: number
  recentChange?: {
    percentage: number
    period: string
  }
  volatilityFlags?: Array<{
    date: string
    change: number
    reason: string
  }>
}

export interface SupplierDelivery {
  id: string
  deliveryNoteNumber: string
  date: string
  status: 'Fully matched' | 'Partially matched' | 'Unmatched'
  onTime: boolean
  missingItems?: number
  delayHours?: number
}

export interface SupplierAuditEntry {
  id: string
  timestamp: string
  actor: string
  action: string
  details?: string
}

export interface SupplierNote {
  id: string
  timestamp: string
  author: string
  role: 'GM' | 'Finance' | 'ShiftLead'
  content: string
}

/**
 * Fetch list of suppliers
 */
export async function fetchSuppliersList(
  venueId?: string,
  dateRange: DateRange = '30d'
): Promise<SupplierListItem[]> {
  const params = new URLSearchParams()
  if (venueId) params.append('venue_id', venueId)
  params.append('date_range', dateRange)

  try {
    const response = await fetch(`${API_BASE_URL}/api/dashboard/suppliers?${params.toString()}`)
    if (!response.ok) {
      throw new Error(`Failed to fetch suppliers: ${response.statusText}`)
    }
    const data = await response.json()
    // Transform backend response to match our interface
    return (data.suppliers || []).map((s: any) => ({
      id: s.id || s.name?.toLowerCase().replace(/\s+/g, '-'),
      name: s.name,
      score: s.score || 'C',
      mismatchRate: s.mismatchRate || 0,
      lateDeliveries: s.lateDeliveries || 0,
      priceVolatility: s.priceVolatility || 0,
      totalSpend: s.totalSpend || 0,
      status: 'Active' as SupplierStatus,
      matchRate: 100 - (s.mismatchRate || 0),
    }))
  } catch (e) {
    const errorMessage = e instanceof Error ? e.message : 'Unknown error'
    console.error('Error fetching suppliers:', errorMessage, e)
    throw new Error(`Failed to fetch suppliers: ${errorMessage}`)
  }
}

/**
 * Fetch detailed supplier data
 */
export async function fetchSupplierDetail(supplierId: string): Promise<SupplierDetail | null> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/suppliers/${encodeURIComponent(supplierId)}/scorecard`)
    if (!response.ok) {
      // 404 means supplier has no scorecard data yet - return null instead of throwing
      if (response.status === 404) {
        console.log(`Supplier ${supplierId} has no scorecard data yet`)
        return null
      }
      // Only log and throw for unexpected errors (5xx, network issues)
      console.error(`Failed to fetch supplier scorecard: ${response.status} ${response.statusText}`)
      throw new Error(`Failed to fetch supplier detail: ${response.statusText}`)
    }
    const data = await response.json()
    
    // Transform backend response
    return {
      id: supplierId,
      name: data.supplier_id || supplierId,
      score: calculateScoreFromMetrics(data.metrics),
      mismatchRate: data.metrics?.mismatch_rate || 0,
      lateDeliveries: data.summary?.late_deliveries || 0,
      priceVolatility: data.metrics?.price_volatility || 0,
      totalSpend: 0, // Would need to calculate from invoices
      status: 'Active' as SupplierStatus,
      accuracy: 100 - (data.metrics?.mismatch_rate || 0),
      reliability: 100 - (data.metrics?.delivery_delay_rate || 0),
      priceBehaviour: (data.metrics?.price_volatility || 0) > 10 ? 'volatile' : 
                      (data.metrics?.price_volatility || 0) > 5 ? 'rising' : 'stable',
      disputeHistory: {
        totalCredits: 0,
        totalEscalations: data.summary?.resolved_issues || 0,
        avgResolutionDays: data.metrics?.avg_issue_resolution_days || 0,
      },
      timeline: [],
    }
  } catch (e) {
    // Only log unexpected errors (not 404s which are handled above)
    if (e instanceof Error && !e.message.includes('404')) {
      console.error('Error fetching supplier detail:', e)
    }
    // Re-throw for 5xx and network errors
    throw e
  }
}

/**
 * Fetch supplier issues and credits
 */
export async function fetchSupplierIssues(
  supplierId: string,
  dateRange: DateRange = '30d'
): Promise<SupplierIssue[]> {
  try {
    const params = new URLSearchParams()
    params.append('supplier_id', supplierId)
    params.append('date_range', dateRange)

    const response = await fetch(`${API_BASE_URL}/api/suppliers/${encodeURIComponent(supplierId)}/issues?${params.toString()}`)
    if (!response.ok) {
      throw new Error(`Failed to fetch supplier issues: ${response.statusText}`)
    }
    const data = await response.json()
    return data.issues || []
  } catch (e) {
    const errorMessage = e instanceof Error ? e.message : 'Unknown error'
    console.error('Error fetching supplier issues:', errorMessage, e)
    throw new Error(`Failed to fetch supplier issues: ${errorMessage}`)
  }
}

/**
 * Fetch supplier pricing data
 */
export async function fetchSupplierPricing(
  supplierId: string,
  itemId?: string,
  dateRange: DateRange = '30d'
): Promise<SupplierPricingData[]> {
  try {
    const params = new URLSearchParams()
    params.append('type', 'price')
    params.append('date_range', dateRange)
    params.append('supplier', supplierId)
    if (itemId) params.append('item', itemId)

    const response = await fetch(`${API_BASE_URL}/api/dashboard/trends?${params.toString()}`)
    if (!response.ok) {
      throw new Error(`Failed to fetch pricing: ${response.statusText}`)
    }
    const data = await response.json()
    
    // Transform trend data to pricing data
    if (data.data && data.data.length > 0) {
      return [{
        itemId: itemId || 'default',
        itemName: itemId || 'Average Price',
        prices: data.data.map((d: any) => ({
          date: d.date,
          price: d.value,
          forecast: d.forecast,
        })),
      }]
    }
    return []
  } catch (e) {
    const errorMessage = e instanceof Error ? e.message : 'Unknown error'
    console.error('Error fetching pricing:', errorMessage, e)
    throw new Error(`Failed to fetch supplier pricing: ${errorMessage}`)
  }
}

/**
 * Fetch supplier delivery history
 */
export async function fetchSupplierDeliveries(
  supplierId: string,
  dateRange: DateRange = '30d'
): Promise<SupplierDelivery[]> {
  try {
    const params = new URLSearchParams()
    params.append('supplier_id', supplierId)
    params.append('date_range', dateRange)

    const response = await fetch(`${API_BASE_URL}/api/suppliers/${encodeURIComponent(supplierId)}/deliveries?${params.toString()}`)
    if (!response.ok) {
      throw new Error(`Failed to fetch supplier deliveries: ${response.statusText}`)
    }
    const data = await response.json()
    return data.deliveries || []
  } catch (e) {
    const errorMessage = e instanceof Error ? e.message : 'Unknown error'
    console.error('Error fetching supplier deliveries:', errorMessage, e)
    throw new Error(`Failed to fetch supplier deliveries: ${errorMessage}`)
  }
}

/**
 * Fetch supplier audit log
 */
export async function fetchSupplierAudit(supplierId: string): Promise<SupplierAuditEntry[]> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/suppliers/${encodeURIComponent(supplierId)}/audit`)
    if (!response.ok) {
      throw new Error(`Failed to fetch supplier audit: ${response.statusText}`)
    }
    const data = await response.json()
    return data.audit || []
  } catch (e) {
    const errorMessage = e instanceof Error ? e.message : 'Unknown error'
    console.error('Error fetching supplier audit:', errorMessage, e)
    throw new Error(`Failed to fetch supplier audit: ${errorMessage}`)
  }
}

/**
 * Update supplier status
 */
export async function updateSupplierStatus(
  supplierId: string,
  status: SupplierStatus
): Promise<void> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/suppliers/${encodeURIComponent(supplierId)}/status`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ status }),
    })
    if (!response.ok) {
      throw new Error(`Failed to update status: ${response.statusText}`)
    }
  } catch (e) {
    const errorMessage = e instanceof Error ? e.message : 'Unknown error'
    console.error('Error updating supplier status:', errorMessage, e)
    throw new Error(`Failed to update supplier status: ${errorMessage}`)
  }
}

/**
 * Add note to supplier
 */
export async function addSupplierNote(
  supplierId: string,
  note: string,
  author: string,
  role: 'GM' | 'Finance' | 'ShiftLead'
): Promise<void> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/suppliers/${encodeURIComponent(supplierId)}/notes`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ note, author, role }),
    })
    if (!response.ok) {
      throw new Error(`Failed to add note: ${response.statusText}`)
    }
  } catch (e) {
    const errorMessage = e instanceof Error ? e.message : 'Unknown error'
    console.error('Error adding supplier note:', errorMessage, e)
    throw new Error(`Failed to add supplier note: ${errorMessage}`)
  }
}

/**
 * Generate credit email template
 */
export async function generateCreditEmail(
  supplierId: string,
  issueIds: string[]
): Promise<string> {
  // TODO: Implement real API call when endpoint is available
  return `Dear ${supplierId},

We are writing to request credit for the following issues:

${issueIds.map(id => `- Issue ${id}`).join('\n')}

Please review and confirm.

Thank you,
Finance Team`
}

// Helper function to calculate score from metrics
function calculateScoreFromMetrics(metrics: any): 'A' | 'B' | 'C' | 'D' | 'E' {
  const mismatchRate = metrics?.mismatch_rate || 0
  const deliveryDelay = metrics?.delivery_delay_rate || 0
  const priceVolatility = metrics?.price_volatility || 0
  
  if (mismatchRate < 2 && deliveryDelay < 2 && priceVolatility < 5) return 'A'
  if (mismatchRate < 5 && deliveryDelay < 5 && priceVolatility < 10) return 'B'
  if (mismatchRate < 10 && deliveryDelay < 10) return 'C'
  if (mismatchRate < 20) return 'D'
  return 'E'
}

