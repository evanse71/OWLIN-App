import { useState, useMemo, useEffect } from 'react'
import { AlertCircle, ChevronDown, CheckCircle2, ChevronRight, Loader2 } from 'lucide-react'
import type { InvoiceListItem } from './DocumentList'
import type { InvoiceDetail } from './DocumentDetailPanel'
import { API_BASE_URL } from '../../lib/config'
import { normalizeInvoice, fetchDeliveryNoteDetails } from '../../lib/api'
import { DeliveryNotesCardsSection } from './DeliveryNotesCardsSection'
import { matchLineItems } from '../../lib/lineItemMatcher'
import './SmartDiscrepancyWidget.css'

export interface Discrepancy {
  id: string
  type: 'price_mismatch' | 'short_delivery' | 'missing_dn' | 'low_confidence' | 
        'calculation_error' | 'missing_field' | 'duplicate' | 'date_anomaly'
  severity: 'critical' | 'warning' | 'info'
  invoiceId: string
  invoiceNumber?: string
  supplier?: string
  description: string
  value?: number
  percentage?: number
  financialImpact?: number
  suggestedAction?: string
  context?: string
  lineItemDetails?: Array<{
    description: string
    invoiceQty: number
    deliveryQty: number
    difference: number
    matchType?: 'exact' | 'sku' | 'fuzzy' | 'partial' | 'none'
    similarity?: number
  }>
}

export interface DiscrepancyContext {
  type: Discrepancy['type']
  lineItemIndex?: number
  lineItemDescription?: string
  section?: 'lineItems' | 'deliveryNote' | 'header'
}

interface SmartDiscrepancyWidgetProps {
  invoices: InvoiceListItem[]
  onSelectInvoice: (invoiceId: string, context?: DiscrepancyContext) => void
  selectedDNId?: string | null
  onSelectDN?: (dnId: string) => void
  pairingMode?: 'automatic' | 'manual'
  onPairingModeChange?: (mode: 'automatic' | 'manual') => void
  refreshTrigger?: number
  onRefreshComplete?: () => void
  onPairSuccess?: () => void
}

