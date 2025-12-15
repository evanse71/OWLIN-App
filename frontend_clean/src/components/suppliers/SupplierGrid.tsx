/**
 * Supplier Grid Component
 * Grid container for supplier cards with sorting
 */

import { ArrowUpDown, DollarSign, ArrowUpAZ, Clock } from 'lucide-react'
import { SupplierCard } from './SupplierCard'
import type { SupplierListItem } from '../../lib/suppliersApi'
import './SupplierGrid.css'

interface SupplierGridProps {
  suppliers: SupplierListItem[]
  selectedSupplierId: string | null
  onSelectSupplier: (supplierId: string | null) => void
  sortBy: 'risk' | 'spend' | 'name' | 'recent'
  onSortChange: (sort: 'risk' | 'spend' | 'name' | 'recent') => void
  loading: boolean
  currentRole: 'GM' | 'Finance' | 'ShiftLead'
}

export function SupplierGrid({
  suppliers,
  selectedSupplierId,
  onSelectSupplier,
  sortBy,
  onSortChange,
  loading,
  currentRole,
}: SupplierGridProps) {
  if (loading) {
    return (
      <div className="supplier-grid">
        <div className="supplier-grid-loading">Loading suppliers...</div>
      </div>
    )
  }

  if (suppliers.length === 0) {
    return (
      <div className="supplier-grid">
        <div className="supplier-grid-empty">
          <h3>No suppliers found</h3>
          <p>Try adjusting your filters or search query</p>
        </div>
      </div>
    )
  }

  return (
    <div className="supplier-grid">
      <div className="supplier-grid-header">
        <div className="supplier-grid-title">
          {suppliers.length} {suppliers.length === 1 ? 'Supplier' : 'Suppliers'}
        </div>
        <div className="supplier-grid-sort">
          <span className="supplier-grid-sort-label">Sort:</span>
          <div className="supplier-grid-sort-buttons">
            <button
              className={`supplier-grid-sort-button ${
                sortBy === 'risk' ? 'active' : ''
              }`}
              onClick={() => onSortChange('risk')}
              title="Sort by risk (spend × issue rate)"
            >
              <ArrowUpDown size={14} />
              Risk
            </button>
            <button
              className={`supplier-grid-sort-button ${
                sortBy === 'spend' ? 'active' : ''
              }`}
              onClick={() => onSortChange('spend')}
              title="Sort by total spend"
            >
              <DollarSign size={14} />
              Spend
            </button>
            <button
              className={`supplier-grid-sort-button ${
                sortBy === 'name' ? 'active' : ''
              }`}
              onClick={() => onSortChange('name')}
              title="Sort alphabetically"
            >
              <ArrowUpAZ size={14} />
              A-Z
            </button>
            <button
              className={`supplier-grid-sort-button ${
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
      </div>

      <div className="supplier-grid-cards">
        {suppliers.map((supplier) => (
          <SupplierCard
            key={supplier.id}
            supplier={supplier}
            isSelected={selectedSupplierId === supplier.id}
            onClick={() =>
              onSelectSupplier(
                selectedSupplierId === supplier.id ? null : supplier.id
              )
            }
            currentRole={currentRole}
          />
        ))}
      </div>
    </div>
  )
}

