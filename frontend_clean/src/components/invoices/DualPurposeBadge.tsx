import { memo } from 'react'
import './DualPurposeBadge.css'

export const DualPurposeBadge = memo(function DualPurposeBadge() {
  return (
    <div className="dual-purpose-badge" title="This receipt acts as both an invoice and delivery note">
      <span className="dual-purpose-badge-icon">🧾</span>
      <span className="dual-purpose-badge-text">Invoice + Delivery Note</span>
    </div>
  )
})

