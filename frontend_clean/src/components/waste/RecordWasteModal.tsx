/**
 * Record Waste Modal Component
 * Modal for recording new waste entries with segmented control, quantity input, reason dropdown, and staff field
 */

import { useState, useEffect } from 'react'
import { X } from 'lucide-react'
import type { WasteItemType, WasteReason } from '../../types/waste'
import { useRecordWaste } from '../../hooks/useWaste'
import { addNotification } from '../dashboard/NotificationStack'
import '../invoices/Modal.css'
import './RecordWasteModal.css'

interface RecordWasteModalProps {
  isOpen: boolean
  onClose: () => void
  onSuccess: () => void
  venue?: string
}

const itemTypes: Array<{ value: WasteItemType; label: string }> = [
  { value: 'meal', label: 'Meal' },
  { value: 'ingredient', label: 'Ingredient' },
  { value: 'prep', label: 'Prep batch' }
]

const reasons: Array<{ value: WasteReason; label: string }> = [
  { value: 'spoilage', label: 'Spoilage' },
  { value: 'overcooked', label: 'Overcooked' },
  { value: 'customer-return', label: 'Customer return' },
  { value: 'over-portion', label: 'Over-portion' },
  { value: 'prep-error', label: 'Prepped too much' },
  { value: 'storage-issue', label: 'Storage issue' },
  { value: 'delivery-quality', label: 'Delivery quality issue' }
]

const units = ['g', 'kg', 'L', 'portion', 'keg', 'crate', 'unit', 'box']

// Mock data for autocomplete
const mockMeals = ['Fish & Chips', 'Beef Burger', 'Caesar Salad', 'Pasta Carbonara', 'Chicken Curry', 'Lamb Shank']
const mockIngredients = ['Chicken Breast 5kg', 'Carling Keg 11g', 'Tomato Soup', 'Bread Loaf', 'Milk 4L', 'Cheese Block', 'Rice 10kg', 'Potatoes 25kg']
const mockPrepItems = ['Prepped Vegetables', 'Marinated Chicken', 'Soup Base', 'Dough Batch', 'Sauce Mix']

