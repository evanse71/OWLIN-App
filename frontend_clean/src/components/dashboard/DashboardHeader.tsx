/**
 * Dashboard Header Component
 * Venue switcher, date range, search, health pill, and quick actions
 */

import { useState, useEffect } from 'react'
import { Building2, Search, Upload, Download, Settings, Calendar, ChevronDown } from 'lucide-react'
import { useDashboardFilters } from '../../contexts/DashboardFiltersContext'
import { checkHealth } from '../../lib/api'
import type { DateRange } from '../../lib/dashboardApi'
import './DashboardHeader.css'

interface DashboardHeaderProps {
  currentRole: 'GM' | 'Finance' | 'ShiftLead'
}

interface HealthStatus {
  api: 'ok' | 'error' | 'checking'
  db: 'ok' | 'error' | 'checking'
  licenseDays: number | null
}

export function DashboardHeader({ currentRole }: DashboardHeaderProps) {
  const { filters, setVenue, setDateRange, setSearchQuery } = useDashboardFilters()
  const [showVenueDropdown, setShowVenueDropdown] = useState(false)
  const [showDateDropdown, setShowDateDropdown] = useState(false)
  const [healthStatus, setHealthStatus] = useState<HealthStatus>({
    api: 'checking',
    db: 'checking',
    licenseDays: null,
  })

  // Mock venues - in real app this would come from API
  const venues = currentRole === 'GM' 
    ? ['All Venues', 'Royal Oak Hotel', 'Waterloo', 'Main Restaurant']
    : ['Royal Oak Hotel']

  const dateRanges: { value: DateRange; label: string }[] = [
    { value: 'today', label: 'Today' },
    { value: '7d', label: '7 Days' },
    { value: '30d', label: '30 Days' },
    { value: 'custom', label: 'Custom' },
  ]

  // Check health status
  useEffect(() => {
    let mounted = true

    async function checkHealthStatus() {
      try {
        const health = await checkHealth()
        if (mounted) {
          setHealthStatus((prev) => ({
            ...prev,
            api: health.status === 'ok' ? 'ok' : 'error',
          }))
        }
      } catch (e) {
        if (mounted) {
          setHealthStatus((prev) => ({ ...prev, api: 'error' }))
        }
      }

      // Mock DB check - in real app this would be a separate endpoint
      if (mounted) {
        setHealthStatus((prev) => ({ ...prev, db: 'ok' }))
      }

      // Mock license check - in real app this would come from license validator
      if (mounted) {
        setHealthStatus((prev) => ({ ...prev, licenseDays: 30 }))
      }
    }

    checkHealthStatus()
    const interval = setInterval(checkHealthStatus, 30000) // Check every 30 seconds

    return () => {
      mounted = false
      clearInterval(interval)
    }
  }, [])

  const handleUploadClick = () => {
    // Navigate to invoices page with upload action
    window.location.href = '/invoices?action=upload'
  }

  const handleExportClick = () => {
    // Trigger export - in real app this would open export modal
    console.log('Export clicked')
  }

  const handleSettingsClick = () => {
    window.location.href = '/settings'
  }

  const getHealthPillColor = () => {
    if (healthStatus.api === 'ok' && healthStatus.db === 'ok') {
      return 'green'
    }
    if (healthStatus.api === 'error' || healthStatus.db === 'error') {
      return 'red'
    }
    return 'amber'
  }

  const getHealthPillText = () => {
    if (healthStatus.api === 'checking' || healthStatus.db === 'checking') {
      return 'Checking...'
    }
    if (healthStatus.api === 'ok' && healthStatus.db === 'ok') {
      const licenseText = healthStatus.licenseDays !== null 
        ? ` · ${healthStatus.licenseDays}d left`
        : ''
      return `All Systems OK${licenseText}`
    }
    return 'System Error'
  }

  return (
    <header className="dashboard-header">
      <div className="dashboard-header-left">
        {/* Venue Switcher */}
        <div className="dashboard-header-dropdown">
          <button
            className="dashboard-header-button"
            onClick={() => setShowVenueDropdown(!showVenueDropdown)}
            aria-label="Select venue"
          >
            <Building2 size={16} />
            <span>{filters.venueId || venues[0]}</span>
            <ChevronDown size={14} />
          </button>
          {showVenueDropdown && (
            <div className="dashboard-header-dropdown-menu">
              {venues.map((venue) => (
                <button
                  key={venue}
                  className="dashboard-header-dropdown-item"
                  onClick={() => {
                    setVenue(venue === 'All Venues' ? null : venue)
                    setShowVenueDropdown(false)
                  }}
                >
                  {venue}
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Date Range Selector */}
        <div className="dashboard-header-dropdown">
          <button
            className="dashboard-header-button"
            onClick={() => setShowDateDropdown(!showDateDropdown)}
            aria-label="Select date range"
          >
            <Calendar size={16} />
            <span>{dateRanges.find((r) => r.value === filters.dateRange)?.label || '30 Days'}</span>
            <ChevronDown size={14} />
          </button>
          {showDateDropdown && (
            <div className="dashboard-header-dropdown-menu">
              {dateRanges.map((range) => (
                <button
                  key={range.value}
                  className="dashboard-header-dropdown-item"
                  onClick={() => {
                    setDateRange(range.value)
                    setShowDateDropdown(false)
                  }}
                >
                  {range.label}
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Global Search */}
        <div className="dashboard-header-search">
          <Search size={16} />
          <input
            type="text"
            placeholder="Search invoices, suppliers, items..."
            value={filters.searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="dashboard-header-search-input"
          />
        </div>
      </div>

      <div className="dashboard-header-right">
        {/* Role Badge */}
        <div className="dashboard-header-role-badge">
          {currentRole}
        </div>

        {/* Health Pill */}
        <div className={`dashboard-header-health-pill dashboard-header-health-pill-${getHealthPillColor()}`}>
          <div className="dashboard-header-health-pill-dot" />
          <span>{getHealthPillText()}</span>
        </div>

        {/* Quick Actions */}
        <button
          className="dashboard-header-action-button"
          onClick={handleUploadClick}
          aria-label="Upload"
          title="Upload documents"
        >
          <Upload size={18} />
        </button>
        <button
          className="dashboard-header-action-button"
          onClick={handleExportClick}
          aria-label="Export"
          title="Export data"
        >
          <Download size={18} />
        </button>
        <button
          className="dashboard-header-action-button"
          onClick={handleSettingsClick}
          aria-label="Settings"
          title="Settings"
        >
          <Settings size={18} />
        </button>
      </div>
    </header>
  )
}

