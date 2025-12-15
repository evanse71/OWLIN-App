import { useState, useEffect, useCallback, useRef } from 'react'
import { AppHeader } from '../components/layout/AppHeader'
import { InvoicesHeader, type DateRange } from '../components/invoices/InvoicesHeader'
import { ChatAssistant } from '../components/ChatAssistant'
import { DocumentList, type InvoiceListItem } from '../components/invoices/DocumentList'
import { DocumentDetailPanel, type InvoiceDetail } from '../components/invoices/DocumentDetailPanel'
import { SmartDiscrepancyWidget, type DiscrepancyContext } from '../components/invoices/SmartDiscrepancyWidget'
import { DiscrepancyPanel } from '../components/discrepancies/DiscrepancyPanel'
import { DeliveryNotesCardsSection } from '../components/invoices/DeliveryNotesCardsSection'
import { buildInvoiceListDiscrepancies, buildInvoiceDetailDiscrepancies } from '../lib/discrepancyBuilders'
import type { DiscrepancyItem } from '../lib/discrepanciesApi'
import type { Issue, DeliveryNoteInfo } from '../components/invoices/IssuesActionsPanel'
import { ProminentUploadZone } from '../components/invoices/ProminentUploadZone'
import { CompactDragDropZone } from '../components/invoices/CompactDragDropZone'
import { ManualInvoiceOrDNModal } from '../components/invoices/ManualInvoiceOrDNModal'
import { LinkDeliveryNoteModal } from '../components/invoices/LinkDeliveryNoteModal'
import { DeliveryNoteDetailModal } from '../components/invoices/DeliveryNoteDetailModal'
import { OCRDetailsModal } from '../components/invoices/OCRDetailsModal'
import { SupplierDetailModal } from '../components/invoices/SupplierDetailModal'
import { uploadFile, type InvoiceMetadata } from '../lib/upload'
import { UploadProgressBar } from '../components/invoices/UploadProgressBar'
import { API_BASE_URL } from '../lib/config'
import {
  normalizeInvoice,
  markInvoiceReviewed,
  escalateToSupplier,
  saveInvoiceNote,
  fetchInvoicePDF,
  fetchDeliveryNoteDetails,
  submitInvoices,
  retryOCR,
  deleteInvoices,
  fetchPairingSuggestions,
  fetchUnpairedDeliveryNotes,
  linkDeliveryNoteToInvoice,
  fetchRecentDocuments,
  type PairingSuggestion,
} from '../lib/api'
import './InvoicesNew.css'

import { ToastContainer, useToast } from '../components/common/Toast'

