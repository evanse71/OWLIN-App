import { memo } from 'react'
import { CheckCircle2, Clock, AlertCircle, XCircle } from 'lucide-react'
import './ConfidenceMeter.css'

export type ConfidenceBand = 'high' | 'medium' | 'low' | 'critical'

interface ConfidenceMeterProps {
  confidence: number
  confidenceBand?: ConfidenceBand
  showLabel?: boolean
  showBand?: boolean
}

export const ConfidenceMeter = memo(function ConfidenceMeter({
  confidence,
  confidenceBand,
  showLabel = true,
  showBand = true,
}: ConfidenceMeterProps) {
  // Calculate band from confidence if not provided
  const getBand = (conf: number): ConfidenceBand => {
    if (conf >= 80) return 'high'
    if (conf >= 60) return 'medium'
    if (conf >= 40) return 'low'
    return 'critical'
  }

  const band = confidenceBand || getBand(confidence)

  const getBandInfo = (b: ConfidenceBand) => {
    switch (b) {
      case 'high':
        return {
          color: 'success',
          label: 'High Confidence',
          icon: <CheckCircle2 size={14} />,
          message: 'Trust financially'
        }
      case 'medium':
        return {
          color: 'warning',
          label: 'Review Recommended',
          icon: <Clock size={14} />,
          message: 'Quick check needed'
        }
      case 'low':
        return {
          color: 'error',
          label: 'Manual Review Required',
          icon: <AlertCircle size={14} />,
          message: 'Significant issues'
        }
      case 'critical':
        return {
          color: 'error',
          label: 'Cannot Trust',
          icon: <XCircle size={14} />,
          message: 'Major data problems'
        }
    }
  }

  const bandInfo = getBandInfo(band)
  const percentage = Math.max(0, Math.min(100, confidence))

  return (
    <div className="confidence-meter">
      {showLabel && (
        <div className="confidence-meter-label">
          <span>Confidence</span>
          {showBand ? (
            <div className={`confidence-meter-band ${bandInfo.color}`}>
              {bandInfo.icon}
              <span>{bandInfo.label}</span>
            </div>
          ) : (
            <span className={`confidence-meter-value ${bandInfo.color}`}>
              {confidence.toFixed(1)}%
            </span>
          )}
        </div>
      )}
      <div className="confidence-meter-bar">
        <div
          className={`confidence-meter-fill ${bandInfo.color}`}
          style={{ width: `${percentage}%` }}
        />
      </div>
      {band !== 'high' && (
        <div className={`confidence-meter-warning ${bandInfo.color}`}>
          {bandInfo.message}
        </div>
      )}
    </div>
  )
})

