/**
 * Trends Graph Component
 * UniversalTrendGraph using recharts with tabs, filters, forecast bands, and tooltips
 */

import { useState, useEffect } from 'react'
import {
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Area,
  AreaChart,
} from 'recharts'
import { TrendingUp, DollarSign, AlertTriangle, CheckCircle2 } from 'lucide-react'
import { useDashboardFilters } from '../../contexts/DashboardFiltersContext'
import { fetchTrends, type TrendType, type TrendData } from '../../lib/dashboardApi'
import './TrendsGraph.css'

const TREND_TYPES: { value: TrendType; label: string; icon: any }[] = [
  { value: 'spend', label: 'Spend', icon: DollarSign },
  { value: 'price', label: 'Price', icon: TrendingUp },
  { value: 'issues', label: 'Issues', icon: AlertTriangle },
  { value: 'matchRate', label: 'Match Rate', icon: CheckCircle2 },
]

const DATE_RANGES = [
  { value: '7d', label: '1W' },
  { value: '30d', label: '1M' },
  { value: '180d', label: '6M' },
  { value: '365d', label: '1Y' },
]

export function TrendsGraph() {
  const { filters } = useDashboardFilters()
  const [selectedType, setSelectedType] = useState<TrendType>('spend')
  const [selectedRange, setSelectedRange] = useState('30d')
  const [data, setData] = useState<TrendData | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let mounted = true

    async function loadTrendData() {
      setLoading(true)
      try {
        // Map frontend date range to backend format
        const backendDateRange = selectedRange === '7d' ? '7d' : selectedRange === '30d' ? '30d' : selectedRange === '180d' ? '180d' : '365d'
        const trendData = await fetchTrends(
          selectedType,
          filters.venueId || undefined,
          backendDateRange,
          {
            supplier: filters.searchQuery || undefined,
          }
        )
        if (mounted) {
          setData(trendData)
        }
      } catch (e) {
        console.error('Failed to load trend data:', e)
        if (mounted) {
          setData({ data: [], forecast: [], unit: '' })
        }
      } finally {
        if (mounted) {
          setLoading(false)
        }
      }
    }

    loadTrendData()
    return () => {
      mounted = false
    }
  }, [selectedType, selectedRange, filters.venueId, filters.searchQuery])

  const formatValue = (value: number) => {
    if (selectedType === 'spend') {
      return new Intl.NumberFormat('en-GB', {
        style: 'currency',
        currency: 'GBP',
        maximumFractionDigits: 0,
      }).format(value)
    }
    if (selectedType === 'matchRate') {
      return `${value.toFixed(1)}%`
    }
    return value.toLocaleString()
  }

  // Prepare chart data - combine actual and forecast
  const chartData = data && data.data && data.data.length > 0
    ? [
        ...data.data.map((d) => ({
          date: d.date,
          value: d.value,
          forecast: undefined,
        })),
        ...(data.forecast || []).map((d) => ({
          date: d.date,
          value: undefined,
          forecast: d.forecast,
        })),
      ]
    : []

  if (loading) {
    return (
      <div className="trends-graph">
        <div className="trends-graph-loading">Loading trend data...</div>
      </div>
    )
  }

  if (!data || !data.data || data.data.length === 0) {
    return (
      <div className="trends-graph">
        <div className="trends-graph-loading">No trend data available</div>
      </div>
    )
  }

  return (
    <div className="trends-graph">
      <div className="trends-graph-header">
        <div className="trends-graph-tabs">
          {TREND_TYPES.map((type) => {
            const Icon = type.icon
            return (
              <button
                key={type.value}
                className={`trends-graph-tab ${selectedType === type.value ? 'trends-graph-tab-active' : ''}`}
                onClick={() => setSelectedType(type.value)}
              >
                <Icon size={16} />
                <span>{type.label}</span>
              </button>
            )
          })}
        </div>
        <div className="trends-graph-range-toggles">
          {DATE_RANGES.map((range) => (
            <button
              key={range.value}
              className={`trends-graph-range-toggle ${selectedRange === range.value ? 'trends-graph-range-toggle-active' : ''}`}
              onClick={() => setSelectedRange(range.value)}
            >
              {range.label}
            </button>
          ))}
        </div>
      </div>

      <div className="trends-graph-chart-container">
        {chartData.length > 0 ? (
          <ResponsiveContainer width="100%" height={300}>
            <AreaChart data={chartData}>
            <defs>
              <linearGradient id="colorActual" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="rgba(59, 130, 246, 0.3)" stopOpacity={0.3} />
                <stop offset="95%" stopColor="rgba(59, 130, 246, 0.3)" stopOpacity={0} />
              </linearGradient>
              <linearGradient id="colorForecast" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="rgba(251, 191, 36, 0.2)" stopOpacity={0.2} />
                <stop offset="95%" stopColor="rgba(251, 191, 36, 0.2)" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255, 255, 255, 0.1)" />
            <XAxis
              dataKey="date"
              stroke="rgba(255, 255, 255, 0.5)"
              tick={{ fill: 'rgba(255, 255, 255, 0.6)', fontSize: 12 }}
            />
            <YAxis
              stroke="rgba(255, 255, 255, 0.5)"
              tick={{ fill: 'rgba(255, 255, 255, 0.6)', fontSize: 12 }}
              tickFormatter={formatValue}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: 'rgba(42, 42, 42, 0.95)',
                border: '1px solid rgba(255, 255, 255, 0.1)',
                borderRadius: '6px',
                color: 'rgba(255, 255, 255, 0.87)',
              }}
              formatter={(value: number) => formatValue(value)}
            />
            <Area
              type="monotone"
              dataKey="value"
              stroke="rgba(59, 130, 246, 1)"
              fill="url(#colorActual)"
              strokeWidth={2}
              dot={false}
              connectNulls={false}
            />
            <Line
              type="monotone"
              dataKey="forecast"
              stroke="rgba(251, 191, 36, 1)"
              strokeWidth={2}
              strokeDasharray="5 5"
              dot={false}
              connectNulls={false}
            />
          </AreaChart>
        </ResponsiveContainer>
        ) : (
          <div className="trends-graph-loading">No data to display</div>
        )}
      </div>
    </div>
  )
}

