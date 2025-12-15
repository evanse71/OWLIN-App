import './DetailViewGen.css'

interface DetailViewGenProps {
  selectedInvoiceId: string | null
}

export function DetailViewGen({ selectedInvoiceId }: DetailViewGenProps) {
  const hasSelection = !!selectedInvoiceId

  return (
    <div className="detail-view-gen">
      {!hasSelection && (
        <div className="detail-view-gen__empty">
          <div className="detail-view-gen__empty-icon" />
          <div className="detail-view-gen__empty-title invoices-gen__h2">
            Select an invoice to review
          </div>
          <div className="detail-view-gen__empty-subtitle invoices-gen__body invoices-gen__text-muted">
            When you choose an invoice, Owlin will show supplier, totals, and line-by-line checks here.
          </div>
        </div>
      )}

      {hasSelection && (
        <div className="detail-view-gen__content">
          <div className="detail-view-gen__section">
            <div className="detail-view-gen__section-title invoices-gen__label">
              Invoice summary
            </div>

            <div className="detail-view-gen__field-row">
              <span className="detail-view-gen__field-label invoices-gen__micro invoices-gen__text-soft">
                Supplier
              </span>
              <span className="detail-view-gen__field-value invoices-gen__body detail-view-gen__placeholder">
                (will show supplier name)
              </span>
            </div>
            <div className="detail-view-gen__field-row">
              <span className="detail-view-gen__field-label invoices-gen__micro invoices-gen__text-soft">
                Invoice number
              </span>
              <span className="detail-view-gen__field-value invoices-gen__body detail-view-gen__placeholder">
                (will show invoice number)
              </span>
            </div>
            <div className="detail-view-gen__field-row">
              <span className="detail-view-gen__field-label invoices-gen__micro invoices-gen__text-soft">
                Total
              </span>
              <span className="detail-view-gen__field-value invoices-gen__body detail-view-gen__placeholder">
                (will show total)
              </span>
            </div>
          </div>

          <div className="invoices-gen-divider" />

          <div className="detail-view-gen__section">
            <div className="detail-view-gen__section-title invoices-gen__label">
              Line items
            </div>
            <div className="detail-view-gen__lines-placeholder invoices-gen__micro invoices-gen__text-soft">
              Line items will appear here once connected to real data.
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

