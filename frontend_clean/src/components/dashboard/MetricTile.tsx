/**
 * Metric Tile Component
 * Compact view with sparklines, expandable in-place with context and actions
 */

import { useEffect, useState } from 'react'
import { TrendingUp, TrendingDown, AlertTriangle, CheckCircle2, DollarSign, BarChart3 } from 'lucide-react'
import { useDashboardFilters } from '../../contexts/DashboardFiltersContext'
import { fetchMetrics } from '../../lib/dashboardApi'
import './MetricTile.css'

interface MetricTileProps {
  id: string
  title: string
  type: 'issues' | 'matchRate' | 'spend' | 'volatility'
  expanded: boolean
  onToggle: () => void
}

export function MetricTile({ id, title, type, expanded, onToggle }: MetricTileProps) {
  const { filters } = useDashboardFilters()
  const [data, setData] = useState<any>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let mounted = true

    async function loadData() {
      setLoading(true)
      try {
        const metrics = await fetchMetrics(filters.venueId || undefined, filters.dateRange)
        if (mounted) {
          // Map metrics to tile data based on type
          let tileData: any = {}
          switch (type) {
            case 'issues':
              tileData = {
                value: metrics.openIssues?.count || 0,
                delta: metrics.openIssues?.delta || 0,
                sparkline: [],
                severity: metrics.openIssues?.severity || { high: 0, medium: 0, low: 0 },
              }
              break
            case 'matchRate':
              tileData = {
                value: metrics.matchRate?.value || 0,
                delta: metrics.matchRate?.delta || 0,
                sparkline: metrics.matchRate?.sparkline || [],
              }
              break
            case 'spend':
              tileData = {
                value: metrics.spend?.total || 0,
                delta: metrics.spend?.delta || 0,
                sparkline: metrics.spend?.sparkline || [],
              }
              break
            case 'volatility':
              tileData = {
                value: metrics.priceVolatility?.itemsAboveThreshold || 0,
                delta: metrics.priceVolatility?.delta || 0,
                sparkline: metrics.priceVolatility?.sparkline || [],
              }
              break
          }
          setData(tileData)
        }
      } catch (e) {
        console.error(`Failed to load ${type} metric:`, e)
        if (mounted) {
          setData({ value: 0, delta: 0, sparkline: [] })
        }
      } finally {
        if (mounted) {
          setLoading(false)
        }
      }
    }

    loadData()
    return () => {
      mounted = false
    }
  }, [type, filters.venueId, filters.dateRange])

  const formatValue = () => {
    if (loading || !data) return '...'
    if (type === 'spend') {
      return new Intl.NumberFormat('en-GB', {
        style: 'currency',
        currency: 'GBP',
        maximumFractionDigits: 0,
      }).format(data.value)
    }
    if (type === 'matchRate') {
      return `${Math.round(data.value)}%`
    }
    return data.value.toLocaleString()
  }

  const getIcon = () => {
    switch (type) {
      case 'issues':
        return <AlertTriangle size={20} />
      case 'matchRate':
        return <CheckCircle2 size={20} />
      case 'spend':
        return <DollarSign size={20} />
      case 'volatility':
        return <BarChart3 size={20} />
    }
  }

  const getDeltaColor = () => {
    if (!data || data.delta === 0) return 'neutral'
    if (type === 'issues' || type === 'volatility') {
      return data.delta > 0 ? 'negative' : 'positive'
    }
    return data.delta > 0 ? 'positive' : 'negative'
  }

  const renderSparkline = () => {
    if (!data || !data.sparkline || data.sparkline.length === 0) {
      return <div className="metric-tile-sparkline-empty">No data</div>
    }

    const max = Math.max(...data.sparkline)
    const min = Math.min(...data.sparkline)
    const range = max - min || 1

    return (
      <svg className="metric-tile-sparkline" viewBox={`0 0 ${data.sparkline.length * 4} 20`}>
        <polyline
          points={data.sparkline
            .map((v: number, i: number) => `${i * 4},${20 - ((v - min) / range) * 18}`)
            .join(' ')}
          fill="none"
          stroke="currentColor"
          strokeWidth="1.5"
        />
      </svg>
    )
  }

  return (
    <div
      className={`metric-tile ${expanded ? 'metric-tile-expanded' : ''}`}
      onClick={onToggle}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault()
          onToggle()
        }
      }}
    >
      <div className="metric-tile-header">
        <div className="metric-tile-icon">{getIcon()}</div>
        <div className="metric-tile-content">
          <div className="metric-tile-title">{title}</div>
          <div className="metric-tile-value">{formatValue()}</div>
        </div>
        {data && data.delta !== 0 && (
          <div className={`metric-tile-delta metric-tile-delta-${getDeltaColor()}`}>
            {data.delta > 0 ? <TrendingUp size={14} /> : <TrendingDown size={14} />}
            <span>{Math.abs(data.delta).toFixed(1)}%</span>
          </div>
        )}
      </div>

      {expanded && (
        <div className="metric-tile-expanded-content">
          <div className="metric-tile-sparkline-container">
            {renderSparkline()}
          </div>
          {type === 'issues' && data?.severity && (
            <div className="metric-tile-severity-breakdown">
              <div className="metric-tile-severity-item">
                <span className="metric-tile-severity-dot metric-tile-severity-high" />
                High: {data.severity.high}
              </div>
              <div className="metric-tile-severity-item">
                <span className="metric-tile-severity-dot metric-tile-severity-medium" />
                Medium: {data.severity.medium}
              </div>
              <div className="metric-tile-severity-item">
                <span className="metric-tile-severity-dot metric-tile-severity-low" />
                Low: {data.severity.low}
              </div>
            </div>
          )}
          <div className="metric-tile-actions">
            <button className="metric-tile-action-button">View Details</button>
            <button className="metric-tile-action-button">Filter</button>
          </div>
        </div>
      )}
    </div>
  )
}

