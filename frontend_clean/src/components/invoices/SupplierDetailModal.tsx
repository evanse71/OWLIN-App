import { useState, useEffect } from 'react'
import { X } from 'lucide-react'
import { fetchSupplierDetail, type SupplierDetail } from '../../lib/suppliersApi'
import './Modal.css'

interface SupplierDetailModalProps {
  isOpen: boolean
  onClose: () => void
  supplierName: string
}

export function SupplierDetailModal({ isOpen, onClose, supplierName }: SupplierDetailModalProps) {
  const [supplier, setSupplier] = useState<SupplierDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (isOpen && supplierName) {
      setLoading(true)
      setError(null)
      fetchSupplierDetail(supplierName)
        .then((data) => {
          if (data === null) {
            // Scorecard not available - show friendly message
            setSupplier(null)
            setError('No scorecard available yet for this supplier')
          } else {
            setSupplier(data)
          }
          setLoading(false)
        })
        .catch((err) => {
          // Only log unexpected errors (network, 5xx)
          console.error('Failed to fetch supplier details:', err)
          setError(err instanceof Error ? err.message : 'Failed to load supplier details')
          setLoading(false)
        })
    }
  }, [isOpen, supplierName])

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('en-GB', { style: 'currency', currency: 'GBP' }).format(value)
  }

  if (!isOpen) return null

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-container large" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2 className="modal-title">Supplier: {supplierName}</h2>
          <button className="modal-close-button" onClick={onClose}>
            <X size={20} />
          </button>
        </div>

        <div className="modal-body">
          {loading ? (
            <div className="modal-loading">Loading supplier details...</div>
          ) : error ? (
            <div style={{ 
              padding: '24px', 
              textAlign: 'center', 
              color: 'var(--text-secondary)',
              background: 'var(--bg-secondary)',
              borderRadius: '8px'
            }}>
              <div style={{ fontSize: '14px', marginBottom: '8px' }}>{error}</div>
              {error.includes('No scorecard') && (
                <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
                  Scorecard data will be available once invoices and delivery notes are paired for this supplier.
                </div>
              )}
            </div>
          ) : supplier ? (
            <>
              <div style={{ marginBottom: '24px' }}>
                <div className="modal-form-row">
                  <div className="modal-form-group">
                    <label className="modal-form-label">Supplier Name</label>
                    <div style={{ padding: '10px 14px', background: 'var(--bg-secondary)', borderRadius: '8px', fontSize: '14px' }}>
                      {supplier.name}
                    </div>
                  </div>

                  <div className="modal-form-group">
                    <label className="modal-form-label">Status</label>
                    <div style={{ padding: '10px 14px', background: 'var(--bg-secondary)', borderRadius: '8px', fontSize: '14px' }}>
                      {supplier.status}
                    </div>
                  </div>
                </div>

                <div className="modal-form-row" style={{ marginTop: '16px' }}>
                  <div className="modal-form-group">
                    <label className="modal-form-label">Risk Score</label>
                    <div style={{ 
                      padding: '10px 14px', 
                      background: supplier.score === 'Low' ? 'rgba(34, 197, 94, 0.1)' : 
                                  supplier.score === 'Medium' ? 'rgba(234, 179, 8, 0.1)' : 
                                  'rgba(239, 68, 68, 0.1)',
                      borderRadius: '8px', 
                      fontSize: '14px',
                      fontWeight: '600',
                      color: supplier.score === 'Low' ? '#4ade80' : 
                             supplier.score === 'Medium' ? '#fbbf24' : 
                             '#f87171'
                    }}>
                      {supplier.score}
                    </div>
                  </div>

                  <div className="modal-form-group">
                    <label className="modal-form-label">Accuracy</label>
                    <div style={{ padding: '10px 14px', background: 'var(--bg-secondary)', borderRadius: '8px', fontSize: '14px' }}>
                      {supplier.accuracy.toFixed(1)}%
                    </div>
                  </div>
                </div>

                <div className="modal-form-row" style={{ marginTop: '16px' }}>
                  <div className="modal-form-group">
                    <label className="modal-form-label">Mismatch Rate</label>
                    <div style={{ padding: '10px 14px', background: 'var(--bg-secondary)', borderRadius: '8px', fontSize: '14px' }}>
                      {supplier.mismatchRate.toFixed(1)}%
                    </div>
                  </div>

                  <div className="modal-form-group">
                    <label className="modal-form-label">Reliability</label>
                    <div style={{ padding: '10px 14px', background: 'var(--bg-secondary)', borderRadius: '8px', fontSize: '14px' }}>
                      {supplier.reliability.toFixed(1)}%
                    </div>
                  </div>
                </div>

                {supplier.totalSpend > 0 && (
                  <div className="modal-form-row" style={{ marginTop: '16px' }}>
                    <div className="modal-form-group">
                      <label className="modal-form-label">Total Spend</label>
                      <div style={{ padding: '10px 14px', background: 'var(--bg-secondary)', borderRadius: '8px', fontSize: '14px', fontWeight: '600' }}>
                        {formatCurrency(supplier.totalSpend)}
                      </div>
                    </div>
                  </div>
                )}
              </div>

              <div style={{ marginTop: '24px', paddingTop: '24px', borderTop: '1px solid var(--border-color)' }}>
                <h3 style={{ fontSize: '16px', fontWeight: '600', marginBottom: '16px' }}>Additional Information</h3>
                <div style={{ fontSize: '13px', color: 'var(--text-secondary)', lineHeight: '1.6' }}>
                  <p>For more detailed supplier information, visit the Suppliers page.</p>
                </div>
              </div>
            </>
          ) : null}
        </div>
      </div>
    </div>
  )
}

