import { memo } from 'react'
import './ConfidenceMeter.css'

interface ConfidenceMeterProps {
  confidence: number
  showLabel?: boolean
}

export const ConfidenceMeter = memo(function ConfidenceMeter({
  confidence,
  showLabel = true,
}: ConfidenceMeterProps) {
  const getColor = (conf: number): string => {
    if (conf >= 80) return 'success'
    if (conf >= 70) return 'warning'
    return 'error'
  }

  const color = getColor(confidence)
  const percentage = Math.max(0, Math.min(100, confidence))

  return (
    <div className="confidence-meter">
      {showLabel && (
        <div className="confidence-meter-label">
          <span>Confidence</span>
          <span className={`confidence-meter-value ${color}`}>
            {confidence.toFixed(1)}%
          </span>
        </div>
      )}
      <div className="confidence-meter-bar">
        <div
          className={`confidence-meter-fill ${color}`}
          style={{ width: `${percentage}%` }}
        />
      </div>
      {confidence < 80 && (
        <div className={`confidence-meter-warning ${color}`}>
          {confidence >= 70
            ? 'Medium confidence - review recommended'
            : 'Low confidence - manual review required'}
        </div>
      )}
    </div>
  )
})

