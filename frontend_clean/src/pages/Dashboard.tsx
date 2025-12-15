/**
 * Dashboard Page
 * Main control surface for Owlin - answers "Where am I today?", "What needs my attention?", "What's changing?"
 */

import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { DashboardFiltersProvider, useDashboardFilters } from '../contexts/DashboardFiltersContext'
import { AppHeader } from '../components/layout/AppHeader'
import { DashboardHeader } from '../components/dashboard/DashboardHeader'
import { MetricTile } from '../components/dashboard/MetricTile'
import { ActionQueue } from '../components/dashboard/ActionQueue'
import { SupplierRiskBoard } from '../components/dashboard/SupplierRiskBoard'
import { TrendsGraph } from '../components/dashboard/TrendsGraph'
import { UnmatchedDNStrip } from '../components/dashboard/UnmatchedDNStrip'
import { ActivityTicker } from '../components/dashboard/ActivityTicker'
import { NotificationStack } from '../components/dashboard/NotificationStack'
import { DiscrepancyPanel } from '../components/discrepancies/DiscrepancyPanel'
import { fetchDiscrepancies, type DiscrepancyItem } from '../lib/discrepanciesApi'
import './Dashboard.css'

// Mock role - in real app this would come from auth context
const currentRole: 'GM' | 'Finance' | 'ShiftLead' = 'GM'

