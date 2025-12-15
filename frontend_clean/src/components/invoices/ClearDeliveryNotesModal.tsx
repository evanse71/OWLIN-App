import { useState, useEffect } from 'react'
import { X, AlertTriangle, Loader2 } from 'lucide-react'
import './Modal.css'

interface ClearDeliveryNotesModalProps {
  isOpen: boolean
  onClose: () => void
  onConfirm: () => void
  count: number
  loading?: boolean
}

export function ClearDeliveryNotesModal({
  isOpen,
  onClose,
  onConfirm,
  count,
  loading = false,
}: ClearDeliveryNotesModalProps) {
  const [step, setStep] = useState<1 | 2>(1)
  const [confirmText, setConfirmText] = useState('')

  // Reset state when modal opens/closes
  useEffect(() => {
    if (isOpen) {
      setStep(1)
      setConfirmText('')
    }
  }, [isOpen])

  // Handle escape key
  useEffect(() => {
    if (!isOpen) return

    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        if (step === 2) {
          setStep(1)
          setConfirmText('')
        } else {
          onClose()
        }
      }
    }

    window.addEventListener('keydown', handleEscape)
    return () => window.removeEventListener('keydown', handleEscape)
  }, [isOpen, step, onClose])

  if (!isOpen) return null

  const canConfirm = confirmText.trim().toUpperCase() === 'DELETE'

  const handleConfirm = () => {
    if (step === 1) {
      setStep(2)
    } else if (step === 2 && canConfirm) {
      onConfirm()
    }
  }

  const handleBack = () => {
    setStep(1)
    setConfirmText('')
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-container" onClick={(e) => e.stopPropagation()} style={{ maxWidth: '500px' }}>
        <div className="modal-header">
          <h2 className="modal-title">
            {step === 1 ? 'Clear All Non-Paired Delivery Notes' : 'Confirm Deletion'}
          </h2>
          <button className="modal-close-button" onClick={onClose} aria-label="Close modal">
            <X size={20} />
          </button>
        </div>

        <div className="modal-body">
          {step === 1 ? (
            <>
              <div style={{ 
                display: 'flex', 
                alignItems: 'center', 
                gap: '12px', 
                marginBottom: '20px',
                padding: '16px',
                background: 'rgba(239, 68, 68, 0.1)',
                border: '1px solid rgba(239, 68, 68, 0.3)',
                borderRadius: '12px'
              }}>
                <AlertTriangle size={24} style={{ color: 'var(--accent-red)', flexShrink: 0 }} />
                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: '16px', fontWeight: '600', marginBottom: '4px', color: 'var(--text-primary)' }}>
                    Warning: Permanent Deletion
                  </div>
                  <div style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>
                    You are about to delete <strong>{count}</strong> non-paired delivery note{count !== 1 ? 's' : ''}. This action cannot be undone.
                  </div>
                </div>
              </div>

              <div style={{ fontSize: '14px', color: 'var(--text-secondary)', lineHeight: '1.6', marginBottom: '24px' }}>
                <p style={{ marginBottom: '12px' }}>
                  This will permanently remove all selected delivery notes from the database. Only non-paired delivery notes will be deleted. Paired delivery notes are protected and will not be affected.
                </p>
                <p style={{ marginBottom: '0' }}>
                  Are you sure you want to continue?
                </p>
              </div>
            </>
          ) : (
            <>
              <div style={{ 
                display: 'flex', 
                alignItems: 'center', 
                gap: '12px', 
                marginBottom: '20px',
                padding: '16px',
                background: 'rgba(239, 68, 68, 0.15)',
                border: '1px solid rgba(239, 68, 68, 0.4)',
                borderRadius: '12px'
              }}>
                <AlertTriangle size={24} style={{ color: 'var(--accent-red)', flexShrink: 0 }} />
                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: '16px', fontWeight: '600', marginBottom: '4px', color: 'var(--text-primary)' }}>
                    Final Confirmation Required
                  </div>
                  <div style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>
                    Type <strong>DELETE</strong> to confirm deletion of {count} delivery note{count !== 1 ? 's' : ''}
                  </div>
                </div>
              </div>

              <div style={{ marginBottom: '24px' }}>
                <label style={{ 
                  display: 'block', 
                  fontSize: '13px', 
                  fontWeight: '500', 
                  marginBottom: '8px',
                  color: 'var(--text-primary)'
                }}>
                  Type "DELETE" to confirm:
                </label>
                <input
                  type="text"
                  value={confirmText}
                  onChange={(e) => setConfirmText(e.target.value)}
                  placeholder="Type DELETE here"
                  autoFocus
                  style={{
                    width: '100%',
                    padding: '12px 16px',
                    background: 'var(--bg-secondary)',
                    border: `2px solid ${canConfirm ? 'var(--accent-red)' : 'var(--border-color)'}`,
                    borderRadius: '8px',
                    fontSize: '14px',
                    color: 'var(--text-primary)',
                    outline: 'none',
                    transition: 'border-color 0.2s ease',
                  }}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' && canConfirm && !loading) {
                      handleConfirm()
                    }
                  }}
                />
                {confirmText && !canConfirm && (
                  <div style={{ 
                    fontSize: '12px', 
                    color: 'var(--accent-red)', 
                    marginTop: '6px' 
                  }}>
                    Text must match "DELETE" exactly
                  </div>
                )}
              </div>
            </>
          )}
        </div>

        <div className="modal-footer">
          {step === 1 ? (
            <>
              <button className="glass-button" onClick={onClose} disabled={loading}>
                Cancel
              </button>
              <button
                className="glass-button"
                onClick={handleConfirm}
                disabled={loading}
                style={{
                  background: 'var(--accent-red)',
                  borderColor: 'var(--accent-red)',
                  color: 'white',
                }}
              >
                Continue to Confirm
              </button>
            </>
          ) : (
            <>
              <button className="glass-button" onClick={handleBack} disabled={loading}>
                Back
              </button>
              <button className="glass-button" onClick={onClose} disabled={loading}>
                Cancel
              </button>
              <button
                className="glass-button"
                onClick={handleConfirm}
                disabled={!canConfirm || loading}
                style={{
                  background: canConfirm ? 'var(--accent-red)' : 'rgba(239, 68, 68, 0.3)',
                  borderColor: canConfirm ? 'var(--accent-red)' : 'rgba(239, 68, 68, 0.3)',
                  color: 'white',
                  cursor: canConfirm && !loading ? 'pointer' : 'not-allowed',
                  opacity: canConfirm && !loading ? 1 : 0.6,
                }}
              >
                {loading ? (
                  <>
                    <Loader2 size={16} style={{ animation: 'spin 1s linear infinite' }} />
                    Deleting...
                  </>
                ) : (
                  'Confirm Delete'
                )}
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  )
}

