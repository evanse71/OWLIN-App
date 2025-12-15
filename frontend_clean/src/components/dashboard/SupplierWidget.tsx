/**
 * Supplier Widget Component
 * Individual supplier card showing score, mismatch rate, late deliveries, price volatility
 */

import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Building2, TrendingUp, Clock, AlertTriangle } from 'lucide-react'
import type { SupplierRisk } from '../../lib/dashboardApi'
import './SupplierWidget.css'

interface SupplierWidgetProps {
  supplier: SupplierRisk
  onClick: (supplier: SupplierRisk) => void
  currentRole: 'GM' | 'Finance' | 'ShiftLead'
}

export function SupplierWidget({ supplier, onClick, currentRole }: SupplierWidgetProps) {
  const [isHovered, setIsHovered] = useState(false)
  const navigate = useNavigate()

  const handleClick = () => {
    // Navigate to suppliers page with preselected supplier
    navigate(`/suppliers?id=${encodeURIComponent(supplier.id)}`)
    onClick(supplier)
  }

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

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('en-GB', {
      style: 'currency',
      currency: 'GBP',
      maximumFractionDigits: 0,
    }).format(value)
  }

  return (
    <div
      className={`supplier-widget supplier-widget-score-${getScoreColor(supplier.score)}`}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      onClick={handleClick}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault()
          handleClick()
        }
      }}
    >
      <div className="supplier-widget-header">
        <Building2 size={18} className="supplier-widget-icon" />
        <div className="supplier-widget-name">{supplier.name}</div>
        <div className={`supplier-widget-score supplier-widget-score-${getScoreColor(supplier.score)}`}>
          {supplier.score}
        </div>
      </div>

      <div className="supplier-widget-metrics">
        <div className="supplier-widget-metric">
          <AlertTriangle size={14} />
          <span className="supplier-widget-metric-label">Mismatch</span>
          <span className="supplier-widget-metric-value">{supplier.mismatchRate.toFixed(1)}%</span>
        </div>
        <div className="supplier-widget-metric">
          <Clock size={14} />
          <span className="supplier-widget-metric-label">Late</span>
          <span className="supplier-widget-metric-value">{supplier.lateDeliveries}</span>
        </div>
        <div className="supplier-widget-metric">
          <TrendingUp size={14} />
          <span className="supplier-widget-metric-label">Volatility</span>
          <span className="supplier-widget-metric-value">{supplier.priceVolatility.toFixed(1)}%</span>
        </div>
      </div>

      <div className="supplier-widget-footer">
        <div className="supplier-widget-spend">
          {formatCurrency(supplier.totalSpend)}
        </div>
      </div>

      {isHovered && (
        <div className="supplier-widget-hover-glow" />
      )}
    </div>
  )
}

