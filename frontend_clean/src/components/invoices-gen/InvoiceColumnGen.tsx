import './InvoiceColumnGen.css'

export interface InvoiceSummary {
  id: string
  supplierName?: string | null
  invoiceNumber?: string | null
  totalAmount?: number | null
  status?: 'pending' | 'ready' | 'matched' | 'flagged'
}

interface InvoiceColumnGenProps {
  invoices: InvoiceSummary[]
  selectedInvoiceId: string | null
  onSelectInvoice: (id: string) => void
}

export function InvoiceColumnGen({
  invoices,
  selectedInvoiceId,
  onSelectInvoice,
}: InvoiceColumnGenProps) {
  const hasInvoices = invoices && invoices.length > 0

  return (
    <div className="invoice-column-gen">
      <div className="invoice-column-gen__header">
        <div className="invoice-column-gen__title invoices-gen__label">
          Invoices
        </div>
        <div className="invoice-column-gen__count invoices-gen__micro invoices-gen__text-soft">
          {hasInvoices ? `${invoices.length} invoices` : 'No invoices yet'}
        </div>
      </div>

      <div className="invoice-column-gen__list">
        {!hasInvoices && (
          <div className="invoice-column-gen__empty">
            <div className="invoice-column-gen__empty-icon" />
            <div className="invoice-column-gen__empty-text">
              Upload documents to see invoices here.
            </div>
          </div>
        )}

        {hasInvoices &&
          invoices.map((inv) => {
            const isSelected = selectedInvoiceId === inv.id
            return (
              <button
                key={inv.id}
                type="button"
                className={
                  'invoice-card-gen invoices-gen-card' +
                  (isSelected ? ' invoice-card-gen--selected' : '')
                }
                onClick={() => onSelectInvoice(inv.id)}
              >
                <div className="invoice-card-gen__top-row">
                  <div className="invoice-card-gen__supplier invoices-gen__body">
                    {inv.supplierName || 'Supplier'}
                  </div>
                  <span className="invoice-card-gen__status-pill">
                    {inv.status || 'Pending'}
                  </span>
                </div>

                <div className="invoice-card-gen__meta-row">
                  <span className="invoice-card-gen__number invoices-gen__micro invoices-gen__text-soft">
                    {inv.invoiceNumber || 'Invoice'}
                  </span>
                </div>

                <div className="invoices-gen-divider" />

                <div className="invoice-card-gen__footer-row">
                  <div className="invoice-card-gen__total invoices-gen__h2">
                    {inv.totalAmount != null ? `£${inv.totalAmount.toFixed(2)}` : '—'}
                  </div>
                </div>
              </button>
            )
          })}
      </div>
    </div>
  )
}

