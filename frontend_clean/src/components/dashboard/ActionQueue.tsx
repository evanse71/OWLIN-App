/**
 * Action Queue Component
 * Stacked list of actionable items with status badges and animations
 */

import { useEffect, useState, useRef } from 'react'
import { useDashboardFilters } from '../../contexts/DashboardFiltersContext'
import { fetchActions, type ActionItem } from '../../lib/dashboardApi'
import { ActionTile } from './ActionTile'
import { EmptyState } from './EmptyState'
import './ActionQueue.css'

interface ActionQueueProps {
  currentRole: 'GM' | 'Finance' | 'ShiftLead'
}

export function ActionQueue({ currentRole }: ActionQueueProps) {
  const { filters } = useDashboardFilters()
  const [actions, setActions] = useState<ActionItem[]>([])
  const [loading, setLoading] = useState(true)
  const [completedIds, setCompletedIds] = useState<Set<string>>(new Set())
  const containerRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    let mounted = true

    async function loadActions() {
      setLoading(true)
      try {
        const fetchedActions = await fetchActions(
          filters.venueId || undefined,
          currentRole
        )
        if (mounted) {
          // Filter out completed actions
          setActions(fetchedActions.filter((a) => !completedIds.has(a.id)))
        }
      } catch (e) {
        console.error('Failed to load actions:', e)
        if (mounted) {
          setActions([])
        }
      } finally {
        if (mounted) {
          setLoading(false)
        }
      }
    }

    loadActions()
    const interval = setInterval(loadActions, 30000) // Refresh every 30 seconds

    return () => {
      mounted = false
      clearInterval(interval)
    }
  }, [filters.venueId, currentRole, completedIds])

  const handleComplete = (id: string) => {
    setCompletedIds((prev) => new Set(prev).add(id))
    // Remove from list with fade animation
    setTimeout(() => {
      setActions((prev) => prev.filter((a) => a.id !== id))
      // Auto-scroll to next action
      if (containerRef.current && actions.length > 1) {
        const nextAction = containerRef.current.querySelector('.action-tile')
        if (nextAction) {
          nextAction.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
        }
      }
    }, 300)
  }

  const visibleActions = actions.filter((a) => a.status !== 'done')

  if (loading) {
    return (
      <div className="action-queue">
        <h2 className="action-queue-title">Action Queue</h2>
        <div className="action-queue-loading">Loading...</div>
      </div>
    )
  }

  if (visibleActions.length === 0) {
    return (
      <div className="action-queue">
        <h2 className="action-queue-title">Action Queue</h2>
        <EmptyState
          title="All Clear"
          message="No actions require your attention right now."
          icon="check"
        />
      </div>
    )
  }

  return (
    <div className="action-queue" ref={containerRef}>
      <h2 className="action-queue-title">Action Queue</h2>
      <div className="action-queue-list">
        {visibleActions.map((action, index) => (
          <ActionTile
            key={action.id}
            action={action}
            onComplete={handleComplete}
            currentRole={currentRole}
          />
        ))}
      </div>
    </div>
  )
}

