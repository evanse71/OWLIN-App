import { ChevronDown, Trash2, X, Package, AlertCircle, AlertTriangle } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import type { Invoice } from '../../types/invoice'
import './DocumentList.css'

// Extended Invoice type for UI-specific fields
export type InvoiceListItem = Invoice & {
  // Document ID (may differ from invoice id for document-only cards)
  doc_id?: string
  // Whether invoice row exists in database
  has_invoice_row?: boolean
  // UI-specific status - now includes document states
  status: 'scanned' | 'manual' | 'uploading' | 'processing' | 'ready' | 'error' | 'needs_review'
  // Database status (from backend) - used for needs_review badge
  dbStatus?: string
  // Additional UI flags
  matched?: boolean
  flagged?: boolean
  pending?: boolean
  hasDeliveryNote?: boolean
  hasQuantityMismatch?: boolean
  readyToSubmit?: boolean
  // Document-specific fields
  error_code?: string | null
  ocr_attempts?: Array<any>
  processing_stage?: string
  filename?: string
  uploaded_at?: string
  doc_type?: string | null
  doc_type_confidence?: number
  ocr_error?: string | null
}

interface DocumentListProps {
  invoices: InvoiceListItem[]
  selectedId: string | null
  onSelect: (id: string) => void
  sortBy: 'date' | 'supplier' | 'value' | 'venue' | 'status'
  onSortChange: (sort: 'date' | 'supplier' | 'value' | 'venue' | 'status') => void
  onSupplierClick?: (supplierName: string) => void
  onBatchSubmit?: (invoiceIds: string[]) => void
  onDelete?: (invoiceId: string) => void
  newlyUploadedIds?: Set<string>
  emptyState?: {
    title: string
    description: string
    actionLabel?: string
    onAction?: () => void
  }
}

