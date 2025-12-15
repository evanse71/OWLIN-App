import { memo, useState, useEffect } from 'react'
import { Package, Trash2, X, CheckCircle2, Circle } from 'lucide-react'
import './DeliveryNoteCard.css'

export interface DeliveryNoteListItem {
  id: string
  noteNumber?: string
  supplier?: string
  date?: string
  total?: number
  venue?: string
  isPaired?: boolean
  recommendedInvoice?: {
    id: string
    invoiceNumber?: string
    confidence?: number
  }
  pairingType?: 'automatic' | 'manual' | 'suggested' | 'pending_confirmation'
}

interface DeliveryNoteCardProps {
  deliveryNote: DeliveryNoteListItem
  isSelected?: boolean
  onClick: () => void
  onDelete?: (dnId: string) => void
}

function formatCurrency(value?: number): string {
  if (value === undefined || value === null) return '£0.00'
  return new Intl.NumberFormat('en-GB', { style: 'currency', currency: 'GBP' }).format(value)
}

function formatDate(dateStr?: string): string {
  if (!dateStr) return 'No date'
  try {
    const date = new Date(dateStr)
    // Always show the actual date in number form (e.g., "27 Nov 2025")
    return date.toLocaleDateString('en-GB', {
      day: 'numeric',
      month: 'short',
      year: 'numeric',
    })
  } catch {
    return dateStr
  }
}

export const DeliveryNoteCard = memo(function DeliveryNoteCard({
  deliveryNote,
  isSelected = false,
  onClick,
  onDelete,
}: DeliveryNoteCardProps) {
  const pairingType = deliveryNote.pairingType || 'suggested'
  const confidence = deliveryNote.recommendedInvoice?.confidence
  const [isDeleteConfirming, setIsDeleteConfirming] = useState(false)

  const handleDeleteClick = (e: React.MouseEvent) => {
    e.stopPropagation()
    setIsDeleteConfirming(true)
  }

  const handleDeleteCancel = (e: React.MouseEvent) => {
    e.stopPropagation()
    setIsDeleteConfirming(false)
  }

  const handleDeleteConfirm = (e: React.MouseEvent) => {
    e.stopPropagation()
    if (onDelete) {
      onDelete(deliveryNote.id)
      setIsDeleteConfirming(false)
    }
  }

  // Close delete confirmation on Escape key
  useEffect(() => {
    const handleEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape' && isDeleteConfirming) {
        setIsDeleteConfirming(false)
      }
    }

    if (isDeleteConfirming) {
      document.addEventListener('keydown', handleEscape)
    }

    return () => {
      document.removeEventListener('keydown', handleEscape)
    }
  }, [isDeleteConfirming])

  return (
    <div
      className={`delivery-note-card ${isSelected ? 'selected' : ''} ${isDeleteConfirming ? 'delete-confirming' : ''}`}
      onClick={onClick}
      tabIndex={0}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault()
          if (!isDeleteConfirming) {
            onClick()
          }
        } else if (e.key === 'Escape' && isDeleteConfirming) {
          e.preventDefault()
          setIsDeleteConfirming(false)
        }
      }}
    >
      {/* Delete button - only show if onDelete handler provided */}
      {onDelete && (
        <>
          {!isDeleteConfirming ? (
            <button
              className="delivery-note-card-delete-btn"
              onClick={handleDeleteClick}
              title="Delete delivery note"
              aria-label="Delete delivery note"
            >
              <Trash2 size={14} />
            </button>
          ) : (
            <div
              className="delivery-note-card-delete-confirm"
              onClick={handleDeleteConfirm}
            >
              <button
                className="delivery-note-card-delete-close"
                onClick={(e) => {
                  e.stopPropagation()
                  handleDeleteCancel(e)
                }}
                title="Close"
                aria-label="Close confirmation"
              >
                <X size={16} />
              </button>
              <div className="delivery-note-card-delete-confirm-content">
                <div className="delivery-note-card-delete-confirm-text">
                  Confirm Delete
                </div>
              </div>
            </div>
          )}
        </>
      )}
      <div className="delivery-note-card-content">
        {/* Row 1: Supplier name (main header, like invoice cards) */}
        <div className="delivery-note-card-row-1">
          <div className="delivery-note-card-supplier" style={{ fontSize: '15px', fontWeight: '600', flex: 1 }}>
            {deliveryNote.supplier || 'Unknown Supplier'}
          </div>
          {/* Pairing Type Badge - positioned to avoid overlap with delete button */}
          {pairingType && (
            <span className={`badge badge-pairing-${pairingType === 'pending_confirmation' ? 'automatic' : pairingType}`} style={{ marginRight: onDelete ? '28px' : '0' }}>
              {pairingType === 'automatic' || pairingType === 'pending_confirmation' ? 'Auto' : pairingType === 'manual' ? 'Manual' : 'Suggested'}
            </span>
          )}
        </div>

        {/* Row 2: Venue/Location and Date */}
        <div className="delivery-note-card-row-3" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '12px', color: 'var(--text-muted)', marginTop: '6px', marginBottom: '8px' }}>
          <div className="delivery-note-card-venue">
            {deliveryNote.venue ? `Site: ${deliveryNote.venue}` : deliveryNote.noteNumber ? `DN: ${deliveryNote.noteNumber}` : `DN-${deliveryNote.id.slice(0, 8)}`}
          </div>
          <div className="delivery-note-card-date">
            {formatDate(deliveryNote.date)}
          </div>
        </div>

        {/* Row 4: Status badges and recommended invoice */}
        <div className="delivery-note-card-row-4" style={{ display: 'flex', gap: '6px', flexWrap: 'wrap', alignItems: 'center', marginTop: '8px' }}>
          {/* Paired/Unpaired Status Symbol */}
          {deliveryNote.isPaired !== undefined && (
            <span title={deliveryNote.isPaired ? 'Paired' : 'Unpaired'} style={{ display: 'inline-flex', alignItems: 'center' }}>
              {deliveryNote.isPaired ? (
                <CheckCircle2 size={14} style={{ color: 'var(--accent-green)' }} />
              ) : (
                <Circle size={14} style={{ color: 'var(--text-muted)' }} />
              )}
            </span>
          )}
          {/* Recommended Invoice */}
          {deliveryNote.recommendedInvoice && (
            <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
              → {deliveryNote.recommendedInvoice.invoiceNumber || `INV-${deliveryNote.recommendedInvoice.id.slice(0, 8)}`}
              {confidence !== undefined && ` (${Math.round(confidence * 100)}%)`}
            </div>
          )}
        </div>
      </div>
    </div>
  )
})

