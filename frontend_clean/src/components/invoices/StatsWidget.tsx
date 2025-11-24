import { memo } from 'react'
import type { FileItem } from '../../pages/Invoices'
import './StatsWidget.css'

interface StatsWidgetProps {
  files: FileItem[]
}

export const StatsWidget = memo(function StatsWidget({ files }: StatsWidgetProps) {
  const totalCount = files.length
  const scannedCount = files.filter((f) => f.status === 'scanned').length
  const submittedCount = files.filter((f) => f.submitted).length
  const flaggedCount = files.filter((f) => f.status === 'error').length
  const totalValue = files.reduce((sum, f) => {
    const value = f.metadata?.value || f.metadata?.total || 0
    return sum + value
  }, 0)

  if (totalCount === 0) return null

  return (
    <div className="stats-widget">
      <div className="stats-widget-item">
        <div className="stats-widget-label">Total Invoices</div>
        <div className="stats-widget-value">{totalCount}</div>
      </div>
      <div className="stats-widget-divider" />
      <div className="stats-widget-item">
        <div className="stats-widget-label">Processed</div>
        <div className="stats-widget-value stats-widget-value-success">{scannedCount}</div>
      </div>
      <div className="stats-widget-divider" />
      <div className="stats-widget-item">
        <div className="stats-widget-label">Matched</div>
        <div className="stats-widget-value stats-widget-value-info">{submittedCount}</div>
      </div>
      <div className="stats-widget-divider" />
      <div className="stats-widget-item">
        <div className="stats-widget-label">Flagged</div>
        <div className="stats-widget-value stats-widget-value-warning">{flaggedCount}</div>
      </div>
      <div className="stats-widget-divider" />
      <div className="stats-widget-item">
        <div className="stats-widget-label">Total Value</div>
        <div className="stats-widget-value stats-widget-value-primary">
          {new Intl.NumberFormat('en-GB', {
            style: 'currency',
            currency: 'GBP',
            maximumFractionDigits: 0,
          }).format(totalValue)}
        </div>
      </div>
    </div>
  )
})

