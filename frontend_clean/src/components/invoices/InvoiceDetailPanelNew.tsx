import { memo, useState } from 'react'
import type { FileItem, RequestLogEntry } from '../../pages/Invoices'
import { InvoiceDebugPanel } from '../InvoiceDebugPanel'
import './InvoiceDetailPanelNew.css'

type TabId = 'contents' | 'deliveryNote' | 'issues' | 'debug'

interface InvoiceDetailPanelNewProps {
  invoice: FileItem
  requestLog: RequestLogEntry[]
  devMode: boolean
}

function formatCurrency(value?: number): string {
  if (value === undefined || value === null) return '—'
  return new Intl.NumberFormat('en-GB', {
    style: 'currency',
    currency: 'GBP',
  }).format(value)
}

function formatDate(dateString?: string): string {
  if (!dateString) return 'Not provided'
  try {
    return new Date(dateString).toLocaleDateString('en-GB', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    })
  } catch {
    return dateString
  }
}

export const InvoiceDetailPanel = memo(function InvoiceDetailPanelNew({
  invoice,
  requestLog,
  devMode,
}: InvoiceDetailPanelNewProps) {
  if (!invoice || !invoice.file) {
    return (
      <div className="invoice-detail-panel">
        <div className="invoice-detail-empty">No invoice selected</div>
      </div>
    )
  }

  const [activeTab, setActiveTab] = useState<TabId>('contents')
  const metadata = invoice?.metadata || {}
  
  // Read-time fallback aliasing (non-mutating)
  const supplier = metadata.supplier || metadata.supplier_name
  const total = metadata.total || metadata.total_value || metadata.value
  const date = metadata.date || metadata.invoice_date
  const lineItems = metadata.lineItems || metadata.line_items || []
  const pages = metadata?.pages || []

  const tabs = [
    { id: 'contents' as TabId, label: 'Invoice Contents', icon: '📋' },
    { id: 'deliveryNote' as TabId, label: 'Delivery Note Match', icon: '🚚' },
    { id: 'issues' as TabId, label: 'Flagged Issues', icon: '⚠️', badge: 0 },
    ...(devMode ? [{ id: 'debug' as TabId, label: 'Debug / OCR', icon: '🔧' }] : []),
  ]

  return (
    <div className="invoice-detail-panel">
      {/* Sticky Header */}
      <div className="invoice-detail-header">
        <div className="invoice-detail-header-main">
          <div className="invoice-detail-header-left">
            <h2 className="invoice-detail-title">
              {invoice?.file?.name || 'Unknown Invoice'}
            </h2>
            <div className="invoice-detail-meta">
              <span>{formatDate(date)}</span>
              {date && <span>•</span>}
              <span>{formatCurrency(total)}</span>
            </div>
          </div>
          <div className="invoice-detail-header-right">
            <div className="invoice-detail-status-badge">
              {invoice?.submitted ? 'Matched' : invoice?.status === 'scanned' ? 'Awaiting DN' : 'Flagged'}
            </div>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="invoice-detail-tabs">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            className={`invoice-detail-tab ${activeTab === tab.id ? 'active' : ''}`}
            onClick={() => setActiveTab(tab.id)}
          >
            <span>{tab.icon}</span>
            <span>{tab.label}</span>
            {tab.badge !== undefined && tab.badge > 0 && (
              <span className="invoice-detail-tab-badge">{tab.badge}</span>
            )}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      <div className="invoice-detail-content">
        {activeTab === 'contents' && (
          <div className="invoice-detail-section">
            {lineItems.length > 0 ? (
              <table className="invoice-detail-table">
                <thead>
                  <tr>
                    <th>Description</th>
                    <th className="text-right">Qty</th>
                    <th className="text-right">Unit Price</th>
                    <th className="text-right">Total</th>
                    <th className="text-right">Variance</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {lineItems.map((item, idx) => {
                    // Read-time fallbacks for line item fields
                    const qty = item.qty ?? item.quantity
                    const unitPrice = item.unitPrice ?? item.price ?? item.unit_price
                    const lineTotal = item.lineTotal ?? item.total ?? item.line_total
                    
                    return (
                      <tr key={idx} className={item.variance ? 'has-variance' : ''}>
                        <td>{item.description || item.item || '—'}</td>
                        <td className="text-right">{qty ?? '—'}</td>
                        <td className="text-right">
                          {unitPrice !== undefined ? formatCurrency(unitPrice) : '—'}
                        </td>
                        <td className="text-right">
                          {lineTotal !== undefined ? formatCurrency(lineTotal) : '—'}
                        </td>
                      <td className="text-right">
                        {item.variance ? (
                          <span className="variance-badge">{item.variance}</span>
                        ) : (
                          '—'
                        )}
                      </td>
                      <td>
                        {item.variance ? (
                          <span className="status-badge flagged">Flagged</span>
                        ) : (
                          <span className="status-badge ok">OK</span>
                        )}
                      </td>
                    </tr>
                    )
                  })}
                </tbody>
              </table>
            ) : (
              <div className="invoice-detail-empty">No line items available</div>
            )}
          </div>
        )}

        {activeTab === 'deliveryNote' && (
          <div className="invoice-detail-section">
            <div className="delivery-note-match">
              <div className="delivery-note-card">
                <div className="delivery-note-header">
                  <span className="delivery-note-id">DN-02394</span>
                  <span className="delivery-note-similarity">Similarity 94%</span>
                </div>
                <div className="delivery-note-meta">
                  <span>Dated 14 Oct</span>
                </div>
                <button className="delivery-note-compare">View Comparison</button>
              </div>
              <p className="delivery-note-hint">
                Click to view side-by-side item comparison
              </p>
            </div>
          </div>
        )}

        {activeTab === 'issues' && (
          <div className="invoice-detail-section">
            <div className="invoice-detail-empty">No issues detected</div>
          </div>
        )}

        {activeTab === 'debug' && devMode && (
          <div className="invoice-detail-section">
            <InvoiceDebugPanel
              invoice={invoice}
              requestLog={requestLog}
              onSimulateError={() => {}}
            />
          </div>
        )}
      </div>
    </div>
  )
})

