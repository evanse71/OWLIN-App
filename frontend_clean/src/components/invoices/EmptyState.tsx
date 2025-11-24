import { memo } from 'react'
import './EmptyState.css'

interface EmptyStateProps {
  title?: string
  description?: string
  actionLabel?: string
  onAction?: () => void
  icon?: string
}

export const EmptyState = memo(function EmptyState({
  title = 'No invoices yet',
  description = 'Upload your first invoice to get started',
  actionLabel = 'Upload Invoice',
  onAction,
  icon = '📄',
}: EmptyStateProps) {
  return (
    <div className="empty-state">
      <div className="empty-state-icon">{icon}</div>
      <h2 className="empty-state-title">{title}</h2>
      <p className="empty-state-description">{description}</p>
      {onAction && (
        <button className="empty-state-action" onClick={onAction}>
          {actionLabel}
        </button>
      )}
    </div>
  )
})

