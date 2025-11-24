import { memo } from 'react'
import './FilterChips.css'

export interface FilterChip {
  id: string
  label: string
  count?: number
  active: boolean
  color?: 'primary' | 'success' | 'warning' | 'error' | 'neutral'
}

interface FilterChipsProps {
  chips: FilterChip[]
  onToggle: (id: string) => void
  onClear?: () => void
}

export const FilterChips = memo(function FilterChips({
  chips,
  onToggle,
  onClear,
}: FilterChipsProps) {
  const activeCount = chips.filter((c) => c.active).length

  return (
    <div className="filter-chips-container">
      <div className="filter-chips-list">
        {chips.map((chip) => (
          <button
            key={chip.id}
            className={`filter-chip ${chip.active ? 'active' : ''} ${chip.color || 'neutral'}`}
            onClick={() => onToggle(chip.id)}
            aria-pressed={chip.active}
          >
            <span className="filter-chip-label">{chip.label}</span>
            {chip.count !== undefined && chip.count > 0 && (
              <span className="filter-chip-count">{chip.count}</span>
            )}
          </button>
        ))}
      </div>
      {activeCount > 0 && onClear && (
        <button className="filter-chips-clear" onClick={onClear}>
          Clear all ({activeCount})
        </button>
      )}
    </div>
  )
})

