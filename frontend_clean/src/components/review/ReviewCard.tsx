import { AlertCircle, CheckCircle2, Clock, XCircle, Edit2 } from 'lucide-react'
import { useState } from 'react'
import './ReviewCard.css'

export interface ReviewCardProps {
  docId: string
  filename?: string
  supplier?: string
  date?: string
  total?: number
  confidence?: number
  confidenceBand?: 'high' | 'medium' | 'low' | 'critical'
  reviewReason?: string
  reviewPriority?: 'low' | 'medium' | 'high' | 'critical'
  primaryIssue?: string
  fixableFields?: string[]
  suggestedActions?: string[]
  onReview?: (docId: string) => void
  onQuickFix?: (docId: string, field: string) => void
}

export function ReviewCard({
  docId,
  filename,
  supplier,
  date,
  total,
  confidence = 0,
  confidenceBand = 'medium',
  reviewReason,
  reviewPriority = 'medium',
  primaryIssue,
  fixableFields = [],
  suggestedActions = [],
  onReview,
  onQuickFix,
}: ReviewCardProps) {
  const [showHints, setShowHints] = useState(false)

  const getBandColor = (band: string) => {
    switch (band) {
      case 'high':
        return 'var(--color-success)'
      case 'medium':
        return 'var(--color-warning)'
      case 'low':
        return 'var(--color-error)'
      case 'critical':
        return 'var(--color-critical)'
      default:
        return 'var(--color-text-secondary)'
    }
  }

  const getBandIcon = (band: string) => {
    switch (band) {
      case 'high':
        return <CheckCircle2 size={16} />
      case 'medium':
        return <Clock size={16} />
      case 'low':
        return <AlertCircle size={16} />
      case 'critical':
        return <XCircle size={16} />
      default:
        return <AlertCircle size={16} />
    }
  }

  const getBandLabel = (band: string) => {
    switch (band) {
      case 'high':
        return 'High Confidence'
      case 'medium':
        return 'Review Recommended'
      case 'low':
        return 'Manual Review Required'
      case 'critical':
        return 'Cannot Trust'
      default:
        return 'Needs Review'
    }
  }

  const formatCurrency = (value?: number) => {
    if (value === undefined || value === null) return 'N/A'
    return new Intl.NumberFormat('en-GB', {
      style: 'currency',
      currency: 'GBP',
    }).format(value)
  }

  return (
    <div
      className={`review-card review-card--${confidenceBand}`}
      onMouseEnter={() => setShowHints(true)}
      onMouseLeave={() => setShowHints(false)}
    >
      <div className="review-card__header">
        <div className="review-card__band-badge" style={{ color: getBandColor(confidenceBand) }}>
          {getBandIcon(confidenceBand)}
          <span>{getBandLabel(confidenceBand)}</span>
        </div>
        <div className="review-card__confidence">
          {Math.round(confidence)}%
        </div>
      </div>

      <div className="review-card__content">
        <div className="review-card__primary-info">
          <h3 className="review-card__supplier">{supplier || 'Unknown Supplier'}</h3>
          {filename && (
            <p className="review-card__filename">{filename}</p>
          )}
          <div className="review-card__meta">
            {date && <span className="review-card__date">{date}</span>}
            {total !== undefined && (
              <span className="review-card__total">{formatCurrency(total)}</span>
            )}
          </div>
        </div>

        {primaryIssue && (
          <div className="review-card__issue">
            <AlertCircle size={14} />
            <span>{primaryIssue}</span>
          </div>
        )}

        {showHints && suggestedActions.length > 0 && (
          <div className="review-card__hints">
            <p className="review-card__hints-title">Suggested actions:</p>
            <ul className="review-card__hints-list">
              {suggestedActions.slice(0, 3).map((action, idx) => (
                <li key={idx}>{action}</li>
              ))}
            </ul>
          </div>
        )}

        {fixableFields.length > 0 && (
          <div className="review-card__quick-fixes">
            <p className="review-card__quick-fixes-title">Quick fixes available:</p>
            <div className="review-card__quick-fixes-list">
              {fixableFields.map((field) => (
                <button
                  key={field}
                  className="review-card__quick-fix-btn"
                  onClick={() => onQuickFix?.(docId, field)}
                  title={`Fix ${field}`}
                >
                  <Edit2 size={12} />
                  {field}
                </button>
              ))}
            </div>
          </div>
        )}
      </div>

      <div className="review-card__actions">
        <button
          className="review-card__review-btn"
          onClick={() => onReview?.(docId)}
        >
          Review
        </button>
      </div>
    </div>
  )
}

