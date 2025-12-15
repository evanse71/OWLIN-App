/**
 * Dashboard Filters Context
 * Global filters for venue and date range with <100ms propagation
 */

import { createContext, useContext, useState, useCallback, ReactNode, useEffect } from 'react'
import type { DateRange } from '../lib/dashboardApi'

interface DashboardFilters {
  venueId: string | null
  dateRange: DateRange
  searchQuery: string
}

interface DashboardFiltersContextValue {
  filters: DashboardFilters
  setVenue: (venueId: string | null) => void
  setDateRange: (range: DateRange) => void
  setSearchQuery: (query: string) => void
  resetFilters: () => void
}

const DashboardFiltersContext = createContext<DashboardFiltersContextValue | undefined>(undefined)

const DEFAULT_FILTERS: DashboardFilters = {
  venueId: null,
  dateRange: '30d',
  searchQuery: '',
}

export function DashboardFiltersProvider({ children }: { children: ReactNode }) {
  // Load from localStorage on mount
  const [filters, setFilters] = useState<DashboardFilters>(() => {
    try {
      const stored = localStorage.getItem('dashboardFilters')
      if (stored) {
        return { ...DEFAULT_FILTERS, ...JSON.parse(stored) }
      }
    } catch (e) {
      console.warn('Failed to load dashboard filters from localStorage', e)
    }
    return DEFAULT_FILTERS
  })

  // Persist to localStorage on change
  useEffect(() => {
    try {
      localStorage.setItem('dashboardFilters', JSON.stringify(filters))
    } catch (e) {
      console.warn('Failed to save dashboard filters to localStorage', e)
    }
  }, [filters])

  const setVenue = useCallback((venueId: string | null) => {
    setFilters((prev) => ({ ...prev, venueId }))
  }, [])

  const setDateRange = useCallback((dateRange: DateRange) => {
    setFilters((prev) => ({ ...prev, dateRange }))
  }, [])

  const setSearchQuery = useCallback((searchQuery: string) => {
    setFilters((prev) => ({ ...prev, searchQuery }))
  }, [])

  const resetFilters = useCallback(() => {
    setFilters(DEFAULT_FILTERS)
  }, [])

  return (
    <DashboardFiltersContext.Provider
      value={{
        filters,
        setVenue,
        setDateRange,
        setSearchQuery,
        resetFilters,
      }}
    >
      {children}
    </DashboardFiltersContext.Provider>
  )
}

export function useDashboardFilters() {
  const context = useContext(DashboardFiltersContext)
  if (!context) {
    throw new Error('useDashboardFilters must be used within DashboardFiltersProvider')
  }
  return context
}

