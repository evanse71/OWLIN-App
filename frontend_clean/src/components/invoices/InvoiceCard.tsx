import { memo } from 'react'
import { DualPurposeBadge } from './DualPurposeBadge'
import type { Invoice } from './VirtualizedInvoiceList'
import './InvoiceCard.css'

interface InvoiceCardProps {
  invoice: Invoice
  isSelected: boolean
  onClick: () => void
}

function getStatusColor(status: Invoice['status']): string {
  switch (status) {
    case 'matched':
      return 'success'
    case 'flagged':
      return 'warning'
    case 'error':
      return 'error'
    case 'pending':
      return 'neutral'
    default:
      return 'neutral'
  }
}

function formatCurrency(value: number): string {
  return new Intl.NumberFormat('en-GB', {
    style: 'currency',
    currency: 'GBP',
  }).format(value)
}

function formatDate(dateString: string): string {
  const date = new Date(dateString)
  const now = new Date()
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate())
  const invoiceDate = new Date(date.getFullYear(), date.getMonth(), date.getDate())
  
  if (invoiceDate.getTime() === today.getTime()) {
    return 'Today'
  }
  
  const yesterday = new Date(today)
  yesterday.setDate(yesterday.getDate() - 1)
  if (invoiceDate.getTime() === yesterday.getTime()) {
    return 'Yesterday'
  }
  
  return date.toLocaleDateString('en-GB', {
    day: 'numeric',
    month: 'short',
    year: date.getFullYear() !== now.getFullYear() ? 'numeric' : undefined,
  })
}

export const InvoiceCard = memo(function InvoiceCard({
  invoice,
  isSelected,
  onClick,
}: InvoiceCardProps) {
  const statusColor = getStatusColor(invoice.status)

  return (
    <div
      className={`invoice-card ${isSelected ? 'selected' : ''}`}
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
      <div className="invoice-card-content">
        <div className="invoice-card-header">
          <div className="invoice-card-supplier">{invoice.supplier}</div>
          {invoice.isReceipt && <DualPurposeBadge />}
        </div>
        
        <div className="invoice-card-amount">
          {formatCurrency(invoice.value)}
        </div>
        
        <div className="invoice-card-meta">
          <span className="invoice-card-date">{formatDate(invoice.date)}</span>
          {invoice.confidence !== undefined && invoice.confidence < 80 && (
            <span className="invoice-card-confidence">
              {invoice.confidence.toFixed(0)}% conf
            </span>
          )}
        </div>
      </div>
      
      <div className={`invoice-card-status status-${statusColor}`}>
        {invoice.status === 'matched' && 'Matched'}
        {invoice.status === 'flagged' && 'Flagged'}
        {invoice.status === 'error' && 'Error'}
        {invoice.status === 'pending' && 'Pending'}
        {invoice.status === 'scanned' && 'Scanned'}
      </div>
    </div>
  )
})

