import { useState } from 'react'
import { Building2, Search, Upload, Plus, ChevronDown } from 'lucide-react'
import './InvoicesHeader.css'

export type DateRange = 'today' | 'week' | 'month' | 'custom'

interface InvoicesHeaderProps {
  venue: string
  onVenueChange: (venue: string) => void
  dateRange: DateRange
  onDateRangeChange: (range: DateRange) => void
  searchQuery: string
  onSearchChange: (query: string) => void
  onUploadClick: () => void
  onNewManualInvoice: () => void
  onNewManualDN?: () => void // Optional for backward compatibility
  venues?: string[]
  manualPairingWorkflowActive?: boolean
  onToggleManualPairingWorkflow?: () => void
}

export function InvoicesHeader({
  venue,
  onVenueChange,
  dateRange,
  onDateRangeChange,
  searchQuery,
  onSearchChange,
  onUploadClick,
  onNewManualInvoice,
  onNewManualDN,
  venues = ['Waterloo', 'Royal Oak', 'Main Restaurant'],
  manualPairingWorkflowActive = false,
  onToggleManualPairingWorkflow,
}: InvoicesHeaderProps) {
  const [showVenueDropdown, setShowVenueDropdown] = useState(false)
  const [showDateDropdown, setShowDateDropdown] = useState(false)

  return (
    <header className="invoices-header-new">
      {/* Left Section: Title */}
      <div className="invoices-header-left">
        <div className="invoices-header-title-section">
          <h1 className="invoices-header-title">Invoices</h1>
        </div>
      </div>

      {/* Center Section: Filters Grouped Together */}
      <div className="invoices-header-center">
        <div className="invoices-header-filters">
          {/* Venue Selector */}
          <div className="dropdown-wrapper">
            <button
              className="glass-button secondary-action"
              onClick={() => setShowVenueDropdown(!showVenueDropdown)}
            >
              <Building2 size={16} className="button-icon" />
              <span className="button-text">{venue}</span>
              <ChevronDown size={14} className="button-chevron" />
            </button>
            {showVenueDropdown && (
              <div className="dropdown-menu">
                {venues.map((v) => (
                  <button
                    key={v}
                    className="dropdown-item"
                    onClick={() => {
                      onVenueChange(v)
                      setShowVenueDropdown(false)
                    }}
                  >
                    {v}
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Date Range Selector */}
          <div className="dropdown-wrapper">
            <button
              className="glass-button secondary-action"
              onClick={() => setShowDateDropdown(!showDateDropdown)}
            >
              <span className="button-text">
                {dateRange === 'today' && 'Today'}
                {dateRange === 'week' && 'This week'}
                {dateRange === 'month' && 'This month'}
                {dateRange === 'custom' && 'Custom'}
              </span>
              <ChevronDown size={14} className="button-chevron" />
            </button>
            {showDateDropdown && (
              <div className="dropdown-menu">
                <button
                  className="dropdown-item"
                  onClick={() => {
                    onDateRangeChange('today')
                    setShowDateDropdown(false)
                  }}
                >
                  Today
                </button>
                <button
                  className="dropdown-item"
                  onClick={() => {
                    onDateRangeChange('week')
                    setShowDateDropdown(false)
                  }}
                >
                  This week
                </button>
                <button
                  className="dropdown-item"
                  onClick={() => {
                    onDateRangeChange('month')
                    setShowDateDropdown(false)
                  }}
                >
                  This month
                </button>
                <button
                  className="dropdown-item"
                  onClick={() => {
                    onDateRangeChange('custom')
                    setShowDateDropdown(false)
                  }}
                >
                  Custom
                </button>
              </div>
            )}
          </div>
        </div>

        {/* Search - Secondary Position */}
        <div className="search-wrapper">
          <Search size={16} className="search-icon" />
          <input
            type="text"
            className="search-input"
            placeholder="Search by supplier, invoice # or filename"
            value={searchQuery}
            onChange={(e) => onSearchChange(e.target.value)}
          />
        </div>
      </div>

      {/* Right Section: Primary Actions */}
      <div className="invoices-header-right">
        <div className="invoices-header-actions">
          {onToggleManualPairingWorkflow && (
            <button
              className={`glass-button ${manualPairingWorkflowActive ? 'primary-action-large' : 'secondary-action'}`}
              onClick={onToggleManualPairingWorkflow}
              title="Toggle manual pairing mode"
            >
              <span className="button-text-full">
                {manualPairingWorkflowActive ? '✓ Pairing Mode' : 'Manual Pairing'}
              </span>
              <span className="button-text-short">
                {manualPairingWorkflowActive ? '✓ Pair' : 'Pair'}
              </span>
            </button>
          )}
          <button className="glass-button primary-action-large primary-action-upload" onClick={onUploadClick}>
            <Upload size={18} className="button-icon" />
            <span className="button-text-full">Upload documents</span>
            <span className="button-text-short">Upload</span>
          </button>
          <button
            className="glass-button primary-action-large"
            onClick={onNewManualInvoice}
          >
            <Plus size={18} className="button-icon" />
            <span className="button-text-full">Create invoice or delivery note</span>
            <span className="button-text-short">Create</span>
          </button>
        </div>
        {/* Spacer to prevent overlap with assistant */}
        <div className="invoices-header-assistant-spacer" />
      </div>
    </header>
  )
}

