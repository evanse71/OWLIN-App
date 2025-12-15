/**
 * Supplier List Component
 * Grid container for supplier cards with pagination
 */

import { ChevronLeft, ChevronRight } from 'lucide-react'
import { SupplierCard } from './SupplierCard'
import type { SupplierListItem } from '../../lib/suppliersApi'
import './SupplierList.css'

interface SupplierListProps {
  suppliers: SupplierListItem[]
  selectedSupplierId: string | null
  onSelectSupplier: (supplierId: string | null) => void
  page: number
  pageCount: number
  onPageChange: (page: number) => void
  loading: boolean
  currentRole: 'GM' | 'Finance' | 'ShiftLead'
}

export function SupplierList({
  suppliers,
  selectedSupplierId,
  onSelectSupplier,
  page,
  pageCount,
  onPageChange,
  loading,
  currentRole,
}: SupplierListProps) {
  if (loading) {
    return (
      <div className="supplier-list">
        <div className="supplier-list-loading">Loading suppliers...</div>
      </div>
    )
  }

  if (suppliers.length === 0) {
    return (
      <div className="supplier-list">
        <div className="supplier-list-empty">
          <h3>No suppliers found</h3>
          <p>Try adjusting your filters or search query</p>
        </div>
      </div>
    )
  }

  return (
    <div className="supplier-list">
      <div className="supplier-list-header">
        <div className="supplier-list-title">
          {suppliers.length} {suppliers.length === 1 ? 'Supplier' : 'Suppliers'}
        </div>
      </div>

      <div className="supplier-list-grid">
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

      {pageCount > 1 && (
        <div className="supplier-list-pagination">
          <button
            className="supplier-list-pagination-button"
            onClick={() => onPageChange(page - 1)}
            disabled={page === 1}
            aria-label="Previous page"
          >
            <ChevronLeft size={16} />
          </button>
          <span className="supplier-list-pagination-info">
            Page {page} of {pageCount}
          </span>
          <button
            className="supplier-list-pagination-button"
            onClick={() => onPageChange(page + 1)}
            disabled={page === pageCount}
            aria-label="Next page"
          >
            <ChevronRight size={16} />
          </button>
        </div>
      )}
    </div>
  )
}

