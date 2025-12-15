/**
 * Waste Filters Component
 * Filter controls for category, reason, staff, and search
 */

import type { WasteFilters as WasteFiltersType, WasteItemType, WasteReason } from '../../types/waste'
import './WasteFilters.css'

interface WasteFiltersProps {
  filters: WasteFiltersType
  onFilterChange: (filters: WasteFiltersType) => void
  availableStaff: string[]
}

export function WasteFilters({ filters, onFilterChange, availableStaff }: WasteFiltersProps) {
  const categories: Array<{ value: WasteItemType | 'all'; label: string }> = [
    { value: 'all', label: 'All' },
    { value: 'meal', label: 'Meals' },
    { value: 'prep', label: 'Prep' },
    { value: 'ingredient', label: 'Ingredients' }
  ]
  
  const reasons: Array<{ value: WasteReason | 'all'; label: string }> = [
    { value: 'all', label: 'All Reasons' },
    { value: 'spoilage', label: 'Spoilage' },
    { value: 'overcooked', label: 'Overcooked' },
    { value: 'customer-return', label: 'Customer return' },
    { value: 'over-portion', label: 'Over-portion' },
    { value: 'prep-error', label: 'Prep error' },
    { value: 'storage-issue', label: 'Storage issue' },
    { value: 'delivery-quality', label: 'Delivery quality' }
  ]
  
  const handleCategoryChange = (category: WasteItemType | 'all') => {
    onFilterChange({ ...filters, category })
  }
  
  const handleReasonChange = (reason: WasteReason | 'all') => {
    onFilterChange({ ...filters, reason })
  }
  
  const handleStaffChange = (staffMember: string | 'all') => {
    onFilterChange({ ...filters, staffMember })
  }
  
  const handleSearchChange = (searchQuery: string) => {
    onFilterChange({ ...filters, searchQuery: searchQuery || undefined })
  }
  
  return (
    <div className="waste-filters">
      <div className="waste-filters-section">
        <div className="waste-filters-label">Category</div>
        <div className="waste-filters-pills">
          {categories.map(cat => (
            <button
              key={cat.value}
              className={`waste-filter-pill ${filters.category === cat.value || (!filters.category && cat.value === 'all') ? 'waste-filter-pill-active' : ''}`}
              onClick={() => handleCategoryChange(cat.value)}
            >
              {cat.label}
            </button>
          ))}
        </div>
      </div>
      
      <div className="waste-filters-section">
        <div className="waste-filters-label">Reason</div>
        <select
          className="waste-filter-select"
          value={filters.reason || 'all'}
          onChange={(e) => handleReasonChange(e.target.value as WasteReason | 'all')}
        >
          {reasons.map(reason => (
            <option key={reason.value} value={reason.value}>
              {reason.label}
            </option>
          ))}
        </select>
      </div>
      
      <div className="waste-filters-section">
        <div className="waste-filters-label">Staff</div>
        <select
          className="waste-filter-select"
          value={filters.staffMember || 'all'}
          onChange={(e) => handleStaffChange(e.target.value)}
        >
          <option value="all">All Staff</option>
          {availableStaff.map(staff => (
            <option key={staff} value={staff}>
              {staff}
            </option>
          ))}
        </select>
      </div>
      
      <div className="waste-filters-section">
        <div className="waste-filters-label">Search</div>
        <input
          type="text"
          className="waste-filter-search"
          placeholder="Search items, venues..."
          value={filters.searchQuery || ''}
          onChange={(e) => handleSearchChange(e.target.value)}
        />
      </div>
    </div>
  )
}

