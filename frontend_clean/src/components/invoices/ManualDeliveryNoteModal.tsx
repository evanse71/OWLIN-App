import { useState } from 'react'
import { X, Plus, Trash2 } from 'lucide-react'
import { createManualDeliveryNote } from '../../lib/api'
import './Modal.css'

interface LineItem {
  description: string
  qty: number
  unit: string
}

interface ManualDeliveryNoteModalProps {
  isOpen: boolean
  onClose: () => void
  onSuccess: () => void
}

export function ManualDeliveryNoteModal({ isOpen, onClose, onSuccess }: ManualDeliveryNoteModalProps) {
  const [noteNumber, setNoteNumber] = useState('')
  const [date, setDate] = useState(new Date().toISOString().split('T')[0])
  const [supplier, setSupplier] = useState('')
  const [lineItems, setLineItems] = useState<LineItem[]>([
    { description: '', qty: 0, unit: '' },
  ])
  const [driver, setDriver] = useState('')
  const [vehicle, setVehicle] = useState('')
  const [timeWindow, setTimeWindow] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const updateLineItem = (index: number, field: keyof LineItem, value: string | number) => {
    const updated = [...lineItems]
    updated[index] = { ...updated[index], [field]: value }
    setLineItems(updated)
  }

  const addLineItem = () => {
    setLineItems([...lineItems, { description: '', qty: 0, unit: '' }])
  }

  const removeLineItem = (index: number) => {
    if (lineItems.length > 1) {
      setLineItems(lineItems.filter((_, i) => i !== index))
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    setLoading(true)

    try {
      // Validate required fields
      if (!noteNumber.trim() || !supplier.trim()) {
        setError('Please fill in note number and supplier')
        setLoading(false)
        return
      }

      const dnData = {
        noteNumber,
        date,
        supplier,
        lineItems: lineItems.filter(item => item.description.trim() !== ''),
        driver: driver.trim() || undefined,
        vehicle: vehicle.trim() || undefined,
        timeWindow: timeWindow.trim() || undefined,
      }

      // Add timeout to prevent hanging
      const createPromise = createManualDeliveryNote(dnData)
      const timeoutPromise = new Promise((_, reject) => 
        setTimeout(() => reject(new Error('Request timeout - please try again')), 10000)
      )
      
      await Promise.race([createPromise, timeoutPromise])
      
      // Call onSuccess before closing to ensure refresh happens
      try {
        onSuccess()
      } catch (successErr) {
        console.warn('onSuccess callback error:', successErr)
        // Continue to close modal even if onSuccess fails
      }
      
      handleClose()
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to create delivery note'
      setError(errorMessage)
      console.error('Failed to create delivery note:', err)
    } finally {
      setLoading(false)
    }
  }

  const handleClose = () => {
    setNoteNumber('')
    setDate(new Date().toISOString().split('T')[0])
    setSupplier('')
    setLineItems([{ description: '', qty: 0, unit: '' }])
    setDriver('')
    setVehicle('')
    setTimeWindow('')
    setError(null)
    onClose()
  }

  if (!isOpen) return null

  return (
    <div className="modal-overlay" onClick={handleClose}>
      <div className="modal-container" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2 className="modal-title">Create Manual Delivery Note</h2>
          <button className="modal-close-button" onClick={handleClose}>
            <X size={20} />
          </button>
        </div>

        <form onSubmit={handleSubmit}>
          <div className="modal-body">
            {error && <div className="modal-error">{error}</div>}

            <div className="modal-form-row">
              <div className="modal-form-group">
                <label className="modal-form-label">Note Number *</label>
                <input
                  type="text"
                  className="modal-form-input"
                  value={noteNumber}
                  onChange={(e) => setNoteNumber(e.target.value)}
                  required
                  placeholder="DN-001"
                />
              </div>

              <div className="modal-form-group">
                <label className="modal-form-label">Date *</label>
                <input
                  type="date"
                  className="modal-form-input"
                  value={date}
                  onChange={(e) => setDate(e.target.value)}
                  required
                />
              </div>
            </div>

            <div className="modal-form-group">
              <label className="modal-form-label">Supplier *</label>
              <input
                type="text"
                className="modal-form-input"
                value={supplier}
                onChange={(e) => setSupplier(e.target.value)}
                required
                placeholder="Supplier name"
              />
            </div>

            <div className="modal-form-group">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                <label className="modal-form-label" style={{ marginBottom: 0 }}>Line Items</label>
                <button
                  type="button"
                  className="glass-button"
                  onClick={addLineItem}
                  style={{ fontSize: '12px', padding: '6px 12px' }}
                >
                  <Plus size={14} />
                  Add Item
                </button>
              </div>

              <table className="line-items-table">
                <thead>
                  <tr>
                    <th>Description</th>
                    <th>Qty</th>
                    <th>Unit</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody>
                  {lineItems.map((item, index) => (
                    <tr key={index}>
                      <td>
                        <input
                          type="text"
                          value={item.description}
                          onChange={(e) => updateLineItem(index, 'description', e.target.value)}
                          placeholder="Item description"
                        />
                      </td>
                      <td>
                        <input
                          type="number"
                          value={item.qty || ''}
                          onChange={(e) => updateLineItem(index, 'qty', Number(e.target.value) || 0)}
                          min="0"
                          step="0.01"
                        />
                      </td>
                      <td>
                        <input
                          type="text"
                          value={item.unit}
                          onChange={(e) => updateLineItem(index, 'unit', e.target.value)}
                          placeholder="kg"
                        />
                      </td>
                      <td>
                        {lineItems.length > 1 && (
                          <button
                            type="button"
                            className="line-item-remove"
                            onClick={() => removeLineItem(index)}
                          >
                            <Trash2 size={16} />
                          </button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div className="modal-form-row">
              <div className="modal-form-group">
                <label className="modal-form-label">Driver</label>
                <input
                  type="text"
                  className="modal-form-input"
                  value={driver}
                  onChange={(e) => setDriver(e.target.value)}
                  placeholder="Driver name"
                />
              </div>

              <div className="modal-form-group">
                <label className="modal-form-label">Vehicle</label>
                <input
                  type="text"
                  className="modal-form-input"
                  value={vehicle}
                  onChange={(e) => setVehicle(e.target.value)}
                  placeholder="Vehicle registration"
                />
              </div>
            </div>

            <div className="modal-form-group">
              <label className="modal-form-label">Time Window</label>
              <input
                type="text"
                className="modal-form-input"
                value={timeWindow}
                onChange={(e) => setTimeWindow(e.target.value)}
                placeholder="e.g., 09:00 - 11:00"
              />
            </div>
          </div>

          <div className="modal-footer">
            <button type="button" className="modal-button-secondary" onClick={handleClose}>
              Cancel
            </button>
            <button type="submit" className="modal-button-primary" disabled={loading}>
              {loading ? 'Creating...' : 'Create Delivery Note'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