function DashboardContent() {
  const { filters } = useDashboardFilters()
  const navigate = useNavigate()
  const containerRef = useRef<HTMLDivElement>(null)
  const [scrollPosition, setScrollPosition] = useState(0)
  const [expandedTiles, setExpandedTiles] = useState<Set<string>>(new Set())
  const [discrepancies, setDiscrepancies] = useState<DiscrepancyItem[]>([])
  const [discrepanciesLoading, setDiscrepanciesLoading] = useState(false)
  const [discrepanciesLastUpdated, setDiscrepanciesLastUpdated] = useState<string | null>(null)

  // Restore scroll position and expanded tiles from localStorage
  useEffect(() => {
    try {
      const savedScroll = localStorage.getItem('dashboardScrollPosition')
      const savedExpanded = localStorage.getItem('dashboardExpandedTiles')
      if (savedScroll) {
        setScrollPosition(Number(savedScroll))
      }
      if (savedExpanded) {
        setExpandedTiles(new Set(JSON.parse(savedExpanded)))
      }
    } catch (e) {
      console.warn('Failed to restore dashboard state', e)
    }
  }, [])

  // Save scroll position
  useEffect(() => {
    const handleScroll = () => {
      if (containerRef.current) {
        const scroll = containerRef.current.scrollTop
        setScrollPosition(scroll)
        try {
          localStorage.setItem('dashboardScrollPosition', scroll.toString())
        } catch (e) {
          // Ignore localStorage errors
        }
      }
    }

    const container = containerRef.current
    if (container) {
      container.addEventListener('scroll', handleScroll)
      // Restore scroll position
      container.scrollTop = scrollPosition
      return () => container.removeEventListener('scroll', handleScroll)
    }
  }, [scrollPosition])

  // Save expanded tiles
  useEffect(() => {
    try {
      localStorage.setItem('dashboardExpandedTiles', JSON.stringify(Array.from(expandedTiles)))
    } catch (e) {
      // Ignore localStorage errors
    }
  }, [expandedTiles])

  // Fetch discrepancies
  useEffect(() => {
    let mounted = true
    async function loadDiscrepancies() {
      setDiscrepanciesLoading(true)
      try {
        const response = await fetchDiscrepancies('dashboard')
        if (mounted) {
          // If API returns empty, add some mock data for testing
          let items = response.items
          if (items.length === 0) {
            items = [
              {
                id: 'dashboard-critical-1',
                type: 'critical_issues',
                severity: 'critical' as const,
                level: 'critical' as const,
                title: 'Several invoices are ready to submit but have unresolved issues',
                description: 'Review and resolve issues before submitting these invoices.',
                contextRef: { type: 'system' },
                createdAt: new Date().toISOString()
              },
              {
                id: 'dashboard-major-1',
                type: 'match_rate_low',
                severity: 'warning' as const,
                level: 'major' as const,
                title: 'Match rate is low this month – many invoices not linked to delivery notes',
                description: 'Link delivery notes to improve match rate and accuracy.',
                contextRef: { type: 'system' },
                createdAt: new Date().toISOString()
              }
            ]
          }
          setDiscrepancies(items)
          setDiscrepanciesLastUpdated(response.lastUpdated)
        }
      } catch (error) {
        console.error('Failed to load discrepancies:', error)
        if (mounted) {
          // Add mock data on error for testing
          setDiscrepancies([
            {
              id: 'dashboard-critical-1',
              type: 'critical_issues',
              severity: 'critical' as const,
              level: 'critical' as const,
              title: 'Several invoices are ready to submit but have unresolved issues',
              description: 'Review and resolve issues before submitting these invoices.',
              contextRef: { type: 'system' },
              createdAt: new Date().toISOString()
            },
            {
              id: 'dashboard-major-1',
              type: 'match_rate_low',
              severity: 'warning' as const,
              level: 'major' as const,
              title: 'Match rate is low this month – many invoices not linked to delivery notes',
              description: 'Link delivery notes to improve match rate and accuracy.',
              contextRef: { type: 'system' },
              createdAt: new Date().toISOString()
            }
          ])
        }
      } finally {
        if (mounted) {
          setDiscrepanciesLoading(false)
        }
      }
    }
    loadDiscrepancies()
    return () => {
      mounted = false
    }
  }, [filters.venueId, filters.dateRange])

  // Handle discrepancy item click
  const handleDiscrepancyClick = (item: DiscrepancyItem) => {
    // If item refers to invoices, navigate to /invoices with appropriate query params
    if (item.contextRef?.type === 'invoice' && item.contextRef.id) {
      navigate(`/invoices?invoice=${item.contextRef.id}`)
    } else if (item.contextRef?.type === 'system' || item.contextRef?.type === 'venue') {
      // Determine filter based on item type
      let filterParam = ''
      if (item.type === 'unpaired_invoices' || item.type === 'match_rate_low') {
        filterParam = '?filter=missing_dn'
      } else if (item.type === 'flagged_invoices' || item.type === 'critical_issues') {
        filterParam = '?filter=flagged'
      }
      navigate(`/invoices${filterParam}`)
    } else if (item.actions && item.actions.length > 0) {
      const action = item.actions[0]
      if (action.actionType === 'navigate' && action.target) {
        console.log('Navigating to:', action.target)
        navigate(action.target)
      } else if (action.actionType === 'filter' && action.target) {
        // Navigate to invoices with filter
        navigate(`/invoices?filter=${action.target}`)
      } else {
        console.log('Discrepancy action:', action)
      }
    }
  }

  return (
    <div className="dashboard-container" ref={containerRef}>
      <AppHeader>
        <DashboardHeader currentRole={currentRole} />
      </AppHeader>
      
      <div className="dashboard-grid">
        {/* Primary Status Row - Four Metric Tiles */}
        <div className="dashboard-metrics-row">
          <MetricTile
            id="open-issues"
            title="Open Issues"
            type="issues"
            expanded={expandedTiles.has('open-issues')}
            onToggle={() => {
              setExpandedTiles((prev) => {
                const next = new Set(prev)
                if (next.has('open-issues')) {
                  next.delete('open-issues')
                } else {
                  next.add('open-issues')
                }
                return next
              })
            }}
          />
          <MetricTile
            id="match-rate"
            title="Match Rate"
            type="matchRate"
            expanded={expandedTiles.has('match-rate')}
            onToggle={() => {
              setExpandedTiles((prev) => {
                const next = new Set(prev)
                if (next.has('match-rate')) {
                  next.delete('match-rate')
                } else {
                  next.add('match-rate')
                }
                return next
              })
            }}
          />
          <MetricTile
            id="spend"
            title="Spend"
            type="spend"
            expanded={expandedTiles.has('spend')}
            onToggle={() => {
              setExpandedTiles((prev) => {
                const next = new Set(prev)
                if (next.has('spend')) {
                  next.delete('spend')
                } else {
                  next.add('spend')
                }
                return next
              })
            }}
          />
          <MetricTile
            id="price-volatility"
            title="Price Volatility"
            type="volatility"
            expanded={expandedTiles.has('price-volatility')}
            onToggle={() => {
              setExpandedTiles((prev) => {
                const next = new Set(prev)
                if (next.has('price-volatility')) {
                  next.delete('price-volatility')
                } else {
                  next.add('price-volatility')
                }
                return next
              })
            }}
          />
        </div>

        {/* Main Content Area */}
        <div className="dashboard-main-content">
          {/* Left Column - Action Queue */}
          <div className="dashboard-left-column">
            <ActionQueue currentRole={currentRole} />
          </div>

          {/* Right Column - Discrepancy Panel and Supplier Risk Board */}
          <div className="dashboard-right-column">
            <DiscrepancyPanel
              scope="dashboard"
              items={discrepancies}
              isLoading={discrepanciesLoading}
              lastUpdated={discrepanciesLastUpdated}
              onItemClick={handleDiscrepancyClick}
            />
            <SupplierRiskBoard currentRole={currentRole} />
          </div>
        </div>

        {/* Full Width - Trends & Forecasts */}
        <div className="dashboard-trends-section">
          <TrendsGraph />
        </div>

        {/* Full Width - Unmatched Delivery Notes */}
        <div className="dashboard-unmatched-section">
          <UnmatchedDNStrip />
        </div>

        {/* Full Width - Recent Activity */}
        <div className="dashboard-activity-section">
          <ActivityTicker />
        </div>
      </div>

      {/* Notifications Stack */}
      <NotificationStack />
    </div>
  )
}

export function Dashboard() {
  return (
    <DashboardFiltersProvider>
      <DashboardContent />
    </DashboardFiltersProvider>
  )
}

