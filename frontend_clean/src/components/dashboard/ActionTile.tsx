/**
 * Action Tile Component
 * Individual actionable item in the Action Queue
 */

import { useState } from 'react'
import { CheckCircle2, Clock, XCircle, AlertCircle, X } from 'lucide-react'
import type { ActionItem } from '../../lib/dashboardApi'
import { resolveMismatch, pairDeliveryNote, submitBatch } from '../../lib/dashboardApi'
import './ActionTile.css'

interface ActionTileProps {
  action: ActionItem
  onComplete: (id: string) => void
  currentRole: 'GM' | 'Finance' | 'ShiftLead'
}

export function ActionTile({ action, onComplete, currentRole }: ActionTileProps) {
  const [isProcessing, setIsProcessing] = useState(false)
  const [isExpanded, setIsExpanded] = useState(false)

  const getStatusIcon = () => {
    switch (action.status) {
      case 'done':
        return <CheckCircle2 size={16} className="action-tile-status-icon action-tile-status-done" />
      case 'in_review':
        return <Clock size={16} className="action-tile-status-icon action-tile-status-in-review" />
      case 'blocked':
        return <XCircle size={16} className="action-tile-status-icon action-tile-status-blocked" />
      default:
        return <AlertCircle size={16} className="action-tile-status-icon action-tile-status-pending" />
    }
  }

  const getStatusColor = () => {
    switch (action.status) {
      case 'done':
        return 'green'
      case 'in_review':
        return 'blue'
      case 'blocked':
        return 'red'
      default:
        return 'amber'
    }
  }

  const handleAction = async () => {
    if (isProcessing || action.status === 'done') return

    setIsProcessing(true)
    try {
      switch (action.type) {
        case 'resolve_mismatch':
          await resolveMismatch(action.id, action.metadata?.suggestedCredit)
          break
        case 'pair_dn':
          if (action.metadata?.invoiceId && action.metadata?.deliveryNoteId) {
            await pairDeliveryNote(action.metadata.deliveryNoteId, action.metadata.invoiceId)
          }
          break
        case 'submit_batch':
          if (action.metadata?.invoiceIds) {
            await submitBatch(action.metadata.invoiceIds)
          }
          break
        case 'review_ocr':
          // OCR review doesn't need API call, just mark as done
          break
      }
      onComplete(action.id)
    } catch (e) {
      console.error(`Failed to complete action ${action.id}:`, e)
      alert(`Failed to complete action: ${e instanceof Error ? e.message : 'Unknown error'}`)
    } finally {
      setIsProcessing(false)
    }
  }

  const canPerformAction = () => {
    if (action.status === 'done' || action.status === 'blocked') return false
    if (action.type === 'resolve_mismatch' && currentRole === 'ShiftLead') return false
    if (action.type === 'submit_batch' && currentRole === 'ShiftLead') return false
    return true
  }

  return (
    <div
      className={`action-tile action-tile-${getStatusColor()}`}
      style={{
        animation: 'slideInLeft 300ms ease',
      }}
    >
      <div className="action-tile-header" onClick={() => setIsExpanded(!isExpanded)}>
        <div className="action-tile-status">{getStatusIcon()}</div>
        <div className="action-tile-content">
          <div className="action-tile-title">{action.title}</div>
          <div className="action-tile-description">{action.description}</div>
        </div>
        <div className="action-tile-priority">
          {action.priority === 'high' && (
            <span className="action-tile-priority-badge action-tile-priority-high">High</span>
          )}
          {action.priority === 'medium' && (
            <span className="action-tile-priority-badge action-tile-priority-medium">Med</span>
          )}
        </div>
      </div>

      {isExpanded && (
        <div className="action-tile-expanded">
          {action.type === 'resolve_mismatch' && action.metadata?.suggestedCredit && (
            <div className="action-tile-meta">
              <strong>Suggested Credit:</strong>{' '}
              {new Intl.NumberFormat('en-GB', {
                style: 'currency',
                currency: 'GBP',
              }).format(action.metadata.suggestedCredit)}
            </div>
          )}
          {action.type === 'pair_dn' && action.metadata?.confidence !== undefined && (
            <div className="action-tile-meta">
              <strong>Confidence:</strong> {Math.round(action.metadata.confidence * 100)}%
            </div>
          )}
          {action.type === 'submit_batch' && action.metadata?.count && (
            <div className="action-tile-meta">
              <strong>Invoices Ready:</strong> {action.metadata.count}
            </div>
          )}
          {action.type === 'review_ocr' && action.metadata?.pages && (
            <div className="action-tile-meta">
              <strong>Pages with Low Confidence:</strong> {action.metadata.pages}
            </div>
          )}

          <div className="action-tile-actions">
            {canPerformAction() && (
              <button
                className="action-tile-action-button action-tile-action-primary"
                onClick={handleAction}
                disabled={isProcessing}
              >
                {isProcessing ? 'Processing...' : 'Complete'}
              </button>
            )}
            {action.type === 'review_ocr' && (
              <button
                className="action-tile-action-button"
                onClick={() => {
                  // Navigate to invoice detail
                  if (action.metadata?.invoiceId) {
                    window.location.href = `/invoices?id=${action.metadata.invoiceId}`
                  }
                }}
              >
                Review
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

