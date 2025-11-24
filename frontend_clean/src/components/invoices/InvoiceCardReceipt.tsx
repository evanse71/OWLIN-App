import { memo } from 'react'
import type { FileItem } from '../../pages/Invoices'
import './InvoiceCardReceipt.css'

interface InvoiceCardReceiptProps {
  invoice: FileItem
  isSelected: boolean
  onClick: () => void
}

function formatCurrency(value?: number): string {
  if (value === undefined || value === null) return '—'
  return new Intl.NumberFormat('en-GB', {
    style: 'currency',
    currency: 'GBP',
  }).format(value)
}

function formatDate(dateString?: string): string {
  if (!dateString) return '—'
  try {
    return new Date(dateString).toLocaleDateString('en-GB', {
      day: 'numeric',
      month: 'short',
      year: 'numeric',
    })
  } catch {
    return dateString
  }
}

function getStatusBadge(status: FileItem['status']) {
  switch (status) {
    case 'uploading':
      return { emoji: '🟡', text: 'Scanning', color: 'yellow' }
    case 'scanned':
      return { emoji: '🟢', text: 'Processed', color: 'green' }
    case 'submitted':
      return { emoji: '🔵', text: 'Matched', color: 'blue' }
    case 'error':
      return { emoji: '🔴', text: 'Flagged', color: 'red' }
    default:
      return { emoji: '⚪', text: 'Pending', color: 'gray' }
  }
}

export const InvoiceCard = memo(function InvoiceCardReceipt({
  invoice,
  isSelected,
  onClick,
}: InvoiceCardReceiptProps) {
  const statusBadge = getStatusBadge(invoice.status)
  const confidence = invoice.metadata?.confidence
  const pages = invoice.metadata?.pages || []
  const pageCount = pages.length

  // Read-time fallback aliasing (non-mutating)
  const metadata = invoice.metadata || {}
  const supplier = metadata.supplier || metadata.supplier_name
  const total = metadata.total || metadata.total_value || metadata.value
  const date = metadata.date || metadata.invoice_date
  const lineItems = metadata.lineItems || metadata.line_items || []
  const itemCount = lineItems.length

  // Extract short filename or invoice ID
  const shortId = invoice.metadata?.id
    ? `INV-${String(invoice.metadata.id).slice(-6)}`
    : invoice.file.name.length > 20
    ? invoice.file.name.substring(0, 20) + '...'
    : invoice.file.name

  return (
    <div
      className={`invoice-card-receipt ${isSelected ? 'selected' : ''} ${invoice.submitted ? 'submitted' : ''}`}
      onClick={onClick}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault()
          onClick()
        }
      }}
    >
      {/* Top Row */}
      <div className="invoice-card-top">
        <span className="invoice-card-id">{shortId.toUpperCase()}</span>
        <span className="invoice-card-date">{formatDate(date)}</span>
      </div>

      {/* Middle - Supplier & Value */}
      <div className="invoice-card-middle">
        <div className="invoice-card-supplier">
          {supplier || 'Unknown Supplier'}
        </div>
        <div className="invoice-card-value">
          {formatCurrency(total)}
        </div>
        {invoice.metadata?.vat !== undefined && (
          <div className="invoice-card-vat">
            VAT: {formatCurrency(invoice.metadata.vat)}
          </div>
        )}
      </div>

      {/* Badges */}
      <div className="invoice-card-badges">
        <span className={`invoice-card-status-badge status-${statusBadge.color}`}>
          {statusBadge.emoji} {statusBadge.text}
        </span>
        {confidence !== undefined && (
          <span className="invoice-card-confidence-badge" title={`OCR Confidence: ${confidence.toFixed(1)}%`}>
            OCR {confidence.toFixed(0)}%
          </span>
        )}
        {pageCount > 1 && (
          <span className="invoice-card-page-badge">
            {pageCount} pages
          </span>
        )}
        {itemCount > 0 && (
          <span className="invoice-card-item-badge">
            {itemCount} item{itemCount !== 1 ? 's' : ''}
          </span>
        )}
      </div>

      {/* Progress Bar */}
      {invoice.status === 'uploading' && (
        <div className="invoice-card-progress">
          <div
            className="invoice-card-progress-bar"
            style={{ width: `${invoice.progress}%` }}
          />
        </div>
      )}
    </div>
  )
})

