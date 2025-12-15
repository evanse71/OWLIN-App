/**
 * Unmatched Delivery Notes Strip Component
 * Horizontal pills representing unmatched DNs with color coding by age
 */

import { useEffect, useState } from 'react'
import { Package, Clock } from 'lucide-react'
import { useDashboardFilters } from '../../contexts/DashboardFiltersContext'
import { fetchUnmatchedDNs, type UnmatchedDN } from '../../lib/dashboardApi'
import { pairDeliveryNote } from '../../lib/dashboardApi'
import { addNotification } from './NotificationStack'
import './UnmatchedDNStrip.css'

export function UnmatchedDNStrip() {
  const { filters } = useDashboardFilters()
  const [dns, setDns] = useState<UnmatchedDN[]>([])
  const [loading, setLoading] = useState(true)
  const [hoveredId, setHoveredId] = useState<string | null>(null)

  useEffect(() => {
    let mounted = true

    async function loadDNs() {
      setLoading(true)
      try {
        const fetchedDNs = await fetchUnmatchedDNs(filters.venueId || undefined)
        if (mounted) {
          // Sort by age (oldest first)
          const sorted = [...fetchedDNs].sort((a, b) => b.age - a.age)
          setDns(sorted)
        }
      } catch (e) {
        console.error('Failed to load unmatched DNs:', e)
        if (mounted) {
          setDns([])
        }
      } finally {
        if (mounted) {
          setLoading(false)
        }
      }
    }

    loadDNs()
    const interval = setInterval(loadDNs, 30000) // Refresh every 30 seconds

    return () => {
      mounted = false
      clearInterval(interval)
    }
  }, [filters.venueId])

  const getAgeColor = (age: number) => {
    if (age <= 1) return 'green'
    if (age <= 3) return 'amber'
    if (age <= 7) return 'amber'
    return 'red'
  }

  const handlePair = async (dn: UnmatchedDN) => {
    if (!dn.suggestedInvoice) {
      addNotification({
        type: 'error',
        message: 'No suggested invoice available for this delivery note',
      })
      return
    }

    try {
      await pairDeliveryNote(dn.id, dn.suggestedInvoice.id)
      addNotification({
        type: 'success',
        message: `Paired ${dn.deliveryNoteNumber} with invoice`,
      })
      // Refresh list
      const fetchedDNs = await fetchUnmatchedDNs(filters.venueId || undefined)
      setDns(fetchedDNs.sort((a, b) => b.age - a.age))
    } catch (e) {
      addNotification({
        type: 'error',
        message: `Failed to pair delivery note: ${e instanceof Error ? e.message : 'Unknown error'}`,
      })
    }
  }

  if (loading) {
    return (
      <div className="unmatched-dn-strip">
        <div className="unmatched-dn-strip-loading">Loading...</div>
      </div>
    )
  }

  if (dns.length === 0) {
    return null
  }

  return (
    <div className="unmatched-dn-strip">
      <h3 className="unmatched-dn-strip-title">Unmatched Delivery Notes</h3>
      <div className="unmatched-dn-strip-pills">
        {dns.map((dn) => (
          <div
            key={dn.id}
            className={`unmatched-dn-pill unmatched-dn-pill-${getAgeColor(dn.age)}`}
            onMouseEnter={() => setHoveredId(dn.id)}
            onMouseLeave={() => setHoveredId(null)}
          >
            <Package size={14} />
            <span className="unmatched-dn-pill-number">{dn.deliveryNoteNumber}</span>
            <span className="unmatched-dn-pill-supplier">{dn.supplier}</span>
            <span className="unmatched-dn-pill-age">{dn.age}d</span>
            {dn.suggestedInvoice && (
              <button
                className="unmatched-dn-pill-pair-button"
                onClick={() => handlePair(dn)}
                title={`Pair with invoice (${Math.round(dn.suggestedInvoice.confidence * 100)}% confidence)`}
              >
                Pair ({Math.round(dn.suggestedInvoice.confidence * 100)}%)
              </button>
            )}
            {hoveredId === dn.id && dn.suggestedInvoice && (
              <div className="unmatched-dn-pill-preview">
                Suggested Invoice: {dn.suggestedInvoice.id} ({Math.round(dn.suggestedInvoice.confidence * 100)}% match)
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}

