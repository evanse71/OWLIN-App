import { AlertCircle, CheckCircle2, Clock, XCircle, Info } from 'lucide-react'
import './ConfidenceBreakdown.css'

export interface ConfidenceBreakdownProps {
  overallConfidence: number
  ocrQuality: number
  extractionQuality: number
  validationQuality: number
  band: 'high' | 'medium' | 'low' | 'critical'
  primaryIssue?: string
  remediationHints?: string[]
}

export function ConfidenceBreakdown({
  overallConfidence,
  ocrQuality,
  extractionQuality,
  validationQuality,
  band,
  primaryIssue,
  remediationHints = [],
}: ConfidenceBreakdownProps) {
  const getBandColor = (band: string) => {
    switch (band) {
      case 'high':
        return 'var(--color-success)'
      case 'medium':
        return 'var(--color-warning)'
      case 'low':
        return 'var(--color-error)'
      case 'critical':
        return 'var(--color-critical, #dc2626)'
      default:
        return 'var(--color-text-secondary)'
    }
  }

  const getBandIcon = (band: string) => {
    switch (band) {
      case 'high':
        return <CheckCircle2 size={20} />
      case 'medium':
        return <Clock size={20} />
      case 'low':
        return <AlertCircle size={20} />
      case 'critical':
        return <XCircle size={20} />
      default:
        return <AlertCircle size={20} />
    }
  }

  const getBandLabel = (band: string) => {
    switch (band) {
      case 'high':
        return 'High Confidence - Trust Financially'
      case 'medium':
        return 'Review Recommended - Quick Check Needed'
      case 'low':
        return 'Manual Review Required - Significant Issues'
      case 'critical':
        return 'Cannot Trust - Major Data Problems'
      default:
        return 'Needs Review'
    }
  }

  const getQualityColor = (quality: number) => {
    if (quality >= 0.75) return 'var(--color-success)'
    if (quality >= 0.50) return 'var(--color-warning)'
    return 'var(--color-error)'
  }

  const formatPercent = (value: number) => {
    return `${Math.round(value * 100)}%`
  }

  return (
    <div className="confidence-breakdown">
      <div className="confidence-breakdown__header">
        <div
          className="confidence-breakdown__band"
          style={{ color: getBandColor(band) }}
        >
          {getBandIcon(band)}
          <div>
            <div className="confidence-breakdown__band-label">{getBandLabel(band)}</div>
            <div className="confidence-breakdown__overall">
              Overall Confidence: {formatPercent(overallConfidence)}
            </div>
          </div>
        </div>
      </div>

      <div className="confidence-breakdown__factors">
        <div className="confidence-breakdown__factor">
          <div className="confidence-breakdown__factor-header">
            <span className="confidence-breakdown__factor-label">OCR Quality</span>
            <span
              className="confidence-breakdown__factor-value"
              style={{ color: getQualityColor(ocrQuality) }}
            >
              {formatPercent(ocrQuality)}
            </span>
          </div>
          <div className="confidence-breakdown__factor-bar">
            <div
              className="confidence-breakdown__factor-bar-fill"
              style={{
                width: `${ocrQuality * 100}%`,
                backgroundColor: getQualityColor(ocrQuality),
              }}
            />
          </div>
          <div className="confidence-breakdown__factor-weight">Weight: 40%</div>
        </div>

        <div className="confidence-breakdown__factor">
          <div className="confidence-breakdown__factor-header">
            <span className="confidence-breakdown__factor-label">Extraction Quality</span>
            <span
              className="confidence-breakdown__factor-value"
              style={{ color: getQualityColor(extractionQuality) }}
            >
              {formatPercent(extractionQuality)}
            </span>
          </div>
          <div className="confidence-breakdown__factor-bar">
            <div
              className="confidence-breakdown__factor-bar-fill"
              style={{
                width: `${extractionQuality * 100}%`,
                backgroundColor: getQualityColor(extractionQuality),
              }}
            />
          </div>
          <div className="confidence-breakdown__factor-weight">Weight: 35%</div>
        </div>

        <div className="confidence-breakdown__factor">
          <div className="confidence-breakdown__factor-header">
            <span className="confidence-breakdown__factor-label">Validation Quality</span>
            <span
              className="confidence-breakdown__factor-value"
              style={{ color: getQualityColor(validationQuality) }}
            >
              {formatPercent(validationQuality)}
            </span>
          </div>
          <div className="confidence-breakdown__factor-bar">
            <div
              className="confidence-breakdown__factor-bar-fill"
              style={{
                width: `${validationQuality * 100}%`,
                backgroundColor: getQualityColor(validationQuality),
              }}
            />
          </div>
          <div className="confidence-breakdown__factor-weight">Weight: 25%</div>
        </div>
      </div>

      {primaryIssue && (
        <div className="confidence-breakdown__issue">
          <AlertCircle size={16} />
          <div>
            <div className="confidence-breakdown__issue-title">Primary Issue</div>
            <div className="confidence-breakdown__issue-text">{primaryIssue}</div>
          </div>
        </div>
      )}

      {remediationHints.length > 0 && (
        <div className="confidence-breakdown__hints">
          <div className="confidence-breakdown__hints-header">
            <Info size={16} />
            <span>Remediation Hints</span>
          </div>
          <ul className="confidence-breakdown__hints-list">
            {remediationHints.map((hint, idx) => (
              <li key={idx}>{hint}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}

