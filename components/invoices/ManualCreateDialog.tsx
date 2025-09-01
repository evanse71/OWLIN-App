import React, { useState } from 'react'
import { X, Upload, FileText } from 'lucide-react'

interface ManualCreateDialogProps {
  isOpen: boolean
  onClose: () => void
  onSubmit: (data: CreateInvoiceData) => void
  unassignedAssets?: Array<{
    id: string
    filename: string
    mime: string
    size: number
  }>
}

interface CreateInvoiceData {
  supplier_name: string
  invoice_no: string
  date_iso: string
  currency: string
  asset_ids: string[]
}

export default function ManualCreateDialog({ 
  isOpen, 
  onClose, 
  onSubmit, 
  unassignedAssets = [] 
}: ManualCreateDialogProps) {
  const [formData, setFormData] = useState<CreateInvoiceData>({
    supplier_name: '',
    invoice_no: '',
    date_iso: new Date().toISOString().split('T')[0],
    currency: 'GBP',
    asset_ids: []
  })
  
  const [selectedAssets, setSelectedAssets] = useState<Set<string>>(new Set())
  
  if (!isOpen) return null
  
  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    
    if (!formData.supplier_name || !formData.invoice_no) {
      alert('Supplier name and invoice number are required')
      return
    }
    
    onSubmit({
      ...formData,
      asset_ids: Array.from(selectedAssets)
    })
    
    // Reset form
    setFormData({
      supplier_name: '',
      invoice_no: '',
      date_iso: new Date().toISOString().split('T')[0],
      currency: 'GBP',
      asset_ids: []
    })
    setSelectedAssets(new Set())
    onClose()
  }
  
  const toggleAsset = (assetId: string) => {
    const newSelected = new Set(selectedAssets)
    if (newSelected.has(assetId)) {
      newSelected.delete(assetId)
    } else {
      newSelected.add(assetId)
    }
    setSelectedAssets(newSelected)
  }
  
  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-2xl max-h-[90vh] overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b">
          <h2 className="text-lg font-semibold">Create Invoice Manually</h2>
          <button
            onClick={onClose}
            className="p-1 hover:bg-gray-100 rounded"
          >
            <X className="h-5 w-5" />
          </button>
        </div>
        
        {/* Form */}
        <form onSubmit={handleSubmit} className="p-4 space-y-4">
          {/* Supplier */}
          <div>
            <label className="block text-sm font-medium mb-1">
              Supplier Name *
            </label>
            <input
              type="text"
              value={formData.supplier_name}
              onChange={(e) => setFormData(prev => ({ ...prev, supplier_name: e.target.value }))}
              className="w-full border rounded px-3 py-2"
              placeholder="Enter supplier name"
              required
            />
          </div>
          
          {/* Invoice details */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium mb-1">
                Invoice Number *
              </label>
              <input
                type="text"
                value={formData.invoice_no}
                onChange={(e) => setFormData(prev => ({ ...prev, invoice_no: e.target.value }))}
                className="w-full border rounded px-3 py-2"
                placeholder="INV-001"
                required
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium mb-1">
                Date
              </label>
              <input
                type="date"
                value={formData.date_iso}
                onChange={(e) => setFormData(prev => ({ ...prev, date_iso: e.target.value }))}
                className="w-full border rounded px-3 py-2"
              />
            </div>
          </div>
          
          <div className="w-32">
            <label className="block text-sm font-medium mb-1">
              Currency
            </label>
            <select
              value={formData.currency}
              onChange={(e) => setFormData(prev => ({ ...prev, currency: e.target.value }))}
              className="w-full border rounded px-3 py-2"
            >
              <option value="GBP">GBP</option>
              <option value="EUR">EUR</option>
              <option value="USD">USD</option>
            </select>
          </div>
          
          {/* Unassigned Assets */}
          {unassignedAssets.length > 0 && (
            <div>
              <label className="block text-sm font-medium mb-2">
                Attach Unassigned Assets ({selectedAssets.size} selected)
              </label>
              <div className="border rounded max-h-48 overflow-y-auto">
                {unassignedAssets.map((asset) => (
                  <div
                    key={asset.id}
                    className={`flex items-center gap-3 p-3 border-b last:border-b-0 cursor-pointer hover:bg-gray-50 ${
                      selectedAssets.has(asset.id) ? 'bg-blue-50' : ''
                    }`}
                    onClick={() => toggleAsset(asset.id)}
                  >
                    <input
                      type="checkbox"
                      checked={selectedAssets.has(asset.id)}
                      onChange={() => {}} // Handled by div click
                      className="rounded"
                    />
                    <FileText className="h-4 w-4 text-gray-400" />
                    <div className="flex-1">
                      <div className="text-sm font-medium">{asset.filename}</div>
                      <div className="text-xs text-gray-500">
                        {asset.mime} • {(asset.size / 1024).toFixed(0)}KB
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
          
          {/* Actions */}
          <div className="flex justify-end gap-3 pt-4 border-t">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-gray-600 hover:text-gray-800"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
            >
              Create Invoice
            </button>
          </div>
        </form>
      </div>
    </div>
  )
} 