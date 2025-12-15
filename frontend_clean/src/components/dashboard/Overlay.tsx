/**
 * Overlay Component
 * Slide-in overlays for supplier details, pairing suggestions, and mismatch diffs
 */

import { useEffect } from 'react'
import { X } from 'lucide-react'
import type { SupplierRisk } from '../../lib/dashboardApi'
import './Overlay.css'

interface OverlayProps {
  supplier?: SupplierRisk
  currentRole: 'GM' | 'Finance' | 'ShiftLead'
  onClose: () => void
}

export function Overlay({ supplier, currentRole, onClose }: OverlayProps) {
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose()
      }
    }
    document.addEventListener('keydown', handleEscape)
    document.body.style.overflow = 'hidden'
    return () => {
      document.removeEventListener('keydown', handleEscape)
      document.body.style.overflow = ''
    }
  }, [onClose])

  if (!supplier) return null

  return (
    <div className="overlay-backdrop" onClick={onClose}>
      <div className="overlay-content" onClick={(e) => e.stopPropagation()}>
        <div className="overlay-header">
          <h2 className="overlay-title">{supplier.name}</h2>
          <button className="overlay-close" onClick={onClose} aria-label="Close">
            <X size={20} />
          </button>
        </div>

        <div className="overlay-body">
          <div className="overlay-section">
            <h3 className="overlay-section-title">Risk Score</h3>
            <div className={`overlay-score overlay-score-${supplier.score.toLowerCase()}`}>
              {supplier.score}
            </div>
          </div>

          <div className="overlay-section">
            <h3 className="overlay-section-title">Metrics</h3>
            <div className="overlay-metrics">
              <div className="overlay-metric">
                <span className="overlay-metric-label">Mismatch Rate</span>
                <span className="overlay-metric-value">{supplier.mismatchRate.toFixed(1)}%</span>
              </div>
              <div className="overlay-metric">
                <span className="overlay-metric-label">Late Deliveries</span>
                <span className="overlay-metric-value">{supplier.lateDeliveries}</span>
              </div>
              <div className="overlay-metric">
                <span className="overlay-metric-label">Price Volatility</span>
                <span className="overlay-metric-value">{supplier.priceVolatility.toFixed(1)}%</span>
              </div>
              <div className="overlay-metric">
                <span className="overlay-metric-label">Total Spend</span>
                <span className="overlay-metric-value">
                  {new Intl.NumberFormat('en-GB', {
                    style: 'currency',
                    currency: 'GBP',
                    maximumFractionDigits: 0,
                  }).format(supplier.totalSpend)}
                </span>
              </div>
            </div>
          </div>

          {currentRole === 'GM' && (
            <div className="overlay-section">
              <h3 className="overlay-section-title">Actions</h3>
              <div className="overlay-actions">
                <button className="overlay-action-button overlay-action-primary">Escalate</button>
                <button className="overlay-action-button">Schedule Review</button>
              </div>
            </div>
          )}

          {currentRole === 'Finance' && (
            <div className="overlay-section">
              <h3 className="overlay-section-title">Actions</h3>
              <div className="overlay-actions">
                <button className="overlay-action-button overlay-action-primary">Generate Credit Email</button>
                <button className="overlay-action-button">View History</button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

