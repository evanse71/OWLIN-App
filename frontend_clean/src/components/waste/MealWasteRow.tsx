/**
 * Meal Waste Row Component
 * Meal breakdown row with click handler (placeholder for Meal module)
 */

import type { MealWaste } from '../../types/waste'
import './MealWasteRow.css'

interface MealWasteRowProps {
  meal: MealWaste
}

export function MealWasteRow({ meal }: MealWasteRowProps) {
  const handleClick = () => {
    // TODO: Navigate to Meal/Recipe module when implemented
    console.log('Navigate to meal:', meal.mealId || meal.mealName)
  }
  
  return (
    <div className="meal-waste-row" onClick={handleClick}>
      <div className="meal-waste-row-content">
        <div className="meal-waste-row-name">{meal.mealName}</div>
        <div className="meal-waste-row-stats">
          <span className="meal-waste-row-count">{meal.wasteEntriesCount} entries</span>
          <span className="meal-waste-row-cost">£{meal.totalCostLost.toLocaleString('en-GB', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} lost</span>
        </div>
      </div>
    </div>
  )
}

