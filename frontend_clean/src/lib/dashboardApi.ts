/**
 * Dashboard API Client
 * Centralized API calls for dashboard data with error handling, caching, and response normalization
 */

import { API_BASE_URL } from './config'

// Cache for query results (simple in-memory cache)
const cache = new Map<string, { data: any; timestamp: number }>()
const CACHE_TTL = 60000 // 60 seconds

export type DateRange = 'today' | '7d' | '30d' | 'custom'
export type TrendType = 'spend' | 'price' | 'issues' | 'matchRate'

export interface DashboardMetrics {
  openIssues: {
    count: number
    severity: { high: number; medium: number; low: number }
    delta: number
  }
  matchRate: {
    value: number
    delta: number
    sparkline: number[]
  }
  spend: {
    total: number
    delta: number
    sparkline: number[]
  }
  priceVolatility: {
    itemsAboveThreshold: number
    delta: number
    sparkline: number[]
  }
}

export interface ActionItem {
  id: string
  type: 'resolve_mismatch' | 'pair_dn' | 'review_ocr' | 'submit_batch'
  title: string
  description: string
  priority: 'high' | 'medium' | 'low'
  status: 'pending' | 'in_review' | 'blocked' | 'done'
  metadata?: Record<string, any>
  createdAt: string
}

export interface SupplierRisk {
  id: string
  name: string
  score: 'A' | 'B' | 'C' | 'D' | 'E'
  mismatchRate: number
  lateDeliveries: number
  priceVolatility: number
  totalSpend: number
}

export interface TrendDataPoint {
  date: string
  value: number
  forecast?: number
  confidence?: number
}

export interface TrendData {
  data: TrendDataPoint[]
  forecast: TrendDataPoint[]
  unit: string
}

export interface UnmatchedDN {
  id: string
  deliveryNoteNumber: string
  supplier: string
  date: string
  age: number // days since creation
  suggestedInvoice?: {
    id: string
    confidence: number
  }
}

export interface ActivityItem {
  id: string
  actor: string
  action: string
  timestamp: string
  detail?: string
}

/**
 * Get cached data or fetch fresh
 */
async function cachedFetch<T>(
  key: string,
  fetcher: () => Promise<T>,
  ttl: number = CACHE_TTL
): Promise<T> {
  const cached = cache.get(key)
  if (cached && Date.now() - cached.timestamp < ttl) {
    return cached.data
  }

  const data = await fetcher()
  cache.set(key, { data, timestamp: Date.now() })
  return data
}

/**
 * Clear cache for a specific key or all cache
 */
export function clearCache(key?: string) {
  if (key) {
    cache.delete(key)
  } else {
    cache.clear()
  }
}

/**
 * Fetch dashboard summary data
 */
export async function fetchDashboard(
  venueId?: string,
  dateRange: DateRange = '30d'
): Promise<any> {
  const params = new URLSearchParams()
  if (venueId) params.append('venue_id', venueId)
  params.append('date_range', dateRange)

  const key = `dashboard:${venueId}:${dateRange}`
  return cachedFetch(key, async () => {
    const response = await fetch(`${API_BASE_URL}/api/dashboard?${params.toString()}`)
    if (!response.ok) {
      throw new Error(`Failed to fetch dashboard: ${response.statusText}`)
    }
    return response.json()
  })
}

/**
 * Fetch dashboard metrics with period comparisons
 */
export async function fetchMetrics(
  venueId?: string,
  dateRange: DateRange = '30d'
): Promise<DashboardMetrics> {
  const params = new URLSearchParams()
  if (venueId) params.append('venue_id', venueId)
  params.append('date_range', dateRange)

  const key = `metrics:${venueId}:${dateRange}`
  try {
    return await cachedFetch(key, async () => {
      const response = await fetch(`${API_BASE_URL}/api/dashboard/metrics?${params.toString()}`)
      if (!response.ok) {
        const errorText = await response.text()
        console.error(`Failed to fetch metrics: ${response.status} ${errorText}`)
        throw new Error(`Failed to fetch metrics: ${response.statusText}`)
      }
      const data = await response.json()
      console.log('Fetched metrics:', data)
      return data
    })
  } catch (e) {
    console.error('Error fetching metrics, using fallback:', e)
    // Return fallback data
    return {
      openIssues: { count: 0, severity: { high: 0, medium: 0, low: 0 }, delta: 0 },
      matchRate: { value: 0, delta: 0, sparkline: [] },
      spend: { total: 0, delta: 0, sparkline: [] },
      priceVolatility: { itemsAboveThreshold: 0, delta: 0, sparkline: [] },
    }
  }
}

/**
 * Fetch action queue items
 */
export async function fetchActions(
  venueId?: string,
  role?: string
): Promise<ActionItem[]> {
  const params = new URLSearchParams()
  if (venueId) params.append('venue_id', venueId)
  if (role) params.append('role', role)

  const key = `actions:${venueId}:${role}`
  try {
    return await cachedFetch(key, async () => {
      const response = await fetch(`${API_BASE_URL}/api/dashboard/actions?${params.toString()}`)
      if (!response.ok) {
        const errorText = await response.text()
        console.error(`Failed to fetch actions: ${response.status} ${errorText}`)
        throw new Error(`Failed to fetch actions: ${response.statusText}`)
      }
      const data = await response.json()
      console.log('Fetched actions:', data)
      return data.actions || []
    })
  } catch (e) {
    console.error('Error fetching actions, using fallback:', e)
    return []
  }
}

/**
 * Fetch supplier risk board data
 */