export function SmartDiscrepancyWidget({ 
  invoices, 
  onSelectInvoice,
  selectedDNId,
  onSelectDN,
  pairingMode = 'manual',
  onPairingModeChange,
  refreshTrigger,
  onRefreshComplete,
  onPairSuccess,
}: SmartDiscrepancyWidgetProps) {
  const [isCollapsed, setIsCollapsed] = useState(false)
  const [invoiceDetails, setInvoiceDetails] = useState<Map<string, InvoiceDetail>>(new Map())
  const [loadingDetails, setLoadingDetails] = useState<Set<string>>(new Set())
  const [errorDetails, setErrorDetails] = useState<Map<string, string>>(new Map())
  const [internalPairingMode, setInternalPairingMode] = useState<'automatic' | 'manual'>('manual')
  const [isRefreshing, setIsRefreshing] = useState(false)
  const [lastRefreshTrigger, setLastRefreshTrigger] = useState<number | undefined>(refreshTrigger)
  const [hasNewError, setHasNewError] = useState(false)
  
  const currentPairingMode = pairingMode !== undefined ? pairingMode : internalPairingMode
  const handlePairingModeChange = onPairingModeChange || setInternalPairingMode
  const handleSelectDN = onSelectDN || (() => {})

  const uploadedInvoices = useMemo(() => {
    return invoices.filter(inv => inv.dbStatus !== 'submitted')
  }, [invoices])

  useEffect(() => {
    if (refreshTrigger !== undefined && refreshTrigger !== lastRefreshTrigger) {
      setIsRefreshing(true)
      setLastRefreshTrigger(refreshTrigger)
      setInvoiceDetails(new Map())
      setLoadingDetails(new Set())
      setErrorDetails(new Map())
    }
  }, [refreshTrigger, lastRefreshTrigger])

  useEffect(() => {
    const fetchDetails = async () => {
      const invoicesToFetch = uploadedInvoices.filter(
        inv => inv.hasDeliveryNote && !invoiceDetails.has(inv.id) && !loadingDetails.has(inv.id)
      )
      
      if (invoicesToFetch.length === 0) {
        if (isRefreshing && loadingDetails.size === 0) {
          setIsRefreshing(false)
          if (onRefreshComplete) {
            onRefreshComplete()
          }
        }
        return
      }
      
      for (const inv of invoicesToFetch) {
        setLoadingDetails(prev => new Set(prev).add(inv.id))
        setErrorDetails(prev => {
          const next = new Map(prev)
          next.delete(inv.id)
          return next
        })
        try {
          let response = await fetch(`${API_BASE_URL}/api/invoices/${inv.id}`)
          let isManual = false
          
          if (!response.ok) {
            response = await fetch(`${API_BASE_URL}/api/manual/invoices/${inv.id}`)
            isManual = true
          }
          
          if (!response.ok) {
            const errorMsg = `Failed to fetch invoice details: ${response.status} ${response.statusText}`
            console.error(`Failed to fetch details for invoice ${inv.id}:`, errorMsg)
            setErrorDetails(prev => new Map(prev).set(inv.id, errorMsg))
            return
          }

          const data = await response.json()
          const rawInvoice = data.invoice || data
          const invData = normalizeInvoice(rawInvoice)
          
          const detail: InvoiceDetail = {
            id: String(invData.id || invData.docId),
            invoiceNumber: String(invData.id || invData.docId || ''),
            supplier: invData.supplier || 'Unknown Supplier',
            date: invData.invoiceDate || '',
            venue: invData.venue || 'Main Restaurant',
            value: invData.totalValue || 0,
            subtotal: invData.totalValue || 0,
            vat: 0,
            status: isManual ? 'manual' : 'scanned',
            matched: invData.paired || false,
            flagged: (invData.issuesCount && invData.issuesCount > 0) || false,
            lineItems: invData.lineItems || [],
            sourceFilename: String(invData.docId || ''),
            confidence: invData.confidence || null,
          }

          if (invData.deliveryNoteId) {
            try {
              const dnId = String(invData.deliveryNoteId)
              const dnDetails = await fetchDeliveryNoteDetails(dnId)
              
              if (!dnDetails) {
                const errorMsg = `Delivery note ${dnId} not found`
                console.error(`Failed to fetch delivery note for invoice ${inv.id}:`, errorMsg)
                setErrorDetails(prev => new Map(prev).set(inv.id, errorMsg))
              } else {
                const lineItems = dnDetails?.lineItems || dnDetails?.line_items || []
                const safeLineItems = Array.isArray(lineItems) ? lineItems : []
                
                detail.deliveryNote = {
                  id: dnId,
                  noteNumber: dnDetails?.noteNumber || dnDetails?.note_number || `DN-${dnId.slice(0, 8)}`,
                  date: dnDetails?.date || dnDetails?.doc_date || '',
                  lineItems: safeLineItems,
                }
              }
            } catch (err) {
              const errorMsg = err instanceof Error ? err.message : 'Failed to fetch delivery note details'
              console.error(`Failed to fetch delivery note for invoice ${inv.id}:`, err)
              setErrorDetails(prev => new Map(prev).set(inv.id, `Delivery note error: ${errorMsg}`))
            }
          }

          setInvoiceDetails(prev => new Map(prev).set(inv.id, detail))
        } catch (err) {
          const errorMsg = err instanceof Error ? err.message : 'Unknown error occurred'
          console.error(`Failed to fetch details for invoice ${inv.id}:`, err)
          setErrorDetails(prev => new Map(prev).set(inv.id, `Failed to load invoice data: ${errorMsg}`))
        } finally {
          setLoadingDetails(prev => {
            const next = new Set(prev)
            next.delete(inv.id)
            return next
          })
        }
      }
    }
    
    fetchDetails()
  }, [uploadedInvoices, invoiceDetails, loadingDetails, onRefreshComplete, isRefreshing])

  useEffect(() => {
    if (isRefreshing && loadingDetails.size === 0) {
      const checkCompletion = setTimeout(() => {
        const needsFetching = uploadedInvoices.some(
          inv => inv.hasDeliveryNote && !invoiceDetails.has(inv.id)
        )
        
        if (!needsFetching || uploadedInvoices.length === 0) {
          setIsRefreshing(false)
          if (onRefreshComplete) {
            onRefreshComplete()
          }
        }
      }, 100)

      return () => clearTimeout(checkCompletion)
    }
  }, [isRefreshing, loadingDetails.size, uploadedInvoices, invoiceDetails, onRefreshComplete])

  useEffect(() => {
    if (isRefreshing) {
      const timeout = setTimeout(() => {
        console.warn('[SmartDiscrepancyWidget] Refresh timed out after 10 seconds, forcing completion')
        setIsRefreshing(false)
        if (onRefreshComplete) {
          onRefreshComplete()
        }
      }, 10000)

      return () => clearTimeout(timeout)
    }
  }, [isRefreshing, onRefreshComplete])

  const formatCurrency = (value?: number) => {
    if (value === undefined || value === null) return ''
    return new Intl.NumberFormat('en-GB', { style: 'currency', currency: 'GBP' }).format(value)
  }

  // Detection functions (keeping existing logic)
  const detectPriceMismatches = (invs: InvoiceListItem[]): Discrepancy[] => {
    const discrepancies: Discrepancy[] = []
    
    for (const inv of invs) {
      if (!inv.hasDeliveryNote || !inv.value) continue
      
      const detail = invoiceDetails.get(inv.id)
      if (!detail || !detail.deliveryNote) continue

      let deliveryTotal = 0
      if (detail.deliveryNote.lineItems && detail.deliveryNote.lineItems.length > 0) {
        deliveryTotal = detail.deliveryNote.lineItems.reduce((sum, item) => {
          return sum + (item.total || item.line_total || (item.qty || item.quantity || 0) * (item.price || item.unit_price || 0))
        }, 0)
      }

      const invoiceTotal = detail.value || inv.value || 0
      if (deliveryTotal === 0) continue

      const difference = Math.abs(invoiceTotal - deliveryTotal)
      const maxTotal = Math.max(invoiceTotal, deliveryTotal)
      const percentDiff = maxTotal > 0 ? (difference / maxTotal) * 100 : 0

      const thresholdPercent = 1.0
      const thresholdAbsolute = 2.0
      const isMismatch = percentDiff > thresholdPercent || difference > thresholdAbsolute

      if (isMismatch) {
        let severity: 'critical' | 'warning' | 'info' = 'warning'
        if (difference > 10 || percentDiff > 5) {
          severity = 'critical'
        } else if (difference <= 2 && percentDiff <= 1.5) {
          severity = 'info'
        }

        const context = percentDiff <= 2 ? 'This is within typical variance for most suppliers' : undefined

        discrepancies.push({
          id: `price-mismatch-${inv.id}`,
          type: 'price_mismatch',
          severity,
          invoiceId: inv.id,
          invoiceNumber: inv.invoiceNumber || detail.invoiceNumber,
          supplier: inv.supplier || detail.supplier,
          description: `Invoice total differs from delivery note by ${formatCurrency(difference)} (${percentDiff.toFixed(1)}%)`,
          value: difference,
          percentage: percentDiff,
          financialImpact: difference,
          context,
          suggestedAction: 'Review invoice and delivery note totals to verify accuracy'
        })
      }
    }
    
    return discrepancies
  }

  const detectShortDeliveries = (invs: InvoiceListItem[]): Discrepancy[] => {
    const discrepancies: Discrepancy[] = []
    
    for (const inv of invs) {
      if (!inv.hasDeliveryNote) continue
      
      const detail = invoiceDetails.get(inv.id)
      if (!detail || !detail.deliveryNote) continue

      const invoiceItems = detail.lineItems || []
      const deliveryItems = detail.deliveryNote.lineItems || []
      
      if (!Array.isArray(invoiceItems) || invoiceItems.length === 0) continue
      if (!Array.isArray(deliveryItems) || deliveryItems.length === 0) continue

      const shortItems: Array<{ 
        description: string
        invoiceQty: number
        deliveryQty: number
        difference: number
        matchType?: 'exact' | 'sku' | 'fuzzy' | 'partial' | 'none'
        similarity?: number
      }> = []
      let totalShortfallValue = 0

      const matchedItems = matchLineItems(invoiceItems, deliveryItems, 0.85)

      for (const match of matchedItems) {
        try {
          const invItem = match.invoiceItem
          const delItem = match.deliveryItem
          const similarity = match.similarity
          const matchType = match.matchType

          const invDesc = invItem?.description || invItem?.item || ''
          if (!invDesc) continue

          const invQty = invItem?.qty || invItem?.quantity || 0
          const invPrice = invItem?.price || invItem?.unit_price || 0
          const invTotal = invItem?.total || invItem?.line_total || 0
          
          const unitPrice = invPrice > 0 ? invPrice : (invQty > 0 && invTotal > 0 ? invTotal / invQty : 0)

          const dnQty = delItem && similarity >= 0.85 
            ? (delItem.qty || delItem.quantity || 0) 
            : 0

          if (dnQty < invQty - 0.01) {
            const difference = invQty - dnQty
            shortItems.push({
              description: invItem.description || invItem.item || 'Unknown item',
              invoiceQty: invQty,
              deliveryQty: dnQty,
              difference,
              matchType,
              similarity,
            })
            totalShortfallValue += difference * unitPrice
          } else if (!delItem || similarity < 0.85) {
            const difference = invQty
            shortItems.push({
              description: invItem.description || invItem.item || 'Unknown item',
              invoiceQty: invQty,
              deliveryQty: 0,
              difference,
              matchType: 'none',
              similarity: 0,
            })
            totalShortfallValue += difference * unitPrice
          }
        } catch (err) {
          console.warn(`Error comparing line item for invoice ${inv.id}:`, err)
        }
      }

      if (shortItems.length > 0) {
        const severity: 'critical' | 'warning' | 'info' = totalShortfallValue > 10 ? 'critical' : totalShortfallValue > 2 ? 'warning' : 'info'
        
        discrepancies.push({
          id: `short-delivery-${inv.id}`,
          type: 'short_delivery',
          severity,
          invoiceId: inv.id,
          invoiceNumber: inv.invoiceNumber || detail.invoiceNumber,
          supplier: inv.supplier || detail.supplier,
          description: `${shortItems.length} item${shortItems.length !== 1 ? 's' : ''} may have been delivered in lower quantities`,
          value: totalShortfallValue,
          financialImpact: totalShortfallValue,
          lineItemDetails: shortItems,
          suggestedAction: `Review line items against delivery note. Potential credit: ${formatCurrency(totalShortfallValue)}`
        })
      }
    }
    
    return discrepancies
  }

  const detectMissingDeliveryNotes = (invs: InvoiceListItem[]): Discrepancy[] => {
    const discrepancies: Discrepancy[] = []
    
    for (const inv of invs) {
      if (!inv.hasDeliveryNote) {
        discrepancies.push({
          id: `missing-dn-${inv.id}`,
          type: 'missing_dn',
          severity: 'warning',
          invoiceId: inv.id,
          invoiceNumber: inv.invoiceNumber,
          supplier: inv.supplier,
          description: `No delivery note paired to invoice`,
          suggestedAction: 'Click to view invoice and link a delivery note'
        })
      }
    }
    
    return discrepancies
  }

  const detectLowConfidence = (invs: InvoiceListItem[]): Discrepancy[] => {
    const discrepancies: Discrepancy[] = []
    
    for (const inv of invs) {
      if (inv.confidence !== undefined && inv.confidence < 0.7) {
        const confidencePercent = Math.round(inv.confidence * 100)
        const severity = inv.confidence < 0.5 ? 'critical' : 'warning'
        discrepancies.push({
          id: `low-confidence-${inv.id}`,
          type: 'low_confidence',
          severity,
          invoiceId: inv.id,
          invoiceNumber: inv.invoiceNumber,
          supplier: inv.supplier,
          description: `OCR confidence is ${confidencePercent}% - extracted data may need review`,
          percentage: inv.confidence * 100,
          suggestedAction: 'Review extracted fields to ensure accuracy, especially amounts and line items'
        })
      }
    }
    
    return discrepancies
  }

  const allDiscrepancies = useMemo(() => {
    if (uploadedInvoices.length === 0) return []
    
    const discrepancies = [
      ...detectPriceMismatches(uploadedInvoices),
      ...detectShortDeliveries(uploadedInvoices),
      ...detectMissingDeliveryNotes(uploadedInvoices),
      ...detectLowConfidence(uploadedInvoices),
    ]

    return discrepancies.sort((a, b) => {
      const aImpact = a.financialImpact || 0
      const bImpact = b.financialImpact || 0
      if (Math.abs(aImpact - bImpact) > 0.01) {
        return bImpact - aImpact
      }
      
      const severityOrder = { critical: 3, warning: 2, info: 1 }
      return severityOrder[b.severity] - severityOrder[a.severity]
    })
  }, [uploadedInvoices, invoiceDetails, refreshTrigger])

  const groupedDiscrepancies = useMemo(() => {
    const critical = allDiscrepancies.filter(d => d.severity === 'critical')
    const secondary = allDiscrepancies.filter(d => d.severity !== 'critical')
    return { critical, secondary }
  }, [allDiscrepancies])

  // Track new errors for pulse effect
  useEffect(() => {
    if (allDiscrepancies.length > 0 && isCollapsed) {
      setHasNewError(true)
      const timer = setTimeout(() => setHasNewError(false), 2000)
      return () => clearTimeout(timer)
    }
  }, [allDiscrepancies.length, isCollapsed])

  const handleDiscrepancyClick = (disc: Discrepancy) => {
    const context: DiscrepancyContext = {
      type: disc.type,
      section: disc.type === 'missing_dn' ? 'deliveryNote' : 
               disc.type === 'short_delivery' ? 'lineItems' : 
               'header'
    }
    
    if (disc.type === 'short_delivery' && disc.lineItemDetails && disc.lineItemDetails.length > 0) {
      context.lineItemDescription = disc.lineItemDetails[0].description
    }
    
    onSelectInvoice(disc.invoiceId, context)
  }

  const getFocusTitle = (disc: Discrepancy): string => {
    switch (disc.type) {
      case 'price_mismatch':
        return 'Invoice Amount Variance'
      case 'short_delivery':
        return 'Short Delivery Detected'
      case 'missing_dn':
        return 'Missing Delivery Note'
      case 'low_confidence':
        return 'Low OCR Confidence'
      default:
        return 'Issue Detected'
    }
  }

  const getFocusContext = (disc: Discrepancy): string => {
    if (disc.type === 'price_mismatch' && disc.value) {
      const invoiceNum = disc.invoiceNumber || 'Invoice'
      const amount = formatCurrency(disc.value)
      const direction = disc.value > 0 ? 'higher' : 'lower'
      // Try to get PO number from context if available, otherwise use generic
      return `${invoiceNum} is ${amount} ${direction} than expected.`
    }
    if (disc.type === 'short_delivery' && disc.lineItemDetails) {
      return `${disc.lineItemDetails.length} item${disc.lineItemDetails.length !== 1 ? 's' : ''} delivered in lower quantities.`
    }
    if (disc.type === 'missing_dn') {
      return `${disc.invoiceNumber || 'Invoice'} is not linked to a delivery note.`
    }
    if (disc.type === 'low_confidence' && disc.percentage) {
      return `OCR confidence is ${Math.round(disc.percentage)}% - extracted data may need review.`
    }
    return disc.description
  }

  const totalCount = allDiscrepancies.length
  const focusItem = groupedDiscrepancies.critical[0]
  const quickFixItems = groupedDiscrepancies.secondary.slice(0, 5) // Limit to 5 items

  if (uploadedInvoices.length === 0) {
    return (
      <div className="smart-discrepancy-widget">
        <div className="analysis-widget">
          <div className="analysis-widget-header">
            <span className="analysis-widget-title">Analysis Assistant</span>
            <span className="analysis-widget-badge analysis-widget-badge-clear">All Clear</span>
            <ChevronDown className="analysis-widget-chevron" size={16} />
          </div>
        </div>
        <DeliveryNotesCardsSection
          selectedDNId={selectedDNId}
          onSelectDN={handleSelectDN}
          pairingMode={currentPairingMode}
          onPairingModeChange={handlePairingModeChange}
          onPairSuccess={onPairSuccess}
        />
      </div>
    )
  }

  return (
    <div className="smart-discrepancy-widget">
      <div className={`analysis-widget ${isCollapsed ? 'analysis-widget-collapsed' : ''} ${hasNewError ? 'analysis-widget-pulse' : ''}`}>
        {/* Header */}
        <div className="analysis-widget-header" onClick={() => setIsCollapsed(!isCollapsed)}>
          <span className="analysis-widget-title">Analysis Assistant</span>
          {totalCount > 0 ? (
            <span className="analysis-widget-badge analysis-widget-badge-issues">
              {totalCount} Action{totalCount !== 1 ? 's' : ''}
            </span>
          ) : (
            <span className="analysis-widget-badge analysis-widget-badge-clear">All Clear</span>
          )}
          <ChevronDown 
            className={`analysis-widget-chevron ${isCollapsed ? 'analysis-widget-chevron-collapsed' : ''}`} 
            size={16} 
          />
        </div>

        {/* Body - Only visible when expanded */}
        {!isCollapsed && (
          <div className="analysis-widget-body">
            {totalCount === 0 ? (
              /* Empty State - Celebration */
              <div className="analysis-widget-empty">
                <CheckCircle2 className="analysis-widget-empty-icon" size={48} strokeWidth={1.5} />
                <div className="analysis-widget-empty-text">All caught up. Nice work.</div>
              </div>
            ) : (
              <>
                {/* Focus Section - Hero Card for Critical Issue */}
                {focusItem && (
                  <div className="analysis-widget-focus analysis-widget-focus-group">
                    <div className="analysis-widget-focus-header">
                      <AlertCircle className="analysis-widget-focus-icon" size={18} />
                      <span className="analysis-widget-focus-title">{getFocusTitle(focusItem)}</span>
                    </div>
                    <div className="analysis-widget-focus-context">
                      {getFocusContext(focusItem)}
                    </div>
                    <div className="analysis-widget-focus-action">
                      <button 
                        className="analysis-widget-focus-button"
                        onClick={(e) => {
                          e.stopPropagation()
                          handleDiscrepancyClick(focusItem)
                        }}
                      >
                        Review Invoice
                      </button>
                    </div>
                  </div>
                )}

                {/* Quick Fix List - Secondary Issues */}
                {quickFixItems.length > 0 && (
                  <div className="analysis-widget-quickfix">
                    <div className="analysis-widget-quickfix-label">Optimization Suggestions</div>
                    <div className="analysis-widget-quickfix-list">
                      {quickFixItems.map((item) => (
                        <div 
                          key={item.id} 
                          className="analysis-widget-quickfix-item"
                          onClick={() => handleDiscrepancyClick(item)}
                        >
                          <span className="analysis-widget-quickfix-dot"></span>
                          <span className="analysis-widget-quickfix-text">
                            {item.type === 'missing_dn' 
                              ? `Unlinked Delivery Note (${item.invoiceNumber || 'Invoice'})`
                              : item.description}
                          </span>
                          <ChevronRight className="analysis-widget-quickfix-arrow" size={14} />
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </>
            )}
          </div>
        )}
      </div>

      {/* Delivery Notes Cards Section */}
      <DeliveryNotesCardsSection
        selectedDNId={selectedDNId}
        onSelectDN={handleSelectDN}
        pairingMode={currentPairingMode}
        onPairingModeChange={handlePairingModeChange}
        onPairSuccess={onPairSuccess}
        refreshTrigger={refreshTrigger}
      />
    </div>
  )
}
