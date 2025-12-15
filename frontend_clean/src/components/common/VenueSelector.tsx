import { useState, useRef, useEffect } from 'react'
import { Building2, ChevronDown } from 'lucide-react'
import './VenueSelector.css'

interface VenueSelectorProps {
  value: string
  onChange: (value: string) => void
  venues?: string[]
  className?: string
}

export function VenueSelector({ value, onChange, venues = ['Waterloo', 'Royal Oak', 'Main Restaurant'], className = '' }: VenueSelectorProps) {
  const [isOpen, setIsOpen] = useState(false)
  const containerRef = useRef<HTMLDivElement>(null)

  // Close when clicking outside
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setIsOpen(false)
      }
    }

    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside)
      return () => document.removeEventListener('mousedown', handleClickOutside)
    }
  }, [isOpen])

  return (
    <div className={`venue-selector-container ${className}`} ref={containerRef}>
      <div
        className="venue-selector-input"
        onClick={() => setIsOpen(!isOpen)}
        style={{ cursor: 'pointer' }}
      >
        <input
          type="text"
          readOnly
          value={value}
          placeholder="Select venue"
          className="modal-form-input"
          style={{ cursor: 'pointer', paddingRight: '40px' }}
        />
        <div className="venue-selector-icons">
          <Building2 size={18} className="venue-selector-icon" />
          <ChevronDown 
            size={16} 
            className={`venue-selector-chevron ${isOpen ? 'open' : ''}`} 
          />
        </div>
      </div>

      {isOpen && (
        <div className="venue-selector-dropdown">
          {venues.map((venue) => (
            <button
              key={venue}
              type="button"
              className={`venue-selector-option ${value === venue ? 'selected' : ''}`}
              onClick={(e) => {
                e.stopPropagation()
                onChange(venue)
                setIsOpen(false)
              }}
            >
              {venue}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}

