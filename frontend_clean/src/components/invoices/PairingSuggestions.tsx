import { memo } from 'react'
import './PairingSuggestions.css'

export interface PairingSuggestion {
  id: string
  supplier: string
  date: string
  value: number
  confidence: number
  reason: string
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
                {suggestion.confidence}% match
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
          </button>
        ))}
      </div>
    </div>
  )
})

function getConfidenceLevel(confidence: number): 'high' | 'medium' | 'low' {
  if (confidence >= 80) return 'high'
  if (confidence >= 60) return 'medium'
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

