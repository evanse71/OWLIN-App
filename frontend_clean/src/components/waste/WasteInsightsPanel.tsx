/**
 * Waste Insights Panel Component
 * Right column component with 5 stacked cards: Overview, Product Breakdown, Meal Breakdown, Supplier Impact, Margin Impact
 */

import type { WasteEntry, WasteInsights, DateRange } from '../../types/waste'
import { ProductWasteRow } from './ProductWasteRow'
import { MealWasteRow } from './MealWasteRow'
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
import './WasteInsightsPanel.css'

interface WasteInsightsPanelProps {
  selectedWasteEntry: WasteEntry | null
  insights: WasteInsights | null
  dateRange: DateRange
  loading?: boolean
}

export function WasteInsightsPanel({
  selectedWasteEntry,
  insights,
  dateRange,
  loading = false
}: WasteInsightsPanelProps) {
  if (loading || !insights) {
    return (
      <div className="waste-insights-panel">
        <div className="waste-insights-loading">Loading insights...</div>
      </div>
    )
  }
  
  const maxProductCost = insights.productBreakdown.length > 0
    ? Math.max(...insights.productBreakdown.map(p => p.costLost))
    : 0
  
  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('en-GB', {
      style: 'currency',
      currency: 'GBP',
      minimumFractionDigits: 2,
      maximumFractionDigits: 2
    }).format(value)
  }
  
  return (
    <div className="waste-insights-panel">
      {/* A. Waste Overview Card */}
      <div className="waste-insights-card">
        <h3 className="waste-insights-card-title">Waste Overview</h3>
        
        <div className="waste-overview-metrics">
          <div className="waste-metric-tile">
            <div className="waste-metric-label">Waste %</div>
            <div className="waste-metric-value">{insights.wastePercentage.toFixed(1)}%</div>
          </div>
          <div className="waste-metric-tile">
            <div className="waste-metric-label">Cost of waste</div>
            <div className="waste-metric-value">{formatCurrency(insights.totalCostLost)}</div>
          </div>
          <div className="waste-metric-tile">
            <div className="waste-metric-label">Top wasted category</div>
            <div className="waste-metric-value">{insights.topCategory}</div>
          </div>
          <div className="waste-metric-tile">
            <div className="waste-metric-label">Staff attribution</div>
            <div className="waste-metric-value">{insights.staffAttribution}</div>
          </div>
        </div>
        
        <div className="waste-overview-graph">
          <div className="waste-graph-title">Waste Cost Over Time</div>
          <ResponsiveContainer width="100%" height={200}>
            <AreaChart data={insights.trendData}>
              <defs>
                <linearGradient id="wasteColorGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#2B3A55" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#2B3A55" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(0, 0, 0, 0.05)" />
              <XAxis
                dataKey="date"
                stroke="rgba(0, 0, 0, 0.4)"
                tick={{ fill: 'rgba(0, 0, 0, 0.6)', fontSize: 11 }}
                tickFormatter={(value) => {
                  const date = new Date(value)
                  return `${date.getDate()}/${date.getMonth() + 1}`
                }}
              />
              <YAxis
                stroke="rgba(0, 0, 0, 0.4)"
                tick={{ fill: 'rgba(0, 0, 0, 0.6)', fontSize: 11 }}
                tickFormatter={(value) => `£${value.toFixed(0)}`}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: 'white',
                  border: '1px solid rgba(0, 0, 0, 0.1)',
                  borderRadius: '6px',
                  boxShadow: '0 1px 2px rgba(0, 0, 0, 0.04)'
                }}
                formatter={(value: number) => formatCurrency(value)}
              />
              <Area
                type="monotone"
                dataKey="value"
                stroke="#2B3A55"
                fill="url(#wasteColorGradient)"
                strokeWidth={2}
                dot={false}
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>
      
      {/* B. Product Waste Breakdown Card */}
      <div className="waste-insights-card">
        <h3 className="waste-insights-card-title">Products with highest waste</h3>
        {insights.productBreakdown.length === 0 ? (
          <div className="waste-insights-empty">No product waste data available</div>
        ) : (
          <div className="waste-product-breakdown">
            {insights.productBreakdown.map((product, index) => (
              <ProductWasteRow
                key={index}
                product={product}
                maxCostLost={maxProductCost}
              />
            ))}
          </div>
        )}
      </div>
      
      {/* C. Meal Waste Breakdown Card */}
      <div className="waste-insights-card">
        <h3 className="waste-insights-card-title">Meals yielding most waste</h3>
        {insights.mealBreakdown.length === 0 ? (
          <div className="waste-insights-empty">No meal waste data available</div>
        ) : (
          <div className="waste-meal-breakdown">
            {insights.mealBreakdown.map((meal, index) => (
              <MealWasteRow
                key={index}
                meal={meal}
              />
            ))}
          </div>
        )}
      </div>
      
      {/* D. Supplier Impact Card */}
      <div className="waste-insights-card">
        <h3 className="waste-insights-card-title">Supplier quality impact</h3>
        {insights.supplierImpact.length === 0 ? (
          <div className="waste-insights-empty">No supplier impact data available</div>
        ) : (
          <div className="waste-supplier-impact">
            {insights.supplierImpact.map((supplier, index) => (
              <div key={index} className="waste-supplier-row">
                <div className="waste-supplier-row-content">
                  <div className="waste-supplier-name">{supplier.supplierName}</div>
                  <div className="waste-supplier-stats">
                    <span className="waste-supplier-cost">{formatCurrency(supplier.wasteCost)}</span>
                    <span className="waste-supplier-percentage">{supplier.wastePercentage.toFixed(1)}% waste</span>
                  </div>
                </div>
                {supplier.isAboveThreshold && (
                  <div className="waste-supplier-badge-amber">
                    High waste detected
                  </div>
                )}
              </div>
            ))}
            <div className="waste-supplier-notes">
              {insights.supplierImpact.some(s => s.isAboveThreshold) && (
                <div className="waste-supplier-note">
                  High waste detected on {insights.supplierImpact.filter(s => s.isAboveThreshold).map(s => s.supplierName).join(', ')} products
                </div>
              )}
            </div>
          </div>
        )}
      </div>
      
      {/* E. Margin Impact Card */}
      <div className="waste-insights-card">
        <h3 className="waste-insights-card-title">Margin erosion due to waste</h3>
        <div className="waste-margin-impact">
          <div className="waste-margin-row">
            <span className="waste-margin-label">Food cost target:</span>
            <span className="waste-margin-value">{insights.marginImpact.foodCostTarget}%</span>
          </div>
          <div className="waste-margin-row">
            <span className="waste-margin-label">Actual cost with waste:</span>
            <span className="waste-margin-value waste-margin-value-high">{insights.marginImpact.actualCostWithWaste.toFixed(1)}%</span>
          </div>
          <div className="waste-margin-row">
            <span className="waste-margin-label">Lost margin:</span>
            <span className="waste-margin-value waste-margin-value-negative">{insights.marginImpact.lostMargin.toFixed(1)}pp</span>
          </div>
          <div className="waste-margin-row waste-margin-row-highlight">
            <span className="waste-margin-label">Amount needed to return to target:</span>
            <span className="waste-margin-value waste-margin-value-amount">{formatCurrency(insights.marginImpact.amountNeededToReturnToTarget)}</span>
          </div>
        </div>
      </div>
      
      {/* Selected Waste Entry Detail (if any) */}
      {selectedWasteEntry && (
        <div className="waste-insights-card waste-selected-entry-card">
          <h3 className="waste-insights-card-title">Selected Entry</h3>
          <div className="waste-selected-entry-details">
            <div className="waste-selected-entry-row">
              <span className="waste-selected-entry-label">Item:</span>
              <span className="waste-selected-entry-value">{selectedWasteEntry.itemName}</span>
            </div>
            <div className="waste-selected-entry-row">
              <span className="waste-selected-entry-label">Quantity:</span>
              <span className="waste-selected-entry-value">{selectedWasteEntry.quantity} {selectedWasteEntry.unit}</span>
            </div>
            <div className="waste-selected-entry-row">
              <span className="waste-selected-entry-label">Cost Lost:</span>
              <span className="waste-selected-entry-value">{formatCurrency(selectedWasteEntry.costLost)}</span>
            </div>
            <div className="waste-selected-entry-row">
              <span className="waste-selected-entry-label">Reason:</span>
              <span className="waste-selected-entry-value">{selectedWasteEntry.reason}</span>
            </div>
            {selectedWasteEntry.note && (
              <div className="waste-selected-entry-row">
                <span className="waste-selected-entry-label">Note:</span>
                <span className="waste-selected-entry-value">{selectedWasteEntry.note}</span>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

