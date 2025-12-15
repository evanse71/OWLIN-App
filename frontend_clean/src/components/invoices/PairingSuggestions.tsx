import { memo } from 'react'
import { AlertTriangle } from 'lucide-react'
import './PairingSuggestions.css'

export interface QuantityDifference {
  description: string
  invoiceQty: number
  dnQty: number
  difference: number
}

export interface PairingSuggestion {
  id: string
  supplier: string
  date: string
  value: number
  confidence: number
  reason: string
  quantityDifferences?: QuantityDifference[]
  hasQuantityMismatch?: boolean
  deliveryNoteId?: string
  deliveryNoteNumber?: string
  quantityMatchScore?: number
  quantityWarnings?: string[]
}

interface PairingSuggestionsProps {
  suggestions: PairingSuggestion[]
  onSelect?: (suggestion: PairingSuggestion) => void
}

export const PairingSuggestions = memo(function PairingSuggestions({
  suggestions,
  onSelect,
}: PairingSuggestionsProps) {
  if (suggestions.length === 0) {
    return (
      <div className="pairing-suggestions-empty">
        <p>No pairing suggestions available</p>
      </div>
    )
  }

  return (
    <div className="pairing-suggestions">
      <h3 className="pairing-suggestions-title">Suggested Pairings</h3>
      <div className="pairing-suggestions-list">
        {suggestions.map((suggestion) => (
          <button
            key={suggestion.id}
            className="pairing-suggestion-card"
            onClick={() => onSelect?.(suggestion)}
          >
            <div className="pairing-suggestion-header">
              <div className="pairing-suggestion-supplier">{suggestion.supplier}</div>
              <div className={`pairing-suggestion-confidence confidence-${getConfidenceLevel(suggestion.confidence)}`}>
                {Math.round(suggestion.confidence * 100)}% match
              </div>
            </div>
            <div className="pairing-suggestion-details">
              <span className="pairing-suggestion-date">{formatDate(suggestion.date)}</span>
              <span className="pairing-suggestion-separator">•</span>
              <span className="pairing-suggestion-value">
                {formatCurrency(suggestion.value)}
              </span>
            </div>
            <div className="pairing-suggestion-reason">{suggestion.reason}</div>
            {suggestion.quantityMatchScore !== undefined && (
              <div className="pairing-suggestion-quantity">
                <span className={`quantity-match-score score-${getQuantityScoreLevel(suggestion.quantityMatchScore)}`}>
                  Qty Match: {(suggestion.quantityMatchScore * 100).toFixed(0)}%
                </span>
                {suggestion.quantityMatchScore < 0.8 && suggestion.quantityWarnings && suggestion.quantityWarnings.length > 0 && (
                  <div className="quantity-warning-badge" title={suggestion.quantityWarnings.join('; ')}>
                    <AlertTriangle size={14} />
                    <span>{suggestion.quantityWarnings.length} warning{suggestion.quantityWarnings.length !== 1 ? 's' : ''}</span>
                  </div>
                )}
              </div>
            )}
            {suggestion.hasQuantityMismatch && (
              <div className="pairing-suggestion-warning" style={{ 
                marginTop: '8px', 
                padding: '8px', 
                background: 'rgba(239, 68, 68, 0.1)', 
                borderRadius: '4px',
                fontSize: '12px',
                color: 'var(--accent-red)'
              }}>
                ⚠️ Quantity mismatch detected
              </div>
            )}
            {suggestion.quantityDifferences && suggestion.quantityDifferences.length > 0 && (
              <div style={{ marginTop: '8px', fontSize: '11px', color: 'var(--text-secondary)' }}>
                <details style={{ cursor: 'pointer' }}>
                  <summary style={{ fontWeight: '500' }}>View quantity differences</summary>
                  <div style={{ marginTop: '8px', padding: '8px', background: 'var(--bg-secondary)', borderRadius: '4px' }}>
                    {suggestion.quantityDifferences.map((diff, idx) => (
                      <div key={idx} style={{ marginBottom: '4px', display: 'flex', justifyContent: 'space-between' }}>
                        <span>{diff.description}:</span>
                        <span style={{ color: diff.difference !== 0 ? 'var(--accent-red)' : 'var(--accent-green)' }}>
                          Invoice: {diff.invoiceQty} | DN: {diff.dnQty} | Diff: {diff.difference > 0 ? '+' : ''}{diff.difference}
                        </span>
                      </div>
                    ))}
                  </div>
                </details>
              </div>
            )}
          </button>
        ))}
      </div>
    </div>
  )
})

function getConfidenceLevel(confidence: number): 'high' | 'medium' | 'low' {
  // Confidence is a decimal (0.0-1.0), so check against 0.8 (80%) and 0.6 (60%)
  if (confidence >= 0.8) return 'high'
  if (confidence >= 0.6) return 'medium'
  return 'low'
}

function formatDate(dateString: string): string {
  return new Date(dateString).toLocaleDateString('en-GB', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  })
}

function formatCurrency(value: number): string {
  return new Intl.NumberFormat('en-GB', {
    style: 'currency',
    currency: 'GBP',
  }).format(value)
}

function getQuantityScoreLevel(score: number): 'high' | 'medium' | 'low' {
  if (score >= 0.8) return 'high'
  if (score >= 0.6) return 'medium'
  return 'low'
}