export async function fetchSuppliers(
  venueId?: string,
  dateRange: DateRange = '30d'
): Promise<SupplierRisk[]> {
  const params = new URLSearchParams()
  if (venueId) params.append('venue_id', venueId)
  params.append('date_range', dateRange)

  const key = `suppliers:${venueId}:${dateRange}`
  try {
    return await cachedFetch(key, async () => {
      const response = await fetch(`${API_BASE_URL}/api/dashboard/suppliers?${params.toString()}`)
      if (!response.ok) {
        const errorText = await response.text()
        console.error(`Failed to fetch suppliers: ${response.status} ${errorText}`)
        throw new Error(`Failed to fetch suppliers: ${response.statusText}`)
      }
      const data = await response.json()
      console.log('Fetched suppliers:', data)
      return data.suppliers || []
    })
  } catch (e) {
    console.error('Error fetching suppliers, using fallback:', e)
    return []
  }
}

/**
 * Fetch trend data
 */
export async function fetchTrends(
  type: TrendType,
  venueId?: string,
  dateRange: DateRange = '30d',
  filters?: {
    supplier?: string
    category?: string
    item?: string
  }
): Promise<TrendData> {
  const params = new URLSearchParams()
  params.append('type', type)
  if (venueId) params.append('venue_id', venueId)
  params.append('date_range', dateRange)
  if (filters?.supplier) params.append('supplier', filters.supplier)
  if (filters?.category) params.append('category', filters.category)
  if (filters?.item) params.append('item', filters.item)

  const key = `trends:${type}:${venueId}:${dateRange}:${JSON.stringify(filters)}`
  try {
    return await cachedFetch(key, async () => {
      const response = await fetch(`${API_BASE_URL}/api/dashboard/trends?${params.toString()}`)
      if (!response.ok) {
        const errorText = await response.text()
        console.error(`Failed to fetch trends: ${response.status} ${errorText}`)
        throw new Error(`Failed to fetch trends: ${response.statusText}`)
      }
      const data = await response.json()
      console.log('Fetched trends:', data)
      return data
    })
  } catch (e) {
    console.error('Error fetching trends, using fallback:', e)
    // Generate mock data for testing
    const days = dateRange === '7d' ? 7 : dateRange === '30d' ? 30 : dateRange === '180d' ? 180 : 365
    const data: TrendDataPoint[] = []
    for (let i = 0; i < days; i++) {
      const date = new Date()
      date.setDate(date.getDate() - (days - i))
      data.push({
        date: date.toISOString().split('T')[0],
        value: type === 'spend' ? 1000 + Math.random() * 500 : type === 'matchRate' ? 80 + Math.random() * 15 : Math.random() * 20,
      })
    }
    return { data, forecast: [], unit: type === 'spend' ? 'GBP' : '%' }
  }
}

/**
 * Fetch unmatched delivery notes
 */
export async function fetchUnmatchedDNs(
  venueId?: string
): Promise<UnmatchedDN[]> {
  const params = new URLSearchParams()
  if (venueId) params.append('venue_id', venueId)

  const key = `unmatched-dns:${venueId}`
  try {
    return await cachedFetch(key, async () => {
      const response = await fetch(`${API_BASE_URL}/api/dashboard/unmatched-dns?${params.toString()}`)
      if (!response.ok) {
        const errorText = await response.text()
        console.error(`Failed to fetch unmatched DNs: ${response.status} ${errorText}`)
        throw new Error(`Failed to fetch unmatched DNs: ${response.statusText}`)
      }
      const data = await response.json()
      console.log('Fetched unmatched DNs:', data)
      return data.deliveryNotes || []
    })
  } catch (e) {
    console.error('Error fetching unmatched DNs, using fallback:', e)
    return []
  }
}

/**
 * Fetch recent activity/audit log
 */
export async function fetchActivity(
  venueId?: string,
  limit: number = 20
): Promise<ActivityItem[]> {
  const params = new URLSearchParams()
  if (venueId) params.append('venue_id', venueId)
  params.append('limit', limit.toString())

  const key = `activity:${venueId}:${limit}`
  try {
    return await cachedFetch(key, async () => {
      const response = await fetch(`${API_BASE_URL}/api/dashboard/activity?${params.toString()}`)
      if (!response.ok) {
        const errorText = await response.text()
        console.error(`Failed to fetch activity: ${response.status} ${errorText}`)
        throw new Error(`Failed to fetch activity: ${response.statusText}`)
      }
      const data = await response.json()
      console.log('Fetched activity:', data)
      return data.activities || []
    })
  } catch (e) {
    console.error('Error fetching activity, using fallback:', e)
    return []
  }
}

/**
 * Resolve a mismatch action
 */
export async function resolveMismatch(
  actionId: string,
  creditAmount?: number
): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/api/dashboard/actions/${actionId}/resolve`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ creditAmount }),
  })
  if (!response.ok) {
    throw new Error(`Failed to resolve mismatch: ${response.statusText}`)
  }
  clearCache() // Clear all cache on action
}

/**
 * Pair a delivery note with an invoice
 */
export async function pairDeliveryNote(
  dnId: string,
  invoiceId: string
): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/api/dashboard/pair`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ deliveryNoteId: dnId, invoiceId }),
  })
  if (!response.ok) {
    throw new Error(`Failed to pair delivery note: ${response.statusText}`)
  }
  clearCache() // Clear all cache on action
}

/**
 * Submit a batch of ready invoices
 */
export async function submitBatch(invoiceIds: string[]): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/api/dashboard/submit-batch`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ invoiceIds }),
  })
  if (!response.ok) {
    throw new Error(`Failed to submit batch: ${response.statusText}`)
  }
  clearCache() // Clear all cache on action
}

