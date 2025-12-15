/**
 * Waste Module Hooks
 * Mocked API hooks for waste tracking - TODO: Replace with real backend API calls
 * 
 * ACTIVE FRONTEND: frontend_clean (served on port 5176)
 * Routing: React Router in App.tsx
 * These hooks provide mocked data until backend endpoints are implemented
 */

import { useState, useEffect, useCallback } from 'react'
import type {
  WasteEntry,
  WasteReason,
  WasteItemType,
  DateRange,
  WasteFilters,
  ProductWaste,
  MealWaste,
  SupplierImpact,
  MarginImpact,
  WasteInsights
} from '../types/waste'

// Re-export all types for convenience
export type {
  WasteEntry,
  WasteReason,
  WasteItemType,
  DateRange,
  WasteFilters,
  ProductWaste,
  MealWaste,
  SupplierImpact,
  MarginImpact,
  WasteInsights
}

// Mock data generators
const generateMockWasteEntries = (count: number = 20): WasteEntry[] => {
  const reasons: WasteReason[] = ['spoilage', 'overcooked', 'customer-return', 'over-portion', 'prep-error', 'storage-issue', 'delivery-quality']
  const itemTypes: WasteItemType[] = ['meal', 'ingredient', 'prep']
  const venues = ['Waterloo', 'Royal Oak Hotel', 'Main Restaurant']
  const staffMembers = ['John Smith', 'Sarah Johnson', 'Mike Brown', 'Emma Wilson', 'David Lee']
  const items = [
    'Chicken Breast 5kg', 'Carling Keg 11g', 'Fish & Chips', 'Beef Burger', 'Caesar Salad',
    'Pasta Carbonara', 'Tomato Soup', 'Bread Loaf', 'Milk 4L', 'Cheese Block',
    'Lamb Shank', 'Salmon Fillet', 'Rice 10kg', 'Potatoes 25kg', 'Onions 5kg'
  ]
  
  const entries: WasteEntry[] = []
  const now = new Date()
  
  for (let i = 0; i < count; i++) {
    const daysAgo = Math.floor(Math.random() * 30)
    const timestamp = new Date(now.getTime() - daysAgo * 24 * 60 * 60 * 1000)
    const quantity = Math.random() * 10 + 1
    const unit = ['kg', 'g', 'L', 'portion', 'keg', 'crate'][Math.floor(Math.random() * 6)]
    const costLost = Math.random() * 500 + 10
    
    entries.push({
      id: `waste-${i + 1}`,
      itemName: items[Math.floor(Math.random() * items.length)],
      itemType: itemTypes[Math.floor(Math.random() * itemTypes.length)],
      quantity: Math.round(quantity * 10) / 10,
      unit,
      costLost: Math.round(costLost * 100) / 100,
      reason: reasons[Math.floor(Math.random() * reasons.length)],
      staffMember: staffMembers[Math.floor(Math.random() * staffMembers.length)],
      venue: venues[Math.floor(Math.random() * venues.length)],
      timestamp: timestamp.toISOString(),
      note: Math.random() > 0.7 ? 'Additional notes about this waste entry' : undefined
    })
  }
  
  return entries.sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime())
}

const generateMockInsights = (): WasteInsights => {
  const trendData: Array<{ date: string; value: number }> = []
  const now = new Date()
  for (let i = 29; i >= 0; i--) {
    const date = new Date(now.getTime() - i * 24 * 60 * 60 * 1000)
    trendData.push({
      date: date.toISOString().split('T')[0],
      value: Math.random() * 500 + 200
    })
  }
  
  return {
    wastePercentage: 6.4,
    totalCostLost: 12450.75,
    topCategory: 'Ingredients',
    staffAttribution: 'John Smith (32%)',
    productBreakdown: [
      { productName: 'Chicken Breast 5kg', wastePercentage: 6.4, costLost: 3120, productId: 'prod-1' },
      { productName: 'Carling Keg 11g', wastePercentage: 3.1, costLost: 1260, productId: 'prod-2' },
      { productName: 'Fish & Chips', wastePercentage: 5.2, costLost: 980, productId: 'prod-3' },
      { productName: 'Beef Burger', wastePercentage: 4.8, costLost: 750, productId: 'prod-4' },
      { productName: 'Caesar Salad', wastePercentage: 3.9, costLost: 620, productId: 'prod-5' }
    ],
    mealBreakdown: [
      { mealName: 'Fish & Chips', wasteEntriesCount: 12, totalCostLost: 980 },
      { mealName: 'Beef Burger', wasteEntriesCount: 8, totalCostLost: 750 },
      { mealName: 'Caesar Salad', wasteEntriesCount: 6, totalCostLost: 620 },
      { mealName: 'Pasta Carbonara', wasteEntriesCount: 5, totalCostLost: 450 }
    ],
    supplierImpact: [
      { supplierName: 'Supplier A', wasteCost: 3200, wastePercentage: 4.2, isAboveThreshold: false },
      { supplierName: 'Supplier B', wasteCost: 5800, wastePercentage: 8.1, isAboveThreshold: true },
      { supplierName: 'Supplier C', wasteCost: 2100, wastePercentage: 3.5, isAboveThreshold: false }
    ],
    marginImpact: {
      foodCostTarget: 30,
      actualCostWithWaste: 33.4,
      lostMargin: -3.4,
      amountNeededToReturnToTarget: 12450.75
    },
    trendData
  }
}

