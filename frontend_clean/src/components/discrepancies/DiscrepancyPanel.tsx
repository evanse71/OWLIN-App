/**
 * DiscrepancyPanel Component
 * Displays a list of discrepancies with actions, grouped by severity level
 * Optimized for handling 100-1000+ invoices with search, filters, and smooth interactions
 */

import { useState, useMemo, useCallback, useEffect, useRef, memo } from 'react'
import { ChevronDown, AlertCircle, Info, CheckCircle2, Search, X } from 'lucide-react'
import type { DiscrepancyItem, DiscrepancyLevel } from '../../lib/discrepanciesApi'
import './DiscrepancyPanel.css'

interface DiscrepancyPanelProps {
  scope: 'invoices' | 'delivery-notes' | 'dashboard' | 'general'
  items: DiscrepancyItem[]
  isLoading?: boolean
  lastUpdated?: string | null
  onItemClick?: (item: DiscrepancyItem) => void
  className?: string
}

const LEVEL_ORDER: DiscrepancyLevel[] = ['critical', 'major', 'minor']
const MAX_ITEMS_PER_GROUP_EXPANDED = 6
const MAX_ITEMS_PER_GROUP_COMPACT = 10

const groupTitleForLevel: Record<DiscrepancyLevel, string> = {
  critical: 'Review these first',
  major: 'Worth a look',
  minor: 'Nice to fix'
}

// Debounce hook
function useDebounce<T>(value: T, delay: number): T {
  const [debouncedValue, setDebouncedValue] = useState<T>(value)

  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedValue(value)
    }, delay)

    return () => {
      clearTimeout(handler)
    }
  }, [value, delay])

  return debouncedValue
}

