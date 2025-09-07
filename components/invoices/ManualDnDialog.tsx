import React, { useState } from 'react'
import { X, FileText, Copy, Upload } from 'lucide-react'

interface ManualDnDialogProps {
  isOpen: boolean
  onClose: () => void
  onSubmit: (data: CreateDnData) => void
  seedFromInvoice?: {
    id: string
    supplier_name: string
    date_iso: string
  }
  unassignedAssets?: Array<{
    id: string
    filename: string
    mime: string
    size: number
  }>
}

interface CreateDnData {
  supplier_name: string
  date_iso: string
  asset_ids: string[]
  from_invoice_id?: string
  seed_lines: boolean
}

export default function ManualDnDialog({ 
  isOpen, 
  onClose, 
  onSubmit,
  seedFromInvoice,
  unassignedAssets = []
}: ManualDnDialogProps) {
  const [formData, setFormData] = useState<CreateDnData>({
    supplier_name: seedFromInvoice?.supplier_name || '',
    date_iso: seedFromInvoice?.date_iso || new Date().toISOString().split('T')[0],
    asset_ids: [],
    from_invoice_id: seedFromInvoice?.id,
    seed_lines: Boolean(seedFromInvoice)
  })
  
  const [selectedAssets, setSelectedAssets] = useState<Set<string>>(new Set())
  
  if (!isOpen) return null
  
  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    
    if (!formData.supplier_name) {
      alert('Supplier name is required')
      return
    }
    
    onSubmit({
      ...formData,
      asset_ids: Array.from(selectedAssets)
    })
    
    // Reset form
    setFormData({
      supplier_name: '',
      date_iso: new Date().toISOString().split('T')[0],
      asset_ids: [],
      seed_lines: false
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
          <h2 className="text-lg font-semibold">
            Create Delivery Note
            {seedFromInvoice && (
              <span className="text-sm text-gray-500 ml-2">
                (from {seedFromInvoice.id})
              </span>
            )}
          </h2>
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
          
          {/* Date */}
          <div>
            <label className="block text-sm font-medium mb-1">
              Delivery Date
            </label>
            <input
              type="date"
              value={formData.date_iso}
              onChange={(e) => setFormData(prev => ({ ...prev, date_iso: e.target.value }))}
              className="w-full border rounded px-3 py-2"
            />
          </div>
          
          {/* Seed options */}
          {seedFromInvoice && (
            <div className="bg-blue-50 p-3 rounded">
              <label className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={formData.seed_lines}
                  onChange={(e) => setFormData(prev => ({ ...prev, seed_lines: e.target.checked }))}
                  className="rounded"
                />
                <span className="text-sm">
                  Copy line items from invoice {seedFromInvoice.id}
                </span>
              </label>
            </div>
          )}
          
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
          
          {/* Upload new files */}
          <div className="border-2 border-dashed border-gray-300 rounded-lg p-6 text-center">
            <Upload className="h-8 w-8 text-gray-400 mx-auto mb-2" />
            <div className="text-sm text-gray-600 mb-2">
              Or upload new files for this invoice
            </div>
            <input
              type="file"
              accept=".pdf,.png,.jpg,.jpeg"
              multiple
              className="hidden"
              id="manual-upload"
            />
            <label
              htmlFor="manual-upload"
              className="inline-flex items-center px-3 py-2 border border-gray-300 rounded text-sm hover:bg-gray-50 cursor-pointer"
            >
              Choose Files
            </label>
          </div>
          
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