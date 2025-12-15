import { X, CheckCircle2, AlertCircle, Edit2, Send, User } from 'lucide-react'
import { useState, useEffect } from 'react'
import { ConfidenceBreakdown } from '../confidence/ConfidenceBreakdown'
import './ReviewModal.css'

export interface ReviewModalProps {
  docId: string
  isOpen: boolean
  onClose: () => void
  onApprove?: (docId: string, notes?: string) => void
  onQuickFix?: (docId: string, fixes: Record<string, any>) => void
  onEscalate?: (docId: string, reason: string, escalateTo?: string) => void
  document?: {
    filename?: string
    supplier?: string
    date?: string
    total?: number
    confidence?: number
    lineItemsCount?: number
  }
  confidenceBreakdown?: {
    ocr_quality: number
    extraction_quality: number
    validation_quality: number
    overall_confidence: number
    band: 'high' | 'medium' | 'low' | 'critical'
    primary_issue?: string
    remediation_hints?: string[]
  }
  reviewMetadata?: {
    review_reason?: string
    review_priority?: 'low' | 'medium' | 'high' | 'critical'
    fixable_fields?: string[]
    suggested_actions?: string[]
  }
}

export function ReviewModal({
  docId,
  isOpen,
  onClose,
  onApprove,
  onQuickFix,
  onEscalate,
  document,
  confidenceBreakdown,
  reviewMetadata,
}: ReviewModalProps) {
  const [activeSection, setActiveSection] = useState<'overview' | 'fixes' | 'actions'>('overview')
  const [quickFixes, setQuickFixes] = useState<Record<string, string>>({})
  const [approvalNotes, setApprovalNotes] = useState('')
  const [escalateReason, setEscalateReason] = useState('')
  const [escalateTo, setEscalateTo] = useState<'supplier' | 'manager'>('manager')

  useEffect(() => {
    if (isOpen) {
      setActiveSection('overview')
      setQuickFixes({})
      setApprovalNotes('')
      setEscalateReason('')
    }
  }, [isOpen])

  if (!isOpen) return null

  const handleQuickFix = (field: string, value: string) => {
    setQuickFixes((prev) => ({ ...prev, [field]: value }))
  }

  const handleApplyQuickFixes = () => {
    if (Object.keys(quickFixes).length > 0) {
      onQuickFix?.(docId, quickFixes)
      setQuickFixes({})
    }
  }

  const handleApprove = () => {
    onApprove?.(docId, approvalNotes)
  }

  const handleEscalate = () => {
    if (escalateReason.trim()) {
      onEscalate?.(docId, escalateReason, escalateTo)
    }
  }

  const formatCurrency = (value?: number) => {
    if (value === undefined || value === null) return 'N/A'
    return new Intl.NumberFormat('en-GB', {
      style: 'currency',
      currency: 'GBP',
    }).format(value)
  }

  const getGoodFields = () => {
    const good: string[] = []
    if (document?.supplier && document.supplier !== 'Unknown Supplier') {
      good.push('Supplier')
    }
    if (document?.date) {
      good.push('Date')
    }
    if (document?.total && document.total > 0) {
      good.push('Total')
    }
    if (document?.lineItemsCount && document.lineItemsCount > 0) {
      good.push('Line Items')
    }
    return good
  }

  const getNeedsAttentionFields = () => {
    const needs: string[] = []
    if (!document?.supplier || document.supplier === 'Unknown Supplier') {
      needs.push('Supplier')
    }
    if (!document?.date) {
      needs.push('Date')
    }
    if (!document?.total || document.total === 0) {
      needs.push('Total')
    }
    if (!document?.lineItemsCount || document.lineItemsCount === 0) {
      needs.push('Line Items')
    }
    return needs
  }

  return (
    <div className="review-modal-overlay" onClick={onClose}>
      <div className="review-modal" onClick={(e) => e.stopPropagation()}>
        <div className="review-modal__header">
          <h2 className="review-modal__title">Review Document</h2>
          <button className="review-modal__close" onClick={onClose}>
            <X size={20} />
          </button>
        </div>

        <div className="review-modal__tabs">
          <button
            className={`review-modal__tab ${activeSection === 'overview' ? 'active' : ''}`}
            onClick={() => setActiveSection('overview')}
          >
            Overview
          </button>
          <button
            className={`review-modal__tab ${activeSection === 'fixes' ? 'active' : ''}`}
            onClick={() => setActiveSection('fixes')}
          >
            Quick Fixes
          </button>
          <button
            className={`review-modal__tab ${activeSection === 'actions' ? 'active' : ''}`}
            onClick={() => setActiveSection('actions')}
          >
            Actions
          </button>
        </div>

        <div className="review-modal__content">
          {activeSection === 'overview' && (
            <div className="review-modal__section">
              {confidenceBreakdown && (
                <div className="review-modal__breakdown">
                  <ConfidenceBreakdown
                    overallConfidence={confidenceBreakdown.overall_confidence}
                    ocrQuality={confidenceBreakdown.ocr_quality}
                    extractionQuality={confidenceBreakdown.extraction_quality}
                    validationQuality={confidenceBreakdown.validation_quality}
                    band={confidenceBreakdown.band}
                    primaryIssue={confidenceBreakdown.primary_issue}
                    remediationHints={confidenceBreakdown.remediation_hints}
                  />
                </div>
              )}

              <div className="review-modal__fields">
                <div className="review-modal__fields-section">
                  <h3 className="review-modal__fields-title">
                    <CheckCircle2 size={16} />
                    What's Good
                  </h3>
                  <div className="review-modal__fields-list">
                    {getGoodFields().map((field) => (
                      <div key={field} className="review-modal__field-item good">
                        <CheckCircle2 size={14} />
                        <span>{field}</span>
                      </div>
                    ))}
                    {getGoodFields().length === 0 && (
                      <p className="review-modal__empty">No fields verified</p>
                    )}
                  </div>
                </div>

                <div className="review-modal__fields-section">
                  <h3 className="review-modal__fields-title">
                    <AlertCircle size={16} />
                    Needs Attention
                  </h3>
                  <div className="review-modal__fields-list">
                    {getNeedsAttentionFields().map((field) => (
                      <div key={field} className="review-modal__field-item needs-attention">
                        <AlertCircle size={14} />
                        <span>{field}</span>
                      </div>
                    ))}
                    {getNeedsAttentionFields().length === 0 && (
                      <p className="review-modal__empty">All fields look good</p>
                    )}
                  </div>
                </div>
              </div>

              {reviewMetadata?.suggested_actions && reviewMetadata.suggested_actions.length > 0 && (
                <div className="review-modal__suggestions">
                  <h3 className="review-modal__suggestions-title">Suggested Corrections</h3>
                  <ul className="review-modal__suggestions-list">
                    {reviewMetadata.suggested_actions.map((action, idx) => (
                      <li key={idx}>{action}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}

          {activeSection === 'fixes' && (
            <div className="review-modal__section">
              <h3 className="review-modal__section-title">Quick Fixes</h3>
              <p className="review-modal__section-description">
                Make quick corrections to fixable fields
              </p>

              {reviewMetadata?.fixable_fields && reviewMetadata.fixable_fields.length > 0 ? (
                <div className="review-modal__fixes">
                  {reviewMetadata.fixable_fields.map((field) => (
                    <div key={field} className="review-modal__fix-item">
                      <label className="review-modal__fix-label">{field}</label>
                      <input
                        type="text"
                        className="review-modal__fix-input"
                        placeholder={`Current: ${document?.[field as keyof typeof document] || 'N/A'}`}
                        value={quickFixes[field] || ''}
                        onChange={(e) => handleQuickFix(field, e.target.value)}
                      />
                    </div>
                  ))}
                  <button
                    className="review-modal__apply-btn"
                    onClick={handleApplyQuickFixes}
                    disabled={Object.keys(quickFixes).length === 0}
                  >
                    <Edit2 size={16} />
                    Apply Fixes
                  </button>
                </div>
              ) : (
                <p className="review-modal__empty">No quick fixes available for this document</p>
              )}
            </div>
          )}

          {activeSection === 'actions' && (
            <div className="review-modal__section">
              <div className="review-modal__actions">
                <div className="review-modal__action-group">
                  <h3 className="review-modal__action-title">Approve</h3>
                  <p className="review-modal__action-description">
                    Mark this document as approved after review
                  </p>
                  <textarea
                    className="review-modal__notes-input"
                    placeholder="Add notes (optional)..."
                    value={approvalNotes}
                    onChange={(e) => setApprovalNotes(e.target.value)}
                  />
                  <button className="review-modal__action-btn approve" onClick={handleApprove}>
                    <CheckCircle2 size={16} />
                    Approve
                  </button>
                </div>

                <div className="review-modal__action-group">
                  <h3 className="review-modal__action-title">Escalate</h3>
                  <p className="review-modal__action-description">
                    Escalate this document for external review
                  </p>
                  <select
                    className="review-modal__escalate-select"
                    value={escalateTo}
                    onChange={(e) => setEscalateTo(e.target.value as 'supplier' | 'manager')}
                  >
                    <option value="manager">Manager</option>
                    <option value="supplier">Supplier</option>
                  </select>
                  <textarea
                    className="review-modal__notes-input"
                    placeholder="Reason for escalation..."
                    value={escalateReason}
                    onChange={(e) => setEscalateReason(e.target.value)}
                    required
                  />
                  <button
                    className="review-modal__action-btn escalate"
                    onClick={handleEscalate}
                    disabled={!escalateReason.trim()}
                  >
                    <Send size={16} />
                    Escalate
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

