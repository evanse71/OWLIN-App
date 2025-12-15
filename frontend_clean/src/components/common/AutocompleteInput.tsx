import { useState, useEffect, useRef, useCallback } from 'react'
import './AutocompleteInput.css'

interface AutocompleteInputProps {
  value: string
  onChange: (value: string) => void
  onFetchSuggestions?: (query: string) => Promise<string[]>
  placeholder?: string
  className?: string
  required?: boolean
  debounceMs?: number
  minChars?: number
}

export function AutocompleteInput({
  value,
  onChange,
  onFetchSuggestions,
  placeholder,
  className = '',
  required = false,
  debounceMs = 400,
  minChars = 2
}: AutocompleteInputProps) {
  const inputRef = useRef<HTMLInputElement>(null)

  // Component now works as a regular input - no visual suggestions
  // The onFetchSuggestions prop is kept for potential future use but not displayed
  return (
    <div className={`autocomplete-input-wrapper ${className}`}>
      <input
        ref={inputRef}
        type="text"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        required={required}
        className="autocomplete-input"
      />
    </div>
  )
}

