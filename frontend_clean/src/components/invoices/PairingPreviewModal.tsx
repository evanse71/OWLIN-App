import { useState, useEffect } from 'react'
import { X, AlertTriangle, CheckCircle, Info } from 'lucide-react'
import { validatePair, linkDeliveryNoteToInvoice, type ValidatePairResponse } from '../../lib/api'
import './Modal.css'
import './PairingPreviewModal.css'

interface PairingPreviewModalProps {
  isOpen: boolean
  onClose: () => void
  onConfirm: () => void
  invoiceId: string
  deliveryNoteId: string
  initialValidation?: ValidatePairResponse | null
  invoiceLineItems?: Array<{
    description?: string
    qty?: number
    unit_price?: number
    total?: number
  }>
  deliveryNoteLineItems?: Array<{
    description?: string
    qty?: number
    unit_price?: number
    total?: number
  }>
}

export function PairingPreviewModal({
  isOpen,
  onClose,
  onConfirm,
  invoiceId,
  deliveryNoteId,
  initialValidation = null,
  invoiceLineItems = [],
  deliveryNoteLineItems = [],
}: PairingPreviewModalProps) {
  const [validation, setValidation] = useState<ValidatePairResponse | null>(initialValidation)
  const [loading, setLoading] = useState(false)
  const [confirming, setConfirming] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (isOpen) {
      // Use initial validation if provided, otherwise load
      if (initialValidation) {
        setValidation(initialValidation)
      } else {
        loadValidation()
      }
    }
  }, [isOpen, invoiceId, deliveryNoteId, initialValidation])

  const loadValidation = async () => {
    setLoading(true)
    setError(null)
    try {
      const result = await validatePair(invoiceId, deliveryNoteId)
      setValidation(result)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to validate pair')
    } finally {
      setLoading(false)
    }
  }

  const handleConfirm = async () => {
    setConfirming(true)
    setError(null)
    try {
      const result = await linkDeliveryNoteToInvoice(invoiceId, deliveryNoteId)
      onConfirm(result.warnings)
      handleClose()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to pair documents')
    } finally {
      setConfirming(false)
    }
  }

  const handleClose = () => {
    setValidation(null)
    setError(null)
    onClose()
  }

  const getSeverityIcon = (severity: 'critical' | 'warning' | 'info') => {
    switch (severity) {
      case 'critical':
        return <AlertTriangle className="icon-critical" />
      case 'warning':
        return <AlertTriangle className="icon-warning" />
      default:
        return <Info className="icon-info" />
    }
  }

  const getSeverityClass = (severity: 'critical' | 'warning' | 'info') => {
    return `severity-${severity}`
  }

  if (!isOpen) return null

  return (
    <div className="modal-overlay" onClick={handleClose}>
      <div className="modal-container pairing-preview-modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>Review Pairing</h2>
          <button className="modal-close" onClick={handleClose}>
            <X size={20} />
          </button>
        </div>

        <div className="modal-body">
          {loading && (
            <div className="loading-state">
              <p>Validating quantities...</p>
            </div>
          )}

          {error && (
            <div className="error-message">
              <AlertTriangle size={16} />
              <span>{error}</span>
              <button
                className="glass-button"
                onClick={loadValidation}
                style={{ marginLeft: '12px', padding: '6px 14px', fontSize: '12px' }}
              >
                Retry
              </button>
            </div>
          )}

          {validation && !loading && (
            <>
              {/* Match Score Indicator */}
              <div className="match-score-section">
                <div className="match-score-header">
                  <span>Quantity Match Score</span>
                  <span className={`match-score-value score-${validation.matchScore >= 0.8 ? 'high' : validation.matchScore >= 0.6 ? 'medium' : 'low'}`}>
                    {(validation.matchScore * 100).toFixed(0)}%
                  </span>
                </div>
                <div className="match-score-bar">
                  <div
                    className="match-score-fill"
                    style={{ width: `${validation.matchScore * 100}%` }}
                  />
                </div>
              </div>

              {/* Warnings */}
              {validation.warnings.length > 0 && (
                <div className="warnings-section">
                  <div className="warnings-header">
                    <AlertTriangle size={18} />
                    <h3>Warnings</h3>
                  </div>
                  <ul className="warnings-list">
                    {validation.warnings.map((warning, idx) => (
                      <li key={idx}>{warning}</li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Discrepancies Table */}
              {validation.discrepancies.length > 0 && (
                <div className="discrepancies-section">
                  <h3>Quantity Discrepancies</h3>
                  <div className="discrepancies-table-container">
                    <table className="discrepancies-table">
                      <thead>
                        <tr>
                          <th>Item</th>
                          <th>Invoice Qty</th>
                          <th>Delivery Qty</th>
                          <th>Difference</th>
                          <th>Status</th>
                        </tr>
                      </thead>
                      <tbody>
                        {validation.discrepancies.map((disc, idx) => (
                          <tr key={idx} className={getSeverityClass(disc.severity)}>
                            <td className="item-description-cell">{disc.description}</td>
                            <td className="qty-cell">{disc.invoiceQty.toFixed(2)}</td>
                            <td className="qty-cell">{disc.deliveryQty.toFixed(2)}</td>
                            <td className={`diff-cell ${disc.difference > 0 ? 'diff-positive' : 'diff-negative'}`}>
                              {disc.difference > 0 ? '+' : ''}{disc.difference.toFixed(2)}
                            </td>
                            <td className="status-cell">
                              <span className={`severity-badge ${getSeverityClass(disc.severity)}`}>
                                {getSeverityIcon(disc.severity)}
                                <span className="severity-text">{disc.severity.toUpperCase()}</span>
                              </span>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

              {/* Line Items Comparison */}
              {(invoiceLineItems.length > 0 || deliveryNoteLineItems.length > 0) && (
                <div className="line-items-comparison">
                  <h3>Line Items Comparison</h3>
                  <div className="comparison-grid">
                    <div className="comparison-column">
                      <h4>Invoice Items</h4>
                      <div className="line-items-list">
                        {invoiceLineItems.map((item, idx) => (
                          <div key={idx} className="line-item-row">
                            <span className="item-description">{item.description || 'N/A'}</span>
                            <span className="item-qty">{item.qty?.toFixed(2) || '0.00'}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                    <div className="comparison-column">
                      <h4>Delivery Note Items</h4>
                      <div className="line-items-list">
                        {deliveryNoteLineItems.map((item, idx) => (
                          <div key={idx} className="line-item-row">
                            <span className="item-description">{item.description || 'N/A'}</span>
                            <span className="item-qty">{item.qty?.toFixed(2) || '0.00'}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {validation.isValid && validation.discrepancies.length === 0 && (
                <div className="success-message">
                  <CheckCircle size={18} />
                  <span>All quantities match. Safe to pair.</span>
                </div>
              )}
            </>
          )}
        </div>

        <div className="modal-footer">
          <button className="glass-button secondary-action" onClick={handleClose} disabled={confirming}>
            Cancel
          </button>
          <button
            className="glass-button primary-action"
            onClick={handleConfirm}
            disabled={loading || confirming || !validation}
          >
            {confirming ? 'Pairing...' : 'Confirm Pair'}
          </button>
        </div>
      </div>
    </div>
  )
}

