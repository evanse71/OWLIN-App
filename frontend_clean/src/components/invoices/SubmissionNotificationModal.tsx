import { useEffect } from 'react'
import { CheckCircle2, AlertTriangle } from 'lucide-react'
import './SubmissionNotificationModal.css'

interface SubmissionNotificationModalProps {
  isOpen: boolean
  type: 'success' | 'error'
  title: string
  message: string
  onClose: () => void
  onAction: () => void
}

export function SubmissionNotificationModal({
  isOpen,
  type,
  title,
  message,
  onClose,
  onAction,
}: SubmissionNotificationModalProps) {
  // Auto-dismiss after 3 seconds
  useEffect(() => {
    if (!isOpen) return

    const timer = setTimeout(() => {
      onAction()
      onClose()
    }, 3000)

    return () => clearTimeout(timer)
  }, [isOpen, onAction, onClose])

  if (!isOpen) return null

  return (
    <div className="submission-notification-overlay" onClick={() => { onAction(); onClose(); }}>
      <div className="submission-notification-card" onClick={(e) => e.stopPropagation()}>
        {type === 'success' ? (
          <>
            <div className="submission-notification-icon success-icon">
              <div className="success-checkmark-circle">
                <CheckCircle2 size={48} strokeWidth={2.5} />
              </div>
              <div className="confetti-container">
                {[...Array(8)].map((_, i) => (
                  <div
                    key={i}
                    className="confetti-piece"
                    style={{
                      '--rotation': `${i * 45}deg`,
                      '--delay': `${i * 0.1}s`,
                    } as React.CSSProperties}
                  />
                ))}
              </div>
            </div>
            <h2 className="submission-notification-title success-title">{title}</h2>
            <p className="submission-notification-message">{message}</p>
          </>
        ) : (
          <>
            <div className="submission-notification-icon error-icon">
              <div className="error-cone-container">
                <AlertTriangle size={48} strokeWidth={2.5} />
                <div className="error-dash-line"></div>
              </div>
            </div>
            <h2 className="submission-notification-title error-title">{title}</h2>
            <p className="submission-notification-message">{message}</p>
          </>
        )}
      </div>
    </div>
  )
}

