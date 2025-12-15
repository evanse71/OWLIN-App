import { useState } from 'react'
import { X, Plus, Trash2 } from 'lucide-react'
import { createManualInvoice } from '../../lib/api'
import './Modal.css'

interface LineItem {
  description: string
  qty: number
  unit: string
  price: number
  total: number
}

interface ManualInvoiceModalProps {
  isOpen: boolean
  onClose: () => void
  onSuccess: () => void
  venue?: string
}

export function ManualInvoiceModal({ isOpen, onClose, onSuccess, venue = 'Waterloo' }: ManualInvoiceModalProps) {
  const [supplier, setSupplier] = useState('')
  const [invoiceNumber, setInvoiceNumber] = useState('')
  const [date, setDate] = useState(new Date().toISOString().split('T')[0])
  const [selectedVenue, setSelectedVenue] = useState(venue)
  const [lineItems, setLineItems] = useState<LineItem[]>([
    { description: '', qty: 0, unit: '', price: 0, total: 0 },
  ])
  const [subtotal, setSubtotal] = useState(0)
  const [vat, setVat] = useState(0)
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const venues = ['Waterloo', 'Royal Oak', 'Main Restaurant']

  const calculateTotals = (items: LineItem[]) => {
    const sub = items.reduce((sum, item) => sum + (item.total || 0), 0)
    const vatAmount = sub * 0.2 // 20% VAT
    const totalAmount = sub + vatAmount
    setSubtotal(sub)
    setVat(vatAmount)
    setTotal(totalAmount)
  }

  const updateLineItem = (index: number, field: keyof LineItem, value: string | number) => {
    const updated = [...lineItems]
    updated[index] = { ...updated[index], [field]: value }
    
    // Auto-calculate total if qty or price changes
    if (field === 'qty' || field === 'price') {
      const qty = field === 'qty' ? Number(value) : updated[index].qty
      const price = field === 'price' ? Number(value) : updated[index].price
      updated[index].total = qty * price
    }
    
    setLineItems(updated)
    calculateTotals(updated)
  }

  const addLineItem = () => {
    setLineItems([...lineItems, { description: '', qty: 0, unit: '', price: 0, total: 0 }])
  }

  const removeLineItem = (index: number) => {
    if (lineItems.length > 1) {
      const updated = lineItems.filter((_, i) => i !== index)
      setLineItems(updated)
      calculateTotals(updated)
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    setLoading(true)

    try {
      // Validate required fields
      if (!supplier.trim() || !invoiceNumber.trim()) {
        setError('Please fill in supplier and invoice number')
        setLoading(false)
        return
      }

      const invoiceData = {
        supplier,
        invoiceNumber,
        date,
        venue: selectedVenue,
        lineItems: lineItems.filter(item => item.description.trim() !== ''),
        subtotal,
        vat,
        total,
      }

      await createManualInvoice(invoiceData)
      onSuccess()
      handleClose()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create invoice')
    } finally {
      setLoading(false)
    }
  }

  const handleClose = () => {
    setSupplier('')
    setInvoiceNumber('')
    setDate(new Date().toISOString().split('T')[0])
    setSelectedVenue(venue)
    setLineItems([{ description: '', qty: 0, unit: '', price: 0, total: 0 }])
    setSubtotal(0)
    setVat(0)
    setTotal(0)
    setError(null)
    onClose()
  }

  if (!isOpen) return null

  return (
    <div className="modal-overlay" onClick={handleClose}>
      <div className="modal-container" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2 className="modal-title">Create Manual Invoice</h2>
          <button className="modal-close-button" onClick={handleClose}>
            <X size={20} />
          </button>
        </div>

        <form onSubmit={handleSubmit}>
          <div className="modal-body">
            {error && <div className="modal-error">{error}</div>}

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

            <div className="modal-form-row">
              <div className="modal-form-group">
                <label className="modal-form-label">Invoice Number *</label>
                <input
                  type="text"
                  className="modal-form-input"
                  value={invoiceNumber}
                  onChange={(e) => setInvoiceNumber(e.target.value)}
                  required
                  placeholder="INV-001"
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
              <label className="modal-form-label">Venue</label>
              <select
                className="modal-form-select"
                value={selectedVenue}
                onChange={(e) => setSelectedVenue(e.target.value)}
              >
                {venues.map((v) => (
                  <option key={v} value={v}>
                    {v}
                  </option>
                ))}
              </select>
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
                    <th>Price</th>
                    <th>Total</th>
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
                        <input
                          type="number"
                          value={item.price || ''}
                          onChange={(e) => updateLineItem(index, 'price', Number(e.target.value) || 0)}
                          min="0"
                          step="0.01"
                        />
                      </td>
                      <td>£{item.total.toFixed(2)}</td>
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
                <label className="modal-form-label">Subtotal</label>
              <input
                type="number"
                className="modal-form-input"
                value={subtotal.toFixed(2)}
                readOnly
                style={{ background: 'var(--bg-secondary)' }}
              />
              </div>

              <div className="modal-form-group">
                <label className="modal-form-label">VAT (20%)</label>
              <input
                type="number"
                className="modal-form-input"
                value={vat.toFixed(2)}
                readOnly
                style={{ background: 'var(--bg-secondary)' }}
              />
              </div>
            </div>

            <div className="modal-form-group">
              <label className="modal-form-label">Total</label>
              <input
                type="number"
                className="modal-form-input"
                value={total.toFixed(2)}
                readOnly
                style={{ background: 'var(--bg-secondary)', fontSize: '18px', fontWeight: '700', color: 'var(--accent-green)' }}
              />
            </div>
          </div>

          <div className="modal-footer">
            <button type="button" className="modal-button-secondary" onClick={handleClose}>
              Cancel
            </button>
            <button type="submit" className="modal-button-primary" disabled={loading}>
              {loading ? 'Creating...' : 'Create Invoice'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

