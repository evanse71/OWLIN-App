/**
 * Supplier Risk Board Component
 * Grid of supplier widgets with scorecards
 */

import { useEffect, useState } from 'react'
import { useDashboardFilters } from '../../contexts/DashboardFiltersContext'
import { fetchSuppliers, type SupplierRisk } from '../../lib/dashboardApi'
import { SupplierWidget } from './SupplierWidget'
import { EmptyState } from './EmptyState'
import { Overlay } from './Overlay'
import './SupplierRiskBoard.css'

interface SupplierRiskBoardProps {
  currentRole: 'GM' | 'Finance' | 'ShiftLead'
}

export function SupplierRiskBoard({ currentRole }: SupplierRiskBoardProps) {
  const { filters } = useDashboardFilters()
  const [suppliers, setSuppliers] = useState<SupplierRisk[]>([])
  const [loading, setLoading] = useState(true)
  const [selectedSupplier, setSelectedSupplier] = useState<SupplierRisk | null>(null)

  useEffect(() => {
    let mounted = true

    async function loadSuppliers() {
      setLoading(true)
      try {
        const fetchedSuppliers = await fetchSuppliers(
          filters.venueId || undefined,
          filters.dateRange
        )
        if (mounted) {
          // Sort by score (A first) then by total spend (descending)
          const sorted = [...fetchedSuppliers].sort((a, b) => {
            const scoreOrder = { A: 0, B: 1, C: 2, D: 3, E: 4 }
            const scoreDiff = (scoreOrder[a.score as keyof typeof scoreOrder] || 5) - 
                             (scoreOrder[b.score as keyof typeof scoreOrder] || 5)
            if (scoreDiff !== 0) return scoreDiff
            return b.totalSpend - a.totalSpend
          })
          setSuppliers(sorted)
        }
      } catch (e) {
        console.error('Failed to load suppliers:', e)
        if (mounted) {
          setSuppliers([])
        }
      } finally {
        if (mounted) {
          setLoading(false)
        }
      }
    }

    loadSuppliers()
    return () => {
      mounted = false
    }
  }, [filters.venueId, filters.dateRange])

  if (loading) {
    return (
      <div className="supplier-risk-board">
        <h2 className="supplier-risk-board-title">Supplier Risk Board</h2>
        <div className="supplier-risk-board-loading">Loading...</div>
      </div>
    )
  }

  if (suppliers.length === 0) {
    return (
      <div className="supplier-risk-board">
        <h2 className="supplier-risk-board-title">Supplier Risk Board</h2>
        <EmptyState
          title="No Suppliers"
          message="No supplier data available for the selected period."
          icon="info"
        />
      </div>
    )
  }

  return (
    <>
      <div className="supplier-risk-board">
        <h2 className="supplier-risk-board-title">Supplier Risk Board</h2>
        <div className="supplier-risk-board-grid">
          {suppliers.map((supplier) => (
            <SupplierWidget
              key={supplier.id}
              supplier={supplier}
              onClick={setSelectedSupplier}
              currentRole={currentRole}
            />
          ))}
        </div>
      </div>

      {selectedSupplier && (
        <Overlay
          supplier={selectedSupplier}
          currentRole={currentRole}
          onClose={() => setSelectedSupplier(null)}
        />
      )}
    </>
  )
}

