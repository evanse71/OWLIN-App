// LEGACY: Experimental invoice page. Not wired into main navigation.
// Uses older data shapes. Do not rely on this for production.
import { useState, useEffect, useCallback } from 'react'
import { InvoicesHeader, type ViewMode, type DateRange } from '../components/invoices/InvoicesHeader'
import { DocumentList, type InvoiceListItem } from '../components/invoices/DocumentList'
import { DocumentDetailPanel, type InvoiceDetail } from '../components/invoices/DocumentDetailPanel'
import {
  IssuesActionsPanel,
  type Issue,
  type DeliveryNoteInfo,
  type DocumentMetadata,
} from '../components/invoices/IssuesActionsPanel'
import { API_BASE_URL } from '../lib/config'
import { normalizeInvoicesPayload } from '../lib/api'
import './InvoicesNew.css'

export function Invoices() {
  const [viewMode, setViewMode] = useState<ViewMode>('scanned')
  const [venue, setVenue] = useState('Waterloo')
  const [dateRange, setDateRange] = useState<DateRange>('month')
  const [searchQuery, setSearchQuery] = useState('')
  const [sortBy, setSortBy] = useState<'date' | 'supplier' | 'value'>('date')
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [invoices, setInvoices] = useState<InvoiceListItem[]>([])
  const [selectedInvoice, setSelectedInvoice] = useState<InvoiceDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Fetch invoices from backend
  const fetchInvoices = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const params = new URLSearchParams()
      if (viewMode === 'manual') {
        // Use manual entry endpoint
        params.append('status', 'ready')
      }
      params.append('sort', sortBy)
      params.append('limit', '100')

      const endpoint =
        viewMode === 'manual'
          ? `${API_BASE_URL}/api/manual/invoices`
          : `${API_BASE_URL}/api/invoices`

      const response = await fetch(`${endpoint}?${params.toString()}`)
      if (!response.ok) {
        throw new Error(`Failed to fetch invoices: ${response.status}`)
      }

      const data = await response.json()
      const normalized = normalizeInvoicesPayload(data)

      const invoiceList: InvoiceListItem[] = (normalized.invoices || []).map((inv: any) => ({
        id: String(inv.id || inv.docId || Date.now()),
        invoiceNumber: inv.invoiceNumber,
        supplier: inv.supplier || inv.supplierName || 'Unknown Supplier',
        date: inv.date || inv.invoiceDate || inv.docDate,
        value: inv.value || inv.total || inv.totalValue || 0,
        venue: inv.venue || 'Main Restaurant',
        status: viewMode === 'manual' ? 'manual' : 'scanned',
        matched: inv.paired || inv.matched || false,
        flagged: inv.flagged || (inv.issuesCount && inv.issuesCount > 0) || false,
        pending: inv.status === 'pending',
        issuesCount: inv.issuesCount || 0,
        hasDeliveryNote: !!inv.deliveryNoteId,
        confidence: inv.confidence || inv.ocrConfidence,
      }))

      setInvoices(invoiceList)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load invoices')
      console.error('Error fetching invoices:', err)
    } finally {
      setLoading(false)
    }
  }, [viewMode, sortBy])

  // Fetch single invoice details
  const fetchInvoiceDetail = useCallback(async (id: string) => {
    try {
      const endpoint =
        viewMode === 'manual'
          ? `${API_BASE_URL}/api/manual/invoices/${id}`
          : `${API_BASE_URL}/api/invoices/${id}`

      const response = await fetch(endpoint)
      if (!response.ok) {
        throw new Error(`Failed to fetch invoice: ${response.status}`)
      }

      const data = await response.json()
      const normalized = normalizeInvoicesPayload(data)
      const inv = normalized.invoice || normalized

      // Fetch delivery note if linked
      let deliveryNote: DeliveryNoteInfo | undefined
      if (inv.deliveryNoteId) {
        // TODO: Fetch delivery note details
        const dnId = String(inv.deliveryNoteId)
        deliveryNote = {
          id: dnId,
          noteNumber: `DN-${dnId.slice(0, 8)}`,
        }
      }

      const invoiceDetail: InvoiceDetail = {
        id: String(inv.id || inv.docId),
        invoiceNumber: inv.invoiceNumber,
        supplier: inv.supplier || inv.supplierName || 'Unknown Supplier',
        date: inv.date || inv.invoiceDate || inv.docDate,
        venue: inv.venue || 'Main Restaurant',
        value: inv.value || inv.total || inv.totalValue || 0,
        subtotal: inv.subtotal,
        vat: inv.vat,
        status: viewMode === 'manual' ? 'manual' : 'scanned',
        matched: inv.paired || inv.matched || false,
        flagged: inv.flagged || (inv.issuesCount && inv.issuesCount > 0) || false,
        deliveryNote,
        lineItems: inv.lineItems || [],
        sourceFilename: inv.filename || inv.sourceFilename,
      }

      setSelectedInvoice(invoiceDetail)
    } catch (err) {
      console.error('Error fetching invoice detail:', err)
      setSelectedInvoice(null)
    }
  }, [viewMode])

  // Load invoices on mount and when filters change
  useEffect(() => {
    fetchInvoices()
  }, [fetchInvoices])

  // Fetch detail when selection changes
  useEffect(() => {
    if (selectedId) {
      fetchInvoiceDetail(selectedId)
    } else {
      setSelectedInvoice(null)
    }
  }, [selectedId, fetchInvoiceDetail])

  // Filter invoices by search query
  const filteredInvoices = invoices.filter((inv) => {
    if (!searchQuery) return true
    const query = searchQuery.toLowerCase()
    return (
      inv.supplier?.toLowerCase().includes(query) ||
      inv.invoiceNumber?.toLowerCase().includes(query) ||
      String(inv.id).toLowerCase().includes(query)
    )
  })

  // Generate issues from invoice data (mock for now)
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
          const invQty = item.qty || item.quantity || 0
          const dnQty = dnItem.qty || dnItem.quantity || 0
          if (dnQty < invQty) {
            const itemDesc = item.description || item.item || 'Unknown item'
            issues.push({
              id: `short-${itemDesc}-${Date.now()}`,
              type: 'short',
              severity: dnQty < invQty * 0.5 ? 'critical' : 'review',
              item: itemDesc,
              description: `Short delivery: invoiced ${invQty}, delivered ${dnQty}`,
              suggestedCredit: (invQty - dnQty) * (item.price || item.unit_price || 0),
            })
          }
        }
      })
    }

    return issues
  }

  const issues = generateIssues(selectedInvoice)

  // Generate metadata
  const metadata: DocumentMetadata | undefined = selectedInvoice
    ? {
        source: selectedInvoice.status === 'manual' ? 'manual' : 'upload',
        filename: selectedInvoice.sourceFilename,
        // TODO: Add real metadata from backend
      }
    : undefined

  const handleUploadClick = () => {
    // TODO: Open upload dialog
    console.log('Upload clicked')
  }

  const handleNewManualInvoice = () => {
    // TODO: Open manual invoice form
    console.log('New manual invoice')
  }

  const handleNewManualDN = () => {
    // TODO: Open manual DN form
    console.log('New manual DN')
  }

  return (
    <div className="invoices-page-new">
      <InvoicesHeader
        viewMode={viewMode}
        onViewModeChange={setViewMode}
        venue={venue}
        onVenueChange={setVenue}
        dateRange={dateRange}
        onDateRangeChange={setDateRange}
        searchQuery={searchQuery}
        onSearchChange={setSearchQuery}
        onUploadClick={handleUploadClick}
        onNewManualInvoice={handleNewManualInvoice}
        onNewManualDN={handleNewManualDN}
      />

      <div className="invoices-main-new">
        {/* Left Column - Document List */}
        <DocumentList
          invoices={filteredInvoices}
          selectedId={selectedId}
          onSelect={setSelectedId}
          sortBy={sortBy}
          onSortChange={setSortBy}
          emptyState={
            loading
              ? undefined
              : {
                  title:
                    viewMode === 'scanned'
                      ? 'No scanned documents yet.'
                      : 'No manual invoices yet.',
                  description:
                    viewMode === 'scanned'
                      ? 'Upload invoices and delivery notes to start matching.'
                      : 'Create manual invoices to get started.',
                  actionLabel: viewMode === 'scanned' ? 'Upload documents' : 'Create manual invoice',
                  onAction: viewMode === 'scanned' ? handleUploadClick : handleNewManualInvoice,
                }
          }
        />

        {/* Middle Column - Document Detail */}
        <DocumentDetailPanel
          invoice={selectedInvoice}
          onLinkDeliveryNote={() => console.log('Link DN')}
          onCreateDeliveryNote={handleNewManualDN}
          onChangeDeliveryNote={() => console.log('Change DN')}
        />

        {/* Right Column - Issues & Actions */}
        <IssuesActionsPanel
          issues={issues}
          deliveryNote={selectedInvoice?.deliveryNote}
          metadata={metadata}
          onLinkDeliveryNote={() => console.log('Link DN')}
          onCreateDeliveryNote={handleNewManualDN}
          onViewDeliveryNote={() => console.log('View DN')}
          onMarkReviewed={() => console.log('Mark reviewed')}
          onEscalateToSupplier={() => console.log('Escalate')}
          showOCRDebug={false}
        />
      </div>
    </div>
  )
}

