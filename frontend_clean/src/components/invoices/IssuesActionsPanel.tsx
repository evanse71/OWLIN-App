import { AlertCircle, CheckCircle2, FileText, Info, Link as LinkIcon, Plus } from 'lucide-react'
import './IssuesActionsPanel.css'

export interface Issue {
  id: string
  type: 'short' | 'price' | 'missing' | 'other'
  severity: 'minor' | 'review' | 'critical'
  item?: string
  description: string
  suggestedAction?: string
  suggestedCredit?: number
}

export interface DeliveryNoteInfo {
  id?: string
  noteNumber?: string
  date?: string
  driver?: string
  vehicle?: string
  timeWindow?: string
}

export interface DocumentMetadata {
  source: 'manual' | 'upload'
  createdBy?: string
  createdAt?: string
  lastEditedBy?: string
  lastEditedAt?: string
  filename?: string
  pages?: number
  filesize?: number
}

interface IssuesActionsPanelProps {
  issues: Issue[]
  deliveryNote?: DeliveryNoteInfo
  metadata?: DocumentMetadata
  onLinkDeliveryNote: () => void
  onCreateDeliveryNote: () => void
  onViewDeliveryNote: () => void
  onMarkReviewed: () => void
  onEscalateToSupplier: () => void
  showOCRDebug?: boolean
}

