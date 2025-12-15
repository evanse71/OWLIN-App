/**
 * Suppliers Page
 * Main supplier management page with grid and detail panel
 */

import { useState, useEffect, useCallback } from 'react'
import { useSearchParams } from 'react-router-dom'
import { DashboardFiltersProvider, useDashboardFilters } from '../contexts/DashboardFiltersContext'
import { AppHeader } from '../components/layout/AppHeader'
import { SuppliersHeader } from '../components/suppliers/SuppliersHeader'
import { SupplierList } from '../components/suppliers/SupplierList'
import { SupplierDetailPanel } from '../components/suppliers/SupplierDetailPanel'
import {
  fetchSuppliersList,
  fetchSupplierDetail,
  type SupplierListItem,
  type SupplierDetail,
} from '../lib/suppliersApi'
import './Suppliers.css'

// Mock role - in real app this would come from auth context
const currentRole: 'GM' | 'Finance' | 'ShiftLead' = 'GM'

function SuppliersContent() {
  console.log('[Suppliers] SuppliersContent rendering')
  const [searchParams, setSearchParams] = useSearchParams()
  const { filters } = useDashboardFilters()
  
  const [suppliers, setSuppliers] = useState<SupplierListItem[]>([])
  const [selectedSupplierId, setSelectedSupplierId] = useState<string | null>(
    searchParams.get('id') || null
  )
  const [selectedSupplierDetail, setSelectedSupplierDetail] = useState<SupplierDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [loadingDetail, setLoadingDetail] = useState(false)
  
  // Filters
  const [searchQuery, setSearchQuery] = useState('')
  const [categoryFilter, setCategoryFilter] = useState<string | null>(null)
  const [riskFilter, setRiskFilter] = useState<string | null>(null)
  const [statusFilter, setStatusFilter] = useState<string | null>(null)
  const [sortBy, setSortBy] = useState<'risk' | 'spend' | 'name' | 'recent'>('risk')
  
  // Pagination
  const [page, setPage] = useState(1)
  const pageSize = 30
  
  // Tab selection for detail panel
  const [activeTab, setActiveTab] = useState<string>(
    searchParams.get('tab') || 'overview'
  )

  // Load suppliers list
  useEffect(() => {
    let mounted = true

    async function loadSuppliers() {
      setLoading(true)
      try {
        const data = await fetchSuppliersList(
          filters.venueId || undefined,
          filters.dateRange
        )
        if (mounted) {
          setSuppliers(data)
        }
      } catch (e) {
        console.error('Failed to load suppliers:', e)
        if (mounted) {
          setSuppliers([])
        }
      } finally {
        if (mounted) {
          setLoading(false)
        }
      }
    }

    loadSuppliers()
    return () => {
      mounted = false
    }
  }, [filters.venueId, filters.dateRange])

  // Load supplier detail when selected
  useEffect(() => {
    if (!selectedSupplierId) {
      setSelectedSupplierDetail(null)
      return
    }

    let mounted = true

    async function loadDetail() {
      setLoadingDetail(true)
      try {
        const detail = await fetchSupplierDetail(selectedSupplierId)
        if (mounted) {
          setSelectedSupplierDetail(detail)
        }
      } catch (e) {
        console.error('Failed to load supplier detail:', e)
        if (mounted) {
          setSelectedSupplierDetail(null)
        }
      } finally {
        if (mounted) {
          setLoadingDetail(false)
        }
      }
    }

    loadDetail()
    return () => {
      mounted = false
    }
  }, [selectedSupplierId])

  // Update URL when selection changes
  useEffect(() => {
    if (selectedSupplierId) {
      const params = new URLSearchParams()
      params.set('id', selectedSupplierId)
      if (activeTab !== 'overview') {
        params.set('tab', activeTab)
      }
      setSearchParams(params, { replace: true })
    } else {
      setSearchParams({}, { replace: true })
    }
  }, [selectedSupplierId, activeTab, setSearchParams])

  // Handle supplier selection
  const handleSelectSupplier = useCallback((supplierId: string | null) => {
    setSelectedSupplierId(supplierId)
    if (supplierId) {
      setActiveTab('overview') // Reset to overview when selecting new supplier
    }
  }, [])

  // Filter and sort suppliers
  const filteredSuppliers = suppliers.filter((supplier) => {
    // Search filter
    if (searchQuery) {
      const query = searchQuery.toLowerCase()
      if (
        !supplier.name.toLowerCase().includes(query) &&
        !supplier.id.toLowerCase().includes(query)
      ) {
        return false
      }
    }

    // Category filter
    if (categoryFilter && supplier.category !== categoryFilter) {
      return false
    }

    // Risk filter (based on score)
    if (riskFilter) {
      const scoreRisk: Record<string, string[]> = {
        High: ['D', 'E'],
        Medium: ['C'],
        Low: ['A', 'B'],
      }
      if (!scoreRisk[riskFilter]?.includes(supplier.score)) {
        return false
      }
    }

    // Status filter
    if (statusFilter && supplier.status !== statusFilter) {
      return false
    }

    return true
  })

  // Sort suppliers
  const sortedSuppliers = [...filteredSuppliers].sort((a, b) => {
    switch (sortBy) {
      case 'spend':
        return b.totalSpend - a.totalSpend
      case 'name':
        return a.name.localeCompare(b.name)
      case 'recent':
        const aDate = a.lastInvoiceDate ? new Date(a.lastInvoiceDate).getTime() : 0
        const bDate = b.lastInvoiceDate ? new Date(b.lastInvoiceDate).getTime() : 0
        return bDate - aDate
      case 'risk':
      default:
        // Risk: High → Medium → Low (map scores: D/E = High, C = Medium, A/B = Low)
        const riskOrder: Record<string, number> = { E: 3, D: 3, C: 2, B: 1, A: 1 }
        const aRiskOrder = riskOrder[a.score] || 0
        const bRiskOrder = riskOrder[b.score] || 0
        if (aRiskOrder !== bRiskOrder) {
          return bRiskOrder - aRiskOrder // Higher risk first
        }
        // If same risk level, sort by impact (spend × issue rate)
        const aRisk = a.totalSpend * (a.mismatchRate / 100)
        const bRisk = b.totalSpend * (b.mismatchRate / 100)
        return bRisk - aRisk
    }
  })

  // Pagination
  const pageCount = Math.ceil(sortedSuppliers.length / pageSize)
  const paginatedSuppliers = sortedSuppliers.slice(
    (page - 1) * pageSize,
    page * pageSize
  )

  // Reset to page 1 when filters change
  useEffect(() => {
    setPage(1)
  }, [searchQuery, categoryFilter, riskFilter, statusFilter, sortBy])

  // Calculate summary stats
  const summaryStats = {
    totalSpend: suppliers.reduce((sum, s) => sum + s.totalSpend, 0),
    activeCount: suppliers.filter((s) => s.status === 'Active').length,
    avgScore: suppliers.length > 0
      ? suppliers.reduce((sum, s) => {
          const scoreValues: Record<string, number> = { A: 5, B: 4, C: 3, D: 2, E: 1 }
          return sum + (scoreValues[s.score] || 0)
        }, 0) / suppliers.length
      : 0,
  }

  return (
    <div className="suppliers-page">
      {/* Suppliers Page - Full Implementation */}
      <AppHeader>
        <SuppliersHeader
          searchQuery={searchQuery}
          onSearchChange={setSearchQuery}
          categoryFilter={categoryFilter}
          onCategoryFilterChange={setCategoryFilter}
          riskFilter={riskFilter}
          onRiskFilterChange={setRiskFilter}
          statusFilter={statusFilter}
          onStatusFilterChange={setStatusFilter}
          sortBy={sortBy}
          onSortChange={setSortBy}
          summaryStats={summaryStats}
          currentRole={currentRole}
        />
      </AppHeader>

      <div className="suppliers-main">
        {/* Left Column - Supplier List */}
        <div className="suppliers-grid-column">
          <SupplierList
            suppliers={paginatedSuppliers}
            selectedSupplierId={selectedSupplierId}
            onSelectSupplier={handleSelectSupplier}
            page={page}
            pageCount={pageCount}
            onPageChange={setPage}
            loading={loading}
            currentRole={currentRole}
          />
        </div>

        {/* Right Column - Detail Panel */}
        <div className="suppliers-detail-column">
          {selectedSupplierId && selectedSupplierDetail ? (
            <SupplierDetailPanel
              supplier={selectedSupplierDetail}
              supplierId={selectedSupplierId}
              activeTab={activeTab}
              onTabChange={setActiveTab}
              loading={loadingDetail}
              currentRole={currentRole}
            />
          ) : (
            <div className="suppliers-empty-detail">
              <div className="suppliers-empty-detail-content">
                <h3>Select a Supplier</h3>
                <p>Click on a supplier card to view detailed information</p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export function Suppliers() {
  console.log('[Suppliers] Component rendering')
  return (
    <DashboardFiltersProvider>
      <SuppliersContent />
    </DashboardFiltersProvider>
  )
}

