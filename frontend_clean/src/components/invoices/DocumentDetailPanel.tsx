import { FileText, ExternalLink, CheckCircle2, Circle, ChevronDown, ChevronUp, Package, Check, X, AlertTriangle, Unlink, Loader2, Edit, MoreVertical, Plus, Trash2, CheckCircle, Eye } from 'lucide-react'
import { useState, useEffect, useRef } from 'react'
import type { LineItem } from '../../lib/upload'
import { fetchPairingSuggestions, linkDeliveryNoteToInvoice, fetchDeliveryNoteDetails, fetchInvoiceSuggestionsForDN, validatePair, unpairDeliveryNoteFromInvoice, fetchPairedInvoicesForDeliveryNote, updateManualInvoice, type PairingSuggestion } from '../../lib/api'
import { PairingPreviewModal } from './PairingPreviewModal'
import { useToast } from '../common/Toast'
import { matchLineItems } from '../../lib/lineItemMatcher'
import type { DiscrepancyContext } from './SmartDiscrepancyWidget'
import { InvoiceVisualizer } from './InvoiceVisualizer'
import './DocumentDetailPanel.css'

export interface DeliveryNote {
  id: string
  noteNumber?: string
  date?: string
  lineItems?: LineItem[]
}

export interface InvoiceDetail {
  id: string
  docId?: string  // doc_id from backend - used for image serving (from normalizeInvoice)
  documentId?: string  // Alternative name for docId (backward compatibility)
  invoiceNumber?: string
  supplier?: string
  date?: string
  venue?: string
  value?: number
  subtotal?: number
  vat?: number
  status: 'scanned' | 'manual'
  matched?: boolean
  flagged?: boolean
  deliveryNote?: DeliveryNote
  lineItems?: LineItem[]
  sourceFilename?: string
  confidence?: number
}

interface DocumentDetailPanelProps {
  invoice: InvoiceDetail | null
  selectedDNId?: string | null
  onLinkDeliveryNote: () => void
  onCreateDeliveryNote: () => void
  onChangeDeliveryNote: () => void
  onOpenPDF?: () => void
  onViewOCRDetails?: () => void
  onSaveNote?: () => void
  noteText?: string
  onNoteTextChange?: (text: string) => void
  savingNote?: boolean
  onSubmit?: (invoiceId: string) => void
  canSubmit?: boolean
  isSubmitting?: boolean
  hasIssues?: boolean
  onPairSuccess?: () => void
  isEmptyState?: boolean
  onUploadClick?: () => void
  onNewManualInvoice?: () => void
  onSelectInvoice?: (invoiceId: string) => void
  manualPairingWorkflowActive?: boolean
  topSuggestion?: PairingSuggestion | null
  onPairWithSuggestion?: (deliveryNoteId: string) => void
  onEditInvoice?: (invoiceId: string) => void
  onEditDeliveryNote?: (deliveryNoteId: string) => void
  highlightContext?: DiscrepancyContext | null
  onHighlightComplete?: () => void
  onInvoiceUpdated?: () => void
}

