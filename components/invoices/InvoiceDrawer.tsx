import React, { useState } from 'react'
import { X, FileText, Link, Plus, Copy } from 'lucide-react'

interface InvoiceLine {
  id: string
  sku: string
  description: string
  quantity_each: number
  packs?: number
  units_per_pack?: number
  quantity_ml?: number
  quantity_l?: number
  quantity_g?: number
  unit_price: number
  nett_price: number
  line_total: number
  vat_rate?: number
  flags: string[]
  verdict: string
  discount?: {
    kind: 'percent' | 'per_case' | 'per_litre'
    value: number
    residual_pennies: number
    implied_pct?: number
  }
  pairing?: {
    dn_id?: string
    qty_match_pct?: number
  }
}

interface InvoicePage {
  id: string
  page_no: number
  ocr_avg_conf_page: number
}

interface InvoiceDrawerProps {
  invoice: {
    id: string
    supplier: string
    invoice_no: string
    date_iso: string
    currency: string
    ocr_avg_conf: number
    ocr_min_conf: number
    total_inc: number
    pages: InvoicePage[]
    lines: InvoiceLine[]
  }
  isOpen: boolean
  onClose: () => void
}

export default function InvoiceDrawer({ invoice, isOpen, onClose }: InvoiceDrawerProps) {
  const [selectedLine, setSelectedLine] = useState<string | null>(null)
  
  if (!isOpen) return null
  
  const formatQuantity = (line: InvoiceLine) => {
    const parts = []
    
    if (line.packs && line.units_per_pack) {
      parts.push(`${line.packs}×${line.units_per_pack}`)
    }
    
    if (line.quantity_ml) {
      parts.push(`${line.quantity_ml}ml`)
    } else if (line.quantity_l) {
      parts.push(`${line.quantity_l}L`)
    } else if (line.quantity_g) {
      parts.push(`${line.quantity_g}g`)
    }
    
    return parts.join(' • ') || `${line.quantity_each} each`
  }
  
  const getVerdictBadge = (verdict: string) => {
    const badgeClasses: Record<string, string> = {
      'OCR_LOW_CONF': 'bg-yellow-100 text-yellow-800',
      'PACK_MISMATCH': 'bg-orange-100 text-orange-800',
      'PRICE_INCOHERENT': 'bg-red-100 text-red-800',
      'VAT_MISMATCH': 'bg-red-100 text-red-800',
      'OFF_CONTRACT_DISCOUNT': 'bg-blue-100 text-blue-800',
      'OK_ON_CONTRACT': 'bg-green-100 text-green-800'
    }
    
    return (
      <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${badgeClasses[verdict] || 'bg-gray-100 text-gray-800'}`}>
        {verdict.replace(/_/g, ' ')}
      </span>
    )
  }
  
  const getPairingStatus = (line: InvoiceLine) => {
    if (line.pairing?.dn_id) {
      return (
        <div className="flex items-center gap-2">
          <span className="text-sm text-green-600">
            DN-{line.pairing.dn_id.slice(-4)}
          </span>
          {line.pairing.qty_match_pct && (
            <span className="text-xs text-gray-500">
              {line.pairing.qty_match_pct.toFixed(0)}%
            </span>
          )}
        </div>
      )
    }
    
    return (
      <div className="flex items-center gap-1">
        <button
          className="text-xs text-blue-600 hover:text-blue-800"
          onClick={() => handleLinkToDN(line.id)}
        >
          Link to DN...
        </button>
        <button
          className="text-xs text-green-600 hover:text-green-800"
          onClick={() => handleCreateDN(line.id)}
        >
          Create DN
        </button>
      </div>
    )
  }
  
  const handleLinkToDN = (lineId: string) => {
    // Open DN selection modal
    console.log('Link line to DN:', lineId)
  }
  
  const handleCreateDN = (lineId: string) => {
    // Open DN creation modal seeded from this line
    console.log('Create DN from line:', lineId)
  }
  
  const handleCopyForensic = (lineId: string) => {
    // Copy forensic JSON to clipboard
    const line = invoice.lines.find(l => l.id === lineId)
    if (line) {
      navigator.clipboard.writeText(JSON.stringify(line, null, 2))
    }
  }
  
  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 z-50">
      <div className="fixed right-0 top-0 h-full w-[90vw] max-w-6xl bg-white shadow-xl">
        <div className="flex h-full">
          {/* Left pane - Page thumbnails */}
          <div className="w-64 border-r bg-gray-50 p-4">
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-medium">Pages ({invoice.pages.length})</h3>
              <button
                onClick={onClose}
                className="p-1 hover:bg-gray-200 rounded"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
            
            <div className="space-y-3">
              {invoice.pages.map((page) => (
                <div key={page.id} className="border rounded p-2 bg-white">
                  <div className="aspect-[3/4] bg-gray-100 rounded mb-2 flex items-center justify-center">
                    <FileText className="h-8 w-8 text-gray-400" />
                  </div>
                  <div className="text-xs">
                    <div>Page {page.page_no}</div>
                    <div className={`font-medium ${page.ocr_avg_conf_page < 50 ? 'text-red-600' : page.ocr_avg_conf_page < 70 ? 'text-yellow-600' : 'text-green-600'}`}>
                      {page.ocr_avg_conf_page.toFixed(0)}% conf
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
          
          {/* Right pane - Invoice details */}
          <div className="flex-1 flex flex-col">
            {/* Header */}
            <div className="border-b p-4">
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-xl font-semibold">{invoice.invoice_no}</h2>
                  <p className="text-gray-600">{invoice.supplier} • {invoice.date_iso}</p>
                </div>
                <div className="text-right">
                  <div className="text-2xl font-bold">{invoice.currency} {invoice.total_inc.toFixed(2)}</div>
                  <div className={`text-sm ${invoice.ocr_avg_conf < 50 ? 'text-red-600' : invoice.ocr_avg_conf < 70 ? 'text-yellow-600' : 'text-green-600'}`}>
                    OCR: {invoice.ocr_avg_conf.toFixed(0)}% avg
                  </div>
                </div>
              </div>
            </div>
            
            {/* Lines table - 5 columns only */}
            <div className="flex-1 overflow-auto">
              <table className="w-full">
                <thead className="bg-gray-50 sticky top-0">
                  <tr>
                    <th className="text-left p-3 font-medium">Item</th>
                    <th className="text-left p-3 font-medium">Quantity</th>
                    <th className="text-left p-3 font-medium">Money</th>
                    <th className="text-left p-3 font-medium">Badges</th>
                    <th className="text-left p-3 font-medium">Pairing</th>
                  </tr>
                </thead>
                <tbody>
                  {invoice.lines.map((line) => (
                    <tr 
                      key={line.id}
                      className={`border-b hover:bg-gray-50 ${selectedLine === line.id ? 'bg-blue-50' : ''}`}
                      onClick={() => setSelectedLine(line.id)}
                    >
                      {/* Column 1: Item */}
                      <td className="p-3">
                        <div>
                          <div className="font-medium">{line.sku}</div>
                          <div className="text-sm text-gray-600" title={line.description}>
                            {line.description.length > 40 
                              ? line.description.substring(0, 40) + '...'
                              : line.description
                            }
                          </div>
                        </div>
                      </td>
                      
                      {/* Column 2: Quantity (canonical) */}
                      <td className="p-3">
                        <div className="font-medium">{formatQuantity(line)}</div>
                        <div className="text-xs text-gray-500">
                          {line.quantity_each} each
                        </div>
                      </td>
                      
                      {/* Column 3: Money */}
                      <td className="p-3">
                        <div>£{line.unit_price.toFixed(2)}</div>
                        <div className="text-sm">£{line.line_total.toFixed(2)}</div>
                        {line.discount && (
                          <div className="text-xs text-blue-600">
                            -{line.discount.implied_pct?.toFixed(1) || line.discount.value.toFixed(1)}%
                          </div>
                        )}
                      </td>
                      
                      {/* Column 4: Badges (ordered by priority) */}
                      <td className="p-3">
                        <div className="flex flex-wrap gap-1">
                          {getVerdictBadge(line.verdict)}
                          {line.flags.map(flag => (
                            <span key={flag} className="inline-flex items-center px-1 py-0.5 rounded text-xs bg-gray-100 text-gray-700">
                              {flag}
                            </span>
                          ))}
                        </div>
                      </td>
                      
                      {/* Column 5: Pairing */}
                      <td className="p-3">
                        <div className="flex items-center gap-2">
                          {getPairingStatus(line)}
                          <button
                            onClick={() => handleCopyForensic(line.id)}
                            className="p-1 hover:bg-gray-200 rounded"
                            title="Copy forensic JSON"
                          >
                            <Copy className="h-3 w-3" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
} 