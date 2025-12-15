/**
 * Waste Log List Component
 * Left column component with filters and scrollable waste cards
 */

import type { WasteEntry, WasteFilters } from '../../types/waste'
import { WasteCard } from './WasteCard'
import { WasteFilters as WasteFiltersComponent } from './WasteFilters'
import { EmptyState } from '../invoices/EmptyState'
import './WasteLogList.css'

interface WasteLogListProps {
  wasteEntries: WasteEntry[]
  selectedId: string | null
  onSelect: (id: string) => void
  filters: WasteFilters
  onFilterChange: (filters: WasteFilters) => void
  onRecordWaste: () => void
}

export function WasteLogList({
  wasteEntries,
  selectedId,
  onSelect,
  filters,
  onFilterChange,
  onRecordWaste
}: WasteLogListProps) {
  // Extract unique staff members from entries
  const availableStaff = Array.from(new Set(wasteEntries.map(e => e.staffMember))).sort()
  
  return (
    <div className="waste-log-list">
      <div className="waste-log-list-header">
        <h2 className="waste-log-list-title">Waste Log</h2>
      </div>
      
      <WasteFiltersComponent
        filters={filters}
        onFilterChange={onFilterChange}
        availableStaff={availableStaff}
      />
      
      <div className="waste-log-list-cards">
        {wasteEntries.length === 0 ? (
          <EmptyState
            title="No waste recorded yet"
            description="Start tracking waste to identify cost savings opportunities"
            actionLabel="Record Waste"
            onAction={onRecordWaste}
            icon="🗑️"
          />
        ) : (
          wasteEntries.map(entry => (
            <WasteCard
              key={entry.id}
              entry={entry}
              isSelected={selectedId === entry.id}
              onClick={() => onSelect(entry.id)}
            />
          ))
        )}
      </div>
    </div>
  )
}

