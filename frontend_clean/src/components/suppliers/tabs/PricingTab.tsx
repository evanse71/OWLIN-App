/**
 * Pricing Tab Component
 * Price trends and analysis for supplier items
 */

import { useState, useEffect } from 'react'
import {
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  LineChart,
  Area,
  AreaChart,
} from 'recharts'
import { TrendingUp, AlertTriangle, Search } from 'lucide-react'
import { fetchSupplierPricing, type SupplierPricingData } from '../../../lib/suppliersApi'
import type { SupplierDetail } from '../../../lib/suppliersApi'
import './PricingTab.css'

interface PricingTabProps {
  supplier: SupplierDetail
  supplierId: string
  currentRole: 'GM' | 'Finance' | 'ShiftLead'
}

export function PricingTab({ supplier, supplierId, currentRole }: PricingTabProps) {
  const [pricingData, setPricingData] = useState<SupplierPricingData[]>([])
  const [selectedItemId, setSelectedItemId] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [searchQuery, setSearchQuery] = useState('')

  useEffect(() => {
    let mounted = true

    async function loadPricing() {
      setLoading(true)
      try {
        const data = await fetchSupplierPricing(supplierId, selectedItemId || undefined)
        if (mounted) {
          setPricingData(data)
          if (!selectedItemId && data.length > 0) {
            setSelectedItemId(data[0].itemId)
          }
        }
      } catch (e) {
        console.error('Failed to load pricing:', e)
        if (mounted) {
          setPricingData([])
        }
      } finally {
        if (mounted) {
          setLoading(false)
        }
      }
    }

    loadPricing()
    return () => {
      mounted = false
    }
  }, [supplierId, selectedItemId])

  const selectedItem = pricingData.find((item) => item.itemId === selectedItemId)
  const filteredItems = pricingData.filter((item) =>
    item.itemName.toLowerCase().includes(searchQuery.toLowerCase())
  )

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('en-GB', {
      style: 'currency',
      currency: 'GBP',
      maximumFractionDigits: 2,
    }).format(value)
  }

  const chartData = selectedItem
    ? selectedItem.prices.map((p) => ({
        date: new Date(p.date).toLocaleDateString('en-GB', { day: 'numeric', month: 'short' }),
        price: p.price,
        forecast: p.forecast,
        confidence: p.confidence,
      }))
    : []

  if (loading) {
    return <div className="pricing-tab-loading">Loading pricing data...</div>
  }

  return (
    <div className="pricing-tab">
      {/* Item Selector */}
      <div className="pricing-tab-selector">
        <div className="pricing-tab-search">
          <Search size={16} />
          <input
            type="text"
            placeholder="Search items..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pricing-tab-search-input"
          />
        </div>
        <select
          value={selectedItemId || ''}
          onChange={(e) => setSelectedItemId(e.target.value || null)}
          className="pricing-tab-select"
        >
          {filteredItems.map((item) => (
            <option key={item.itemId} value={item.itemId}>
              {item.itemName}
            </option>
          ))}
        </select>
      </div>

      {selectedItem && (
        <>
          {/* Price Change Indicator */}
          {selectedItem.recentChange && (
            <div className="pricing-tab-change">
              <TrendingUp size={16} />
              <span>
                {selectedItem.recentChange.percentage > 0 ? '+' : ''}
                {selectedItem.recentChange.percentage.toFixed(1)}% vs{' '}
                {selectedItem.recentChange.period}
              </span>
            </div>
          )}

          {/* Volatility Flags */}
          {selectedItem.volatilityFlags && selectedItem.volatilityFlags.length > 0 && (
            <div className="pricing-tab-flags">
              {selectedItem.volatilityFlags.map((flag, idx) => (
                <div key={idx} className="pricing-tab-flag">
                  <AlertTriangle size={14} />
                  <span>
                    {new Date(flag.date).toLocaleDateString('en-GB')}: {flag.change.toFixed(1)}% -{' '}
                    {flag.reason}
                  </span>
                </div>
              ))}
            </div>
          )}

          {/* Price Graph */}
          {chartData.length > 0 && (
            <div className="pricing-tab-chart">
              <ResponsiveContainer width="100%" height={300}>
                <AreaChart data={chartData}>
                  <defs>
                    <linearGradient id="colorPrice" x1="0" y1="0" x2="0" y2="1">
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
                    tickFormatter={(value) => formatCurrency(value)}
                  />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: 'rgba(42, 42, 42, 0.95)',
                      border: '1px solid rgba(255, 255, 255, 0.1)',
                      borderRadius: '6px',
                      color: 'rgba(255, 255, 255, 0.87)',
                    }}
                    formatter={(value: number) => formatCurrency(value)}
                  />
                  <Area
                    type="monotone"
                    dataKey="price"
                    stroke="rgba(59, 130, 246, 1)"
                    fill="url(#colorPrice)"
                    strokeWidth={2}
                    dot={false}
                  />
                  <Line
                    type="monotone"
                    dataKey="forecast"
                    stroke="rgba(251, 191, 36, 1)"
                    strokeWidth={2}
                    strokeDasharray="5 5"
                    dot={false}
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          )}

          {/* Average Price */}
          {selectedItem.averagePrice && (
            <div className="pricing-tab-average">
              <div className="pricing-tab-average-label">Average Price</div>
              <div className="pricing-tab-average-value">
                {formatCurrency(selectedItem.averagePrice)}
              </div>
            </div>
          )}

          {/* Actions */}
          {currentRole !== 'ShiftLead' && (
            <div className="pricing-tab-actions">
              <button className="pricing-tab-action-button">
                Compare with other suppliers
              </button>
              <button className="pricing-tab-action-button">
                Mark price as under review
              </button>
            </div>
          )}
        </>
      )}
    </div>
  )
}

