import { useState } from 'react'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Plus, X } from 'lucide-react'
import type { LineItem } from '@/types'

interface CreateInvoiceModalProps {
  onCreated: (invoice: any) => void
  children: React.ReactNode
}

export default function CreateInvoiceModal({ onCreated, children }: CreateInvoiceModalProps) {
  const [open, setOpen] = useState(false)
  const [formData, setFormData] = useState({
    invoice_number: '',
    invoice_date: '',
    supplier_name: '',
    venue: '',
    line_items: [] as LineItem[]
  })

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    try {
      const response = await fetch('http://localhost:8001/invoices', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(formData)
      })
      
      if (!response.ok) {
        throw new Error('Failed to create invoice')
      }
      
      const result = await response.json()
      onCreated(result.invoice)
      setOpen(false)
      setFormData({
        invoice_number: '',
        invoice_date: '',
        supplier_name: '',
        venue: '',
        line_items: []
      })
    } catch (error) {
      console.error('Create failed:', error)
    }
  }

  const addLineItem = () => {
    setFormData(prev => ({
      ...prev,
      line_items: [...prev.line_items, {
        description: '',
        qty: 1,
        unit_price: 0,
        total: 0
      }]
    }))
  }

  const updateLineItem = (index: number, field: keyof LineItem, value: any) => {
    setFormData(prev => {
      const newItems = [...prev.line_items]
      newItems[index] = { ...newItems[index], [field]: value }
      
      // Auto-calculate total
      if (field === 'qty' || field === 'unit_price') {
        newItems[index] = {
          ...newItems[index],
          total: (newItems[index].qty || 0) * (newItems[index].unit_price || 0)
        }
      }
      
      return { ...prev, line_items: newItems }
    })
  }

  const removeLineItem = (index: number) => {
    setFormData(prev => ({
      ...prev,
      line_items: prev.line_items.filter((_, i) => i !== index)
    }))
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        {children}
      </DialogTrigger>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>Create New Invoice</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <Label htmlFor="invoice_number">Invoice Number</Label>
              <Input
                id="invoice_number"
                value={formData.invoice_number}
                onChange={(e) => setFormData(prev => ({ ...prev, invoice_number: e.target.value }))}
                required
              />
            </div>
            <div>
              <Label htmlFor="invoice_date">Date</Label>
              <Input
                id="invoice_date"
                type="date"
                value={formData.invoice_date}
                onChange={(e) => setFormData(prev => ({ ...prev, invoice_date: e.target.value }))}
                required
              />
            </div>
          </div>
          
          <div className="grid grid-cols-2 gap-4">
            <div>
              <Label htmlFor="supplier_name">Supplier</Label>
              <Input
                id="supplier_name"
                value={formData.supplier_name}
                onChange={(e) => setFormData(prev => ({ ...prev, supplier_name: e.target.value }))}
                required
              />
            </div>
            <div>
              <Label htmlFor="venue">Venue</Label>
              <Input
                id="venue"
                value={formData.venue}
                onChange={(e) => setFormData(prev => ({ ...prev, venue: e.target.value }))}
              />
            </div>
          </div>

          <div>
            <div className="flex items-center justify-between mb-2">
              <Label>Line Items</Label>
              <Button type="button" size="sm" onClick={addLineItem}>
                <Plus className="h-4 w-4 mr-2" />
                Add Item
              </Button>
            </div>
            
            <div className="space-y-2">
              {(formData.line_items || []).map((item, index) => (
                <div key={index} className="grid grid-cols-12 gap-2 items-center p-2 bg-gray-50 rounded">
                  <div className="col-span-4">
                    <Input
                      placeholder="Description"
                      value={item.description}
                      onChange={(e) => updateLineItem(index, 'description', e.target.value)}
                    />
                  </div>
                  <div className="col-span-2">
                    <Input
                      type="number"
                      placeholder="Qty"
                      value={item.qty}
                      onChange={(e) => updateLineItem(index, 'qty', parseFloat(e.target.value) || 0)}
                    />
                  </div>
                  <div className="col-span-2">
                    <Input
                      type="number"
                      placeholder="Unit £"
                      value={item.unit_price}
                      onChange={(e) => updateLineItem(index, 'unit_price', parseFloat(e.target.value) || 0)}
                    />
                  </div>
                  <div className="col-span-2">
                    <Input
                      type="number"
                      placeholder="Total"
                      value={item.total}
                      readOnly
                    />
                  </div>
                  <div className="col-span-1">
                    <Button
                      type="button"
                      size="sm"
                      variant="outline"
                      onClick={() => removeLineItem(index)}
                    >
                      <X className="h-3 w-3" />
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="flex justify-end gap-2">
            <Button type="button" variant="outline" onClick={() => setOpen(false)}>
              Cancel
            </Button>
            <Button type="submit">
              Create Invoice
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  )
} 