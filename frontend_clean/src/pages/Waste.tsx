/**
 * Waste Page Component
 * 
 * ACTIVE FRONTEND: frontend_clean (served on port 5176)
 * Routing: React Router in App.tsx - route registered at /waste
 * 
 * This page provides waste tracking functionality with:
 * - Left column (4/12): Waste Log list with filters
 * - Right column (8/12): Insights panel with metrics and breakdowns
 * - Record Waste modal for logging new entries
 */

import { useState } from 'react'
import { AppHeader } from '../components/layout/AppHeader'
import { WasteLogList } from '../components/waste/WasteLogList'
import { WasteInsightsPanel } from '../components/waste/WasteInsightsPanel'
import { RecordWasteModal } from '../components/waste/RecordWasteModal'
import { NotificationStack } from '../components/dashboard/NotificationStack'
import type { WasteFilters, DateRange } from '../types/waste'
import { useWasteLog, useWasteInsights } from '../hooks/useWaste'
import './Waste.css'

export function Waste() {
  const [venue, setVenue] = useState<string>('Waterloo')
  const [dateRange, setDateRange] = useState<DateRange>('30d')
  const [searchQuery, setSearchQuery] = useState('')
  const [filters, setFilters] = useState<WasteFilters>({})
  const [selectedWasteId, setSelectedWasteId] = useState<string | null>(null)
  const [showRecordModal, setShowRecordModal] = useState(false)
  
  // Combine search query with filters
  const combinedFilters: WasteFilters = {
    ...filters,
    searchQuery: searchQuery || undefined
  }
  
  const { data: wasteEntries, loading: loadingEntries } = useWasteLog(combinedFilters, dateRange)
  const { data: insights, loading: loadingInsights } = useWasteInsights(dateRange, venue)
  
  const selectedWasteEntry = wasteEntries.find(e => e.id === selectedWasteId) || null
  
  const venues = ['All Venues', 'Waterloo', 'Royal Oak Hotel', 'Main Restaurant']
  
  const dateRanges: Array<{ value: DateRange; label: string }> = [
    { value: '7d', label: '7 Days' },
    { value: '30d', label: '30 Days' },
    { value: '90d', label: '90 Days' },
    { value: 'custom', label: 'Custom' }
  ]
  
  const handleRecordSuccess = () => {
    // Refresh data will happen automatically via hooks
    setShowRecordModal(false)
  }
  
  return (
    <div className="waste-page">
      <AppHeader>
        <div className="waste-page-header">
          <div className="waste-page-header-content">
            <h1 className="waste-page-title">Waste Log</h1>
            <p className="waste-page-subtitle">Track waste, cost and margin loss across all venues</p>
          </div>
          
          <div className="waste-page-controls">
            <select
              className="waste-page-control-select"
              value={venue}
              onChange={(e) => setVenue(e.target.value)}
            >
              {venues.map(v => (
                <option key={v} value={v}>{v}</option>
              ))}
            </select>
            
            <select
              className="waste-page-control-select"
              value={dateRange}
              onChange={(e) => setDateRange(e.target.value as DateRange)}
            >
              {dateRanges.map(range => (
                <option key={range.value} value={range.value}>{range.label}</option>
              ))}
            </select>
            
            <input
              type="text"
              className="waste-page-control-search"
              placeholder="Search waste entries..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
            
            <button
              className="waste-page-record-button"
              onClick={() => setShowRecordModal(true)}
            >
              Record Waste
            </button>
          </div>
        </div>
      </AppHeader>
      
      <div className="waste-page-content">
        <div className="waste-page-grid">
          {/* Left Column: Waste Log List (4 columns) */}
          <div className="waste-page-left-column">
            <WasteLogList
              wasteEntries={wasteEntries}
              selectedId={selectedWasteId}
              onSelect={setSelectedWasteId}
              filters={filters}
              onFilterChange={setFilters}
              onRecordWaste={() => setShowRecordModal(true)}
            />
          </div>
          
          {/* Right Column: Insights Panel (8 columns) */}
          <div className="waste-page-right-column">
            <WasteInsightsPanel
              selectedWasteEntry={selectedWasteEntry}
              insights={insights}
              dateRange={dateRange}
              loading={loadingInsights}
            />
          </div>
        </div>
      </div>
      
      {/* Record Waste Modal */}
      <RecordWasteModal
        isOpen={showRecordModal}
        onClose={() => setShowRecordModal(false)}
        onSuccess={handleRecordSuccess}
        venue={venue === 'All Venues' ? 'Waterloo' : venue}
      />
      
      {/* Notification Stack */}
      <NotificationStack />
    </div>
  )
}

