/**
 * Empty State Component
 * Used for "All clear" states and empty data scenarios
 */

import { CheckCircle2, AlertCircle, Info } from 'lucide-react'
import './EmptyState.css'

interface EmptyStateProps {
  title: string
  message: string
  icon?: 'check' | 'info' | 'alert'
}

export function EmptyState({ title, message, icon = 'info' }: EmptyStateProps) {
  const getIcon = () => {
    switch (icon) {
      case 'check':
        return <CheckCircle2 size={32} className="empty-state-icon empty-state-icon-check" />
      case 'alert':
        return <AlertCircle size={32} className="empty-state-icon empty-state-icon-alert" />
      default:
        return <Info size={32} className="empty-state-icon empty-state-icon-info" />
    }
  }

  return (
    <div className="empty-state">
      {getIcon()}
      <h3 className="empty-state-title">{title}</h3>
      <p className="empty-state-message">{message}</p>
    </div>
  )
}