export function RecordWasteModal({ isOpen, onClose, onSuccess, venue = 'Waterloo' }: RecordWasteModalProps) {
  const [itemType, setItemType] = useState<WasteItemType>('meal')
  const [itemName, setItemName] = useState('')
  const [quantity, setQuantity] = useState<number>(0)
  const [unit, setUnit] = useState('kg')
  const [reason, setReason] = useState<WasteReason>('spoilage')
  const [note, setNote] = useState('')
  const [staffMember, setStaffMember] = useState('John Smith') // Mock current user
  const [taggedStaff, setTaggedStaff] = useState<string | ''>('')
  const [autocompleteSuggestions, setAutocompleteSuggestions] = useState<string[]>([])
  const [showSuggestions, setShowSuggestions] = useState(false)
  
  const { recordWaste, loading } = useRecordWaste()
  
  // Mock staff members
  const availableStaff = ['John Smith', 'Sarah Johnson', 'Mike Brown', 'Emma Wilson', 'David Lee']
  
  // Update autocomplete suggestions based on item type
  useEffect(() => {
    if (itemName.length > 0) {
      const suggestions = (itemType === 'meal' ? mockMeals :
                          itemType === 'ingredient' ? mockIngredients :
                          mockPrepItems)
        .filter(item => item.toLowerCase().includes(itemName.toLowerCase()))
        .slice(0, 5)
      setAutocompleteSuggestions(suggestions)
      setShowSuggestions(suggestions.length > 0)
    } else {
      setAutocompleteSuggestions([])
      setShowSuggestions(false)
    }
  }, [itemName, itemType])
  
  // Mock cost calculation (in real app, this would fetch from products/meals API)
  const calculateCostLost = () => {
    if (quantity <= 0) return 0
    // Mock price per unit based on item type
    const mockPricePerUnit = itemType === 'meal' ? 8.50 :
                            itemType === 'ingredient' ? 5.20 :
                            3.75
    const unitMultiplier = unit === 'kg' ? 1 : unit === 'g' ? 0.001 : unit === 'L' ? 1 : 1
    return Math.round((quantity * mockPricePerUnit * unitMultiplier) * 100) / 100
  }
  
  const costLost = calculateCostLost()
  
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    if (!itemName.trim() || quantity <= 0) {
      return
    }
    
    try {
      await recordWaste({
        itemName: itemName.trim(),
        itemType,
        quantity,
        unit,
        reason,
        staffMember: taggedStaff || staffMember,
        venue,
        note: note.trim() || undefined
      })
      
      addNotification({
        type: 'success',
        message: 'Waste logged successfully'
      })
      
      // Reset form
      setItemName('')
      setQuantity(0)
      setUnit('kg')
      setReason('spoilage')
      setNote('')
      setTaggedStaff('')
      
      onSuccess()
      onClose()
    } catch (error) {
      addNotification({
        type: 'error',
        message: 'Failed to log waste. Please try again.'
      })
    }
  }
  
  const handleClose = () => {
    if (!loading) {
      onClose()
    }
  }
  
  if (!isOpen) return null
  
  return (
    <div className="modal-overlay" onClick={handleClose}>
      <div className="modal-container" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2 className="modal-title">Record Waste</h2>
          <button className="modal-close-button" onClick={handleClose} disabled={loading}>
            <X size={20} />
          </button>
        </div>
        
        <form onSubmit={handleSubmit}>
          <div className="modal-body">
            {/* Section 1: What was wasted? */}
            <div className="modal-form-group">
              <label className="modal-form-label">What was wasted?</label>
              <div className="waste-modal-segmented-control">
                {itemTypes.map(type => (
                  <button
                    key={type.value}
                    type="button"
                    className={`waste-modal-segment ${itemType === type.value ? 'waste-modal-segment-active' : ''}`}
                    onClick={() => {
                      setItemType(type.value)
                      setItemName('')
                      setAutocompleteSuggestions([])
                      setShowSuggestions(false)
                    }}
                  >
                    {type.label}
                  </button>
                ))}
              </div>
              
              <div className="waste-modal-autocomplete-container">
                <input
                  type="text"
                  className="modal-form-input"
                  placeholder={`Select ${itemType === 'meal' ? 'meal' : itemType === 'ingredient' ? 'ingredient' : 'prep item'}`}
                  value={itemName}
                  onChange={(e) => setItemName(e.target.value)}
                  onFocus={() => {
                    if (autocompleteSuggestions.length > 0) {
                      setShowSuggestions(true)
                    }
                  }}
                  required
                />
                {showSuggestions && autocompleteSuggestions.length > 0 && (
                  <div className="waste-modal-autocomplete-dropdown">
                    {autocompleteSuggestions.map((suggestion, index) => (
                      <div
                        key={index}
                        className="waste-modal-autocomplete-item"
                        onClick={() => {
                          setItemName(suggestion)
                          setShowSuggestions(false)
                        }}
                      >
                        {suggestion}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
            
            {/* Section 2: Quantity wasted */}
            <div className="modal-form-group">
              <label className="modal-form-label">Quantity wasted</label>
              <div className="waste-modal-quantity-row">
                <input
                  type="number"
                  className="modal-form-input waste-modal-quantity-input"
                  placeholder="0"
                  value={quantity || ''}
                  onChange={(e) => setQuantity(parseFloat(e.target.value) || 0)}
                  min="0"
                  step="0.01"
                  required
                />
                <select
                  className="modal-form-select waste-modal-unit-select"
                  value={unit}
                  onChange={(e) => setUnit(e.target.value)}
                >
                  {units.map(u => (
                    <option key={u} value={u}>{u}</option>
                  ))}
                </select>
              </div>
              {costLost > 0 && (
                <div className="waste-modal-cost-display">
                  <span className="waste-modal-cost-label">Cost lost:</span>
                  <span className="waste-modal-cost-value">£{costLost.toFixed(2)}</span>
                </div>
              )}
              <div className="waste-modal-cost-note">
                Approximate cost based on recent purchases
              </div>
            </div>
            
            {/* Section 3: Reason */}
            <div className="modal-form-group">
              <label className="modal-form-label">Reason</label>
              <select
                className="modal-form-select"
                value={reason}
                onChange={(e) => setReason(e.target.value as WasteReason)}
                required
              >
                {reasons.map(r => (
                  <option key={r.value} value={r.value}>
                    {r.label}
                  </option>
                ))}
              </select>
              
              <textarea
                className="modal-form-textarea"
                placeholder="Optional note..."
                value={note}
                onChange={(e) => setNote(e.target.value)}
                rows={3}
              />
            </div>
            
            {/* Section 4: Staff */}
            <div className="modal-form-group">
              <label className="modal-form-label">Staff</label>
              <input
                type="text"
                className="modal-form-input"
                value={staffMember}
                onChange={(e) => setStaffMember(e.target.value)}
                required
              />
              
              <select
                className="modal-form-select waste-modal-tag-staff"
                value={taggedStaff}
                onChange={(e) => setTaggedStaff(e.target.value)}
              >
                <option value="">Tag another staff member (optional)</option>
                {availableStaff.filter(s => s !== staffMember).map(s => (
                  <option key={s} value={s}>{s}</option>
                ))}
              </select>
            </div>
          </div>
          
          <div className="modal-footer">
            <button
              type="button"
              className="glass-button"
              onClick={handleClose}
              disabled={loading}
            >
              Cancel
            </button>
            <button
              type="submit"
              className="glass-button"
              disabled={loading || !itemName.trim() || quantity <= 0}
            >
              {loading ? 'Logging...' : 'Log Waste'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

