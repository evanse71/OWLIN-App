import { useState, useEffect } from 'react'
import { X } from 'lucide-react'
import { fetchDeliveryNoteDetails } from '../../lib/api'
import './Modal.css'

interface LineItem {
  description?: string
  item?: string
  qty?: number
  quantity?: number
  unit?: string
  uom?: string
}

interface DeliveryNoteDetail {
  id: string
  noteNumber?: string
  date?: string
  supplier?: string
  driver?: string
  vehicle?: string
  timeWindow?: string
  lineItems?: LineItem[]
}

interface DeliveryNoteDetailModalProps {
  isOpen: boolean
  onClose: () => void
  deliveryNoteId: string
}

export function DeliveryNoteDetailModal({ isOpen, onClose, deliveryNoteId }: DeliveryNoteDetailModalProps) {
  const [deliveryNote, setDeliveryNote] = useState<DeliveryNoteDetail | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (isOpen && deliveryNoteId) {
      loadDeliveryNote()
    }
  }, [isOpen, deliveryNoteId])

  const loadDeliveryNote = async () => {
    setLoading(true)
    setError(null)
    try {
      const details = await fetchDeliveryNoteDetails(deliveryNoteId)
      setDeliveryNote(details)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load delivery note details')
    } finally {
      setLoading(false)
    }
  }

  const formatDate = (dateStr?: string) => {
    if (!dateStr) return 'No date'
    try {
      const date = new Date(dateStr)
      return date.toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' })
    } catch {
      return dateStr
    }
  }

  if (!isOpen) return null

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-container large" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2 className="modal-title">
            Delivery Note: {deliveryNote?.noteNumber || `DN-${deliveryNoteId.slice(0, 8)}`}
          </h2>
          <button className="modal-close-button" onClick={onClose}>
            <X size={20} />
          </button>
        </div>

        <div className="modal-body">
          {loading ? (
            <div className="modal-loading">Loading delivery note details...</div>
          ) : error ? (
            <div className="modal-error">{error}</div>
          ) : deliveryNote ? (
            <>
              <div style={{ marginBottom: '24px' }}>
                <div className="modal-form-row">
                  <div className="modal-form-group">
                    <label className="modal-form-label">Supplier</label>
                    <div style={{ padding: '10px 14px', background: 'var(--bg-secondary)', borderRadius: '8px', fontSize: '14px' }}>
                      {deliveryNote.supplier || 'Unknown Supplier'}
                    </div>
                  </div>

                  <div className="modal-form-group">
                    <label className="modal-form-label">Date</label>
                    <div style={{ padding: '10px 14px', background: 'var(--bg-secondary)', borderRadius: '8px', fontSize: '14px' }}>
                      {formatDate(deliveryNote.date)}
                    </div>
                  </div>
                </div>

                {(deliveryNote.driver || deliveryNote.vehicle || deliveryNote.timeWindow) && (
                  <div className="modal-form-row" style={{ marginTop: '16px' }}>
                    {deliveryNote.driver && (
                      <div className="modal-form-group">
                        <label className="modal-form-label">Driver</label>
                        <div style={{ padding: '10px 14px', background: 'var(--bg-secondary)', borderRadius: '8px', fontSize: '14px' }}>
                          {deliveryNote.driver}
                        </div>
                      </div>
                    )}

                    {deliveryNote.vehicle && (
                      <div className="modal-form-group">
                        <label className="modal-form-label">Vehicle</label>
                        <div style={{ padding: '10px 14px', background: 'var(--bg-secondary)', borderRadius: '8px', fontSize: '14px' }}>
                          {deliveryNote.vehicle}
                        </div>
                      </div>
                    )}

                    {deliveryNote.timeWindow && (
                      <div className="modal-form-group">
                        <label className="modal-form-label">Time Window</label>
                        <div style={{ padding: '10px 14px', background: 'var(--bg-secondary)', borderRadius: '8px', fontSize: '14px' }}>
                          {deliveryNote.timeWindow}
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>

              {deliveryNote.lineItems && deliveryNote.lineItems.length > 0 ? (
                <div className="modal-form-group">
                  <label className="modal-form-label">Line Items</label>
                  <table className="line-items-table">
                    <thead>
                      <tr>
                        <th>Description</th>
                        <th>Quantity</th>
                        <th>Unit</th>
                      </tr>
                    </thead>
                    <tbody>
                      {deliveryNote.lineItems.map((item, index) => (
                        <tr key={index}>
                          <td>{item.description || item.item || 'Unknown item'}</td>
                          <td>{item.qty || item.quantity || 0}</td>
                          <td>{item.unit || item.uom || '-'}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <div style={{ padding: '24px', textAlign: 'center', color: 'var(--text-muted)' }}>
                  No line items available
                </div>
              )}
            </>
          ) : null}
        </div>

        <div className="modal-footer">
          <button className="modal-button-secondary" onClick={onClose}>
            Close
          </button>
        </div>
      </div>
    </div>
  )
}

