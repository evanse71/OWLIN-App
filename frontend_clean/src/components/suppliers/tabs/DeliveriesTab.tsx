/**
 * Deliveries Tab Component
 * Delivery reliability and history for supplier
 */

import { useState, useEffect } from 'react'
import { CheckCircle, XCircle, AlertCircle } from 'lucide-react'
import { fetchSupplierDeliveries, type SupplierDelivery } from '../../../lib/suppliersApi'
import type { SupplierDetail } from '../../../lib/suppliersApi'
import './DeliveriesTab.css'

interface DeliveriesTabProps {
  supplier: SupplierDetail
  supplierId: string
  currentRole: 'GM' | 'Finance' | 'ShiftLead'
}

export function DeliveriesTab({ supplier, supplierId, currentRole }: DeliveriesTabProps) {
  const [deliveries, setDeliveries] = useState<SupplierDelivery[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let mounted = true

    async function loadDeliveries() {
      setLoading(true)
      try {
        const data = await fetchSupplierDeliveries(supplierId)
        if (mounted) {
          setDeliveries(data)
        }
      } catch (e) {
        console.error('Failed to load deliveries:', e)
        if (mounted) {
          setDeliveries([])
        }
      } finally {
        if (mounted) {
          setLoading(false)
        }
      }
    }

    loadDeliveries()
    return () => {
      mounted = false
    }
  }, [supplierId])

  const onTimeCount = deliveries.filter((d) => d.onTime).length
  const onTimeRate = deliveries.length > 0 ? (onTimeCount / deliveries.length) * 100 : 0
  const avgDelay = deliveries
    .filter((d) => d.delayHours && d.delayHours > 0)
    .reduce((sum, d) => sum + (d.delayHours || 0), 0) / deliveries.filter((d) => d.delayHours && d.delayHours > 0).length || 0
  const shortDeliveryCount = deliveries.filter((d) => d.missingItems && d.missingItems > 0).length

  // Group deliveries by day of week
  const deliveriesByDay: Record<string, number> = {}
  deliveries.forEach((d) => {
    const day = new Date(d.date).toLocaleDateString('en-GB', { weekday: 'long' })
    deliveriesByDay[day] = (deliveriesByDay[day] || 0) + 1
  })

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'Fully matched':
        return 'green'
      case 'Partially matched':
        return 'amber'
      case 'Unmatched':
        return 'red'
      default:
        return 'gray'
    }
  }

  if (loading) {
    return <div className="deliveries-tab-loading">Loading delivery data...</div>
  }

  return (
    <div className="deliveries-tab">
      {/* Metrics */}
      <div className="deliveries-tab-metrics">
        <div className="deliveries-tab-metric">
          <div className="deliveries-tab-metric-label">On-time Rate</div>
          <div className="deliveries-tab-metric-value">{onTimeRate.toFixed(1)}%</div>
        </div>
        <div className="deliveries-tab-metric">
          <div className="deliveries-tab-metric-label">Average Delay</div>
          <div className="deliveries-tab-metric-value">
            {avgDelay > 0 ? `${avgDelay.toFixed(1)} hours` : 'N/A'}
          </div>
        </div>
        <div className="deliveries-tab-metric">
          <div className="deliveries-tab-metric-label">Short Deliveries</div>
          <div className="deliveries-tab-metric-value">{shortDeliveryCount}</div>
        </div>
      </div>

      {/* Day of Week Calendar */}
      {Object.keys(deliveriesByDay).length > 0 && (
        <div className="deliveries-tab-calendar">
          <div className="deliveries-tab-calendar-title">Delivery Days</div>
          <div className="deliveries-tab-calendar-days">
            {['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'].map(
              (day) => {
                const count = deliveriesByDay[day] || 0
                const deliveriesForDay = deliveries.filter(
                  (d) => new Date(d.date).toLocaleDateString('en-GB', { weekday: 'long' }) === day
                )
                const onTimeForDay = deliveriesForDay.filter((d) => d.onTime).length
                const isActive = count > 0

                return (
                  <div
                    key={day}
                    className={`deliveries-tab-calendar-day ${isActive ? 'active' : ''}`}
                  >
                    <div className="deliveries-tab-calendar-day-name">{day.slice(0, 3)}</div>
                    {isActive && (
                      <>
                        <div className="deliveries-tab-calendar-day-count">{count}</div>
                        <div className="deliveries-tab-calendar-day-status">
                          {onTimeForDay === count ? (
                            <CheckCircle size={12} className="status-on-time" />
                          ) : onTimeForDay > 0 ? (
                            <AlertCircle size={12} className="status-partial" />
                          ) : (
                            <XCircle size={12} className="status-late" />
                          )}
                        </div>
                      </>
                    )}
                  </div>
                )
              }
            )}
          </div>
        </div>
      )}

      {/* Recent Deliveries List */}
      <div className="deliveries-tab-list">
        <div className="deliveries-tab-list-title">Recent Deliveries</div>
        {deliveries.length === 0 ? (
          <div className="deliveries-tab-empty">No delivery data available</div>
        ) : (
          <div className="deliveries-tab-deliveries">
            {deliveries.map((delivery) => {
              const statusColor = getStatusColor(delivery.status)

              return (
                <div key={delivery.id} className="deliveries-tab-delivery">
                  <div className="deliveries-tab-delivery-main">
                    <div className="deliveries-tab-delivery-number">{delivery.deliveryNoteNumber}</div>
                    <div className="deliveries-tab-delivery-date">
                      {new Date(delivery.date).toLocaleDateString('en-GB', {
                        day: 'numeric',
                        month: 'short',
                        year: 'numeric',
                      })}
                    </div>
                  </div>
                  <div className="deliveries-tab-delivery-status">
                    <div className={`deliveries-tab-delivery-status-chip deliveries-tab-delivery-status-${statusColor}`}>
                      {delivery.status}
                    </div>
                    {!delivery.onTime && delivery.delayHours && (
                      <div className="deliveries-tab-delivery-delay">
                        {delivery.delayHours}h delay
                      </div>
                    )}
                    {delivery.missingItems && delivery.missingItems > 0 && (
                      <div className="deliveries-tab-delivery-missing">
                        {delivery.missingItems} items missing
                      </div>
                    )}
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}

