/**
 * Product Waste Row Component
 * Product breakdown row with visual bar and click handler for navigation
 */

import { useNavigate } from 'react-router-dom'
import type { ProductWaste } from '../../types/waste'
import './ProductWasteRow.css'

interface ProductWasteRowProps {
  product: ProductWaste
  maxCostLost: number
}

export function ProductWasteRow({ product, maxCostLost }: ProductWasteRowProps) {
  const navigate = useNavigate()
  const barWidth = maxCostLost > 0 ? (product.costLost / maxCostLost) * 100 : 0
  
  const handleClick = () => {
    if (product.productId) {
      navigate(`/products?product=${product.productId}`)
    } else {
      navigate('/products')
    }
  }
  
  return (
    <div className="product-waste-row" onClick={handleClick}>
      <div className="product-waste-row-content">
        <div className="product-waste-row-name">{product.productName}</div>
        <div className="product-waste-row-stats">
          <span className="product-waste-row-percentage">{product.wastePercentage.toFixed(1)}% waste</span>
          <span className="product-waste-row-cost">£{product.costLost.toLocaleString('en-GB', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} lost</span>
        </div>
      </div>
      <div className="product-waste-row-bar-container">
        <div 
          className="product-waste-row-bar"
          style={{ width: `${barWidth}%` }}
        />
      </div>
    </div>
  )
}

