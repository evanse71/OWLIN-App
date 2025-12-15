import { useState, useRef, useEffect } from 'react'
import { Loader2, Eye, EyeOff } from 'lucide-react'
import './InvoiceVisualizer.css'

export interface LineItemWithBBox {
  description?: string
  item?: string
  desc?: string
  qty?: number
  quantity?: number
  unit_price?: number
  price?: number
  total?: number
  line_total?: number
  bbox?: number[] // [x, y, w, h] in original image pixels
  [key: string]: unknown
}

interface InvoiceVisualizerProps {
  docId: string
  lineItems?: LineItemWithBBox[]
  activeLineItemIndex?: number | null
  onLineItemHover?: (index: number | null) => void
  className?: string
}

export function InvoiceVisualizer({
  docId,
  lineItems = [],
  activeLineItemIndex = null,
  onLineItemHover,
  className = '',
}: InvoiceVisualizerProps) {
  const [imageLoaded, setImageLoaded] = useState(false)
  const [imageError, setImageError] = useState(false)
  const [imageErrorDetail, setImageErrorDetail] = useState<string | null>(null)
  const [imageDimensions, setImageDimensions] = useState<{ width: number; height: number } | null>(null)
  const [hoveredBoxIndex, setHoveredBoxIndex] = useState<number | null>(null)
  const [showBoxes, setShowBoxes] = useState(true)
  const imageRef = useRef<HTMLImageElement>(null)
  const containerRef = useRef<HTMLDivElement>(null)

  // Image URL from the new endpoint
  // Use relative path - Vite proxy will handle it in dev, or use full URL in production
  const imageUrl = `/api/ocr/page-image/${docId}`

  // Reset error state when docId changes
  useEffect(() => {
    setImageError(false)
    setImageErrorDetail(null)
    setImageLoaded(false)
  }, [docId])

  // Handle image load
  const handleImageLoad = () => {
    if (imageRef.current) {
      const naturalWidth = imageRef.current.naturalWidth
      const naturalHeight = imageRef.current.naturalHeight
      setImageDimensions({ width: naturalWidth, height: naturalHeight })
      setImageLoaded(true)
      setImageError(false)
      setImageErrorDetail(null)
    }
  }

  const handleImageError = (event: React.SyntheticEvent<HTMLImageElement, Event>) => {
    setImageError(true)
    setImageLoaded(false)
    // Try to get more error details
    const img = event.currentTarget
    const errorMsg = img.src ? `Failed to load: ${img.src}` : 'Failed to load image'
    setImageErrorDetail(errorMsg)
    console.error('[InvoiceVisualizer] Image load error:', {
      docId,
      imageUrl,
      error: errorMsg,
    })
  }

  // Filter line items that have bounding boxes
  const itemsWithBBoxes = lineItems.filter((item) => {
    const bbox = item.bbox
    const hasValidBbox = bbox && Array.isArray(bbox) && bbox.length >= 4
    if (!hasValidBbox && lineItems.length > 0) {
      // Debug: log when items don't have bbox
      console.debug('[InvoiceVisualizer] Item missing bbox:', {
        description: item.description || item.desc || item.item,
        hasBbox: !!bbox,
        bboxType: typeof bbox,
        bboxValue: bbox,
        allKeys: Object.keys(item),
      })
    }
    return hasValidBbox
  })
  
  // Debug: log bbox data availability
  useEffect(() => {
    if (lineItems.length > 0) {
      console.log('[InvoiceVisualizer] Line items bbox status:', {
        totalItems: lineItems.length,
        itemsWithBbox: itemsWithBBoxes.length,
        sampleItem: lineItems[0],
        showBoxes,
        imageLoaded,
        imageDimensions,
      })
    }
  }, [lineItems, itemsWithBBoxes.length, showBoxes, imageLoaded, imageDimensions])

  // Calculate box styles based on percentage positioning
  const getBoxStyle = (bbox: number[], index: number) => {
    if (!imageDimensions) {
      return {}
    }

    const [x, y, w, h] = bbox
    const { width: naturalWidth, height: naturalHeight } = imageDimensions

    // Convert pixel coordinates to percentages
    const leftPercent = (x / naturalWidth) * 100
    const topPercent = (y / naturalHeight) * 100
    const widthPercent = (w / naturalWidth) * 100
    const heightPercent = (h / naturalHeight) * 100

    // Determine if this box is active (hovered or selected)
    const isActive = hoveredBoxIndex === index || activeLineItemIndex === index
    const isHovered = hoveredBoxIndex === index

    return {
      position: 'absolute' as const,
      left: `${leftPercent}%`,
      top: `${topPercent}%`,
      width: `${widthPercent}%`,
      height: `${heightPercent}%`,
      border: isActive
        ? `2px solid ${isHovered ? 'rgba(59, 130, 246, 1)' : 'rgba(16, 185, 129, 0.9)'}`
        : '2px solid rgba(0, 255, 0, 0.7)',
      backgroundColor: isActive
        ? `${isHovered ? 'rgba(59, 130, 246, 0.2)' : 'rgba(16, 185, 129, 0.15)'}`
        : 'rgba(0, 255, 0, 0.1)',
      cursor: 'pointer',
      transition: 'all 0.2s ease',
      zIndex: isActive ? 10 : 1,
      boxShadow: isActive
        ? `0 0 0 2px ${isHovered ? 'rgba(59, 130, 246, 0.3)' : 'rgba(16, 185, 129, 0.3)'}`
        : 'none',
    }
  }

  // Get description text for tooltip
  const getItemDescription = (item: LineItemWithBBox) => {
    return (
      item.description ||
      item.item ||
      item.desc ||
      'Unknown item'
    )
  }

  // Handle box hover
  const handleBoxMouseEnter = (index: number) => {
    setHoveredBoxIndex(index)
    if (onLineItemHover) {
      onLineItemHover(index)
    }
  }

  const handleBoxMouseLeave = () => {
    setHoveredBoxIndex(null)
    if (onLineItemHover) {
      onLineItemHover(null)
    }
  }

  // Reset hover when activeLineItemIndex changes externally
  useEffect(() => {
    if (activeLineItemIndex !== null && activeLineItemIndex !== hoveredBoxIndex) {
      setHoveredBoxIndex(null)
    }
  }, [activeLineItemIndex])

  if (imageError) {
    return (
      <div className={`invoice-visualizer error ${className}`}>
        <div className="error-message">
          <p>Unable to load invoice image</p>
          <p className="error-detail">Document ID: {docId}</p>
          {imageErrorDetail && (
            <p className="error-detail" style={{ fontSize: '0.75rem', marginTop: '8px' }}>
              {imageErrorDetail}
            </p>
          )}
          <p className="error-detail" style={{ fontSize: '0.75rem', marginTop: '8px', color: 'var(--text-tertiary)' }}>
            URL: {imageUrl}
          </p>
          <p className="error-detail" style={{ fontSize: '0.75rem', marginTop: '4px', color: 'var(--text-tertiary)' }}>
            Check browser console for details. Ensure backend is running and document exists.
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className={`invoice-visualizer ${className}`} ref={containerRef}>
      {/* Controls */}
      <div className="visualizer-controls">
        <button
          type="button"
          onClick={() => setShowBoxes(!showBoxes)}
          className="toggle-boxes-btn"
          title={showBoxes ? 'Hide bounding boxes' : 'Show bounding boxes'}
        >
          {showBoxes ? <EyeOff size={16} /> : <Eye size={16} />}
          <span>{showBoxes ? 'Hide Boxes' : 'Show Boxes'}</span>
        </button>
        {itemsWithBBoxes.length > 0 && (
          <span className="box-count">
            {itemsWithBBoxes.length} item{itemsWithBBoxes.length !== 1 ? 's' : ''} detected
          </span>
        )}
      </div>

      {/* Image Container */}
      <div className="image-container">
        {!imageLoaded && !imageError && (
          <div className="loading-overlay">
            <Loader2 className="spinner" size={24} />
            <p>Loading invoice image...</p>
          </div>
        )}

        <img
          ref={imageRef}
          src={imageUrl}
          alt="Invoice"
          className="invoice-image"
          onLoad={handleImageLoad}
          onError={handleImageError}
          style={{ display: imageLoaded ? 'block' : 'none' }}
        />

        {/* Bounding Box Overlays */}
        {imageLoaded && showBoxes && imageDimensions && imageRef.current && (
          <div 
            className="bbox-overlay-container"
            style={{
              width: imageRef.current.offsetWidth > 0 ? `${imageRef.current.offsetWidth}px` : '100%',
              height: imageRef.current.offsetHeight > 0 ? `${imageRef.current.offsetHeight}px` : '100%',
            }}
          >
            {itemsWithBBoxes.map((item, index) => {
              const bbox = item.bbox!
              return (
                <div
                  key={index}
                  className="bbox-overlay"
                  style={getBoxStyle(bbox, index)}
                  onMouseEnter={() => handleBoxMouseEnter(index)}
                  onMouseLeave={handleBoxMouseLeave}
                  title={`${getItemDescription(item)} | Qty: ${item.qty || 'N/A'} | Total: £${item.total || 'N/A'}`}
                >
                  {/* Tooltip on hover */}
                  {hoveredBoxIndex === index && (
                    <div className="bbox-tooltip">
                      <div className="tooltip-content">
                        <strong>{getItemDescription(item)}</strong>
                        {item.qty && (
                          <span>Qty: {item.qty}</span>
                        )}
                        {item.total && (
                          <span>Total: £{item.total}</span>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        )}
      </div>

      {/* Legend */}
      {imageLoaded && showBoxes && itemsWithBBoxes.length > 0 && (
        <div className="visualizer-legend">
          <div className="legend-item">
            <div className="legend-box" style={{ borderColor: 'rgba(0, 255, 0, 0.7)' }} />
            <span>Detected item</span>
          </div>
          <div className="legend-item">
            <div className="legend-box" style={{ borderColor: 'rgba(59, 130, 246, 1)' }} />
            <span>Hovered</span>
          </div>
          <div className="legend-item">
            <div className="legend-box" style={{ borderColor: 'rgba(16, 185, 129, 0.9)' }} />
            <span>Selected</span>
          </div>
        </div>
      )}
    </div>
  )
}