export function DocumentList({
  invoices,
  selectedId,
  onSelect,
  sortBy,
  onSortChange,
  onSupplierClick,
  onBatchSubmit,
  onDelete,
  newlyUploadedIds,
  emptyState,
}: DocumentListProps) {
  const [showSortDropdown, setShowSortDropdown] = useState(false)
  const [deleteConfirmId, setDeleteConfirmId] = useState<string | null>(null)
  const scrollContainerRef = useRef<HTMLDivElement>(null)
  const dropdownRef = useRef<HTMLDivElement>(null)
  const deleteConfirmCardRef = useRef<HTMLDivElement | null>(null)
  const previousInvoicesLengthRef = useRef(invoices.length)

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setShowSortDropdown(false)
      }
    }

    if (showSortDropdown) {
      document.addEventListener('mousedown', handleClickOutside)
    }

    return () => {
      document.removeEventListener('mousedown', handleClickOutside)
    }
  }, [showSortDropdown])

  // Close delete confirmation on Escape key or click outside
  useEffect(() => {
    const handleEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape' && deleteConfirmId) {
        setDeleteConfirmId(null)
      }
    }

    const handleClickOutside = (event: MouseEvent) => {
      if (deleteConfirmId && deleteConfirmCardRef.current) {
        // Check if click is outside the card with confirmation
        if (!deleteConfirmCardRef.current.contains(event.target as Node)) {
          setDeleteConfirmId(null)
        }
      }
    }

    if (deleteConfirmId) {
      document.addEventListener('keydown', handleEscape)
      // Use mousedown to catch clicks before they propagate
      document.addEventListener('mousedown', handleClickOutside)
    }

    return () => {
      document.removeEventListener('keydown', handleEscape)
      document.removeEventListener('mousedown', handleClickOutside)
    }
  }, [deleteConfirmId])

  const handleSupplierClick = (e: React.MouseEvent, supplierName: string) => {
    e.stopPropagation() // Prevent card selection
    if (onSupplierClick) {
      onSupplierClick(supplierName)
    }
  }

  const handleDeleteClick = (e: React.MouseEvent, invoiceId: string) => {
    e.stopPropagation() // Prevent card selection
    setDeleteConfirmId(invoiceId)
  }

  const handleDeleteConfirm = async (e: React.MouseEvent, invoiceId: string) => {
    e.stopPropagation() // Prevent card selection
    if (onDelete) {
      await onDelete(invoiceId)
      setDeleteConfirmId(null)
    }
  }

  const handleDeleteCancel = (e: React.MouseEvent) => {
    e.stopPropagation() // Prevent card selection
    setDeleteConfirmId(null)
  }

  const handleSortOptionClick = (sort: 'date' | 'supplier' | 'value' | 'venue' | 'status') => {
    onSortChange(sort)
    setShowSortDropdown(false)
  }

  // Auto-scroll to new items (Micro-Automation #1)
  useEffect(() => {
    if (invoices.length > previousInvoicesLengthRef.current && scrollContainerRef.current) {
      // New invoice added - scroll to it smoothly
      const lastCard = scrollContainerRef.current.lastElementChild as HTMLElement
      if (lastCard) {
        setTimeout(() => {
          lastCard.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
          lastCard.classList.add('scroll-target')
          setTimeout(() => lastCard.classList.remove('scroll-target'), 1000)
        }, 100)
      }
    }
    previousInvoicesLengthRef.current = invoices.length
  }, [invoices.length])

  // Auto-scroll to selected item
  useEffect(() => {
    if (selectedId && scrollContainerRef.current) {
      const selectedCard = scrollContainerRef.current.querySelector(`[data-invoice-id="${selectedId}"]`) as HTMLElement
      if (selectedCard) {
        setTimeout(() => {
          selectedCard.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
        }, 100)
      }
    }
  }, [selectedId])

  const formatDate = (dateStr?: string) => {
    if (!dateStr) return 'No date'
    try {
      const date = new Date(dateStr)
      return date.toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' })
    } catch {
      return dateStr
    }
  }

  const formatCurrency = (value?: number) => {
    if (value === undefined || value === null) return '£0.00'
    return new Intl.NumberFormat('en-GB', { style: 'currency', currency: 'GBP' }).format(value)
  }

  // When empty, just show the header and empty list (no empty state message)
  // The empty state message is now shown in the middle column (DocumentDetailPanel)

  // Count ready to submit invoices
  const readyToSubmitCount = invoices.filter((inv) => inv.readyToSubmit).length
  const readyToSubmitIds = invoices.filter((inv) => inv.readyToSubmit).map((inv) => inv.id)

  const handleBatchSubmit = () => {
    if (readyToSubmitCount === 0 || !onBatchSubmit) return
    if (readyToSubmitIds.length > 0) {
      onBatchSubmit(readyToSubmitIds)
    }
  }

  return (
    <div className="invoices-list-column">
      <div className="invoices-list-header">
        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', flex: 1 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <h3 className="invoices-list-title">Documents</h3>
            <div className="dropdown-wrapper" ref={dropdownRef}>
              <button 
                className="sort-button"
                onClick={() => setShowSortDropdown(!showSortDropdown)}
              >
                Sort by: {sortBy === 'date' ? 'Date' : sortBy === 'supplier' ? 'Supplier' : sortBy === 'value' ? 'Value' : sortBy === 'venue' ? 'Venue' : 'Status'}
                <ChevronDown size={14} />
              </button>
              {showSortDropdown && (
                <div className="dropdown-menu">
                  <button className="dropdown-item" onClick={() => handleSortOptionClick('date')}>
                    Date
                  </button>
                  <button className="dropdown-item" onClick={() => handleSortOptionClick('supplier')}>
                    Supplier
                  </button>
                  <button className="dropdown-item" onClick={() => handleSortOptionClick('value')}>
                    Value
                  </button>
                  <button className="dropdown-item" onClick={() => handleSortOptionClick('venue')}>
                    Venue
                  </button>
                  <button className="dropdown-item" onClick={() => handleSortOptionClick('status')}>
                    Status
                  </button>
                </div>
              )}
            </div>
          </div>
          {readyToSubmitCount > 0 && onBatchSubmit && (
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '12px', color: 'var(--text-secondary)' }}>
              <span>{readyToSubmitCount} invoice{readyToSubmitCount !== 1 ? 's' : ''} ready to submit</span>
              <button 
                className="glass-button" 
                style={{ fontSize: '11px', padding: '4px 10px' }}
                onClick={handleBatchSubmit}
              >
                Submit all
              </button>
            </div>
          )}
        </div>
      </div>
      <div className="invoices-list-scrollable" ref={scrollContainerRef}>
        {invoices.map((invoice, index) => {
          // Group by supplier for predictive hover (Micro-Automation #3)
          const supplierGroup = invoice.supplier || 'unknown'
          const invoiceId = String(invoice.id || invoice.docId || index)
          // Use a unique key combining id and status to prevent React key conflicts
          const uniqueKey = `${invoiceId}-${invoice.status}-${index}`
          
          const isDeleteConfirming = deleteConfirmId === invoiceId
          const isSubmitted = invoice.status === 'submitted'
          const isNewlyUploaded = newlyUploadedIds?.has(invoiceId)
          
          return (
            <div
              key={uniqueKey}
              ref={isDeleteConfirming ? (el) => { deleteConfirmCardRef.current = el } : null}
              data-invoice-id={invoiceId}
              data-supplier={supplierGroup}
              className={`invoice-card-new ${selectedId === invoiceId ? 'selected' : ''} supplier-group ${isDeleteConfirming ? 'delete-confirming' : ''} ${isNewlyUploaded ? 'newly-uploaded' : ''}`}
              onClick={(e) => {
                // If in delete confirmation mode, clicking the card cancels it
                if (isDeleteConfirming) {
                  // Cancel confirmation when clicking on card (overlay will stop propagation for its buttons)
                  setDeleteConfirmId(null)
                } else {
                  onSelect(invoiceId)
                }
              }}
              tabIndex={0}
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                  e.preventDefault()
                  if (!isDeleteConfirming) {
                    onSelect(invoiceId)
                  }
                } else if (e.key === 'Escape' && isDeleteConfirming) {
                  e.preventDefault()
                  setDeleteConfirmId(null)
                }
              }}
            >
              {/* Delete button - only show if not submitted */}
              {!isSubmitted && onDelete && (
                <>
                  {!isDeleteConfirming ? (
                    <button
                      className="invoice-card-delete-btn"
                      onClick={(e) => handleDeleteClick(e, invoiceId)}
                      title="Delete invoice"
                      aria-label="Delete invoice"
                    >
                      <Trash2 size={14} />
                    </button>
                  ) : (
                    <div 
                      className="invoice-card-delete-confirm" 
                      onClick={(e) => handleDeleteConfirm(e, invoiceId)}
                    >
                      <button
                        className="invoice-card-delete-close"
                        onClick={(e) => {
                          e.stopPropagation()
                          handleDeleteCancel(e)
                        }}
                        title="Close"
                        aria-label="Close confirmation"
                      >
                        <X size={16} />
                      </button>
                      <div className="invoice-card-delete-confirm-content">
                        <div className="invoice-card-delete-confirm-text">
                          Confirm Delete
                        </div>
                      </div>
                    </div>
                  )}
                </>
              )}
              
              {/* Rectangular card layout - compact and stackable */}
              <div className="invoice-card-rectangular">
                {/* Error State */}
                {invoice.status === 'error' && (
                  <div style={{ padding: '12px', textAlign: 'center' }}>
                    <div style={{ fontSize: '14px', fontWeight: '600', color: 'var(--error)', marginBottom: '8px' }}>
                      Couldn't read this document
                    </div>
                    {invoice.ocr_error && (
                      <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginBottom: '8px' }}>
                        {typeof invoice.ocr_error === 'string' && invoice.ocr_error.length > 100 
                          ? invoice.ocr_error.substring(0, 100) + '...' 
                          : invoice.ocr_error}
                      </div>
                    )}
                    {invoice.error_code && (
                      <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginBottom: '8px' }}>
                        Error: {invoice.error_code}
                      </div>
                    )}
                    <div style={{ display: 'flex', gap: '8px', justifyContent: 'center', marginTop: '12px' }}>
                      <button
                        className="glass-button"
                        style={{ fontSize: '11px', padding: '6px 12px' }}
                        onClick={(e) => {
                          e.stopPropagation()
                          const debugInfo = `doc_id: ${invoice.doc_id || invoice.docId}\nerror_code: ${invoice.error_code || 'unknown'}\nerror: ${invoice.ocr_error || 'none'}`
                          navigator.clipboard.writeText(debugInfo)
                          // Could show toast here
                        }}
                      >
                        Copy debug info
                      </button>
                      <button
                        className="glass-button"
                        style={{ fontSize: '11px', padding: '6px 12px' }}
                        onClick={async (e) => {
                          e.stopPropagation()
                          try {
                            const { retryOCR } = await import('../../lib/api')
                            await retryOCR(invoice.doc_id || invoice.docId || String(invoice.id))
                            // Refresh invoices to show updated status
                            window.location.reload()
                          } catch (err) {
                            console.error('Failed to retry OCR:', err)
                          }
                        }}
                      >
                        Retry OCR
                      </button>
                    </div>
                  </div>
                )}
                
                {/* Processing State */}
                {invoice.status === 'processing' && (
                  <div style={{ padding: '12px', textAlign: 'center' }}>
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px', marginBottom: '8px' }}>
                      <div className="spinner" style={{ width: '16px', height: '16px', borderWidth: '2px' }}></div>
                      <span style={{ fontSize: '13px', fontWeight: '500' }}>Processing</span>
                    </div>
                    {invoice.processing_stage && (
                      <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginBottom: '4px' }}>
                        {invoice.processing_stage}
                      </div>
                    )}
                    {invoice.confidence !== null && invoice.confidence !== undefined && (
                      <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                        Confidence: {Math.round((invoice.confidence <= 1 ? invoice.confidence : invoice.confidence / 100) * 100)}%
                      </div>
                    )}
                  </div>
                )}
                
                {/* Needs Review State */}
                {invoice.status === 'needs_review' && (
                  <div style={{ padding: '12px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
                      <span className="badge badge-needs-review" style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                        <AlertTriangle size={12} />
                        Needs Review
                      </span>
                    </div>
                    <button
                      className="glass-button"
                      style={{ fontSize: '11px', padding: '6px 12px', width: '100%' }}
                      onClick={(e) => {
                        e.stopPropagation()
                        // Open review modal - this would need to be passed as a prop
                        // For now, just select the card
                        onSelect(invoiceId)
                      }}
                    >
                      Open review
                    </button>
                  </div>
                )}
                
                {/* Normal State (ready/scanned/manual) */}
                {invoice.status !== 'error' && invoice.status !== 'processing' && invoice.status !== 'needs_review' && (
                  <>
                    {/* Row 1: Supplier name (top, bold) */}
                    <div className="invoice-card-row-1">
                      <div className="invoice-card-supplier" style={{ fontSize: '15px', fontWeight: '600', flex: 1 }}>
                        {invoice.supplier ? (
                          <button
                            onClick={(e) => handleSupplierClick(e, invoice.supplier!)}
                            className="invoice-card-supplier-link"
                            title="View supplier details"
                            style={{ fontSize: '15px', fontWeight: '600', textAlign: 'left', width: '100%' }}
                          >
                            {invoice.supplier}
                          </button>
                        ) : (
                          'Unknown Supplier'
                        )}
                      </div>
                    </div>

                    {/* Row 2: Total value (prominent) */}
                    <div className="invoice-card-row-2">
                      <div className="invoice-card-value" style={{ fontSize: '18px', fontWeight: '700', color: 'var(--accent-green)' }}>
                        {formatCurrency(invoice.totalValue)}
                      </div>
                    </div>
                  </>
                )}

                {/* Row 3: Site/Venue and Date (only show for non-error/processing states) */}
                {invoice.status !== 'error' && invoice.status !== 'processing' && (
                  <div className="invoice-card-row-3" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '12px', color: 'var(--text-muted)', marginTop: '6px', marginBottom: '8px' }}>
                    <div className="invoice-card-venue">
                      Site: {invoice.venue || 'Main Restaurant'}
                    </div>
                    <div className="invoice-card-date">
                      {formatDate(invoice.invoiceDate || invoice.uploaded_at)}
                    </div>
                  </div>
                )}

                {/* Row 4: Status badges - Paired/Unpaired, Scanned/Manual, Issues, OCR */}
                <div className="invoice-card-row-4" style={{ display: 'flex', gap: '6px', flexWrap: 'wrap', alignItems: 'center', marginTop: '8px' }}>
                  {/* Status: Paired/Unpaired with delivery note indicator */}
                  {invoice.matched || invoice.hasDeliveryNote ? (
                    <span className="badge badge-matched" style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                      <Package size={10} />
                      Paired
                    </span>
                  ) : (
                    <span className="badge badge-unmatched" style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                      <AlertCircle size={10} />
                      Unpaired
                    </span>
                  )}
                  
                  {/* Method: Scanned/Manual/Processing/Error */}
                  {invoice.status === 'manual' ? (
                    <span className="badge badge-manual">Manual</span>
                  ) : invoice.status === 'processing' ? (
                    <span className="badge badge-processing">Processing</span>
                  ) : invoice.status === 'error' ? (
                    <span className="badge badge-error">Error</span>
                  ) : (
                    <span className="badge badge-scanned">Scanned</span>
                  )}
                  
                  {/* Needs Review badge - shows when validation errors detected */}
                  {invoice.dbStatus === 'needs_review' && (
                    <span 
                      className="badge badge-needs-review" 
                      style={{ display: 'flex', alignItems: 'center', gap: '4px' }}
                      title="Owlin flagged this invoice because totals don't quite add up. Please double-check."
                    >
                      <AlertTriangle size={10} />
                      Needs Review
                    </span>
                  )}
                  
                  {/* Quantity Mismatch indicator - show if paired but has quantity issues */}
                  {invoice.matched && invoice.hasQuantityMismatch && (
                    <span 
                      className="badge badge-flagged" 
                      style={{ display: 'flex', alignItems: 'center', gap: '4px' }}
                      title="Quantity mismatch between invoice and delivery note"
                    >
                      <AlertTriangle size={10} />
                      Qty Mismatch
                    </span>
                  )}
                  
                  {/* Issues/Flagged indicator */}
                  {(invoice.issuesCount && invoice.issuesCount > 0) || invoice.flagged ? (
                    <span className="badge badge-flagged">
                      Issues: {invoice.issuesCount || (invoice.flagged ? 1 : 0)}
                    </span>
                  ) : null}
                  
                  {/* OCR confidence score (only if scanned) or Manual badge (for manual invoices) */}
                  {invoice.status === 'scanned' && invoice.confidence !== undefined ? (
                    <span className="badge badge-ocr" style={{ fontSize: '10px' }}>
                      OCR: {typeof invoice.confidence === 'number' && invoice.confidence <= 1 
                        ? Math.round(invoice.confidence * 100) 
                        : Math.round(invoice.confidence)}%
                    </span>
                  ) : invoice.status === 'manual' ? (
                    <span className="badge badge-manual-indicator" style={{ fontSize: '10px' }}>
                      Manual
                    </span>
                  ) : null}
                  
                  {/* Validation badge - shows if invoice has been numerically validated */}
                  {(invoice as any).validation?.badge && (
                    <span 
                      className={`badge badge-validation badge-validation-${(invoice as any).validation.badge.color}`}
                      style={{ fontSize: '10px' }}
                      title={(invoice as any).validation.badge.tooltip}
                    >
                      {(invoice as any).validation.badge.label}
                    </span>
                  )}
                </div>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}