// Memoized item component for performance
const DiscrepancyItemCard = memo(({
  item,
  isInvoicesScope,
  viewMode,
  onItemClick,
  isSelected,
  isHovered,
}: {
  item: DiscrepancyItem
  isInvoicesScope: boolean
  viewMode: 'compact' | 'expanded'
  onItemClick?: (item: DiscrepancyItem) => void
  isSelected: boolean
  isHovered: boolean
}) => {
  const itemRef = useRef<HTMLDivElement>(null)
  const [showDropdown, setShowDropdown] = useState(false)

  const handleClick = useCallback(() => {
    // Show dropdown
    setShowDropdown(true)
    // Navigate to the relevant section (this will scroll and highlight)
    onItemClick?.(item)
  }, [item, onItemClick])

  // Close dropdown when clicking outside
  useEffect(() => {
    if (!showDropdown) return

    const handleClickOutside = (e: MouseEvent) => {
      if (itemRef.current && !itemRef.current.contains(e.target as Node)) {
        setShowDropdown(false)
      }
    }

    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [showDropdown])

  return (
    <div ref={itemRef} className="discrepancy-item-wrapper">
      <button
        type="button"
        onClick={handleClick}
        className="discrepancy-item-button"
      >
        <div className={`${isInvoicesScope ? 'discrepancy-item' : 'discrepancy-item-card'} ${isHovered ? 'discrepancy-item-hovered' : ''} ${showDropdown ? 'discrepancy-item-selected' : ''}`}>
          <div className="discrepancy-item-left">
            {isInvoicesScope ? (
              <div className="discrepancy-priority-indicator-wrapper">
                <span className={`discrepancy-priority-indicator discrepancy-priority-indicator-${item.level || 'minor'}`}></span>
              </div>
            ) : (
              <div className="discrepancy-item-icon-wrapper">
                {item.level === 'critical' && (
                  <AlertCircle className="discrepancy-icon discrepancy-icon-critical" size={16} strokeWidth={1.7} />
                )}
                {item.level === 'major' && (
                  <Info className="discrepancy-icon discrepancy-icon-major" size={16} strokeWidth={1.7} />
                )}
                {(item.level === 'minor' || !item.level) && (
                  <Info className="discrepancy-icon discrepancy-icon-minor" size={16} strokeWidth={1.4} />
                )}
              </div>
            )}
            <div className="discrepancy-item-text">
              <div className={isInvoicesScope ? 'discrepancy-item-title' : 'discrepancy-item-title-new'}>
                {item.title}
              </div>
              {/* Minimal info only - no description on card */}
            </div>
          </div>
          {item.contextLabel && (
            <span className={isInvoicesScope ? 'discrepancy-context-badge' : 'discrepancy-context-label'}>
              {item.contextLabel}
            </span>
          )}
        </div>
      </button>
      
      {/* Click-triggered dropdown */}
      {showDropdown && (
        <div className="discrepancy-item-dropdown discrepancy-item-dropdown-clicked">
          <div className="discrepancy-item-dropdown-content">
            {item.description && (
              <div className="discrepancy-item-dropdown-section">
                <div className="discrepancy-item-dropdown-label">Details</div>
                <div className="discrepancy-item-dropdown-text">{item.description}</div>
              </div>
            )}
            {item.contextLabel && (
              <div className="discrepancy-item-dropdown-section">
                <div className="discrepancy-item-dropdown-label">Invoice</div>
                <div className="discrepancy-item-dropdown-text">{item.contextLabel}</div>
              </div>
            )}
            {item.actions && item.actions.length > 0 && (
              <div className="discrepancy-item-dropdown-actions">
                {item.actions.map((action, idx) => (
                  <button
                    key={idx}
                    type="button"
                    className="discrepancy-item-dropdown-action"
                    onClick={(e) => {
                      e.stopPropagation()
                      onItemClick?.(item)
                    }}
                  >
                    {action.label || action.actionType}
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
})

DiscrepancyItemCard.displayName = 'DiscrepancyItemCard'

export function DiscrepancyPanel({
  scope,
  items,
  isLoading = false,
  lastUpdated = null,
  onItemClick,
  className,
}: DiscrepancyPanelProps) {
  const isInvoicesScope = scope === 'invoices'
  
  // State management
  const storageKey = `discrepancy-panel-collapsed-${scope}`
  const [isCollapsed, setIsCollapsed] = useState(() => {
    try {
      const saved = localStorage.getItem(storageKey)
      return saved === 'true'
    } catch {
      return false
    }
  })

  const [searchQuery, setSearchQuery] = useState('')
  const [viewMode, setViewMode] = useState<'compact' | 'expanded'>('expanded')
  const [hoveredItemId, setHoveredItemId] = useState<string | null>(null)
  const [showJumpTo, setShowJumpTo] = useState(false)
  const [focusedLevel, setFocusedLevel] = useState<DiscrepancyLevel | null>(null)
  const [selectedItemIndex, setSelectedItemIndex] = useState<number>(-1)
  
  const searchInputRef = useRef<HTMLInputElement>(null)
  const debouncedSearchQuery = useDebounce(searchQuery, 150)

  // Filter items by search query
  const filteredItems = useMemo(() => {
    if (!debouncedSearchQuery.trim()) return items
    
    const query = debouncedSearchQuery.toLowerCase()
    return items.filter(item => 
      item.title.toLowerCase().includes(query) ||
      item.description?.toLowerCase().includes(query) ||
      item.contextLabel?.toLowerCase().includes(query)
    )
  }, [items, debouncedSearchQuery])

  // Group filtered items by level
  const groupedItems = useMemo(() => {
    const groups: Record<DiscrepancyLevel, DiscrepancyItem[]> = {
      critical: [],
      major: [],
      minor: []
    }

    filteredItems.forEach(item => {
      const level = item.level || (item.severity === 'critical' ? 'critical' : item.severity === 'warning' ? 'major' : 'minor')
      if (groups[level]) {
        groups[level].push(item)
      }
    })

    return groups
  }, [filteredItems])

  // Determine overall label and chip styling
  const hasCritical = groupedItems.critical.length > 0
  const hasMajor = groupedItems.major.length > 0
  
  let overallLabel: string | null = null
  if (hasCritical) overallLabel = 'High priority'
  else if (hasMajor) overallLabel = 'Needs attention'
  else if (filteredItems.length > 0) overallLabel = 'All low priority'

  // Auto-enable compact mode for large lists
  useEffect(() => {
    if (isInvoicesScope && items.length > 50 && viewMode === 'expanded') {
      setViewMode('compact')
    }
  }, [items.length, isInvoicesScope, viewMode])

  // Build flat list of all visible items for keyboard navigation
  const allVisibleItems = useMemo(() => {
    const items: DiscrepancyItem[] = []
    LEVEL_ORDER.forEach(level => {
      const group = groupedItems[level]
      if (group) {
        const maxItems = viewMode === 'compact' ? MAX_ITEMS_PER_GROUP_COMPACT : MAX_ITEMS_PER_GROUP_EXPANDED
        items.push(...group.slice(0, maxItems))
      }
    })
    return items
  }, [groupedItems, viewMode])

  // Keyboard navigation
  useEffect(() => {
    if (!isInvoicesScope || isCollapsed) return

    const handleKeyDown = (e: KeyboardEvent) => {
      // Focus search with /
      if (e.key === '/' && !e.ctrlKey && !e.metaKey) {
        const target = e.target as HTMLElement
        if (target.tagName !== 'INPUT' && target.tagName !== 'TEXTAREA') {
          e.preventDefault()
          searchInputRef.current?.focus()
        }
        return
      }

      // Navigate with j/k
      if ((e.key === 'j' || e.key === 'k') && !e.ctrlKey && !e.metaKey) {
        const target = e.target as HTMLElement
        if (target.tagName !== 'INPUT' && target.tagName !== 'TEXTAREA') {
          e.preventDefault()
          
          if (allVisibleItems.length === 0) return

          let newIndex = selectedItemIndex
          if (e.key === 'j') {
            newIndex = selectedItemIndex < 0 ? 0 : Math.min(selectedItemIndex + 1, allVisibleItems.length - 1)
          } else {
            newIndex = selectedItemIndex < 0 ? allVisibleItems.length - 1 : Math.max(selectedItemIndex - 1, 0)
          }
          
          setSelectedItemIndex(newIndex)
          const item = allVisibleItems[newIndex]
          if (item) {
            setHoveredItemId(item.id)
            // Scroll item into view
            setTimeout(() => {
              const element = document.querySelector(`[data-item-id="${item.id}"]`)
              element?.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
            }, 50)
          }
        }
        return
      }

      // Select with Enter
      if (e.key === 'Enter' && selectedItemIndex >= 0) {
        const target = e.target as HTMLElement
        if (target.tagName !== 'INPUT' && target.tagName !== 'TEXTAREA') {
          e.preventDefault()
          const item = allVisibleItems[selectedItemIndex]
          if (item) {
            onItemClick?.(item)
          }
        }
        return
      }

      // Escape to clear selection
      if (e.key === 'Escape') {
        setSelectedItemIndex(-1)
        setHoveredItemId(null)
        searchInputRef.current?.blur()
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [isInvoicesScope, isCollapsed, selectedItemIndex, allVisibleItems, onItemClick])

  const toggleCollapse = () => {
    const newState = !isCollapsed
    setIsCollapsed(newState)
    try {
      localStorage.setItem(storageKey, String(newState))
    } catch {
      // Ignore localStorage errors
    }
  }

  const scrollToLevel = (level: DiscrepancyLevel) => {
    const element = document.querySelector(`[data-level="${level}"]`)
    if (element) {
      element.scrollIntoView({ behavior: 'smooth', block: 'start' })
      setFocusedLevel(level)
      setTimeout(() => setFocusedLevel(null), 2000)
    }
    setShowJumpTo(false)
  }

  // Close jump-to menu when clicking outside
  useEffect(() => {
    if (!showJumpTo) return

    const handleClickOutside = (e: MouseEvent) => {
      const target = e.target as HTMLElement
      if (!target.closest('.discrepancy-jump-to-container')) {
        setShowJumpTo(false)
      }
    }

    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [showJumpTo])

  const MAX_ITEMS = viewMode === 'compact' ? MAX_ITEMS_PER_GROUP_COMPACT : MAX_ITEMS_PER_GROUP_EXPANDED

  const renderGroup = (level: DiscrepancyLevel, groupItems: DiscrepancyItem[]) => {
    if (groupItems.length === 0) return null

    const visibleItems = groupItems.slice(0, MAX_ITEMS)
    const remainingCount = groupItems.length - MAX_ITEMS

    return (
      <div 
        key={level} 
        data-level={level}
        className={`${isInvoicesScope ? 'discrepancy-group-invoices' : 'discrepancy-group-new'} ${focusedLevel === level ? 'discrepancy-group-focused' : ''}`}
      >
        <h3 className={isInvoicesScope ? 'discrepancy-section-title' : 'discrepancy-group-title-new'}>
          {groupTitleForLevel[level]} ({groupItems.length})
        </h3>
        <div className={isInvoicesScope ? 'discrepancy-group-items-invoices' : 'discrepancy-group-items-new'}>
          {visibleItems.map((item, idx) => {
            // Calculate global index for keyboard navigation
            const globalIndex = allVisibleItems.findIndex(i => i.id === item.id)
            
            return (
              <div key={item.id} data-item-id={item.id}>
                <DiscrepancyItemCard
                  item={item}
                  isInvoicesScope={isInvoicesScope}
                  viewMode={viewMode}
                  onItemClick={onItemClick}
                  isSelected={selectedItemIndex === globalIndex}
                  isHovered={hoveredItemId === item.id || selectedItemIndex === globalIndex}
                />
              </div>
            )
          })}
          {remainingCount > 0 && (
            <button
              type="button"
              onClick={() => {
                // Expand to show all items in this group
                console.log(`Show all ${remainingCount} more ${level} issues`)
                if (groupItems[MAX_ITEMS]) {
                  onItemClick?.(groupItems[MAX_ITEMS])
                }
              }}
              className="discrepancy-item-button"
            >
              <div className={isInvoicesScope ? 'discrepancy-item-more-invoices' : 'discrepancy-item-more-new'}>
                <span>
                  + {remainingCount} more item{remainingCount !== 1 ? 's' : ''} — scroll to view
                </span>
              </div>
            </button>
          )}
        </div>
      </div>
    )
  }

  const footerText = scope === 'dashboard' 
    ? 'Issues for this dashboard period.'
    : scope === 'invoices'
    ? 'Issues for invoices in this view.'
    : 'Issues in this view.'

  const showSearch = isInvoicesScope && items.length > 10
  const showCompactToggle = isInvoicesScope && items.length > 20
  const showJumpToMenu = isInvoicesScope && !isCollapsed && (groupedItems.critical.length > 0 || groupedItems.major.length > 0 || groupedItems.minor.length > 0)
  const displayCount = debouncedSearchQuery ? filteredItems.length : items.length

  const containerClass = isInvoicesScope ? 'discrepancy-panel' : 'discrepancy-panel-container'
  const headerClass = isInvoicesScope ? 'discrepancy-panel-header-invoices' : 'discrepancy-panel-header-new'
  const titleClass = isInvoicesScope ? 'discrepancy-panel-title-invoices' : 'discrepancy-panel-title'
  const sublineClass = isInvoicesScope ? 'discrepancy-panel-subline-invoices' : 'discrepancy-panel-subline'
  const chipClass = isInvoicesScope 
    ? `discrepancy-priority-chip ${hasCritical ? 'discrepancy-priority-critical' : hasMajor ? 'discrepancy-priority-major' : ''}`
    : `discrepancy-chip-new ${hasCritical ? 'discrepancy-chip-critical-new' : hasMajor ? 'discrepancy-chip-major-new' : 'discrepancy-chip-minor-new'}`

  if (isLoading) {
    return (
      <div className={`${containerClass} ${className || ''}`}>
        <div className={headerClass}>
          <div>
            <h2 className={titleClass}>Discrepancies</h2>
          </div>
        </div>
        <div className="discrepancy-panel-content-new">
          <div className="discrepancy-loading">Loading discrepancies...</div>
        </div>
      </div>
    )
  }

  if (items.length === 0) {
    return (
      <div className={`${containerClass} ${className || ''}`}>
        <div className={headerClass}>
          <div>
            <h2 className={titleClass}>Discrepancies (0)</h2>
            <p className={sublineClass}>
              Owlin hasn't found anything that needs your attention.
            </p>
          </div>
        </div>
        <div className="discrepancy-empty-state">
          <CheckCircle2 className="discrepancy-empty-icon" size={16} strokeWidth={1.7} />
          <div>
            <div className="discrepancy-empty-title">All clear for now</div>
            <div className="discrepancy-empty-description">
              Owlin didn't find any issues in this view.
            </div>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className={`${containerClass} ${className || ''}`}>
      <div className={headerClass}>
        <div className="discrepancy-panel-header-left">
          <div>
            <h2 className={titleClass}>
              Discrepancies ({debouncedSearchQuery ? `${displayCount} of ${items.length}` : displayCount})
            </h2>
            <p className={sublineClass}>
              {items.length === 0
                ? "Owlin hasn't found anything that needs your attention."
                : "Owlin found a few things to review."}
            </p>
          </div>
          
          {/* Search bar */}
          {showSearch && !isCollapsed && (
            <div className="discrepancy-search-container">
              <Search className="discrepancy-search-icon" size={14} />
              <input
                ref={searchInputRef}
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search issues..."
                className="discrepancy-search-input"
              />
              {searchQuery && (
                <button
                  type="button"
                  onClick={() => setSearchQuery('')}
                  className="discrepancy-search-clear"
                  aria-label="Clear search"
                >
                  <X size={12} />
                </button>
              )}
            </div>
          )}
        </div>

        <div className="discrepancy-panel-header-right-new">
          {/* Jump to menu */}
          {showJumpToMenu && (
            <div className="discrepancy-jump-to-container">
              <button
                type="button"
                onClick={() => setShowJumpTo(!showJumpTo)}
                className="discrepancy-jump-to-button"
                aria-label="Jump to section"
              >
                Jump to
                <ChevronDown size={12} className={showJumpTo ? 'discrepancy-jump-to-chevron-open' : ''} />
              </button>
              {showJumpTo && (
                <div className="discrepancy-jump-to-menu">
                  {groupedItems.critical.length > 0 && (
                    <button
                      type="button"
                      className="discrepancy-jump-to-item"
                      onClick={() => scrollToLevel('critical')}
                    >
                      <span className="discrepancy-priority-dot discrepancy-priority-dot-critical"></span>
                      Review these first ({groupedItems.critical.length})
                    </button>
                  )}
                  {groupedItems.major.length > 0 && (
                    <button
                      type="button"
                      className="discrepancy-jump-to-item"
                      onClick={() => scrollToLevel('major')}
                    >
                      <span className="discrepancy-priority-dot discrepancy-priority-dot-major"></span>
                      Worth a look ({groupedItems.major.length})
                    </button>
                  )}
                  {groupedItems.minor.length > 0 && (
                    <button
                      type="button"
                      className="discrepancy-jump-to-item"
                      onClick={() => scrollToLevel('minor')}
                    >
                      <span className="discrepancy-priority-dot discrepancy-priority-dot-minor"></span>
                      Nice to fix ({groupedItems.minor.length})
                    </button>
                  )}
                </div>
              )}
            </div>
          )}

          {/* Compact/Expanded toggle */}
          {showCompactToggle && !isCollapsed && (
            <button
              type="button"
              onClick={() => setViewMode(viewMode === 'compact' ? 'expanded' : 'compact')}
              className="discrepancy-view-toggle"
              aria-label={`Switch to ${viewMode === 'compact' ? 'expanded' : 'compact'} view`}
              title={viewMode === 'compact' ? 'Switch to expanded view' : 'Switch to compact view'}
            >
              {viewMode === 'compact' ? 'Expand' : 'Compact'}
            </button>
          )}

          {overallLabel && (
            <span className={chipClass}>
              {isInvoicesScope && (
                <span className={`discrepancy-priority-dot ${
                  hasCritical ? 'discrepancy-priority-dot-critical' : 
                  hasMajor ? 'discrepancy-priority-dot-major' : 
                  'discrepancy-priority-dot-minor'
                }`}></span>
              )}
              {overallLabel}
            </span>
          )}

          <button
            type="button"
            onClick={toggleCollapse}
            aria-label={isCollapsed ? 'Expand discrepancies' : 'Collapse discrepancies'}
            className="discrepancy-collapse-button"
          >
            <ChevronDown
              className={`discrepancy-chevron-icon ${isCollapsed ? 'discrepancy-chevron-collapsed' : ''}`}
              size={14}
            />
          </button>
        </div>
      </div>

      {!isCollapsed && (
        <div className="discrepancy-panel-content-new">
          {filteredItems.length === 0 && searchQuery ? (
            <div className="discrepancy-empty-state">
              <div className="discrepancy-empty-title">No matches found</div>
              <div className="discrepancy-empty-description">
                Try a different search term.
              </div>
            </div>
          ) : (
            <div className="discrepancy-panel-body-new">
              {LEVEL_ORDER.map(level => renderGroup(level, groupedItems[level]))}
            </div>
          )}
          <div className="discrepancy-panel-footer-new">
            <p>{footerText}</p>
            {isInvoicesScope && items.length > 10 && (
              <p className="discrepancy-keyboard-hint">
                Press <kbd>/</kbd> to search, <kbd>j</kbd>/<kbd>k</kbd> to navigate
              </p>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
