import { memo } from 'react'
import { InvoiceCard } from './InvoiceCard'
import type { Invoice } from './VirtualizedInvoiceList'
import './InvoiceGroup.css'

interface InvoiceGroupProps {
  groupKey: string
  label: string
  invoices: Invoice[]
  isExpanded: boolean
  onToggle: () => void
  onInvoiceClick: (invoice: Invoice) => void
  selectedId?: string | null
  itemHeight: number
}

export const InvoiceGroup = memo(function InvoiceGroup({
  label,
  invoices,
  isExpanded,
  onToggle,
  onInvoiceClick,
  selectedId,
  itemHeight,
}: InvoiceGroupProps) {
  return (
    <div className="invoice-group">
      <button
        className={`invoice-group-header ${isExpanded ? 'expanded' : ''}`}
        onClick={onToggle}
        aria-expanded={isExpanded}
      >
        <svg
          className="invoice-group-chevron"
          width="16"
          height="16"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <polyline points="6 9 12 15 18 9" />
        </svg>
        <span className="invoice-group-label">{label}</span>
        <span className="invoice-group-count">{invoices.length}</span>
      </button>
      {isExpanded && (
        <div className="invoice-group-content">
          {invoices.map((invoice) => (
            <div
              key={invoice.id}
              style={{ height: itemHeight, marginBottom: 8 }}
            >
              <InvoiceCard
                invoice={invoice}
                isSelected={selectedId === invoice.id}
                onClick={() => onInvoiceClick(invoice)}
              />
            </div>
          ))}
        </div>
      )}
    </div>
  )
})

