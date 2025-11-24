import { useState, useRef, useEffect, useCallback } from 'react'
import './SmartSearchBar.css'

interface SmartSearchBarProps {
  value: string
  onChange: (value: string) => void
  placeholder?: string
  suggestions?: string[]
  onSuggestionSelect?: (suggestion: string) => void
}

export function SmartSearchBar({
  value,
  onChange,
  placeholder = 'Search suppliers, dates, amounts...',
  suggestions = [],
  onSuggestionSelect,
}: SmartSearchBarProps) {
  const [isFocused, setIsFocused] = useState(false)
  const [showSuggestions, setShowSuggestions] = useState(false)
  const [selectedIndex, setSelectedIndex] = useState(-1)
  const inputRef = useRef<HTMLInputElement>(null)
  const containerRef = useRef<HTMLDivElement>(null)

  const filteredSuggestions = suggestions.filter((s) =>
    s.toLowerCase().includes(value.toLowerCase())
  ).slice(0, 5)

  useEffect(() => {
    setShowSuggestions(isFocused && filteredSuggestions.length > 0 && value.length > 0)
  }, [isFocused, filteredSuggestions.length, value.length])

  const handleFocus = useCallback(() => {
    setIsFocused(true)
  }, [])

  const handleBlur = useCallback((e: React.FocusEvent) => {
    // Don't hide suggestions if clicking on them
    if (!containerRef.current?.contains(e.relatedTarget as Node)) {
      setIsFocused(false)
      setShowSuggestions(false)
    }
  }, [])

  const handleChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    onChange(e.target.value)
    setSelectedIndex(-1)
  }, [onChange])

  const handleSuggestionClick = useCallback((suggestion: string) => {
    onChange(suggestion)
    onSuggestionSelect?.(suggestion)
    setShowSuggestions(false)
    inputRef.current?.blur()
  }, [onChange, onSuggestionSelect])

  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (!showSuggestions || filteredSuggestions.length === 0) return

    switch (e.key) {
      case 'ArrowDown':
        e.preventDefault()
        setSelectedIndex((prev) =>
          prev < filteredSuggestions.length - 1 ? prev + 1 : prev
        )
        break
      case 'ArrowUp':
        e.preventDefault()
        setSelectedIndex((prev) => (prev > 0 ? prev - 1 : -1))
        break
      case 'Enter':
        e.preventDefault()
        if (selectedIndex >= 0 && selectedIndex < filteredSuggestions.length) {
          handleSuggestionClick(filteredSuggestions[selectedIndex])
        }
        break
      case 'Escape':
        setShowSuggestions(false)
        inputRef.current?.blur()
        break
    }
  }, [showSuggestions, filteredSuggestions, selectedIndex, handleSuggestionClick])

  return (
    <div className="smart-search-container" ref={containerRef}>
      <div className={`smart-search-input-wrapper ${isFocused ? 'focused' : ''}`}>
        <svg
          className="smart-search-icon"
          width="20"
          height="20"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <circle cx="11" cy="11" r="8" />
          <path d="m21 21-4.35-4.35" />
        </svg>
        <input
          ref={inputRef}
          type="text"
          className="smart-search-input"
          value={value}
          onChange={handleChange}
          onFocus={handleFocus}
          onBlur={handleBlur}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          aria-label="Search invoices"
        />
        {value && (
          <button
            className="smart-search-clear"
            onClick={() => {
              onChange('')
              inputRef.current?.focus()
            }}
            aria-label="Clear search"
          >
            <svg
              width="16"
              height="16"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <line x1="18" y1="6" x2="6" y2="18" />
              <line x1="6" y1="6" x2="18" y2="18" />
            </svg>
          </button>
        )}
      </div>

      {showSuggestions && (
        <div className="smart-search-suggestions">
          {filteredSuggestions.map((suggestion, index) => (
            <button
              key={suggestion}
              className={`smart-search-suggestion ${index === selectedIndex ? 'selected' : ''}`}
              onClick={() => handleSuggestionClick(suggestion)}
              onMouseEnter={() => setSelectedIndex(index)}
            >
              <svg
                width="16"
                height="16"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <path d="m21 21-4.35-4.35" />
              </svg>
              <span>{suggestion}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  )
}

