import { memo } from 'react'
import './QuickFilters.css'

export interface QuickFilter {
  id: string
  label: string
  icon?: string
  active: boolean
  count?: number
}

interface QuickFiltersProps {
  filters: QuickFilter[]
  onToggle: (id: string) => void
}

export const QuickFilters = memo(function QuickFilters({
  filters,
  onToggle,
}: QuickFiltersProps) {
  return (
    <div className="quick-filters">
      {filters.map((filter) => (
        <button
          key={filter.id}
          className={`quick-filter ${filter.active ? 'active' : ''}`}
          onClick={() => onToggle(filter.id)}
          aria-pressed={filter.active}
        >
          {filter.icon && <span className="quick-filter-icon">{filter.icon}</span>}
          <span className="quick-filter-label">{filter.label}</span>
          {filter.count !== undefined && filter.count > 0 && (
            <span className="quick-filter-badge">{filter.count}</span>
          )}
        </button>
      ))}
    </div>
  )
})

