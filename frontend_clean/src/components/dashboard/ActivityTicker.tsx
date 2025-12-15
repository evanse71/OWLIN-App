/**
 * Activity Ticker Component
 * Subtle activity ticker with audit log display and export
 */

import { useEffect, useState } from 'react'
import { Clock, Download, ChevronDown, ChevronUp } from 'lucide-react'
import { useDashboardFilters } from '../../contexts/DashboardFiltersContext'
import { fetchActivity, type ActivityItem } from '../../lib/dashboardApi'
import './ActivityTicker.css'

export function ActivityTicker() {
  const { filters } = useDashboardFilters()
  const [activities, setActivities] = useState<ActivityItem[]>([])
  const [loading, setLoading] = useState(true)
  const [expanded, setExpanded] = useState(false)

  useEffect(() => {
    let mounted = true

    async function loadActivity() {
      setLoading(true)
      try {
        const fetchedActivities = await fetchActivity(filters.venueId || undefined, 20)
        if (mounted) {
          setActivities(fetchedActivities)
        }
      } catch (e) {
        console.error('Failed to load activity:', e)
        if (mounted) {
          setActivities([])
        }
      } finally {
        if (mounted) {
          setLoading(false)
        }
      }
    }

    loadActivity()
    const interval = setInterval(loadActivity, 60000) // Refresh every minute

    return () => {
      mounted = false
      clearInterval(interval)
    }
  }, [filters.venueId])

  const formatTime = (timestamp: string) => {
    const date = new Date(timestamp)
    const now = new Date()
    const diffMs = now.getTime() - date.getTime()
    const diffMins = Math.floor(diffMs / 60000)

    if (diffMins < 1) return 'Just now'
    if (diffMins < 60) return `${diffMins}m ago`
    const diffHours = Math.floor(diffMins / 60)
    if (diffHours < 24) return `${diffHours}h ago`
    return date.toLocaleDateString()
  }

  const handleExport = () => {
    const csv = [
      ['Timestamp', 'Actor', 'Action', 'Detail'].join(','),
      ...activities.map((a) =>
        [
          a.timestamp,
          a.actor,
          a.action,
          a.detail || '',
        ].map((v) => `"${v.replace(/"/g, '""')}"`).join(',')
      ),
    ].join('\n')

    const blob = new Blob([csv], { type: 'text/csv' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `audit_log_${new Date().toISOString().split('T')[0]}.csv`
    a.click()
    URL.revokeObjectURL(url)
  }

  if (loading) {
    return (
      <div className="activity-ticker">
        <div className="activity-ticker-loading">Loading...</div>
      </div>
    )
  }

  const recentActivities = activities.slice(0, 3)

  return (
    <div className="activity-ticker">
      <div className="activity-ticker-header">
        <div className="activity-ticker-title">
          <Clock size={16} />
          <span>Recent Activity</span>
        </div>
        <div className="activity-ticker-actions">
          {expanded && (
            <button className="activity-ticker-action-button" onClick={handleExport} title="Export CSV">
              <Download size={14} />
            </button>
          )}
          <button
            className="activity-ticker-action-button"
            onClick={() => setExpanded(!expanded)}
            title={expanded ? 'Collapse' : 'Expand'}
          >
            {expanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
          </button>
        </div>
      </div>

      <div className="activity-ticker-content">
        {!expanded ? (
          <div className="activity-ticker-preview">
            {recentActivities.map((activity, index) => (
              <div key={activity.id} className="activity-ticker-item">
                <span className="activity-ticker-actor">{activity.actor}</span>
                <span className="activity-ticker-action">{activity.action}</span>
                <span className="activity-ticker-time">{formatTime(activity.timestamp)}</span>
              </div>
            ))}
            {activities.length === 0 && (
              <div className="activity-ticker-empty">No recent activity</div>
            )}
          </div>
        ) : (
          <div className="activity-ticker-expanded">
            {activities.map((activity) => (
              <div key={activity.id} className="activity-ticker-item-full">
                <div className="activity-ticker-item-header">
                  <span className="activity-ticker-actor">{activity.actor}</span>
                  <span className="activity-ticker-time-full">{new Date(activity.timestamp).toLocaleString()}</span>
                </div>
                <div className="activity-ticker-action-full">{activity.action}</div>
                {activity.detail && (
                  <div className="activity-ticker-detail">{activity.detail}</div>
                )}
              </div>
            ))}
            {activities.length === 0 && (
              <div className="activity-ticker-empty">No activity found</div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

