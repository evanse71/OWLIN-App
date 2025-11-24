import { memo } from 'react'
import './FilterDrawer.css'

interface FilterDrawerProps {
  activeFilters: Set<string>
  onFilterChange: (filters: Set<string>) => void
  onClose: () => void
}

export const FilterDrawer = memo(function FilterDrawer({
  activeFilters,
  onFilterChange,
  onClose,
}: FilterDrawerProps) {
  const filters = [
    { id: 'pending', label: 'Pending', color: 'gray' },
    { id: 'scanned', label: 'Processed', color: 'green' },
    { id: 'submitted', label: 'Matched', color: 'blue' },
    { id: 'error', label: 'Flagged', color: 'red' },
  ]

  const toggleFilter = (filterId: string) => {
    const next = new Set(activeFilters)
    if (next.has(filterId)) {
      next.delete(filterId)
    } else {
      next.add(filterId)
    }
    onFilterChange(next)
  }

  return (
    <div className="filter-drawer">
      <div className="filter-drawer-header">
        <h3 className="filter-drawer-title">Filters</h3>
        <button className="filter-drawer-close" onClick={onClose} aria-label="Close filters">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <line x1="18" y1="6" x2="6" y2="18" />
            <line x1="6" y1="6" x2="18" y2="18" />
          </svg>
        </button>
      </div>
      <div className="filter-drawer-content">
        {filters.map((filter) => (
          <label key={filter.id} className="filter-drawer-item">
            <input
              type="checkbox"
              checked={activeFilters.has(filter.id)}
              onChange={() => toggleFilter(filter.id)}
            />
            <span className={`filter-drawer-label filter-${filter.color}`}>
              {filter.label}
            </span>
          </label>
        ))}
      </div>
    </div>
  )
})

