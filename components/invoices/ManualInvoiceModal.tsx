import React, { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { X, Plus, Trash2, Edit2 } from 'lucide-react'
import { createManualInvoice } from '@/lib/api'

interface LineItem {
  description: string
  quantity: number
  unit_price: number
  uom: string
  vat_rate: number
}

interface ManualInvoiceModalProps {
  isOpen: boolean
  onClose: () => void
  onCreated: () => void
}

export default function ManualInvoiceModal({ isOpen, onClose, onCreated }: ManualInvoiceModalProps) {
  const [formData, setFormData] = useState({
    supplier: '',
    invoice_date: new Date().toISOString().split('T')[0],
    reference: '',
    currency: 'GBP'
  })
  const [lineItems, setLineItems] = useState<LineItem[]>([
    { description: '', quantity: 0, unit_price: 0, uom: '', vat_rate: 0 }
  ])
  const [editingIndex, setEditingIndex] = useState<number | null>(null)
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    
    try {
      // Filter out empty line items
      const validLineItems = lineItems.filter(item => 
        item.description.trim() && item.quantity > 0 && item.unit_price > 0
      )
      
      await createManualInvoice({
        supplier: formData.supplier,
        invoice_date: formData.invoice_date,
        reference: formData.reference,
        currency: formData.currency,
        line_items: validLineItems
      })
      onCreated()
      onClose()
      // Reset form
      setFormData({ supplier: '', invoice_date: new Date().toISOString().split('T')[0], reference: '', currency: 'GBP' })
      setLineItems([{ description: '', quantity: 0, unit_price: 0, uom: '', vat_rate: 0 }])
    } catch (error) {
      console.error('Failed to create manual invoice:', error)
    } finally {
      setLoading(false)
    }
  }

  const addLineItem = () => {
    setLineItems([...lineItems, { description: '', quantity: 0, unit_price: 0, uom: '', vat_rate: 0 }])
  }

  const updateLineItem = (index: number, field: keyof LineItem, value: string | number) => {
    const updated = [...lineItems]
    updated[index] = { ...updated[index], [field]: value }
    setLineItems(updated)
  }

  const removeLineItem = (index: number) => {
    if (lineItems.length > 1) {
      setLineItems(lineItems.filter((_, i) => i !== index))
    }
  }

  const calculateTotal = () => {
    return lineItems.reduce((sum, item) => sum + (item.quantity * item.unit_price), 0)
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <Card className="w-full max-w-4xl max-h-[90vh] overflow-y-auto">
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle>Create Manual Invoice</CardTitle>
          <Button variant="ghost" size="icon" onClick={onClose}>
            <X className="h-4 w-4" />
          </Button>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-6">
            {/* Basic Invoice Info */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <Label htmlFor="supplier">Supplier *</Label>
                <Input
                  id="supplier"
                  value={formData.supplier}
                  onChange={(e) => setFormData({ ...formData, supplier: e.target.value })}
                  placeholder="Enter supplier name"
                  required
                />
              </div>
              <div>
                <Label htmlFor="reference">Reference</Label>
                <Input
                  id="reference"
                  value={formData.reference}
                  onChange={(e) => setFormData({ ...formData, reference: e.target.value })}
                  placeholder="Invoice number"
                />
              </div>
              <div>
                <Label htmlFor="invoice_date">Invoice Date *</Label>
                <Input
                  id="invoice_date"
                  type="date"
                  value={formData.invoice_date}
                  onChange={(e) => setFormData({ ...formData, invoice_date: e.target.value })}
                  required
                />
              </div>
              <div>
                <Label htmlFor="currency">Currency</Label>
                <Input
                  id="currency"
                  value={formData.currency}
                  onChange={(e) => setFormData({ ...formData, currency: e.target.value })}
                  placeholder="GBP"
                />
              </div>
            </div>

            {/* Line Items */}
            <div>
              <div className="flex items-center justify-between mb-4">
                <Label className="text-base font-medium">Line Items</Label>
                <Button type="button" onClick={addLineItem} size="sm" variant="outline">
                  <Plus className="h-4 w-4 mr-2" />
                  Add Item
                </Button>
              </div>
              
              <div className="space-y-3">
                {lineItems.map((item, index) => (
                  <div key={index} className="grid grid-cols-12 gap-2 items-end p-3 border rounded-lg">
                    <div className="col-span-5">
                      <Label className="text-xs">Description</Label>
                      <Input
                        value={item.description}
                        onChange={(e) => updateLineItem(index, 'description', e.target.value)}
                        placeholder="Item description"
                      />
                    </div>
                    <div className="col-span-2">
                      <Label className="text-xs">Qty</Label>
                      <Input
                        type="number"
                        step="0.01"
                        value={item.quantity}
                        onChange={(e) => updateLineItem(index, 'quantity', parseFloat(e.target.value) || 0)}
                        placeholder="0"
                      />
                    </div>
                    <div className="col-span-2">
                      <Label className="text-xs">Unit Price</Label>
                      <Input
                        type="number"
                        step="0.01"
                        value={item.unit_price}
                        onChange={(e) => updateLineItem(index, 'unit_price', parseFloat(e.target.value) || 0)}
                        placeholder="0.00"
                      />
                    </div>
                    <div className="col-span-2">
                      <Label className="text-xs">UOM</Label>
                      <Input
                        value={item.uom}
                        onChange={(e) => updateLineItem(index, 'uom', e.target.value)}
                        placeholder="each"
                      />
                    </div>
                    <div className="col-span-1 flex gap-1">
                      <Button
                        type="button"
                        size="sm"
                        variant="ghost"
                        onClick={() => removeLineItem(index)}
                        disabled={lineItems.length === 1}
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
              
              {/* Total */}
              <div className="mt-4 p-3 bg-gray-50 rounded-lg">
                <div className="flex justify-between items-center">
                  <span className="font-medium">Total: £{calculateTotal().toFixed(2)}</span>
                </div>
              </div>
            </div>

            <div className="flex gap-2 pt-4">
              <Button type="submit" disabled={loading} className="flex-1">
                {loading ? 'Creating...' : 'Create Invoice'}
              </Button>
              <Button type="button" variant="outline" onClick={onClose}>
                Cancel
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  )
}