/**
 * Hook to fetch waste log entries
 * TODO: Replace with real API call to GET /api/waste/entries
 */
export function useWasteLog(
  filters: WasteFilters = {},
  dateRange: DateRange = '30d'
): { data: WasteEntry[]; loading: boolean; error: string | null } {
  const [data, setData] = useState<WasteEntry[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  
  useEffect(() => {
    // TODO: Replace with actual API call
    // const fetchWasteLog = async () => {
    //   try {
    //     const response = await fetch(`${API_BASE_URL}/api/waste/entries?dateRange=${dateRange}&...`)
    //     const result = await response.json()
    //     setData(result.entries)
    //   } catch (err) {
    //     setError(err.message)
    //   } finally {
    //     setLoading(false)
    //   }
    // }
    // fetchWasteLog()
    
    // Mock implementation
    setLoading(true)
    setTimeout(() => {
      let entries = generateMockWasteEntries(25)
      
      // Apply filters
      if (filters.category && filters.category !== 'all') {
        entries = entries.filter(e => e.itemType === filters.category)
      }
      if (filters.reason && filters.reason !== 'all') {
        entries = entries.filter(e => e.reason === filters.reason)
      }
      if (filters.staffMember && filters.staffMember !== 'all') {
        entries = entries.filter(e => e.staffMember === filters.staffMember)
      }
      if (filters.searchQuery) {
        const query = filters.searchQuery.toLowerCase()
        entries = entries.filter(e => 
          e.itemName.toLowerCase().includes(query) ||
          e.venue.toLowerCase().includes(query) ||
          e.staffMember.toLowerCase().includes(query)
        )
      }
      
      setData(entries)
      setLoading(false)
    }, 300)
  }, [filters, dateRange])
  
  return { data, loading, error }
}

/**
 * Hook to fetch waste insights and analytics
 * TODO: Replace with real API call to GET /api/waste/insights
 */
export function useWasteInsights(
  dateRange: DateRange = '30d',
  venueId?: string | null
): { data: WasteInsights | null; loading: boolean; error: string | null } {
  const [data, setData] = useState<WasteInsights | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  
  useEffect(() => {
    // TODO: Replace with actual API call
    // const fetchInsights = async () => {
    //   try {
    //     const response = await fetch(`${API_BASE_URL}/api/waste/insights?dateRange=${dateRange}&venueId=${venueId || ''}`)
    //     const result = await response.json()
    //     setData(result)
    //   } catch (err) {
    //     setError(err.message)
    //   } finally {
    //     setLoading(false)
    //   }
    // }
    // fetchInsights()
    
    // Mock implementation
    setLoading(true)
    setTimeout(() => {
      setData(generateMockInsights())
      setLoading(false)
    }, 400)
  }, [dateRange, venueId])
  
  return { data, loading, error }
}

/**
 * Hook to record new waste entry
 * TODO: Replace with real API call to POST /api/waste/entries
 */
export function useRecordWaste() {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  
  const recordWaste = useCallback(async (wasteData: {
    itemName: string
    itemType: WasteItemType
    quantity: number
    unit: string
    reason: WasteReason
    staffMember: string
    venue: string
    note?: string
  }): Promise<WasteEntry> => {
    setLoading(true)
    setError(null)
    
    // TODO: Replace with actual API call
    // try {
    //   const response = await fetch(`${API_BASE_URL}/api/waste/entries`, {
    //     method: 'POST',
    //     headers: { 'Content-Type': 'application/json' },
    //     body: JSON.stringify(wasteData)
    //   })
    //   const result = await response.json()
    //   return result.entry
    // } catch (err) {
    //   setError(err.message)
    //   throw err
    // } finally {
    //   setLoading(false)
    // }
    
    // Mock implementation
    return new Promise((resolve) => {
      setTimeout(() => {
        const mockEntry: WasteEntry = {
          id: `waste-${Date.now()}`,
          ...wasteData,
          costLost: Math.random() * 500 + 10, // Mock cost calculation
          timestamp: new Date().toISOString()
        }
        setLoading(false)
        resolve(mockEntry)
      }, 500)
    })
  }, [])
  
  return { recordWaste, loading, error }
}