function InvoicesContent() {
  const toast = useToast()
  // Removed console.log to prevent log spam - only log on actual state changes
  
  // Removed viewMode - unified list
  const [venue, setVenue] = useState('Waterloo')
  const [dateRange, setDateRange] = useState<DateRange>('month')
  const [searchQuery, setSearchQuery] = useState('')
  const [sortBy, setSortBy] = useState<'date' | 'supplier' | 'value' | 'venue' | 'status'>('date')
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [invoices, setInvoices] = useState<InvoiceListItem[]>([])
  const [selectedInvoice, setSelectedInvoice] = useState<InvoiceDetail | null>(null)
  const [loading, setLoading] = useState(false) // Start as false, set to true when fetching
  const [error, setError] = useState<string | null>(null)
  const [uploadingFiles, setUploadingFiles] = useState<Set<string>>(new Set())
  const [uploadProgress, setUploadProgress] = useState<Map<string, number>>(new Map())
  const [processingFiles, setProcessingFiles] = useState<Set<string>>(new Set())
  const [newlyUploadedIds, setNewlyUploadedIds] = useState<Set<string>>(new Set())
  
  // New upload queue and staging state
  const [uploadStages, setUploadStages] = useState<Map<string, 'uploading' | 'processing' | 'waiting-for-card' | 'complete'>>(new Map())
  const [uploadQueue, setUploadQueue] = useState<string[]>([])
  const [activeUploads, setActiveUploads] = useState<Set<string>>(new Set())
  const [stagedProgress, setStagedProgress] = useState<Map<string, number>>(new Map())
  const [uploadMetadata, setUploadMetadata] = useState<Map<string, { id: string, fileName: string, raw?: any, error?: string }>>(new Map())
  const animationRefs = useRef<Map<string, number>>(new Map())
  const fileObjectsRef = useRef<Map<string, File>>(new Map())
  
  const fileInputRef = useRef<HTMLInputElement>(null)

  // Modal states
  const [showManualInvoiceOrDNModal, setShowManualInvoiceOrDNModal] = useState(false)
  const [showLinkDNModal, setShowLinkDNModal] = useState(false)
  const [showDNDetailModal, setShowDNDetailModal] = useState(false)
  const [showOCRModal, setShowOCRModal] = useState(false)
  const [showSupplierModal, setShowSupplierModal] = useState(false)
  const [editingInvoiceId, setEditingInvoiceId] = useState<string | null>(null)
  const [editingDNId, setEditingDNId] = useState<string | null>(null)
  const [editMode, setEditMode] = useState<'invoice' | 'delivery-note' | null>(null)
  const [selectedDNId, setSelectedDNId] = useState<string | null>(null)
  const [selectedSupplierName, setSelectedSupplierName] = useState<string | null>(null)
  const [pairingMode, setPairingMode] = useState<'automatic' | 'manual'>('manual')
  const [discrepancyRefreshTrigger, setDiscrepancyRefreshTrigger] = useState(0)
  const [highlightContext, setHighlightContext] = useState<DiscrepancyContext | null>(null)
  const [discrepancies, setDiscrepancies] = useState<DiscrepancyItem[]>([])
  const [discrepanciesLastUpdated, setDiscrepanciesLastUpdated] = useState<string | null>(null)
  
  // Track active polling for documents
  const pollingRefs = useRef<Map<string, NodeJS.Timeout>>(new Map())

  // Manual pairing workflow state
  const [manualPairingWorkflowActive, setManualPairingWorkflowActive] = useState(false)
  const [activePairingInvoiceId, setActivePairingInvoiceId] = useState<string | null>(null)
  const [pairingSuggestions, setPairingSuggestions] = useState<PairingSuggestion[]>([])
  const [unpairedDeliveryNotes, setUnpairedDeliveryNotes] = useState<any[]>([])
  const [loadingPairingData, setLoadingPairingData] = useState(false)
  const [pairingError, setPairingError] = useState<string | null>(null)
  const [pairingInProgress, setPairingInProgress] = useState<string | null>(null)

  // Note state
  const [noteText, setNoteText] = useState('')
  const [savingNote, setSavingNote] = useState(false)

  // Submit state
  const [isSubmitting, setIsSubmitting] = useState(false)

  // Fetch invoices from backend with timeout
  // Fetch invoices from both endpoints in parallel and merge
  // Memoized with useCallback to prevent infinite loops in useEffect dependencies
  const fetchInvoices = useCallback(async () => {
    console.log('[Invoices] fetchInvoices called', { sortBy, API_BASE_URL })
    setLoading(true)
    setError(null)
    
    const controller = new AbortController()
    const timeoutId = setTimeout(() => controller.abort(), 8000) // 8 second timeout
    
    try {
      const params = new URLSearchParams()
      params.append('sort', sortBy)
      params.append('limit', '100')

      // Fetch invoices and documents in parallel
      const scannedUrl = `${API_BASE_URL}/api/invoices?${params.toString()}`
      const manualUrl = `${API_BASE_URL}/api/manual/invoices?${params.toString()}`
      console.log('[Invoices] Fetching invoices and documents from:', { scannedUrl, manualUrl })
      
      console.log('[Invoices] 🔵 Starting Promise.all for invoices + documents fetch...')
      const [scannedResponse, manualResponse, documentsResponse] = await Promise.all([
        fetch(scannedUrl, {
          signal: controller.signal,
        }).catch(() => ({ ok: false, json: async () => ({ invoices: [] }) })),
        fetch(manualUrl, {
          signal: controller.signal,
        }).catch(() => ({ ok: false, json: async () => ({ invoices: [] }) })),
        fetchRecentDocuments(100, 0).catch((err) => {
          console.warn('[Invoices] ❌ fetchRecentDocuments failed:', err)
          return { documents: [], count: 0, total: 0, limit: 100, offset: 0 }
        }),
      ])
      console.log('[Invoices] 🟢 Promise.all completed, documentsResponse type:', typeof documentsResponse, 'hasDocuments:', documentsResponse?.documents?.length || 0)
      
      clearTimeout(timeoutId)
      
      // Log documents response immediately after Promise.all
      console.log('[Invoices] 📦📦📦 Raw documentsResponse from Promise.all:', {
        type: typeof documentsResponse,
        isNull: documentsResponse === null,
        isUndefined: documentsResponse === undefined,
        hasDocuments: documentsResponse?.documents ? documentsResponse.documents.length : 'no documents property',
        keys: documentsResponse && typeof documentsResponse === 'object' ? Object.keys(documentsResponse) : 'N/A',
        fullResponse: documentsResponse
      })
      
      console.log('[Invoices] API responses:', {
        scannedStatus: scannedResponse.ok ? scannedResponse.status : 'failed',
        manualStatus: manualResponse.ok ? manualResponse.status : 'failed'
      })
      
      // Process scanned invoices using normalizeInvoice()
      const scannedData = scannedResponse.ok ? await scannedResponse.json() : { invoices: [] }
      console.log('[Invoices] Scanned invoices raw response:', {
        responseSize: JSON.stringify(scannedData).length,
        invoiceCount: scannedData.invoices?.length || 0,
        firstInvoice: scannedData.invoices?.[0] ? {
          id: scannedData.invoices[0].id,
          supplier: scannedData.invoices[0].supplier || scannedData.invoices[0].supplier_name,
          total: scannedData.invoices[0].total_value || scannedData.invoices[0].total_amount,
          status: scannedData.invoices[0].status,
          lineItemsCount: scannedData.invoices[0].line_items?.length || 0
        } : null
      })
      const scannedList: InvoiceListItem[] = (scannedData.invoices || []).map((rawInv: any) => {
        const inv = normalizeInvoice(rawInv)
        // Add UI-specific fields to canonical Invoice
        return {
          ...inv,
          // Keep original id (may be UUID string or number) - don't force to number
          id: inv.id || inv.docId || 0,
          status: 'scanned' as const, // UI status override
          dbStatus: rawInv.status || inv.status, // Preserve database status for needs_review badge
          matched: inv.paired || false,
          flagged: (inv.issuesCount && inv.issuesCount > 0) || false,
          pending: inv.status === 'pending',
          hasDeliveryNote: !!inv.deliveryNoteId,
          readyToSubmit: inv.status === 'ready',
        }
      })

      // Process manual invoices using normalizeInvoice()
      const manualData = manualResponse.ok ? await manualResponse.json() : { invoices: [] }
      const manualList: InvoiceListItem[] = (manualData.invoices || []).map((rawInv: any) => {
        const inv = normalizeInvoice(rawInv)
        // Add UI-specific fields to canonical Invoice
        return {
          ...inv,
          // Keep original id (may be UUID string or number) - don't force to number
          id: inv.id || inv.docId || 0,
          status: 'manual' as const, // UI status override
          dbStatus: rawInv.status || inv.status, // Preserve database status for needs_review badge
          matched: inv.paired || false,
          flagged: (inv.issuesCount && inv.issuesCount > 0) || false,
          pending: inv.status === 'pending',
          hasDeliveryNote: !!inv.deliveryNoteId,
          readyToSubmit: inv.status === 'ready',
        }
      })

      // Process documents (convert to InvoiceListItem format)
      // fetchRecentDocuments returns { documents: [], count: 0, total: 0, ... }
      console.log('[Invoices] Processing documents response:', { 
        responseType: typeof documentsResponse, 
        isNull: documentsResponse === null,
        isUndefined: documentsResponse === undefined,
        responseKeys: documentsResponse && typeof documentsResponse === 'object' ? Object.keys(documentsResponse) : 'N/A'
      })
      
      let documentsData: any
      try {
        if (typeof documentsResponse === 'object' && documentsResponse !== null) {
          if ('documents' in documentsResponse) {
            documentsData = documentsResponse
          } else if (Array.isArray(documentsResponse)) {
            documentsData = { documents: documentsResponse }
          } else {
            documentsData = { documents: [] }
          }
        } else {
          documentsData = { documents: [] }
        }
      } catch (e) {
        console.warn('[Invoices] Failed to parse documents response:', e)
        documentsData = { documents: [] }
      }
      
      const documentsCount = documentsData?.documents ? documentsData.documents.length : 0
      console.log('[Invoices] 📄 Documents response:', {
        type: typeof documentsResponse,
        isArray: Array.isArray(documentsResponse),
        hasDocuments: documentsCount,
        allDocIds: documentsData?.documents?.map((d: any) => d.doc_id) || [],
        errorDocIds: documentsData?.documents?.filter((d: any) => d.status === 'error').map((d: any) => d.doc_id) || [],
        sample: documentsData?.documents?.[0] ? {
          doc_id: documentsData.documents[0].doc_id,
          status: documentsData.documents[0].status,
          has_invoice_row: documentsData.documents[0].has_invoice_row,
          filename: documentsData.documents[0].filename
        } : null
      })
      
      if (documentsCount === 0) {
        console.warn('[Invoices] ⚠️ No documents returned from fetchRecentDocuments - this might be why error cards are missing!')
      }
      
      const documentList: InvoiceListItem[] = (documentsData.documents || []).map((doc: any) => {
        // Convert document to InvoiceListItem
        const card: InvoiceListItem = {
          id: doc.has_invoice_row && doc.invoice ? (doc.invoice.invoice_id || doc.doc_id) : doc.doc_id,
          docId: doc.doc_id,
          doc_id: doc.doc_id,
          has_invoice_row: doc.has_invoice_row,
          supplier: doc.invoice?.supplier || 'Unknown Supplier',
          invoiceDate: doc.invoice?.date || doc.uploaded_at || '',
          totalValue: doc.invoice?.total || 0,
          currency: 'GBP',
          confidence: doc.confidence || doc.invoice?.confidence || null,
          status: doc.status === 'ready' ? 'ready' : 
                  doc.status === 'error' ? 'error' : 
                  doc.status === 'needs_review' ? 'needs_review' :
                  doc.status === 'processing' ? 'processing' : 'scanned',
          dbStatus: doc.status,
          venue: null,
          issuesCount: 0,
          paired: false,
          pairingStatus: null,
          deliveryNoteId: null,
          lineItems: [],
          // Document-specific fields
          error_code: doc.error_code,
          ocr_attempts: doc.ocr_attempts,
          filename: doc.filename,
          uploaded_at: doc.uploaded_at,
          doc_type: doc.doc_type,
          doc_type_confidence: doc.doc_type_confidence,
          ocr_error: doc.ocr_error,
          matched: false,
          flagged: false,
          pending: doc.status === 'processing',
          hasDeliveryNote: false,
          readyToSubmit: doc.status === 'ready' && doc.has_invoice_row,
        }
        return card
      })
      
      // Merge invoices and documents
      const merged = [...scannedList, ...manualList, ...documentList]
      
      // Deduplicate by doc_id or id - prefer invoice cards over document cards
      // BUT: Always keep error/needs_review documents even if they don't have invoice rows
      // Use string keys to handle both UUID strings and numeric IDs
      const cardMap = new Map<string | number, InvoiceListItem>()
      for (const card of merged) {
        // Use doc_id as primary key, fallback to id
        const cardKey = card.doc_id || card.docId || card.id || 0
        const existing = cardMap.get(cardKey)
        
        // Prefer cards with invoice data over document-only cards
        // Prefer manual over scanned
        // BUT: Always keep error/needs_review documents
        if (!existing) {
          cardMap.set(cardKey, card)
        } else if (card.status === 'error' || card.status === 'needs_review') {
          // Always keep error/needs_review documents - they're important for visibility
          if (existing.status !== 'error' && existing.status !== 'needs_review') {
            // Replace non-error with error/needs_review
            cardMap.set(cardKey, card)
          } else if (card.has_invoice_row && !existing.has_invoice_row) {
            // Both are error/needs_review, prefer one with invoice data
            cardMap.set(cardKey, card)
          }
          // Otherwise keep existing error/needs_review card
        } else if (card.has_invoice_row && !existing.has_invoice_row) {
          // Card has invoice data, existing doesn't - replace
          cardMap.set(cardKey, card)
        } else if (card.status === 'manual' && existing.status !== 'manual') {
          // Prefer manual over scanned
          cardMap.set(cardKey, card)
        } else if (card.has_invoice_row === existing.has_invoice_row && 
                   card.status === existing.status &&
                   !existing.doc_id && card.doc_id) {
          // Same type, but new one has doc_id - prefer it
          cardMap.set(cardKey, card)
        }
      }
      const deduplicated = Array.from(cardMap.values())
      
      // Log final deduplicated list to verify error cards are included
      const errorCards = deduplicated.filter(c => c.status === 'error' || c.dbStatus === 'error')
      const needsReviewCards = deduplicated.filter(c => c.status === 'needs_review' || c.dbStatus === 'needs_review')
      if (errorCards.length > 0 || needsReviewCards.length > 0) {
        console.log('[Invoices] ✅ Error/needs_review cards in final list:', {
          errorCount: errorCards.length,
          needsReviewCount: needsReviewCards.length,
          errorDocIds: errorCards.map(c => c.doc_id),
          needsReviewDocIds: needsReviewCards.map(c => c.doc_id)
        })
      }
      
      // Sort based on sortBy option (stable sort)
      deduplicated.sort((a, b) => {
        switch (sortBy) {
          case 'date':
            const dateA = a.invoiceDate ? new Date(a.invoiceDate).getTime() : 0
            const dateB = b.invoiceDate ? new Date(b.invoiceDate).getTime() : 0
            return dateB - dateA // Most recent first
          case 'supplier':
            return (a.supplier || '').localeCompare(b.supplier || '')
          case 'value':
            return (b.totalValue || 0) - (a.totalValue || 0) // Highest first
          case 'venue':
            return (a.venue || '').localeCompare(b.venue || '')
          case 'status':
            // Sort by: matched > unmatched, then ready > draft
            if (a.matched !== b.matched) {
              return a.matched ? -1 : 1
            }
            const aReady = a.readyToSubmit || false
            const bReady = b.readyToSubmit || false
            if (aReady !== bReady) {
              return aReady ? -1 : 1
            }
            return 0
          default:
            return 0
        }
      })

      console.log('[Invoices] Merged invoice list:', { 
        count: deduplicated.length, 
        scanned: scannedList.length, 
        manual: manualList.length,
        documents: documentList.length,
        duplicatesRemoved: merged.length - deduplicated.length,
        documentDocIds: documentList.map(d => d.doc_id).slice(0, 5),
        invoices: deduplicated.map(inv => ({
          id: inv.id,
          supplier: inv.supplier,
          total: inv.totalValue,
          status: inv.status,
          dbStatus: inv.dbStatus,
          lineItemsCount: inv.lineItems?.length || 0,
          hasData: !!(inv.supplier && inv.supplier !== 'Unknown Supplier' && (inv.totalValue || 0) > 0)
        }))
      })
      
      // Log any invoices that might be filtered out
      const emptyInvoices = deduplicated.filter(inv => 
        (!inv.supplier || inv.supplier === 'Unknown Supplier') && 
        (!inv.totalValue || inv.totalValue === 0) && 
        (!inv.lineItems || inv.lineItems.length === 0)
      )
      if (emptyInvoices.length > 0) {
        console.warn('[Invoices] Found invoices with empty data (may be filtered):', emptyInvoices.map(inv => ({
          id: inv.id,
          supplier: inv.supplier,
          total: inv.totalValue,
          status: inv.status,
          dbStatus: inv.dbStatus
        })))
      }
      
      // Merge with existing invoices to preserve immediately-created error/processing cards
      // that might not be in the fetched list yet
      setInvoices((prev) => {
        // Create a map of existing cards by doc_id
        const existingMap = new Map<string | number, InvoiceListItem>()
        prev.forEach(card => {
          const key = card.doc_id || card.docId || card.id || 0
          existingMap.set(key, card)
        })
        
        // Create a map of fetched cards by doc_id
        const fetchedMap = new Map<string | number, InvoiceListItem>()
        deduplicated.forEach(card => {
          const key = card.doc_id || card.docId || card.id || 0
          fetchedMap.set(key, card)
        })
        
        // Merge: prefer fetched cards, but keep existing error/processing cards that aren't in fetched
        const merged = new Map<string | number, InvoiceListItem>()
        
        // Add all fetched cards
        fetchedMap.forEach((card, key) => {
          merged.set(key, card)
        })
        
        // Add existing cards that aren't in fetched (especially error/processing cards)
        existingMap.forEach((card, key) => {
          if (!merged.has(key)) {
            // Keep existing card if it's error/processing/needs_review
            if (card.status === 'error' || card.status === 'processing' || card.status === 'needs_review' || 
                card.dbStatus === 'error' || card.dbStatus === 'processing' || card.dbStatus === 'needs_review') {
              merged.set(key, card)
            }
          }
        })
        
        return Array.from(merged.values())
      })
      setError(null)
    } catch (err) {
      clearTimeout(timeoutId)
      if (err instanceof Error && err.name === 'AbortError') {
        const errorMsg = 'Unable to connect to the server. The backend may not be running or the API endpoint is unavailable.'
        setError(errorMsg)
        console.error('[Invoices] API request timed out')
      } else {
        const errorMsg = err instanceof Error ? err.message : 'Failed to load invoices'
        setError(errorMsg)
        console.error('[Invoices] Error fetching invoices:', err)
      }
      setInvoices([])
    } finally {
      setLoading(false)
      console.log('[Invoices] fetchInvoices completed')
    }
  }, [sortBy]) // Only depend on sortBy, not invoices state

  // Poll document status to update cards as processing progresses
  const pollDocumentStatus = useCallback(async (docId: string) => {
    // Check if already polling this doc
    if (pollingRefs.current.has(docId)) {
      console.log(`[POLL] Already polling doc_id=${docId}, skipping`)
      return
    }
    
    const maxPolls = 60 // 2 minutes max (60 * 2 seconds)
    let pollCount = 0
    
    const poll = async () => {
      if (pollCount >= maxPolls) {
        // Timeout - mark as error
        console.warn(`[POLL] Timeout after ${maxPolls} attempts for doc_id=${docId}`)
        setInvoices((prev) => prev.map(card => 
          (card.doc_id === docId || card.docId === docId) 
            ? { ...card, status: 'error' as const, dbStatus: 'error', error_code: 'TIMEOUT', ocr_error: 'Processing timeout' }
            : card
        ))
        pollingRefs.current.delete(docId)
        return
      }
      
      try {
        const response = await fetch(`${API_BASE_URL}/api/upload/status?doc_id=${docId}`)
        if (!response.ok) {
          pollCount++
          const timeoutId = setTimeout(poll, 2000)
          pollingRefs.current.set(docId, timeoutId)
          return
        }
        
        const data = await response.json()
        
        // Update card with status data
        setInvoices((prev) => prev.map(card => {
          if (card.doc_id === docId || card.docId === docId) {
            const updated: InvoiceListItem = {
              ...card,
              status: data.status === 'ready' ? 'ready' as const :
                      data.status === 'error' ? 'error' as const :
                      data.status === 'needs_review' ? 'needs_review' as const :
                      data.status === 'processing' ? 'processing' as const :
                      card.status,
              dbStatus: data.status,
              confidence: data.confidence || card.confidence,
              error_code: data.error_code || card.error_code,
              ocr_error: data.error || card.ocr_error,
              ocr_attempts: data.ocr_attempts || card.ocr_attempts,
            }
            
            // If invoice data is available, hydrate the card
            if (data.parsed || data.invoice) {
              const invoiceData = data.invoice || data.parsed
              updated.has_invoice_row = true
              updated.supplier = invoiceData.supplier || updated.supplier
              updated.invoiceDate = invoiceData.invoice_date || invoiceData.date || updated.invoiceDate
              updated.totalValue = invoiceData.total_value || invoiceData.total || invoiceData.value || updated.totalValue
              updated.confidence = invoiceData.confidence || updated.confidence
            }
            
            // If line items are available, add them
            if (data.items && Array.isArray(data.items) && data.items.length > 0) {
              updated.lineItems = data.items.map((item: any) => ({
                description: item.description || item.desc || '',
                qty: item.qty || item.quantity || 0,
                unitPrice: item.unit_price || item.price || 0,
                total: item.total || item.line_total || 0,
                uom: item.uom || item.unit || '',
                confidence: item.confidence || null,
              }))
            }
            
            return updated
          }
          return card
        }))
        
        // Stop polling if final state reached
        if (['ready', 'error', 'needs_review'].includes(data.status)) {
          console.log(`[POLL] Final state reached for doc_id=${docId}: ${data.status}`)
          const timeoutId = pollingRefs.current.get(docId)
          if (timeoutId) {
            clearTimeout(timeoutId)
          }
          pollingRefs.current.delete(docId)
          return
        }
        
        pollCount++
        const timeoutId = setTimeout(poll, 2000) // Poll every 2 seconds
        pollingRefs.current.set(docId, timeoutId)
      } catch (error) {
        console.warn(`[POLL] Poll attempt ${pollCount + 1} failed for doc_id=${docId}:`, error)
        pollCount++
        const timeoutId = setTimeout(poll, 2000)
        pollingRefs.current.set(docId, timeoutId)
      }
    }
    
    // Mark as active and start polling
    pollingRefs.current.set(docId, setTimeout(() => {}, 0)) // Placeholder
    poll()
  }, [])

  // Fetch single invoice details - try both endpoints
  const fetchInvoiceDetail = useCallback(async (id: string) => {
    try {
      // Try scanned endpoint first, then manual
      let response = await fetch(`${API_BASE_URL}/api/invoices/${id}`)
      let isManual = false
      
      if (!response.ok) {
        // Try manual endpoint
        response = await fetch(`${API_BASE_URL}/api/manual/invoices/${id}`)
        isManual = true
      }
      
      if (!response.ok) {
        throw new Error(`Failed to fetch invoice: ${response.status}`)
      }

      const data = await response.json()
      console.log('[Invoices] Raw invoice detail response:', data)
      // Use normalizeInvoice() for canonical invoice structure
      const rawInvoice = data.invoice || data
      const inv = normalizeInvoice(rawInvoice)
      console.log('[Invoices] Normalized invoice detail:', inv)

      // Determine if invoice is manual by checking:
      // 1. If we got it from manual endpoint (isManual flag)
      // 2. If confidence is 1.0 and status is 'ready' (indicators of manual invoice)
      // 3. If source field indicates manual
      const confidence = inv.confidence || 0
      const invoiceStatus = inv.status || rawInvoice.status
      const source = rawInvoice.source
      const ocrStage = rawInvoice.ocr_stage || rawInvoice.ocrStage
      const isActuallyManual = isManual || 
                               (confidence === 1.0 && invoiceStatus === 'ready') ||
                               source === 'manual' ||
                               ocrStage === 'manual'

      // Create invoice detail first without delivery note (non-blocking)
      const invoiceDetail: InvoiceDetail = {
        id: String(inv.id || inv.docId),
        docId: inv.docId || String(inv.id || inv.docId), // doc_id for image serving
        invoiceNumber: inv.invoiceNumber,
        supplier: inv.supplier || 'Unknown Supplier',
        date: inv.invoiceDate,
        venue: inv.venue || 'Main Restaurant',
        value: inv.totalValue || 0,
        subtotal: inv.subtotal,
        vat: inv.vat,
        status: isActuallyManual ? 'manual' : 'scanned',
        matched: inv.paired || false,
        flagged: (inv.issuesCount && inv.issuesCount > 0) || false,
        deliveryNote: undefined, // Will be populated async
        lineItems: inv.lineItems || [],
        confidence: inv.confidence || null,
      }
      console.log('[Invoices] Created invoice detail:', invoiceDetail)

      // Set invoice detail immediately so UI renders
      setSelectedInvoice(invoiceDetail)

      // Fetch delivery note if linked (async, non-blocking)
      if (inv.deliveryNoteId) {
        const dnId = String(inv.deliveryNoteId)
        
        // Check if dnId looks like a note number (e.g., "dn-001") instead of a database ID
        // Database IDs are typically UUIDs or numeric strings, not prefixed with "dn-"
        const looksLikeNoteNumber = /^dn-?\d+/i.test(dnId.trim())
        
        if (looksLikeNoteNumber) {
          // If it looks like a note number, just use it as the note number and skip fetching
          console.warn(`Delivery note ID appears to be a note number (${dnId}), not a database ID. Skipping fetch.`)
          const basicDeliveryNote: DeliveryNoteInfo = {
            id: dnId, // Use the note number as ID for now
            noteNumber: dnId,
          }
          setSelectedInvoice({ ...invoiceDetail, deliveryNote: basicDeliveryNote })
        } else {
          // Set basic delivery note info immediately
          const basicDeliveryNote: DeliveryNoteInfo = {
            id: dnId,
            noteNumber: `DN-${dnId.slice(0, 8)}`,
          }
          setSelectedInvoice({ ...invoiceDetail, deliveryNote: basicDeliveryNote })

          // Fetch full delivery note details in background (non-blocking)
          fetchDeliveryNoteDetails(dnId)
            .then((dnDetails) => {
              // Check if dnDetails is null (404 or not found)
              if (!dnDetails) {
                console.warn(`Delivery note ${dnId} not found - using basic info only`)
                return
              }
              
              const fullDeliveryNote: DeliveryNoteInfo = {
                id: dnId,
                noteNumber: dnDetails.noteNumber || dnDetails.deliveryNoteNumber || dnDetails.delivery_no || dnDetails.note_number || `DN-${dnId.slice(0, 8)}`,
                date: dnDetails.date || dnDetails.deliveryDate || dnDetails.delivery_date,
                driver: dnDetails.driver,
                vehicle: dnDetails.vehicle,
                timeWindow: dnDetails.timeWindow,
              }
              // Add lineItems to deliveryNote for InvoiceDetail
              if (dnDetails.lineItems || dnDetails.line_items) {
                ;(fullDeliveryNote as any).lineItems = dnDetails.lineItems || dnDetails.line_items
              }
              // Update invoice detail with full delivery note info
              setSelectedInvoice((prev) => {
                if (prev && prev.id === invoiceDetail.id) {
                  return { ...prev, deliveryNote: fullDeliveryNote }
                }
                return prev
              })
            })
            .catch((err) => {
              // Silently fail - basic info already set
              console.warn('Failed to fetch delivery note details:', err)
            })
        }
      }
    } catch (err) {
      console.error('Error fetching invoice detail:', err)
      setSelectedInvoice(null)
    }
  }, [])

  // Check backend health on mount
  useEffect(() => {
    const checkBackendHealth = async () => {
      try {
        const healthUrl = `${API_BASE_URL}/api/health`
        console.log('[Invoices] Checking backend health at:', healthUrl)
        
        // Use a shorter timeout and better error handling
        const controller = new AbortController()
        const timeoutId = setTimeout(() => controller.abort(), 2000) // 2 second timeout
        
        try {
          const response = await fetch(healthUrl, { 
            signal: controller.signal,
            cache: 'no-cache',
            headers: {
              'Cache-Control': 'no-cache'
            }
          })
          clearTimeout(timeoutId)
          
          if (response.ok) {
            const health = await response.json()
            console.log('[Invoices] Backend health check passed:', health)
          } else {
            console.warn('[Invoices] Backend health check failed:', response.status, response.statusText)
          }
        } catch (fetchErr: any) {
          clearTimeout(timeoutId)
          if (fetchErr.name === 'AbortError') {
            console.warn('[Invoices] Backend health check timed out - backend may not be running or is slow to respond')
          } else {
            throw fetchErr
          }
        }
      } catch (err: any) {
        // Only log error details, don't spam console with instructions
        if (err.name !== 'AbortError') {
          console.warn('[Invoices] Backend health check error:', err.message || err)
          console.info('[Invoices] Tip: Make sure the backend is running. In dev mode, check Vite proxy config.')
        }
      }
    }
    checkBackendHealth()
  }, [])

  // Load invoices on mount and when filters change
  useEffect(() => {
    console.log('[Invoices] useEffect triggered', { sortBy })
    let mounted = true
    // Fetch immediately on mount
    fetchInvoices().catch((err) => {
      // Error already handled in fetchInvoices
      console.error('[Invoices] useEffect fetchInvoices error:', err)
      if (!mounted) return
    })
    return () => {
      console.log('[Invoices] useEffect cleanup')
      mounted = false
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sortBy]) // Use direct dependencies instead of callback to prevent infinite loops

  // Fetch detail when selection changes
  useEffect(() => {
    if (selectedId) {
      fetchInvoiceDetail(selectedId)
    } else {
      setSelectedInvoice(null)
    }
  }, [selectedId, fetchInvoiceDetail])

  // Build discrepancies - always show page-level, add invoice-level if selected
  useEffect(() => {
    const now = new Date().toISOString()
    let items: DiscrepancyItem[] = []
    
    // Always include page-level discrepancies
    items = [
      ...buildInvoiceListDiscrepancies(invoices),
    ]
    
    // Add invoice-level discrepancies if an invoice is selected
    if (selectedInvoice) {
      items = [
        ...items,
        ...buildInvoiceDetailDiscrepancies(selectedInvoice)
      ]
    }
    
    setDiscrepancies(items)
    setDiscrepanciesLastUpdated(now)
  }, [selectedInvoice, invoices])

  // Easing function for smooth animations
  const easeInOutCubic = (t: number): number => {
    return t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2
  }

  // Animate progress smoothly between two values
  const animateProgress = useCallback((
    fileId: string,
    from: number,
    to: number,
    duration: number
  ) => {
    // Cancel any existing animation for this file
    const existingFrame = animationRefs.current.get(fileId)
    if (existingFrame) {
      cancelAnimationFrame(existingFrame)
    }

    const startTime = Date.now()
    const startValue = from

    const animate = () => {
      const elapsed = Date.now() - startTime
      const progress = Math.min(elapsed / duration, 1)
      const eased = easeInOutCubic(progress)
      const current = startValue + (to - startValue) * eased

      setStagedProgress((prev) => {
        const newMap = new Map(prev)
        newMap.set(fileId, current)
        return newMap
      })

      if (progress < 1) {
        const frameId = requestAnimationFrame(animate)
        animationRefs.current.set(fileId, frameId)
      } else {
        animationRefs.current.delete(fileId)
      }
    }

    const frameId = requestAnimationFrame(animate)
    animationRefs.current.set(fileId, frameId)
  }, [])

  // Use ref to break circular dependency between startUpload and processUploadQueue
  const processUploadQueueRef = useRef<(() => void) | null>(null)

  // Start upload for a specific file
  const startUpload = useCallback(async (fileId: string, file: File) => {
    console.log(`[UPLOAD] Starting upload for file: ${file.name} (${(file.size / 1024).toFixed(1)}KB)`)
    
    // Set initial stage and progress
    setUploadStages((prev) => {
      const newMap = new Map(prev)
      newMap.set(fileId, 'uploading')
      return newMap
    })
    setStagedProgress((prev) => new Map(prev).set(fileId, 0))
    setUploadingFiles((prev) => new Set(prev).add(fileId))

    // Track if onComplete was called to handle timeout cases
    let onCompleteCalled = false
    let uploadMetadataId: string | undefined = undefined

    try {
      const result = await uploadFile(file, {
        onProgress: (progress) => {
          // Use real upload progress to provide feedback during actual upload
          // Map 0-100% upload progress to 0-20% of total progress (upload phase)
          const uploadPhaseProgress = Math.min(20, Math.round(progress.percentage * 0.2))
          console.log(`[UPLOAD] onProgress: ${progress.percentage}% upload → ${uploadPhaseProgress}% staged (fileId: ${fileId})`)
          setStagedProgress((prev) => {
            const newMap = new Map(prev)
            newMap.set(fileId, uploadPhaseProgress)
            return newMap
          })
        },
        onComplete: async (metadata) => {
          onCompleteCalled = true
          console.log(`[UPLOAD] onComplete called for ${file.name} (fileId: ${fileId})`)
          console.log(`[UPLOAD] Metadata:`, { id: metadata.id, status: metadata.raw?.status, hasItems: !!metadata.lineItems?.length })
          
          // Store metadata for card detection (include raw status for error detection)
          if (metadata.id) {
            uploadMetadataId = String(metadata.id)
            console.log(`[UPLOAD] Storing metadata: fileId=${fileId}, docId=${uploadMetadataId}, status=${metadata.raw?.status}, error=${metadata.error || metadata.raw?.error || 'none'}`)
            setUploadMetadata((prev) => {
              const newMap = new Map(prev)
              newMap.set(fileId, { 
                id: uploadMetadataId, 
                fileName: file.name,
                raw: metadata.raw, // Store raw status for error detection
                error: metadata.error || metadata.raw?.error // Store error message if present
              })
              return newMap
            })
            
            // IMMEDIATELY create a card for this document
            const docId = uploadMetadataId
            const isError = metadata.status === 'error' || metadata.raw?.status === 'error'
            const cardStatus = isError ? 'error' : (metadata.status === 'ready' ? 'ready' : 'processing')
            const dbStatus = isError ? 'error' : (metadata.status === 'ready' ? 'ready' : 'processing')
            
            console.log(`[UPLOAD] 🎯 Creating card: docId=${docId}, isError=${isError}, cardStatus=${cardStatus}, metadata.status=${metadata.status}, metadata.raw?.status=${metadata.raw?.status}`)
            
            const newCard: InvoiceListItem = {
              id: docId,
              docId: docId,
              doc_id: docId,
              has_invoice_row: false,
              supplier: 'Unknown Supplier',
              invoiceDate: new Date().toISOString().split('T')[0],
              totalValue: 0,
              currency: 'GBP',
              confidence: null,
              status: cardStatus,
              dbStatus: dbStatus,
              venue: null,
              issuesCount: 0,
              paired: false,
              pairingStatus: null,
              deliveryNoteId: null,
              lineItems: [],
              filename: file.name,
              uploaded_at: new Date().toISOString(),
              matched: false,
              flagged: false,
              pending: !isError && cardStatus === 'processing',
              hasDeliveryNote: false,
              readyToSubmit: false,
              ocr_error: isError ? (metadata.error || metadata.raw?.error || 'OCR processing failed') : undefined,
              error_code: isError ? (metadata.raw?.error_code || null) : undefined,
            }
            
            // Add card to invoices list immediately
            setInvoices((prev) => {
              // Check if card already exists
              const exists = prev.some(card => card.doc_id === docId || card.docId === docId)
              if (exists) {
                // Update existing card if status changed to error
                if (isError) {
                  console.log(`[UPLOAD] ✅ Updating existing card to error status for doc_id=${docId}`)
                  return prev.map(card => {
                    if (card.doc_id === docId || card.docId === docId) {
                      return {
                        ...card,
                        status: 'error',
                        dbStatus: 'error',
                        pending: false,
                        ocr_error: metadata.error || metadata.raw?.error || card.ocr_error,
                        error_code: metadata.raw?.error_code || card.error_code,
                      }
                    }
                    return card
                  })
                }
                return prev
              }
              // Add new card at the beginning (most recent first)
              console.log(`[UPLOAD] ✅ Created ${cardStatus} card for doc_id=${docId}, filename=${file.name}`)
              return [newCard, ...prev]
            })
            
            // Start polling for status updates
            pollDocumentStatus(docId)
          }

          // File uploaded successfully - ensure we're at 20%, then transition to 45%
          console.log(`[UPLOAD] Setting progress to 20% for fileId: ${fileId}`)
          setStagedProgress((prev) => {
            const newMap = new Map(prev)
            const current = newMap.get(fileId) || 0
            console.log(`[UPLOAD] Progress update: ${current}% → 20% (fileId: ${fileId})`)
            newMap.set(fileId, 20)
            return newMap
          })
          
          setTimeout(() => {
            console.log(`[UPLOAD] Animating progress 20% → 45% for fileId: ${fileId}`)
            animateProgress(fileId, 20, 45, 2000)
          }, 500)

          // Then transition to 90% and mark as processing
          setTimeout(() => {
            console.log(`[UPLOAD] Animating progress 45% → 90% and setting stage to 'waiting-for-card' for fileId: ${fileId}`)
            animateProgress(fileId, 45, 90, 1500)
            setUploadStages((prev) => {
              const newMap = new Map(prev)
              const oldStage = newMap.get(fileId)
              console.log(`[UPLOAD] Stage update: ${oldStage} → 'waiting-for-card' (fileId: ${fileId})`)
              newMap.set(fileId, 'waiting-for-card')
              return newMap
            })
            setProcessingFiles((prev) => new Set(prev).add(fileId))
          }, 2500)

          // Poll for OCR completion by refreshing invoices
          console.log(`[UPLOAD] Waiting for OCR to complete for doc_id: ${uploadMetadataId}...`)
          await fetchInvoices()

          // Mark as newly uploaded for animation
          if (metadata.id) {
            setNewlyUploadedIds((prev) => new Set(prev).add(String(metadata.id)))
            setTimeout(() => {
              setNewlyUploadedIds((prev) => {
                const newSet = new Set(prev)
                newSet.delete(String(metadata.id))
                return newSet
              })
            }, 1000)
          }
          
          // Note: Periodic refresh is handled by the useEffect hook that watches uploadStages
          // It will refresh invoices every 5 seconds while files are in 'waiting-for-card' state

          // Trigger discrepancy refresh
          setTimeout(() => {
            setDiscrepancyRefreshTrigger((prev) => prev + 1)
          }, 200)
        },
      })

      console.log(`[UPLOAD] Upload result for ${file.name}:`, { success: result.success, hasMetadata: !!result.metadata, error: result.error })

      // Handle upload result
      if (result.success && result.metadata) {
        // Store metadata immediately (in case onComplete doesn't fire)
        if (result.metadata.id) {
          uploadMetadataId = String(result.metadata.id)
          setUploadMetadata((prev) => {
            const newMap = new Map(prev)
            newMap.set(fileId, { id: uploadMetadataId, fileName: file.name })
            return newMap
          })
        }

        // If status is "processing", onComplete will be called after polling
        // But set up a timeout to handle cases where onComplete never fires
        console.log(`[UPLOAD] Upload result status: ${result.metadata.raw?.status}, onCompleteCalled: ${onCompleteCalled}`)
        if (result.metadata.raw?.status === 'processing' || result.metadata.raw?.status === 'duplicate') {
          // For duplicates, check if invoice already exists - if so, complete immediately
          if (result.metadata.raw?.status === 'duplicate' && uploadMetadataId) {
            const hasInvoice = result.metadata.raw?.has_invoice ?? false
            const docStatus = result.metadata.raw?.doc_status || result.metadata.raw?.status
            const isError = docStatus === 'error' || result.metadata.raw?.status === 'error'
            
            // Check invoice.docId to match the document (doc_id is stored in invoice.docId, not invoice.id)
            const invoiceExists = invoices.some((inv) => String(inv.docId || '') === uploadMetadataId)
            
            if (invoiceExists || hasInvoice) {
              // Invoice exists - complete immediately
              console.log(`[UPLOAD] Duplicate file - invoice already exists (matched by docId=${uploadMetadataId}), completing immediately`)
              setStagedProgress((prev) => {
                const newMap = new Map(prev)
                newMap.set(fileId, 100)
                return newMap
              })
              setUploadStages((prev) => {
                const newMap = new Map(prev)
                newMap.set(fileId, 'complete')
                return newMap
              })
              toast.success(`File already uploaded: ${file.name}`)
              
              // Clean up after showing completion
              setTimeout(() => {
                setActiveUploads((prev) => {
                  const newSet = new Set(prev)
                  newSet.delete(fileId)
                  return newSet
                })
                setStagedProgress((prev) => {
                  const newMap = new Map(prev)
                  newMap.delete(fileId)
                  return newMap
                })
                setUploadStages((prev) => {
                  const newMap = new Map(prev)
                  newMap.delete(fileId)
                  return newMap
                })
                if (processUploadQueueRef.current) {
                  processUploadQueueRef.current()
                }
              }, 2000)
              return // Exit early for duplicate that already exists
            } else if (isError) {
              // Duplicate document with error status and no invoice - show error state immediately
              console.log(`[UPLOAD] Duplicate document with error status (doc_id=${uploadMetadataId}) - showing error state immediately`)
              
              // IMMEDIATELY create a card for this error document
              const errorCard: InvoiceListItem = {
                id: uploadMetadataId,
                docId: uploadMetadataId,
                doc_id: uploadMetadataId,
                has_invoice_row: false,
                supplier: 'Unknown Supplier',
                invoiceDate: new Date().toISOString().split('T')[0],
                totalValue: 0,
                currency: 'GBP',
                confidence: null,
                status: 'error',
                dbStatus: 'error',
                venue: null,
                issuesCount: 0,
                paired: false,
                pairingStatus: null,
                deliveryNoteId: null,
                lineItems: [],
                filename: file.name,
                uploaded_at: new Date().toISOString(),
                matched: false,
                flagged: false,
                pending: false,
                hasDeliveryNote: false,
                readyToSubmit: false,
                ocr_error: result.metadata.raw?.error || 'OCR processing failed previously',
                error_code: result.metadata.raw?.error_code || null,
              }
              
              // Add card to invoices list immediately
              setInvoices((prev) => {
                const exists = prev.some(card => card.doc_id === uploadMetadataId || card.docId === uploadMetadataId)
                if (exists) {
                  console.log(`[UPLOAD] Error card already exists for doc_id=${uploadMetadataId}`)
                  return prev
                }
                console.log(`[UPLOAD] ✅ Created error card for doc_id=${uploadMetadataId}, filename=${file.name}, status=error`)
                console.log(`[UPLOAD] Error card details:`, { id: errorCard.id, doc_id: errorCard.doc_id, status: errorCard.status, ocr_error: errorCard.ocr_error })
                return [errorCard, ...prev]
              })
              
              // Fetch detailed error message from document status endpoint
              fetch(`${API_BASE_URL}/api/documents/${encodeURIComponent(uploadMetadataId)}/status`)
                .then((response) => {
                  if (response.ok) {
                    return response.json()
                  }
                  throw new Error(`Status check failed: ${response.status}`)
                })
                .then((docStatusData) => {
                  const errorMsg = docStatusData.error || result.metadata.raw?.error || 'OCR processing failed previously'
                  setUploadMetadata((prev) => {
                    const newMap = new Map(prev)
                    const existing = newMap.get(fileId) || {}
                    newMap.set(fileId, {
                      ...existing,
                      id: uploadMetadataId,
                      error: errorMsg,
                      raw: {
                        ...existing.raw,
                        ...result.metadata.raw,
                        status: 'error',
                        error: errorMsg
                      }
                    })
                    return newMap
                  })
                  
                  // Update the card with detailed error info
                  setInvoices((prev) => {
                    return prev.map(card => {
                      if (card.doc_id === uploadMetadataId || card.docId === uploadMetadataId) {
                        return {
                          ...card,
                          ocr_error: errorMsg,
                          error_code: docStatusData.error_code || card.error_code,
                          ocr_attempts: docStatusData.ocr_attempts || card.ocr_attempts,
                        }
                      }
                      return card
                    })
                  })
                })
                .catch((err) => {
                  console.warn(`[UPLOAD] Failed to fetch document status for error details:`, err)
                  // Fallback to basic error message
                  setUploadMetadata((prev) => {
                    const newMap = new Map(prev)
                    const existing = newMap.get(fileId) || {}
                    newMap.set(fileId, {
                      ...existing,
                      id: uploadMetadataId,
                      error: result.metadata.raw?.error || 'OCR processing failed previously',
                      raw: {
                        ...existing.raw,
                        ...result.metadata.raw,
                        status: 'error'
                      }
                    })
                    return newMap
                  })
                })
              
              // Set progress to 100% and mark as complete (error state)
              setStagedProgress((prev) => {
                const newMap = new Map(prev)
                newMap.set(fileId, 100)
                return newMap
              })
              setUploadStages((prev) => {
                const newMap = new Map(prev)
                newMap.set(fileId, 'complete')
                return newMap
              })
              
              // Clean up after showing error
              setTimeout(() => {
                setActiveUploads((prev) => {
                  const newSet = new Set(prev)
                  newSet.delete(fileId)
                  return newSet
                })
                setStagedProgress((prev) => {
                  const newMap = new Map(prev)
                  newMap.delete(fileId)
                  return newMap
                })
                setUploadStages((prev) => {
                  const newMap = new Map(prev)
                  newMap.delete(fileId)
                  return newMap
                })
                if (processUploadQueueRef.current) {
                  processUploadQueueRef.current()
                }
              }, 2000)
              return // Exit early for duplicate error document
              
              setUploadStages((prev) => {
                const newMap = new Map(prev)
                newMap.set(fileId, 'waiting-for-card')
                return newMap
              })
              setStagedProgress((prev) => {
                const newMap = new Map(prev)
                newMap.set(fileId, 90)
                return newMap
              })
              // Don't wait for polling - error state is already set
              return
            } else {
              // Duplicate document exists but no invoice found - OCR may still be processing
              console.log(`[UPLOAD] Duplicate document found (doc_id=${uploadMetadataId}, status=${docStatus}) but no invoice exists yet. Will poll for invoice creation.`)
            }
          }
          
          console.log(`[UPLOAD] Upload returned ${result.metadata.raw?.status} status, waiting for onComplete callback...`)
          
          // Set a timeout: if onComplete doesn't fire within 10 seconds, proceed anyway
          setTimeout(() => {
            if (!onCompleteCalled) {
              console.warn(`[UPLOAD] onComplete not called within 10s for ${file.name}, proceeding with basic flow`)
              console.warn(`[UPLOAD] Metadata:`, result.metadata)
              // Transition to processing state manually
              setStagedProgress((prev) => {
                const newMap = new Map(prev)
                newMap.set(fileId, 90) // Set to 90% to show processing
                return newMap
              })
              setUploadStages((prev) => {
                const newMap = new Map(prev)
                newMap.set(fileId, 'waiting-for-card')
                return newMap
              })
              setProcessingFiles((prev) => new Set(prev).add(fileId))
              // Store metadata if we have it
              if (result.metadata.id) {
                setUploadMetadata((prev) => {
                  const newMap = new Map(prev)
                  newMap.set(fileId, { id: String(result.metadata.id), fileName: file.name })
                  return newMap
                })
              }
              // Refresh invoices to check for completion
              fetchInvoices().catch(err => console.error('[UPLOAD] Error fetching invoices:', err))
            }
          }, 10000) // Increased to 10 seconds to give polling more time
        } else {
          // Immediate success (no polling needed) - complete immediately
          console.log(`[UPLOAD] Upload completed immediately for ${file.name}`)
          setStagedProgress((prev) => {
            const newMap = new Map(prev)
            newMap.set(fileId, 100)
            return newMap
          })
          setUploadStages((prev) => {
            const newMap = new Map(prev)
            newMap.set(fileId, 'complete')
            return newMap
          })
          toast.success(`Successfully uploaded ${file.name}`)
          
          // Clean up after showing completion
          setTimeout(() => {
            setActiveUploads((prev) => {
              const newSet = new Set(prev)
              newSet.delete(fileId)
              return newSet
            })
            setStagedProgress((prev) => {
              const newMap = new Map(prev)
              newMap.delete(fileId)
              return newMap
            })
            setUploadStages((prev) => {
              const newMap = new Map(prev)
              newMap.delete(fileId)
              return newMap
            })
            if (processUploadQueueRef.current) {
              processUploadQueueRef.current()
            }
          }, 2000)
        }
      } else {
        // Upload failed
        setUploadStages((prev) => {
          const newMap = new Map(prev)
          newMap.delete(fileId)
          return newMap
        })
        setProcessingFiles((prev) => {
          const newSet = new Set(prev)
          newSet.delete(fileId)
          return newSet
        })
        console.error(`[UPLOAD] Upload failed for ${file.name}:`, result.error)
        toast.error(result.error || 'Upload failed')
        setActiveUploads((prev) => {
          const newSet = new Set(prev)
          newSet.delete(fileId)
          return newSet
        })
        setStagedProgress((prev) => {
          const newMap = new Map(prev)
          newMap.delete(fileId)
          return newMap
        })
        setUploadMetadata((prev) => {
          const newMap = new Map(prev)
          newMap.delete(fileId)
          return newMap
        })
        // Process next in queue
        if (processUploadQueueRef.current) {
          processUploadQueueRef.current()
        }
      }
    } catch (err) {
      console.error(`[UPLOAD] Error uploading ${file.name}:`, err)
      const errorMessage = err instanceof Error ? err.message : 'Unknown error'
      toast.error(`Upload failed: ${errorMessage}`)
      
      // Clean up all upload state
      setUploadStages((prev) => {
        const newMap = new Map(prev)
        newMap.delete(fileId)
        return newMap
      })
      setProcessingFiles((prev) => {
        const newSet = new Set(prev)
        newSet.delete(fileId)
        return newSet
      })
      setActiveUploads((prev) => {
        const newSet = new Set(prev)
        newSet.delete(fileId)
        return newSet
      })
      setStagedProgress((prev) => {
        const newMap = new Map(prev)
        newMap.delete(fileId)
        return newMap
      })
      setUploadMetadata((prev) => {
        const newMap = new Map(prev)
        newMap.delete(fileId)
        return newMap
      })
      
      // Process next in queue
      if (processUploadQueueRef.current) {
        processUploadQueueRef.current()
      }
      setUploadingFiles((prev) => {
        const next = new Set(prev)
        next.delete(fileId)
        return next
      })
      setActiveUploads((prev) => {
        const newSet = new Set(prev)
        newSet.delete(fileId)
        return newSet
      })
      setStagedProgress((prev) => {
        const newMap = new Map(prev)
        newMap.delete(fileId)
        return newMap
      })
      setProcessingFiles((prev) => {
        const newSet = new Set(prev)
        newSet.delete(fileId)
        return newSet
      })
      setUploadMetadata((prev) => {
        const newMap = new Map(prev)
        newMap.delete(fileId)
        return newMap
      })
      // Clean up file object
      fileObjectsRef.current.delete(fileId)
      // Process next in queue
      setTimeout(() => {
        if (processUploadQueueRef.current) {
          processUploadQueueRef.current()
        }
      }, 100)
    }
  }, [animateProgress, fetchInvoices, toast, invoices])

  // Process upload queue - start uploads up to max 3 active
  const processUploadQueue = useCallback(() => {
    // Use a single state update to avoid race conditions
    setActiveUploads((prevActive) => {
      const newActive = new Set(prevActive)
      const filesToStart: Array<{ fileId: string; file: File }> = []
      const filesToRemove: string[] = []

      // Get current queue state
      setUploadQueue((prevQueue) => {
        const newQueue = [...prevQueue]

        // Find files to start (up to 3 active)
        while (newActive.size < 3 && newQueue.length > 0) {
          const fileId = newQueue.shift()
          if (fileId) {
            const file = fileObjectsRef.current.get(fileId)
            if (file) {
              newActive.add(fileId)
              filesToStart.push({ fileId, file })
              filesToRemove.push(fileId)
            }
          }
        }

        // Start uploads for files that were moved to active (after state updates)
        if (filesToStart.length > 0) {
          setTimeout(() => {
            filesToStart.forEach(({ fileId, file }) => {
              startUpload(fileId, file)
            })
          }, 0)
        }

        // Remove files that were moved to active from the queue
        return newQueue.filter((fileId) => !filesToRemove.includes(fileId))
      })

      return newActive
    })
  }, [startUpload])

  // Set the ref so startUpload can call processUploadQueue
  processUploadQueueRef.current = processUploadQueue

  // Detect when invoice cards appear and transition progress to 100%
  // Also periodically refresh invoice list for files in 'waiting-for-card' state
  useEffect(() => {
    // Check if any processing files have appeared in invoices list
    const waitingFiles = Array.from(uploadStages.entries())
      .filter(([_, stage]) => stage === 'waiting-for-card' || stage === 'processing')
      .map(([fileId]) => fileId)

    // Periodically refresh invoices for files waiting for cards (every 5 seconds)
    if (waitingFiles.length > 0) {
      console.log(`[UPLOAD] Setting up periodic refresh for ${waitingFiles.length} waiting files: ${waitingFiles.join(', ')}`)
      const refreshInterval = setInterval(() => {
        // Check current state (not closure) to see if we still have waiting files
        const currentWaitingFiles = Array.from(uploadStages.entries())
          .filter(([_, stage]) => stage === 'waiting-for-card' || stage === 'processing')
        if (currentWaitingFiles.length > 0) {
          console.log(`[UPLOAD] 🔄 Periodic refresh: checking for ${currentWaitingFiles.length} waiting files`)
          fetchInvoices().catch(err => console.error('[UPLOAD] ❌ Error refreshing invoices:', err))
        } else {
          console.log(`[UPLOAD] ⏹️ No waiting files, stopping periodic refresh`)
          clearInterval(refreshInterval)
        }
      }, 5000) // Refresh every 5 seconds

      // Clean up interval when component unmounts or no more waiting files
      return () => {
        console.log(`[UPLOAD] Cleaning up periodic refresh interval`)
        clearInterval(refreshInterval)
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [uploadStages]) // Removed fetchInvoices dependency to prevent infinite loop - fetchInvoices is stable via useCallback

  // Separate effect to detect when cards appear
  // This effect runs whenever invoices list or upload stages change
  // Use ref to track which fileIds we've already successfully matched to prevent re-checking
  const matchedFileIdsRef = useRef<Set<string>>(new Set())
  const lastInvoiceIdsRef = useRef<string>('') // Track invoice IDs as string to detect changes
  
  useEffect(() => {
    const waitingFiles = Array.from(uploadStages.entries())
      .filter(([_, stage]) => stage === 'waiting-for-card' || stage === 'processing')
      .map(([fileId]) => fileId)

    if (waitingFiles.length === 0) {
      matchedFileIdsRef.current.clear() // Reset when no waiting files
      lastInvoiceIdsRef.current = '' // Reset invoice tracking
      return // Early exit if no waiting files
    }

    // Always check for cards if we have waiting files and invoices exist
    // Don't skip just because invoice count hasn't changed - the invoice might have just appeared
    if (invoices.length === 0) {
      console.log(`[UPLOAD] ⏳ Waiting for invoices to appear (currently 0 invoices)`)
      return // No invoices to match against
    }
    
    // Always run check if we have waiting files and invoices - don't skip based on invoice IDs
    // The matchedFileIdsRef will prevent duplicate processing
    const currentInvoiceIds = invoices.map(inv => `${inv.id}/${inv.docId}`).sort().join(',')
    const invoiceIdsChanged = currentInvoiceIds !== lastInvoiceIdsRef.current
    if (invoiceIdsChanged) {
      lastInvoiceIdsRef.current = currentInvoiceIds
      // Reset matched file IDs when invoice list changes (new invoice might have appeared)
      matchedFileIdsRef.current.clear()
    }
    
    console.log(`[UPLOAD] 🔍 Card detection effect running: ${waitingFiles.length} waiting files, ${invoices.length} invoices, invoiceIdsChanged=${invoiceIdsChanged}, invoiceIds=${currentInvoiceIds.substring(0, 100)}...`)

    waitingFiles.forEach((fileId) => {
      // Skip if we've already matched this fileId (prevent duplicate processing)
      if (matchedFileIdsRef.current.has(fileId)) {
        return
      }
      
      const metadata = uploadMetadata.get(fileId)
      if (!metadata?.id) {
        console.warn(`[UPLOAD] ⚠️ No metadata.id for fileId=${fileId}, metadata=`, metadata)
        return
      }
      
      // Try multiple ID matching strategies
      // Metadata ID can be doc_id (UUID string) or invoice id
      // Invoice list items have: id (may be numeric or string UUID), docId (string UUID)
      const metadataIdStr = String(metadata.id)
      const metadataIdNum = Number(metadata.id) || 0
      
      // Check all possible ID fields - must be exact string matches (no NaN comparisons)
      const invoiceExistsById = invoices.some((inv) => {
        const invIdStr = String(inv.id)
        // Only check numeric comparison if both are valid numbers (not NaN)
        const invIdNum = Number(inv.id)
        const metadataIdNum = Number(metadata.id)
        // Numeric match only if both are valid numbers AND not zero (zero is ambiguous)
        const numericMatch = !isNaN(invIdNum) && !isNaN(metadataIdNum) && invIdNum !== 0 && metadataIdNum !== 0 && invIdNum === metadataIdNum
        const stringMatch = invIdStr === metadataIdStr
        const match = stringMatch || numericMatch
        if (match) {
          console.log(`[UPLOAD] 🔍 Match by ID: inv.id=${invIdStr} (${typeof inv.id}) === metadataId=${metadataIdStr} (${typeof metadata.id}), stringMatch=${stringMatch}, numericMatch=${numericMatch}`)
        }
        return match
      })
      const invoiceExistsByDocId = invoices.some((inv) => {
        const docIdStr = String(inv.docId || '')
        const match = docIdStr === metadataIdStr && docIdStr !== '' // Must be non-empty
        if (match) {
          console.log(`[UPLOAD] 🔍 Match by DocId: inv.docId=${docIdStr} === metadataId=${metadataIdStr}`)
        }
        return match
      })
      const invoiceExists = invoiceExistsById || invoiceExistsByDocId
      
      // Log detailed matching info - use same logic as matching check
      const matchingInvoices = invoices.filter((inv) => {
        const invIdStr = String(inv.id)
        const invIdNum = Number(inv.id)
        const metadataIdNum = Number(metadata.id)
        const docIdStr = String(inv.docId || '')
        // Numeric match only if both are valid numbers AND not zero (zero is ambiguous)
        const numericMatch = !isNaN(invIdNum) && !isNaN(metadataIdNum) && invIdNum !== 0 && metadataIdNum !== 0 && invIdNum === metadataIdNum
        const stringMatch = invIdStr === metadataIdStr
        const docIdMatch = docIdStr === metadataIdStr && docIdStr !== ''
        return stringMatch || numericMatch || docIdMatch
      })
      console.log(`[UPLOAD] 🔍 Card detection check: fileId=${fileId}, metadataId=${metadataIdStr} (type: ${typeof metadata.id})`)
      console.log(`[UPLOAD] 📋 Invoice list: ${invoices.length} invoices, IDs: [${invoices.slice(0, 5).map(inv => `${inv.id}/${inv.docId}`).join(', ')}...]`)
      console.log(`[UPLOAD] ✅ Matching: byId=${invoiceExistsById}, byDocId=${invoiceExistsByDocId}, total=${invoiceExists}, matches=${matchingInvoices.length}`)
      
      // Log each invoice's ID comparison for debugging
      invoices.forEach((inv, idx) => {
        const invIdStr = String(inv.id)
        const invIdNum = Number(inv.id)
        const metadataIdNum = Number(metadata.id)
        const docIdStr = String(inv.docId || '')
        const stringMatch = invIdStr === metadataIdStr
        // Numeric match only if both are valid numbers AND not zero (zero is ambiguous)
        const numericMatch = !isNaN(invIdNum) && !isNaN(metadataIdNum) && invIdNum !== 0 && metadataIdNum !== 0 && invIdNum === metadataIdNum
        const docIdMatch = docIdStr === metadataIdStr && docIdStr !== ''
        const matches = stringMatch || numericMatch || docIdMatch
        console.log(`[UPLOAD] 📊 Invoice ${idx}: id=${invIdStr} (num=${invIdNum}), docId=${docIdStr}, matches=${matches} (str=${stringMatch}, num=${numericMatch}, doc=${docIdMatch})`)
      })
      
      if (matchingInvoices.length > 0) {
        console.log(`[UPLOAD] 🎯 Matched invoice details:`, matchingInvoices[0])
      }
        
      // Only proceed if we actually found a matching invoice (not just a false positive)
      if (invoiceExists && matchingInvoices.length > 0) {
        // Mark as matched to prevent re-processing
        matchedFileIdsRef.current.add(fileId)
        const matchedInvoice = matchingInvoices[0]
        console.log(`[UPLOAD] ✅ Card appeared for file ${fileId}, invoice ID: ${metadata.id}, matched invoice: id=${matchedInvoice.id}, docId=${matchedInvoice.docId}`)
        console.log(`[UPLOAD] 🎯 Transitioning to 100% and marking as complete`)
        // Card appeared - transition to 100%
        animateProgress(fileId, 90, 100, 1000)
        
        // Mark as complete after animation
        setTimeout(() => {
          console.log(`[UPLOAD] 🎯 Marking file ${fileId} as complete`)
          setUploadStages((prev) => {
            const newMap = new Map(prev)
            newMap.set(fileId, 'complete')
            console.log(`[UPLOAD] ✅ Upload stage set to 'complete' for ${fileId}`)
            return newMap
          })
          
          // Clean up after showing completion (wait longer to ensure card is visible)
          setTimeout(() => {
            console.log(`[UPLOAD] 🧹 Starting cleanup for ${fileId} (card should be visible by now)`)
            setActiveUploads((prev) => {
              const newSet = new Set(prev)
              newSet.delete(fileId)
              return newSet
            })
            setStagedProgress((prev) => {
              const newMap = new Map(prev)
              newMap.delete(fileId)
              return newMap
            })
            setUploadStages((prev) => {
              const newMap = new Map(prev)
              newMap.delete(fileId)
              return newMap
            })
            setProcessingFiles((prev) => {
              const newSet = new Set(prev)
              newSet.delete(fileId)
              return newSet
            })
            setUploadingFiles((prev) => {
              const newSet = new Set(prev)
              newSet.delete(fileId)
              return newSet
            })
            setUploadMetadata((prev) => {
              const newMap = new Map(prev)
              newMap.delete(fileId)
              return newMap
            })
            
            // Clean up file object
            fileObjectsRef.current.delete(fileId)
            
            // Process next in queue
            setTimeout(() => {
              processUploadQueue()
            }, 100)
          }, 5000) // Wait 5 seconds before cleanup (give card time to appear and be visible)
        }, 1000)
      } else {
        console.log(`[UPLOAD] ❌ No match found for fileId=${fileId}, metadataId=${metadataIdStr}`)
        console.log(`[UPLOAD] ⚠️ Invoice with doc_id=${metadataIdStr} doesn't exist in invoice list. This might mean:`)
        console.log(`[UPLOAD]   1. OCR processing failed (check backend logs)`)
        console.log(`[UPLOAD]   2. Invoice hasn't been created yet (still processing)`)
        console.log(`[UPLOAD]   3. Document exists but invoice record is missing`)
        console.log(`[UPLOAD] 📊 Debug: invoiceExists=${invoiceExists}, matchingInvoices.length=${matchingInvoices.length}`)
        
        // Check if metadata indicates error status
        const metadata = uploadMetadata.get(fileId)
        const hasErrorStatus = metadata?.raw?.status === 'error'
        
        // If we've been waiting for a while (more than 2 minutes) and status is error, show error state
        // Otherwise keep waiting - periodic refresh will keep checking
        if (hasErrorStatus) {
          console.warn(`[UPLOAD] ⚠️ Document has error status - OCR likely failed. Keeping at 90% and showing error state.`)
          // Don't mark as complete - keep it in waiting state but don't progress to 100%
          // The progress bar will stay at 90% (isProcessing=true shows 100% width, but percentage stays at 90)
        }
        // Keep waiting - periodic refresh will keep checking
        // Don't mark as complete - let it keep waiting for the invoice to appear
      }
    })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [uploadStages, uploadMetadata, invoices]) // Include invoices so effect runs when invoices appear - matchedFileIdsRef prevents duplicate processing

  // Manual pairing workflow: Auto-select first unpaired invoice when entering mode
  useEffect(() => {
    if (manualPairingWorkflowActive && !activePairingInvoiceId) {
      const firstUnpaired = invoices.find(inv => !inv.matched && !inv.paired)
      if (firstUnpaired) {
        setActivePairingInvoiceId(firstUnpaired.id)
        setSelectedId(firstUnpaired.id) // Also select it in the main view
      }
    }
  }, [manualPairingWorkflowActive, activePairingInvoiceId, invoices])

  // Manual pairing workflow: Fetch suggestions and unpaired DNs when active invoice changes
  useEffect(() => {
    if (manualPairingWorkflowActive && activePairingInvoiceId) {
      setLoadingPairingData(true)
      setPairingError(null)
      
      // Fetch suggestions for this invoice
      fetchPairingSuggestions(activePairingInvoiceId)
        .then(res => {
          setPairingSuggestions(res.suggestions || [])
        })
        .catch(err => {
          console.error('Failed to fetch pairing suggestions:', err)
          setPairingSuggestions([])
          setPairingError('Could not load suggestions. You can still pair manually using unpaired delivery notes.')
        })
      
      // Fetch unpaired delivery notes
      fetchUnpairedDeliveryNotes()
        .then(dns => {
          setUnpairedDeliveryNotes(dns || [])
        })
        .catch(err => {
          console.error('Failed to fetch unpaired delivery notes:', err)
          setUnpairedDeliveryNotes([])
          if (!pairingError) {
            setPairingError('Could not load unpaired delivery notes. Please check your connection and retry.')
          }
        })
        .finally(() => {
          setLoadingPairingData(false)
        })
    }
  }, [manualPairingWorkflowActive, activePairingInvoiceId])

  // Filter invoices by search query
  // IMPORTANT: Show ALL invoices including "needs_review" and empty data ones
  // Don't filter out invoices with Unknown Supplier or £0.00 - they need to be visible for review
  const filteredInvoices = invoices.filter((inv) => {
    if (!searchQuery) return true
    const query = searchQuery.toLowerCase()
    return (
      inv.supplier?.toLowerCase().includes(query) ||
      inv.invoiceNumber?.toLowerCase().includes(query) ||
      String(inv.id).toLowerCase().includes(query)
    )
  })
  
  // Log filtering results
  console.log('[Invoices] Filtering results:', {
    totalInvoices: invoices.length,
    filteredCount: filteredInvoices.length,
    searchQuery: searchQuery || '(none)',
    needsReviewCount: filteredInvoices.filter(inv => inv.dbStatus === 'needs_review').length,
    emptyDataCount: filteredInvoices.filter(inv => 
      (!inv.supplier || inv.supplier === 'Unknown Supplier') && 
      (!inv.totalValue || inv.totalValue === 0)
    ).length
  })

  // Generate issues from invoice data
  const generateIssues = (invoice: InvoiceDetail | null): Issue[] => {
    if (!invoice) return []
    const issues: Issue[] = []

    // Check for short deliveries
    if (invoice.lineItems && invoice.deliveryNote?.lineItems) {
      invoice.lineItems.forEach((item) => {
        const dnItem = invoice.deliveryNote?.lineItems?.find(
          (dn) => dn.description === item.description || dn.item === item.item
        )
        if (dnItem) {
          const invQty = item.qty || 0
          const dnQty = dnItem.qty || 0
          if (dnQty < invQty) {
            const itemDesc = item.description || 'Unknown item'
            issues.push({
              id: `short-${itemDesc}-${Date.now()}`,
              type: 'short',
              severity: dnQty < invQty * 0.5 ? 'critical' : 'review',
              item: itemDesc,
              description: `Short delivery: invoiced ${invQty}, delivered ${dnQty}`,
              suggestedCredit: (invQty - dnQty) * (item.unitPrice || 0),
            })
          }
        }
      })
    }

    return issues
  }

  const issues = generateIssues(selectedInvoice)

  // Compute readyToSubmit for selected invoice
  const canSubmitInvoice = selectedInvoice && (() => {
    // Invoice must be scanned or manual
    if (!selectedInvoice.status) return false
    
    // No unresolved issues (or issues have been reviewed - simplified for now)
    const hasUnresolvedIssues = issues.length > 0
    
    // Delivery note linked (optional but preferred)
    const hasDeliveryNote = !!selectedInvoice.deliveryNote
    
    // Status is not already submitted (we don't track this yet, so assume not submitted)
    
    // Ready if: scanned/manual AND (no issues OR delivery note linked)
    return !hasUnresolvedIssues || hasDeliveryNote
  })()

  // Compute readyToSubmit for invoice list items
  const invoicesWithReadyStatus = invoices.map((inv) => {
    // Simplified logic: ready if no issues or has delivery note
    const ready = (!inv.issuesCount || inv.issuesCount === 0) || inv.hasDeliveryNote
    return { ...inv, readyToSubmit: ready }
  })

  // Derive ready invoices (don't use separate state)
  const readyInvoices = invoicesWithReadyStatus.filter((inv) => inv.readyToSubmit)

  // Handle clear selection - delete all uploaded invoices that haven't been submitted
  const handleClearSelection = async () => {
    // Filter invoices that haven't been submitted (status !== 'submitted')
    const nonSubmittedInvoices = invoices.filter((inv) => inv.dbStatus !== 'submitted')
    
    if (nonSubmittedInvoices.length === 0) {
      toast.info('No invoices to clear. All invoices have already been submitted.')
      return
    }
    
    const confirmed = window.confirm(
      `Are you sure you want to delete ${nonSubmittedInvoices.length} uploaded invoice${nonSubmittedInvoices.length !== 1 ? 's' : ''}? This will permanently remove them from the database. Submitted invoices will not be affected.`
    )
    
    if (!confirmed) return
    
    try {
      const invoiceIds = nonSubmittedInvoices.map((inv) => inv.id)
      console.log('[Invoices] Clearing invoices:', { count: invoiceIds.length, ids: invoiceIds })
      
      const result = await deleteInvoices(invoiceIds)
      
      // Refresh invoice list
      await fetchInvoices()
      
      // Clear selected invoice if it was deleted
      if (selectedId && invoiceIds.includes(selectedId)) {
        setSelectedId(null)
        setSelectedInvoice(null)
      }
      
      // Show success message with details
      let message = `Successfully deleted ${result.deleted_count} invoice${result.deleted_count !== 1 ? 's' : ''}!`
      if (result.skipped_count && result.skipped_count > 0) {
        message += ` (${result.skipped_count} submitted invoice${result.skipped_count !== 1 ? 's' : ''} were skipped)`
      }
      toast.success(message)
    } catch (err) {
      console.error('[Invoices] Failed to delete invoices:', err)
      const errorMessage = err instanceof Error ? err.message : 'Unknown error'
      
      // Provide more helpful error messages
      if (errorMessage.includes('405')) {
        toast.error('Failed to delete invoices: The server endpoint is not available. Please check that the backend is running and the route is properly configured.')
      } else if (errorMessage.includes('403')) {
        toast.error('Failed to delete invoices: This operation is not allowed in the current environment.')
      } else {
        toast.error(`Failed to delete invoices: ${errorMessage}`)
      }
    }
  }

  // Generate metadata
  const metadata: DocumentMetadata | undefined = selectedInvoice
    ? {
        source: selectedInvoice.status === 'manual' ? 'manual' : 'upload',
        // TODO: Add real metadata from backend
      }
    : undefined

  // Handle invoice submit
  const handleSubmitInvoice = async () => {
    if (!selectedId || !canSubmitInvoice) return

    setIsSubmitting(true)
    try {
      await submitInvoices([selectedId])
      // Refresh invoice detail and list
      await fetchInvoiceDetail(selectedId)
      await fetchInvoices()
      // Trigger discrepancy refresh after submission
      setDiscrepancyRefreshTrigger(prev => prev + 1)
      // Show success notification
      toast.success('Invoice submitted successfully!')
    } catch (err) {
      console.error('Failed to submit invoice:', err)
      toast.error(`Failed to submit invoice: ${err instanceof Error ? err.message : 'Unknown error'}`)
    } finally {
      setIsSubmitting(false)
    }
  }

  // Handle batch submit
  const handleBatchSubmit = async (invoiceIds: string[]) => {
    if (invoiceIds.length === 0) return

    const confirmed = window.confirm(
      `Are you sure you want to submit ${invoiceIds.length} invoice${invoiceIds.length !== 1 ? 's' : ''}?`
    )
    if (!confirmed) return

    setIsSubmitting(true)
    try {
      await submitInvoices(invoiceIds)
      // Refresh invoice list
      await fetchInvoices()
      // Refresh selected invoice if it was submitted
      if (selectedId && invoiceIds.includes(selectedId)) {
        await fetchInvoiceDetail(selectedId)
      }
      // Trigger discrepancy refresh after batch submission
      setDiscrepancyRefreshTrigger(prev => prev + 1)
      toast.success(`Successfully submitted ${invoiceIds.length} invoice${invoiceIds.length !== 1 ? 's' : ''}!`)
    } catch (err) {
      console.error('Failed to submit invoices:', err)
      toast.error(`Failed to submit invoices: ${err instanceof Error ? err.message : 'Unknown error'}`)
    } finally {
      setIsSubmitting(false)
    }
  }

  // Handle single invoice deletion
  const handleDeleteInvoice = async (invoiceId: string) => {
    try {
      const result = await deleteInvoices([invoiceId])
      
      // Refresh invoice list
      await fetchInvoices()
      
      // Clear selected invoice if it was deleted
      if (selectedId === invoiceId) {
        setSelectedId(null)
        setSelectedInvoice(null)
      }
      
      // Show success message
      if (result.deleted_count > 0) {
        toast.success('Invoice deleted successfully!')
      } else if (result.skipped_count && result.skipped_count > 0) {
        toast.warning('This invoice has already been submitted and cannot be deleted.')
      } else {
        toast.error('Failed to delete invoice. Please try again.')
      }
    } catch (err) {
      console.error('[Invoices] Failed to delete invoice:', err)
      const errorMessage = err instanceof Error ? err.message : 'Unknown error'
      
      // Provide helpful error messages
      if (errorMessage.includes('405')) {
        toast.error('Failed to delete invoice: The server endpoint is not available. Please check that the backend is running.')
      } else if (errorMessage.includes('403')) {
        toast.error('Failed to delete invoice: This operation is not allowed in the current environment.')
      } else {
        toast.error(`Failed to delete invoice: ${errorMessage}`)
      }
    }
  }

  // Handle file upload with drag and drop
  const handleFileUpload = useCallback(async (files: FileList) => {
    const fileArray = Array.from(files)
    
    // Add all files to queue with unique IDs
    const newFileIds: string[] = []
    fileArray.forEach((file) => {
      const fileId = `${file.name}-${Date.now()}-${Math.random()}`
      newFileIds.push(fileId)
      
      // Store file object for later use
      fileObjectsRef.current.set(fileId, file)
      
      // Initialize metadata
      setUploadMetadata((prev) => {
        const newMap = new Map(prev)
        newMap.set(fileId, { id: '', fileName: file.name })
        return newMap
      })
      
      // Initialize staged progress
      setStagedProgress((prev) => new Map(prev).set(fileId, 0))
      setUploadStages((prev) => {
        const newMap = new Map(prev)
        newMap.set(fileId, 'uploading')
        return newMap
      })
    })
    
    // Process files: add to active if space available, otherwise to queue
    setActiveUploads((prevActive) => {
      const newActive = new Set(prevActive)
      const filesToStart: Array<{ fileId: string; file: File }> = []
      const filesToQueue: string[] = []
      
      newFileIds.forEach((fileId, index) => {
        const file = fileArray[index]
        if (newActive.size < 3) {
          // Can start immediately
          newActive.add(fileId)
          filesToStart.push({ fileId, file })
        } else {
          // Add to queue
          filesToQueue.push(fileId)
        }
      })
      
      // Update queue with files that need to wait
      if (filesToQueue.length > 0) {
        setUploadQueue((prevQueue) => [...prevQueue, ...filesToQueue])
      }
      
      // Start uploads for files that can start immediately
      if (filesToStart.length > 0) {
        setTimeout(() => {
          filesToStart.forEach(({ fileId, file }) => {
            startUpload(fileId, file)
          })
        }, 0)
      }
      
      return newActive
    })
  }, [startUpload])

  const handleUploadClick = () => {
    fileInputRef.current?.click()
  }

  const handleNewManualInvoice = () => {
    setShowManualInvoiceOrDNModal(true)
  }

  const handleNewManualDN = () => {
    setShowManualInvoiceOrDNModal(true)
  }

  const handleInvoiceUpdated = async () => {
    // Refresh invoice list
    await fetchInvoices()
    
    // Refresh selected invoice details if one is selected
    if (selectedId) {
      await fetchInvoiceDetail(selectedId)
    }
    
    // Trigger discrepancy refresh
    setDiscrepancyRefreshTrigger(prev => prev + 1)
  }

  const handleManualInvoiceOrDNSuccess = (invoiceId?: string, createdType?: 'invoice' | 'delivery-note' | 'both') => {
    fetchInvoices()
    // If a new invoice was created, select it and fetch its details
    if (invoiceId) {
      setSelectedId(invoiceId)
      fetchInvoiceDetail(invoiceId)
    } else if (selectedId) {
      // Refresh invoice detail if one is already selected (to update delivery note options)
      fetchInvoiceDetail(selectedId)
    }
    // Only trigger delivery note refresh if a delivery note was actually created
    // This prevents DN cards from appearing when only an invoice is created
    if (createdType === 'delivery-note' || createdType === 'both') {
      setDiscrepancyRefreshTrigger(prev => prev + 1)
    }
  }

  const handleLinkDeliveryNote = () => {
    if (selectedId) {
      setShowLinkDNModal(true)
    }
  }

  const handleChangeDeliveryNote = () => {
    handleLinkDeliveryNote() // Same as linking
  }

  const handleLinkDNSuccess = async (warnings?: string[]) => {
    if (warnings && warnings.length > 0) {
      toast.warning(`Pairing completed with warnings: ${warnings.slice(0, 2).join(', ')}`)
    } else {
      toast.success('Invoice paired with delivery note successfully')
    }
    if (selectedId) {
      await fetchInvoiceDetail(selectedId)
      
      // Refresh pairing suggestions after pairing (will be empty since invoice is now paired)
      try {
        const response = await fetchPairingSuggestions(selectedId)
        setPairingSuggestions(response.suggestions || [])
      } catch (err) {
        console.debug('Failed to refresh pairing suggestions after pairing:', err)
      }
    }
    // Trigger discrepancy refresh after pairing
    setDiscrepancyRefreshTrigger(prev => prev + 1)
  }

  // Manual pairing workflow: Handle pairing a DN to the active invoice
  const handlePairDeliveryNote = async (deliveryNoteId: string) => {
    if (!activePairingInvoiceId || pairingInProgress) return
    
    setPairingInProgress(deliveryNoteId)
    setPairingError(null)
    
    try {
      await linkDeliveryNoteToInvoice(activePairingInvoiceId, deliveryNoteId)
      
      toast.success('Delivery note paired successfully')
      
      // Update local state
      setInvoices(prev => prev.map(inv => 
        inv.id === activePairingInvoiceId 
          ? { ...inv, matched: true, paired: true }
          : inv
      ))
      
      // Remove DN from unpaired list
      setUnpairedDeliveryNotes(prev => prev.filter(dn => dn.id !== deliveryNoteId))
      setPairingSuggestions(prev => prev.filter(s => s.deliveryNoteId !== deliveryNoteId))
      
      // Refresh invoice detail
      if (selectedId === activePairingInvoiceId) {
        fetchInvoiceDetail(activePairingInvoiceId)
      }
      
      // Refresh pairing suggestions for the next invoice (will be set below)
      // Auto-advance to next unpaired invoice
      const nextUnpaired = invoices.find(inv => !inv.matched && !inv.paired && inv.id !== activePairingInvoiceId)
      if (nextUnpaired) {
        setActivePairingInvoiceId(nextUnpaired.id)
        setSelectedId(nextUnpaired.id)
        
        // Refresh pairing suggestions for the next invoice
        try {
          const response = await fetchPairingSuggestions(nextUnpaired.id)
          setPairingSuggestions(response.suggestions || [])
        } catch (err) {
          console.error('Failed to refresh pairing suggestions for next invoice:', err)
          setPairingSuggestions([])
        }
      } else {
        // No more unpaired invoices
        setActivePairingInvoiceId(null)
        setPairingSuggestions([])
        toast.info('All invoices have been paired!')
      }
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'Failed to pair delivery note'
      toast.error(errorMsg)
      setPairingError(errorMsg)
      console.error('Failed to pair delivery note:', err)
      // Don't auto-advance on error - stay on current invoice
    } finally {
      setPairingInProgress(null)
    }
  }

  // Toggle manual pairing workflow mode
  const handleToggleManualPairingWorkflow = () => {
    setManualPairingWorkflowActive(prev => !prev)
    if (!manualPairingWorkflowActive) {
      // Entering pairing mode - will auto-select first unpaired invoice via useEffect
    } else {
      // Exiting pairing mode
      setActivePairingInvoiceId(null)
      setPairingSuggestions([])
      setUnpairedDeliveryNotes([])
    }
  }

  const handleViewDeliveryNote = async () => {
    if (selectedInvoice?.deliveryNote?.id) {
      setSelectedDNId(selectedInvoice.deliveryNote.id)
      setShowDNDetailModal(true)
    }
  }

  const handleMarkReviewed = async () => {
    if (!selectedId) return

    try {
      await markInvoiceReviewed(selectedId)
      // Refresh invoice detail and list
      fetchInvoiceDetail(selectedId)
      fetchInvoices()
      // Trigger discrepancy refresh after marking as reviewed
      setDiscrepancyRefreshTrigger(prev => prev + 1)
      // Show success notification could be added here
    } catch (err) {
      console.error('Failed to mark as reviewed:', err)
      // Show error notification could be added here
    }
  }

  const handleEscalateToSupplier = async () => {
    if (!selectedId) return

    const confirmed = window.confirm('Are you sure you want to escalate this invoice to the supplier?')
    if (!confirmed) return

    try {
      await escalateToSupplier(selectedId)
      // Refresh invoice detail
      fetchInvoiceDetail(selectedId)
      // Show success notification could be added here
    } catch (err) {
      console.error('Failed to escalate:', err)
      // Show error notification could be added here
    }
  }

  const handleOpenPDF = async () => {
    if (!selectedId) return

    try {
      const pdfUrl = await fetchInvoicePDF(selectedId)
      window.open(pdfUrl, '_blank')
    } catch (err) {
      console.error('Failed to open PDF:', err)
      toast.error('Failed to open PDF. Please try again.')
    }
  }

  const handleViewOCRDetails = () => {
    if (selectedId) {
      setShowOCRModal(true)
    }
  }

  const handleSaveNote = async () => {
    if (!selectedId || !noteText.trim()) return

    setSavingNote(true)
    try {
      await saveInvoiceNote(selectedId, noteText.trim())
      setNoteText('')
      // Refresh invoice detail to show saved note
      fetchInvoiceDetail(selectedId)
      // Show success notification could be added here
    } catch (err) {
      console.error('Failed to save note:', err)
      // Show error notification could be added here
    } finally {
      setSavingNote(false)
    }
  }

  const handleSupplierClick = (supplierName: string) => {
    setSelectedSupplierName(supplierName)
    setShowSupplierModal(true)
  }

  // Debug logging - REMOVED to prevent infinite render loops
  // If you need to debug, use React DevTools Profiler instead
  // console.log('[Invoices] Render state:', { loading, error, filteredInvoicesLength: filteredInvoices.length, invoicesLength: invoices.length, selectedId })

  // Ensure component always renders - wrap in try-catch at render level
  try {
    return (
      <div className="invoices-page-new">
      <AppHeader>
        <InvoicesHeader
            // Removed viewMode prop
          venue={venue}
          onVenueChange={setVenue}
          dateRange={dateRange}
          onDateRangeChange={setDateRange}
          searchQuery={searchQuery}
          onSearchChange={setSearchQuery}
          onUploadClick={handleUploadClick}
          onNewManualInvoice={handleNewManualInvoice}
          onNewManualDN={handleNewManualDN}
          manualPairingWorkflowActive={manualPairingWorkflowActive}
          onToggleManualPairingWorkflow={handleToggleManualPairingWorkflow}
        />
      </AppHeader>

        <div className="invoices-main-new has-submission-footer">
        {/* Loading State - Show as overlay when loading and no invoices */}
        {loading && filteredInvoices.length === 0 && (
          <div style={{ 
            position: 'absolute',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            display: 'flex', 
            alignItems: 'center', 
            justifyContent: 'center', 
            padding: '80px',
            color: 'var(--text-muted)',
            fontSize: '14px',
            zIndex: 10,
            background: 'rgba(26, 26, 26, 0.8)',
            backdropFilter: 'blur(4px)'
          }}>
            Loading invoices...
          </div>
        )}

        {/* Error State - Show but don't block UI */}
        {error && filteredInvoices.length === 0 && !loading && (
          <div style={{ 
            gridColumn: '1 / -1', 
            display: 'flex', 
            flexDirection: 'column',
            alignItems: 'center', 
            justifyContent: 'center', 
            padding: '24px',
            marginBottom: '24px',
            background: 'rgba(239, 68, 68, 0.1)',
            border: '1px solid rgba(239, 68, 68, 0.3)',
            borderRadius: '12px',
            color: 'var(--accent-red)',
            fontSize: '13px',
            gap: '12px',
            maxWidth: '600px',
            margin: '0 auto 24px auto'
          }}>
            <div style={{ fontWeight: '600', marginBottom: '4px' }}>⚠️ Connection Error</div>
            <div style={{ textAlign: 'center', marginBottom: '12px', color: 'var(--text-secondary)' }}>{error}</div>
            <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginBottom: '12px', textAlign: 'center' }}>
              <div style={{ marginBottom: '8px' }}>
                <strong>Backend may not be running.</strong>
              </div>
              <div style={{ marginBottom: '8px' }}>
                Start the backend with:
              </div>
              <code style={{ 
                display: 'block', 
                background: 'rgba(0, 0, 0, 0.3)', 
                padding: '8px', 
                borderRadius: '4px',
                fontSize: '11px',
                marginBottom: '8px'
              }}>
                python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
              </code>
              <div style={{ marginTop: '8px' }}>
                Or use: <code style={{ fontSize: '11px' }}>start_backend_8000.bat</code>
              </div>
            </div>
            <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginBottom: '12px', textAlign: 'center' }}>
              You can still upload documents or create manual invoices using the buttons above.
            </div>
            <button 
              className="glass-button" 
              onClick={() => fetchInvoices()}
              style={{ marginTop: '8px' }}
            >
              Retry Connection
            </button>
          </div>
        )}

        {/* Left Column - Document List - Hide when loading and no invoices */}
        {!(loading && filteredInvoices.length === 0) && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0', gridColumn: '1' }}>
            <CompactDragDropZone onUpload={handleFileUpload} />
            
            {/* Active Upload Progress Bars (max 3) - reversed order (first at bottom) */}
            {Array.from(activeUploads).slice(0, 3).reverse().map((fileId, index) => {
              const percentage = stagedProgress.get(fileId) || 0
              const fileName = uploadMetadata.get(fileId)?.fileName || fileId.split('-').slice(0, -2).join('-')
              const stage = uploadStages.get(fileId)
              const isComplete = stage === 'complete'
              const isProcessing = stage === 'processing' || stage === 'waiting-for-card'
              const metadata = uploadMetadata.get(fileId)
              const hasError = metadata?.raw?.status === 'error' && stage === 'waiting-for-card'
              const errorMessage = metadata?.error || metadata?.raw?.error || undefined
              
              const docId = metadata?.id || undefined
              
              return (
                <UploadProgressBar
                  key={fileId}
                  fileName={fileName}
                  percentage={percentage}
                  isComplete={isComplete}
                  isProcessing={isProcessing}
                  hasError={hasError}
                  errorMessage={errorMessage}
                  docId={docId}
                  onRetry={async (retryDocId) => {
                    try {
                      console.log(`[UPLOAD] Retrying OCR for doc_id: ${retryDocId}`)
                      await retryOCR(retryDocId)
                      toast.success('OCR retry initiated. Processing...')
                      
                      // Reset upload state to allow re-polling
                      setUploadStages((prev) => {
                        const newMap = new Map(prev)
                        newMap.set(fileId, 'processing')
                        return newMap
                      })
                      setStagedProgress((prev) => {
                        const newMap = new Map(prev)
                        newMap.set(fileId, 90) // Reset to 90% to show processing
                        return newMap
                      })
                      
                      // Clear error status from metadata
                      setUploadMetadata((prev) => {
                        const newMap = new Map(prev)
                        const existing = newMap.get(fileId)
                        if (existing) {
                          newMap.set(fileId, {
                            ...existing,
                            raw: { ...existing.raw, status: 'processing' },
                            error: undefined
                          })
                        }
                        return newMap
                      })
                      
                      // Start polling again
                      setTimeout(() => {
                        fetchInvoices()
                      }, 2000)
                    } catch (err) {
                      console.error(`[UPLOAD] Failed to retry OCR:`, err)
                      toast.error(`Failed to retry OCR: ${err instanceof Error ? err.message : 'Unknown error'}`)
                    }
                  }}
                  onComplete={() => {
                    // Remove from active and process next in queue
                    setActiveUploads((prev) => {
                      const newSet = new Set(prev)
                      newSet.delete(fileId)
                      return newSet
                    })
                    if (processUploadQueueRef.current) {
                      processUploadQueueRef.current()
                    }
                  }}
                />
              )
            })}
            
            {/* Next in Queue - Show only first queued item with fade effect */}
            {uploadQueue.length > 0 && (
              <div className="upload-next-in-queue">
                <div className="upload-next-in-queue-content">
                  <div className="upload-next-in-queue-icon">
                    <svg width="14" height="14" viewBox="0 0 16 16" fill="none">
                      <circle cx="8" cy="8" r="7" stroke="currentColor" strokeWidth="1.5" opacity="0.3" />
                    </svg>
                  </div>
                  <div className="upload-next-in-queue-info">
                    <div className="upload-next-in-queue-filename">
                      {uploadMetadata.get(uploadQueue[0])?.fileName || uploadQueue[0].split('-').slice(0, -2).join('-')}
                    </div>
                    <div className="upload-next-in-queue-status">
                      Next in queue {uploadQueue.length > 1 && `(${uploadQueue.length} total)`}
                    </div>
                  </div>
                </div>
              </div>
            )}
            
            <DocumentList
              invoices={filteredInvoices.length > 0 ? invoicesWithReadyStatus.filter((inv) => {
                if (!searchQuery) return true
                const query = searchQuery.toLowerCase()
                return (
                  inv.supplier?.toLowerCase().includes(query) ||
                  inv.invoiceNumber?.toLowerCase().includes(query) ||
                  String(inv.id).toLowerCase().includes(query)
                )
              }) : []}
              selectedId={selectedId}
              onSelect={(invoiceId) => {
                setSelectedId(invoiceId)
                setSelectedDNId(null) // Clear DN selection when invoice is selected
              }}
              sortBy={sortBy}
              onSortChange={setSortBy}
              newlyUploadedIds={newlyUploadedIds}
              onSupplierClick={handleSupplierClick}
              onBatchSubmit={handleBatchSubmit}
              onDelete={handleDeleteInvoice}
            />
          </div>
        )}

        {/* Middle Column - Document Detail - Hide when loading and no invoices */}
        {!(loading && filteredInvoices.length === 0) && (
          <DocumentDetailPanel
            invoice={selectedInvoice}
            selectedDNId={selectedDNId}
            onLinkDeliveryNote={handleLinkDeliveryNote}
            onCreateDeliveryNote={handleNewManualDN}
            onChangeDeliveryNote={handleChangeDeliveryNote}
            onOpenPDF={handleOpenPDF}
            onViewOCRDetails={handleViewOCRDetails}
            onSaveNote={handleSaveNote}
            noteText={noteText}
            onNoteTextChange={setNoteText}
            savingNote={savingNote}
            onSubmit={handleSubmitInvoice}
            canSubmit={!!canSubmitInvoice}
            isSubmitting={isSubmitting}
            hasIssues={issues.length > 0}
            onPairSuccess={handleLinkDNSuccess}
            isEmptyState={filteredInvoices.length === 0}
            onUploadClick={handleUploadClick}
            onNewManualInvoice={handleNewManualInvoice}
            onSelectInvoice={(invoiceId) => {
              setSelectedId(invoiceId)
              setSelectedDNId(null) // Clear DN selection when invoice is selected
              setHighlightContext(null) // Clear highlight when manually selecting
            }}
            manualPairingWorkflowActive={manualPairingWorkflowActive}
            topSuggestion={pairingSuggestions.length > 0 ? pairingSuggestions[0] : null}
            onPairWithSuggestion={handlePairDeliveryNote}
            onEditInvoice={(invoiceId) => {
              setEditingInvoiceId(invoiceId)
              setEditMode('invoice')
              setShowManualInvoiceOrDNModal(true)
            }}
            onEditDeliveryNote={(dnId) => {
              setEditingDNId(dnId)
              setEditMode('delivery-note')
              setShowManualInvoiceOrDNModal(true)
            }}
            highlightContext={highlightContext}
            onHighlightComplete={() => setHighlightContext(null)}
            onInvoiceUpdated={handleInvoiceUpdated}
          />
        )}

        {/* Right Column - Manual Pairing Mode or Smart Discrepancy Widget */}
        {!(loading && filteredInvoices.length === 0) && (
          <div style={{ gridColumn: '3', display: 'flex', flexDirection: 'column', gap: '16px' }}>
            {manualPairingWorkflowActive ? (
              <div className="manual-pairing-column">
                <div className="manual-pairing-header">
                  <h3>Delivery Notes</h3>
                  {loadingPairingData && <span className="loading-indicator">Loading...</span>}
                </div>
                
                {pairingError && (
                  <div style={{
                    padding: '12px',
                    background: 'rgba(239, 68, 68, 0.1)',
                    border: '1px solid rgba(239, 68, 68, 0.3)',
                    borderRadius: '8px',
                    fontSize: '12px',
                    color: 'var(--accent-red)',
                    marginBottom: '12px'
                  }}>
                    {pairingError}
                  </div>
                )}
                
                {activePairingInvoiceId ? (
                  <>
                    {/* Section A: Suggested DNs */}
                    {pairingSuggestions.length > 0 && (
                      <div className="pairing-section">
                        <h4 className="pairing-section-title">Suggested ({pairingSuggestions.length})</h4>
                        {pairingSuggestions.map((suggestion) => (
                          <div key={suggestion.id} className="dn-card suggested">
                            <div className="dn-card-header">
                              <span className="dn-number">{suggestion.deliveryNoteNumber || 'No number'}</span>
                              <span className="confidence-badge">{Math.round((suggestion.confidence || 0) * 100)}%</span>
                            </div>
                            <div className="dn-card-body">
                              <div className="dn-info">
                                <span className="dn-supplier">{suggestion.supplier || 'Unknown'}</span>
                                <span className="dn-date">{suggestion.deliveryDate || 'No date'}</span>
                                <span className="dn-total">£{(suggestion.totalAmount || 0).toFixed(2)}</span>
                              </div>
                              <button
                                className="glass-button primary-action"
                                onClick={() => handlePairDeliveryNote(suggestion.deliveryNoteId)}
                                disabled={pairingInProgress === suggestion.deliveryNoteId}
                              >
                                {pairingInProgress === suggestion.deliveryNoteId ? 'Pairing...' : 'Pair'}
                              </button>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                    
                    {/* Section B: Other Unpaired DNs */}
                    {unpairedDeliveryNotes.filter(dn => !pairingSuggestions.some(s => s.deliveryNoteId === dn.id)).length > 0 && (
                      <div className="pairing-section">
                        <h4 className="pairing-section-title">
                          Other Unpaired ({unpairedDeliveryNotes.filter(dn => !pairingSuggestions.some(s => s.deliveryNoteId === dn.id)).length})
                        </h4>
                        {unpairedDeliveryNotes
                          .filter(dn => !pairingSuggestions.some(s => s.deliveryNoteId === dn.id))
                          .map((dn) => (
                            <div key={dn.id} className="dn-card">
                              <div className="dn-card-header">
                                <span className="dn-number">{dn.noteNumber || dn.deliveryNo || 'No number'}</span>
                              </div>
                              <div className="dn-card-body">
                                <div className="dn-info">
                                  <span className="dn-supplier">{dn.supplier || 'Unknown'}</span>
                                  <span className="dn-date">{dn.date || 'No date'}</span>
                                  <span className="dn-total">£{(dn.total || 0).toFixed(2)}</span>
                                </div>
                                <button
                                  className="glass-button primary-action"
                                  onClick={() => handlePairDeliveryNote(dn.id)}
                                  disabled={pairingInProgress === dn.id}
                                >
                                  {pairingInProgress === dn.id ? 'Pairing...' : 'Pair'}
                                </button>
                              </div>
                            </div>
                          ))}
                      </div>
                    )}
                    
                    {pairingSuggestions.length === 0 && unpairedDeliveryNotes.length === 0 && !loadingPairingData && (
                      <div className="empty-state">
                        <p>No unpaired delivery notes found</p>
                      </div>
                    )}
                  </>
                ) : (
                  <div className="empty-state">
                    <p>All invoices have been paired!</p>
                    <button
                      className="glass-button secondary-action"
                      onClick={handleToggleManualPairingWorkflow}
                    >
                      Exit Pairing Mode
                    </button>
                  </div>
                )}
              </div>
            ) : (
              <>
                <DiscrepancyPanel
                  scope="invoices"
                  items={discrepancies}
                  isLoading={false}
                  lastUpdated={discrepanciesLastUpdated}
                  onItemClick={(item) => {
                    // Helper function to scroll to a section with highlight
                    const scrollToSection = (section: string) => {
                      const el = document.querySelector<HTMLElement>(`[data-section="${section}"]`)
                      if (el) {
                        el.scrollIntoView({ behavior: 'smooth', block: 'start' })
                        el.classList.add('owlin-section-highlight')
                        setTimeout(() => {
                          el.classList.remove('owlin-section-highlight')
                        }, 1200)
                      }
                    }

                    // Handle invoice-specific discrepancies
                    if (item.contextRef?.type === 'invoice' && item.contextRef.id) {
                      const invoiceId = String(item.contextRef.id)
                      
                      // Select the invoice if not already selected
                      if (selectedId !== invoiceId) {
                        setSelectedId(invoiceId)
                        // Wait a bit for the invoice to load, then scroll
                        setTimeout(() => {
                          if (item.focusTarget) {
                            scrollToSection(item.focusTarget)
                          } else {
                            // Default to invoice header if no focusTarget
                            scrollToSection('invoice_header')
                          }
                        }, 300)
                      } else {
                        // Already selected, just scroll
                        if (item.focusTarget) {
                          scrollToSection(item.focusTarget)
                        } else {
                          scrollToSection('invoice_header')
                        }
                      }
                    }
                    // Handle system/venue level discrepancies
                    else if (item.contextRef?.type === 'system' || item.contextRef?.type === 'venue') {
                      // Log filter action for future implementation
                      if (item.actions && item.actions.length > 0) {
                        const action = item.actions[0]
                        if (action.actionType === 'filter' && action.target) {
                          console.log('Filter should be applied:', action.target)
                          // TODO: Implement actual filtering logic
                          // For now, just scroll to top of invoice list
                          const listContainer = document.querySelector('.document-list-container') || 
                                                document.querySelector('[data-section="invoice_list"]')
                          if (listContainer) {
                            listContainer.scrollIntoView({ behavior: 'smooth', block: 'start' })
                          }
                        }
                      }
                    }
                    // Handle action-based navigation
                    else if (item.actions && item.actions.length > 0) {
                      const action = item.actions[0]
                      if (action.actionType === 'navigate' && action.target) {
                        window.location.href = action.target
                      } else if (action.actionType === 'scroll' && action.target) {
                        scrollToSection(action.target)
                      }
                    }
                  }}
                />
                {/* Delivery Notes Cards Section */}
                <DeliveryNotesCardsSection
                  selectedDNId={selectedDNId}
                  onSelectDN={(dnId) => {
                    setSelectedDNId(dnId)
                    // Optionally select the invoice if there's a suggested pairing
                  }}
                  pairingMode={pairingMode}
                  onPairingModeChange={setPairingMode}
                  onPairSuccess={() => {
                    // Refresh invoices and discrepancies after pairing
                    fetchInvoices()
                    setDiscrepancyRefreshTrigger(prev => prev + 1)
                    if (selectedId) {
                      fetchInvoiceDetail(selectedId)
                    }
                  }}
                  refreshTrigger={discrepancyRefreshTrigger}
                />
                {/* Code Assistant Widget - Renders below Delivery Notes */}
                <div style={{ 
                  display: 'flex', 
                  flexDirection: 'column',
                  marginTop: '16px',
                }}>
                  <ChatAssistant compactInputExternal={false} renderAsWidget={true} useSharedState={true} />
                </div>
              </>
            )}
          </div>
        )}

        {/* Modals */}
        <ManualInvoiceOrDNModal
          isOpen={showManualInvoiceOrDNModal}
          onClose={() => {
            setShowManualInvoiceOrDNModal(false)
            setEditingInvoiceId(null)
            setEditingDNId(null)
            setEditMode(null)
          }}
          onSuccess={handleManualInvoiceOrDNSuccess}
          venue={venue}
          editInvoiceId={editingInvoiceId || undefined}
          editDNId={editingDNId || undefined}
          editMode={editMode || undefined}
        />
        {selectedId && (
          <LinkDeliveryNoteModal
            isOpen={showLinkDNModal}
            onClose={() => setShowLinkDNModal(false)}
            onSuccess={handleLinkDNSuccess}
            invoiceId={selectedId}
          />
        )}
        {selectedDNId && (
          <DeliveryNoteDetailModal
            isOpen={showDNDetailModal}
            onClose={() => {
              setShowDNDetailModal(false)
              setSelectedDNId(null)
            }}
            deliveryNoteId={selectedDNId}
          />
        )}
        {selectedId && (
          <OCRDetailsModal
            isOpen={showOCRModal}
            onClose={() => setShowOCRModal(false)}
            invoiceId={selectedId}
          />
        )}
        {selectedSupplierName && (
          <SupplierDetailModal
            isOpen={showSupplierModal}
            onClose={() => {
              setShowSupplierModal(false)
              setSelectedSupplierName(null)
            }}
            supplierName={selectedSupplierName}
          />
        )}

        {/* Hidden file input for button clicks */}
        <input
          ref={fileInputRef}
          type="file"
          multiple
          accept=".pdf,.jpg,.jpeg,.png,.heic"
          onChange={(e) => {
            if (e.target.files) {
              handleFileUpload(e.target.files)
            }
            if (fileInputRef.current) {
              fileInputRef.current.value = ''
            }
          }}
          style={{ display: 'none' }}
        />

        {/* Fixed Submission Footer - Hide when any modal is open */}
        {!(showManualInvoiceOrDNModal || showLinkDNModal || showDNDetailModal || showOCRModal || showSupplierModal) && (
          <div className="submission-bar-fixed">
            <div className="submission-bar-content">
              <div className="submission-bar-text">
                <span className="submission-bar-count">{readyInvoices.length}</span>
                <span className="submission-bar-label">
                  invoice{readyInvoices.length !== 1 ? 's' : ''} ready to submit
                </span>
              </div>
              <div className="submission-bar-actions">
                <button
                  className="submission-button-clear"
                  onClick={handleClearSelection}
                  title="Clear all uploaded invoices that haven't been submitted"
                  disabled={invoices.length === 0 || isSubmitting}
                >
                  Clear all uploaded
                </button>
                <button
                  className="submission-button-submit"
                  onClick={() => handleBatchSubmit(readyInvoices.map((inv) => inv.id))}
                  disabled={readyInvoices.length === 0 || isSubmitting}
                >
                  {isSubmitting ? 'Submitting...' : 'Submit all ready invoices'}
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
    )
  } catch (renderError) {
    console.error('[Invoices] Render error:', renderError)
    return (
      <>
        <div className="invoices-page-new" style={{ padding: '24px' }}>
          <div style={{ 
            background: 'rgba(239, 68, 68, 0.1)',
            border: '1px solid rgba(239, 68, 68, 0.3)',
            borderRadius: '12px',
            padding: '24px',
            color: '#ef4444'
          }}>
            <h2>Render Error</h2>
            <p>The invoices page encountered an error while rendering.</p>
            <pre style={{ background: 'rgba(0, 0, 0, 0.3)', padding: '12px', borderRadius: '8px', overflow: 'auto' }}>
              {renderError instanceof Error ? renderError.message : String(renderError)}
            </pre>
            <button 
              onClick={() => window.location.reload()}
              style={{
                marginTop: '16px',
                padding: '8px 16px',
                background: '#ef4444',
                color: 'white',
                border: 'none',
                borderRadius: '6px',
                cursor: 'pointer',
              }}
            >
              Reload Page
            </button>
          </div>
        </div>
        <ToastContainer toasts={toast.toasts} onClose={toast.removeToast} />
      </>
    )
  }
}

export function Invoices() {
  return <InvoicesContent />
}
