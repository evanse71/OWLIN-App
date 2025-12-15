/**
 * Supplier Card Component
 * Individual supplier card for the grid
 */

import { useState } from 'react'
import { TrendingUp, Clock, AlertTriangle } from 'lucide-react'
import type { SupplierListItem } from '../../lib/suppliersApi'
import './SupplierCard.css'

interface SupplierCardProps {
  supplier: SupplierListItem
  isSelected: boolean
  onClick: () => void
  currentRole: 'GM' | 'Finance' | 'ShiftLead'
}

export function SupplierCard({
  supplier,
  isSelected,
  onClick,
  currentRole,
}: SupplierCardProps) {
  const [isHovered, setIsHovered] = useState(false)

  const getScoreColor = (score: string) => {
    switch (score) {
      case 'A':
        return 'green'
      case 'B':
        return 'blue'
      case 'C':
        return 'amber'
      case 'D':
        return 'orange'
      case 'E':
        return 'red'
      default:
        return 'gray'
    }
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'Active':
        return 'green'
      case 'On Watch':
        return 'amber'
      case 'Blocked':
        return 'red'
      default:
        return 'gray'
    }
  }

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('en-GB', {
      style: 'currency',
      currency: 'GBP',
      maximumFractionDigits: 0,
    }).format(value)
  }

  const getInitial = (name: string) => {
    return name.charAt(0).toUpperCase()
  }

  const scoreColor = getScoreColor(supplier.score)
  const statusColor = getStatusColor(supplier.status)

  return (
    <div
      className={`supplier-card ${isSelected ? 'selected' : ''} ${
        isHovered ? 'hovered' : ''
      }`}
      onClick={onClick}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault()
          onClick()
        }
      }}
    >
      {/* Top row: Avatar + Name + Grade */}
      <div className="supplier-card-top-row">
        <div className={`supplier-card-avatar-initial supplier-card-avatar-${scoreColor}`}>
          {getInitial(supplier.name)}
        </div>
        <div className="supplier-card-name">{supplier.name}</div>
        <div className={`supplier-card-grade supplier-card-grade-${scoreColor}`}>
          {supplier.score}
        </div>
      </div>

      {/* Middle row: Metrics */}
      <div className="supplier-card-metrics-row">
        <div className="supplier-card-metric">
          <AlertTriangle size={12} />
          <span className="supplier-card-metric-value">
            {supplier.matchRate?.toFixed(0) || (100 - supplier.mismatchRate).toFixed(0)}%
          </span>
        </div>
        <div className="supplier-card-metric">
          <Clock size={12} />
          <span className="supplier-card-metric-value">{supplier.lateDeliveries}</span>
        </div>
        <div className="supplier-card-metric">
          <TrendingUp size={12} />
          <span className="supplier-card-metric-value">
            {supplier.priceVolatility.toFixed(1)}%
          </span>
        </div>
      </div>

      {/* Bottom row: Spend + Status */}
      <div className="supplier-card-bottom-row">
        <div className="supplier-card-spend">
          {formatCurrency(supplier.totalSpend)}
        </div>
        <div className={`supplier-card-status supplier-card-status-${statusColor}`}>
          {supplier.status}
        </div>
      </div>

      {/* Tooltip on hover */}
      {isHovered && supplier.lastInvoiceDate && (
        <div className="supplier-card-tooltip">
          Last invoice: {formatCurrency(supplier.lastInvoiceValue || 0)} on{' '}
          {new Date(supplier.lastInvoiceDate).toLocaleDateString('en-GB', {
            day: '2-digit',
            month: '2-digit',
          })}
          {supplier.flagsCount !== undefined && supplier.flagsCount > 0 && (
            <> · {supplier.flagsCount} flags</>
          )}
          {supplier.matchRate && <> · {supplier.matchRate.toFixed(0)}% match rate</>}
        </div>
      )}
    </div>
  )
}