export function DocumentDetailPanel({
  invoice,
  selectedDNId,
  onLinkDeliveryNote,
  onCreateDeliveryNote,
  onChangeDeliveryNote,
  onOpenPDF,
  onViewOCRDetails,
  onSaveNote,
  noteText = '',
  onNoteTextChange,
  savingNote = false,
  onSubmit,
  canSubmit = false,
  isSubmitting = false,
  hasIssues = false,
  onPairSuccess,
  isEmptyState = false,
  onUploadClick,
  onNewManualInvoice,
  onSelectInvoice,
  manualPairingWorkflowActive = false,
  topSuggestion = null,
  onPairWithSuggestion,
  onEditInvoice,
  onEditDeliveryNote,
  highlightContext,
  onHighlightComplete,
  onInvoiceUpdated,
}: DocumentDetailPanelProps) {
  const toast = useToast()
  const [lineItemsExpanded, setLineItemsExpanded] = useState(false)
  const [dnWidgetExpanded, setDnWidgetExpanded] = useState(false)
  const [invoiceWidgetExpanded, setInvoiceWidgetExpanded] = useState(false)
  const [hoveredLineItemIndex, setHoveredLineItemIndex] = useState<number | null>(null)
  const [showVisualizer, setShowVisualizer] = useState(false)
  const lineItemsRef = useRef<HTMLDivElement>(null)
  const highlightedLineItemRef = useRef<HTMLTableRowElement | null>(null)
  const [pairingSuggestions, setPairingSuggestions] = useState<PairingSuggestion[]>([])
  const [loadingSuggestions, setLoadingSuggestions] = useState(false)
  const [pairing, setPairing] = useState<string | null>(null)
  const [pairingInvoiceId, setPairingInvoiceId] = useState<string | null>(null)
  const [unpairing, setUnpairing] = useState(false)
  const [showUnpairConfirm, setShowUnpairConfirm] = useState(false)
  
  // Delivery note detail state
  const [deliveryNoteDetail, setDeliveryNoteDetail] = useState<any>(null)
  const [deliveryNoteError, setDeliveryNoteError] = useState<string | null>(null)
  const [loadingDN, setLoadingDN] = useState(false)
  const [invoiceSuggestions, setInvoiceSuggestions] = useState<any[]>([])
  const [loadingInvoiceSuggestions, setLoadingInvoiceSuggestions] = useState(false)
  const [pairedInvoices, setPairedInvoices] = useState<any[]>([])
  const [loadingPairedInvoices, setLoadingPairedInvoices] = useState(false)
  
  // Pairing preview modal state
  const [previewModalOpen, setPreviewModalOpen] = useState(false)
  const [previewDeliveryNoteId, setPreviewDeliveryNoteId] = useState<string | null>(null)
  const [previewInvoiceId, setPreviewInvoiceId] = useState<string | null>(null)
  const [previewValidation, setPreviewValidation] = useState<any>(null)
  
  // Error state for pairing operations
  const [pairingError, setPairingError] = useState<string | null>(null)
  const [invoicePairingError, setInvoicePairingError] = useState<string | null>(null)
  
  // Inline editing state
  const [isEditing, setIsEditing] = useState(false)
  const [editableLineItems, setEditableLineItems] = useState<Array<{
    description: string
    qty: number
    unit: string
    price: number
    total: number
    dnQty?: number
  }>>([])
  const [savingEdit, setSavingEdit] = useState(false)

  const formatCurrency = (value?: number) => {
    if (value === undefined || value === null) return '£0.00'
    return new Intl.NumberFormat('en-GB', { style: 'currency', currency: 'GBP' }).format(value)
  }

  const formatDate = (dateStr?: string) => {
    if (!dateStr) return 'No date'
    try {
      const date = new Date(dateStr)
      return date.toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' })
    } catch {
      return dateStr
    }
  }

  // Initialize editable line items from invoice data
  const handleStartEdit = () => {
    if (!invoice || !invoice.lineItems) return
    
    // Get DN quantities from delivery note if available
    const dnLineItems = invoice.deliveryNote?.lineItems || []
    const matchedItems = invoice.lineItems.map((item) => {
      // Try to find matching DN item
      const dnItem = dnLineItems.find(dn => {
        const itemDesc = (item.description || '').toLowerCase()
        const dnDesc = (dn.description || '').toLowerCase()
        return itemDesc.includes(dnDesc) || dnDesc.includes(itemDesc)
      })
      
      return {
        description: item.description || 'Item',
        qty: Math.round(item.qty || 0), // Ensure integer
        unit: item.uom || item.unit || '',
        price: item.unitPrice || 0,
        total: item.total || 0,
        dnQty: dnItem ? Math.round(dnItem.qty || 0) : undefined, // Ensure integer
      }
    })
    
    setEditableLineItems(matchedItems)
    setIsEditing(true)
  }

  // Update a line item field
  const updateEditableLineItem = (index: number, field: string, value: string | number) => {
    const updated = [...editableLineItems]
    
    // Ensure quantity is always an integer
    if (field === 'qty' || field === 'dnQty') {
      updated[index] = { ...updated[index], [field]: Math.round(Number(value)) || 0 }
    } else {
      updated[index] = { ...updated[index], [field]: value }
    }
    
    // Auto-calculate total if qty or price changes
    if (field === 'qty' || field === 'price') {
      const qty = field === 'qty' ? Math.round(Number(value)) : (updated[index].qty || 0)
      const price = field === 'price' ? Number(value) : (updated[index].price || 0)
      updated[index].total = qty * price
    }
    
    setEditableLineItems(updated)
  }

  // Increment/decrement quantity or price
  const adjustValue = (index: number, field: 'qty' | 'price', delta: number) => {
    const updated = [...editableLineItems]
    const currentValue = updated[index][field] || 0
    const newValue = Math.max(0, currentValue + delta)
    updateEditableLineItem(index, field, newValue)
  }

  // Add a new line item
  const addLineItem = () => {
    setEditableLineItems([...editableLineItems, {
      description: '',
      qty: 0,
      unit: '', // Preserve unit field in data but don't show in UI
      price: 0,
      total: 0,
      dnQty: undefined,
    }])
  }

  // Remove a line item
  const removeLineItem = (index: number) => {
    if (editableLineItems.length > 1) {
      setEditableLineItems(editableLineItems.filter((_, i) => i !== index))
    }
  }

  // Calculate totals from editable line items
  const calculateTotals = () => {
    const subtotal = editableLineItems.reduce((sum, item) => sum + (item.total || 0), 0)
    const vat = subtotal * 0.2 // 20% VAT
    const total = subtotal + vat
    return { subtotal, vat, total }
  }

  // Save edited invoice
  const handleSaveEdit = async () => {
    if (!invoice) return
    
    setSavingEdit(true)
    try {
      const { subtotal, vat, total } = calculateTotals()
      
      // Filter out empty line items
      const validLineItems = editableLineItems.filter(item => item.description.trim() !== '')
      
      // Save the invoice with updated data
      await updateManualInvoice(invoice.id, {
        supplier: invoice.supplier || '',
        invoiceNumber: invoice.invoiceNumber || '',
        date: invoice.date || new Date().toISOString().split('T')[0],
        venue: invoice.venue || 'Waterloo',
        lineItems: validLineItems.map(item => ({
          description: item.description,
          qty: Math.round(item.qty || 0), // Ensure integer
          unit: item.unit || '', // Preserve unit if it exists
          price: item.price || 0,
          total: item.total || 0,
        })),
        subtotal,
        vat,
        total,
      })
      
      toast.success('Invoice updated successfully')
      
      // Clear editable state
      setIsEditing(false)
      setEditableLineItems([])
      
      // Refresh invoice data - this will update the displayed invoice
      if (onInvoiceUpdated) {
        await onInvoiceUpdated()
      }
    } catch (err) {
      console.error('Failed to update invoice:', err)
      toast.error(err instanceof Error ? err.message : 'Failed to update invoice')
    } finally {
      setSavingEdit(false)
    }
  }

  // Cancel editing
  const handleCancelEdit = () => {
    setIsEditing(false)
    setEditableLineItems([])
  }

  // Reset editing state when invoice changes
  useEffect(() => {
    if (invoice) {
      setIsEditing(false)
      setEditableLineItems([])
    }
  }, [invoice?.id])

  // Handle highlighting when highlightContext changes
  useEffect(() => {
    if (!highlightContext || !invoice) return

    let cleanupTimeouts: NodeJS.Timeout[] = []

    const performHighlight = () => {
      if (highlightContext.section === 'lineItems' && invoice.lineItems) {
        // Auto-expand line items if collapsed - use functional update
        setLineItemsExpanded(prev => {
          const needsExpansion = !prev
          if (needsExpansion) {
            // Wait for expansion, then scroll and highlight
            const delay = 400
            const timeoutId = setTimeout(() => {
              if (lineItemsRef.current) {
                lineItemsRef.current.scrollIntoView({ behavior: 'smooth', block: 'center' })
              }
              
              // Find and highlight matching line items
              if (highlightContext.lineItemDescription) {
                const rows = document.querySelectorAll('[data-line-item-description]')
                rows.forEach((row) => {
                  const desc = row.getAttribute('data-line-item-description')?.toLowerCase() || ''
                  const targetDesc = highlightContext.lineItemDescription?.toLowerCase() || ''
                  if (desc.includes(targetDesc) || targetDesc.includes(desc)) {
                    row.classList.add('line-item-pulse')
                    highlightedLineItemRef.current = row as HTMLTableRowElement
                  }
                })
              } else {
                // Highlight all line items if no specific item
                const rows = document.querySelectorAll('[data-line-item-description]')
                if (rows.length > 0) {
                  rows[0].classList.add('line-item-pulse')
                  highlightedLineItemRef.current = rows[0] as HTMLTableRowElement
                }
              }
            }, delay)
            cleanupTimeouts.push(timeoutId)
          } else {
            // Already expanded, highlight immediately
            const timeoutId = setTimeout(() => {
              if (lineItemsRef.current) {
                lineItemsRef.current.scrollIntoView({ behavior: 'smooth', block: 'center' })
              }
              
              if (highlightContext.lineItemDescription) {
                const rows = document.querySelectorAll('[data-line-item-description]')
                rows.forEach((row) => {
                  const desc = row.getAttribute('data-line-item-description')?.toLowerCase() || ''
                  const targetDesc = highlightContext.lineItemDescription?.toLowerCase() || ''
                  if (desc.includes(targetDesc) || targetDesc.includes(desc)) {
                    row.classList.add('line-item-pulse')
                    highlightedLineItemRef.current = row as HTMLTableRowElement
                  }
                })
              } else {
                const rows = document.querySelectorAll('[data-line-item-description]')
                if (rows.length > 0) {
                  rows[0].classList.add('line-item-pulse')
                  highlightedLineItemRef.current = rows[0] as HTMLTableRowElement
                }
              }
            }, 100)
            cleanupTimeouts.push(timeoutId)
          }
          return true // Always expand
        })
      } else if (highlightContext.section === 'deliveryNote') {
        // Highlight delivery note section
        setDnWidgetExpanded(prev => {
          const needsExpansion = !prev
          if (needsExpansion) {
            const delay = 400
            const timeoutId = setTimeout(() => {
              const dnSection = document.querySelector('[data-delivery-note-section]')
              if (dnSection) {
                dnSection.scrollIntoView({ behavior: 'smooth', block: 'center' })
                dnSection.classList.add('section-pulse')
              }
            }, delay)
            cleanupTimeouts.push(timeoutId)
          } else {
            const timeoutId = setTimeout(() => {
              const dnSection = document.querySelector('[data-delivery-note-section]')
              if (dnSection) {
                dnSection.scrollIntoView({ behavior: 'smooth', block: 'center' })
                dnSection.classList.add('section-pulse')
              }
            }, 100)
            cleanupTimeouts.push(timeoutId)
          }
          return true // Always expand
        })
      }
      
      // Clear highlight after 3 seconds
      const clearTimeoutId = setTimeout(() => {
        document.querySelectorAll('.line-item-pulse').forEach(el => el.classList.remove('line-item-pulse'))
        document.querySelectorAll('.section-pulse').forEach(el => el.classList.remove('section-pulse'))
        if (onHighlightComplete) {
          onHighlightComplete()
        }
      }, 3000)
      cleanupTimeouts.push(clearTimeoutId)
    }

    const timeoutId = setTimeout(performHighlight, 100)
    cleanupTimeouts.push(timeoutId)

    return () => {
      cleanupTimeouts.forEach(id => clearTimeout(id))
    }
  }, [highlightContext, invoice?.id, onHighlightComplete])

  const formatDateTime = (dateStr?: string) => {
    if (!dateStr) return 'No date/time'
    try {
      const date = new Date(dateStr)
      return date.toLocaleString('en-GB', { 
        day: 'numeric', 
        month: 'short', 
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
      })
    } catch {
      return dateStr
    }
  }

  // Fetch pairing suggestions when invoice changes (but not when widget expands to avoid double fetching)
  useEffect(() => {
    if (invoice && !invoice.deliveryNote && pairingSuggestions.length === 0 && !loadingSuggestions) {
      // Only auto-fetch on invoice change, not on widget expand
      // This prevents double fetching when user clicks the button
    } else if (invoice?.deliveryNote) {
      setPairingSuggestions([])
      setDnWidgetExpanded(false)
    }
  }, [invoice?.id, invoice?.deliveryNote])

  // Fetch delivery note details when selectedDNId changes
  useEffect(() => {
    if (selectedDNId) {
      setLoadingDN(true)
      setDeliveryNoteDetail(null) // Clear previous data while loading
      setDeliveryNoteError(null) // Clear previous errors
      setPairedInvoices([])
      
      // Fetch delivery note details
      fetchDeliveryNoteDetails(selectedDNId)
        .then((details) => {
          // Ensure supplier is set, even if missing from response
          const detailsWithSupplier = {
            ...details,
            supplier: details.supplier || 'Unknown Supplier',
            noteNumber: details.noteNumber || details.note_number || details.deliveryNo || `DN-${selectedDNId.slice(0, 8)}`,
          }
          setDeliveryNoteDetail(detailsWithSupplier)
          
          // Fetch invoice suggestions and paired invoices in parallel
          return Promise.all([
            fetchInvoiceSuggestionsForDN(selectedDNId),
            fetchPairedInvoicesForDeliveryNote(selectedDNId)
          ])
        })
        .then(([suggestions, paired]) => {
          const invoiceSuggestionsList = suggestions.suggestions || []
          setInvoiceSuggestions(invoiceSuggestionsList)
          setPairedInvoices(paired || [])
          // Auto-expand widget if we have suggestions and no paired invoices
          if (invoiceSuggestionsList.length > 0 && (!paired || paired.length === 0)) {
            setInvoiceWidgetExpanded(true)
          }
        })
        .catch((err) => {
          const errorMsg = err instanceof Error ? err.message : 'Unknown error'
          console.error('Failed to fetch delivery note details:', err)
          // Set error state - don't create fallback data
          setDeliveryNoteDetail(null)
          setDeliveryNoteError(`Failed to load delivery note: ${errorMsg}`)
        })
        .finally(() => {
          setLoadingDN(false)
        })
    } else {
      setDeliveryNoteDetail(null)
      setDeliveryNoteError(null)
      setInvoiceSuggestions([])
      setPairedInvoices([])
      setInvoiceWidgetExpanded(false)
      setInvoicePairingError(null)
      setPairingInvoiceId(null)
    }
  }, [selectedDNId])

  // Handle pairing with a delivery note (one-click action)
  const handlePairWithDN = async (dnId: string) => {
    if (!invoice) return
    
    setPairingError(null)
    
    // Validate before pairing
    try {
      setPairing(dnId)
      const validation = await validatePair(invoice.id, dnId)
      
      // If validation shows warnings or low match score, show preview modal
      if (!validation.isValid || validation.matchScore < 0.8 || validation.warnings.length > 0) {
        setPairing(null)
        setPreviewDeliveryNoteId(dnId)
        setPreviewValidation(validation)
        setPreviewModalOpen(true)
        return
      }
      
      // If validation passes, proceed with pairing directly
      const result = await linkDeliveryNoteToInvoice(invoice.id, dnId)
      
      // Show success toast
      if (result.warnings && result.warnings.length > 0) {
        toast.warning(`Pairing completed with warnings: ${result.warnings.slice(0, 2).join(', ')}`)
      } else {
        toast.success('Invoice paired with delivery note successfully')
      }
      
      // Clear pairing suggestions since invoice is now paired
      setPairingSuggestions([])
      
      // Refresh pairing suggestions (will return empty since invoice is now paired)
      try {
        const response = await fetchPairingSuggestions(invoice.id)
        setPairingSuggestions(response.suggestions || [])
      } catch (err) {
        // Ignore errors when refreshing - invoice is paired so suggestions aren't critical
        console.debug('Failed to refresh pairing suggestions after pairing:', err)
      }
      
      // Notify parent to refresh invoice detail with warnings
      if (onPairSuccess) {
        onPairSuccess(result.warnings)
      } else {
        // Fallback: trigger refresh via onLinkDeliveryNote
        onLinkDeliveryNote()
      }
    } catch (err) {
      console.error('Failed to validate or pair delivery note:', err)
      const errorMessage = err instanceof Error ? err.message : 'Failed to pair delivery note'
      setPairingError(errorMessage)
      toast.error(errorMessage)
    } finally {
      setPairing(null)
    }
  }
  
  // Handle unpairing
  const handleUnpair = async () => {
    if (!invoice) return
    
    setUnpairing(true)
    setPairingError(null)
    
    try {
      await unpairDeliveryNoteFromInvoice(invoice.id)
      toast.success('Invoice unpaired from delivery note successfully')
      
      // Refresh pairing suggestions after unpairing
      try {
        const response = await fetchPairingSuggestions(invoice.id)
        setPairingSuggestions(response.suggestions || [])
        // Auto-expand widget if we have suggestions
        if (response.suggestions && response.suggestions.length > 0) {
          setDnWidgetExpanded(true)
        }
      } catch (err) {
        console.error('Failed to refresh pairing suggestions after unpairing:', err)
      }
      
      // Notify parent to refresh invoice detail
      if (onPairSuccess) {
        onPairSuccess()
      } else {
        onLinkDeliveryNote()
      }
      
      setShowUnpairConfirm(false)
    } catch (err) {
      console.error('Failed to unpair delivery note:', err)
      const errorMessage = err instanceof Error ? err.message : 'Failed to unpair delivery note'
      setPairingError(errorMessage)
      toast.error(errorMessage)
    } finally {
      setUnpairing(false)
    }
  }
  
  // Handle confirmation from preview modal
  const handlePreviewConfirm = async () => {
    // The modal handles the actual pairing, we just need to refresh
    if (onPairSuccess) {
      onPairSuccess()
    } else {
      onLinkDeliveryNote()
    }
    
    // If we're pairing from DN side, refresh the DN details
    if (selectedDNId && previewInvoiceId) {
      try {
        const [suggestions, paired] = await Promise.all([
          fetchInvoiceSuggestionsForDN(selectedDNId),
          fetchPairedInvoicesForDeliveryNote(selectedDNId)
        ])
        setInvoiceSuggestions(suggestions.suggestions || [])
        setPairedInvoices(paired || [])
        // Clear suggestions since we're now paired
        if (paired && paired.length > 0) {
          setInvoiceSuggestions([])
          setInvoiceWidgetExpanded(false)
        }
      } catch (err) {
        console.error('Failed to refresh delivery note details after pairing:', err)
      }
    }
    
    setPreviewModalOpen(false)
    setPreviewDeliveryNoteId(null)
    setPreviewInvoiceId(null)
  }

  // Handle clicking "Link Delivery Note" - expand widget and show recommendations, or open modal
  const handleLinkDeliveryNoteClick = async () => {
    if (!invoice?.deliveryNote) {
      // First, try to fetch suggestions
      setLoadingSuggestions(true)
      try {
        const response = await fetchPairingSuggestions(invoice.id)
        const suggestions = response.suggestions || []
        setPairingSuggestions(suggestions)
        
        // If we have suggestions, expand the widget to show them
        if (suggestions.length > 0) {
          setDnWidgetExpanded(true)
        } else {
          // If no suggestions, open the modal to browse all delivery notes
          onLinkDeliveryNote()
        }
      } catch (err) {
        console.error('Failed to fetch pairing suggestions:', err)
        setPairingSuggestions([])
        // On error, open the modal to browse all delivery notes
        onLinkDeliveryNote()
      } finally {
        setLoadingSuggestions(false)
      }
    } else {
      // If already paired, just open the modal
      onLinkDeliveryNote()
    }
  }

  // Handle clicking "Link Invoice" from DN side - expand widget and show recommendations
  const handleLinkInvoiceClick = async () => {
    if (!selectedDNId) return
    
    if (pairedInvoices.length === 0) {
      // First, try to fetch suggestions if we don't have them
      if (invoiceSuggestions.length === 0) {
        setLoadingInvoiceSuggestions(true)
        try {
          const response = await fetchInvoiceSuggestionsForDN(selectedDNId)
          const suggestions = response.suggestions || []
          setInvoiceSuggestions(suggestions)
          
          // If we have suggestions, expand the widget to show them
          if (suggestions.length > 0) {
            setInvoiceWidgetExpanded(true)
          }
        } catch (err) {
          console.error('Failed to fetch invoice suggestions:', err)
          setInvoiceSuggestions([])
        } finally {
          setLoadingInvoiceSuggestions(false)
        }
      } else {
        // We already have suggestions, just expand the widget
        setInvoiceWidgetExpanded(true)
      }
    }
  }

  // Handle pairing DN with an invoice (from DN side)
  const handlePairWithInvoice = async (invoiceId: string) => {
    if (!selectedDNId) return
    
    setInvoicePairingError(null)
    
    // Validate before pairing
    try {
      setPairingInvoiceId(invoiceId)
      const validation = await validatePair(invoiceId, selectedDNId)
      
      // If validation shows warnings or low match score, show preview modal
      if (!validation.isValid || validation.matchScore < 0.8 || validation.warnings.length > 0) {
        setPairingInvoiceId(null)
        setPreviewInvoiceId(invoiceId)
        setPreviewDeliveryNoteId(selectedDNId)
        setPreviewValidation(validation)
        setPreviewModalOpen(true)
        return
      }
      
      // If validation passes, proceed with pairing directly
      const result = await linkDeliveryNoteToInvoice(invoiceId, selectedDNId)
      
      // Show success toast
      if (result.warnings && result.warnings.length > 0) {
        toast.warning(`Pairing completed with warnings: ${result.warnings.slice(0, 2).join(', ')}`)
      } else {
        toast.success('Delivery note paired with invoice successfully')
      }
      
      // Refresh the delivery note details to show the paired invoice
      if (onPairSuccess) {
        onPairSuccess()
      }
      
      // Refresh paired invoices list
      try {
        const paired = await fetchPairedInvoicesForDeliveryNote(selectedDNId)
        setPairedInvoices(paired || [])
        // Clear suggestions since we're now paired
        setInvoiceSuggestions([])
        setInvoiceWidgetExpanded(false)
      } catch (err) {
        console.error('Failed to refresh paired invoices:', err)
      }
    } catch (err) {
      console.error('Failed to validate or pair invoice:', err)
      const errorMessage = err instanceof Error ? err.message : 'Failed to pair invoice'
      setInvoicePairingError(errorMessage)
      toast.error(errorMessage)
    } finally {
      setPairingInvoiceId(null)
    }
  }

  // Calculate totals from line items if invoice.totalValue is missing or zero
  const calculatedSubtotal = invoice?.lineItems?.reduce(
    (sum, item) => sum + (item.total || 0),
    0
  ) || 0

  const calculatedVat = calculatedSubtotal * 0.2 // 20% VAT
  const calculatedTotal = calculatedSubtotal + calculatedVat

  // Use invoice values if available and non-zero, otherwise use calculated
  // Note: InvoiceDetail may have 'value' for backward compatibility, but prefer totalValue
  const invoiceTotal = invoice?.value || 0
  const displayTotal = (invoiceTotal > 0) ? invoiceTotal : calculatedTotal
  const displaySubtotal = (invoice as any)?.subtotal && (invoice as any).subtotal > 0 ? (invoice as any).subtotal : calculatedSubtotal
  const displayVat = (invoice as any)?.vat && (invoice as any).vat > 0 ? (invoice as any).vat : calculatedVat

  // Show delivery note detail view if DN is selected
  if (selectedDNId) {
    // Show error state if delivery note failed to load
    if (deliveryNoteError) {
      return (
        <div className="document-detail-panel">
          <div className="detail-card" style={{ padding: '24px', textAlign: 'center' }}>
            <AlertTriangle size={48} style={{ color: 'var(--accent-red)', marginBottom: '16px' }} />
            <h3 style={{ marginBottom: '8px', color: 'var(--text-primary)' }}>Error Loading Delivery Note</h3>
            <p style={{ color: 'var(--text-secondary)', marginBottom: '16px' }}>{deliveryNoteError}</p>
            <button
              className="glass-button"
              onClick={async () => {
                setDeliveryNoteError(null)
                setLoadingDN(true)
                setDeliveryNoteDetail(null)
                
                try {
                  const details = await fetchDeliveryNoteDetails(selectedDNId)
                  if (!details) {
                    throw new Error('Delivery note not found')
                  }
                  const detailsWithSupplier = {
                    ...details,
                    supplier: details.supplier || 'Unknown Supplier',
                    noteNumber: details.noteNumber || details.note_number || details.deliveryNo || `DN-${selectedDNId.slice(0, 8)}`,
                  }
                  setDeliveryNoteDetail(detailsWithSupplier)
                  
                  const [suggestions, paired] = await Promise.all([
                    fetchInvoiceSuggestionsForDN(selectedDNId),
                    fetchPairedInvoicesForDeliveryNote(selectedDNId)
                  ])
                  setInvoiceSuggestions(suggestions.suggestions || [])
                  setPairedInvoices(paired || [])
                } catch (err) {
                  const errorMsg = err instanceof Error ? err.message : 'Unknown error'
                  setDeliveryNoteError(`Failed to load delivery note: ${errorMsg}`)
                } finally {
                  setLoadingDN(false)
                }
              }}
            >
              Retry
            </button>
          </div>
        </div>
      )
    }
    
    // Show loading state
    if (loadingDN || !deliveryNoteDetail) {
      return (
        <div className="document-detail-panel">
          <div className="detail-card" style={{ padding: '24px', textAlign: 'center' }}>
            <Loader2 size={32} className="spinner" style={{ animation: 'spin 1s linear infinite', marginBottom: '16px' }} />
            <p style={{ color: 'var(--text-secondary)' }}>Loading delivery note details...</p>
          </div>
        </div>
      )
    }
    
    // Show delivery note detail (we know deliveryNoteDetail exists here)
    const lineItemsCount = deliveryNoteDetail.lineItems?.length || 0
    const isPaired = pairedInvoices.length > 0

    return (
      <div className="invoices-detail-column invoices-detail-column-selected">
        {/* Delivery Note Header Card - Enhanced to match invoice style */}
        <div className="detail-card document-header-card">
          <div className="document-header-left">
            <div className="document-header-supplier" style={{ fontSize: '28px', fontWeight: '700', marginBottom: '4px' }}>
              <Package size={24} style={{ marginRight: '8px', display: 'inline-block', verticalAlign: 'middle' }} />
              {deliveryNoteDetail.supplier || 'Unknown Supplier'}
            </div>
            <div className="document-header-meta">
              <span>{deliveryNoteDetail.noteNumber || `DN-${selectedDNId.slice(0, 8)}`}</span>
              <span>·</span>
              <span>{formatDate(deliveryNoteDetail.date)}</span>
              {deliveryNoteDetail.venue && (
                <>
                  <span>·</span>
                  <span>{deliveryNoteDetail.venue}</span>
                </>
              )}
            </div>
            <div style={{ display: 'flex', gap: '8px', marginTop: '12px', flexWrap: 'wrap' }}>
              {isPaired ? (
                <span className="badge badge-matched">Paired</span>
              ) : (
                <span className="badge badge-unmatched">Unpaired</span>
              )}
              {lineItemsCount > 0 && (
                <span className="badge" style={{ background: 'rgba(255, 255, 255, 0.1)', color: 'var(--text-muted)' }}>
                  {lineItemsCount} item{lineItemsCount !== 1 ? 's' : ''}
                </span>
              )}
            </div>
          </div>
        </div>

        {/* Delivery Details Card */}
        <div className="detail-card" style={{ marginTop: '12px' }}>
          <h3 className="detail-card-title">Delivery Details</h3>
          <div className="detail-card-content">
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px', fontSize: '13px' }}>
              <div>
                <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginBottom: '4px', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Delivery Date</div>
                <div style={{ fontWeight: '600', color: 'var(--text-primary)' }}>
                  {formatDate(deliveryNoteDetail.date)}
                </div>
              </div>
              {deliveryNoteDetail.timeWindow && (
                <div>
                  <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginBottom: '4px', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Time of Delivery</div>
                  <div style={{ fontWeight: '600', color: 'var(--text-primary)' }}>
                    {deliveryNoteDetail.timeWindow}
                  </div>
                </div>
              )}
              {deliveryNoteDetail.driver && (
                <div>
                  <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginBottom: '4px', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Driver Name</div>
                  <div style={{ fontWeight: '600', color: 'var(--text-primary)' }}>
                    {deliveryNoteDetail.driver}
                  </div>
                </div>
              )}
              {deliveryNoteDetail.vehicle && (
                <div>
                  <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginBottom: '4px', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Number Plate</div>
                  <div style={{ fontWeight: '600', color: 'var(--text-primary)' }}>
                    {deliveryNoteDetail.vehicle}
                  </div>
                </div>
              )}
              {deliveryNoteDetail.venue && (
                <div>
                  <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginBottom: '4px', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Site/Venue</div>
                  <div style={{ fontWeight: '600', color: 'var(--text-primary)' }}>
                    {deliveryNoteDetail.venue}
                  </div>
                </div>
              )}
              <div>
                <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginBottom: '4px', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Line Items</div>
                <div style={{ fontWeight: '600', color: 'var(--text-primary)' }}>
                  {lineItemsCount}
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Invoice Pairing Widget */}
        <div style={{ marginTop: '12px', paddingTop: '12px', borderTop: '1px solid var(--border-color)' }} data-invoice-pairing-section>
          {pairedInvoices.length > 0 ? (
            <div className="dn-pairing-widget">
              <button
                className="dn-pairing-widget-header"
                onClick={() => setInvoiceWidgetExpanded(!invoiceWidgetExpanded)}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flex: 1 }}>
                  <FileText size={16} />
                  <div style={{ flex: 1, textAlign: 'left' }}>
                    <div style={{ fontSize: '13px', fontWeight: '600' }}>
                      Paired: {pairedInvoices[0].invoiceNumber || `INV-${pairedInvoices[0].id?.slice(0, 8)}`}
                    </div>
                    <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '2px' }}>
                      {formatDate(pairedInvoices[0].date)}
                    </div>
                  </div>
                  {invoiceWidgetExpanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                </div>
              </button>
              {invoiceWidgetExpanded && (
                <div className="dn-pairing-widget-content">
                  <div style={{ marginBottom: '12px' }}>
                    {pairedInvoices.map((pairedInvoice, idx) => (
                      <div key={idx} style={{ 
                        marginBottom: idx < pairedInvoices.length - 1 ? '12px' : '0',
                        padding: '12px', 
                        background: 'var(--bg-card)', 
                        borderRadius: '8px', 
                        border: '1px solid var(--border-color)' 
                      }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                          <div style={{ flex: 1 }}>
                            <div style={{ fontSize: '14px', fontWeight: '600', marginBottom: '4px' }}>
                              {pairedInvoice.invoiceNumber || `INV-${pairedInvoice.id?.slice(0, 8)}`}
                            </div>
                            <div style={{ fontSize: '12px', color: 'var(--text-secondary)', marginBottom: '4px' }}>
                              {formatDate(pairedInvoice.date)}
                            </div>
                            <div style={{ fontSize: '12px', fontWeight: '600', color: 'var(--text-primary)' }}>
                              {formatCurrency(pairedInvoice.total || pairedInvoice.totalValue || 0)}
                            </div>
                          </div>
                          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: '6px' }}>
                            <span className={`badge ${pairedInvoice.pairStatus === 'confirmed' || pairedInvoice.pairStatus === 'accepted' ? 'badge-matched' : 'badge-unmatched'}`}>
                              {pairedInvoice.pairStatus === 'confirmed' ? 'Confirmed' : pairedInvoice.pairStatus === 'accepted' ? 'Accepted' : pairedInvoice.pairStatus}
                            </span>
                            {onSelectInvoice && (
                              <button
                                className="glass-button primary-action"
                                style={{ fontSize: '12px', padding: '6px 12px' }}
                                onClick={() => onSelectInvoice(pairedInvoice.id || pairedInvoice.invoiceId)}
                              >
                                View Invoice
                              </button>
                            )}
                          </div>
                        </div>
                        {pairedInvoice.pairedAt && (
                          <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '8px', paddingTop: '8px', borderTop: '1px solid var(--border-color)' }}>
                            Paired: {formatDateTime(pairedInvoice.pairedAt)}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ) : loadingInvoiceSuggestions ? (
            <div style={{ padding: '12px' }}>
              <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginBottom: '12px', fontWeight: '500' }}>
                Loading recommendations...
              </div>
              <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                <button 
                  className="glass-button primary-action" 
                  style={{ fontSize: '12px', padding: '8px 16px', fontWeight: '600', opacity: 0.6 }} 
                  disabled
                >
                  <FileText size={14} style={{ marginRight: '6px' }} />
                  Link Invoice
                </button>
                <button 
                  className="glass-button" 
                  style={{ fontSize: '12px', padding: '8px 16px', opacity: 0.6 }} 
                  disabled
                >
                  Create Manual Invoice
                </button>
              </div>
            </div>
          ) : invoiceSuggestions.length > 0 ? (
            <>
              <button
                className="dn-pairing-widget-header"
                onClick={() => setInvoiceWidgetExpanded(!invoiceWidgetExpanded)}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flex: 1 }}>
                  <FileText size={16} />
                  <div style={{ flex: 1, textAlign: 'left' }}>
                    <div style={{ fontSize: '13px', fontWeight: '600' }}>
                      Recommended: {invoiceSuggestions[0].invoiceNumber || `INV-${invoiceSuggestions[0].invoiceId?.slice(0, 8) || invoiceSuggestions[0].id?.slice(0, 8)}`}
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginTop: '2px' }}>
                      {invoiceSuggestions[0].confidence !== undefined && (
                        <span 
                          className={`confidence-badge ${invoiceSuggestions[0].confidence >= 0.8 ? 'high' : invoiceSuggestions[0].confidence >= 0.6 ? 'medium' : 'low'}`}
                          style={{ 
                            fontSize: '10px',
                            padding: '2px 6px',
                            background: invoiceSuggestions[0].confidence >= 0.8 
                              ? 'rgba(34, 197, 94, 0.2)' 
                              : invoiceSuggestions[0].confidence >= 0.6
                              ? 'rgba(251, 191, 36, 0.2)'
                              : 'rgba(239, 68, 68, 0.2)',
                            color: invoiceSuggestions[0].confidence >= 0.8
                              ? 'var(--accent-green)'
                              : invoiceSuggestions[0].confidence >= 0.6
                              ? 'var(--accent-yellow)'
                              : 'var(--accent-red)',
                            border: `1px solid ${invoiceSuggestions[0].confidence >= 0.8 
                              ? 'rgba(34, 197, 94, 0.3)' 
                              : invoiceSuggestions[0].confidence >= 0.6
                              ? 'rgba(251, 191, 36, 0.3)'
                              : 'rgba(239, 68, 68, 0.3)'}`,
                            fontWeight: '600'
                          }}
                        >
                          {Math.round(invoiceSuggestions[0].confidence * 100)}% match
                        </span>
                      )}
                      {!invoiceSuggestions[0].confidence && (
                        <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Suggested pairing</span>
                      )}
                    </div>
                  </div>
                  {invoiceWidgetExpanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                </div>
              </button>
              {invoiceWidgetExpanded && (
                <div className="dn-pairing-widget-content">
                  <div style={{ marginBottom: '12px' }}>
                    {/* LLM Explanation */}
                    {invoiceSuggestions[0].llmExplanation && (
                      <div className="llm-explanation" style={{
                        background: 'rgba(59, 130, 246, 0.1)',
                        borderLeft: '3px solid #3b82f6',
                        padding: '12px',
                        marginBottom: '12px',
                        borderRadius: '4px',
                        fontSize: '12px',
                        lineHeight: '1.5',
                        color: 'var(--text-primary)'
                      }}>
                        <span style={{ marginRight: '8px' }}>💡</span>
                        <span>{invoiceSuggestions[0].llmExplanation}</span>
                      </div>
                    )}
                    {/* Fallback reason if no LLM explanation */}
                    {!invoiceSuggestions[0].llmExplanation && invoiceSuggestions[0].reason && (
                      <div style={{ fontSize: '12px', color: 'var(--text-secondary)', marginBottom: '12px' }}>
                        {invoiceSuggestions[0].reason}
                      </div>
                    )}
                    {/* Feature highlights */}
                    {invoiceSuggestions[0].featuresSummary && (
                      <div className="feature-highlights" style={{
                        display: 'flex',
                        gap: '8px',
                        flexWrap: 'wrap',
                        marginBottom: '12px'
                      }}>
                        {invoiceSuggestions[0].featuresSummary.amountDiffPct !== undefined && (
                          <span className="feature-tag" style={{
                            background: 'rgba(255, 255, 255, 0.1)',
                            padding: '4px 8px',
                            borderRadius: '4px',
                            fontSize: '11px',
                            color: 'var(--text-secondary)'
                          }}>
                            Amount: {Math.abs(invoiceSuggestions[0].featuresSummary.amountDiffPct * 100).toFixed(1)}% diff
                          </span>
                        )}
                        {invoiceSuggestions[0].featuresSummary.dateDiffDays !== undefined && (
                          <span className="feature-tag" style={{
                            background: 'rgba(255, 255, 255, 0.1)',
                            padding: '4px 8px',
                            borderRadius: '4px',
                            fontSize: '11px',
                            color: 'var(--text-secondary)'
                          }}>
                            Date: {Math.abs(invoiceSuggestions[0].featuresSummary.dateDiffDays).toFixed(0)} days
                          </span>
                        )}
                        {invoiceSuggestions[0].featuresSummary.supplierNameSimilarity !== undefined && (
                          <span className="feature-tag" style={{
                            background: 'rgba(255, 255, 255, 0.1)',
                            padding: '4px 8px',
                            borderRadius: '4px',
                            fontSize: '11px',
                            color: 'var(--text-secondary)'
                          }}>
                            Supplier: {Math.round(invoiceSuggestions[0].featuresSummary.supplierNameSimilarity * 100)}% match
                          </span>
                        )}
                      </div>
                    )}
                    {invoicePairingError && (
                      <div style={{ 
                        padding: '8px 12px', 
                        marginBottom: '12px', 
                        background: 'rgba(239, 68, 68, 0.1)', 
                        border: '1px solid rgba(239, 68, 68, 0.3)', 
                        borderRadius: '6px',
                        fontSize: '12px',
                        color: 'var(--accent-red)',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '8px'
                      }}>
                        <AlertTriangle size={14} />
                        <span style={{ flex: 1 }}>{invoicePairingError}</span>
                        <button
                          onClick={() => {
                            setInvoicePairingError(null)
                            if (invoiceSuggestions[0]?.invoiceId || invoiceSuggestions[0]?.id) {
                              handlePairWithInvoice(invoiceSuggestions[0].invoiceId || invoiceSuggestions[0].id)
                            }
                          }}
                          className="glass-button"
                          style={{ fontSize: '11px', padding: '4px 8px' }}
                        >
                          Retry
                        </button>
                        <button
                          onClick={() => setInvoicePairingError(null)}
                          style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--accent-red)' }}
                        >
                          <X size={14} />
                        </button>
                      </div>
                    )}
                    {/* Show all suggestions with expandable details */}
                    {invoiceSuggestions.map((suggestion, idx) => {
                      const suggestionInvoiceId = suggestion.invoiceId || suggestion.id
                      const isPairing = pairingInvoiceId === suggestionInvoiceId
                      return (
                        <div key={idx} style={{ 
                          marginBottom: idx < invoiceSuggestions.length - 1 ? '12px' : '0',
                          padding: '12px', 
                          background: 'var(--bg-card)', 
                          borderRadius: '8px', 
                          border: '1px solid var(--border-color)' 
                        }}>
                          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                            <div style={{ flex: 1 }}>
                              <div style={{ fontSize: '13px', fontWeight: '600', marginBottom: '4px' }}>
                                {suggestion.invoiceNumber || `INV-${suggestionInvoiceId?.slice(0, 8)}`}
                              </div>
                              <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginTop: '4px' }}>
                                {suggestion.confidence !== undefined && (
                                  <span 
                                    className={`confidence-badge ${suggestion.confidence >= 0.8 ? 'high' : suggestion.confidence >= 0.6 ? 'medium' : 'low'}`}
                                    style={{ 
                                      fontSize: '10px',
                                      padding: '2px 6px',
                                      background: suggestion.confidence >= 0.8 
                                        ? 'rgba(34, 197, 94, 0.2)' 
                                        : suggestion.confidence >= 0.6
                                        ? 'rgba(251, 191, 36, 0.2)'
                                        : 'rgba(239, 68, 68, 0.2)',
                                      color: suggestion.confidence >= 0.8
                                        ? 'var(--accent-green)'
                                        : suggestion.confidence >= 0.6
                                        ? 'var(--accent-yellow)'
                                        : 'var(--accent-red)',
                                      border: `1px solid ${suggestion.confidence >= 0.8 
                                        ? 'rgba(34, 197, 94, 0.3)' 
                                        : suggestion.confidence >= 0.6
                                        ? 'rgba(251, 191, 36, 0.3)'
                                        : 'rgba(239, 68, 68, 0.3)'}`,
                                      fontWeight: '600'
                                    }}
                                  >
                                    {Math.round(suggestion.confidence * 100)}% match
                                  </span>
                                )}
                                {suggestion.date && (
                                  <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                                    {formatDate(suggestion.date)}
                                  </span>
                                )}
                                {suggestion.value !== undefined && (
                                  <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                                    · {formatCurrency(suggestion.value)}
                                  </span>
                                )}
                              </div>
                            </div>
                            <div style={{ display: 'flex', gap: '8px', marginLeft: '12px' }}>
                              <button 
                                className="glass-button primary-action" 
                                style={{ fontSize: '12px', padding: '6px 12px', fontWeight: '600' }} 
                                onClick={() => handlePairWithInvoice(suggestionInvoiceId)}
                                disabled={isPairing}
                              >
                                {isPairing ? (
                                  <>
                                    <Loader2 size={12} style={{ marginRight: '4px', display: 'inline-block', animation: 'spin 1s linear infinite' }} />
                                    Pairing...
                                  </>
                                ) : (
                                  'Pair'
                                )}
                              </button>
                              {onSelectInvoice && (
                                <button
                                  className="glass-button"
                                  style={{ fontSize: '12px', padding: '6px 12px' }}
                                  onClick={() => onSelectInvoice(suggestionInvoiceId)}
                                >
                                  View
                                </button>
                              )}
                            </div>
                          </div>
                          {suggestion.reason && (
                            <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '8px' }}>
                              {suggestion.reason}
                            </div>
                          )}
                          {suggestion.quantityMatchScore !== undefined && (
                            <div style={{ marginTop: '8px', fontSize: '11px' }}>
                              <span className={`quantity-match-score score-${suggestion.quantityMatchScore >= 0.8 ? 'high' : suggestion.quantityMatchScore >= 0.6 ? 'medium' : 'low'}`}>
                                Qty Match: {(suggestion.quantityMatchScore * 100).toFixed(0)}%
                              </span>
                              {suggestion.quantityMatchScore < 0.8 && suggestion.quantityWarnings && suggestion.quantityWarnings.length > 0 && (
                                <div style={{ display: 'inline-flex', alignItems: 'center', gap: '4px', marginLeft: '8px', color: 'var(--accent-yellow)' }}>
                                  <AlertTriangle size={12} />
                                  <span>{suggestion.quantityWarnings.length} warning{suggestion.quantityWarnings.length !== 1 ? 's' : ''}</span>
                                </div>
                              )}
                            </div>
                          )}
                          {suggestion.hasQuantityMismatch && (
                            <div style={{ 
                              marginTop: '8px', 
                              padding: '8px', 
                              background: 'rgba(239, 68, 68, 0.1)', 
                              borderRadius: '4px',
                              fontSize: '12px',
                              color: 'var(--accent-red)'
                            }}>
                              ⚠️ Quantity mismatch detected
                            </div>
                          )}
                          {suggestion.quantityDifferences && suggestion.quantityDifferences.length > 0 && (
                            <div style={{ marginTop: '8px', fontSize: '11px', color: 'var(--text-secondary)' }}>
                              <details style={{ cursor: 'pointer' }}>
                                <summary style={{ fontWeight: '500' }}>View quantity differences</summary>
                                <div style={{ marginTop: '8px', padding: '8px', background: 'var(--bg-secondary)', borderRadius: '4px' }}>
                                  {suggestion.quantityDifferences.map((diff: any, diffIdx: number) => (
                                    <div key={diffIdx} style={{ marginBottom: '4px', display: 'flex', justifyContent: 'space-between' }}>
                                      <span>{diff.description}:</span>
                                      <span style={{ color: diff.difference !== 0 ? 'var(--accent-red)' : 'var(--accent-green)' }}>
                                        Invoice: {diff.invoiceQty} | DN: {diff.dnQty} | Diff: {diff.difference > 0 ? '+' : ''}{diff.difference}
                                      </span>
                                    </div>
                                  ))}
                                </div>
                              </details>
                            </div>
                          )}
                        </div>
                      )
                    })}
                    <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', marginTop: '12px' }}>
                      {onNewManualInvoice && (
                        <button 
                          className="glass-button" 
                          style={{ fontSize: '12px', padding: '8px 16px' }} 
                          onClick={onNewManualInvoice}
                        >
                          Create manual invoice
                        </button>
                      )}
                    </div>
                  </div>
                </div>
              )}
            </>
          ) : (
            <div className="dn-pairing-widget">
              <div style={{ 
                padding: '16px',
                background: 'rgba(255, 255, 255, 0.02)',
                backdropFilter: 'blur(10px)',
                borderRadius: '12px',
                border: '1px solid rgba(255, 255, 255, 0.08)'
              }}>
                <div style={{ 
                  fontSize: '13px', 
                  color: 'var(--text-secondary)', 
                  marginBottom: '16px', 
                  fontWeight: '500',
                  letterSpacing: '0.3px'
                }}>
                  No invoice linked yet
                </div>
                <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
                  <button 
                    className="glass-button" 
                    style={{ 
                      flex: '1',
                      minWidth: '160px',
                      fontSize: '13px', 
                      padding: '10px 20px', 
                      fontWeight: '500',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      gap: '8px',
                      background: 'rgba(59, 130, 246, 0.1)',
                      border: '1px solid rgba(59, 130, 246, 0.2)',
                      color: 'var(--accent-blue)',
                      transition: 'all 0.2s ease',
                      backdropFilter: 'blur(10px)'
                    }}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.background = 'rgba(59, 130, 246, 0.15)'
                      e.currentTarget.style.borderColor = 'rgba(59, 130, 246, 0.3)'
                      e.currentTarget.style.transform = 'translateY(-1px)'
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.background = 'rgba(59, 130, 246, 0.1)'
                      e.currentTarget.style.borderColor = 'rgba(59, 130, 246, 0.2)'
                      e.currentTarget.style.transform = 'translateY(0)'
                    }}
                    onClick={handleLinkInvoiceClick}
                  >
                    <FileText size={16} />
                    Link Invoice
                  </button>
                  {onNewManualInvoice && (
                    <button 
                      className="glass-button" 
                      style={{ 
                        flex: '1',
                        minWidth: '160px',
                        fontSize: '13px', 
                        padding: '10px 20px',
                        fontWeight: '500',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        gap: '8px',
                        background: 'rgba(255, 255, 255, 0.05)',
                        border: '1px solid rgba(255, 255, 255, 0.1)',
                        color: 'var(--text-primary)',
                        transition: 'all 0.2s ease',
                        backdropFilter: 'blur(10px)'
                      }}
                      onMouseEnter={(e) => {
                        e.currentTarget.style.background = 'rgba(255, 255, 255, 0.08)'
                        e.currentTarget.style.borderColor = 'rgba(255, 255, 255, 0.15)'
                        e.currentTarget.style.transform = 'translateY(-1px)'
                      }}
                      onMouseLeave={(e) => {
                        e.currentTarget.style.background = 'rgba(255, 255, 255, 0.05)'
                        e.currentTarget.style.borderColor = 'rgba(255, 255, 255, 0.1)'
                        e.currentTarget.style.transform = 'translateY(0)'
                      }}
                      onClick={onNewManualInvoice}
                    >
                      <Plus size={16} />
                      Create Manual Invoice
                    </button>
                  )}
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Line Items Table - Simplified to show only Item Name and Quantity */}
        {deliveryNoteDetail.lineItems && deliveryNoteDetail.lineItems.length > 0 && (
          <div className="detail-card line-items-card" style={{ marginTop: '12px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
              <h3 className="detail-card-title" style={{ margin: 0 }}>Delivery Note Line Items</h3>
              {(deliveryNoteDetail.ocrStage === 'manual' || deliveryNoteDetail.source === 'manual') && onEditDeliveryNote && selectedDNId && (
                <button
                  className="glass-button"
                  onClick={() => onEditDeliveryNote(selectedDNId)}
                  style={{ fontSize: '12px', padding: '6px 12px', display: 'flex', alignItems: 'center', gap: '6px' }}
                >
                  <Edit size={14} />
                  Edit Delivery Note
                </button>
              )}
            </div>
            <div className="detail-card-content" style={{ padding: 0 }}>
              <div className="invoice-line-items-table-wrapper" style={{ width: '100%', overflowX: 'auto' }}>
                <table className="invoice-line-items-table" style={{ width: '100%', tableLayout: 'auto' }}>
                  <thead>
                    <tr>
                      <th className="col-description" style={{ width: 'auto', minWidth: 0, maxWidth: 'none' }}>Item Name</th>
                      <th className="col-quantity" style={{ width: '80px', minWidth: '80px', maxWidth: '80px' }}>Quantity</th>
                    </tr>
                  </thead>
                  <tbody>
                    {deliveryNoteDetail.lineItems.map((item: any, idx: number) => (
                      <tr key={idx}>
                        <td className="col-description" style={{ width: 'auto', minWidth: 0, maxWidth: 'none', paddingRight: '16px' }}>
                          <div className="line-item-description" style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                            {item.description || 'Unknown item'}
                          </div>
                        </td>
                        <td className="col-quantity text-numeric" style={{ width: '80px', minWidth: '80px', maxWidth: '80px', textAlign: 'right', paddingRight: '16px' }}>
                          <span className="quantity-value">
                            {item.qty || 0}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}
      </div>
    )
  }

  if (!invoice) {
    // Show "Upload your first invoice" message when in empty state (no invoices at all)
    if (isEmptyState) {
      return (
        <div className="invoices-detail-column">
          <div className="detail-card" style={{ 
            display: 'flex', 
            flexDirection: 'column', 
            alignItems: 'center', 
            justifyContent: 'center',
            padding: '80px 40px',
            textAlign: 'center',
            minHeight: '400px'
          }}>
            <div className="empty-state-icon" style={{ fontSize: '64px', marginBottom: '24px' }}>📄</div>
            <div className="empty-state-title" style={{ fontSize: '24px', fontWeight: '600', marginBottom: '12px', color: 'var(--text-primary)' }}>
              Upload your first invoice
            </div>
            <div className="empty-state-description" style={{ fontSize: '14px', color: 'var(--text-secondary)', marginBottom: '32px', maxWidth: '400px' }}>
              Drag and drop a file above, or click the button below to get started. Owlin will automatically extract and process your invoice details.
            </div>
            <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap', justifyContent: 'center' }}>
              {onUploadClick && (
                <button 
                  className="glass-button primary-action" 
                  onClick={onUploadClick}
                  style={{ fontSize: '14px', padding: '12px 24px', fontWeight: '600' }}
                >
                  Choose File to Upload
                </button>
              )}
              {onNewManualInvoice && (
                <button 
                  className="glass-button" 
                  onClick={onNewManualInvoice}
                  style={{ fontSize: '14px', padding: '12px 24px' }}
                >
                  Create Manual Invoice
                </button>
              )}
            </div>
          </div>
        </div>
      )
    }
    
    // Show "Select an invoice" message when there are invoices but none selected
    return (
      <div className="invoices-detail-column">
        <div className="empty-state">
          <div className="empty-state-icon" style={{ fontSize: '64px', marginBottom: '24px' }}>📋</div>
          <div className="empty-state-title">Select an invoice</div>
          <div className="empty-state-description">
            Choose a document from the left to review its details and resolve any issues.
          </div>
        </div>
      </div>
    )
  }

  // Compare line items between invoice and delivery note using fuzzy matching
  const comparisonRows: Array<{
    item: string
    invQty?: number
    dnQty?: number
    unit?: string
    price?: number
    lineTotal?: number
    status: 'ok' | 'short' | 'over' | 'not_matched'
  }> = []

  if (invoice.lineItems) {
    // Use fuzzy matching to match invoice items with delivery note items
    const dnLineItems = invoice.deliveryNote?.lineItems || []
    const matchedItems = matchLineItems(invoice.lineItems, dnLineItems, 0.85)
    
    matchedItems.forEach((matched) => {
      const item = matched.invoiceItem
      const dnItem = matched.deliveryItem
      const invQty = item.qty || 0
      const dnQty = dnItem ? (dnItem.qty || 0) : undefined
      
      let status: 'ok' | 'short' | 'over' | 'not_matched' = 'not_matched'
      if (dnQty !== undefined) {
        if (dnQty < invQty) status = 'short'
        else if (dnQty > invQty) status = 'over'
        else status = 'ok'
      }

      comparisonRows.push({
        item: item.description || 'Unknown item',
        invQty,
        dnQty,
        unit: item.uom || item.unit || '',
        price: item.unitPrice || 0,
        lineTotal: item.total || (invQty * (item.unitPrice || 0)),
        status,
      })
    })
  }

  // Determine workflow progress
  const stepScanned = invoice.status === 'scanned' || invoice.status === 'manual'
  const stepIssuesResolved = !hasIssues
  const stepDNLinked = !!invoice.deliveryNote
  const stepSubmitted = false // This would come from invoice status if we track it

  return (
    <div className="invoices-detail-column invoices-detail-column-selected">
      {/* Document Header Card */}
      <div className="detail-card document-header-card" data-section="invoice_header">
        <div className="document-header-left">
          <div className="document-header-supplier" style={{ fontSize: '28px', fontWeight: '700', marginBottom: '4px' }}>
            {invoice.supplier || 'Unknown Supplier'}
          </div>
          <div className="document-header-meta">
            <span>{invoice.invoiceNumber || `INV-${invoice.id.slice(0, 8)}`}</span>
            <span>·</span>
            <span>{formatDate(invoice.date || '')}</span>
            {invoice.venue && (
              <>
                <span>·</span>
                <span>{invoice.venue}</span>
              </>
            )}
          </div>
          <div style={{ display: 'flex', gap: '8px', marginTop: '12px', flexWrap: 'wrap' }}>
            {invoice.status === 'manual' ? (
              <span className="badge badge-manual">Manual</span>
            ) : (
              <span className="badge badge-scanned">Scanned</span>
            )}
            {invoice.matched ? (
              <span className="badge badge-matched">Matched</span>
            ) : (
              <span className="badge badge-unmatched">Unmatched</span>
            )}
            {canSubmit ? (
              <span className="badge badge-ready">Ready</span>
            ) : (
              <span className="badge" style={{ background: 'rgba(255, 255, 255, 0.1)', color: 'var(--text-muted)' }}>Draft</span>
            )}
            {invoice.status === 'scanned' && invoice.confidence !== undefined && (
              <span className="badge badge-ocr" style={{ fontSize: '11px' }}>
                {typeof invoice.confidence === 'number' && invoice.confidence <= 1 
                  ? Math.round(invoice.confidence * 100) 
                  : Math.round(invoice.confidence)}% OCR
              </span>
            )}
            {invoice.flagged && <span className="badge badge-flagged">Flagged</span>}
          </div>
        </div>
        <div className="document-header-right">
          <div className="document-header-total">{formatCurrency(displayTotal)}</div>
          {(displaySubtotal > 0 || displayVat > 0) && (
            <div className="document-header-subtotal">
              Subtotal {formatCurrency(displaySubtotal)} · VAT {formatCurrency(displayVat)}
            </div>
          )}
        </div>
        
        {/* Compressed Workflow Progress */}
        <div style={{ gridColumn: '1 / -1', marginTop: '16px', paddingTop: '16px', borderTop: '1px solid var(--border-color)' }}>
          <div className="workflow-progress-compressed">
            <div className="workflow-step" style={{ opacity: stepScanned ? 1 : 0.5 }}>
              {stepScanned ? <CheckCircle2 size={14} style={{ color: 'var(--accent-green)' }} /> : <Circle size={14} style={{ color: 'var(--text-muted)' }} />}
              <span style={{ fontSize: '11px' }}>Scanned</span>
            </div>
            <div className="workflow-step" style={{ opacity: stepIssuesResolved ? 1 : 0.5 }}>
              {stepIssuesResolved ? <CheckCircle2 size={14} style={{ color: 'var(--accent-green)' }} /> : <Circle size={14} style={{ color: 'var(--text-muted)' }} />}
              <span style={{ fontSize: '11px' }}>Issues</span>
            </div>
            <div className="workflow-step" style={{ opacity: stepDNLinked ? 1 : 0.5 }}>
              {stepDNLinked ? <CheckCircle2 size={14} style={{ color: 'var(--accent-green)' }} /> : <Circle size={14} style={{ color: 'var(--text-muted)' }} />}
              <span style={{ fontSize: '11px' }}>DN Linked</span>
            </div>
            <div className="workflow-step" style={{ opacity: stepSubmitted ? 1 : 0.5 }}>
              {stepSubmitted ? <CheckCircle2 size={14} style={{ color: 'var(--accent-green)' }} /> : <Circle size={14} style={{ color: 'var(--text-muted)' }} />}
              <span style={{ fontSize: '11px' }}>Submitted</span>
            </div>
          </div>
        </div>
        
        <div style={{ gridColumn: '1 / -1', marginTop: '16px', paddingTop: '16px', borderTop: '1px solid var(--border-color)', display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
          {onOpenPDF && (
            <button className="glass-button" style={{ fontSize: '12px' }} onClick={onOpenPDF}>
              <ExternalLink size={14} />
              Open original PDF
            </button>
          )}
          <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
            {invoice.status === 'scanned' && invoice.lineItems && invoice.lineItems.some(item => item.bbox) && (
              <button 
                className="glass-button" 
                style={{ fontSize: '12px' }} 
                onClick={() => setShowVisualizer(!showVisualizer)}
                title="Toggle visual verification"
              >
                <Eye size={14} style={{ marginRight: '6px' }} />
                {showVisualizer ? 'Hide' : 'Show'} Visual
              </button>
            )}
            {invoice.status === 'scanned' && onViewOCRDetails && (
              <button className="glass-button" style={{ fontSize: '12px' }} onClick={onViewOCRDetails}>
                <FileText size={14} />
                OCR details
              </button>
            )}
          </div>
        </div>
        
        {/* Delivery Note Pairing Widget */}
        <div style={{ gridColumn: '1 / -1', marginTop: '16px', paddingTop: '16px', borderTop: '1px solid var(--border-color)' }} data-section="delivery_link" data-delivery-note-section>
          {invoice.deliveryNote ? (
            <div className="dn-pairing-widget">
              <button
                className="dn-pairing-widget-header"
                onClick={() => setDnWidgetExpanded(!dnWidgetExpanded)}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flex: 1 }}>
                  <Package size={16} />
                  <div style={{ flex: 1, textAlign: 'left' }}>
                    <div style={{ fontSize: '13px', fontWeight: '600' }}>
                      Paired: {invoice.deliveryNote.noteNumber || `DN-${invoice.deliveryNote.id.slice(0, 8)}`}
                    </div>
                    <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '2px' }}>
                      {formatDate(invoice.deliveryNote.date)}
                    </div>
                  </div>
                  {dnWidgetExpanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                </div>
              </button>
              {dnWidgetExpanded && (
                <div className="dn-pairing-widget-content">
                  <div style={{ marginBottom: '12px' }}>
                    {pairingError && (
                      <div style={{ 
                        padding: '8px 12px', 
                        marginBottom: '12px', 
                        background: 'rgba(239, 68, 68, 0.1)', 
                        border: '1px solid rgba(239, 68, 68, 0.3)', 
                        borderRadius: '6px',
                        fontSize: '12px',
                        color: 'var(--accent-red)',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '8px'
                      }}>
                        <AlertTriangle size={14} />
                        <span>{pairingError}</span>
                        <button
                          onClick={() => setPairingError(null)}
                          style={{ marginLeft: 'auto', background: 'none', border: 'none', cursor: 'pointer', color: 'var(--accent-red)' }}
                        >
                          <X size={14} />
                        </button>
                      </div>
                    )}
                    <div style={{ display: 'flex', gap: '8px', marginBottom: '12px', flexWrap: 'wrap' }}>
                      <button className="glass-button" style={{ fontSize: '11px', padding: '6px 12px' }} onClick={onChangeDeliveryNote}>
                        Change DN
                      </button>
                      <button className="glass-button" style={{ fontSize: '11px', padding: '6px 12px' }} onClick={onLinkDeliveryNote}>
                        View full details
                      </button>
                      <button 
                        className="glass-button" 
                        style={{ 
                          fontSize: '11px', 
                          padding: '6px 12px',
                          color: 'var(--accent-red)',
                          borderColor: 'rgba(239, 68, 68, 0.3)'
                        }} 
                        onClick={() => setShowUnpairConfirm(true)}
                        disabled={unpairing}
                      >
                        {unpairing ? (
                          <>
                            <Loader2 size={12} style={{ marginRight: '4px', animation: 'spin 1s linear infinite' }} />
                            Unpairing...
                          </>
                        ) : (
                          <>
                            <Unlink size={12} style={{ marginRight: '4px' }} />
                            Unpair
                          </>
                        )}
                      </button>
                    </div>
                    {showUnpairConfirm && (
                      <div style={{
                        padding: '12px',
                        marginBottom: '12px',
                        background: 'rgba(239, 68, 68, 0.05)',
                        border: '1px solid rgba(239, 68, 68, 0.2)',
                        borderRadius: '6px',
                        fontSize: '12px'
                      }}>
                        <div style={{ marginBottom: '8px', fontWeight: '600', color: 'var(--text-primary)' }}>
                          Unpair delivery note?
                        </div>
                        <div style={{ marginBottom: '12px', color: 'var(--text-secondary)' }}>
                          This will remove the pairing between this invoice and its delivery note. You can pair them again later.
                        </div>
                        <div style={{ display: 'flex', gap: '8px' }}>
                          <button
                            className="glass-button"
                            style={{ fontSize: '11px', padding: '6px 12px', background: 'var(--accent-red)', color: 'white' }}
                            onClick={handleUnpair}
                            disabled={unpairing}
                          >
                            {unpairing ? 'Unpairing...' : 'Confirm Unpair'}
                          </button>
                          <button
                            className="glass-button"
                            style={{ fontSize: '11px', padding: '6px 12px' }}
                            onClick={() => setShowUnpairConfirm(false)}
                            disabled={unpairing}
                          >
                            Cancel
                          </button>
                        </div>
                      </div>
                    )}
                    {comparisonRows.length > 0 && (
                      <table className="comparison-table" style={{ fontSize: '12px' }}>
                        <thead>
                          <tr>
                            <th>Item</th>
                            <th>Inv Qty</th>
                            <th>DN Qty</th>
                            <th>Status</th>
                          </tr>
                        </thead>
                        <tbody>
                          {comparisonRows.map((row, idx) => (
                            <tr key={idx} className={row.status !== 'ok' ? 'mismatch' : ''}>
                              <td>{row.item}</td>
                              <td>{row.invQty}</td>
                              <td>{row.dnQty !== undefined ? row.dnQty : '-'}</td>
                              <td>
                                {row.status === 'not_matched' && (
                                  <span title="No delivery note paired" style={{ color: 'var(--accent-red)', fontSize: '11px' }}>Not Matched</span>
                                )}
                                {row.status === 'ok' && (
                                  <Check size={14} style={{ color: 'var(--accent-green)' }} title="Quantities match" />
                                )}
                                {row.status === 'short' && (
                                  <AlertTriangle 
                                    size={14} 
                                    style={{ color: 'var(--accent-red)', cursor: 'help' }} 
                                    title={`Under delivered: ${row.invQty! - (row.dnQty || 0)} units short`}
                                  />
                                )}
                                {row.status === 'over' && (
                                  <AlertTriangle 
                                    size={14} 
                                    style={{ color: 'var(--accent-yellow)', cursor: 'help' }} 
                                    title={`Over delivered: ${(row.dnQty || 0) - row.invQty!} units extra`}
                                  />
                                )}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    )}
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="dn-pairing-widget">
              {loadingSuggestions ? (
                <div style={{ padding: '12px' }}>
                  <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginBottom: '12px', fontWeight: '500' }}>
                    Loading recommendations...
                  </div>
                  <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                    <button 
                      className="glass-button primary-action" 
                      style={{ fontSize: '12px', padding: '8px 16px', fontWeight: '600', opacity: 0.6 }} 
                      disabled
                    >
                      <Package size={14} style={{ marginRight: '6px' }} />
                      Link Delivery Note
                    </button>
                    <button 
                      className="glass-button" 
                      style={{ fontSize: '12px', padding: '8px 16px', opacity: 0.6 }} 
                      disabled
                    >
                      Create Manual DN
                    </button>
                  </div>
                </div>
              ) : pairingSuggestions.length > 0 ? (
                <>
                  <button
                    className="dn-pairing-widget-header"
                    onClick={() => setDnWidgetExpanded(!dnWidgetExpanded)}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flex: 1 }}>
                      <Package size={16} />
                      <div style={{ flex: 1, textAlign: 'left' }}>
                        <div style={{ fontSize: '13px', fontWeight: '600' }}>
                          Recommended: {pairingSuggestions[0].deliveryNoteNumber || `DN-${pairingSuggestions[0].deliveryNoteId.slice(0, 8)}`}
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginTop: '2px' }}>
                          {pairingSuggestions[0].confidence !== undefined && (
                            <span 
                              className={`confidence-badge ${pairingSuggestions[0].confidence >= 0.8 ? 'high' : pairingSuggestions[0].confidence >= 0.6 ? 'medium' : 'low'}`}
                              style={{ 
                                fontSize: '10px',
                                padding: '2px 6px',
                                background: pairingSuggestions[0].confidence >= 0.8 
                                  ? 'rgba(34, 197, 94, 0.2)' 
                                  : pairingSuggestions[0].confidence >= 0.6
                                  ? 'rgba(251, 191, 36, 0.2)'
                                  : 'rgba(239, 68, 68, 0.2)',
                                color: pairingSuggestions[0].confidence >= 0.8
                                  ? 'var(--accent-green)'
                                  : pairingSuggestions[0].confidence >= 0.6
                                  ? 'var(--accent-yellow)'
                                  : 'var(--accent-red)',
                                border: `1px solid ${pairingSuggestions[0].confidence >= 0.8 
                                  ? 'rgba(34, 197, 94, 0.3)' 
                                  : pairingSuggestions[0].confidence >= 0.6
                                  ? 'rgba(251, 191, 36, 0.3)'
                                  : 'rgba(239, 68, 68, 0.3)'}`,
                                fontWeight: '600'
                              }}
                            >
                              {Math.round(pairingSuggestions[0].confidence * 100)}% match
                            </span>
                          )}
                          {!pairingSuggestions[0].confidence && (
                            <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Suggested pairing</span>
                          )}
                        </div>
                      </div>
                      {dnWidgetExpanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                    </div>
                  </button>
                  {dnWidgetExpanded && (
                    <div className="dn-pairing-widget-content">
                      <div style={{ marginBottom: '12px' }}>
                        {/* LLM Explanation */}
                        {pairingSuggestions[0].llmExplanation && (
                          <div className="llm-explanation" style={{
                            background: 'rgba(59, 130, 246, 0.1)',
                            borderLeft: '3px solid #3b82f6',
                            padding: '12px',
                            marginBottom: '12px',
                            borderRadius: '4px',
                            fontSize: '12px',
                            lineHeight: '1.5',
                            color: 'var(--text-primary)'
                          }}>
                            <span style={{ marginRight: '8px' }}>💡</span>
                            <span>{pairingSuggestions[0].llmExplanation}</span>
                          </div>
                        )}
                        {/* Fallback reason if no LLM explanation */}
                        {!pairingSuggestions[0].llmExplanation && pairingSuggestions[0].reason && (
                          <div style={{ fontSize: '12px', color: 'var(--text-secondary)', marginBottom: '12px' }}>
                            {pairingSuggestions[0].reason}
                          </div>
                        )}
                        {/* Feature highlights */}
                        {pairingSuggestions[0].featuresSummary && (
                          <div className="feature-highlights" style={{
                            display: 'flex',
                            gap: '8px',
                            flexWrap: 'wrap',
                            marginBottom: '12px'
                          }}>
                            {pairingSuggestions[0].featuresSummary.amountDiffPct !== undefined && (
                              <span className="feature-tag" style={{
                                background: 'rgba(255, 255, 255, 0.1)',
                                padding: '4px 8px',
                                borderRadius: '4px',
                                fontSize: '11px',
                                color: 'var(--text-secondary)'
                              }}>
                                Amount: {Math.abs(pairingSuggestions[0].featuresSummary.amountDiffPct * 100).toFixed(1)}% diff
                              </span>
                            )}
                            {pairingSuggestions[0].featuresSummary.dateDiffDays !== undefined && (
                              <span className="feature-tag" style={{
                                background: 'rgba(255, 255, 255, 0.1)',
                                padding: '4px 8px',
                                borderRadius: '4px',
                                fontSize: '11px',
                                color: 'var(--text-secondary)'
                              }}>
                                Date: {Math.abs(pairingSuggestions[0].featuresSummary.dateDiffDays).toFixed(0)} days
                              </span>
                            )}
                            {pairingSuggestions[0].featuresSummary.supplierNameSimilarity !== undefined && (
                              <span className="feature-tag" style={{
                                background: 'rgba(255, 255, 255, 0.1)',
                                padding: '4px 8px',
                                borderRadius: '4px',
                                fontSize: '11px',
                                color: 'var(--text-secondary)'
                              }}>
                                Supplier: {Math.round(pairingSuggestions[0].featuresSummary.supplierNameSimilarity * 100)}% match
                              </span>
                            )}
                          </div>
                        )}
                        {pairingError && (
                          <div style={{ 
                            padding: '8px 12px', 
                            marginBottom: '12px', 
                            background: 'rgba(239, 68, 68, 0.1)', 
                            border: '1px solid rgba(239, 68, 68, 0.3)', 
                            borderRadius: '6px',
                            fontSize: '12px',
                            color: 'var(--accent-red)',
                            display: 'flex',
                            alignItems: 'center',
                            gap: '8px'
                          }}>
                            <AlertTriangle size={14} />
                            <span style={{ flex: 1 }}>{pairingError}</span>
                            <button
                              onClick={() => {
                                setPairingError(null)
                                handlePairWithDN(pairingSuggestions[0].deliveryNoteId)
                              }}
                              className="glass-button"
                              style={{ fontSize: '11px', padding: '4px 8px' }}
                            >
                              Retry
                            </button>
                            <button
                              onClick={() => setPairingError(null)}
                              style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--accent-red)' }}
                            >
                              <X size={14} />
                            </button>
                          </div>
                        )}
                        <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', marginBottom: '12px' }}>
                          <button 
                            className="glass-button primary-action" 
                            style={{ fontSize: '12px', padding: '8px 16px', fontWeight: '600' }} 
                            onClick={() => handlePairWithDN(pairingSuggestions[0].deliveryNoteId)}
                            disabled={pairing === pairingSuggestions[0].deliveryNoteId}
                          >
                            {pairing === pairingSuggestions[0].deliveryNoteId ? (
                              <>
                                <Loader2 size={14} style={{ marginRight: '6px', display: 'inline-block', animation: 'spin 1s linear infinite' }} />
                                Pairing...
                              </>
                            ) : (
                              'Pair with this DN'
                            )}
                          </button>
                          <button 
                            className="glass-button" 
                            style={{ fontSize: '12px', padding: '8px 16px' }} 
                            onClick={onLinkDeliveryNote}
                          >
                            View all DNs
                          </button>
                          <button 
                            className="glass-button" 
                            style={{ fontSize: '12px', padding: '8px 16px' }} 
                            onClick={onCreateDeliveryNote}
                          >
                            Create manual DN
                          </button>
                        </div>
                        {pairingSuggestions.length > 1 && (
                          <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '8px' }}>
                            {pairingSuggestions.length - 1} more suggestion{pairingSuggestions.length - 1 !== 1 ? 's' : ''} available
                          </div>
                        )}
                      </div>
                    </div>
                  )}
                </>
              ) : (
                <div style={{ 
                  padding: '16px',
                  background: 'rgba(255, 255, 255, 0.02)',
                  backdropFilter: 'blur(10px)',
                  borderRadius: '12px',
                  border: '1px solid rgba(255, 255, 255, 0.08)'
                }}>
                  <div style={{ 
                    fontSize: '13px', 
                    color: 'var(--text-secondary)', 
                    marginBottom: '16px', 
                    fontWeight: '500',
                    letterSpacing: '0.3px'
                  }}>
                    No delivery note linked yet
                  </div>
                  <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
                    <button 
                      className="glass-button" 
                      style={{ 
                        flex: '1',
                        minWidth: '160px',
                        fontSize: '13px', 
                        padding: '10px 20px', 
                        fontWeight: '500',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        gap: '8px',
                        background: 'rgba(59, 130, 246, 0.1)',
                        border: '1px solid rgba(59, 130, 246, 0.2)',
                        color: 'var(--accent-blue)',
                        transition: 'all 0.2s ease',
                        backdropFilter: 'blur(10px)'
                      }}
                      onMouseEnter={(e) => {
                        e.currentTarget.style.background = 'rgba(59, 130, 246, 0.15)'
                        e.currentTarget.style.borderColor = 'rgba(59, 130, 246, 0.3)'
                        e.currentTarget.style.transform = 'translateY(-1px)'
                      }}
                      onMouseLeave={(e) => {
                        e.currentTarget.style.background = 'rgba(59, 130, 246, 0.1)'
                        e.currentTarget.style.borderColor = 'rgba(59, 130, 246, 0.2)'
                        e.currentTarget.style.transform = 'translateY(0)'
                      }}
                      onClick={handleLinkDeliveryNoteClick}
                    >
                      <Package size={16} />
                      Link Delivery Note
                    </button>
                    <button 
                      className="glass-button" 
                      style={{ 
                        flex: '1',
                        minWidth: '160px',
                        fontSize: '13px', 
                        padding: '10px 20px',
                        fontWeight: '500',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        gap: '8px',
                        background: 'rgba(255, 255, 255, 0.05)',
                        border: '1px solid rgba(255, 255, 255, 0.1)',
                        color: 'var(--text-primary)',
                        transition: 'all 0.2s ease',
                        backdropFilter: 'blur(10px)'
                      }}
                      onMouseEnter={(e) => {
                        e.currentTarget.style.background = 'rgba(255, 255, 255, 0.08)'
                        e.currentTarget.style.borderColor = 'rgba(255, 255, 255, 0.15)'
                        e.currentTarget.style.transform = 'translateY(-1px)'
                      }}
                      onMouseLeave={(e) => {
                        e.currentTarget.style.background = 'rgba(255, 255, 255, 0.05)'
                        e.currentTarget.style.borderColor = 'rgba(255, 255, 255, 0.1)'
                        e.currentTarget.style.transform = 'translateY(0)'
                      }}
                      onClick={onCreateDeliveryNote}
                    >
                      <Plus size={16} />
                      Create Manual DN
                    </button>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Visual Verification Component */}
      {showVisualizer && invoice.status === 'scanned' && invoice.lineItems && invoice.lineItems.some(item => item.bbox) && (
        <div className="detail-card">
          <div className="detail-card-header">
            <h3 className="detail-card-title">Visual Verification</h3>
            <button 
              className="glass-button" 
              style={{ fontSize: '12px', padding: '4px 8px' }} 
              onClick={() => setShowVisualizer(false)}
            >
              <X size={14} />
            </button>
          </div>
          <div className="detail-card-content" style={{ padding: 0 }}>
            <InvoiceVisualizer
              docId={invoice.id}
              lineItems={invoice.lineItems}
              activeLineItemIndex={hoveredLineItemIndex}
              onLineItemHover={setHoveredLineItemIndex}
            />
          </div>
        </div>
      )}

      {/* Top Recommended DN - One Click Action Card */}
      {!invoice.deliveryNote && (manualPairingWorkflowActive ? topSuggestion : pairingSuggestions.length > 0) && !loadingSuggestions && (
        <div className="detail-card recommended-dn-card" style={{ animation: 'fadeIn 0.3s ease-out' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '12px' }}>
            <div>
              <div style={{ fontSize: '14px', fontWeight: '600', marginBottom: '4px' }}>
                {manualPairingWorkflowActive ? 'Suggested Delivery Note' : 'Recommended Delivery Note'}
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
                <span style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
                  {(manualPairingWorkflowActive ? topSuggestion : pairingSuggestions[0])?.deliveryNoteNumber || `DN-${(manualPairingWorkflowActive ? topSuggestion : pairingSuggestions[0])?.deliveryNoteId.slice(0, 8)}`}
                </span>
                {(manualPairingWorkflowActive ? topSuggestion : pairingSuggestions[0])?.confidence !== undefined && (
                  <span 
                    className="badge" 
                    style={{ 
                      fontSize: '10px',
                      padding: '2px 6px',
                      background: (manualPairingWorkflowActive ? topSuggestion : pairingSuggestions[0])!.confidence >= 0.8 
                        ? 'rgba(34, 197, 94, 0.2)' 
                        : (manualPairingWorkflowActive ? topSuggestion : pairingSuggestions[0])!.confidence >= 0.6
                        ? 'rgba(251, 191, 36, 0.2)'
                        : 'rgba(239, 68, 68, 0.2)',
                      color: pairingSuggestions[0].confidence >= 0.8
                        ? 'var(--accent-green)'
                        : pairingSuggestions[0].confidence >= 0.6
                        ? 'var(--accent-yellow)'
                        : 'var(--accent-red)',
                      border: `1px solid ${pairingSuggestions[0].confidence >= 0.8 
                        ? 'rgba(34, 197, 94, 0.3)' 
                        : pairingSuggestions[0].confidence >= 0.6
                        ? 'rgba(251, 191, 36, 0.3)'
                        : 'rgba(239, 68, 68, 0.3)'}`
                    }}
                  >
                    {Math.round(pairingSuggestions[0].confidence * 100)}% match
                  </span>
                )}
              </div>
            </div>
            <button
              className="glass-button primary-action"
              style={{ fontSize: '13px', padding: '10px 20px', fontWeight: '600' }}
              onClick={() => handlePairWithDN(pairingSuggestions[0].deliveryNoteId)}
              disabled={pairing === pairingSuggestions[0].deliveryNoteId}
            >
              {pairing === pairingSuggestions[0].deliveryNoteId ? (
                <>
                  <Loader2 size={14} style={{ marginRight: '6px', display: 'inline-block', animation: 'spin 1s linear infinite' }} />
                  Pairing...
                </>
              ) : (
                'Pair Now'
              )}
            </button>
          </div>
          {pairingSuggestions[0].reason && (
            <div style={{ fontSize: '11px', color: 'var(--text-muted)', paddingTop: '8px', borderTop: '1px solid var(--border-color)' }}>
              {pairingSuggestions[0].reason}
            </div>
          )}
        </div>
      )}

      {/* Line Items Table Card with Totals - Moved to Top */}
      <div className="detail-card line-items-card" data-section="line_items">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
          <h3 className="detail-card-title" style={{ margin: 0 }}>Invoice Line Items</h3>
          {invoice.status === 'manual' && (
            <>
              {!isEditing ? (
                <button
                  className="glass-button"
                  onClick={handleStartEdit}
                  style={{ fontSize: '12px', padding: '6px 12px', display: 'flex', alignItems: 'center', gap: '6px' }}
                >
                  <Edit size={14} />
                  Edit Invoice
                </button>
              ) : (
                <div style={{ display: 'flex', gap: '8px' }}>
                  <button
                    className="glass-button"
                    onClick={handleCancelEdit}
                    disabled={savingEdit}
                    style={{ fontSize: '11px', padding: '4px 8px', display: 'flex', alignItems: 'center', gap: '4px' }}
                  >
                    <X size={12} />
                    Cancel
                  </button>
                  <button
                    className="glass-button"
                    onClick={handleSaveEdit}
                    disabled={savingEdit}
                    style={{ fontSize: '11px', padding: '4px 8px', display: 'flex', alignItems: 'center', gap: '4px', background: 'rgba(34, 197, 94, 0.2)', borderColor: 'rgba(34, 197, 94, 0.4)' }}
                  >
                    {savingEdit ? (
                      <>
                        <Loader2 size={12} className="spinning" />
                        Saving...
                      </>
                    ) : (
                      <>
                        <CheckCircle size={12} />
                        Done
                      </>
                    )}
                  </button>
                </div>
              )}
            </>
          )}
        </div>
        <div className="detail-card-content" style={isEditing ? { padding: '8px' } : {}}>
          {isEditing ? (
            // Editable line items table
            <>
              <div className="invoice-line-items-table-wrapper" ref={lineItemsRef}>
                <table className="invoice-line-items-table invoice-line-items-table-editing">
                  <thead>
                    <tr>
                      <th className="col-description">Description</th>
                      <th className="col-quantity">Qty</th>
                      <th className="col-quantity-dn">DN</th>
                      <th className="col-price">Price</th>
                      <th className="col-total">Total</th>
                      <th className="col-status"></th>
                    </tr>
                  </thead>
                  <tbody>
                    {editableLineItems.map((item, idx) => (
                      <tr key={idx}>
                        <td className="col-description" data-label="Description">
                          <input
                            type="text"
                            className="line-item-input"
                            value={item.description}
                            onChange={(e) => updateEditableLineItem(idx, 'description', e.target.value)}
                            placeholder="Item description"
                          />
                        </td>
                        <td className="col-quantity text-numeric" data-label="Qty">
                          <input
                            type="number"
                            className="line-item-input numeric-input"
                            value={item.qty || ''}
                            onChange={(e) => updateEditableLineItem(idx, 'qty', Math.round(Number(e.target.value)) || 0)}
                            min="0"
                            step="1"
                            disabled={savingEdit}
                            placeholder="0"
                          />
                        </td>
                        <td className="col-quantity-dn text-numeric" data-label="DN">
                          <input
                            type="number"
                            className="line-item-input numeric-input"
                            value={item.dnQty !== undefined ? item.dnQty : ''}
                            onChange={(e) => updateEditableLineItem(idx, 'dnQty', e.target.value === '' ? undefined : Math.round(Number(e.target.value)))}
                            placeholder="—"
                            min="0"
                            step="1"
                            disabled={savingEdit || !invoice?.deliveryNote}
                            title={!invoice?.deliveryNote ? "Link a delivery note first to edit DN quantities" : ""}
                          />
                        </td>
                        <td className="col-price text-numeric" data-label="Price">
                          <input
                            type="number"
                            className="line-item-input numeric-input"
                            value={item.price || ''}
                            onChange={(e) => updateEditableLineItem(idx, 'price', Number(e.target.value) || 0)}
                            min="0"
                            step="0.01"
                            disabled={savingEdit}
                            placeholder="0.00"
                          />
                        </td>
                        <td className="col-total text-numeric" data-label="Total">
                          <span className="total-value">{formatCurrency(item.total)}</span>
                        </td>
                        <td className="col-status" data-label="Actions">
                          {editableLineItems.length > 1 && (
                            <button
                              type="button"
                              className="line-item-delete-button"
                              onClick={() => removeLineItem(idx)}
                              disabled={savingEdit}
                              title="Delete row"
                            >
                              <Trash2 size={12} />
                            </button>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                  <tfoot className="invoice-totals">
                    <tr className="totals-row-subtotal">
                      <td colSpan={4} className="totals-label">
                        Subtotal
                      </td>
                      <td colSpan={2} className="totals-value text-numeric">
                        {formatCurrency(calculateTotals().subtotal)}
                      </td>
                    </tr>
                    <tr className="totals-row-vat">
                      <td colSpan={4} className="totals-label">
                        VAT (20%)
                      </td>
                      <td colSpan={2} className="totals-value text-numeric">
                        {formatCurrency(calculateTotals().vat)}
                      </td>
                    </tr>
                    <tr className="totals-row-total">
                      <td colSpan={4} className="totals-label-total">
                        Total
                      </td>
                      <td colSpan={2} className="totals-value-total text-numeric">
                        {formatCurrency(calculateTotals().total)}
                      </td>
                    </tr>
                  </tfoot>
                </table>
              </div>
              <div style={{ marginTop: '8px', display: 'flex', justifyContent: 'flex-end' }}>
                <button
                  type="button"
                  className="glass-button"
                  onClick={addLineItem}
                  disabled={savingEdit}
                  style={{ fontSize: '11px', padding: '4px 8px', display: 'flex', alignItems: 'center', gap: '4px' }}
                >
                  <Plus size={12} />
                  Add Item
                </button>
              </div>
            </>
          ) : (
            // Read-only line items table
            <>
              {comparisonRows.length > 0 ? (
                <>
                  {comparisonRows.length > 10 && (
                    <button
                      className="glass-button"
                      onClick={() => setLineItemsExpanded(!lineItemsExpanded)}
                      style={{ marginBottom: '12px', fontSize: '12px', display: 'flex', alignItems: 'center', gap: '6px' }}
                    >
                      {lineItemsExpanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                      {lineItemsExpanded ? 'Collapse' : 'Expand'} line items ({comparisonRows.length})
                    </button>
                  )}
                  {(comparisonRows.length <= 10 || lineItemsExpanded) && (
                    <div className="invoice-line-items-table-wrapper" ref={lineItemsRef}>
                      <table className="invoice-line-items-table">
                        <thead>
                          <tr>
                            <th className="col-description">Name</th>
                            <th className="col-quantity">Qty</th>
                            <th className="col-quantity-dn">DN</th>
                            <th className="col-price">PPU</th>
                            <th className="col-total">Total</th>
                            <th className="col-status">Status</th>
                          </tr>
                        </thead>
                        <tbody>
                          {comparisonRows.map((row, idx) => {
                            // Find corresponding line item index in invoice.lineItems
                            const lineItemIndex = invoice.lineItems?.findIndex(item => 
                              (item.description || '').toLowerCase() === row.item.toLowerCase()
                            ) ?? null
                            
                            return (
                            <tr 
                              key={idx} 
                              className={row.status !== 'ok' ? 'mismatch' : ''}
                              data-line-item-description={row.item}
                              data-line-item-index={idx}
                              onMouseEnter={() => {
                                if (lineItemIndex !== null && lineItemIndex >= 0) {
                                  setHoveredLineItemIndex(lineItemIndex)
                                }
                              }}
                              onMouseLeave={() => setHoveredLineItemIndex(null)}
                              style={{
                                backgroundColor: hoveredLineItemIndex === lineItemIndex ? 'rgba(59, 130, 246, 0.1)' : 'transition',
                                transition: 'background-color 0.2s ease'
                              }}
                            >
                              <td className="col-description" data-label="Name">
                                <div className="line-item-description">{row.item}</div>
                              </td>
                              <td className="col-quantity text-numeric" data-label="Qty">
                                <span className="quantity-value">{row.invQty}</span>
                              </td>
                              <td className="col-quantity-dn text-numeric" data-label="DN">
                                {row.dnQty !== undefined ? (
                                  <span className="quantity-value">{row.dnQty}</span>
                                ) : (
                                  <span className="quantity-empty">—</span>
                                )}
                              </td>
                              <td className="col-price text-numeric" data-label="PPU">
                                <span className="price-value">{formatCurrency(row.price)}</span>
                              </td>
                              <td className="col-total text-numeric" data-label="Total">
                                <span className="total-value">{formatCurrency(row.lineTotal)}</span>
                              </td>
                              <td className="col-status" data-label="Status">
                                {row.status === 'not_matched' && (
                                  <span className="status-badge status-not-matched" title="No delivery note paired">
                                    No Match
                                  </span>
                                )}
                                {row.status === 'ok' && (
                                  <span className="status-badge status-matched" title="Quantities match">
                                    <Check size={10} style={{ marginRight: '3px' }} />
                                    OK
                                  </span>
                                )}
                                {row.status === 'short' && (
                                  <span 
                                    className="status-badge status-short" 
                                    title={`Under delivered: ${row.invQty! - (row.dnQty || 0)} units short`}
                                  >
                                    <AlertTriangle size={10} />
                                    Short
                                  </span>
                                )}
                                {row.status === 'over' && (
                                  <span 
                                    className="status-badge status-over" 
                                    title={`Over delivered: ${(row.dnQty || 0) - row.invQty!} units extra`}
                                  >
                                    <AlertTriangle size={10} />
                                    Over
                                  </span>
                                )}
                              </td>
                            </tr>
                            )
                          })}
                        </tbody>
                        <tfoot className="invoice-totals">
                          <tr className="totals-row-subtotal">
                            <td colSpan={3} className="totals-label">
                              Subtotal
                            </td>
                            <td colSpan={2} className="totals-value text-numeric">
                              {formatCurrency(displaySubtotal)}
                            </td>
                            <td className="col-status"></td>
                          </tr>
                          <tr className="totals-row-vat">
                            <td colSpan={3} className="totals-label">
                              VAT (20%)
                            </td>
                            <td colSpan={2} className="totals-value text-numeric">
                              {formatCurrency(displayVat)}
                            </td>
                            <td className="col-status"></td>
                          </tr>
                          <tr className="totals-row-total">
                            <td colSpan={3} className="totals-label-total">
                              Total
                            </td>
                            <td colSpan={2} className="totals-value-total text-numeric">
                              {formatCurrency(displayTotal)}
                            </td>
                            <td className="col-status"></td>
                          </tr>
                        </tfoot>
                      </table>
                    </div>
                  )}
                </>
              ) : (
                <div style={{ padding: '24px', textAlign: 'center', color: 'var(--text-muted)' }}>
                  No line items available
                </div>
              )}
            </>
          )}
        </div>
      </div>


      {/* Invoice vs Delivery Note Summary Card */}
      <div className="detail-card">
        <div className="detail-card-header">
          <h3 className="detail-card-title">Invoice & Delivery Note</h3>
        </div>
        <div className="detail-card-content">
          {/* Summary Boxes */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
            <div className="summary-box">
              <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginBottom: '4px' }}>Invoice</div>
              <div style={{ fontSize: '14px', fontWeight: '600' }}>
                {invoice.invoiceNumber || `INV-${invoice.id.slice(0, 8)}`}
              </div>
              <div style={{ fontSize: '12px', color: 'var(--text-secondary)', marginTop: '4px' }}>
                Lines: {invoice.lineItems?.length || 0}
              </div>
              <div style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
                Total: {formatCurrency(displayTotal)}
              </div>
            </div>
            <div className="summary-box">
              <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginBottom: '4px' }}>Delivery Note</div>
              {invoice.deliveryNote ? (
                <>
                  <div style={{ fontSize: '14px', fontWeight: '600' }}>
                    {invoice.deliveryNote.noteNumber || `DN-${invoice.deliveryNote.id.slice(0, 8)}`}
                  </div>
                  <div style={{ fontSize: '12px', color: 'var(--text-secondary)', marginTop: '4px' }}>
                    Lines: {invoice.deliveryNote.lineItems?.length || 0}
                  </div>
                  <div style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
                    Delivered: {formatDate(invoice.deliveryNote.date)}
                  </div>
                </>
              ) : (
                <div style={{ fontSize: '13px', color: 'var(--text-muted)' }}>No delivery note linked</div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Discussion & Log Card */}
      <div className="detail-card">
        <h3 className="detail-card-title" style={{ fontSize: '15px', fontWeight: '600', marginBottom: '16px' }}>Discussion & log</h3>
        <div className="detail-card-content">
          <textarea
            className="comment-textarea"
            placeholder="Add a note about this invoice…"
            rows={3}
            value={noteText}
            onChange={(e) => onNoteTextChange?.(e.target.value)}
            disabled={savingNote}
          />
          <button
            className="glass-button"
            style={{ marginTop: '8px', alignSelf: 'flex-start' }}
            onClick={onSaveNote}
            disabled={!noteText.trim() || savingNote}
          >
            {savingNote ? 'Saving...' : 'Save note'}
          </button>
          {/* Past notes would go here */}
        </div>
      </div>

      {/* Document Image Preview with Highlighted Extractions */}
      {invoice && invoice.status === 'scanned' && (
        <div className="detail-card document-preview-card">
          <div className="detail-card-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px', paddingBottom: '12px', borderBottom: '1px solid var(--border-color)' }}>
            <h3 className="detail-card-title" style={{ fontSize: '15px', fontWeight: '600', margin: 0 }}>Document Preview</h3>
            <div style={{ fontSize: '12px', color: 'var(--text-secondary)', display: 'flex', alignItems: 'center', gap: '8px' }}>
              {invoice.lineItems && invoice.lineItems.some(item => item.bbox) ? (
                <>
                  <div style={{ width: '8px', height: '8px', borderRadius: '2px', backgroundColor: 'rgba(0, 255, 0, 0.7)', border: '1px solid rgba(0, 255, 0, 0.9)' }} />
                  <span>Highlighted areas show extracted line items</span>
                </>
              ) : (
                <span>Image preview (no bounding box data available)</span>
              )}
            </div>
          </div>
          <div className="detail-card-content" style={{ padding: 0 }}>
            <InvoiceVisualizer
              docId={invoice.docId || invoice.documentId || invoice.id}
              lineItems={invoice.lineItems || []}
              activeLineItemIndex={hoveredLineItemIndex}
              onLineItemHover={setHoveredLineItemIndex}
            />
          </div>
        </div>
      )}
      
      {/* Pairing Preview Modal - Invoice to DN */}
      {invoice && previewDeliveryNoteId && (
        <PairingPreviewModal
          isOpen={previewModalOpen}
          onClose={() => {
            setPreviewModalOpen(false)
            setPreviewDeliveryNoteId(null)
            setPreviewValidation(null)
          }}
          onConfirm={handlePreviewConfirm}
          invoiceId={invoice.id}
          deliveryNoteId={previewDeliveryNoteId}
          initialValidation={previewValidation}
          invoiceLineItems={invoice.lineItems}
          deliveryNoteLineItems={deliveryNoteDetail?.lineItems}
        />
      )}
      
      {/* Pairing Preview Modal - DN to Invoice */}
      {selectedDNId && previewInvoiceId && (
        <PairingPreviewModal
          isOpen={previewModalOpen}
          onClose={() => {
            setPreviewModalOpen(false)
            setPreviewInvoiceId(null)
            setPreviewDeliveryNoteId(null)
            setPreviewValidation(null)
          }}
          onConfirm={handlePreviewConfirm}
          invoiceId={previewInvoiceId}
          deliveryNoteId={selectedDNId}
          initialValidation={previewValidation}
          invoiceLineItems={undefined}
          deliveryNoteLineItems={deliveryNoteDetail?.lineItems}
        />
      )}
    </div>
  )
}

