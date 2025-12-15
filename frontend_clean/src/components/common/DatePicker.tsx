import { useState, useRef, useEffect } from 'react'
import { Calendar, ChevronLeft, ChevronRight } from 'lucide-react'
import './DatePicker.css'

interface DatePickerProps {
  value: string
  onChange: (value: string) => void
  required?: boolean
  className?: string
  placeholder?: string
}

export function DatePicker({ value, onChange, required, className = '', placeholder }: DatePickerProps) {
  const [isOpen, setIsOpen] = useState(false)
  const [currentMonth, setCurrentMonth] = useState(new Date())
  const containerRef = useRef<HTMLDivElement>(null)
  const popupRef = useRef<HTMLDivElement>(null)
  const isNavigatingRef = useRef(false)

  // Parse the value (YYYY-MM-DD format)
  const selectedDate = value ? new Date(value + 'T00:00:00') : null

  // Close when clicking outside
  useEffect(() => {
    if (!isOpen) return

    function handleClickOutside(event: MouseEvent) {
      // If we're navigating, don't close
      if (isNavigatingRef.current) {
        return
      }

      const target = event.target as Element
      
      // Check if click is inside the popup or container
      if (popupRef.current?.contains(target as Node) || 
          containerRef.current?.contains(target as Node)) {
        // Check if it's specifically a navigation button
        const isNavButton = target.closest?.('.date-picker-nav-button') || 
                           target.classList?.contains('date-picker-nav-button') ||
                           (target.tagName === 'BUTTON' && target.closest?.('.date-picker-popup'))
        if (isNavButton) {
          return // Don't close on navigation button clicks
        }
        // For other clicks inside popup, don't close
        if (popupRef.current?.contains(target as Node)) {
          return
        }
        // If clicking the input, let it handle the toggle
        if (target.closest?.('.date-picker-input')) {
          return
        }
      }
      
      // Click is outside, close the popup
      setIsOpen(false)
    }

    // Use a longer delay to ensure button clicks are fully processed
    const timeoutId = setTimeout(() => {
      document.addEventListener('click', handleClickOutside, true)
    }, 100)
    
    return () => {
      clearTimeout(timeoutId)
      document.removeEventListener('click', handleClickOutside, true)
    }
  }, [isOpen])

  // Set current month to selected date when opening (only on initial open, not on every selectedDate change)
  useEffect(() => {
    if (isOpen) {
      if (selectedDate) {
        setCurrentMonth(new Date(selectedDate.getFullYear(), selectedDate.getMonth(), 1))
      } else {
        setCurrentMonth(new Date())
      }
    }
    // Only run when isOpen changes, not when selectedDate changes
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isOpen])

  const formatDisplayDate = (dateString: string) => {
    if (!dateString) return ''
    const date = new Date(dateString + 'T00:00:00')
    const day = date.getDate().toString().padStart(2, '0')
    const month = (date.getMonth() + 1).toString().padStart(2, '0')
    const year = date.getFullYear()
    return `${day}/${month}/${year}`
  }

  const getDaysInMonth = (date: Date) => {
    return new Date(date.getFullYear(), date.getMonth() + 1, 0).getDate()
  }

  const getFirstDayOfMonth = (date: Date) => {
    const firstDay = new Date(date.getFullYear(), date.getMonth(), 1)
    return firstDay.getDay() === 0 ? 6 : firstDay.getDay() - 1 // Monday = 0
  }

  const handleDateSelect = (day: number) => {
    const year = currentMonth.getFullYear()
    const month = currentMonth.getMonth()
    const date = new Date(year, month, day)
    const dateString = `${year}-${String(month + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`
    onChange(dateString)
    setIsOpen(false)
  }

  const handleToday = () => {
    const today = new Date()
    const dateString = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}-${String(today.getDate()).padStart(2, '0')}`
    onChange(dateString)
    setIsOpen(false)
  }

  const handleClear = () => {
    onChange('')
    setIsOpen(false)
  }

  const navigateMonth = (direction: 'prev' | 'next') => {
    // Set flag immediately and synchronously
    isNavigatingRef.current = true
    
    setCurrentMonth(prev => {
      const newDate = new Date(prev)
      if (direction === 'prev') {
        newDate.setMonth(prev.getMonth() - 1)
      } else {
        newDate.setMonth(prev.getMonth() + 1)
      }
      return newDate
    })
    
    // Reset flag after navigation completes
    requestAnimationFrame(() => {
      setTimeout(() => {
        isNavigatingRef.current = false
      }, 200)
    })
  }

  const navigateYear = (direction: 'prev' | 'next') => {
    // Set flag immediately and synchronously
    isNavigatingRef.current = true
    
    setCurrentMonth(prev => {
      const newDate = new Date(prev)
      if (direction === 'prev') {
        newDate.setFullYear(prev.getFullYear() - 1)
      } else {
        newDate.setFullYear(prev.getFullYear() + 1)
      }
      return newDate
    })
    
    // Reset flag after navigation completes
    requestAnimationFrame(() => {
      setTimeout(() => {
        isNavigatingRef.current = false
      }, 200)
    })
  }

  const daysInMonth = getDaysInMonth(currentMonth)
  const firstDay = getFirstDayOfMonth(currentMonth)
  const days: (number | null)[] = []

  // Add empty cells for days before the first day of the month
  for (let i = 0; i < firstDay; i++) {
    days.push(null)
  }

  // Add days of the month
  for (let day = 1; day <= daysInMonth; day++) {
    days.push(day)
  }

  const monthNames = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']
  const dayNames = ['Mo', 'Tu', 'We', 'Th', 'Fr', 'Sa', 'Su']

  const today = new Date()
  const isToday = (day: number) => {
    return (
      day === today.getDate() &&
      currentMonth.getMonth() === today.getMonth() &&
      currentMonth.getFullYear() === today.getFullYear()
    )
  }

  const isSelected = (day: number) => {
    if (!selectedDate) return false
    return (
      day === selectedDate.getDate() &&
      currentMonth.getMonth() === selectedDate.getMonth() &&
      currentMonth.getFullYear() === selectedDate.getFullYear()
    )
  }

  return (
    <div className={`date-picker-container ${className}`} ref={containerRef}>
      <div
        className="date-picker-input"
        onClick={() => setIsOpen(!isOpen)}
        style={{ cursor: 'pointer' }}
      >
        <input
          type="text"
          readOnly
          value={formatDisplayDate(value)}
          placeholder={placeholder || 'Select date'}
          required={required}
          className="modal-form-input"
          style={{ cursor: 'pointer' }}
        />
        <Calendar size={18} className="date-picker-icon" />
      </div>

      {isOpen && (
        <div 
          ref={popupRef}
          className="date-picker-popup"
          onClick={(e) => {
            e.stopPropagation()
          }}
          onMouseDown={(e) => {
            e.stopPropagation()
          }}
          onMouseUp={(e) => {
            e.stopPropagation()
          }}
        >
          <div className="date-picker-header">
            <div className="date-picker-nav">
              <button
                type="button"
                className="date-picker-nav-button"
                onClick={(e) => {
                  e.stopPropagation()
                  e.preventDefault()
                  isNavigatingRef.current = true
                  navigateYear('prev')
                }}
                onMouseDown={(e) => {
                  e.stopPropagation()
                  e.preventDefault()
                  isNavigatingRef.current = true
                }}
                aria-label="Previous year"
              >
                <ChevronLeft size={16} />
              </button>
              <button
                type="button"
                className="date-picker-nav-button"
                onClick={(e) => {
                  e.stopPropagation()
                  e.preventDefault()
                  isNavigatingRef.current = true
                  navigateMonth('prev')
                }}
                onMouseDown={(e) => {
                  e.stopPropagation()
                  e.preventDefault()
                  isNavigatingRef.current = true
                }}
                aria-label="Previous month"
              >
                <ChevronLeft size={14} />
              </button>
            </div>
            <div className="date-picker-month-year">
              {monthNames[currentMonth.getMonth()]} {currentMonth.getFullYear()}
            </div>
            <div className="date-picker-nav">
              <button
                type="button"
                className="date-picker-nav-button"
                onClick={(e) => {
                  e.stopPropagation()
                  e.preventDefault()
                  isNavigatingRef.current = true
                  navigateMonth('next')
                }}
                onMouseDown={(e) => {
                  e.stopPropagation()
                  e.preventDefault()
                  isNavigatingRef.current = true
                }}
                aria-label="Next month"
              >
                <ChevronRight size={14} />
              </button>
              <button
                type="button"
                className="date-picker-nav-button"
                onClick={(e) => {
                  e.stopPropagation()
                  e.preventDefault()
                  isNavigatingRef.current = true
                  navigateYear('next')
                }}
                onMouseDown={(e) => {
                  e.stopPropagation()
                  e.preventDefault()
                  isNavigatingRef.current = true
                }}
                aria-label="Next year"
              >
                <ChevronRight size={16} />
              </button>
            </div>
          </div>

          <div className="date-picker-weekdays">
            {dayNames.map(day => (
              <div key={day} className="date-picker-weekday">
                {day}
              </div>
            ))}
          </div>

          <div className="date-picker-days">
            {days.map((day, index) => {
              if (day === null) {
                return <div key={`empty-${index}`} className="date-picker-day empty" />
              }
              return (
                <button
                  key={day}
                  type="button"
                  className={`date-picker-day ${isSelected(day) ? 'selected' : ''} ${isToday(day) ? 'today' : ''}`}
                  onClick={(e) => {
                    e.stopPropagation()
                    handleDateSelect(day)
                  }}
                >
                  {day}
                </button>
              )
            })}
          </div>

          <div className="date-picker-footer">
            <button
              type="button"
              className="date-picker-footer-button"
              onClick={(e) => {
                e.stopPropagation()
                handleClear()
              }}
            >
              Clear
            </button>
            <button
              type="button"
              className="date-picker-footer-button"
              onClick={(e) => {
                e.stopPropagation()
                handleToday()
              }}
            >
              Today
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

