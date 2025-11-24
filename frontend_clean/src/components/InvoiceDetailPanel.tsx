import type { InvoiceMetadata } from '../lib/upload'

interface InvoiceDetailPanelProps {
  invoice: {
    id: string
    file: File
    metadata?: InvoiceMetadata
  }
}

export function InvoiceDetailPanel({ invoice }: InvoiceDetailPanelProps) {
  const metadata = invoice.metadata || {}
  const pages = metadata.pages || []
  const lineItems = metadata.lineItems || []
  const invoiceId = metadata.id ?? invoice.id
  const confidence = metadata.confidence ?? null

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

  const hasLowConfidence = confidence !== null && (confidence === 0 || confidence < 50)

  // Check if OCR preview is available for DEV hint
  const hasOCRPreview = (): boolean => {
    if (pages && pages.some(p => p.text)) return true
    const raw = metadata.raw || {}
    return !!(raw.ocr_text || raw.text || raw.extracted_text)
  }

  const showOCRHint = !metadata.supplier && hasOCRPreview()

  return (
    <div className="detail-panel" style={{ padding: '24px', height: '100%', overflowY: 'auto' }}>
      {/* Header */}
      <div style={{ marginBottom: '24px', paddingBottom: '16px', borderBottom: '1px solid rgba(0, 0, 0, 0.06)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '8px' }}>
          <h2 style={{ margin: 0, fontSize: '24px', fontWeight: 600 }}>
            {metadata.supplier || 'Unknown Supplier'}
          </h2>
          {hasLowConfidence && (
            <span style={{ fontSize: '18px' }} title="Low confidence; review manually">
              ⚠️
            </span>
          )}
        </div>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '16px', fontSize: '14px', color: 'rgba(0, 0, 0, 0.6)' }}>
          <div>
            <span style={{ fontWeight: 500 }}>ID:</span>{' '}
            <code style={{ fontFamily: 'monospace', backgroundColor: 'rgba(0, 0, 0, 0.05)', padding: '2px 6px', borderRadius: '4px' }}>
              {String(invoiceId).slice(0, 12)}
            </code>
          </div>
          <div>
            <span style={{ fontWeight: 500 }}>Date:</span> {formatDate(metadata.date)}
          </div>
          <div>
            <span style={{ fontWeight: 500 }}>Value:</span> {formatCurrency(metadata.value)}
          </div>
          {confidence !== null && (
            <div>
              <span style={{ fontWeight: 500 }}>Confidence:</span> {confidence.toFixed(1)}%
            </div>
          )}
        </div>
        {hasLowConfidence && (
          <div
            style={{
              marginTop: '12px',
              padding: '8px 12px',
              backgroundColor: 'rgba(251, 191, 36, 0.1)',
              border: '1px solid rgba(251, 191, 36, 0.3)',
              borderRadius: '6px',
              fontSize: '14px',
              color: 'rgb(180, 83, 9)',
            }}
          >
            ⚠️ Low confidence; review manually
          </div>
        )}
      </div>

      {/* Pages Preview */}
      {pages.length > 0 && (
        <div style={{ marginBottom: '24px' }}>
          <h3 style={{ fontSize: '16px', fontWeight: 600, marginBottom: '12px' }}>Pages</h3>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
            {pages.map((page, idx) => (
              <div
                key={idx}
                style={{
                  padding: '6px 12px',
                  backgroundColor: 'rgba(0, 0, 0, 0.05)',
                  borderRadius: '6px',
                  fontSize: '14px',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                }}
              >
                <span style={{ fontWeight: 500 }}>Page {page.index ?? idx + 1}</span>
                {page.confidence !== undefined && (
                  <span style={{ color: 'rgba(0, 0, 0, 0.6)', fontSize: '12px' }}>
                    {page.confidence.toFixed(1)}%
                  </span>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Key Fields */}
      <div style={{ marginBottom: '24px' }}>
        <h3 style={{ fontSize: '16px', fontWeight: 600, marginBottom: '12px' }}>Key Fields</h3>
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
            gap: '16px',
          }}
        >
          <div>
            <div style={{ fontSize: '12px', color: 'rgba(0, 0, 0, 0.6)', marginBottom: '4px' }}>Supplier</div>
            <div style={{ fontWeight: 500 }}>
              {metadata.supplier || <span style={{ color: 'rgba(0, 0, 0, 0.4)' }}>Not provided</span>}
            </div>
            {showOCRHint && (
              <div style={{ fontSize: '11px', color: 'rgba(0, 0, 0, 0.5)', fontStyle: 'italic', marginTop: '4px' }}>
                No structured supplier returned. See OCR Preview in DEV.
              </div>
            )}
          </div>
          <div>
            <div style={{ fontSize: '12px', color: 'rgba(0, 0, 0, 0.6)', marginBottom: '4px' }}>Invoice No.</div>
            <div style={{ fontWeight: 500 }}>{metadata.invoiceNo || <span style={{ color: 'rgba(0, 0, 0, 0.4)' }}>Not provided</span>}</div>
          </div>
          <div>
            <div style={{ fontSize: '12px', color: 'rgba(0, 0, 0, 0.6)', marginBottom: '4px' }}>Date</div>
            <div style={{ fontWeight: 500 }}>{formatDate(metadata.date) || <span style={{ color: 'rgba(0, 0, 0, 0.4)' }}>Not provided</span>}</div>
          </div>
          {metadata.subtotal !== undefined && (
            <div>
              <div style={{ fontSize: '12px', color: 'rgba(0, 0, 0, 0.6)', marginBottom: '4px' }}>Subtotal</div>
              <div style={{ fontWeight: 500 }}>{formatCurrency(metadata.subtotal as number)}</div>
            </div>
          )}
          {metadata.vat !== undefined && (
            <div>
              <div style={{ fontSize: '12px', color: 'rgba(0, 0, 0, 0.6)', marginBottom: '4px' }}>VAT</div>
              <div style={{ fontWeight: 500 }}>{formatCurrency(metadata.vat as number)}</div>
            </div>
          )}
          {metadata.total !== undefined && (
            <div>
              <div style={{ fontSize: '12px', color: 'rgba(0, 0, 0, 0.6)', marginBottom: '4px' }}>Total</div>
              <div style={{ fontWeight: 500 }}>{formatCurrency(metadata.total as number)}</div>
            </div>
          )}
        </div>
      </div>

      {/* Line Items */}
      {lineItems.length > 0 ? (
        <div style={{ marginBottom: '24px' }}>
          <h3 style={{ fontSize: '16px', fontWeight: 600, marginBottom: '12px' }}>Line Items</h3>
          <div style={{ overflowX: 'auto' }}>
            <table
              style={{
                width: '100%',
                borderCollapse: 'collapse',
                fontSize: '14px',
              }}
            >
              <thead>
                <tr style={{ borderBottom: '1px solid rgba(0, 0, 0, 0.1)' }}>
                  <th style={{ textAlign: 'left', padding: '8px', fontWeight: 600 }}>Item</th>
                  <th style={{ textAlign: 'right', padding: '8px', fontWeight: 600 }}>Qty</th>
                  <th style={{ textAlign: 'left', padding: '8px', fontWeight: 600 }}>Unit</th>
                  <th style={{ textAlign: 'right', padding: '8px', fontWeight: 600 }}>Price</th>
                  <th style={{ textAlign: 'right', padding: '8px', fontWeight: 600 }}>Total</th>
                </tr>
              </thead>
              <tbody>
                {lineItems.map((item, idx) => (
                  <tr key={idx} style={{ borderBottom: '1px solid rgba(0, 0, 0, 0.05)' }}>
                    <td style={{ padding: '8px' }}>{item.description || item.item || '-'}</td>
                    <td style={{ padding: '8px', textAlign: 'right' }}>{item.qty ?? item.quantity ?? '-'}</td>
                    <td style={{ padding: '8px' }}>{item.unit || item.uom || '-'}</td>
                    <td style={{ padding: '8px', textAlign: 'right' }}>
                      {item.price !== undefined ? formatCurrency(item.price) : '-'}
                    </td>
                    <td style={{ padding: '8px', textAlign: 'right', fontWeight: 500 }}>
                      {item.total !== undefined ? formatCurrency(item.total) : item.line_total !== undefined ? formatCurrency(item.line_total) : '-'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ) : (
        <div style={{ marginBottom: '24px', padding: '24px', textAlign: 'center', color: 'rgba(0, 0, 0, 0.5)' }}>
          No line items returned
        </div>
      )}

      {/* Status Chips */}
      <div style={{ marginBottom: '24px' }}>
        <h3 style={{ fontSize: '16px', fontWeight: 600, marginBottom: '12px' }}>Status</h3>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
          <span
            style={{
              padding: '6px 12px',
              backgroundColor: 'rgba(34, 197, 94, 0.1)',
              color: 'rgb(22, 163, 74)',
              borderRadius: '6px',
              fontSize: '14px',
              fontWeight: 500,
            }}
          >
            Scanned
          </span>
          <span
            style={{
              padding: '6px 12px',
              backgroundColor: 'rgba(156, 163, 175, 0.1)',
              color: 'rgb(107, 114, 128)',
              borderRadius: '6px',
              fontSize: '14px',
              fontWeight: 500,
            }}
          >
            Matched (placeholder)
          </span>
          <span
            style={{
              padding: '6px 12px',
              backgroundColor: 'rgba(156, 163, 175, 0.1)',
              color: 'rgb(107, 114, 128)',
              borderRadius: '6px',
              fontSize: '14px',
              fontWeight: 500,
            }}
          >
            Flagged (placeholder)
          </span>
        </div>
      </div>

      {/* Actions Row */}
      <div>
        <h3 style={{ fontSize: '16px', fontWeight: 600, marginBottom: '12px' }}>Actions</h3>
        <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
          <button
            style={{
              padding: '8px 16px',
              borderRadius: '6px',
              border: '1px solid rgba(0, 0, 0, 0.1)',
              backgroundColor: 'white',
              color: 'rgb(107, 114, 128)',
              fontSize: '14px',
              fontWeight: 500,
              cursor: 'not-allowed',
              opacity: 0.6,
            }}
            disabled
          >
            Mark as Flagged
          </button>
          <button
            style={{
              padding: '8px 16px',
              borderRadius: '6px',
              border: '1px solid rgba(0, 0, 0, 0.1)',
              backgroundColor: 'white',
              color: 'rgb(107, 114, 128)',
              fontSize: '14px',
              fontWeight: 500,
              cursor: 'not-allowed',
              opacity: 0.6,
            }}
            disabled
          >
            Pair Delivery Note
          </button>
        </div>
      </div>
    </div>
  )
}

