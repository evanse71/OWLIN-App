/**
 * Suppliers Header Component
 * Header with search, filters, and summary tiles
 */

import { Search, X, ArrowUpDown, DollarSign, ArrowUpAZ, Clock, Sparkles } from 'lucide-react'
import type { SupplierCategory, SupplierRiskLevel, SupplierStatus } from '../../lib/suppliersApi'
import './SuppliersHeader.css'

interface SuppliersHeaderProps {
  searchQuery: string
  onSearchChange: (query: string) => void
  categoryFilter: string | null
  onCategoryFilterChange: (category: string | null) => void
  riskFilter: string | null
  onRiskFilterChange: (risk: string | null) => void
  statusFilter: string | null
  onStatusFilterChange: (status: string | null) => void
  sortBy: 'risk' | 'spend' | 'name' | 'recent'
  onSortChange: (sort: 'risk' | 'spend' | 'name' | 'recent') => void
  summaryStats: {
    totalSpend: number
    activeCount: number
    avgScore: number
  }
  currentRole: 'GM' | 'Finance' | 'ShiftLead'
}

const CATEGORIES: SupplierCategory[] = ['Food', 'Beverage', 'Utilities', 'Other']
const RISK_LEVELS: SupplierRiskLevel[] = ['High', 'Medium', 'Low']
const STATUSES: SupplierStatus[] = ['Active', 'On Watch', 'Blocked']

export function SuppliersHeader({
  searchQuery,
  onSearchChange,
  categoryFilter,
  onCategoryFilterChange,
  riskFilter,
  onRiskFilterChange,
  statusFilter,
  onStatusFilterChange,
  sortBy,
  onSortChange,
  summaryStats,
  currentRole,
}: SuppliersHeaderProps) {
  const hasActiveFilters =
    categoryFilter || riskFilter || statusFilter || searchQuery

  const clearFilters = () => {
    onSearchChange('')
    onCategoryFilterChange(null)
    onRiskFilterChange(null)
    onStatusFilterChange(null)
  }

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('en-GB', {
      style: 'currency',
      currency: 'GBP',
      maximumFractionDigits: 0,
    }).format(value)
  }

  const getScoreLabel = (score: number) => {
    if (score >= 4.5) return 'A'
    if (score >= 3.5) return 'B'
    if (score >= 2.5) return 'C'
    if (score >= 1.5) return 'D'
    return 'E'
  }

  return (
    <div className="suppliers-header">
      {/* Row 1: Title + Search + Assistant */}
      <div className="suppliers-header-row-1">
        <div className="suppliers-header-title-section">
          <h1 className="suppliers-header-title">Suppliers</h1>
          <p className="suppliers-header-subtitle">
            Manage supplier relationships and monitor performance
          </p>
        </div>

        <div className="suppliers-header-row-1-right">
          {/* Search Bar */}
          <div className="suppliers-header-search">
            <Search size={18} className="suppliers-header-search-icon" />
            <input
              type="text"
              placeholder="Search suppliers..."
              value={searchQuery}
              onChange={(e) => onSearchChange(e.target.value)}
              className="suppliers-header-search-input"
            />
            {searchQuery && (
              <button
                onClick={() => onSearchChange('')}
                className="suppliers-header-search-clear"
                aria-label="Clear search"
              >
                <X size={16} />
              </button>
            )}
          </div>

          {/* Assistant Indicator */}
          <div className="suppliers-header-assistant-chip">
            <Sparkles size={14} />
            <span>Owlin Assistant</span>
          </div>
        </div>
      </div>

      {/* Row 2: KPI Cards */}
      <div className="suppliers-header-row-2">
        <div className="suppliers-summary-tile">
          <div className="suppliers-summary-tile-label">Total Spend</div>
          <div className="suppliers-summary-tile-value">
            {formatCurrency(summaryStats.totalSpend)}
          </div>
        </div>

        <div className="suppliers-summary-tile">
          <div className="suppliers-summary-tile-label">Active Suppliers</div>
          <div className="suppliers-summary-tile-value">
            {summaryStats.activeCount}
          </div>
        </div>

        <div className="suppliers-summary-tile">
          <div className="suppliers-summary-tile-label">Avg Score</div>
          <div className="suppliers-summary-tile-value">
            {getScoreLabel(summaryStats.avgScore)}
          </div>
        </div>
      </div>

      {/* Row 3: Filters + Sort + Clear */}
      <div className="suppliers-header-row-3">
        <div className="suppliers-header-filters">
          <div className="suppliers-header-filter-group">
            <span className="suppliers-header-filter-label">Category:</span>
            <div className="suppliers-header-filter-chips">
              {CATEGORIES.map((cat) => (
                <button
                  key={cat}
                  className={`suppliers-header-filter-chip ${
                    categoryFilter === cat ? 'active' : ''
                  }`}
                  onClick={() =>
                    onCategoryFilterChange(categoryFilter === cat ? null : cat)
                  }
                >
                  {cat}
                </button>
              ))}
            </div>
          </div>

          <div className="suppliers-header-filter-group">
            <span className="suppliers-header-filter-label">Risk:</span>
            <div className="suppliers-header-filter-chips">
              {RISK_LEVELS.map((risk) => (
                <button
                  key={risk}
                  className={`suppliers-header-filter-chip ${
                    riskFilter === risk ? 'active' : ''
                  }`}
                  onClick={() =>
                    onRiskFilterChange(riskFilter === risk ? null : risk)
                  }
                >
                  {risk}
                </button>
              ))}
            </div>
          </div>

          <div className="suppliers-header-filter-group">
            <span className="suppliers-header-filter-label">Status:</span>
            <div className="suppliers-header-filter-chips">
              {STATUSES.map((status) => (
                <button
                  key={status}
                  className={`suppliers-header-filter-chip ${
                    statusFilter === status ? 'active' : ''
                  }`}
                  onClick={() =>
                    onStatusFilterChange(statusFilter === status ? null : status)
                  }
                >
                  {status}
                </button>
              ))}
            </div>
          </div>
        </div>

        <div className="suppliers-header-sort-controls">
          <span className="suppliers-header-sort-label">Sort by:</span>
          <div className="suppliers-header-sort-buttons">
            <button
              className={`suppliers-header-sort-button ${
                sortBy === 'risk' ? 'active' : ''
              }`}
              onClick={() => onSortChange('risk')}
              title="Sort by risk"
            >
              <ArrowUpDown size={14} />
              Risk
            </button>
            <button
              className={`suppliers-header-sort-button ${
                sortBy === 'spend' ? 'active' : ''
              }`}
              onClick={() => onSortChange('spend')}
              title="Sort by total spend"
            >
              <DollarSign size={14} />
              Spend
            </button>
            <button
              className={`suppliers-header-sort-button ${
                sortBy === 'name' ? 'active' : ''
              }`}
              onClick={() => onSortChange('name')}
              title="Sort alphabetically"
            >
              <ArrowUpAZ size={14} />
              Name
            </button>
            <button
              className={`suppliers-header-sort-button ${
                sortBy === 'recent' ? 'active' : ''
              }`}
              onClick={() => onSortChange('recent')}
              title="Sort by most recent activity"
            >
              <Clock size={14} />
              Recent
            </button>
          </div>
        </div>

        {hasActiveFilters && (
          <button
            onClick={clearFilters}
            className="suppliers-header-clear-filters"
          >
            Clear filters
          </button>
        )}
      </div>
    </div>
  )
}

