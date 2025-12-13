import React, { useState, useEffect } from 'react'
import { FileText, Image as ImageIcon, File, Plus, Trash2 } from 'lucide-react'

interface UnassignedAsset {
  id: string
  filename: string
  mime: string
  size: number
  uploaded_at: string
  thumbnail_url?: string
}

interface UnassignedAssetsPanelProps {
  onCreateInvoice: (assetIds: string[]) => void
  onCreateDN: (assetIds: string[]) => void
  onDeleteAssets: (assetIds: string[]) => void
}

export default function UnassignedAssetsPanel({
  onCreateInvoice,
  onCreateDN,
  onDeleteAssets
}: UnassignedAssetsPanelProps) {
  const [assets, setAssets] = useState<UnassignedAsset[]>([])
  const [selectedAssets, setSelectedAssets] = useState<Set<string>>(new Set())
  const [loading, setLoading] = useState(true)
  
  useEffect(() => {
    fetchUnassignedAssets()
  }, [])
  
  const fetchUnassignedAssets = async () => {
    try {
      setLoading(true)
      const response = await fetch('/api/assets/unassigned')
      const data = await response.json()
      setAssets(data.assets || [])
    } catch (error) {
      console.error('Failed to fetch unassigned assets:', error)
      setAssets([])
    } finally {
      setLoading(false)
    }
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
  
  const selectAll = () => {
    setSelectedAssets(new Set(assets.map(a => a.id)))
  }
  
  const clearSelection = () => {
    setSelectedAssets(new Set())
  }
  
  const getFileIcon = (mime: string) => {
    if (mime.startsWith('image/')) {
      return <ImageIcon className="h-4 w-4" />
    }
    if (mime === 'application/pdf') {
      return <FileText className="h-4 w-4" />
    }
    return <File className="h-4 w-4" />
  }
  
  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes}B`
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)}KB`
    return `${(bytes / (1024 * 1024)).toFixed(1)}MB`
  }
  
  const handleCreateInvoice = () => {
    if (selectedAssets.size === 0) {
      alert('Please select at least one asset')
      return
    }
    onCreateInvoice(Array.from(selectedAssets))
    clearSelection()
  }
  
  const handleCreateDN = () => {
    if (selectedAssets.size === 0) {
      alert('Please select at least one asset')
      return
    }
    onCreateDN(Array.from(selectedAssets))
    clearSelection()
  }
  
  const handleDelete = () => {
    if (selectedAssets.size === 0) {
      alert('Please select assets to delete')
      return
    }
    if (confirm(`Delete ${selectedAssets.size} asset(s)? This cannot be undone.`)) {
      onDeleteAssets(Array.from(selectedAssets))
      clearSelection()
      fetchUnassignedAssets() // Refresh list
    }
  }
  
  if (loading) {
    return (
      <div className="bg-white rounded-lg border p-4">
        <div className="animate-pulse">
          <div className="h-4 bg-gray-200 rounded w-1/3 mb-4"></div>
          <div className="space-y-3">
            {[1, 2, 3].map(i => (
              <div key={i} className="h-12 bg-gray-200 rounded"></div>
            ))}
          </div>
        </div>
      </div>
    )
  }
  
  return (
    <div className="bg-white rounded-lg border">
      {/* Header */}
      <div className="p-4 border-b">
        <div className="flex items-center justify-between">
          <h3 className="font-medium">
            Unassigned Assets ({assets.length})
          </h3>
          {assets.length > 0 && (
            <div className="flex items-center gap-2 text-xs">
              <button
                onClick={selectAll}
                className="text-blue-600 hover:text-blue-800"
              >
                Select All
              </button>
              {selectedAssets.size > 0 && (
                <button
                  onClick={clearSelection}
                  className="text-gray-600 hover:text-gray-800"
                >
                  Clear ({selectedAssets.size})
                </button>
              )}
            </div>
          )}
        </div>
      </div>
      
      {/* Asset list */}
      <div className="max-h-96 overflow-y-auto">
        {assets.length === 0 ? (
          <div className="p-8 text-center text-gray-500">
            <FileText className="h-12 w-12 text-gray-300 mx-auto mb-3" />
            <p>No unassigned assets</p>
            <p className="text-sm">Upload files to get started</p>
          </div>
        ) : (
          <div className="divide-y">
            {assets.map((asset) => (
              <div
                key={asset.id}
                className={`flex items-center gap-3 p-3 cursor-pointer hover:bg-gray-50 ${
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
                
                <div className="text-gray-400">
                  {getFileIcon(asset.mime)}
                </div>
                
                <div className="flex-1 min-w-0">
                  <div className="text-sm font-medium truncate">
                    {asset.filename}
                  </div>
                  <div className="text-xs text-gray-500">
                    {formatFileSize(asset.size)} • {new Date(asset.uploaded_at).toLocaleDateString()}
                  </div>
                </div>
                
                {asset.thumbnail_url && (
                  <div className="w-8 h-8 bg-gray-100 rounded overflow-hidden">
                    <img 
                      src={asset.thumbnail_url}
                      alt="Thumbnail"
                      className="w-full h-full object-cover"
                    />
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
      
      {/* Actions */}
      {selectedAssets.size > 0 && (
        <div className="p-3 border-t bg-gray-50">
          <div className="flex items-center justify-between">
            <span className="text-sm text-gray-600">
              {selectedAssets.size} selected
            </span>
            
            <div className="flex items-center gap-2">
              <button
                onClick={handleCreateInvoice}
                className="flex items-center gap-1 px-3 py-1 bg-blue-600 text-white rounded text-sm hover:bg-blue-700"
              >
                <Plus className="h-3 w-3" />
                Invoice
              </button>
              
              <button
                onClick={handleCreateDN}
                className="flex items-center gap-1 px-3 py-1 bg-green-600 text-white rounded text-sm hover:bg-green-700"
              >
                <Plus className="h-3 w-3" />
                Delivery Note
              </button>
              
              <button
                onClick={handleDelete}
                className="flex items-center gap-1 px-3 py-1 bg-red-600 text-white rounded text-sm hover:bg-red-700"
              >
                <Trash2 className="h-3 w-3" />
                Delete
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
} 