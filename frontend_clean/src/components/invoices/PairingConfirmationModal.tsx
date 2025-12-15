import { useState } from 'react'
import { X, AlertTriangle, CheckCircle } from 'lucide-react'
import './Modal.css'

export interface PairingConfirmationData {
  invoiceId: string
  invoiceNumber: string
  invoiceSupplier: string
  invoiceDate: string
  invoiceTotal: number
  invoiceLineItems?: Array<{
    description: string
    qty: number
    unit: string
    price: number
  }>
  deliveryNoteId: string
  deliveryNoteNumber: string
  deliveryNoteSupplier: string
  deliveryNoteDate: string
  deliveryNoteTotal: number
  deliveryNoteLineItems?: Array<{
    description: string
    qty: number
    unit: string
  }>
  confidence: number
  reason: string
  quantityDifferences?: Array<{
    description: string
    invoiceQty: number
    dnQty: number
    difference: number
  }>
  hasQuantityMismatch?: boolean
}

interface PairingConfirmationModalProps {
  isOpen: boolean
  onClose: () => void
  onConfirm: () => void
  onReject: () => void
  data: PairingConfirmationData | null
  loading?: boolean
}

export function PairingConfirmationModal({
  isOpen,
  onClose,
  onConfirm,
  onReject,
  data,
  loading = false,
}: PairingConfirmationModalProps) {
  const [expandedItems, setExpandedItems] = useState<Set<string>>(new Set())

  if (!isOpen || !data) return null

  const toggleItemExpansion = (description: string) => {
    const newExpanded = new Set(expandedItems)
    if (newExpanded.has(description)) {
      newExpanded.delete(description)
    } else {
      newExpanded.add(description)
    }
    setExpandedItems(newExpanded)
  }

  const formatDate = (dateStr: string) => {
    try {
      return new Date(dateStr).toLocaleDateString('en-GB', {
        day: 'numeric',
        month: 'short',
        year: 'numeric',
      })
    } catch {
      return dateStr
    }
  }

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('en-GB', {
      style: 'currency',
      currency: 'GBP',
    }).format(value)
  }

  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 0.9) return 'var(--accent-green)'
    if (confidence >= 0.7) return 'var(--accent-yellow)'
    return 'var(--accent-red)'
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-container" onClick={(e) => e.stopPropagation()} style={{ maxWidth: '800px', maxHeight: '90vh', overflowY: 'auto' }}>
        <div className="modal-header">
          <h2 className="modal-title">Confirm Automatic Pairing</h2>
          <button className="modal-close-button" onClick={onClose} aria-label="Close modal">
            <X size={20} />
          </button>
        </div>

        <div className="modal-body">
          {/* Confidence Score */}
          <div style={{
            padding: '16px',
            background: 'var(--bg-secondary)',
            borderRadius: '8px',
            marginBottom: '16px',
            display: 'flex',
            alignItems: 'center',
            gap: '12px'
          }}>
            <div style={{
              width: '48px',
              height: '48px',
              borderRadius: '50%',
              background: `rgba(${getConfidenceColor(data.confidence) === 'var(--accent-green)' ? '34, 197, 94' : getConfidenceColor(data.confidence) === 'var(--accent-yellow)' ? '251, 191, 36' : '239, 68, 68'}, 0.1)`,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              flexShrink: 0
            }}>
              {data.confidence >= 0.9 ? (
                <CheckCircle size={24} style={{ color: getConfidenceColor(data.confidence) }} />
              ) : (
                <AlertTriangle size={24} style={{ color: getConfidenceColor(data.confidence) }} />
              )}
            </div>
            <div style={{ flex: 1 }}>
              <div style={{ fontWeight: '600', marginBottom: '4px' }}>
                Confidence: {Math.round(data.confidence * 100)}%
              </div>
              <div style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>
                {data.reason}
              </div>
            </div>
          </div>

          {/* Quantity Mismatch Warning */}
          {data.hasQuantityMismatch && (
            <div style={{
              padding: '12px',
              background: 'rgba(239, 68, 68, 0.1)',
              border: '1px solid rgba(239, 68, 68, 0.3)',
              borderRadius: '8px',
              marginBottom: '16px',
              display: 'flex',
              alignItems: 'flex-start',
              gap: '8px'
            }}>
              <AlertTriangle size={20} style={{ color: 'var(--accent-red)', flexShrink: 0, marginTop: '2px' }} />
              <div style={{ fontSize: '13px', color: 'var(--accent-red)' }}>
                <strong>Warning:</strong> Quantity mismatches detected between invoice and delivery note. Please review before confirming.
              </div>
            </div>
          )}

          {/* Side-by-side comparison */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px', marginBottom: '16px' }}>
            {/* Invoice Details */}
            <div style={{
              padding: '16px',
              background: 'var(--bg-secondary)',
              borderRadius: '8px',
              border: '1px solid var(--border-color)'
            }}>
              <h3 style={{ fontSize: '14px', fontWeight: '600', marginBottom: '12px', color: 'var(--accent-blue)' }}>
                Invoice
              </h3>
              <div style={{ fontSize: '13px', marginBottom: '8px' }}>
                <strong>Number:</strong> {data.invoiceNumber}
              </div>
              <div style={{ fontSize: '13px', marginBottom: '8px' }}>
                <strong>Supplier:</strong> {data.invoiceSupplier}
              </div>
              <div style={{ fontSize: '13px', marginBottom: '8px' }}>
                <strong>Date:</strong> {formatDate(data.invoiceDate)}
              </div>
              <div style={{ fontSize: '13px', marginBottom: '12px' }}>
                <strong>Total:</strong> {formatCurrency(data.invoiceTotal)}
              </div>
              
              {data.invoiceLineItems && data.invoiceLineItems.length > 0 && (
                <div>
                  <div style={{ fontSize: '12px', fontWeight: '600', marginBottom: '8px', color: 'var(--text-secondary)' }}>
                    Line Items:
                  </div>
                  <div style={{ maxHeight: '200px', overflowY: 'auto' }}>
                    {data.invoiceLineItems.map((item, idx) => (
                      <div key={idx} style={{
                        padding: '6px',
                        background: 'var(--bg-card)',
                        borderRadius: '4px',
                        marginBottom: '4px',
                        fontSize: '11px'
                      }}>
                        <div style={{ fontWeight: '500' }}>{item.description}</div>
                        <div style={{ color: 'var(--text-secondary)' }}>
                          {item.qty} {item.unit} @ {formatCurrency(item.price)}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {/* Delivery Note Details */}
            <div style={{
              padding: '16px',
              background: 'var(--bg-secondary)',
              borderRadius: '8px',
              border: '1px solid var(--border-color)'
            }}>
              <h3 style={{ fontSize: '14px', fontWeight: '600', marginBottom: '12px', color: 'var(--accent-green)' }}>
                Delivery Note
              </h3>
              <div style={{ fontSize: '13px', marginBottom: '8px' }}>
                <strong>Number:</strong> {data.deliveryNoteNumber}
              </div>
              <div style={{ fontSize: '13px', marginBottom: '8px' }}>
                <strong>Supplier:</strong> {data.deliveryNoteSupplier}
              </div>
              <div style={{ fontSize: '13px', marginBottom: '8px' }}>
                <strong>Date:</strong> {formatDate(data.deliveryNoteDate)}
              </div>
              <div style={{ fontSize: '13px', marginBottom: '12px' }}>
                <strong>Total:</strong> {formatCurrency(data.deliveryNoteTotal)}
              </div>
              
              {data.deliveryNoteLineItems && data.deliveryNoteLineItems.length > 0 && (
                <div>
                  <div style={{ fontSize: '12px', fontWeight: '600', marginBottom: '8px', color: 'var(--text-secondary)' }}>
                    Line Items:
                  </div>
                  <div style={{ maxHeight: '200px', overflowY: 'auto' }}>
                    {data.deliveryNoteLineItems.map((item, idx) => (
                      <div key={idx} style={{
                        padding: '6px',
                        background: 'var(--bg-card)',
                        borderRadius: '4px',
                        marginBottom: '4px',
                        fontSize: '11px'
                      }}>
                        <div style={{ fontWeight: '500' }}>{item.description}</div>
                        <div style={{ color: 'var(--text-secondary)' }}>
                          {item.qty} {item.unit}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Quantity Differences */}
          {data.quantityDifferences && data.quantityDifferences.length > 0 && (
            <div style={{
              padding: '16px',
              background: 'rgba(239, 68, 68, 0.05)',
              border: '1px solid rgba(239, 68, 68, 0.2)',
              borderRadius: '8px',
              marginBottom: '16px'
            }}>
              <h3 style={{ fontSize: '14px', fontWeight: '600', marginBottom: '12px', color: 'var(--accent-red)' }}>
                Quantity Differences
              </h3>
              <div style={{ maxHeight: '200px', overflowY: 'auto' }}>
                {data.quantityDifferences.map((diff, idx) => (
                  <div
                    key={idx}
                    style={{
                      padding: '10px',
                      background: 'var(--bg-card)',
                      borderRadius: '6px',
                      marginBottom: '8px',
                      border: '1px solid var(--border-color)'
                    }}
                  >
                    <div style={{ fontWeight: '600', marginBottom: '6px', fontSize: '13px' }}>
                      {diff.description}
                    </div>
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '8px', fontSize: '12px' }}>
                      <div>
                        <div style={{ color: 'var(--text-secondary)', fontSize: '11px' }}>Invoice Qty</div>
                        <div style={{ fontWeight: '500' }}>{diff.invoiceQty}</div>
                      </div>
                      <div>
                        <div style={{ color: 'var(--text-secondary)', fontSize: '11px' }}>DN Qty</div>
                        <div style={{ fontWeight: '500' }}>{diff.dnQty}</div>
                      </div>
                      <div>
                        <div style={{ color: 'var(--text-secondary)', fontSize: '11px' }}>Difference</div>
                        <div style={{
                          fontWeight: '600',
                          color: diff.difference === 0 ? 'var(--accent-green)' : 'var(--accent-red)'
                        }}>
                          {diff.difference > 0 ? '+' : ''}{diff.difference}
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        <div className="modal-footer">
          <button
            className="modal-button-secondary"
            onClick={onReject}
            disabled={loading}
          >
            Reject
          </button>
          <button
            className="modal-button-primary"
            onClick={onConfirm}
            disabled={loading}
            style={{
              background: data.hasQuantityMismatch ? 'var(--accent-yellow)' : 'var(--accent-blue)'
            }}
          >
            {loading ? 'Pairing...' : 'Confirm Pairing'}
          </button>
        </div>
      </div>
    </div>
  )
}

