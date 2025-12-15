/**
 * Waste Card Component
 * Individual waste entry card with click handling and badge styling
 */

import type { WasteEntry, WasteReason } from '../../types/waste'
import './WasteCard.css'

interface WasteCardProps {
  entry: WasteEntry
  isSelected: boolean
  onClick: () => void
}

const reasonLabels: Record<WasteReason, string> = {
  'spoilage': 'Spoilage',
  'overcooked': 'Overcooked',
  'customer-return': 'Customer return',
  'over-portion': 'Over-portion',
  'prep-error': 'Prep error',
  'storage-issue': 'Storage issue',
  'delivery-quality': 'Delivery quality'
}

const reasonBadgeClass: Record<WasteReason, string> = {
  'spoilage': 'badge-spoilage',
  'overcooked': 'badge-overcooked',
  'customer-return': 'badge-customer-return',
  'over-portion': 'badge-over-portion',
  'prep-error': 'badge-prep-error',
  'storage-issue': 'badge-storage-issue',
  'delivery-quality': 'badge-delivery-quality'
}

export function WasteCard({ entry, isSelected, onClick }: WasteCardProps) {
  const formatTimestamp = (timestamp: string) => {
    const date = new Date(timestamp)
    const day = date.getDate()
    const month = date.toLocaleDateString('en-GB', { month: 'short' })
    const hours = date.getHours()
    const minutes = date.getMinutes().toString().padStart(2, '0')
    return `${day} ${month} • ${hours}:${minutes}`
  }
  
  return (
    <div 
      className={`waste-card ${isSelected ? 'waste-card-selected' : ''}`}
      onClick={onClick}
    >
      <div className="waste-card-top">
        <div className="waste-card-item-name">{entry.itemName}</div>
        <div className="waste-card-timestamp">{formatTimestamp(entry.timestamp)}</div>
      </div>
      
      <div className="waste-card-middle">
        <div className="waste-card-cost">£{entry.costLost.toFixed(2)} lost</div>
        <span className={`waste-card-badge ${reasonBadgeClass[entry.reason]}`}>
          {reasonLabels[entry.reason]}
        </span>
      </div>
      
      <div className="waste-card-bottom">
        <span className="waste-card-staff">{entry.staffMember}</span>
        <span className="waste-card-venue">{entry.venue}</span>
      </div>
    </div>
  )
}

