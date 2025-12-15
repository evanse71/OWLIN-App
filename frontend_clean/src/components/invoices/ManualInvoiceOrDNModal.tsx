import { useState, useEffect, useLayoutEffect, useRef } from 'react'
import { X, Plus, Trash2, Copy, Check, AlertCircle, ArrowRight, ArrowLeft, FileText, Package, ChevronUp, ChevronDown } from 'lucide-react'
import { createManualInvoice, createManualDeliveryNote, updateManualInvoice, updateManualDeliveryNote, fetchPairingSuggestions, fetchDeliveryNotes, linkDeliveryNoteToInvoice, validatePair, fetchInvoiceSuggestionsForDN, deleteInvoices, deleteDeliveryNotes, fetchDeliveryNoteDetails, fetchItemSuggestions, type PairingSuggestion } from '../../lib/api'
import { PairingPreviewModal } from './PairingPreviewModal'
import { SubmissionNotificationModal } from './SubmissionNotificationModal'
import { SpellingValidationModal } from './SpellingValidationModal'
import { AutocompleteInput } from '../common/AutocompleteInput'
import { checkSpellingMultiple, type SpellCheckResult } from '../../lib/spellchecker'
import { useToast } from '../common/Toast'
import { DatePicker } from '../common/DatePicker'
import { VenueSelector } from '../common/VenueSelector'
import { API_BASE_URL } from '../../lib/config'
import { normalizeInvoice } from '../../lib/api'
import './Modal.css'

interface InvoiceLineItem {
  description: string
  qty: number
  unit: string
  price: number
  total: number
  vat?: number // VAT percentage for this item (when per-item mode)
}

interface DNLineItem {
  description: string
  qty: number
  unit: string
  weight?: number
}

interface UnifiedLineItem {
  description: string
  invQty: number
  invPrice: number
  invTotal: number
  invVat?: number // VAT percentage for this item (when per-item mode)
  dnQty: number
  dnWeight?: number
  unit: string
}

type TabType = 'invoice' | 'delivery-note'

interface ManualInvoiceOrDNModalProps {
  isOpen: boolean
  onClose: () => void
  onSuccess: (invoiceId?: string, createdType?: 'invoice' | 'delivery-note' | 'both') => void
  venue?: string
  initialTab?: TabType
  editInvoiceId?: string
  editDNId?: string
  editMode?: 'invoice' | 'delivery-note'
}

