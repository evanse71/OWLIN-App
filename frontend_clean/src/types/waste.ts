/**
 * Waste Module Type Definitions
 * Centralized type exports for waste tracking
 */

export type WasteReason = 
  | 'spoilage' 
  | 'overcooked' 
  | 'customer-return' 
  | 'over-portion' 
  | 'prep-error' 
  | 'storage-issue' 
  | 'delivery-quality'

export type WasteItemType = 'meal' | 'ingredient' | 'prep'

export type DateRange = '7d' | '30d' | '90d' | 'custom'

export type WasteEntry = {
  id: string
  itemName: string
  itemType: WasteItemType
  quantity: number
  unit: string
  costLost: number
  reason: WasteReason
  staffMember: string
  venue: string
  timestamp: string
  note?: string
}

export interface WasteFilters {
  category?: WasteItemType | 'all'
  reason?: WasteReason | 'all'
  staffMember?: string | 'all'
  searchQuery?: string
}

export interface ProductWaste {
  productName: string
  wastePercentage: number
  costLost: number
  productId?: string
}

export interface MealWaste {
  mealName: string
  wasteEntriesCount: number
  totalCostLost: number
  mealId?: string
}

export interface SupplierImpact {
  supplierName: string
  wasteCost: number
  wastePercentage: number
  isAboveThreshold: boolean
}

export interface MarginImpact {
  foodCostTarget: number
  actualCostWithWaste: number
  lostMargin: number
  amountNeededToReturnToTarget: number
}

export interface WasteInsights {
  wastePercentage: number
  totalCostLost: number
  topCategory: string
  staffAttribution: string
  productBreakdown: ProductWaste[]
  mealBreakdown: MealWaste[]
  supplierImpact: SupplierImpact[]
  marginImpact: MarginImpact
  trendData: Array<{ date: string; value: number }>
}

