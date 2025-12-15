import React from 'react'
import { Trash2, Send, CheckCircle2, AlertTriangle, AlertCircle } from 'lucide-react'
import './ReviewFooterGen.css'

export type ReviewStatus = 'empty' | 'all-clear' | 'minor-issues' | 'critical-issues'

export interface ReviewIssue {
  id: string
  type: 'info' | 'warning' | 'error'
  message: string
}

interface ReviewFooterGenProps {
  status?: ReviewStatus
  issues?: ReviewIssue[]
  hasDocuments?: boolean
  onSubmit?: () => void
  onClear?: () => void
}

export function ReviewFooterGen({
  status = 'empty',
  issues = [],
  hasDocuments = false,
  onSubmit = () => {},
  onClear = () => {},
}: ReviewFooterGenProps) {
  const isSubmitDisabled = status === 'empty' || status === 'critical-issues'
  const showClearButton = hasDocuments

  const getStatusPill = () => {
    if (status === 'all-clear') {
      return (
        <div className="review-footer-gen__pill review-footer-gen__pill--success">
          <CheckCircle2 className="review-footer-gen__pill-icon" />
          <span>All clear – nothing requires your attention</span>
        </div>
      )
    }

    if (status === 'minor-issues' && issues.length > 0) {
      return issues.map((issue) => (
        <div
          key={issue.id}
          className={`review-footer-gen__pill review-footer-gen__pill--${issue.type === 'warning' ? 'warning' : 'info'}`}
        >
          {issue.type === 'warning' && <AlertTriangle className="review-footer-gen__pill-icon" />}
          <span>{issue.message}</span>
        </div>
      ))
    }

    if (status === 'critical-issues' && issues.length > 0) {
      return issues
        .filter((issue) => issue.type === 'error')
        .map((issue) => (
          <div key={issue.id} className="review-footer-gen__pill review-footer-gen__pill--error">
            <AlertCircle className="review-footer-gen__pill-icon" />
            <span>{issue.message}</span>
          </div>
        ))
    }

    return null
  }

  return (
    <div className="review-footer-gen">
      <div className="review-footer-gen__inner">
        <div className="review-footer-gen__left">
          <div className="review-footer-gen__header">
            <div className="review-footer-gen__title">Review &amp; submit</div>
            <div className="review-footer-gen__subtitle">
              Owlin will only ask you to act on mismatches and exceptions. Everything else flows
              through automatically.
            </div>
          </div>

          {status !== 'empty' && (
            <div className="review-footer-gen__pills">{getStatusPill()}</div>
          )}
        </div>

        <div className="review-footer-gen__right">
          {showClearButton && (
            <button
              type="button"
              className="review-footer-gen__button review-footer-gen__button--ghost"
              onClick={onClear}
            >
              <Trash2 className="review-footer-gen__button-icon" />
              Clear all
            </button>
          )}
          <button
            type="button"
            className={`review-footer-gen__button review-footer-gen__button--primary ${isSubmitDisabled ? 'review-footer-gen__button--disabled' : ''}`}
            onClick={onSubmit}
            disabled={isSubmitDisabled}
            title={
              status === 'critical-issues'
                ? 'Resolve required issues before submitting'
                : undefined
            }
          >
            <Send className="review-footer-gen__button-icon" />
            Submit documents
          </button>
        </div>
      </div>
    </div>
  )
}