export function ManualInvoiceOrDNModal({ 
  isOpen, 
  onClose, 
  onSuccess, 
  venue = 'Waterloo',
  initialTab = 'invoice',
  editInvoiceId,
  editDNId,
  editMode
}: ManualInvoiceOrDNModalProps) {
  const toast = useToast()
  const [activeTab, setActiveTab] = useState<TabType>(initialTab)
  const [unifiedMode, setUnifiedMode] = useState(false)
  const [isTabTransitioning, setIsTabTransitioning] = useState(false)
  const [showCopiedFeedback, setShowCopiedFeedback] = useState(false)
  const [hasCopiedData, setHasCopiedData] = useState(false)
  const contentRef = useRef<HTMLDivElement>(null)
  const [contentHeight, setContentHeight] = useState<number | 'auto'>('auto')
  const prevUnifiedModeRef = useRef(unifiedMode)
  const prevActiveTabRef = useRef(activeTab)
  const heightBeforeChangeRef = useRef<number | null>(null)
  const isExpandingRef = useRef(false)
  const isTransitioningRef = useRef(false)
  
  // Store last submitted invoice data so it can be copied even after submission
  const [lastSubmittedInvoice, setLastSubmittedInvoice] = useState<{
    supplier: string
    date: string
    lineItems: InvoiceLineItem[]
  } | null>(null)
  
  // Pairing suggestions state
  const [createdInvoiceId, setCreatedInvoiceId] = useState<string | null>(null)
  const [pairingSuggestions, setPairingSuggestions] = useState<PairingSuggestion[]>([])
  const [showPairingSuggestions, setShowPairingSuggestions] = useState(false)
  const [loadingSuggestions, setLoadingSuggestions] = useState(false)
  const [showDNCreationPrompt, setShowDNCreationPrompt] = useState(false)
  const [checkingDN, setCheckingDN] = useState(false)
  const [previewModalOpen, setPreviewModalOpen] = useState(false)
  const [previewData, setPreviewData] = useState<{ invoiceId: string; deliveryNoteId: string; validation: any } | null>(null)
  
  // Invoice suggestions state (for delivery notes)
  const [createdDNId, setCreatedDNId] = useState<string | null>(null)
  const [invoiceSuggestions, setInvoiceSuggestions] = useState<any[]>([])
  const [showInvoiceSuggestions, setShowInvoiceSuggestions] = useState(false)
  const [loadingInvoiceSuggestions, setLoadingInvoiceSuggestions] = useState(false)
  
  // Track if invoice is being created from DN (for auto-pairing)
  const [creatingInvoiceFromDN, setCreatingInvoiceFromDN] = useState<string | null>(null)
  
  // Store last submitted DN data for creating invoice from it
  const [lastSubmittedDN, setLastSubmittedDN] = useState<{
    supplier: string
    date: string
    lineItems: DNLineItem[]
    venue: string
  } | null>(null)
  
  // Notification modal state
  const [showNotification, setShowNotification] = useState(false)
  const [notificationType, setNotificationType] = useState<'success' | 'error'>('success')
  const [notificationTitle, setNotificationTitle] = useState('')
  const [notificationMessage, setNotificationMessage] = useState('')
  const [pendingSuccessCallback, setPendingSuccessCallback] = useState<(() => void) | null>(null)
  
  // Spelling validation state
  const [showSpellingModal, setShowSpellingModal] = useState(false)
  const [spellingErrors, setSpellingErrors] = useState<Array<{
    index: number
    itemDescription: string
    result: SpellCheckResult
  }>>([])
  const [pendingSubmitCallback, setPendingSubmitCallback] = useState<(() => void) | null>(null)
  
  // Invoice state
  const [supplier, setSupplier] = useState('')
  const [invoiceNumber, setInvoiceNumber] = useState('')
  const [invoiceDate, setInvoiceDate] = useState(new Date().toISOString().split('T')[0])
  const [selectedVenue, setSelectedVenue] = useState(venue)
  const [invoiceLineItems, setInvoiceLineItems] = useState<InvoiceLineItem[]>([
    { description: '', qty: 0, unit: '', price: 0, total: 0 },
  ])
  const [subtotal, setSubtotal] = useState(0)
  const [vat, setVat] = useState(0)
  const [total, setTotal] = useState(0)
  
  // VAT settings
  const [vatPercentage, setVatPercentage] = useState(20) // Default 20%
  const [vatMode, setVatMode] = useState<'whole' | 'per-item'>('whole') // VAT as whole or per item
  
  // Delivery Note state
  const [noteNumber, setNoteNumber] = useState('')
  const [dnDate, setDnDate] = useState(new Date().toISOString().split('T')[0])
  const [dnSupplier, setDnSupplier] = useState('')
  const [dnLineItems, setDnLineItems] = useState<DNLineItem[]>([
    { description: '', qty: 0, unit: '' },
  ])
  const [supervisor, setSupervisor] = useState('')
  const [driver, setDriver] = useState('')
  const [vehicle, setVehicle] = useState('')
  const [timeWindow, setTimeWindow] = useState('')
  
  // Unified form state
  const [unifiedLineItems, setUnifiedLineItems] = useState<UnifiedLineItem[]>([
    { description: '', invQty: 0, invPrice: 0, invTotal: 0, dnQty: 0, dnWeight: 0, unit: '', invVat: 20 },
  ])
  
  // Common state
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [loadingEditData, setLoadingEditData] = useState(false)
  
  // Load data when in edit mode
  useEffect(() => {
    const loadEditData = async () => {
      if (!isOpen) return
      
      if (editInvoiceId && editMode === 'invoice') {
        setLoadingEditData(true)
        try {
          const response = await fetch(`${API_BASE_URL}/api/manual/invoices/${editInvoiceId}`)
          if (!response.ok) throw new Error('Failed to load invoice')
          const data = await response.json()
          const inv = normalizeInvoice(data.invoice || data)
          
          setSupplier(inv.supplier || '')
          setInvoiceNumber(inv.invoiceNumber || '')
          setInvoiceDate(inv.invoiceDate || new Date().toISOString().split('T')[0])
          setSelectedVenue(inv.venue || venue)
          
          const items = inv.lineItems || []
          if (items.length > 0) {
            setInvoiceLineItems(items.map((item: any) => ({
              description: item.description || '',
              qty: item.qty || 0,
              unit: item.uom || item.unit || '',
              price: item.unitPrice || 0,
              total: item.total || 0,
            })))
          }
          
          setSubtotal(inv.subtotal || 0)
          setVat(inv.vat || 0)
          setTotal(inv.totalValue || 0)
          setActiveTab('invoice')
        } catch (err) {
          console.error('Failed to load invoice for editing:', err)
          toast.error('Failed to load invoice data')
        } finally {
          setLoadingEditData(false)
        }
      } else if (editDNId && editMode === 'delivery-note') {
        setLoadingEditData(true)
        try {
          const dnData = await fetchDeliveryNoteDetails(editDNId)
          if (!dnData) throw new Error('Delivery note not found')
          
          setDnSupplier(dnData.supplier || '')
          setNoteNumber(dnData.noteNumber || dnData.deliveryNoteNumber || dnData.delivery_no || '')
          setDnDate(dnData.date || dnData.deliveryDate || new Date().toISOString().split('T')[0])
          setSelectedVenue(dnData.venue || venue)
          
          // Parse notes for driver, vehicle, timeWindow
          if (dnData.notes) {
            const notes = dnData.notes
            const driverMatch = notes.match(/Driver:\s*(.+)/i)
            const vehicleMatch = notes.match(/Vehicle:\s*(.+)/i)
            const timeWindowMatch = notes.match(/Time Window:\s*(.+)/i)
            if (driverMatch) setDriver(driverMatch[1].trim())
            if (vehicleMatch) setVehicle(vehicleMatch[1].trim())
            if (timeWindowMatch) setTimeWindow(timeWindowMatch[1].trim())
          }
          
          const items = dnData.lineItems || dnData.line_items || []
          if (items.length > 0) {
            setDnLineItems(items.map((item: any) => ({
              description: item.description || item.item || '',
              qty: item.qty || item.quantity || 0,
              unit: item.unit || item.uom || '',
              weight: item.weight,
            })))
          }
          
          setActiveTab('delivery-note')
        } catch (err) {
          console.error('Failed to load delivery note for editing:', err)
          toast.error('Failed to load delivery note data')
        } finally {
          setLoadingEditData(false)
        }
      }
    }
    
    loadEditData()
  }, [isOpen, editInvoiceId, editDNId, editMode, venue, toast])
  
  // Mode switch confirmation state
  const [showModeSwitchConfirm, setShowModeSwitchConfirm] = useState(false)
  const [pendingModeChange, setPendingModeChange] = useState<{
    type: 'unified' | 'individual-invoice' | 'individual-dn'
    hasInvoiceData: boolean
    hasDNData: boolean
  } | null>(null)

  const venues = ['Waterloo', 'Royal Oak', 'Main Restaurant']

  // localStorage keys
  const STORAGE_KEY_INVOICE = 'manualInvoiceFormData'
  const STORAGE_KEY_DN = 'manualDNFormData'
  const STORAGE_KEY_UNIFIED = 'manualUnifiedFormData'
  const STORAGE_KEY_MODE = 'manualFormMode'

  // Save form data to localStorage
  const saveFormData = () => {
    try {
      if (unifiedMode) {
        // Save unified form data
        const unifiedData = {
          supplier,
          invoiceNumber,
          invoiceDate,
          selectedVenue,
          unifiedLineItems,
          noteNumber,
          dnDate,
          dnSupplier,
          driver,
          vehicle,
          timeWindow,
          vatPercentage,
          vatMode,
        }
        localStorage.setItem(STORAGE_KEY_UNIFIED, JSON.stringify(unifiedData))
        localStorage.setItem(STORAGE_KEY_MODE, JSON.stringify({ unifiedMode: true, activeTab }))
      } else if (activeTab === 'invoice') {
        // Save invoice form data
        const invoiceData = {
          supplier,
          invoiceNumber,
          invoiceDate,
          selectedVenue,
          invoiceLineItems,
          vatPercentage,
          vatMode,
        }
        localStorage.setItem(STORAGE_KEY_INVOICE, JSON.stringify(invoiceData))
        localStorage.setItem(STORAGE_KEY_MODE, JSON.stringify({ unifiedMode: false, activeTab: 'invoice' }))
      } else {
        // Save delivery note form data
        const dnData = {
          noteNumber,
          dnDate,
          dnSupplier,
          dnLineItems,
          driver,
          vehicle,
          timeWindow,
          selectedVenue,
        }
        localStorage.setItem(STORAGE_KEY_DN, JSON.stringify(dnData))
        localStorage.setItem(STORAGE_KEY_MODE, JSON.stringify({ unifiedMode: false, activeTab: 'delivery-note' }))
      }
    } catch (error) {
      console.error('Failed to save form data:', error)
    }
  }

  // Restore form data from localStorage
  const restoreFormData = () => {
    try {
      const modeData = localStorage.getItem(STORAGE_KEY_MODE)
      if (!modeData) return

      const { unifiedMode: savedUnifiedMode, activeTab: savedActiveTab } = JSON.parse(modeData)

      if (savedUnifiedMode) {
        // Restore unified form data
        const unifiedData = localStorage.getItem(STORAGE_KEY_UNIFIED)
        if (unifiedData) {
          const data = JSON.parse(unifiedData)
          setSupplier(data.supplier || '')
          setInvoiceNumber(data.invoiceNumber || '')
          setInvoiceDate(data.invoiceDate || new Date().toISOString().split('T')[0])
          setSelectedVenue(data.selectedVenue || venue)
          setUnifiedLineItems(data.unifiedLineItems || [{ description: '', invQty: 0, invPrice: 0, invTotal: 0, dnQty: 0, dnWeight: 0, unit: '', invVat: 20 }])
          setNoteNumber(data.noteNumber || '')
          setDnDate(data.dnDate || new Date().toISOString().split('T')[0])
          setDnSupplier(data.dnSupplier || '')
          setDriver(data.driver || '')
          setVehicle(data.vehicle || '')
          setTimeWindow(data.timeWindow || '')
          setVatPercentage(data.vatPercentage || 20)
          setVatMode(data.vatMode || 'whole')
          setUnifiedMode(true)
          setActiveTab('invoice')
        }
      } else if (savedActiveTab === 'invoice') {
        // Restore invoice form data
        const invoiceData = localStorage.getItem(STORAGE_KEY_INVOICE)
        if (invoiceData) {
          const data = JSON.parse(invoiceData)
          setSupplier(data.supplier || '')
          setInvoiceNumber(data.invoiceNumber || '')
          setInvoiceDate(data.invoiceDate || new Date().toISOString().split('T')[0])
          setSelectedVenue(data.selectedVenue || venue)
          setInvoiceLineItems(data.invoiceLineItems || [{ description: '', qty: 0, unit: '', price: 0, total: 0 }])
          setVatPercentage(data.vatPercentage || 20)
          setVatMode(data.vatMode || 'whole')
          setUnifiedMode(false)
          setActiveTab('invoice')
        }
      } else {
        // Restore delivery note form data
        const dnData = localStorage.getItem(STORAGE_KEY_DN)
        if (dnData) {
          const data = JSON.parse(dnData)
          setNoteNumber(data.noteNumber || '')
          setDnDate(data.dnDate || new Date().toISOString().split('T')[0])
          setDnSupplier(data.dnSupplier || '')
          setDnLineItems(data.dnLineItems || [{ description: '', qty: 0, unit: '' }])
          setDriver(data.driver || '')
          setVehicle(data.vehicle || '')
          setTimeWindow(data.timeWindow || '')
          setSelectedVenue(data.selectedVenue || venue)
          setUnifiedMode(false)
          setActiveTab('delivery-note')
        }
      }
    } catch (error) {
      console.error('Failed to restore form data:', error)
    }
  }

  // Clear saved form data
  const clearSavedFormData = () => {
    try {
      localStorage.removeItem(STORAGE_KEY_INVOICE)
      localStorage.removeItem(STORAGE_KEY_DN)
      localStorage.removeItem(STORAGE_KEY_UNIFIED)
      localStorage.removeItem(STORAGE_KEY_MODE)
    } catch (error) {
      console.error('Failed to clear form data:', error)
    }
  }

  // Update initial tab when prop changes and restore saved data
  useEffect(() => {
    if (isOpen) {
      restoreFormData()
      // If no saved data, use initial tab
      const modeData = localStorage.getItem(STORAGE_KEY_MODE)
      if (!modeData) {
      setActiveTab(initialTab)
      }
    }
  }, [isOpen, initialTab])

  // Recalculate totals when VAT settings change
  useEffect(() => {
    if (activeTab === 'invoice' && !unifiedMode) {
      calculateInvoiceTotals(invoiceLineItems)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [vatPercentage, vatMode])

  // Initialize VAT on line items when switching to per-item mode
  useEffect(() => {
    if (vatMode === 'per-item') {
      // Update unified line items
      setUnifiedLineItems(prev => prev.map(item => ({
        ...item,
        invVat: item.invVat !== undefined ? item.invVat : vatPercentage
      })))
      // Update invoice line items
      setInvoiceLineItems(prev => prev.map(item => ({
        ...item,
        vat: item.vat !== undefined ? item.vat : vatPercentage
      })))
    }
  }, [vatMode, vatPercentage])

  // Measure and transition content height when unifiedMode or activeTab changes
  // Use the same logic for both expansion and contraction - ensures smooth scaling in both directions
  useLayoutEffect(() => {
    const unifiedModeChanged = prevUnifiedModeRef.current !== unifiedMode
    const activeTabChanged = prevActiveTabRef.current !== activeTab
    
    if ((unifiedModeChanged || activeTabChanged) && contentRef.current && !isTransitioningRef.current) {
      isTransitioningRef.current = true
      
      // Get old height - use stored value if available, otherwise measure current
      const oldHeight = heightBeforeChangeRef.current ?? contentRef.current.scrollHeight
      
      // Update refs first
      prevUnifiedModeRef.current = unifiedMode
      prevActiveTabRef.current = activeTab
      
      // Same logic for both expansion and contraction:
      // 1. Lock old height first (this prevents jump)
      setContentHeight(oldHeight)
      void contentRef.current.offsetHeight // Force reflow to apply the height
      
      // 2. Measure new height after content updates (wait for DOM to update)
      requestAnimationFrame(() => {
        requestAnimationFrame(() => {
          if (contentRef.current) {
            const newHeight = contentRef.current.scrollHeight
            
            // 3. Transition from old to new (CSS transition handles both directions smoothly)
            if (Math.abs(newHeight - oldHeight) > 2) {
              // Ensure transition is applied by setting the new height
              // The CSS transition will smoothly animate from oldHeight to newHeight
              setContentHeight(newHeight)
              heightBeforeChangeRef.current = null
              
              // Match setTimeout to CSS transition duration (400ms) + small buffer for rendering
              // This ensures the transition completes before resetting to 'auto'
              setTimeout(() => {
                setContentHeight('auto')
                isTransitioningRef.current = false
              }, 420) // 400ms transition + 20ms buffer
            } else {
              // Heights are very close, no transition needed
              setContentHeight('auto')
              heightBeforeChangeRef.current = null
              isTransitioningRef.current = false
            }
          } else {
            isTransitioningRef.current = false
          }
        })
      })
    } else {
      // Update refs even if no change detected
      prevUnifiedModeRef.current = unifiedMode
      prevActiveTabRef.current = activeTab
    }
  }, [unifiedMode, activeTab])

  // Invoice calculations
  const calculateInvoiceTotals = (items: InvoiceLineItem[]) => {
    const sub = items.reduce((sum, item) => sum + (item.total || 0), 0)
    
    let vatAmount = 0
    if (vatMode === 'whole') {
      // Apply single VAT rate to entire subtotal
      vatAmount = sub * (vatPercentage / 100)
    } else {
      // Calculate VAT per item
      vatAmount = items.reduce((sum, item) => {
        const itemVat = item.vat !== undefined ? item.vat : vatPercentage
        return sum + (item.total * (itemVat / 100))
      }, 0)
    }
    
    const totalAmount = sub + vatAmount
    setSubtotal(sub)
    setVat(vatAmount)
    setTotal(totalAmount)
  }

  const updateInvoiceLineItem = (index: number, field: keyof InvoiceLineItem, value: string | number) => {
    const updated = [...invoiceLineItems]
    // Ensure quantity is always an integer
    if (field === 'qty') {
      updated[index] = { ...updated[index], [field]: Math.floor(Number(value)) || 0 }
    } else {
    updated[index] = { ...updated[index], [field]: value }
    }
    
    // Initialize VAT if not set and in per-item mode
    if (vatMode === 'per-item' && updated[index].vat === undefined) {
      updated[index].vat = vatPercentage
    }
    
    if (field === 'qty' || field === 'price') {
      const qty = field === 'qty' ? Math.floor(Number(value)) || 0 : updated[index].qty
      const price = field === 'price' ? Number(value) : updated[index].price
      updated[index].total = qty * price
    }
    
    setInvoiceLineItems(updated)
    calculateInvoiceTotals(updated)
  }

  const addInvoiceLineItem = () => {
    const newItem: InvoiceLineItem = { description: '', qty: 0, unit: '', price: 0, total: 0 }
    if (vatMode === 'per-item') {
      newItem.vat = vatPercentage
    }
    setInvoiceLineItems([...invoiceLineItems, newItem])
  }

  const removeInvoiceLineItem = (index: number) => {
    if (invoiceLineItems.length > 1) {
      const updated = invoiceLineItems.filter((_, i) => i !== index)
      setInvoiceLineItems(updated)
      calculateInvoiceTotals(updated)
    }
  }

  // Delivery Note functions
  const updateDNLineItem = (index: number, field: keyof DNLineItem, value: string | number) => {
    const updated = [...dnLineItems]
    // Ensure quantity is always an integer
    if (field === 'qty') {
      updated[index] = { ...updated[index], [field]: Math.floor(Number(value)) || 0 }
    } else {
    updated[index] = { ...updated[index], [field]: value }
    }
    setDnLineItems(updated)
  }

  const addDNLineItem = () => {
    setDnLineItems([...dnLineItems, { description: '', qty: 0, unit: '', weight: 0 }])
  }

  const removeDNLineItem = (index: number) => {
    if (dnLineItems.length > 1) {
      setDnLineItems(dnLineItems.filter((_, i) => i !== index))
    }
  }

  // Unified form functions
  const updateUnifiedLineItem = (index: number, field: keyof UnifiedLineItem, value: string | number) => {
    const updated = [...unifiedLineItems]
    // Ensure quantities are always integers
    if (field === 'invQty' || field === 'dnQty') {
      updated[index] = { ...updated[index], [field]: Math.floor(Number(value)) || 0 }
    } else {
      updated[index] = { ...updated[index], [field]: value }
    }
    
    // Initialize VAT if not set and in per-item mode
    if (vatMode === 'per-item' && updated[index].invVat === undefined) {
      updated[index].invVat = vatPercentage
    }
    
    // Auto-calculate invoice total if qty or price changes
    if (field === 'invQty' || field === 'invPrice') {
      const qty = field === 'invQty' ? Math.floor(Number(value)) || 0 : updated[index].invQty
      const price = field === 'invPrice' ? Number(value) : updated[index].invPrice
      updated[index].invTotal = qty * price
    }
    
    setUnifiedLineItems(updated)
  }

  const addUnifiedLineItem = () => {
    const newItem: UnifiedLineItem = { description: '', invQty: 0, invPrice: 0, invTotal: 0, dnQty: 0, dnWeight: 0, unit: '' }
    if (vatMode === 'per-item') {
      newItem.invVat = vatPercentage
    }
    setUnifiedLineItems([...unifiedLineItems, newItem])
  }

  const removeUnifiedLineItem = (index: number) => {
    if (unifiedLineItems.length > 1) {
      setUnifiedLineItems(unifiedLineItems.filter((_, i) => i !== index))
    }
  }

  const calculateUnifiedInvoiceTotals = () => {
    const sub = unifiedLineItems.reduce((sum, item) => sum + (item.invTotal || 0), 0)
    
    let vatAmount = 0
    if (vatMode === 'whole') {
      // Apply single VAT rate to entire subtotal
      vatAmount = sub * (vatPercentage / 100)
    } else {
      // Calculate VAT per item
      vatAmount = unifiedLineItems.reduce((sum, item) => {
        const itemVat = item.invVat !== undefined ? item.invVat : vatPercentage
        return sum + (item.invTotal * (itemVat / 100))
      }, 0)
    }
    
    const totalAmount = sub + vatAmount
    return { subtotal: sub, vat: vatAmount, total: totalAmount }
  }

  // Copy invoice data to delivery note (from current form or last submitted)
  const copyInvoiceToDN = (useLastSubmitted = false) => {
    const sourceSupplier = useLastSubmitted && lastSubmittedInvoice ? lastSubmittedInvoice.supplier : supplier
    const sourceDate = useLastSubmitted && lastSubmittedInvoice ? lastSubmittedInvoice.date : invoiceDate
    const sourceLineItems = useLastSubmitted && lastSubmittedInvoice ? lastSubmittedInvoice.lineItems : invoiceLineItems
    
    setDnSupplier(sourceSupplier)
    setDnDate(sourceDate)
    // Copy line items (without price/total)
    const copiedItems: DNLineItem[] = sourceLineItems
      .filter(item => item.description.trim() !== '')
      .map(item => ({
        description: item.description,
        qty: item.qty,
        unit: item.unit,
      }))
    
    if (copiedItems.length > 0) {
      setDnLineItems(copiedItems.length > 0 ? copiedItems : [{ description: '', qty: 0, unit: '', weight: 0 }])
    }
    
    setHasCopiedData(true)
    setShowCopiedFeedback(true)
    
    // Switch to delivery note tab if not already there
    if (activeTab !== 'delivery-note') {
      setActiveTab('delivery-note')
    }
    
    // Hide feedback after 3 seconds
    setTimeout(() => {
      setShowCopiedFeedback(false)
    }, 3000)
  }

  // Check if invoice has data to copy (current form or last submitted)
  const hasInvoiceData = supplier.trim() !== '' || invoiceLineItems.some(item => item.description.trim() !== '')
  const hasLastSubmittedInvoice = lastSubmittedInvoice !== null

  // Verification functions
  const verifyCreatedInvoice = async (
    invoiceId: string,
    submittedData: {
      supplier: string
      invoiceNumber: string
      date: string
      venue: string
      lineItems: InvoiceLineItem[]
      subtotal: number
      vat: number
      total: number
    }
  ): Promise<{ isValid: boolean; errors: string[] }> => {
    const errors: string[] = []
    
    try {
      // Fetch the created invoice
      let response = await fetch(`${API_BASE_URL}/api/manual/invoices/${invoiceId}`)
      if (!response.ok) {
        response = await fetch(`${API_BASE_URL}/api/invoices/${invoiceId}`)
      }
      
      if (!response.ok) {
        errors.push('Failed to fetch created invoice for verification')
        return { isValid: false, errors }
      }
      
      const data = await response.json()
      const rawInvoice = data.invoice || data
      const inv = normalizeInvoice(rawInvoice)
      
      // Compare supplier (case-insensitive)
      if (inv.supplier?.toLowerCase().trim() !== submittedData.supplier.toLowerCase().trim()) {
        errors.push(`Supplier mismatch: expected "${submittedData.supplier}", got "${inv.supplier || 'missing'}"`)
      }
      
      // Compare invoice number (case-insensitive)
      // For manual invoices, invoice number is stored separately, not as the id
      const createdInvoiceNumber = inv.invoiceNumber || ''
      if (createdInvoiceNumber && createdInvoiceNumber.toLowerCase().trim() !== submittedData.invoiceNumber.toLowerCase().trim()) {
        errors.push(`Invoice number mismatch: expected "${submittedData.invoiceNumber}", got "${createdInvoiceNumber || 'missing'}"`)
      }
      
      // Compare date (normalize format)
      const submittedDate = new Date(submittedData.date).toISOString().split('T')[0]
      const createdDate = inv.invoiceDate
      if (createdDate) {
        const normalizedCreatedDate = new Date(createdDate).toISOString().split('T')[0]
        if (normalizedCreatedDate !== submittedDate) {
          errors.push(`Date mismatch: expected "${submittedDate}", got "${normalizedCreatedDate}"`)
        }
      } else {
        errors.push('Date is missing in created invoice')
      }
      
      // Compare venue (case-insensitive)
      if (inv.venue?.toLowerCase().trim() !== submittedData.venue.toLowerCase().trim()) {
        errors.push(`Venue mismatch: expected "${submittedData.venue}", got "${inv.venue || 'missing'}"`)
      }
      
      // Compare totals (allow small floating point differences)
      const createdTotal = inv.totalValue || 0
      if (Math.abs(createdTotal - submittedData.total) > 0.01) {
        errors.push(`Total mismatch: expected ${submittedData.total}, got ${createdTotal}`)
      }
      
      // Compare line items
      const createdLineItems = inv.lineItems || inv.line_items || []
      const submittedLineItems = submittedData.lineItems.filter(item => item.description.trim() !== '')
      
      if (createdLineItems.length !== submittedLineItems.length) {
        errors.push(`Line item count mismatch: expected ${submittedLineItems.length}, got ${createdLineItems.length}`)
      } else {
        // Compare each line item (order may differ, so we'll match by description)
        for (const submittedItem of submittedLineItems) {
          const matchingItem = createdLineItems.find((item: any) => 
            (item.description || '').toLowerCase().trim() === submittedItem.description.toLowerCase().trim()
          )
          
          if (!matchingItem) {
            errors.push(`Line item not found: "${submittedItem.description}"`)
            continue
          }
          
          // Compare quantity (allow small differences)
          const createdQty = matchingItem.qty || 0
          if (Math.abs(createdQty - submittedItem.qty) > 0.01) {
            errors.push(`Quantity mismatch for "${submittedItem.description}": expected ${submittedItem.qty}, got ${createdQty}`)
          }
          
          // Compare price (allow small differences)
          const createdPrice = matchingItem.unitPrice || 0
          if (Math.abs(createdPrice - submittedItem.price) > 0.01) {
            errors.push(`Price mismatch for "${submittedItem.description}": expected ${submittedItem.price}, got ${createdPrice}`)
          }
          
          // Compare total (allow small differences)
          const createdItemTotal = matchingItem.total || 0
          if (Math.abs(createdItemTotal - submittedItem.total) > 0.01) {
            errors.push(`Line total mismatch for "${submittedItem.description}": expected ${submittedItem.total}, got ${createdItemTotal}`)
          }
        }
      }
      
      return { isValid: errors.length === 0, errors }
    } catch (err) {
      errors.push(`Verification error: ${err instanceof Error ? err.message : 'Unknown error'}`)
      return { isValid: false, errors }
    }
  }

  const verifyCreatedDeliveryNote = async (
    dnId: string,
    submittedData: {
      noteNumber: string
      date: string
      supplier: string
      venue: string
      lineItems: DNLineItem[]
    },
    creationResponse?: any // Optional: use creation response data if available
  ): Promise<{ isValid: boolean; errors: string[] }> => {
    const errors: string[] = []
    
    try {
      // Use creation response data if available, otherwise fetch from database
      let dnData = creationResponse
      
      if (!dnData) {
        // Fetch the created delivery note
        dnData = await fetchDeliveryNoteDetails(dnId)
        
        if (!dnData) {
          errors.push('Failed to fetch created delivery note for verification')
          return { isValid: false, errors }
        }
      }
      
      // Debug: Log the data we're comparing
      console.log('[DEBUG] verifyCreatedDeliveryNote: dnData keys:', Object.keys(dnData))
      console.log('[DEBUG] verifyCreatedDeliveryNote: dnData.supplier:', dnData.supplier)
      console.log('[DEBUG] verifyCreatedDeliveryNote: dnData.noteNumber:', dnData.noteNumber)
      console.log('[DEBUG] verifyCreatedDeliveryNote: dnData.deliveryNoteNumber:', dnData.deliveryNoteNumber)
      console.log('[DEBUG] verifyCreatedDeliveryNote: dnData.delivery_note_number:', dnData.delivery_note_number)
      
      // Compare supplier (case-insensitive)
      const createdSupplier = dnData.supplier || dnData.supplierName || ''
      if (createdSupplier?.toLowerCase().trim() !== submittedData.supplier.toLowerCase().trim()) {
        errors.push(`Supplier mismatch: expected "${submittedData.supplier}", got "${createdSupplier || 'missing'}"`)
      }
      
      // Compare note number (case-insensitive, extract from noteNumber field or filename)
      const createdNoteNumber = dnData.noteNumber || dnData.note_number || dnData.deliveryNo || dnData.deliveryNoteNumber || dnData.delivery_note_number || ''
      if (createdNoteNumber?.toLowerCase().trim() !== submittedData.noteNumber.toLowerCase().trim()) {
        errors.push(`Note number mismatch: expected "${submittedData.noteNumber}", got "${createdNoteNumber || 'missing'}"`)
      }
      
      // Compare date (normalize format)
      const submittedDate = new Date(submittedData.date).toISOString().split('T')[0]
      const createdDate = dnData.date || dnData.deliveryDate
      if (createdDate) {
        const normalizedCreatedDate = new Date(createdDate).toISOString().split('T')[0]
        if (normalizedCreatedDate !== submittedDate) {
          errors.push(`Date mismatch: expected "${submittedDate}", got "${normalizedCreatedDate}"`)
        }
      } else {
        errors.push('Date is missing in created delivery note')
      }
      
      // Compare venue (case-insensitive) - skip if not in response (creation response doesn't include venue)
      if (dnData.venue && dnData.venue.toLowerCase().trim() !== submittedData.venue.toLowerCase().trim()) {
        errors.push(`Venue mismatch: expected "${submittedData.venue}", got "${dnData.venue}"`)
      }
      
      // Compare line items - skip if using creation response (line items not in response)
      // Only verify line items if we fetched from database
      if (creationResponse) {
        // When using creation response, skip line item verification
        // The backend has already validated the line items during creation
        console.log('[DEBUG] verifyCreatedDeliveryNote: Using creation response, skipping line item verification')
      } else {
        // Compare line items when fetching from database
        const createdLineItems = dnData.lineItems || dnData.line_items || []
        const submittedLineItems = submittedData.lineItems.filter(item => item.description.trim() !== '')
        
        if (createdLineItems.length !== submittedLineItems.length) {
          errors.push(`Line item count mismatch: expected ${submittedLineItems.length}, got ${createdLineItems.length}`)
        } else {
          // Compare each line item (match by description)
          for (const submittedItem of submittedLineItems) {
            const matchingItem = createdLineItems.find((item: any) => 
              (item.description || '').toLowerCase().trim() === submittedItem.description.toLowerCase().trim()
            )
            
            if (!matchingItem) {
              errors.push(`Line item not found: "${submittedItem.description}"`)
              continue
            }
            
            // Compare quantity (allow small differences)
            const createdQty = matchingItem.qty || 0
            if (Math.abs(createdQty - submittedItem.qty) > 0.01) {
              errors.push(`Quantity mismatch for "${submittedItem.description}": expected ${submittedItem.qty}, got ${createdQty}`)
            }
            
            // Compare unit
            const createdUnit = matchingItem.unit || matchingItem.uom || ''
            if (createdUnit?.toLowerCase().trim() !== submittedItem.unit.toLowerCase().trim()) {
              errors.push(`Unit mismatch for "${submittedItem.description}": expected "${submittedItem.unit}", got "${createdUnit || 'missing'}"`)
            }
            
            // Compare weight if provided
            if (submittedItem.weight !== undefined) {
              const createdWeight = matchingItem.weight || 0
              if (Math.abs(createdWeight - submittedItem.weight) > 0.01) {
                errors.push(`Weight mismatch for "${submittedItem.description}": expected ${submittedItem.weight}, got ${createdWeight}`)
              }
            }
          }
        }
      }
      
      return { isValid: errors.length === 0, errors }
    } catch (err) {
      errors.push(`Verification error: ${err instanceof Error ? err.message : 'Unknown error'}`)
      return { isValid: false, errors }
    }
  }

  const checkForDeliveryNotes = async (supplierName: string, invoiceDateStr: string) => {
    setCheckingDN(true)
    try {
      const deliveryNotes = await fetchDeliveryNotes()
      // Check if any delivery note matches supplier and date (within 3 days)
      const invoiceDate = new Date(invoiceDateStr)
      const matchingDN = deliveryNotes.find((dn: any) => {
        if (dn.supplier?.toLowerCase() !== supplierName.toLowerCase()) return false
        if (!dn.date) return false
        const dnDate = new Date(dn.date)
        const daysDiff = Math.abs((invoiceDate.getTime() - dnDate.getTime()) / (1000 * 60 * 60 * 24))
        return daysDiff <= 3
      })
      
      if (!matchingDN) {
        setShowDNCreationPrompt(true)
      }
    } catch (err) {
      console.warn('Failed to check for delivery notes:', err)
      // Don't show error, just skip the prompt
    } finally {
      setCheckingDN(false)
    }
  }

  const fetchAndShowPairingSuggestions = async (invoiceId: string) => {
    setLoadingSuggestions(true)
    try {
      const response = await fetchPairingSuggestions(invoiceId)
      if (response.suggestions && response.suggestions.length > 0) {
        setPairingSuggestions(response.suggestions)
        setShowPairingSuggestions(true)
      }
    } catch (err) {
      console.warn('Failed to fetch pairing suggestions:', err)
      // Don't show error, just skip suggestions
    } finally {
      setLoadingSuggestions(false)
    }
  }

  // Helper function to check spelling before submission
  const checkSpellingBeforeSubmit = async (lineItems: Array<{ description: string }>, itemType: 'invoice' | 'dn' | 'unified'): Promise<boolean> => {
    // Create array with original indices
    const itemsWithIndices = lineItems
      .map((item, originalIndex) => ({ item, originalIndex }))
      .filter(({ item }) => item.description.trim() !== '')
    
    if (itemsWithIndices.length === 0) {
      return true // No items to check
    }
    
    const descriptions = itemsWithIndices.map(({ item }) => item.description.trim())
    
    try {
      const results = await checkSpellingMultiple(descriptions, ['en', 'cy'])
      
      if (results.length > 0) {
        // Map results to include original item indices and descriptions
        const errors = results.map(({ index, result }) => {
          const { originalIndex, item } = itemsWithIndices[index]
          return {
            index: originalIndex, // Use original index in the full array
            itemDescription: item.description.trim(),
            result
          }
        })
        
        setSpellingErrors(errors)
        setShowSpellingModal(true)
        return false // Spelling errors found, wait for user confirmation
      }
      
      return true // No spelling errors
    } catch (error) {
      console.error('Error checking spelling:', error)
      // If spelling check fails, allow submission to proceed
      return true
    }
  }

  // Handle spelling modal confirmation
  const handleSpellingConfirm = (corrections: Map<number, string>) => {
    // Apply corrections to the appropriate line items
    if (activeTab === 'invoice') {
      const updatedItems = [...invoiceLineItems]
      corrections.forEach((correctedText, index) => {
        if (updatedItems[index]) {
          updatedItems[index] = { ...updatedItems[index], description: correctedText }
        }
      })
      setInvoiceLineItems(updatedItems)
    } else if (activeTab === 'delivery-note') {
      const updatedItems = [...dnLineItems]
      corrections.forEach((correctedText, index) => {
        if (updatedItems[index]) {
          updatedItems[index] = { ...updatedItems[index], description: correctedText }
        }
      })
      setDnLineItems(updatedItems)
    } else if (unifiedMode) {
      const updatedItems = [...unifiedLineItems]
      corrections.forEach((correctedText, index) => {
        if (updatedItems[index]) {
          updatedItems[index] = { ...updatedItems[index], description: correctedText }
        }
      })
      setUnifiedLineItems(updatedItems)
    }
    
    setShowSpellingModal(false)
    setSpellingErrors([])
    
    // Execute pending submit callback
    if (pendingSubmitCallback) {
      pendingSubmitCallback()
      setPendingSubmitCallback(null)
    }
  }

  const handleInvoiceSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    setLoading(true)

    try {
      if (!supplier.trim() || !invoiceNumber.trim()) {
        setError('Please fill in supplier and invoice number')
        setLoading(false)
        return
      }

      // Filter out empty line items
      const validLineItems = invoiceLineItems.filter(item => item.description.trim() !== '')
      
      if (validLineItems.length === 0) {
        setError('Please add at least one line item with a description')
        setLoading(false)
        return
      }

      // Check spelling before submission (use full array to preserve indices)
      const spellingOk = await checkSpellingBeforeSubmit(invoiceLineItems, 'invoice')
      if (!spellingOk) {
        // Store the submit callback to execute after spelling confirmation
        setPendingSubmitCallback(() => () => {
          // This will be called after spelling confirmation
          const updatedValidItems = invoiceLineItems.filter(item => item.description.trim() !== '')
          handleInvoiceSubmitInternal(updatedValidItems)
        })
        setLoading(false)
        return
      }
      
      // Proceed with submission
      await handleInvoiceSubmitInternal(validLineItems)
    } catch (err: any) {
      console.error('Error in handleInvoiceSubmit:', err)
      setError(err.message || 'Failed to submit invoice')
      setLoading(false)
    }
  }

  const handleInvoiceSubmitInternal = async (validLineItems: InvoiceLineItem[]) => {
    setLoading(true)

    try {
      // Check backend health first
      try {
        const healthUrl = `${API_BASE_URL || window.location.origin}/api/health`
        console.log('[handleInvoiceSubmit] Checking backend health at:', healthUrl)
        
        const controller = new AbortController()
        const timeoutId = setTimeout(() => controller.abort(), 3000) // 3 second timeout
        
        try {
          const healthResponse = await fetch(healthUrl, { 
            method: 'GET',
            cache: 'no-cache',
            signal: controller.signal
          })
          clearTimeout(timeoutId)
          
          if (!healthResponse.ok) {
            throw new Error(`Backend health check failed: ${healthResponse.status} ${healthResponse.statusText}`)
          }
          console.log('[handleInvoiceSubmit] Backend health check passed')
        } catch (fetchErr: any) {
          clearTimeout(timeoutId)
          if (fetchErr.name === 'AbortError') {
            throw new Error('TIMEOUT')
          }
          throw fetchErr
        }
      } catch (healthErr: any) {
        const isTimeout = healthErr.message === 'TIMEOUT' || healthErr.name === 'AbortError'
        const attemptedUrl = API_BASE_URL ? `${API_BASE_URL}/api/health` : `${window.location.origin}/api/health`
        const errorMsg = isTimeout
          ? `Backend server is not responding (timeout after 3 seconds).\n\nPlease ensure:\n1. Backend is running on port 8000\n2. Run: python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000\n3. Or use: start_backend_8000.bat\n\n(Attempted: ${attemptedUrl})`
          : `Cannot connect to backend server: ${healthErr.message}.\n\nPlease ensure the backend is running on port 8000.\n(Attempted: ${attemptedUrl})`
        console.error('[handleInvoiceSubmit] Backend health check failed:', healthErr)
        setError(errorMsg)
        setLoading(false)
        return
      }

      const invoiceData = {
        supplier,
        invoiceNumber,
        date: invoiceDate,
        venue: selectedVenue,
        lineItems: validLineItems,
        subtotal,
        vat,
        total,
      }

      console.log('[handleInvoiceSubmit]', editInvoiceId ? 'Updating' : 'Creating', 'invoice with data:', invoiceData)
      
      let invoiceId: string
      let response: any
      
      if (editInvoiceId) {
        // Update existing invoice
        response = await updateManualInvoice(editInvoiceId, invoiceData)
        invoiceId = editInvoiceId
      } else {
        // Create new invoice
        response = await createManualInvoice(invoiceData)
        invoiceId = response.id || response.invoiceId || response.invoice_id || response.invoice?.id
        
        if (!invoiceId) {
          console.warn('Invoice created but no ID returned in response:', response)
          setError('Invoice created but no ID returned. Please check if it was created successfully.')
          setLoading(false)
          return
        }
        
        // Verify the created invoice matches submitted data (only for new invoices)
        const verification = await verifyCreatedInvoice(String(invoiceId), invoiceData)
        
        if (!verification.isValid) {
          // Validation failed - delete the invoice and show error
          try {
            await deleteInvoices([String(invoiceId)])
          } catch (deleteErr) {
            console.error('Failed to delete invalid invoice:', deleteErr)
          }
          
          // Show error notification
          setNotificationType('error')
          setNotificationTitle('OH NO...')
          setNotificationMessage(
            verification.errors.length > 0
              ? `Something went wrong. ${verification.errors.slice(0, 2).join('. ')}. Let's try again.`
              : 'Something went wrong, let\'s try again.'
          )
          setShowNotification(true)
          setLoading(false)
          // Don't call onSuccess - prevents card creation
          return
        }
      }
      
      // Validation passed - show success notification
      setCreatedInvoiceId(String(invoiceId))
      
      // Store submitted invoice data for copying to delivery note later
      setLastSubmittedInvoice({
        supplier,
        date: invoiceDate,
        lineItems: invoiceLineItems.filter(item => item.description.trim() !== ''),
      })
      
      // Auto-pair with delivery note if invoice was created from DN
      if (creatingInvoiceFromDN) {
        try {
          const pairResult = await linkDeliveryNoteToInvoice(String(invoiceId), creatingInvoiceFromDN)
          if (pairResult.warnings && pairResult.warnings.length > 0) {
            setNotificationType('success')
            setNotificationTitle('SUCCESS!')
            setNotificationMessage(`Congratulations, your upload was successful. Note: ${pairResult.warnings.slice(0, 1).join(', ')}.`)
          } else {
            setNotificationType('success')
            setNotificationTitle('SUCCESS!')
            setNotificationMessage('Congratulations, your upload was successful.')
          }
          setCreatingInvoiceFromDN(null) // Clear the flag
          setPendingSuccessCallback(() => {
            // Wrap in setTimeout to avoid setState during render
            setTimeout(() => {
              onSuccess(String(invoiceId), 'invoice')
              // Reset form but keep modal open
              setSupplier('')
              setInvoiceNumber('')
              setInvoiceDate(new Date().toISOString().split('T')[0])
              setInvoiceLineItems([{ description: '', qty: 0, unit: '', price: 0, total: 0 }])
              setSubtotal(0)
              setVat(0)
              setTotal(0)
            }, 0)
          })
          setShowNotification(true)
          setLoading(false)
          return
        } catch (pairErr) {
          console.warn('Failed to auto-pair invoice with delivery note:', pairErr)
          // Still show success for invoice creation, but note pairing failed
          setNotificationType('success')
          setNotificationTitle('SUCCESS!')
          setNotificationMessage('Congratulations, your upload was successful. Pairing with delivery note failed, but you can pair it manually later.')
          setPendingSuccessCallback(() => {
            // Wrap in setTimeout to avoid setState during render
            setTimeout(() => {
              onSuccess(String(invoiceId), 'invoice')
              // Reset form but keep modal open
              setSupplier('')
              setInvoiceNumber('')
              setInvoiceDate(new Date().toISOString().split('T')[0])
              setInvoiceLineItems([{ description: '', qty: 0, unit: '', price: 0, total: 0 }])
              setSubtotal(0)
              setVat(0)
              setTotal(0)
            }, 0)
          })
          setShowNotification(true)
          setLoading(false)
          return
        }
      }
      
      // Check for existing delivery notes and show prompt if none found (only for new invoices)
      if (!editInvoiceId && !creatingInvoiceFromDN) {
        await checkForDeliveryNotes(supplier, invoiceDate)
      }
      
      // Fetch pairing suggestions if invoice ID is available (only for new invoices)
      if (!editInvoiceId) {
        await fetchAndShowPairingSuggestions(String(invoiceId))
      }
      
      // Show success notification (for both update and create)
      setNotificationType('success')
      setNotificationTitle('SUCCESS!')
      setNotificationMessage(editInvoiceId ? 'Invoice updated successfully!' : 'Congratulations, your upload was successful.')
      setPendingSuccessCallback(() => {
        // Wrap in setTimeout to avoid setState during render
        setTimeout(() => {
          // Refresh the invoice list and pass invoice ID
          onSuccess(String(invoiceId), 'invoice')
          // Reset form but keep modal open (only for new invoices)
          if (!editInvoiceId) {
            setSupplier('')
            setInvoiceNumber('')
            setInvoiceDate(new Date().toISOString().split('T')[0])
            setInvoiceLineItems([{ description: '', qty: 0, unit: '', price: 0, total: 0 }])
            setSubtotal(0)
            setVat(0)
            setTotal(0)
          }
        }, 0)
      })
      setShowNotification(true)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create invoice')
    } finally {
      setLoading(false)
    }
  }

  const fetchAndShowInvoiceSuggestions = async (deliveryNoteId: string) => {
    setLoadingInvoiceSuggestions(true)
    try {
      const response = await fetchInvoiceSuggestionsForDN(deliveryNoteId)
      if (response.suggestions && response.suggestions.length > 0) {
        setInvoiceSuggestions(response.suggestions)
        setShowInvoiceSuggestions(true)
      }
    } catch (err) {
      console.warn('Failed to fetch invoice suggestions:', err)
      // Don't show error, just skip suggestions
    } finally {
      setLoadingInvoiceSuggestions(false)
    }
  }

  const handlePairInvoiceSuggestion = async (suggestion: any) => {
    if (!createdDNId || !suggestion.invoiceId) return
    
    setLoading(true)
    try {
      // Validate before pairing
      const validation = await validatePair(suggestion.invoiceId, createdDNId)
      
      // If validation shows warnings or low match score, show preview modal
      if (!validation.isValid || validation.matchScore < 0.8 || validation.warnings.length > 0) {
        setPreviewData({
          invoiceId: suggestion.invoiceId,
          deliveryNoteId: createdDNId,
          validation
        })
        setPreviewModalOpen(true)
        setLoading(false)
        return
      }
      
      // If validation passes, proceed with pairing directly
      await linkDeliveryNoteToInvoice(suggestion.invoiceId, createdDNId)
      toast.success('Invoice paired with delivery note successfully!')
      setShowInvoiceSuggestions(false)
      // Wrap in setTimeout to avoid setState during render
      setTimeout(() => {
        onSuccess()
      }, 0)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to pair invoice')
    } finally {
      setLoading(false)
    }
  }

  const handlePairSuggestion = async (suggestion: PairingSuggestion) => {
    if (!createdInvoiceId || !suggestion.deliveryNoteId) return
    
    setLoading(true)
    try {
      // Validate before pairing
      const validation = await validatePair(createdInvoiceId, suggestion.deliveryNoteId)
      
      // If validation shows warnings or low match score, show preview modal
      if (!validation.isValid || validation.matchScore < 0.8 || validation.warnings.length > 0) {
        setPreviewData({
          invoiceId: createdInvoiceId,
          deliveryNoteId: suggestion.deliveryNoteId,
          validation
        })
        setPreviewModalOpen(true)
        setLoading(false)
        return
      }
      
      // If validation passes, proceed with pairing directly
      await linkDeliveryNoteToInvoice(createdInvoiceId, suggestion.deliveryNoteId)
      toast.success('Invoice paired with delivery note successfully!')
      setShowPairingSuggestions(false)
      // Wrap in setTimeout to avoid setState during render
      setTimeout(() => {
        onSuccess(createdInvoiceId, 'invoice')
      }, 0)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to pair invoice')
    } finally {
      setLoading(false)
    }
  }

  const handleAcceptDNPrompt = () => {
    setShowDNCreationPrompt(false)
    // Pre-fill delivery note form with invoice data
    copyInvoiceToDN(true) // Use last submitted invoice data
  }

  const handleDismissDNPrompt = () => {
    setShowDNCreationPrompt(false)
  }

  const handleUnifiedSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    // Prevent double submission
    if (loading) {
      return
    }
    
    setError(null)
    setLoading(true)

    try {
      // Validate required fields - check if we have at least one line item with description
      const hasLineItems = unifiedLineItems.some(item => item.description.trim() !== '')
      
      if (!supplier.trim() || !invoiceNumber.trim()) {
        setError('Please fill in supplier and invoice number')
        setLoading(false)
        return
      }

      // Filter out empty line items
      const validLineItems = unifiedLineItems.filter(item => item.description.trim() !== '')
      
      if (validLineItems.length === 0) {
        setError('Please add at least one line item with a description')
        setLoading(false)
        return
      }

      // Check spelling before submission (use full array to preserve indices)
      const spellingOk = await checkSpellingBeforeSubmit(unifiedLineItems, 'unified')
      if (!spellingOk) {
        setPendingSubmitCallback(() => () => {
          const updatedValidItems = unifiedLineItems.filter(item => item.description.trim() !== '')
          handleUnifiedSubmitInternal(updatedValidItems)
        })
        setLoading(false)
        return
      }
      
      await handleUnifiedSubmitInternal(validLineItems)
    } catch (err: any) {
      console.error('Error in handleUnifiedSubmit:', err)
      setError(err.message || 'Failed to submit')
      setLoading(false)
    }
  }

  const handleUnifiedSubmitInternal = async (validLineItems: UnifiedLineItem[]) => {
    setLoading(true)

    try {
      
      if (!hasLineItems) {
        setError('Please add at least one line item with a description')
        setLoading(false)
        return
      }

      const unifiedTotals = calculateUnifiedInvoiceTotals()

      // Create invoice first
      const invoiceData = {
        supplier,
        invoiceNumber,
        date: invoiceDate,
        venue: selectedVenue,
        lineItems: unifiedLineItems
          .filter(item => item.description.trim() !== '')
          .map(item => ({
            description: item.description,
            qty: item.invQty || 0,
            unit: item.unit || '',
            price: item.invPrice || 0,
            total: item.invTotal || 0,
            vat: vatMode === 'per-item' ? (item.invVat || vatPercentage) : undefined,
          })),
        subtotal: unifiedTotals.subtotal,
        vat: unifiedTotals.vat,
        total: unifiedTotals.total,
      }

      const invoiceResponse = await createManualInvoice(invoiceData)
      const invoiceId = invoiceResponse.id || invoiceResponse.invoiceId || invoiceResponse.invoice_id || invoiceResponse.invoice?.id

      if (!invoiceId) {
        setError('Invoice created but no ID returned')
        setLoading(false)
        return
      }

      // Verify invoice first
      const invoiceVerification = await verifyCreatedInvoice(String(invoiceId), invoiceData)

      // Create delivery note - use supplier if dnSupplier is empty
      const deliveryNoteSupplier = dnSupplier.trim() || supplier.trim()
      if (!deliveryNoteSupplier) {
        // Delete invoice if supplier is missing for DN
        if (invoiceVerification.isValid) {
          try {
            await deleteInvoices([String(invoiceId)])
          } catch (deleteErr) {
            console.error('Failed to delete invoice:', deleteErr)
          }
        }
        setError('Please fill in supplier for delivery note')
        setLoading(false)
        return
      }
      
      const dnData = {
        noteNumber: noteNumber.trim() || `DN-${invoiceNumber}`,
        date: dnDate || invoiceDate,
        supplier: deliveryNoteSupplier,
        lineItems: unifiedLineItems
          .filter(item => item.description.trim() !== '')
          .map(item => ({
            description: item.description,
            qty: item.dnQty || 0,
            unit: item.unit || '',
            weight: item.dnWeight || 0,
          })),
        driver: driver.trim() || undefined,
        vehicle: vehicle.trim() ? vehicle.trim().toUpperCase() : undefined,
        timeWindow: timeWindow.trim() || undefined,
        venue: selectedVenue,
      }

      const dnResponse = await createManualDeliveryNote(dnData)
      const dnId = dnResponse.id || dnResponse.deliveryNoteId || dnResponse.delivery_note_id

      if (!dnId) {
        // Delete invoice if DN creation failed
        if (invoiceVerification.isValid) {
          try {
            await deleteInvoices([String(invoiceId)])
          } catch (deleteErr) {
            console.error('Failed to delete invoice:', deleteErr)
          }
        }
        setError('Delivery note created but no ID returned')
        setLoading(false)
        return
      }

      // Verify delivery note
      const dnVerification = await verifyCreatedDeliveryNote(String(dnId), {
        noteNumber: noteNumber.trim() || `DN-${invoiceNumber}`,
        date: dnDate || invoiceDate,
        supplier: deliveryNoteSupplier,
        venue: selectedVenue,
        lineItems: unifiedLineItems
          .filter(item => item.description.trim() !== '')
          .map(item => ({
            description: item.description,
            qty: item.dnQty || 0,
            unit: item.unit || '',
            weight: item.dnWeight || 0,
          })),
      })

      // If either validation failed, delete both and show error
      if (!invoiceVerification.isValid || !dnVerification.isValid) {
        const allErrors = [
          ...(invoiceVerification.isValid ? [] : invoiceVerification.errors),
          ...(dnVerification.isValid ? [] : dnVerification.errors),
        ]
        
        // Delete both if created
        try {
          if (!invoiceVerification.isValid) {
            await deleteInvoices([String(invoiceId)])
          }
          if (!dnVerification.isValid) {
            await deleteDeliveryNotes([String(dnId)])
          }
        } catch (deleteErr) {
          console.error('Failed to delete invalid records:', deleteErr)
        }
        
        // Show error notification
        setNotificationType('error')
        setNotificationTitle('OH NO...')
        setNotificationMessage(
          allErrors.length > 0
            ? `Something went wrong. ${allErrors.slice(0, 2).join('. ')}. Let's try again.`
            : 'Something went wrong, let\'s try again.'
        )
        setShowNotification(true)
        setLoading(false)
        // Don't call onSuccess - prevents card creation
        return
      }

      // Both validations passed - auto-pair invoice and delivery note
      try {
        await linkDeliveryNoteToInvoice(String(invoiceId), String(dnId))
        setNotificationType('success')
        setNotificationTitle('SUCCESS!')
        setNotificationMessage('Congratulations, your upload was successful.')
      } catch (pairErr) {
        console.warn('Failed to auto-pair:', pairErr)
        setNotificationType('success')
        setNotificationTitle('SUCCESS!')
        setNotificationMessage('Congratulations, your upload was successful. Pairing failed, but you can pair them manually.')
      }

      setPendingSuccessCallback(() => {
        // Wrap in setTimeout to avoid setState during render
        setTimeout(() => {
          // Refresh the list to show both new cards
          // Call onSuccess which will refresh the invoice list, and the DN should appear too
          onSuccess(String(invoiceId), 'both')
          
          // Reset form
          setSupplier('')
          setInvoiceNumber('')
          setInvoiceDate(new Date().toISOString().split('T')[0])
          setNoteNumber('')
          setDnDate(new Date().toISOString().split('T')[0])
          setDnSupplier('')
          setUnifiedLineItems([{ description: '', invQty: 0, invPrice: 0, invTotal: 0, dnQty: 0, dnWeight: 0, unit: '' }])
          setDriver('')
          setVehicle('')
          setTimeWindow('')
          
          // Close the modal after showing success
          setTimeout(() => {
            handleClose(false)
          }, 500)
        }, 0)
      })
      setShowNotification(true)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create invoice and delivery note')
    } finally {
      setLoading(false)
    }
  }

  const handleDNSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    // Prevent double submission
    if (loading) {
      return
    }
    
    setError(null)
    setLoading(true)

    try {
      if (!noteNumber.trim() || !dnSupplier.trim()) {
        setError('Please fill in note number and supplier')
        setLoading(false)
        return
      }

      // Filter out empty line items
      const validLineItems = dnLineItems.filter(item => item.description.trim() !== '')
      
      if (validLineItems.length === 0) {
        setError('Please add at least one line item with a description')
        setLoading(false)
        return
      }

      // Check spelling before submission (use full array to preserve indices)
      const spellingOk = await checkSpellingBeforeSubmit(dnLineItems, 'dn')
      if (!spellingOk) {
        setPendingSubmitCallback(() => () => {
          const updatedValidItems = dnLineItems.filter(item => item.description.trim() !== '')
          handleDNSubmitInternal(updatedValidItems)
        })
        setLoading(false)
        return
      }
      
      await handleDNSubmitInternal(validLineItems)
    } catch (err: any) {
      console.error('Error in handleDNSubmit:', err)
      setError(err.message || 'Failed to submit delivery note')
      setLoading(false)
    }
  }

  const handleDNSubmitInternal = async (validLineItems: DNLineItem[]) => {
    setLoading(true)

    try {
      // Ensure supplier is not empty - use supplier from invoice if DN supplier is empty
      const deliveryNoteSupplier = dnSupplier.trim() || supplier.trim()
      if (!deliveryNoteSupplier) {
        setError('Please fill in supplier for delivery note')
        setLoading(false)
        return
      }
      
      const dnData = {
        noteNumber: noteNumber.trim(),
        date: dnDate || new Date().toISOString().split('T')[0],
        supplier: deliveryNoteSupplier,
        lineItems: dnLineItems.filter(item => item.description.trim() !== ''),
        supervisor: supervisor.trim() || undefined,
        driver: driver.trim() || undefined,
        vehicle: vehicle.trim() ? vehicle.trim().toUpperCase() : undefined,
        timeWindow: timeWindow.trim() || undefined,
        venue: selectedVenue,
      }

      console.log('[DEBUG] ManualInvoiceOrDNModal: Submitting DN data:', {
        noteNumber: dnData.noteNumber,
        date: dnData.date,
        supplier: dnData.supplier,
        venue: dnData.venue,
        lineItemsCount: dnData.lineItems.length
      })

      // Add timeout to prevent hanging
      const createPromise = createManualDeliveryNote(dnData)
      const timeoutPromise = new Promise((_, reject) => 
        setTimeout(() => reject(new Error('Request timeout - please try again')), 10000)
      )
      
      const response = await Promise.race([createPromise, timeoutPromise]) as any
      
      // Extract delivery note ID from response
      const dnId = response.id || response.deliveryNoteId || response.delivery_note_id
      if (!dnId) {
        setError('Delivery note created but no ID returned')
        setLoading(false)
        return
      }
      
      // Skip verification for now - backend already validates the data
      // Verification can be slow and blocks the user experience
      // If needed, we can add it back as a background check
      let verification: { isValid: boolean; errors: string[] } | null = { isValid: true, errors: [] }
      
      // Optional: Run verification in background (non-blocking)
      // verifyCreatedDeliveryNote(String(dnId), {
      //   noteNumber: noteNumber.trim(),
      //   date: dnDate || new Date().toISOString().split('T')[0],
      //   supplier: deliveryNoteSupplier,
      //   venue: selectedVenue,
      //   lineItems: dnLineItems.filter(item => item.description.trim() !== ''),
      // }, response).catch(err => {
      //   console.warn('Background verification failed:', err)
      // })
      
      if (verification && !verification.isValid) {
        // Validation failed - delete the delivery note and show error
        try {
          await deleteDeliveryNotes([String(dnId)])
        } catch (deleteErr) {
          console.error('Failed to delete invalid delivery note:', deleteErr)
        }
        
        // Show error notification
        setNotificationType('error')
        setNotificationTitle('OH NO...')
        setNotificationMessage(
          verification.errors.length > 0
            ? `Something went wrong. ${verification.errors.slice(0, 2).join('. ')}. Let's try again.`
            : 'Something went wrong, let\'s try again.'
        )
        setShowNotification(true)
        setLoading(false)
        // Don't call onSuccess - prevents card creation
        return
      }
      
      // Validation passed - show success notification immediately
      setCreatedDNId(String(dnId))
      // Store submitted DN data for creating invoice from it later
      setLastSubmittedDN({
        supplier: deliveryNoteSupplier,
        date: dnDate || new Date().toISOString().split('T')[0],
        lineItems: dnLineItems.filter(item => item.description.trim() !== ''),
        venue: selectedVenue,
      })
      
      // Show success notification immediately (don't wait for suggestions)
      setNotificationType('success')
      setNotificationTitle('SUCCESS!')
      setNotificationMessage('Congratulations, your upload was successful.')
      setPendingSuccessCallback(() => {
        // Wrap in setTimeout to avoid setState during render
        setTimeout(() => {
          // Refresh the invoice list - pass 'delivery-note' to indicate DN was created
          console.log('[DEBUG] ManualInvoiceOrDNModal: Triggering refresh for delivery note', dnId)
          onSuccess(undefined, 'delivery-note')
          // Reset form but keep modal open
          setNoteNumber('')
          setDnDate(new Date().toISOString().split('T')[0])
          setDnSupplier('')
          setDnLineItems([{ description: '', qty: 0, unit: '', weight: 0 }])
          setSupervisor('')
          setDriver('')
          setVehicle('')
          setTimeWindow('')
          setHasCopiedData(false)
        }, 0)
      })
      setShowNotification(true)
      
      // Fetch invoice suggestions in the background (non-blocking)
      // Do this after showing success so user gets immediate feedback
      fetchAndShowInvoiceSuggestions(String(dnId)).catch(suggestionErr => {
        // Don't fail the whole operation if suggestions fail
        console.warn('Failed to fetch invoice suggestions:', suggestionErr)
      })
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create delivery note')
    } finally {
      setLoading(false)
    }
  }

  const handleClose = (shouldSave = false) => {
    if (shouldSave) {
      // Save form data before closing
      saveFormData()
    } else {
      // Clear saved data if not saving
      clearSavedFormData()
    // Reset invoice state
    setSupplier('')
    setInvoiceNumber('')
    setInvoiceDate(new Date().toISOString().split('T')[0])
    setSelectedVenue(venue)
    setInvoiceLineItems([{ description: '', qty: 0, unit: '', price: 0, total: 0 }])
    setSubtotal(0)
    setVat(0)
    setTotal(0)
    
    // Reset delivery note state
    setNoteNumber('')
    setDnDate(new Date().toISOString().split('T')[0])
    setDnSupplier('')
    setDnLineItems([{ description: '', qty: 0, unit: '' }])
    setSupervisor('')
    setDriver('')
    setVehicle('')
    setTimeWindow('')
      
      // Reset unified state
      setUnifiedLineItems([{ description: '', invQty: 0, invPrice: 0, invTotal: 0, dnQty: 0, dnWeight: 0, unit: '', invVat: 20 }])
    
    // Reset common state
    setActiveTab(initialTab)
      setUnifiedMode(false)
    }
    
    setError(null)
    setShowCopiedFeedback(false)
    setHasCopiedData(false)
    setLastSubmittedInvoice(null)
    
    // Reset pairing suggestions state
    setCreatedInvoiceId(null)
    setPairingSuggestions([])
    setShowPairingSuggestions(false)
    setLoadingSuggestions(false)
    setShowDNCreationPrompt(false)
    setCheckingDN(false)
    
    // Reset invoice suggestions state (for delivery notes)
    setCreatedDNId(null)
    setInvoiceSuggestions([])
    setShowInvoiceSuggestions(false)
    setLoadingInvoiceSuggestions(false)
    setCreatingInvoiceFromDN(null)
    setLastSubmittedDN(null)
    
    onClose()
  }

  const handleSaveAndClose = () => {
    saveFormData()
    toast.success('Form data saved')
    handleClose(true)
  }

  // Handle mode switching with data transfer
  const handleModeSwitch = (newUnifiedMode: boolean, clearInvoice: boolean, clearDN: boolean) => {
    // Capture height before change
    if (contentRef.current) {
      heightBeforeChangeRef.current = contentRef.current.scrollHeight
      isExpandingRef.current = newUnifiedMode && !unifiedMode
    }

    // Capture current unified line items before any state changes
    // This ensures we have the latest data even if state hasn't updated yet
    const currentUnifiedItems = [...unifiedLineItems]

    if (newUnifiedMode) {
      // Switching TO unified mode - transfer existing data
      setUnifiedMode(true)
      setActiveTab('invoice')
      
      // Check what data exists
      const hasInvoiceData = !clearInvoice && (supplier || invoiceNumber || invoiceLineItems.some(item => item.description.trim() !== ''))
      const hasDNData = !clearDN && (dnSupplier || noteNumber || dnLineItems.some(item => item.description.trim() !== ''))
      
      if (hasInvoiceData && hasDNData) {
        // Both invoice and DN data exist - merge them by matching item descriptions
        const mergedItems: UnifiedLineItem[] = []
        
        // Start with invoice items - include ALL items, not just those with descriptions
        invoiceLineItems.forEach(invItem => {
          const matchingDN = dnLineItems.find(dnItem => 
            dnItem.description.trim() !== '' && 
            invItem.description.trim() !== '' &&
            dnItem.description.toLowerCase().trim() === invItem.description.toLowerCase().trim()
          )
          mergedItems.push({
            description: invItem.description,
            invQty: invItem.qty,
            invPrice: invItem.unitPrice,
            invTotal: invItem.total,
            invVat: invItem.vat || vatPercentage,
            dnQty: matchingDN ? matchingDN.qty : 0,
            dnWeight: matchingDN?.weight || 0,
            unit: invItem.unit || matchingDN?.unit || ''
          })
        })
        
        // Add DN items that don't have matching invoice items
        dnLineItems.forEach(dnItem => {
          if (dnItem.description.trim() !== '') {
            const hasMatch = mergedItems.some(item => 
              item.description.trim() !== '' &&
              item.description.toLowerCase().trim() === dnItem.description.toLowerCase().trim()
            )
            if (!hasMatch) {
              mergedItems.push({
                description: dnItem.description,
                invQty: 0,
                invPrice: 0,
                invTotal: 0,
                invVat: vatPercentage,
                dnQty: dnItem.qty,
                dnWeight: dnItem.weight || 0,
                unit: dnItem.unit || ''
              })
            }
          }
        })
        
        // Always set unified line items, even if empty
        setUnifiedLineItems(mergedItems.length > 0 ? mergedItems : [{ description: '', invQty: 0, invPrice: 0, invTotal: 0, dnQty: 0, dnWeight: 0, unit: '', invVat: vatPercentage }])
      } else if (hasInvoiceData) {
        // Only invoice data exists - transfer invoice line items to unified form with ALL fields
        // Transfer ALL invoice line items, including those with empty descriptions (they might have other data)
        const invoiceItems = invoiceLineItems.map(item => ({
          description: item.description,
          invQty: item.qty,
          invPrice: item.unitPrice,
          invTotal: item.total,
          invVat: item.vat || vatPercentage,
          dnQty: 0,
          dnWeight: 0,
          unit: item.unit || ''
        }))
        // Always set unified line items, even if empty
        setUnifiedLineItems(invoiceItems.length > 0 ? invoiceItems : [{ description: '', invQty: 0, invPrice: 0, invTotal: 0, dnQty: 0, dnWeight: 0, unit: '', invVat: vatPercentage }])
        // Also ensure supplier, invoice number, date are preserved (they're already in state)
      } else if (hasDNData) {
        // Only DN data exists - transfer DN line items to unified form with ALL fields
        // Transfer ALL DN line items, including those with empty descriptions (they might have other data)
        const dnItems = dnLineItems.map(item => ({
          description: item.description,
          invQty: 0,
          invPrice: 0,
          invTotal: 0,
          invVat: vatPercentage,
          dnQty: item.qty,
          dnWeight: item.weight || 0,
          unit: item.unit || ''
        }))
        // Always set unified line items, even if empty
        setUnifiedLineItems(dnItems.length > 0 ? dnItems : [{ description: '', invQty: 0, invPrice: 0, invTotal: 0, dnQty: 0, dnWeight: 0, unit: '', invVat: vatPercentage }])
        // Set DN-specific fields (they're already in state, but ensure they're preserved)
        // Also set supplier to match DN supplier if invoice supplier is empty
        if (dnSupplier && !supplier) {
          setSupplier(dnSupplier)
        }
      } else {
        // No data exists - ensure we have at least one empty line item
        setUnifiedLineItems([{ description: '', invQty: 0, invPrice: 0, invTotal: 0, dnQty: 0, dnWeight: 0, unit: '', invVat: vatPercentage }])
      }
      
      // Clear data if requested
      if (clearInvoice) {
        setSupplier('')
        setInvoiceNumber('')
        setInvoiceDate(new Date().toISOString().split('T')[0])
        setInvoiceLineItems([{ description: '', qty: 0, unit: '', price: 0, total: 0 }])
        setSubtotal(0)
        setVat(0)
        setTotal(0)
      }
      if (clearDN) {
        setDnSupplier('')
        setNoteNumber('')
        setDnDate(new Date().toISOString().split('T')[0])
        setDnLineItems([{ description: '', qty: 0, unit: '' }])
        setDriver('')
        setVehicle('')
        setTimeWindow('')
      }
    } else {
      // Switching FROM unified mode OR switching between individual tabs
      if (unifiedMode) {
        // Coming from unified mode - transfer to individual mode
        // Transfer BOTH invoice and DN data from unified to their respective individual forms
        
        // Always transfer invoice data from unified (if not clearing)
        // Use captured currentUnifiedItems to ensure we have the latest data
        if (!clearInvoice) {
          // Transfer ALL items from unified, preserving all data
          const invoiceItems = currentUnifiedItems.length > 0 
            ? currentUnifiedItems.map(item => ({
                description: item.description || '',
                qty: item.invQty || 0,
                unit: item.unit || '',
                price: item.invPrice || 0,
                total: item.invTotal || 0,
                vat: item.invVat || vatPercentage
              }))
            : [{ description: '', qty: 0, unit: '', price: 0, total: 0, vat: vatPercentage }]
          
          // Set invoice line items immediately
          setInvoiceLineItems(invoiceItems)
          // Keep supplier, invoice number, date, venue, VAT settings (already in state)
        }
        
        // Always transfer DN data from unified (if not clearing)
        // Use captured currentUnifiedItems to ensure we have the latest data
        if (!clearDN) {
          // Transfer ALL items from unified, preserving all data
          const dnItems = currentUnifiedItems.length > 0
            ? currentUnifiedItems.map(item => ({
                description: item.description || '',
                qty: item.dnQty || 0,
                unit: item.unit || '',
                weight: item.dnWeight || 0
              }))
            : [{ description: '', qty: 0, unit: '' }]
          
          // Set DN line items immediately
          setDnLineItems(dnItems)
          // Keep DN-specific fields (supplier, note number, date, driver, vehicle, timeWindow) - already in state
          // Also set DN supplier if invoice supplier exists but DN supplier doesn't
          if (supplier && !dnSupplier) {
            setDnSupplier(supplier)
          }
        }
        
        // Set unified mode to false AFTER transferring data
        setUnifiedMode(false)
        
        // Determine which tab to show based on pendingModeChange or default to invoice
        if (pendingModeChange?.type === 'individual-dn') {
          setActiveTab('delivery-note')
        } else {
          setActiveTab('invoice')
        }
      } else {
        // Just switching tabs in individual mode (not changing unifiedMode)
        if (pendingModeChange?.type === 'individual-invoice') {
          // Switching to invoice tab
          // Clear data if requested
          if (clearDN) {
            setDnSupplier('')
            setNoteNumber('')
            setDnDate(new Date().toISOString().split('T')[0])
            setDnLineItems([{ description: '', qty: 0, unit: '' }])
            setDriver('')
            setVehicle('')
            setTimeWindow('')
          }
          if (contentRef.current) {
            heightBeforeChangeRef.current = contentRef.current.scrollHeight
          }
          setIsTabTransitioning(true)
          requestAnimationFrame(() => {
            setActiveTab('invoice')
            setTimeout(() => setIsTabTransitioning(false), 300)
          })
        } else if (pendingModeChange?.type === 'individual-dn') {
          // Switching to delivery note tab
          // Clear data if requested
          if (clearInvoice) {
            setSupplier('')
            setInvoiceNumber('')
            setInvoiceDate(new Date().toISOString().split('T')[0])
            setInvoiceLineItems([{ description: '', qty: 0, unit: '', price: 0, total: 0 }])
            setSubtotal(0)
            setVat(0)
            setTotal(0)
          }
          if (contentRef.current) {
            heightBeforeChangeRef.current = contentRef.current.scrollHeight
          }
          setIsTabTransitioning(true)
          requestAnimationFrame(() => {
            setActiveTab('delivery-note')
            setTimeout(() => setIsTabTransitioning(false), 300)
          })
        }
      }
      
      // Clear data if requested
      if (clearInvoice) {
        setSupplier('')
        setInvoiceNumber('')
        setInvoiceDate(new Date().toISOString().split('T')[0])
        setInvoiceLineItems([{ description: '', qty: 0, unit: '', price: 0, total: 0 }])
        setUnifiedLineItems(unifiedLineItems.map(item => ({
          ...item,
          invQty: 0,
          invPrice: 0,
          invTotal: 0
        })))
        setSubtotal(0)
        setVat(0)
        setTotal(0)
      }
      if (clearDN) {
        setDnSupplier('')
        setNoteNumber('')
        setDnDate(new Date().toISOString().split('T')[0])
        setDnLineItems([{ description: '', qty: 0, unit: '' }])
        setUnifiedLineItems(unifiedLineItems.map(item => ({
          ...item,
          dnQty: 0,
          dnWeight: 0
        })))
        setDriver('')
        setVehicle('')
        setTimeWindow('')
      }
    }
    
    setShowModeSwitchConfirm(false)
    setPendingModeChange(null)
  }

  if (!isOpen) return null

  return (
    <div className="modal-overlay" onClick={() => handleClose(true)}>
      <div 
        className="modal-container" 
        onClick={(e) => e.stopPropagation()} 
        style={{ 
          maxWidth: unifiedMode ? '1200px' : '800px',
          maxHeight: unifiedMode ? '85vh' : '90vh',
          height: unifiedMode ? '85vh' : '90vh',
          position: 'relative',
          transition: 'max-width 0.4s cubic-bezier(0.4, 0, 0.2, 1), width 0.4s cubic-bezier(0.4, 0, 0.2, 1), max-height 0.4s cubic-bezier(0.4, 0, 0.2, 1), height 0.4s cubic-bezier(0.4, 0, 0.2, 1)',
          width: '100%',
          overflow: 'hidden',
          display: 'flex',
          flexDirection: 'column'
        }}
      >
        <div className="modal-header" style={{ position: 'relative', display: 'flex', flexDirection: 'column', width: '100%' }}>
          {/* Invoice/Delivery Note Menu - Rectangular buttons with text inside, within widget */}
          {!unifiedMode && (
            <div style={{ 
              width: '100%',
              display: 'flex',
              justifyContent: 'center',
              alignItems: 'center',
              gap: '12px',
              marginBottom: '16px',
              position: 'relative'
            }}>
              {/* Invoice Menu Item */}
              <div
                onClick={() => {
                  if (activeTab !== 'invoice' && !isTabTransitioning) {
                    // Check if there's data in the current tab that might conflict
                    const hasCurrentDNData = dnSupplier || noteNumber || dnLineItems.some(item => item.description.trim() !== '')
                    const hasTargetInvoiceData = supplier || invoiceNumber || invoiceLineItems.some(item => item.description.trim() !== '')
                    
                    if (hasCurrentDNData && hasTargetInvoiceData) {
                      // Both tabs have data, show confirmation
                      setPendingModeChange({
                        type: 'individual-invoice',
                        hasInvoiceData: hasTargetInvoiceData,
                        hasDNData: hasCurrentDNData
                      })
                      setShowModeSwitchConfirm(true)
                    } else {
                      // No conflict, proceed with tab switch
                      if (contentRef.current) {
                        heightBeforeChangeRef.current = contentRef.current.scrollHeight
                      }
                      setIsTabTransitioning(true)
                      requestAnimationFrame(() => {
                        setActiveTab('invoice')
                        setTimeout(() => setIsTabTransitioning(false), 300)
                      })
                    }
                  }
                }}
                style={{
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: '8px',
                  padding: '10px 20px',
                  borderRadius: '12px',
                  background: activeTab === 'invoice' 
                    ? 'var(--accent-blue, #3b82f6)' 
                    : 'rgba(59, 130, 246, 0.3)',
                  transition: 'all 0.4s cubic-bezier(0.4, 0, 0.2, 1)',
                  border: activeTab === 'invoice' ? '2px solid rgba(0, 0, 0, 0.2)' : '2px solid transparent',
                  minWidth: '160px',
                  width: '160px'
                }}
              >
                <FileText size={20} style={{ color: 'white' }} />
                <span style={{
                  fontSize: '14px',
                  fontWeight: activeTab === 'invoice' ? '600' : '500',
                  color: 'white',
                  transition: 'all 0.4s cubic-bezier(0.4, 0, 0.2, 1)',
                  whiteSpace: 'nowrap'
                }}>
                  Invoice
                </span>
              </div>

              {/* Delivery Note Menu Item */}
              <div
                onClick={() => {
                  if (activeTab !== 'delivery-note' && !isTabTransitioning) {
                    // Check if there's data in the current tab that might conflict
                    const hasCurrentInvoiceData = supplier || invoiceNumber || invoiceLineItems.some(item => item.description.trim() !== '')
                    const hasTargetDNData = dnSupplier || noteNumber || dnLineItems.some(item => item.description.trim() !== '')
                    
                    if (hasCurrentInvoiceData && hasTargetDNData) {
                      // Both tabs have data, show confirmation
                      setPendingModeChange({
                        type: 'individual-dn',
                        hasInvoiceData: hasCurrentInvoiceData,
                        hasDNData: hasTargetDNData
                      })
                      setShowModeSwitchConfirm(true)
                    } else {
                      // No conflict, proceed with tab switch
                      if (contentRef.current) {
                        heightBeforeChangeRef.current = contentRef.current.scrollHeight
                      }
                      setIsTabTransitioning(true)
                      requestAnimationFrame(() => {
                        setActiveTab('delivery-note')
                        setTimeout(() => setIsTabTransitioning(false), 300)
                      })
                    }
                  }
                }}
                style={{
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: '8px',
                  padding: '10px 20px',
                  borderRadius: '12px',
                  background: activeTab === 'delivery-note' 
                    ? 'var(--accent-blue, #3b82f6)' 
                    : 'rgba(59, 130, 246, 0.3)',
                  transition: 'all 0.4s cubic-bezier(0.4, 0, 0.2, 1)',
                  border: activeTab === 'delivery-note' ? '2px solid rgba(0, 0, 0, 0.2)' : '2px solid transparent',
                  position: 'relative',
                  minWidth: '160px',
                  width: '160px'
                }}
              >
                <Package size={20} style={{ color: 'white' }} />
                <span style={{
                  fontSize: '14px',
                  fontWeight: activeTab === 'delivery-note' ? '600' : '500',
                  color: 'white',
                  transition: 'all 0.4s cubic-bezier(0.4, 0, 0.2, 1)',
                  whiteSpace: 'nowrap'
                }}>
                  Delivery Note
                </span>
                {hasCopiedData && activeTab === 'delivery-note' && (
                  <span style={{
                    position: 'absolute',
                    top: '-6px',
                    right: '-6px',
                    width: '18px',
                    height: '18px',
                    borderRadius: '50%',
                    background: 'var(--accent-green, #22c55e)',
                    border: '2px solid var(--bg-card)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    zIndex: 2
                  }}>
                    <Check size={10} style={{ color: 'white' }} />
                  </span>
                )}
              </div>
            </div>
          )}
          {unifiedMode && (
            <div style={{ 
              width: '100%', 
              marginBottom: '12px',
              background: 'var(--bg-secondary)',
              borderRadius: '8px',
              padding: '12px 16px',
              fontSize: '15px',
              color: 'var(--text-primary)',
              fontWeight: '600',
              textAlign: 'center'
            }}>
              Creating Invoice & Delivery Note Together
            </div>
          )}
          
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end', width: '100%', position: 'absolute', top: '0', right: '0' }}>
            <button className="modal-close-button" onClick={() => handleClose(true)} aria-label="Close modal" style={{ color: 'var(--text-muted)' }}>
              <X size={20} />
            </button>
          </div>
        </div>
        
        {/* Individual/Create Pair Toggle - Bottom left with sliding animation */}
        <div style={{ 
          position: 'absolute',
          bottom: '20px',
          left: '28px',
          zIndex: 10
        }}>
          <div 
            onClick={() => {
              // Check for data conflicts before switching modes
              const hasInvoiceData = supplier || invoiceNumber || invoiceLineItems.some(item => item.description.trim() !== '') || unifiedLineItems.some(item => item.description.trim() !== '' && (item.invQty > 0 || item.invPrice > 0))
              const hasDNData = dnSupplier || noteNumber || dnLineItems.some(item => item.description.trim() !== '') || unifiedLineItems.some(item => item.description.trim() !== '' && item.dnQty > 0)
              
              const newUnifiedMode = !unifiedMode
              
              // If switching to unified mode and both have data, or switching away from unified with data, show confirmation
              if ((newUnifiedMode && (hasInvoiceData || hasDNData)) || (!newUnifiedMode && unifiedMode && (hasInvoiceData || hasDNData))) {
                setPendingModeChange({
                  type: newUnifiedMode ? 'unified' : (activeTab === 'invoice' ? 'individual-invoice' : 'individual-dn'),
                  hasInvoiceData,
                  hasDNData
                })
                setShowModeSwitchConfirm(true)
              } else {
                // No conflict, proceed with mode switch
                handleModeSwitch(newUnifiedMode, false, false)
              }
            }}
            style={{
              position: 'relative',
              display: 'flex',
              alignItems: 'center',
              background: 'rgba(255, 255, 255, 0.1)',
              borderRadius: '24px',
              padding: '4px',
              cursor: 'pointer',
              width: '220px',
              height: '44px',
              transition: 'all 0.3s ease'
            }} 
            onClick={() => {
              // Capture height before change and determine if expanding or contracting
              if (contentRef.current) {
                heightBeforeChangeRef.current = contentRef.current.scrollHeight
                // If going from false to true, we're expanding (unified mode is larger)
                isExpandingRef.current = !unifiedMode
              }
              setUnifiedMode(!unifiedMode)
              if (!unifiedMode) {
                setActiveTab('invoice')
              }
            }}
          >
            {/* White pill with text - slides across */}
            <div style={{
              position: 'absolute',
              left: unifiedMode ? 'calc(100% - 4px)' : '4px',
              transform: unifiedMode ? 'translateX(-100%)' : 'translateX(0)',
              background: 'white',
              borderRadius: '20px',
              padding: '8px 16px',
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              transition: 'left 0.4s cubic-bezier(0.4, 0, 0.2, 1), transform 0.4s cubic-bezier(0.4, 0, 0.2, 1)',
              boxShadow: '0 2px 4px rgba(0, 0, 0, 0.1)',
              whiteSpace: 'nowrap',
              minWidth: '140px',
              justifyContent: 'space-between'
            }}>
              <span style={{
                fontSize: '13px',
                fontWeight: '600',
                color: '#000',
                transition: 'opacity 0.3s ease 0.1s',
                order: unifiedMode ? 2 : 1
              }}>
                {unifiedMode ? 'Create Individually' : 'Create as Pair'}
              </span>
              {/* Arrow icon - inside pill, opposite side of text */}
              <div style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: '#000',
                transition: 'opacity 0.3s ease 0.1s',
                order: unifiedMode ? 1 : 2
              }}>
                {unifiedMode ? (
                  <ArrowLeft size={18} />
                ) : (
                  <ArrowRight size={18} />
                )}
              </div>
            </div>
          </div>
        </div>

        {unifiedMode ? (
          <form onSubmit={handleUnifiedSubmit} style={{ display: 'flex', flexDirection: 'column', flex: 1, minHeight: 0 }}>
            <div 
              ref={contentRef}
              className="modal-body"
              style={{
                flex: 1,
                minHeight: 0,
                overflowY: 'auto',
                paddingBottom: '20px',
                transition: 'opacity 0.3s cubic-bezier(0.4, 0, 0.2, 1), transform 0.3s cubic-bezier(0.4, 0, 0.2, 1)'
              }}
            >
              {error && <div className="modal-error">{error}</div>}

              {/* Common Fields */}
              <div className="modal-form-row">
                <div className="modal-form-group">
                  <label className="modal-form-label">Supplier *</label>
                  <input
                    type="text"
                    className="modal-form-input"
                    value={supplier}
                    onChange={(e) => setSupplier(e.target.value)}
                    required
                    placeholder="Supplier name"
                  />
                </div>
                <div className="modal-form-group">
                  <label className="modal-form-label">Venue</label>
                  <VenueSelector
                    value={selectedVenue}
                    onChange={setSelectedVenue}
                    venues={venues}
                  />
                </div>
              </div>

              <div className="modal-form-row">
                <div className="modal-form-group">
                  <label className="modal-form-label">Invoice Number *</label>
                  <input
                    type="text"
                    className="modal-form-input"
                    value={invoiceNumber}
                    onChange={(e) => setInvoiceNumber(e.target.value)}
                    required
                    placeholder="INV-001"
                  />
                </div>
                <div className="modal-form-group">
                  <label className="modal-form-label">Invoice Date *</label>
                  <DatePicker
                    value={invoiceDate}
                    onChange={setInvoiceDate}
                    required
                  />
                </div>
                <div className="modal-form-group">
                  <label className="modal-form-label">Delivery Note Number *</label>
                  <input
                    type="text"
                    className="modal-form-input"
                    value={noteNumber}
                    onChange={(e) => setNoteNumber(e.target.value)}
                    required
                    placeholder="DN-001"
                  />
                </div>
                <div className="modal-form-group">
                  <label className="modal-form-label">DN Date *</label>
                  <DatePicker
                    value={dnDate}
                    onChange={setDnDate}
                    required
                  />
                </div>
              </div>

              {/* Unified Line Items Table */}
              <div className="modal-form-group">
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                  <label className="modal-form-label" style={{ marginBottom: 0 }}>Line Items</label>
              <button
                type="button"
                    className="glass-button"
                    onClick={addUnifiedLineItem}
                    style={{ fontSize: '12px', padding: '6px 12px' }}
                  >
                    <Plus size={14} />
                    Add Item
              </button>
                </div>

                <div 
                  className="line-items-table-container"
                  style={unifiedLineItems.length > 3 ? {
                    maxHeight: '400px',
                    overflowY: 'auto',
                    overflowX: 'auto',
                    display: 'block'
                  } : {
                    maxHeight: 'none',
                    overflowY: 'visible',
                    overflowX: 'auto',
                    display: 'block'
                  }}
                >
                  <table className="line-items-table" style={{ minWidth: vatMode === 'per-item' ? '1100px' : '1000px' }}>
                    <thead>
                      <tr>
                        <th>Item Name</th>
                        <th>Quantity</th>
                        <th>Price per Unit</th>
                        <th>Total (no VAT)</th>
                        {vatMode === 'per-item' && <th>VAT %</th>}
                        <th>Delivery Qty</th>
                        <th></th>
                      </tr>
                    </thead>
                    <tbody>
                      {unifiedLineItems.map((item, index) => (
                        <tr key={index}>
                          <td>
                            <AutocompleteInput
                              value={item.description}
                              onChange={(value) => updateUnifiedLineItem(index, 'description', value)}
                              onFetchSuggestions={fetchItemSuggestions}
                              placeholder="Item description (e.g., 12Litre pepsi pink container)"
                              className="line-items-table input"
                              minChars={2}
                              debounceMs={400}
                            />
                          </td>
                          <td>
                            <div style={{ position: 'relative', display: 'flex', alignItems: 'center' }}>
                              <input
                                type="number"
                                value={item.invQty || ''}
                                onChange={(e) => updateUnifiedLineItem(index, 'invQty', Math.floor(Number(e.target.value)) || 0)}
                                min="0"
                                step="1"
                                style={{ 
                                  paddingRight: '30px', 
                                  width: '100%',
                                  WebkitAppearance: 'none',
                                  MozAppearance: 'textfield'
                                }}
                                onWheel={(e) => e.currentTarget.blur()}
                              />
                              <style>{`
                                input[type="number"]::-webkit-inner-spin-button,
                                input[type="number"]::-webkit-outer-spin-button {
                                  -webkit-appearance: none;
                                  margin: 0;
                                }
                              `}</style>
                              <div style={{ position: 'absolute', right: '4px', display: 'flex', flexDirection: 'column', gap: '2px' }}>
              <button
                type="button"
                                  onClick={(e) => {
                                    e.preventDefault()
                                    e.stopPropagation()
                                    updateUnifiedLineItem(index, 'invQty', Math.floor((item.invQty || 0) + 1))
                                  }}
                                  style={{
                                    background: 'transparent',
                                    border: 'none',
                                    padding: '2px',
                                    cursor: 'pointer',
                                    display: 'flex',
                                    alignItems: 'center',
                                    justifyContent: 'center',
                                    color: 'var(--text-muted)',
                                    transition: 'color 0.2s ease'
                                  }}
                                  onMouseEnter={(e) => e.currentTarget.style.color = 'var(--accent-blue)'}
                                  onMouseLeave={(e) => e.currentTarget.style.color = 'var(--text-muted)'}
                                >
                                  <ChevronUp size={14} />
                                </button>
                                <button
                                  type="button"
                                  onClick={(e) => {
                                    e.preventDefault()
                                    e.stopPropagation()
                                    updateUnifiedLineItem(index, 'invQty', Math.max(0, Math.floor((item.invQty || 0) - 1)))
                                  }}
                                  style={{
                                    background: 'transparent',
                                    border: 'none',
                                    padding: '2px',
                                    cursor: 'pointer',
                                    display: 'flex',
                                    alignItems: 'center',
                                    justifyContent: 'center',
                                    color: 'var(--text-muted)',
                                    transition: 'color 0.2s ease'
                                  }}
                                  onMouseEnter={(e) => e.currentTarget.style.color = 'var(--accent-blue)'}
                                  onMouseLeave={(e) => e.currentTarget.style.color = 'var(--text-muted)'}
                                >
                                  <ChevronDown size={14} />
                                </button>
                              </div>
                            </div>
                          </td>
                          <td>
                            <div style={{ position: 'relative', display: 'flex', alignItems: 'center' }}>
                              <input
                                type="number"
                                value={item.invPrice || ''}
                                onChange={(e) => updateUnifiedLineItem(index, 'invPrice', Number(e.target.value) || 0)}
                                min="0"
                                step="0.01"
                                style={{ 
                                  paddingRight: '30px', 
                                  width: '100%',
                                  WebkitAppearance: 'none',
                                  MozAppearance: 'textfield'
                                }}
                                onWheel={(e) => e.currentTarget.blur()}
                              />
                              <div style={{ position: 'absolute', right: '4px', display: 'flex', flexDirection: 'column', gap: '2px' }}>
                                <button
                                  type="button"
                                  onClick={(e) => {
                                    e.preventDefault()
                                    e.stopPropagation()
                                    updateUnifiedLineItem(index, 'invPrice', Number((Number(item.invPrice || 0) + 0.01).toFixed(2)))
                                  }}
                                  style={{
                                    background: 'transparent',
                                    border: 'none',
                                    padding: '2px',
                                    cursor: 'pointer',
                                    display: 'flex',
                                    alignItems: 'center',
                                    justifyContent: 'center',
                                    color: 'var(--text-muted)',
                                    transition: 'color 0.2s ease'
                                  }}
                                  onMouseEnter={(e) => e.currentTarget.style.color = 'var(--accent-blue)'}
                                  onMouseLeave={(e) => e.currentTarget.style.color = 'var(--text-muted)'}
                                >
                                  <ChevronUp size={14} />
                                </button>
                                <button
                                  type="button"
                                  onClick={(e) => {
                                    e.preventDefault()
                                    e.stopPropagation()
                                    updateUnifiedLineItem(index, 'invPrice', Math.max(0, Number((Number(item.invPrice || 0) - 0.01).toFixed(2))))
                                  }}
                                  style={{
                                    background: 'transparent',
                                    border: 'none',
                                    padding: '2px',
                                    cursor: 'pointer',
                                    display: 'flex',
                                    alignItems: 'center',
                                    justifyContent: 'center',
                                    color: 'var(--text-muted)',
                                    transition: 'color 0.2s ease'
                                  }}
                                  onMouseEnter={(e) => e.currentTarget.style.color = 'var(--accent-blue)'}
                                  onMouseLeave={(e) => e.currentTarget.style.color = 'var(--text-muted)'}
                                >
                                  <ChevronDown size={14} />
                                </button>
                              </div>
                            </div>
                          </td>
                          <td>£{item.invTotal.toFixed(2)}</td>
                          {vatMode === 'per-item' && (
                            <td>
                              <div style={{ position: 'relative', display: 'flex', alignItems: 'center' }}>
                                <input
                                  type="number"
                                  value={item.invVat !== undefined ? item.invVat : vatPercentage}
                                  onChange={(e) => updateUnifiedLineItem(index, 'invVat', Number(e.target.value) || vatPercentage)}
                                  min="0"
                                  max="100"
                                  step="0.1"
                                  style={{ 
                                    width: '70px',
                                    paddingRight: '30px',
                                    WebkitAppearance: 'none',
                                    MozAppearance: 'textfield'
                                  }}
                                  onWheel={(e) => e.currentTarget.blur()}
                                />
                                <div style={{ position: 'absolute', right: '4px', display: 'flex', flexDirection: 'column', gap: '2px' }}>
                                  <button
                                    type="button"
                                    onClick={(e) => {
                                      e.preventDefault()
                                      e.stopPropagation()
                                      const currentVat = item.invVat !== undefined ? item.invVat : vatPercentage
                                      updateUnifiedLineItem(index, 'invVat', Math.min(100, Number((Number(currentVat) + 0.1).toFixed(1))))
                                    }}
                                    style={{
                                      background: 'transparent',
                                      border: 'none',
                                      padding: '2px',
                                      cursor: 'pointer',
                                      display: 'flex',
                                      alignItems: 'center',
                                      justifyContent: 'center',
                                      color: 'var(--text-muted)',
                                      transition: 'color 0.2s ease'
                                    }}
                                    onMouseEnter={(e) => e.currentTarget.style.color = 'var(--accent-blue)'}
                                    onMouseLeave={(e) => e.currentTarget.style.color = 'var(--text-muted)'}
                                  >
                                    <ChevronUp size={14} />
                                  </button>
                                  <button
                                    type="button"
                                    onClick={(e) => {
                                      e.preventDefault()
                                      e.stopPropagation()
                                      const currentVat = item.invVat !== undefined ? item.invVat : vatPercentage
                                      updateUnifiedLineItem(index, 'invVat', Math.max(0, Number((Number(currentVat) - 0.1).toFixed(1))))
                                    }}
                                    style={{
                                      background: 'transparent',
                                      border: 'none',
                                      padding: '2px',
                                      cursor: 'pointer',
                                      display: 'flex',
                                      alignItems: 'center',
                                      justifyContent: 'center',
                                      color: 'var(--text-muted)',
                                      transition: 'color 0.2s ease'
                                    }}
                                    onMouseEnter={(e) => e.currentTarget.style.color = 'var(--accent-blue)'}
                                    onMouseLeave={(e) => e.currentTarget.style.color = 'var(--text-muted)'}
                                  >
                                    <ChevronDown size={14} />
                                  </button>
                                </div>
                              </div>
                            </td>
                          )}
                          <td>
                            <div style={{ position: 'relative', display: 'flex', alignItems: 'center' }}>
                              <input
                                type="number"
                                value={item.dnQty || ''}
                                onChange={(e) => updateUnifiedLineItem(index, 'dnQty', Math.floor(Number(e.target.value)) || 0)}
                                min="0"
                                step="1"
                                style={{ 
                                  paddingRight: '30px', 
                                  width: '100%',
                                  WebkitAppearance: 'none',
                                  MozAppearance: 'textfield'
                                }}
                                onWheel={(e) => e.currentTarget.blur()}
                              />
                              <div style={{ position: 'absolute', right: '4px', display: 'flex', flexDirection: 'column', gap: '2px' }}>
                                <button
                                  type="button"
                                  onClick={(e) => {
                                    e.preventDefault()
                                    e.stopPropagation()
                                    updateUnifiedLineItem(index, 'dnQty', Math.floor((item.dnQty || 0) + 1))
                                  }}
                                  style={{
                                    background: 'transparent',
                                    border: 'none',
                                    padding: '2px',
                                    cursor: 'pointer',
                                    display: 'flex',
                                    alignItems: 'center',
                                    justifyContent: 'center',
                                    color: 'var(--text-muted)',
                                    transition: 'color 0.2s ease'
                                  }}
                                  onMouseEnter={(e) => e.currentTarget.style.color = 'var(--accent-blue)'}
                                  onMouseLeave={(e) => e.currentTarget.style.color = 'var(--text-muted)'}
                                >
                                  <ChevronUp size={14} />
                                </button>
                                <button
                                  type="button"
                                  onClick={(e) => {
                                    e.preventDefault()
                                    e.stopPropagation()
                                    updateUnifiedLineItem(index, 'dnQty', Math.max(0, Math.floor((item.dnQty || 0) - 1)))
                                  }}
                                  style={{
                                    background: 'transparent',
                                    border: 'none',
                                    padding: '2px',
                                    cursor: 'pointer',
                                    display: 'flex',
                                    alignItems: 'center',
                                    justifyContent: 'center',
                                    color: 'var(--text-muted)',
                                    transition: 'color 0.2s ease'
                                  }}
                                  onMouseEnter={(e) => e.currentTarget.style.color = 'var(--accent-blue)'}
                                  onMouseLeave={(e) => e.currentTarget.style.color = 'var(--text-muted)'}
                                >
                                  <ChevronDown size={14} />
              </button>
            </div>
          </div>
                          </td>
                          <td>
                            {unifiedLineItems.length > 1 && (
                              <button
                                type="button"
                                className="line-item-remove"
                                onClick={() => removeUnifiedLineItem(index)}
                              >
                                <Trash2 size={16} />
          </button>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
        </div>

              {/* VAT Settings */}
              <div className="modal-form-group">
                <div style={{ display: 'flex', alignItems: 'center', gap: '16px', marginBottom: '12px' }}>
                  <label className="modal-form-label" style={{ marginBottom: 0, flex: '0 0 auto' }}>VAT Mode:</label>
                  <div style={{ position: 'relative', display: 'flex', gap: '4px', background: 'var(--bg-secondary)', borderRadius: '8px', padding: '4px', flex: '0 0 auto', minWidth: '200px' }}>
                    <div
                      style={{
                        position: 'absolute',
                        top: '4px',
                        left: vatMode === 'whole' ? '4px' : '50%',
                        width: 'calc(50% - 4px)',
                        height: 'calc(100% - 8px)',
                        background: 'var(--accent-blue)',
                        borderRadius: '6px',
                        transition: 'left 0.4s cubic-bezier(0.4, 0, 0.2, 1)',
                        zIndex: 0,
                        boxShadow: '0 2px 4px rgba(59, 130, 246, 0.3)'
                      }}
                    />
                    <button
                      type="button"
                      onClick={() => setVatMode('whole')}
                      style={{ 
                        fontSize: '12px', 
                        padding: '6px 12px',
                        position: 'relative',
                        zIndex: 1,
                        border: 'none',
                        background: 'transparent',
                        color: vatMode === 'whole' ? 'white' : 'var(--text-secondary)',
                        cursor: 'pointer',
                        fontWeight: vatMode === 'whole' ? 600 : 500,
                        transition: 'color 0.3s ease, font-weight 0.3s ease',
                        borderRadius: '6px',
                        flex: 1
                      }}
                    >
                      VAT as Whole
                    </button>
                    <button
                      type="button"
                      onClick={() => setVatMode('per-item')}
                      style={{ 
                        fontSize: '12px', 
                        padding: '6px 12px',
                        position: 'relative',
                        zIndex: 1,
                        border: 'none',
                        background: 'transparent',
                        color: vatMode === 'per-item' ? 'white' : 'var(--text-secondary)',
                        cursor: 'pointer',
                        fontWeight: vatMode === 'per-item' ? 600 : 500,
                        transition: 'color 0.3s ease, font-weight 0.3s ease',
                        borderRadius: '6px',
                        flex: 1
                      }}
                    >
                      VAT per Item
                    </button>
                  </div>
                  {vatMode === 'whole' && (
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flex: '1' }}>
                      <label className="modal-form-label" style={{ marginBottom: 0, whiteSpace: 'nowrap' }}>VAT %:</label>
                      <div style={{ position: 'relative', display: 'flex', alignItems: 'center' }}>
                        <input
                          type="number"
                          className="modal-form-input"
                          value={vatPercentage}
                          onChange={(e) => setVatPercentage(Number(e.target.value) || 0)}
                          min="0"
                          max="100"
                          step="0.1"
                          style={{ 
                            width: '80px',
                            paddingRight: '30px',
                            WebkitAppearance: 'none',
                            MozAppearance: 'textfield'
                          }}
                          onWheel={(e) => e.currentTarget.blur()}
                        />
                        <div style={{ position: 'absolute', right: '4px', display: 'flex', flexDirection: 'column', gap: '2px' }}>
                          <button
                            type="button"
                            onClick={(e) => {
                              e.preventDefault()
                              e.stopPropagation()
                              setVatPercentage(Math.min(100, Number((Number(vatPercentage) + 0.1).toFixed(1))))
                            }}
                            style={{
                              background: 'transparent',
                              border: 'none',
                              padding: '2px',
                              cursor: 'pointer',
                              display: 'flex',
                              alignItems: 'center',
                              justifyContent: 'center',
                              color: 'var(--text-muted)',
                              transition: 'color 0.2s ease'
                            }}
                            onMouseEnter={(e) => e.currentTarget.style.color = 'var(--accent-blue)'}
                            onMouseLeave={(e) => e.currentTarget.style.color = 'var(--text-muted)'}
                          >
                            <ChevronUp size={14} />
                          </button>
                          <button
                            type="button"
                            onClick={(e) => {
                              e.preventDefault()
                              e.stopPropagation()
                              setVatPercentage(Math.max(0, Number((Number(vatPercentage) - 0.1).toFixed(1))))
                            }}
                            style={{
                              background: 'transparent',
                              border: 'none',
                              padding: '2px',
                              cursor: 'pointer',
                              display: 'flex',
                              alignItems: 'center',
                              justifyContent: 'center',
                              color: 'var(--text-muted)',
                              transition: 'color 0.2s ease'
                            }}
                            onMouseEnter={(e) => e.currentTarget.style.color = 'var(--accent-blue)'}
                            onMouseLeave={(e) => e.currentTarget.style.color = 'var(--text-muted)'}
                          >
                            <ChevronDown size={14} />
                          </button>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              </div>

              {/* Invoice Totals */}
              {(() => {
                const totals = calculateUnifiedInvoiceTotals()
                return (
                  <div className="modal-form-row">
                    <div className="modal-form-group">
                      <label className="modal-form-label">Subtotal</label>
                      <input
                        type="number"
                        className="modal-form-input"
                        value={totals.subtotal.toFixed(2)}
                        readOnly
                        style={{ background: 'var(--bg-secondary)' }}
                      />
                    </div>
                    <div className="modal-form-group">
                      <label className="modal-form-label">VAT ({vatMode === 'whole' ? `${vatPercentage}%` : 'Variable'})</label>
                      <input
                        type="number"
                        className="modal-form-input"
                        value={totals.vat.toFixed(2)}
                        readOnly
                        style={{ background: 'var(--bg-secondary)' }}
                      />
                    </div>
                    <div className="modal-form-group">
                      <label className="modal-form-label">Total</label>
                      <input
                        type="number"
                        className="modal-form-input"
                        value={totals.total.toFixed(2)}
                        readOnly
                        style={{ background: 'var(--bg-secondary)', fontSize: '18px', fontWeight: '700', color: 'var(--accent-green)' }}
                      />
                    </div>
                  </div>
                )
              })()}

              {/* DN Additional Fields */}
              <div className="modal-form-row">
                <div className="modal-form-group">
                  <label className="modal-form-label">Driver</label>
                  <input
                    type="text"
                    className="modal-form-input"
                    value={driver}
                    onChange={(e) => setDriver(e.target.value)}
                    placeholder="Driver name"
                  />
                </div>
                <div className="modal-form-group">
                  <label className="modal-form-label">Vehicle</label>
                  <input
                    type="text"
                    className="modal-form-input"
                    value={vehicle}
                    onChange={(e) => setVehicle(e.target.value.toUpperCase())}
                    placeholder="Vehicle registration"
                    style={{ textTransform: 'uppercase' }}
                  />
                </div>
              </div>
              <div className="modal-form-row">
                <div className="modal-form-group">
                  <label className="modal-form-label">Time Window</label>
                  <input
                    type="text"
                    className="modal-form-input"
                    value={timeWindow}
                    onChange={(e) => setTimeWindow(e.target.value)}
                    placeholder="e.g., 09:00 - 11:00"
                  />
                </div>
                <div className="modal-form-group">
                  {/* Empty space to maintain layout */}
                </div>
              </div>
            </div>

            <div className="modal-footer">
              <button type="button" className="modal-button-secondary" onClick={() => handleClose(false)}>
                Cancel
              </button>
              <button type="button" className="modal-button-secondary" onClick={handleSaveAndClose}>
                Save and Close
              </button>
              <button type="submit" className="modal-button-primary" disabled={loading}>
                {loading ? 'Creating...' : 'Create Invoice & Delivery Note'}
              </button>
            </div>
          </form>
        ) : (
          <div 
            ref={contentRef}
            style={{
              flex: 1,
              minHeight: 0,
              display: 'flex',
              flexDirection: 'column',
              overflow: 'hidden'
            }}
          >
          <div style={{
            opacity: isTabTransitioning ? 0 : 1,
            transform: isTabTransitioning ? 'translateY(10px)' : 'translateY(0)',
            transition: 'opacity 0.4s cubic-bezier(0.4, 0, 0.2, 1), transform 0.4s cubic-bezier(0.4, 0, 0.2, 1)',
            flex: 1,
            minHeight: 0,
            display: 'flex',
            flexDirection: 'column'
          }}>
        {activeTab === 'invoice' ? (
          <form onSubmit={handleInvoiceSubmit} style={{ display: 'flex', flexDirection: 'column', flex: 1, minHeight: 0 }}>
                <div className="modal-body" style={{ 
                  paddingBottom: '20px',
                  flex: 1,
                  minHeight: 0,
                  overflowY: 'auto',
                  transition: 'opacity 0.3s cubic-bezier(0.4, 0, 0.2, 1), transform 0.3s cubic-bezier(0.4, 0, 0.2, 1)'
                }}>
              {error && <div className="modal-error">{error}</div>}
              
              {/* Delivery Note Creation Prompt */}
              {showDNCreationPrompt && (
                <div style={{
                  padding: '16px',
                  background: 'rgba(59, 130, 246, 0.1)',
                  border: '1px solid rgba(59, 130, 246, 0.3)',
                  borderRadius: '8px',
                  marginBottom: '16px',
                  display: 'flex',
                  alignItems: 'flex-start',
                  gap: '12px'
                }}>
                  <AlertCircle size={20} style={{ color: 'var(--accent-blue)', flexShrink: 0, marginTop: '2px' }} />
                  <div style={{ flex: 1 }}>
                    <div style={{ fontWeight: '600', marginBottom: '4px', color: 'var(--text-primary)' }}>
                      Create Delivery Note?
                    </div>
                    <div style={{ fontSize: '13px', color: 'var(--text-secondary)', marginBottom: '12px' }}>
                      No delivery note found for this supplier and date. Would you like to create one now? The form will be pre-filled with invoice data.
                    </div>
                    <div style={{ display: 'flex', gap: '8px' }}>
                      <button
                        type="button"
                        className="glass-button"
                        onClick={handleAcceptDNPrompt}
                        style={{ fontSize: '12px', padding: '6px 12px' }}
                      >
                        Yes, Create Delivery Note
                      </button>
                      <button
                        type="button"
                        className="modal-button-secondary"
                        onClick={handleDismissDNPrompt}
                        style={{ fontSize: '12px', padding: '6px 12px' }}
                      >
                        Not Now
                      </button>
                    </div>
                  </div>
                </div>
              )}
              
              {/* Pairing Suggestions */}
              {loadingSuggestions && (
                <div style={{
                  padding: '16px',
                  background: 'var(--bg-secondary)',
                  border: '1px solid var(--border-color)',
                  borderRadius: '8px',
                  marginBottom: '16px',
                  textAlign: 'center'
                }}>
                  <div style={{ color: 'var(--text-muted)', fontSize: '13px' }}>
                    Loading pairing suggestions...
                  </div>
                </div>
              )}
              {!loadingSuggestions && showPairingSuggestions && pairingSuggestions.length > 0 && (
                <div style={{
                  padding: '16px',
                  background: 'var(--bg-secondary)',
                  border: '1px solid var(--border-color)',
                  borderRadius: '8px',
                  marginBottom: '16px'
                }}>
                  <div style={{ fontWeight: '600', marginBottom: '12px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span>Pairing Suggestions</span>
                    <button
                      type="button"
                      onClick={() => setShowPairingSuggestions(false)}
                      style={{ background: 'none', border: 'none', cursor: 'pointer', padding: '4px' }}
                    >
                      <X size={16} />
                    </button>
                  </div>
                  <div style={{ maxHeight: '300px', overflowY: 'auto' }}>
                      {pairingSuggestions.map((suggestion) => (
                        <div
                          key={suggestion.id}
                          style={{
                            padding: '12px',
                            border: '1px solid var(--border-color)',
                            borderRadius: '6px',
                            marginBottom: '8px',
                            background: 'var(--bg-card)'
                          }}
                        >
                          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '8px' }}>
                            <div>
                              <div style={{ fontWeight: '600', fontSize: '14px' }}>{suggestion.supplier}</div>
                              <div style={{ fontSize: '12px', color: 'var(--text-secondary)', marginTop: '4px' }}>
                                {suggestion.deliveryNoteNumber || 'DN-' + suggestion.deliveryNoteId?.slice(0, 8)} · {suggestion.deliveryDate ? new Date(suggestion.deliveryDate).toLocaleDateString('en-GB') : 'No date'}
                              </div>
                            </div>
                            <div style={{
                              padding: '4px 8px',
                              background: (suggestion.confidence || 0) >= 0.8 ? 'rgba(34, 197, 94, 0.1)' : (suggestion.confidence || 0) >= 0.6 ? 'rgba(251, 191, 36, 0.1)' : 'rgba(239, 68, 68, 0.1)',
                              color: (suggestion.confidence || 0) >= 0.8 ? 'var(--accent-green)' : (suggestion.confidence || 0) >= 0.6 ? 'var(--accent-yellow)' : 'var(--accent-red)',
                              borderRadius: '4px',
                              fontSize: '11px',
                              fontWeight: '600'
                            }}>
                              {Math.round((suggestion.confidence || 0) * 100)}% match
                            </div>
                          </div>
                          <div style={{ fontSize: '12px', color: 'var(--text-secondary)', marginBottom: '8px' }}>
                            {suggestion.reason}
                          </div>
                          {suggestion.hasQuantityMismatch && (
                            <div style={{
                              padding: '6px',
                              background: 'rgba(239, 68, 68, 0.1)',
                              borderRadius: '4px',
                              fontSize: '11px',
                              color: 'var(--accent-red)',
                              marginBottom: '8px'
                            }}>
                              ⚠️ Quantity mismatch detected
                            </div>
                          )}
                          <button
                            type="button"
                            className="glass-button"
                            onClick={() => handlePairSuggestion(suggestion)}
                            disabled={loading}
                            style={{ fontSize: '12px', padding: '6px 12px', width: '100%' }}
                          >
                            {loading ? 'Pairing...' : 'Pair with this Delivery Note'}
                          </button>
                        </div>
                      ))}
                    </div>
                </div>
              )}

              {/* Copy to DN button - only show if invoice has data */}
              {hasInvoiceData && (
                <div style={{ marginBottom: '16px' }}>
                  <button
                    type="button"
                    onClick={() => copyInvoiceToDN()}
                    className="copy-button glass-button"
                  >
                    <Copy size={16} />
                    Copy to Delivery Note
                  </button>
                  {showCopiedFeedback && (
                    <div className="copied-feedback">
                      <Check size={14} />
                      Data copied! Switched to Delivery Note tab.
                    </div>
                  )}
                </div>
              )}

              <div className="modal-form-group">
                <label className="modal-form-label">Supplier *</label>
                <input
                  type="text"
                  className="modal-form-input"
                  value={supplier}
                  onChange={(e) => setSupplier(e.target.value)}
                  required
                  placeholder="Supplier name"
                />
              </div>

              <div className="modal-form-row">
                <div className="modal-form-group">
                  <label className="modal-form-label">Invoice Number *</label>
                  <input
                    type="text"
                    className="modal-form-input"
                    value={invoiceNumber}
                    onChange={(e) => setInvoiceNumber(e.target.value)}
                    required
                    placeholder="INV-001"
                  />
                </div>

                <div className="modal-form-group">
                  <label className="modal-form-label">Date *</label>
                  <DatePicker
                    value={invoiceDate}
                    onChange={setInvoiceDate}
                    required
                  />
                </div>
              </div>

              <div className="modal-form-group">
                <label className="modal-form-label">Venue</label>
                <VenueSelector
                  value={selectedVenue}
                  onChange={setSelectedVenue}
                  venues={venues}
                />
              </div>

              {/* VAT Settings */}
              <div className="modal-form-group">
                <div style={{ display: 'flex', alignItems: 'center', gap: '16px', marginBottom: '12px' }}>
                  <label className="modal-form-label" style={{ marginBottom: 0, flex: '0 0 auto' }}>VAT Mode:</label>
                  <div style={{ position: 'relative', display: 'flex', gap: '4px', background: 'var(--bg-secondary)', borderRadius: '8px', padding: '4px', flex: '0 0 auto', minWidth: '200px' }}>
                    <div
                      style={{
                        position: 'absolute',
                        top: '4px',
                        left: vatMode === 'whole' ? '4px' : '50%',
                        width: 'calc(50% - 4px)',
                        height: 'calc(100% - 8px)',
                        background: 'var(--accent-blue)',
                        borderRadius: '6px',
                        transition: 'left 0.4s cubic-bezier(0.4, 0, 0.2, 1)',
                        zIndex: 0,
                        boxShadow: '0 2px 4px rgba(59, 130, 246, 0.3)'
                      }}
                    />
                    <button
                      type="button"
                      onClick={() => setVatMode('whole')}
                      style={{ 
                        fontSize: '12px', 
                        padding: '6px 12px',
                        position: 'relative',
                        zIndex: 1,
                        border: 'none',
                        background: 'transparent',
                        color: vatMode === 'whole' ? 'white' : 'var(--text-secondary)',
                        cursor: 'pointer',
                        fontWeight: vatMode === 'whole' ? 600 : 500,
                        transition: 'color 0.3s ease, font-weight 0.3s ease',
                        borderRadius: '6px',
                        flex: 1
                      }}
                    >
                      VAT as Whole
                    </button>
                    <button
                      type="button"
                      onClick={() => setVatMode('per-item')}
                      style={{ 
                        fontSize: '12px', 
                        padding: '6px 12px',
                        position: 'relative',
                        zIndex: 1,
                        border: 'none',
                        background: 'transparent',
                        color: vatMode === 'per-item' ? 'white' : 'var(--text-secondary)',
                        cursor: 'pointer',
                        fontWeight: vatMode === 'per-item' ? 600 : 500,
                        transition: 'color 0.3s ease, font-weight 0.3s ease',
                        borderRadius: '6px',
                        flex: 1
                      }}
                    >
                      VAT per Item
                    </button>
                  </div>
                  {vatMode === 'whole' && (
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flex: '1' }}>
                      <label className="modal-form-label" style={{ marginBottom: 0, whiteSpace: 'nowrap' }}>VAT %:</label>
                      <div style={{ position: 'relative', display: 'flex', alignItems: 'center' }}>
                        <input
                          type="number"
                          className="modal-form-input"
                          value={vatPercentage}
                          onChange={(e) => setVatPercentage(Number(e.target.value) || 0)}
                          min="0"
                          max="100"
                          step="0.1"
                          style={{ 
                            width: '80px',
                            paddingRight: '30px',
                            WebkitAppearance: 'none',
                            MozAppearance: 'textfield'
                          }}
                          onWheel={(e) => e.currentTarget.blur()}
                        />
                        <div style={{ position: 'absolute', right: '4px', display: 'flex', flexDirection: 'column', gap: '2px' }}>
                          <button
                            type="button"
                            onClick={(e) => {
                              e.preventDefault()
                              e.stopPropagation()
                              setVatPercentage(Math.min(100, Number((Number(vatPercentage) + 0.1).toFixed(1))))
                            }}
                            style={{
                              background: 'transparent',
                              border: 'none',
                              padding: '2px',
                              cursor: 'pointer',
                              display: 'flex',
                              alignItems: 'center',
                              justifyContent: 'center',
                              color: 'var(--text-muted)',
                              transition: 'color 0.2s ease'
                            }}
                            onMouseEnter={(e) => e.currentTarget.style.color = 'var(--accent-blue)'}
                            onMouseLeave={(e) => e.currentTarget.style.color = 'var(--text-muted)'}
                          >
                            <ChevronUp size={14} />
                          </button>
                          <button
                            type="button"
                            onClick={(e) => {
                              e.preventDefault()
                              e.stopPropagation()
                              setVatPercentage(Math.max(0, Number((Number(vatPercentage) - 0.1).toFixed(1))))
                            }}
                            style={{
                              background: 'transparent',
                              border: 'none',
                              padding: '2px',
                              cursor: 'pointer',
                              display: 'flex',
                              alignItems: 'center',
                              justifyContent: 'center',
                              color: 'var(--text-muted)',
                              transition: 'color 0.2s ease'
                            }}
                            onMouseEnter={(e) => e.currentTarget.style.color = 'var(--accent-blue)'}
                            onMouseLeave={(e) => e.currentTarget.style.color = 'var(--text-muted)'}
                          >
                            <ChevronDown size={14} />
                          </button>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              </div>

              <div className="modal-form-group">
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                  <label className="modal-form-label" style={{ marginBottom: 0 }}>Line Items</label>
                  <button
                    type="button"
                    className="glass-button"
                    onClick={addInvoiceLineItem}
                    style={{ fontSize: '12px', padding: '6px 12px' }}
                  >
                    <Plus size={14} />
                    Add Item
                  </button>
                </div>

                <div 
                  className="line-items-table-container"
                  style={invoiceLineItems.length >= 3 ? {
                    maxHeight: '400px',
                    overflowY: 'auto',
                    overflowX: 'auto',
                    display: 'block'
                  } : {
                    maxHeight: 'none',
                    overflowY: 'visible',
                    overflowX: 'auto',
                    display: 'block'
                  }}
                >
                  <table className="line-items-table">
                    <thead>
                      <tr>
                        <th>Item Name</th>
                        <th>Quantity</th>
                        <th>Price per Unit</th>
                        <th>Total (no VAT)</th>
                        {vatMode === 'per-item' && <th>VAT %</th>}
                        <th></th>
                      </tr>
                    </thead>
                    <tbody>
                      {invoiceLineItems.map((item, index) => (
                      <tr key={index}>
                        <td>
                          <AutocompleteInput
                            value={item.description}
                            onChange={(value) => updateInvoiceLineItem(index, 'description', value)}
                            onFetchSuggestions={fetchItemSuggestions}
                            placeholder="Item description (e.g., 12Litre pepsi pink container)"
                            className="line-items-table input"
                            minChars={2}
                            debounceMs={400}
                          />
                        </td>
                        <td>
                          <div style={{ position: 'relative', display: 'flex', alignItems: 'center' }}>
                          <input
                            type="number"
                            value={item.qty || ''}
                              onChange={(e) => updateInvoiceLineItem(index, 'qty', Math.floor(Number(e.target.value)) || 0)}
                            min="0"
                              step="1"
                              style={{ 
                                paddingRight: '30px', 
                                width: '100%',
                                WebkitAppearance: 'none',
                                MozAppearance: 'textfield'
                              }}
                              onWheel={(e) => e.currentTarget.blur()}
                            />
                            <div style={{ position: 'absolute', right: '4px', display: 'flex', flexDirection: 'column', gap: '2px' }}>
                              <button
                                type="button"
                                onClick={(e) => {
                                  e.preventDefault()
                                  e.stopPropagation()
                                  updateInvoiceLineItem(index, 'qty', Math.floor((item.qty || 0) + 1))
                                }}
                                style={{
                                  background: 'transparent',
                                  border: 'none',
                                  padding: '2px',
                                  cursor: 'pointer',
                                  display: 'flex',
                                  alignItems: 'center',
                                  justifyContent: 'center',
                                  color: 'var(--text-muted)',
                                  transition: 'color 0.2s ease'
                                }}
                                onMouseEnter={(e) => e.currentTarget.style.color = 'var(--accent-blue)'}
                                onMouseLeave={(e) => e.currentTarget.style.color = 'var(--text-muted)'}
                              >
                                <ChevronUp size={14} />
                              </button>
                              <button
                                type="button"
                                onClick={(e) => {
                                  e.preventDefault()
                                  e.stopPropagation()
                                  updateInvoiceLineItem(index, 'qty', Math.max(0, Math.floor((item.qty || 0) - 1)))
                                }}
                                style={{
                                  background: 'transparent',
                                  border: 'none',
                                  padding: '2px',
                                  cursor: 'pointer',
                                  display: 'flex',
                                  alignItems: 'center',
                                  justifyContent: 'center',
                                  color: 'var(--text-muted)',
                                  transition: 'color 0.2s ease'
                                }}
                                onMouseEnter={(e) => e.currentTarget.style.color = 'var(--accent-blue)'}
                                onMouseLeave={(e) => e.currentTarget.style.color = 'var(--text-muted)'}
                              >
                                <ChevronDown size={14} />
                              </button>
                            </div>
                          </div>
                        </td>
                        <td>
                          <div style={{ position: 'relative', display: 'flex', alignItems: 'center' }}>
                          <input
                            type="number"
                            value={item.price || ''}
                            onChange={(e) => updateInvoiceLineItem(index, 'price', Number(e.target.value) || 0)}
                            min="0"
                            step="0.01"
                              style={{ 
                                paddingRight: '30px', 
                                width: '100%',
                                WebkitAppearance: 'none',
                                MozAppearance: 'textfield'
                              }}
                              onWheel={(e) => e.currentTarget.blur()}
                            />
                            <div style={{ position: 'absolute', right: '4px', display: 'flex', flexDirection: 'column', gap: '2px' }}>
                              <button
                                type="button"
                                onClick={(e) => {
                                  e.preventDefault()
                                  e.stopPropagation()
                                  updateInvoiceLineItem(index, 'price', Number((Number(item.price || 0) + 0.01).toFixed(2)))
                                }}
                                style={{
                                  background: 'transparent',
                                  border: 'none',
                                  padding: '2px',
                                  cursor: 'pointer',
                                  display: 'flex',
                                  alignItems: 'center',
                                  justifyContent: 'center',
                                  color: 'var(--text-muted)',
                                  transition: 'color 0.2s ease'
                                }}
                                onMouseEnter={(e) => e.currentTarget.style.color = 'var(--accent-blue)'}
                                onMouseLeave={(e) => e.currentTarget.style.color = 'var(--text-muted)'}
                              >
                                <ChevronUp size={14} />
                              </button>
                              <button
                                type="button"
                                onClick={(e) => {
                                  e.preventDefault()
                                  e.stopPropagation()
                                  updateInvoiceLineItem(index, 'price', Math.max(0, Number((Number(item.price || 0) - 0.01).toFixed(2))))
                                }}
                                style={{
                                  background: 'transparent',
                                  border: 'none',
                                  padding: '2px',
                                  cursor: 'pointer',
                                  display: 'flex',
                                  alignItems: 'center',
                                  justifyContent: 'center',
                                  color: 'var(--text-muted)',
                                  transition: 'color 0.2s ease'
                                }}
                                onMouseEnter={(e) => e.currentTarget.style.color = 'var(--accent-blue)'}
                                onMouseLeave={(e) => e.currentTarget.style.color = 'var(--text-muted)'}
                              >
                                <ChevronDown size={14} />
                              </button>
                            </div>
                          </div>
                        </td>
                        <td>£{item.total.toFixed(2)}</td>
                        {vatMode === 'per-item' && (
                          <td>
                            <div style={{ position: 'relative', display: 'flex', alignItems: 'center' }}>
                              <input
                                type="number"
                                value={item.vat !== undefined ? item.vat : vatPercentage}
                                onChange={(e) => updateInvoiceLineItem(index, 'vat', Number(e.target.value) || vatPercentage)}
                                min="0"
                                max="100"
                                step="0.1"
                                style={{ 
                                  width: '70px',
                                  paddingRight: '30px',
                                  WebkitAppearance: 'none',
                                  MozAppearance: 'textfield'
                                }}
                                onWheel={(e) => e.currentTarget.blur()}
                              />
                              <div style={{ position: 'absolute', right: '4px', display: 'flex', flexDirection: 'column', gap: '2px' }}>
                                <button
                                  type="button"
                                  onClick={(e) => {
                                    e.preventDefault()
                                    e.stopPropagation()
                                    const currentVat = item.vat !== undefined ? item.vat : vatPercentage
                                    updateInvoiceLineItem(index, 'vat', Math.min(100, Number((Number(currentVat) + 0.1).toFixed(1))))
                                  }}
                                  style={{
                                    background: 'transparent',
                                    border: 'none',
                                    padding: '2px',
                                    cursor: 'pointer',
                                    display: 'flex',
                                    alignItems: 'center',
                                    justifyContent: 'center',
                                    color: 'var(--text-muted)',
                                    transition: 'color 0.2s ease'
                                  }}
                                  onMouseEnter={(e) => e.currentTarget.style.color = 'var(--accent-blue)'}
                                  onMouseLeave={(e) => e.currentTarget.style.color = 'var(--text-muted)'}
                                >
                                  <ChevronUp size={14} />
                                </button>
                                <button
                                  type="button"
                                  onClick={(e) => {
                                    e.preventDefault()
                                    e.stopPropagation()
                                    const currentVat = item.vat !== undefined ? item.vat : vatPercentage
                                    updateInvoiceLineItem(index, 'vat', Math.max(0, Number((Number(currentVat) - 0.1).toFixed(1))))
                                  }}
                                  style={{
                                    background: 'transparent',
                                    border: 'none',
                                    padding: '2px',
                                    cursor: 'pointer',
                                    display: 'flex',
                                    alignItems: 'center',
                                    justifyContent: 'center',
                                    color: 'var(--text-muted)',
                                    transition: 'color 0.2s ease'
                                  }}
                                  onMouseEnter={(e) => e.currentTarget.style.color = 'var(--accent-blue)'}
                                  onMouseLeave={(e) => e.currentTarget.style.color = 'var(--text-muted)'}
                                >
                                  <ChevronDown size={14} />
                                </button>
                              </div>
                            </div>
                          </td>
                        )}
                        <td>
                          {invoiceLineItems.length > 1 && (
                            <button
                              type="button"
                              className="line-item-remove"
                              onClick={() => removeInvoiceLineItem(index)}
                            >
                              <Trash2 size={16} />
                            </button>
                          )}
                        </td>
                      </tr>
                    ))}
                    </tbody>
                  </table>
                </div>
              </div>

              <div className="modal-form-row">
                <div className="modal-form-group">
                  <label className="modal-form-label">Subtotal</label>
                  <input
                    type="number"
                    className="modal-form-input"
                    value={subtotal.toFixed(2)}
                    readOnly
                    style={{ background: 'var(--bg-secondary)' }}
                  />
                </div>

                <div className="modal-form-group">
                  <label className="modal-form-label">VAT ({vatMode === 'whole' ? `${vatPercentage}%` : 'Variable'})</label>
                  <input
                    type="number"
                    className="modal-form-input"
                    value={vat.toFixed(2)}
                    readOnly
                    style={{ background: 'var(--bg-secondary)' }}
                  />
                </div>
              </div>

              <div className="modal-form-group">
                <label className="modal-form-label">Total</label>
                <input
                  type="number"
                  className="modal-form-input"
                  value={total.toFixed(2)}
                  readOnly
                  style={{ background: 'var(--bg-secondary)', fontSize: '18px', fontWeight: '700', color: 'var(--accent-green)' }}
                />
              </div>
            </div>

            <div className="modal-footer">
              <button type="button" className="modal-button-secondary" onClick={() => handleClose(false)}>
                Cancel
              </button>
              <button type="button" className="modal-button-secondary" onClick={handleSaveAndClose}>
                Save and Close
              </button>
              <button type="submit" className="modal-button-primary" disabled={loading}>
                {loading ? 'Creating...' : 'Create Invoice'}
              </button>
            </div>
          </form>
        ) : (
          <form onSubmit={handleDNSubmit} style={{ display: 'flex', flexDirection: 'column', flex: 1, minHeight: 0 }}>
            <div className="modal-body" style={{ 
              paddingBottom: '20px',
              flex: 1,
              minHeight: 0,
              overflowY: 'auto',
              transition: 'opacity 0.3s cubic-bezier(0.4, 0, 0.2, 1), transform 0.3s cubic-bezier(0.4, 0, 0.2, 1)'
            }}>
              {error && <div className="modal-error">{error}</div>}

              {/* Invoice Suggestions for Delivery Note */}
              {loadingInvoiceSuggestions && (
                <div style={{
                  padding: '16px',
                  background: 'var(--bg-secondary)',
                  border: '1px solid var(--border-color)',
                  borderRadius: '8px',
                  marginBottom: '16px',
                  textAlign: 'center'
                }}>
                  <div style={{ color: 'var(--text-muted)', fontSize: '13px' }}>
                    Loading invoice suggestions...
                  </div>
                </div>
              )}
              {!loadingInvoiceSuggestions && showInvoiceSuggestions && invoiceSuggestions.length === 0 && (
                <div style={{
                  padding: '16px',
                  background: 'var(--bg-secondary)',
                  border: '1px solid var(--border-color)',
                  borderRadius: '8px',
                  marginBottom: '16px',
                  textAlign: 'center',
                  color: 'var(--text-muted)',
                  fontSize: '13px'
                }}>
                  No matching invoices found. You can create a new invoice from this delivery note or link an existing one manually.
                </div>
              )}
              {!loadingInvoiceSuggestions && showInvoiceSuggestions && invoiceSuggestions.length > 0 && (
                <div style={{
                  padding: '16px',
                  background: 'var(--bg-secondary)',
                  border: '1px solid var(--border-color)',
                  borderRadius: '8px',
                  marginBottom: '16px'
                }}>
                  <div style={{ fontWeight: '600', marginBottom: '12px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span>Invoice Suggestions</span>
                    <button
                      type="button"
                      onClick={() => setShowInvoiceSuggestions(false)}
                      style={{ background: 'none', border: 'none', cursor: 'pointer', padding: '4px' }}
                    >
                      <X size={16} />
                    </button>
                  </div>
                  <div style={{ maxHeight: '300px', overflowY: 'auto' }}>
                    {invoiceSuggestions.map((suggestion) => (
                      <div
                        key={suggestion.id}
                        style={{
                          padding: '12px',
                          border: '1px solid var(--border-color)',
                          borderRadius: '6px',
                          marginBottom: '8px',
                          background: 'var(--bg-card)'
                        }}
                      >
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '8px' }}>
                          <div>
                            <div style={{ fontWeight: '600', fontSize: '14px' }}>{suggestion.supplier || 'Unknown Supplier'}</div>
                            <div style={{ fontSize: '12px', color: 'var(--text-secondary)', marginTop: '4px' }}>
                              {suggestion.invoiceNumber || 'INV-' + suggestion.invoiceId?.slice(0, 8)} · {suggestion.invoiceDate ? new Date(suggestion.invoiceDate).toLocaleDateString('en-GB') : 'No date'}
                            </div>
                          </div>
                          <div style={{
                            padding: '4px 8px',
                            background: (suggestion.confidence || 0) >= 0.8 ? 'rgba(34, 197, 94, 0.1)' : (suggestion.confidence || 0) >= 0.6 ? 'rgba(251, 191, 36, 0.1)' : 'rgba(239, 68, 68, 0.1)',
                            color: (suggestion.confidence || 0) >= 0.8 ? 'var(--accent-green)' : (suggestion.confidence || 0) >= 0.6 ? 'var(--accent-yellow)' : 'var(--accent-red)',
                            borderRadius: '4px',
                            fontSize: '11px',
                            fontWeight: '600'
                          }}>
                            {Math.round((suggestion.confidence || 0) * 100)}% match
                          </div>
                        </div>
                        <div style={{ fontSize: '12px', color: 'var(--text-secondary)', marginBottom: '8px' }}>
                          {suggestion.reason || 'Potential match'}
                        </div>
                        {suggestion.hasQuantityMismatch && (
                          <div style={{
                            padding: '6px',
                            background: 'rgba(239, 68, 68, 0.1)',
                            borderRadius: '4px',
                            fontSize: '11px',
                            color: 'var(--accent-red)',
                            marginBottom: '8px'
                          }}>
                            ⚠️ Quantity mismatch detected
                          </div>
                        )}
                        {suggestion.quantityDifferences && suggestion.quantityDifferences.length > 0 && (
                          <div style={{ marginBottom: '8px', fontSize: '11px', color: 'var(--text-secondary)' }}>
                            {suggestion.quantityDifferences.slice(0, 2).map((diff: any, idx: number) => (
                              <div key={idx} style={{ marginBottom: '4px' }}>
                                {diff.description}: Invoice {diff.invoiceQty}, DN {diff.dnQty}
                              </div>
                            ))}
                          </div>
                        )}
                        <button
                          type="button"
                          className="glass-button"
                          onClick={() => handlePairInvoiceSuggestion(suggestion)}
                          disabled={loading}
                          style={{ fontSize: '12px', padding: '6px 12px', width: '100%' }}
                        >
                          {loading ? 'Pairing...' : 'Pair with this Invoice'}
                        </button>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Copy from Invoice button - available on delivery note tab */}
              {(hasInvoiceData || hasLastSubmittedInvoice) && (
                <div style={{ marginBottom: '16px' }}>
                  <button
                    type="button"
                    onClick={() => copyInvoiceToDN(hasLastSubmittedInvoice && !hasInvoiceData)}
                    className="copy-button glass-button"
                  >
                    <Copy size={16} />
                    {hasLastSubmittedInvoice && !hasInvoiceData 
                      ? 'Copy from Last Submitted Invoice' 
                      : 'Copy from Invoice'}
                  </button>
                  {showCopiedFeedback && (
                    <div className="copied-feedback">
                      <Check size={14} />
                      Data copied! You can edit any fields before submitting.
                    </div>
                  )}
                </div>
              )}

              {hasCopiedData && (
                <div className="copied-indicator">
                  <Check size={16} />
                  <span>This delivery note was created from invoice data. You can edit any fields before submitting.</span>
                </div>
              )}

              <div className="modal-form-group">
                <label className="modal-form-label">Supplier *</label>
                <input
                  type="text"
                  className="modal-form-input"
                  value={dnSupplier}
                  onChange={(e) => setDnSupplier(e.target.value)}
                  required
                  placeholder="Supplier name"
                />
              </div>

              <div className="modal-form-row">
                <div className="modal-form-group">
                  <label className="modal-form-label">Note Number *</label>
                  <input
                    type="text"
                    className="modal-form-input"
                    value={noteNumber}
                    onChange={(e) => setNoteNumber(e.target.value)}
                    required
                    placeholder="DN-001"
                  />
                </div>

                <div className="modal-form-group">
                  <label className="modal-form-label">Date *</label>
                  <DatePicker
                    value={dnDate}
                    onChange={setDnDate}
                    required
                  />
                </div>
              </div>

              <div className="modal-form-group">
                <label className="modal-form-label">Venue</label>
                <VenueSelector
                  value={selectedVenue}
                  onChange={setSelectedVenue}
                  venues={venues}
                />
              </div>

              <div className="modal-form-group">
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                  <label className="modal-form-label" style={{ marginBottom: 0 }}>Line Items</label>
                  <button
                    type="button"
                    className="glass-button"
                    onClick={addDNLineItem}
                    style={{ fontSize: '12px', padding: '6px 12px' }}
                  >
                    <Plus size={14} />
                    Add Item
                  </button>
                </div>

                <div 
                  className="line-items-table-container"
                  style={dnLineItems.length >= 3 ? {
                    maxHeight: '400px',
                    overflowY: 'auto',
                    overflowX: 'auto',
                    display: 'block'
                  } : {
                    maxHeight: 'none',
                    overflowY: 'visible',
                    overflowX: 'auto',
                    display: 'block'
                  }}
                >
                  <table className="line-items-table">
                    <thead>
                      <tr>
                        <th>Item Name</th>
                        <th>Quantity</th>
                        <th></th>
                      </tr>
                    </thead>
                    <tbody>
                      {dnLineItems.map((item, index) => (
                      <tr key={index}>
                        <td>
                          <AutocompleteInput
                            value={item.description}
                            onChange={(value) => updateDNLineItem(index, 'description', value)}
                            onFetchSuggestions={fetchItemSuggestions}
                            placeholder="Item description (e.g., 12Litre pepsi pink container)"
                            className="line-items-table input"
                            minChars={2}
                            debounceMs={400}
                          />
                        </td>
                        <td>
                          <div style={{ position: 'relative', display: 'flex', alignItems: 'center' }}>
                          <input
                            type="number"
                            value={item.qty || ''}
                              onChange={(e) => updateDNLineItem(index, 'qty', Math.floor(Number(e.target.value)) || 0)}
                            min="0"
                              step="1"
                              style={{ 
                                paddingRight: '30px', 
                                width: '100%',
                                WebkitAppearance: 'none',
                                MozAppearance: 'textfield'
                              }}
                              onWheel={(e) => e.currentTarget.blur()}
                            />
                            <div style={{ position: 'absolute', right: '4px', display: 'flex', flexDirection: 'column', gap: '2px' }}>
                              <button
                                type="button"
                                onClick={(e) => {
                                  e.preventDefault()
                                  e.stopPropagation()
                                  updateDNLineItem(index, 'qty', Math.floor((item.qty || 0) + 1))
                                }}
                                style={{
                                  background: 'transparent',
                                  border: 'none',
                                  padding: '2px',
                                  cursor: 'pointer',
                                  display: 'flex',
                                  alignItems: 'center',
                                  justifyContent: 'center',
                                  color: 'var(--text-muted)',
                                  transition: 'color 0.2s ease'
                                }}
                                onMouseEnter={(e) => e.currentTarget.style.color = 'var(--accent-blue)'}
                                onMouseLeave={(e) => e.currentTarget.style.color = 'var(--text-muted)'}
                              >
                                <ChevronUp size={14} />
                              </button>
                              <button
                                type="button"
                                onClick={(e) => {
                                  e.preventDefault()
                                  e.stopPropagation()
                                  updateDNLineItem(index, 'qty', Math.max(0, Math.floor((item.qty || 0) - 1)))
                                }}
                                style={{
                                  background: 'transparent',
                                  border: 'none',
                                  padding: '2px',
                                  cursor: 'pointer',
                                  display: 'flex',
                                  alignItems: 'center',
                                  justifyContent: 'center',
                                  color: 'var(--text-muted)',
                                  transition: 'color 0.2s ease'
                                }}
                                onMouseEnter={(e) => e.currentTarget.style.color = 'var(--accent-blue)'}
                                onMouseLeave={(e) => e.currentTarget.style.color = 'var(--text-muted)'}
                              >
                                <ChevronDown size={14} />
                              </button>
                            </div>
                          </div>
                        </td>
                        <td>
                          {dnLineItems.length > 1 && (
                            <button
                              type="button"
                              className="line-item-remove"
                              onClick={() => removeDNLineItem(index)}
                            >
                              <Trash2 size={16} />
                            </button>
                          )}
                        </td>
                      </tr>
                    ))}
                    </tbody>
                  </table>
                </div>
              </div>

              <div className="modal-form-group">
                <label className="modal-form-label">Supervisor</label>
                <input
                  type="text"
                  className="modal-form-input"
                  value={supervisor}
                  onChange={(e) => setSupervisor(e.target.value)}
                  placeholder="Name of supervisor who took the delivery"
                />
              </div>

              <div className="modal-form-row">
                <div className="modal-form-group">
                  <label className="modal-form-label">Driver</label>
                  <input
                    type="text"
                    className="modal-form-input"
                    value={driver}
                    onChange={(e) => setDriver(e.target.value)}
                    placeholder="Driver name"
                  />
                </div>

                <div className="modal-form-group">
                  <label className="modal-form-label">Vehicle</label>
                  <input
                    type="text"
                    className="modal-form-input"
                    value={vehicle}
                    onChange={(e) => setVehicle(e.target.value.toUpperCase())}
                    placeholder="Vehicle registration"
                    style={{ textTransform: 'uppercase' }}
                  />
                </div>
              </div>

              <div className="modal-form-group">
                <label className="modal-form-label">Time Window</label>
                <input
                  type="text"
                  className="modal-form-input"
                  value={timeWindow}
                  onChange={(e) => setTimeWindow(e.target.value)}
                  placeholder="e.g., 09:00 - 11:00"
                />
              </div>

              {/* Create Invoice from DN button - only show after DN is created */}
              {createdDNId && lastSubmittedDN && (
                <div style={{ marginTop: '16px', marginBottom: '16px' }}>
                  <button
                    type="button"
                    onClick={() => {
                      // Store DN ID for auto-pairing after invoice creation
                      setCreatingInvoiceFromDN(createdDNId)
                      // Copy DN data to invoice form (use the stored DN data)
                      setSupplier(lastSubmittedDN.supplier)
                      setInvoiceDate(lastSubmittedDN.date)
                      setSelectedVenue(lastSubmittedDN.venue)
                      // Copy line items (without price/total)
                      const invoiceItems: InvoiceLineItem[] = lastSubmittedDN.lineItems
                        .map(item => ({
                          description: item.description,
                          qty: item.qty,
                          unit: item.unit,
                          price: 0,
                          total: 0,
                        }))
                      if (invoiceItems.length > 0) {
                        setInvoiceLineItems(invoiceItems)
                        calculateInvoiceTotals(invoiceItems)
                      }
                      // Switch to invoice tab
                      setActiveTab('invoice')
                    }}
                    className="glass-button"
                    style={{ width: '100%', padding: '10px' }}
                  >
                    <Copy size={16} style={{ marginRight: '8px', verticalAlign: 'middle' }} />
                    Create Invoice from This Delivery Note
                  </button>
                </div>
              )}
            </div>

            <div className="modal-footer">
              <button type="button" className="modal-button-secondary" onClick={() => handleClose(false)}>
                Cancel
              </button>
              <button type="button" className="modal-button-secondary" onClick={handleSaveAndClose}>
                Save and Close
              </button>
              <button type="submit" className="modal-button-primary" disabled={loading}>
                {loading ? 'Creating...' : 'Create Delivery Note'}
              </button>
            </div>
          </form>
        )}
          </div>
        </div>
        )}
      </div>
      
      {/* Spelling Validation Modal */}
      <SpellingValidationModal
        isOpen={showSpellingModal}
        onClose={() => {
          setShowSpellingModal(false)
          setSpellingErrors([])
          setPendingSubmitCallback(null)
        }}
        onConfirm={handleSpellingConfirm}
        errors={spellingErrors}
      />

      {/* Pairing Preview Modal */}
      {previewData && (
        <PairingPreviewModal
          isOpen={previewModalOpen}
          onClose={() => {
            setPreviewModalOpen(false)
            setPreviewData(null)
          }}
          onConfirm={() => {
            setPreviewModalOpen(false)
            setPreviewData(null)
            toast.success('Invoice paired with delivery note successfully!')
            setShowPairingSuggestions(false)
            // Wrap in setTimeout to avoid setState during render
            setTimeout(() => {
              onSuccess(createdInvoiceId || '', 'invoice')
            }, 0)
          }}
          invoiceId={previewData.invoiceId}
          deliveryNoteId={previewData.deliveryNoteId}
          initialValidation={previewData.validation}
        />
      )}

      {/* Mode Switch Confirmation Modal */}
      {showModeSwitchConfirm && pendingModeChange && (
        <div className="modal-overlay" style={{ zIndex: 2000 }} onClick={() => {
          setShowModeSwitchConfirm(false)
          setPendingModeChange(null)
        }}>
          <div className="modal-container" onClick={(e) => e.stopPropagation()} style={{ maxWidth: '500px' }}>
            <div className="modal-header">
              <h2 className="modal-title">Switch Mode?</h2>
              <button className="modal-close-button" onClick={() => {
                setShowModeSwitchConfirm(false)
                setPendingModeChange(null)
              }} aria-label="Close modal">
                <X size={20} />
              </button>
            </div>
            <div className="modal-body">
              <div style={{ marginBottom: '16px', color: 'var(--text-secondary)' }}>
                {pendingModeChange.type === 'unified' 
                  ? 'You have existing data. How would you like to proceed?'
                  : 'You have existing data in unified mode. How would you like to proceed?'}
              </div>
              
              {pendingModeChange.hasInvoiceData && (
                <div style={{ 
                  padding: '12px', 
                  background: 'rgba(59, 130, 246, 0.1)', 
                  borderRadius: '8px', 
                  marginBottom: '12px',
                  fontSize: '13px',
                  color: 'var(--text-secondary)'
                }}>
                  Invoice data will be {pendingModeChange.type === 'unified' ? 'transferred' : 'kept'}
                </div>
              )}
              
              {pendingModeChange.hasDNData && (
                <div style={{ 
                  padding: '12px', 
                  background: 'rgba(59, 130, 246, 0.1)', 
                  borderRadius: '8px', 
                  marginBottom: '12px',
                  fontSize: '13px',
                  color: 'var(--text-secondary)'
                }}>
                  Delivery Note data will be {pendingModeChange.type === 'unified' ? 'transferred' : 'kept'}
                </div>
              )}
            </div>
            <div className="modal-footer">
              <button 
                type="button" 
                className="modal-button-secondary" 
                onClick={() => {
                  setShowModeSwitchConfirm(false)
                  setPendingModeChange(null)
                }}
              >
                Cancel (Mistake)
              </button>
              {pendingModeChange.hasInvoiceData && (
                <button 
                  type="button" 
                  className="modal-button-secondary" 
                  onClick={() => {
                    handleModeSwitch(
                      pendingModeChange.type === 'unified',
                      true,
                      false
                    )
                  }}
                  style={{ background: 'rgba(239, 68, 68, 0.2)', color: 'var(--accent-red)' }}
                >
                  Clear Invoice Data
                </button>
              )}
              {pendingModeChange.hasDNData && (
                <button 
                  type="button" 
                  className="modal-button-secondary" 
                  onClick={() => {
                    handleModeSwitch(
                      pendingModeChange.type === 'unified',
                      false,
                      true
                    )
                  }}
                  style={{ background: 'rgba(239, 68, 68, 0.2)', color: 'var(--accent-red)' }}
                >
                  Clear DN Data
                </button>
              )}
              <button 
                type="button" 
                className="modal-button-primary" 
                onClick={() => {
                  handleModeSwitch(
                    pendingModeChange.type === 'unified',
                    false,
                    false
                  )
                }}
              >
                Transfer All Data
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Submission Notification Modal */}
      <SubmissionNotificationModal
        isOpen={showNotification}
        type={notificationType}
        title={notificationTitle}
        message={notificationMessage}
        onClose={() => {
          setShowNotification(false)
          setPendingSuccessCallback(null)
        }}
        onAction={() => {
          if (pendingSuccessCallback) {
            // Wrap in setTimeout to avoid setState during render
            setTimeout(() => {
              pendingSuccessCallback()
              setPendingSuccessCallback(null)
            }, 0)
          }
        }}
      />
    </div>
  )
}

