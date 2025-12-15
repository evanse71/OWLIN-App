import { memo, useState } from 'react'
import type { InvoiceMetadata } from '../../lib/upload'
import { DetailPanelTabs, type TabId } from './DetailPanelTabs'
import { ConfidenceMeter } from './ConfidenceMeter'
import { PairingSuggestions, type PairingSuggestion } from './PairingSuggestions'
import './EnhancedInvoiceDetailPanel.css'

interface EnhancedInvoiceDetailPanelProps {
  invoice: {
    id: string
    file: File
    metadata?: InvoiceMetadata
  }
  isVisible: boolean
  onClose: () => void
}

export const EnhancedInvoiceDetailPanel = memo(function EnhancedInvoiceDetailPanel({
  invoice,
  isVisible,
  onClose,
}: EnhancedInvoiceDetailPanelProps) {
  const [activeTab, setActiveTab] = useState<TabId>('overview')
  const metadata = invoice.metadata || {}
  const pages = metadata.pages || []
  const lineItems = metadata.lineItems || []
  const invoiceId = metadata.id ?? invoice.id
  const confidence = metadata.confidence ?? null

  // Pairing suggestions - fetched from API when needed
  const pairingSuggestions: PairingSuggestion[] = []

  const formatDate = (dateString?: string): string => {
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

  const formatCurrency = (value?: number): string => {
    if (value === undefined || value === null) return 'Not provided'
    return new Intl.NumberFormat('en-GB', {
      style: 'currency',
      currency: 'GBP',
    }).format(value)
  }

  const tabs = [
    { id: 'overview' as TabId, label: 'Overview', icon: '📋' },
    { id: 'lineItems' as TabId, label: 'Line Items', icon: '📝', badge: lineItems.length },
    { id: 'issues' as TabId, label: 'Issues', icon: '⚠️', badge: 0 },
    { id: 'pairing' as TabId, label: 'Pairing', icon: '🔗', badge: pairingSuggestions.length },
  ]

  if (!isVisible) return null

  return (
    <>
      <div className="detail-panel-overlay" onClick={onClose} />
      <div className={`enhanced-detail-panel ${isVisible ? 'visible' : ''}`}>
        <div className="detail-panel-header-sticky">
          <div className="detail-panel-header">
            <div className="detail-panel-header-main">
              <h2 className="detail-panel-title">
                {metadata.supplier || 'Unknown Supplier'}
              </h2>
              <button
                className="detail-panel-close"
                onClick={onClose}
                aria-label="Close panel"
              >
                <svg
                  width="20"
                  height="20"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  <line x1="18" y1="6" x2="6" y2="18" />
                  <line x1="6" y1="6" x2="18" y2="18" />
                </svg>
              </button>
            </div>
            <div className="detail-panel-header-meta">
              <span className="detail-panel-meta-item">
                <strong>Date:</strong> {formatDate(metadata.date)}
              </span>
              <span className="detail-panel-meta-item">
                <strong>Total:</strong> {formatCurrency(metadata.value)}
              </span>
              {confidence !== null && (
                <span className="detail-panel-meta-item">
                  <strong>ID:</strong> {String(invoiceId).slice(0, 12)}
                </span>
              )}
            </div>
            {confidence !== null && (
              <div className="detail-panel-confidence">
                <ConfidenceMeter confidence={confidence} />
              </div>
            )}
          </div>
        </div>

        <DetailPanelTabs tabs={tabs} activeTab={activeTab} onTabChange={setActiveTab}>
          {activeTab === 'overview' && (
            <div className="detail-panel-tab-content">
              <div className="detail-panel-section">
                <h3 className="detail-panel-section-title">Key Fields</h3>
                <div className="detail-panel-fields-grid">
                  <div className="detail-panel-field">
                    <label>Supplier</label>
                    <div>{metadata.supplier || 'Not provided'}</div>
                  </div>
                  <div className="detail-panel-field">
                    <label>Invoice No.</label>
                    <div>{metadata.invoiceNo || 'Not provided'}</div>
                  </div>
                  <div className="detail-panel-field">
                    <label>Date</label>
                    <div>{formatDate(metadata.date)}</div>
                  </div>
                  {metadata.subtotal !== undefined && (
                    <div className="detail-panel-field">
                      <label>Subtotal</label>
                      <div>{formatCurrency(metadata.subtotal as number)}</div>
                    </div>
                  )}
                  {metadata.vat !== undefined && (
                    <div className="detail-panel-field">
                      <label>VAT</label>
                      <div>{formatCurrency(metadata.vat as number)}</div>
                    </div>
                  )}
                  {metadata.total !== undefined && (
                    <div className="detail-panel-field">
                      <label>Total</label>
                      <div className="detail-panel-field-value-large">
                        {formatCurrency(metadata.total as number)}
                      </div>
                    </div>
                  )}
                </div>
              </div>

              {pages.length > 0 && (
                <div className="detail-panel-section">
                  <h3 className="detail-panel-section-title">Pages</h3>
                  <div className="detail-panel-pages">
                    {pages.map((page, idx) => (
                      <div key={idx} className="detail-panel-page-badge">
                        <span>Page {page.index ?? idx + 1}</span>
                        {page.confidence !== undefined && (
                          <span className="detail-panel-page-confidence">
                            {page.confidence.toFixed(1)}%
                          </span>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {activeTab === 'lineItems' && (
            <div className="detail-panel-tab-content">
              {lineItems.length > 0 ? (
                <div className="detail-panel-line-items">
                  <table className="detail-panel-table">
                    <thead>
                      <tr>
                        <th>Item</th>
                        <th className="text-right">Qty</th>
                        <th>Unit</th>
                        <th className="text-right">Price</th>
                        <th className="text-right">Total</th>
                      </tr>
                    </thead>
                    <tbody>
                      {lineItems.map((item, idx) => (
                        <tr key={idx}>
                          <td>{item.description || item.item || '-'}</td>
                          <td className="text-right">{item.qty ?? item.quantity ?? '-'}</td>
                          <td>{item.unit || item.uom || '-'}</td>
                          <td className="text-right">
                            {item.price !== undefined ? formatCurrency(item.price) : '-'}
                          </td>
                          <td className="text-right detail-panel-line-total">
                            {item.total !== undefined
                              ? formatCurrency(item.total)
                              : item.line_total !== undefined
                              ? formatCurrency(item.line_total)
                              : '-'}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <div className="detail-panel-empty">No line items available</div>
              )}
            </div>
          )}

          {activeTab === 'issues' && (
            <div className="detail-panel-tab-content">
              <div className="detail-panel-empty">No issues detected</div>
            </div>
          )}

          {activeTab === 'pairing' && (
            <div className="detail-panel-tab-content">
              <PairingSuggestions
                suggestions={pairingSuggestions}
                onSelect={(suggestion) => {
                  console.log('Selected pairing:', suggestion)
                }}
              />
            </div>
          )}
        </DetailPanelTabs>

        <div className="detail-panel-actions">
          <button className="detail-panel-action-primary">Submit to Owlin</button>
          <button className="detail-panel-action-secondary">Pair Delivery Note</button>
          <button className="detail-panel-action-tertiary">Flag Issue</button>
        </div>
      </div>
    </>
  )
})