export function IssuesActionsPanel({
  issues,
  deliveryNote,
  metadata,
  onLinkDeliveryNote,
  onCreateDeliveryNote,
  onViewDeliveryNote,
  onMarkReviewed,
  onEscalateToSupplier,
  showOCRDebug = false,
}: IssuesActionsPanelProps) {
  const formatCurrency = (value?: number) => {
    if (value === undefined || value === null) return '£0.00'
    return new Intl.NumberFormat('en-GB', { style: 'currency', currency: 'GBP' }).format(value)
  }

  const formatDate = (dateStr?: string) => {
    if (!dateStr) return 'Unknown'
    try {
      const date = new Date(dateStr)
      return date.toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' })
    } catch {
      return dateStr
    }
  }

  // Group issues by type for summary
  const issuesByType: Record<string, number> = {}
  issues.forEach((issue) => {
    const key = issue.type === 'short' ? 'items short' : issue.type === 'price' ? 'price change' : 'other'
    issuesByType[key] = (issuesByType[key] || 0) + 1
  })

  return (
    <div className="invoices-actions-column">
      {/* Flagged Issues Card */}
      <div className="issues-card">
        <div className="issues-card-header">
          <h3 className="issues-card-title">Issues on this invoice</h3>
        </div>
        <div className="issues-card-content">
          {issues.length === 0 ? (
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', padding: '32px 24px', color: 'var(--text-muted)' }}>
              <div style={{ 
                width: '48px', 
                height: '48px', 
                borderRadius: '50%', 
                background: 'rgba(16, 185, 129, 0.1)', 
                display: 'flex', 
                alignItems: 'center', 
                justifyContent: 'center',
                marginBottom: '12px'
              }}>
                <CheckCircle2 size={24} style={{ color: 'var(--accent-green)' }} />
              </div>
              <div style={{ fontSize: '14px', fontWeight: '500', color: 'var(--text-primary)', marginBottom: '4px' }}>No issues flagged</div>
              <div style={{ fontSize: '12px', color: 'var(--text-muted)', textAlign: 'center', marginBottom: '8px' }}>This invoice looks good!</div>
              <div style={{ fontSize: '12px', color: 'var(--text-secondary)', textAlign: 'center', marginTop: '8px' }}>
                You can still link a delivery note or submit this invoice.
              </div>
            </div>
          ) : (
            <>
              {/* Summary Chips */}
              {Object.keys(issuesByType).length > 0 && (
                <div style={{ display: 'flex', gap: '8px', marginBottom: '12px', flexWrap: 'wrap' }}>
                  {Object.entries(issuesByType).map(([type, count]) => (
                    <span key={type} className="badge" style={{ fontSize: '11px' }}>
                      {count} {type}
                    </span>
                  ))}
                </div>
              )}

              {/* Issues List */}
              <div className="issues-list">
                {issues.map((issue) => (
                  <div key={issue.id} className={`issue-item ${issue.severity}`}>
                    <div className="issue-item-header">
                      <div className="issue-item-title">
                        {issue.item || 'General issue'}
                      </div>
                      <span className={`issue-item-severity severity-${issue.severity}`}>
                        {issue.severity}
                      </span>
                    </div>
                    <div className="issue-item-description">{issue.description}</div>
                    {issue.suggestedAction && (
                      <div style={{ marginTop: '8px', fontSize: '12px', color: 'var(--accent-blue)' }}>
                        {issue.suggestedAction}
                        {issue.suggestedCredit && `: ${formatCurrency(issue.suggestedCredit)}`}
                      </div>
                    )}
                  </div>
                ))}
              </div>

              {/* Action Buttons */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', marginTop: '16px', paddingTop: '16px', borderTop: '1px solid var(--border-color)' }}>
                <button className="glass-button" onClick={onMarkReviewed}>
                  Mark as reviewed
                </button>
                <button className="glass-button" onClick={onEscalateToSupplier}>
                  Escalate to supplier
                </button>
              </div>
            </>
          )}
        </div>
      </div>

      {/* Delivery Notes Context Card */}
      <div className="issues-card">
        <div className="issues-card-header">
          <h3 className="issues-card-title">Delivery notes</h3>
        </div>
        <div className="issues-card-content">
          {deliveryNote ? (
            <>
              <div style={{ marginBottom: '12px' }}>
                <div style={{ fontSize: '14px', fontWeight: '600', marginBottom: '8px' }}>
                  {deliveryNote.noteNumber || `DN-${deliveryNote.id?.slice(0, 8)}`}
                </div>
                <div style={{ fontSize: '12px', color: 'var(--text-secondary)', marginBottom: '4px' }}>
                  {formatDate(deliveryNote.date)}
                </div>
                {(deliveryNote.driver || deliveryNote.vehicle || deliveryNote.timeWindow) && (
                  <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '8px' }}>
                    {deliveryNote.driver && <div>Driver: {deliveryNote.driver}</div>}
                    {deliveryNote.vehicle && <div>Vehicle: {deliveryNote.vehicle}</div>}
                    {deliveryNote.timeWindow && <div>Time: {deliveryNote.timeWindow}</div>}
                  </div>
                )}
              </div>
              <button className="glass-button" onClick={onViewDeliveryNote} style={{ width: '100%' }}>
                <FileText size={14} />
                View delivery note details
              </button>
            </>
          ) : (
            <>
              <div style={{ fontSize: '13px', color: 'var(--text-muted)', marginBottom: '12px' }}>
                No delivery note linked to this invoice.
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                <button className="glass-button" onClick={onLinkDeliveryNote} style={{ width: '100%' }}>
                  <LinkIcon size={14} />
                  Link existing delivery note
                </button>
                <button className="glass-button" onClick={onCreateDeliveryNote} style={{ width: '100%' }}>
                  <Plus size={14} />
                  Create manual delivery note
                </button>
              </div>
            </>
          )}
        </div>
      </div>

      {/* Document Metadata Card */}
      {metadata && (
        <div className="issues-card">
          <div className="issues-card-header">
            <h3 className="issues-card-title">Document metadata</h3>
          </div>
          <div className="issues-card-content">
            <div className="metadata-list">
              <div className="metadata-item">
                <span className="metadata-label">Source:</span>
                <span className="metadata-value">{metadata.source === 'manual' ? 'Manual' : 'Upload'}</span>
              </div>
              {metadata.createdBy && (
                <div className="metadata-item">
                  <span className="metadata-label">Created by:</span>
                  <span className="metadata-value">{metadata.createdBy}</span>
                </div>
              )}
              {metadata.createdAt && (
                <div className="metadata-item">
                  <span className="metadata-label">Created at:</span>
                  <span className="metadata-value">{formatDate(metadata.createdAt)}</span>
                </div>
              )}
              {metadata.lastEditedBy && (
                <div className="metadata-item">
                  <span className="metadata-label">Last edited by:</span>
                  <span className="metadata-value">{metadata.lastEditedBy}</span>
                </div>
              )}
              {metadata.lastEditedAt && (
                <div className="metadata-item">
                  <span className="metadata-label">Last edited at:</span>
                  <span className="metadata-value">{formatDate(metadata.lastEditedAt)}</span>
                </div>
              )}
              {metadata.filename && (
                <div className="metadata-item">
                  <span className="metadata-label">Filename:</span>
                  <span className="metadata-value" style={{ fontSize: '11px', wordBreak: 'break-all' }}>
                    {metadata.filename}
                  </span>
                </div>
              )}
              {metadata.pages !== undefined && (
                <div className="metadata-item">
                  <span className="metadata-label">Pages:</span>
                  <span className="metadata-value">{metadata.pages}</span>
                </div>
              )}
              {metadata.filesize !== undefined && (
                <div className="metadata-item">
                  <span className="metadata-label">Filesize:</span>
                  <span className="metadata-value">
                    {metadata.filesize < 1024
                      ? `${metadata.filesize} B`
                      : metadata.filesize < 1024 * 1024
                        ? `${(metadata.filesize / 1024).toFixed(1)} KB`
                        : `${(metadata.filesize / (1024 * 1024)).toFixed(1)} MB`}
                  </span>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* OCR Debug Card (optional) */}
      {showOCRDebug && (
        <div className="issues-card">
          <div className="issues-card-header">
            <h3 className="issues-card-title">OCR debug</h3>
          </div>
          <div className="issues-card-content">
            <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
              Debug information would appear here in dev mode.
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

