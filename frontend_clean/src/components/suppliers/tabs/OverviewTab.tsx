/**
 * Overview Tab Component
 * Supplier overview with score dial, breakdown chips, timeline, and actions
 */

import { useState } from 'react'
import { Eye, Ban, Calendar, FileText, Download, ScrollText } from 'lucide-react'
import { updateSupplierStatus } from '../../../lib/suppliersApi'
import type { SupplierDetail } from '../../../lib/suppliersApi'
import './OverviewTab.css'

interface OverviewTabProps {
  supplier: SupplierDetail
  supplierId: string
  currentRole: 'GM' | 'Finance' | 'ShiftLead'
}

export function OverviewTab({ supplier, supplierId, currentRole }: OverviewTabProps) {
  const [updatingStatus, setUpdatingStatus] = useState(false)

  const calculateScore = () => {
    const scoreValues: Record<string, number> = { A: 5, B: 4, C: 3, D: 2, E: 1 }
    return (scoreValues[supplier.score] || 3) * 20 // Convert to 0-100 scale
  }

  const score = calculateScore()

  const handleStatusChange = async (status: 'Active' | 'On Watch' | 'Blocked') => {
    setUpdatingStatus(true)
    try {
      await updateSupplierStatus(supplierId, status)
      // In a real app, we'd refresh the supplier data here
      window.location.reload() // Temporary - should use state update instead
    } catch (e) {
      console.error('Failed to update status:', e)
    } finally {
      setUpdatingStatus(false)
    }
  }

  const getScoreColor = (scoreValue: number) => {
    if (scoreValue >= 80) return 'green'
    if (scoreValue >= 60) return 'blue'
    if (scoreValue >= 40) return 'amber'
    if (scoreValue >= 20) return 'orange'
    return 'red'
  }

  const scoreColor = getScoreColor(score)

  return (
    <div className="overview-tab">
      {/* Score Dial */}
      <div className="overview-score-section">
        <div className="overview-score-dial">
          <svg width="120" height="120" className="overview-score-svg">
            <circle
              cx="60"
              cy="60"
              r="50"
              fill="none"
              stroke="rgba(255, 255, 255, 0.1)"
              strokeWidth="8"
            />
            <circle
              cx="60"
              cy="60"
              r="50"
              fill="none"
              stroke={`var(--accent-${scoreColor})`}
              strokeWidth="8"
              strokeDasharray={`${(score / 100) * 314} 314`}
              strokeLinecap="round"
              transform="rotate(-90 60 60)"
              className="overview-score-progress"
            />
          </svg>
          <div className="overview-score-value">
            <div className="overview-score-number">{score}</div>
            <div className={`overview-score-grade overview-score-grade-${scoreColor}`}>
              {supplier.score}
            </div>
          </div>
        </div>
        <div className="overview-score-label">
          <div className="overview-score-status">Score: {score} – Stable</div>
        </div>
      </div>

      {/* Breakdown Chips */}
      <div className="overview-breakdown">
        <div className="overview-breakdown-chip">
          <div className="overview-breakdown-label">Accuracy</div>
          <div className="overview-breakdown-value">{supplier.accuracy.toFixed(1)}%</div>
        </div>
        <div className="overview-breakdown-chip">
          <div className="overview-breakdown-label">Reliability</div>
          <div className="overview-breakdown-value">{supplier.reliability.toFixed(1)}%</div>
        </div>
        <div className="overview-breakdown-chip">
          <div className="overview-breakdown-label">Price Behaviour</div>
          <div className="overview-breakdown-value">
            {supplier.priceBehaviour === 'stable' ? '✓ Stable' :
             supplier.priceBehaviour === 'rising' ? '↑ Rising' : '⚠ Volatile'}
          </div>
        </div>
        <div className="overview-breakdown-chip">
          <div className="overview-breakdown-label">Disputes</div>
          <div className="overview-breakdown-value">
            {supplier.disputeHistory.totalEscalations} escalations
          </div>
        </div>
      </div>

      {/* Timeline */}
      {supplier.timeline && supplier.timeline.length > 0 && (
        <div className="overview-timeline">
          <div className="overview-timeline-title">Timeline</div>
          <div className="overview-timeline-strip">
            {supplier.timeline.map((event, idx) => (
              <div key={idx} className="overview-timeline-event">
                <div className={`overview-timeline-dot overview-timeline-dot-${event.type}`} />
                <div className="overview-timeline-content">
                  <div className="overview-timeline-date">
                    {new Date(event.date).toLocaleDateString('en-GB', {
                      day: 'numeric',
                      month: 'short',
                    })}
                  </div>
                  <div className="overview-timeline-text">{event.event}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Role-specific Actions */}
      <div className="overview-actions">
        {currentRole === 'GM' && (
          <>
            <button
              className="overview-action-button"
              onClick={() => handleStatusChange('On Watch')}
              disabled={updatingStatus || supplier.status === 'On Watch'}
            >
              <Eye size={16} />
              Mark as On Watch
            </button>
            <button
              className="overview-action-button"
              onClick={() => handleStatusChange('Blocked')}
              disabled={updatingStatus || supplier.status === 'Blocked'}
            >
              <Ban size={16} />
              Block new orders
            </button>
            <button className="overview-action-button">
              <Calendar size={16} />
              Request review meeting
            </button>
          </>
        )}
        {currentRole === 'Finance' && (
          <>
            <button className="overview-action-button">
              <Download size={16} />
              Export supplier report
            </button>
            <button className="overview-action-button">
              <ScrollText size={16} />
              View contract terms
            </button>
          </>
        )}
        {currentRole === 'ShiftLead' && (
          <button className="overview-action-button">
            <FileText size={16} />
            View delivery expectations
          </button>
        )}
      </div>
    </div>
  )
}

