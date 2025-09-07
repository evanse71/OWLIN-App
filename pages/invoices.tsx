import { useState, useEffect, useCallback } from 'react'
import { Button } from '@/components/ui/button'
import { useToast } from '@/hooks/use-toast'
import { 
  getInvoices, 
  getUnmatchedNotes, 
  uploadDocument, 
  getJob,
  getInvoice,
  pairNote, 
  clearAllDocuments, 
  saveDraftDocuments, 
  submitDocuments,
  getUnmatchedDNCount,
  getOpenIssuesCount,
  createInvoice,
  createDeliveryNote
} from '@/lib/api'
import { reprocessInvoice } from '@/lib/api.real'
import type { InvoiceSummary, DeliveryNote, LineItem } from '@/types'
import { 
  Trash2,
  Save,
  Send,
  Plus
} from 'lucide-react'

// Progress semantics
const PROGRESS_STAGES = {
  UPLOAD:    { min: 0,  max: 60, label: 'Uploading…' },
  OCR_PARSE: { min: 60, max: 95, label: 'Processing…' },
  COMPLETE:  { min: 95, max: 100, label: 'Complete' }
};

const clampProgress = (n: number) => Math.max(0, Math.min(100, n ?? 0));

// Import Lovable components
import PageHeader from '@/components/layout/PageHeader'
import UploadArea from '@/components/invoices/UploadArea'
import InvoiceCard from '@/components/invoices/InvoiceCard'
import UnmatchedDeliveryNotesSidebar from '@/components/invoices/UnmatchedDeliveryNotesSidebar'
import CreateInvoiceModal from '@/components/invoices/CreateInvoiceModal'
import CreateDeliveryNoteModal from '@/components/invoices/CreateDeliveryNoteModal'

interface Filters {
  q?: string
  venue?: string
  supplier?: string
  from?: string
  to?: string
  onlyUnmatched?: boolean
  onlyFlagged?: boolean
}

export default function Invoices() {
  const [invoices, setInvoices] = useState<InvoiceSummary[]>([])
  const [deliveryNotes, setDeliveryNotes] = useState<DeliveryNote[]>([])
  const [selectedInvoice, setSelectedInvoice] = useState<InvoiceSummary | null>(null)
  const [isUploading, setIsUploading] = useState(false)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [unmatchedCount, setUnmatchedCount] = useState(0)
  const [issuesCount, setIssuesCount] = useState(0)
  const [itemsById, setItemsById] = useState<Record<string, LineItem[]>>({})
  const [filters, setFilters] = useState<Filters>({})
  const { toast } = useToast()

  const loadData = useCallback(async () => {
    try {
      const [invoicesData, notesData, unmatchedCountData, issuesCountData] = await Promise.all([
        getInvoices(),
        getUnmatchedNotes(),
        getUnmatchedDNCount(),
        getOpenIssuesCount()
      ])
      
      setInvoices(invoicesData)
      setDeliveryNotes(notesData)
      setUnmatchedCount(unmatchedCountData)
      setIssuesCount(issuesCountData)
      
      // Load items for each invoice and merge VAT fields
      const itemsMap: Record<string, LineItem[]> = {}
      for (const invoice of invoicesData) {
        try {
          const invoiceDetail = await getInvoice(invoice.id)
          if (invoiceDetail && Array.isArray(invoiceDetail.line_items)) {
            itemsMap[invoice.id] = invoiceDetail.line_items
            
            // Merge VAT fields from detail into list invoice, never overwrite non-null values
            setInvoices(prev => prev.map(x =>
              x.id === invoice.id
                ? {
                    ...x,
                    ...invoiceDetail,
                    subtotal_p: invoiceDetail.subtotal_p ?? x.subtotal_p ?? null,
                    vat_total_p: invoiceDetail.vat_total_p ?? x.vat_total_p ?? null,
                    total_p: invoiceDetail.total_p ?? x.total_p ?? null,
                    status: 'scanned',
                    processing_progress: null,
                  }
                : x
            ))
          } else {
            // Handle case where line_items is undefined or not an array
            itemsMap[invoice.id] = []
            console.warn(`Invoice ${invoice.id} has no line_items or invalid format:`, invoiceDetail)
          }
        } catch (error) {
          console.error(`Failed to load items for invoice ${invoice.id}:`, error)
          itemsMap[invoice.id] = []
        }
      }
      setItemsById(itemsMap)
    } catch (error) {
      console.error('Failed to load data:', error)
      toast({
        title: "Error",
        description: "Failed to load invoices and delivery notes.",
        variant: "destructive",
      })
    }
  }, [toast])

  useEffect(() => {
    loadData()
  }, [loadData])

  // Apply filters to invoices
  const applyFilters = (invoices: InvoiceSummary[], filters: Filters): InvoiceSummary[] => {
    return invoices.filter(invoice => {
      // Search query
      if (filters.q) {
        const query = filters.q.toLowerCase()
        const matchesNumber = invoice.invoice_number?.toLowerCase().includes(query)
        const matchesSupplier = invoice.supplier_name?.toLowerCase().includes(query)
        if (!matchesNumber && !matchesSupplier) return false
      }

      // Venue filter
      if (filters.venue && invoice.venue !== filters.venue) return false

      // Supplier filter
      if (filters.supplier && invoice.supplier_name !== filters.supplier) return false

      // Date range
      if (filters.from && invoice.invoice_date) {
        const fromDate = new Date(filters.from)
        const invoiceDate = new Date(invoice.invoice_date)
        if (invoiceDate < fromDate) return false
      }

      if (filters.to && invoice.invoice_date) {
        const toDate = new Date(filters.to)
        const invoiceDate = new Date(invoice.invoice_date)
        if (invoiceDate > toDate) return false
      }

      // Only unmatched
      if (filters.onlyUnmatched && invoice.paired) return false

      // Only flagged
      if (filters.onlyFlagged && invoice.issues_count === 0) return false

      return true
    })
  }

  const visibleInvoices = applyFilters(invoices, filters)

  const handleFilterChange = (newFilters: Filters) => {
    setFilters(newFilters)
  }

  const handleFiles = async (files: File[]) => {
    setIsUploading(true)
    
    for (const file of files) {
      try {
        // Upload file and get job ID
        const result = await uploadDocument(file)
        
        // Create optimistic invoice
        const optimisticInvoice: InvoiceSummary = {
          id: `tmp_${result.job_id}`,
          status: 'processing',
          processing_progress: 10,
          invoice_number: null,
          supplier_name: 'Processing document...', // Better placeholder text
          invoice_date: null,
          total_amount: 0,
          confidence: 0,
          paired: 0,
          issues_count: 0,
          venue: ''
        }
        
        // Add to state
        setInvoices(prev => [optimisticInvoice, ...prev])
        
        // Start polling
        const pollJob = async (startTime = Date.now()) => {
          try {
            const job = await getJob(result.job_id)
            
            // Update progress
            setInvoices(prev => prev.map(inv => 
              inv.id === `tmp_${result.job_id}` 
                ? { ...inv, processing_progress: job.progress }
                : inv
            ))
            
            if (job.status === 'done') {
              // Get the real invoice
              const invoiceId = JSON.parse(job.result_json).invoice_id
              const fullInvoice = await getInvoice(invoiceId)
              
              if (fullInvoice) {
                // Replace optimistic with real invoice - handle both 'scanned' and 'parsed' status
                setInvoices(prev => prev.map(inv => 
                  inv.id === `tmp_${result.job_id}` 
                    ? {
                        id: fullInvoice.id,
                        status: fullInvoice.status || 'parsed', // Use actual status from backend
                        processing_progress: null, // Clear processing progress
                        invoice_number: fullInvoice.invoice_number,
                        supplier_name: fullInvoice.supplier_name,
                        invoice_date: fullInvoice.invoice_date,
                        total_amount: fullInvoice.total_amount,
                        confidence: fullInvoice.confidence,
                        paired: fullInvoice.paired,
                        issues_count: fullInvoice.issues_count,
                        venue: fullInvoice.venue
                      }
                    : inv
                ))
                
                // Store line items
                setItemsById(prev => ({
                  ...prev,
                  [fullInvoice.id]: fullInvoice.line_items || []
                }))
                
                toast({
                  title: "Upload successful",
                  description: "Document processed successfully.",
                })
              }
              return
            } else if (job.status === 'failed') {
              throw new Error(job.error || 'Processing failed')
            }
            
            // Check timeout (30 seconds)
            if (Date.now() - startTime > 30000) {
              throw new Error('Processing timeout - job took too long')
            }
            
            // Continue polling
            setTimeout(() => pollJob(startTime), 1000)
          } catch (error) {
            // Remove optimistic invoice on error
            setInvoices(prev => prev.filter(inv => inv.id !== `tmp_${result.job_id}`))
            throw error
          }
        }
        
        setTimeout(pollJob, 1000)
        
      } catch (error) {
        console.error('Upload failed:', error)
        toast({
          title: "Upload failed",
          description: `Failed to process ${file.name}.`,
          variant: "destructive",
        })
      }
    }
    
    setIsUploading(false)
  }

  const handleInvoiceChange = (invoiceId: string, patch: Partial<InvoiceSummary> & { line_items?: LineItem[] }) => {
    // Update invoice in state
    setInvoices(prev => prev.map(inv => 
      inv.id === invoiceId 
        ? { ...inv, ...patch }
        : inv
    ))
    
    // Update line items if provided
    if (patch.line_items) {
      setItemsById(prev => ({
        ...prev,
        [invoiceId]: patch.line_items!
      }))
    }
  }

  const handleInvoiceSelect = (invoice: InvoiceSummary) => {
    setSelectedInvoice(invoice)
  }

  const handleRetry = async (invoiceId: string) => {
    try {
      const { job_id } = await reprocessInvoice(invoiceId);

      // Replace card with an optimistic processing state tied to the new job
      setInvoices(prev => prev.map(inv =>
        inv.id === invoiceId
          ? { ...inv, status: 'processing', processing_progress: 10, error_message: undefined, show_retry: false }
          : inv
      ));

      // Simple polling for the retry job
      const pollRetryJob = async (startTime = Date.now()) => {
        try {
          const job = await getJob(job_id)
          
          // Update progress
          setInvoices(prev => prev.map(inv => 
            inv.id === invoiceId 
              ? { ...inv, processing_progress: job.progress }
              : inv
          ))
          
          if (job.status === 'done') {
            // Get the real invoice
            const invoiceId = JSON.parse(job.result_json).invoice_id
            const fullInvoice = await getInvoice(invoiceId)
            
            if (fullInvoice) {
              // Replace with real invoice
              setInvoices(prev => prev.map(inv => 
                inv.id === invoiceId 
                  ? {
                      ...fullInvoice,
                      status: fullInvoice.status || 'parsed',
                      processing_progress: null,
                      error_message: undefined,
                      show_retry: false
                    }
                  : inv
              ))
              
              // Store line items
              setItemsById(prev => ({
                ...prev,
                [fullInvoice.id]: fullInvoice.line_items || []
              }))
              
              toast({
                title: "Retry successful",
                description: "Document reprocessed successfully.",
              })
            }
            return
          } else if (job.status === 'failed' || job.status === 'timeout') {
            // Update invoice with error state
            setInvoices(prev => prev.map(inv => 
              inv.id === invoiceId 
                ? { 
                    ...inv, 
                    status: job.status, 
                    error_message: job.error || 'Processing failed',
                    show_retry: true 
                  }
                : inv
            ))
            return
          }
          
          // Check timeout (30 seconds)
          if (Date.now() - startTime > 30000) {
            setInvoices(prev => prev.map(inv => 
              inv.id === invoiceId 
                ? { 
                    ...inv, 
                    status: 'timeout', 
                    error_message: 'Processing timeout - job took too long',
                    show_retry: true 
                  }
                : inv
            ))
            return
          }
          
          // Continue polling
          setTimeout(() => pollRetryJob(startTime), 1000)
        } catch (error) {
          // Update invoice with error state
          setInvoices(prev => prev.map(inv => 
            inv.id === invoiceId 
              ? { 
                  ...inv, 
                  status: 'failed', 
                  error_message: 'Retry failed',
                  show_retry: true 
                }
              : inv
          ))
        }
      }
      
      // Start polling
      setTimeout(() => pollRetryJob(), 1000);

      toast({ title: "Retry started", description: "Reprocessing the document…" });
    } catch (e: any) {
      toast({ title: "Retry failed", description: e.message || "Could not restart processing", variant: "destructive" });
    }
  }

  const handleCreateInvoice = (invoice: any) => {
    // Add new invoice to the top of the list
    setInvoices(prev => [invoice, ...prev])
    toast({
      title: "Invoice created",
      description: "New invoice has been created successfully.",
    })
  }

  const handleCreateDeliveryNote = (deliveryNote: any) => {
    // Add new delivery note to the list
    setDeliveryNotes(prev => [deliveryNote, ...prev])
    toast({
      title: "Delivery note created",
      description: "New delivery note has been created successfully.",
    })
  }

  const handlePair = async (noteId: string) => {
    if (!selectedInvoice) return
    
    try {
      const success = await pairNote(selectedInvoice.id, noteId)
      if (success) {
        await loadData() // Refresh data
        toast({
          title: "Paired successfully",
          description: "Delivery note paired with invoice.",
        })
      } else {
        throw new Error('Pairing failed')
      }
    } catch (error) {
      console.error('Pairing failed:', error)
      toast({
        title: "Pairing failed",
        description: "Failed to pair delivery note with invoice.",
        variant: "destructive",
      })
    }
  }

  const handleClearAll = async () => {
    try {
      // Clear non-submitted invoices from state
      setInvoices(prev => prev.filter(inv => inv.status === 'submitted'))
      setItemsById(prev => {
        const newItemsById: Record<string, LineItem[]> = {}
        invoices.forEach(inv => {
          if (inv.status === 'submitted') {
            newItemsById[inv.id] = prev[inv.id] || []
          }
        })
        return newItemsById
      })
      toast({
        title: "Cleared all documents",
        description: "Non-submitted documents have been cleared.",
      })
    } catch (error) {
      console.error('Clear failed:', error)
      toast({
        title: "Clear failed",
        description: "Failed to clear documents.",
        variant: "destructive",
      })
    }
  }

  const handleSaveDraft = async () => {
    try {
      // Save current state to localStorage
      const draftData = {
        invoices,
        itemsById,
        deliveryNotes,
        timestamp: new Date().toISOString()
      }
      localStorage.setItem('owlin:draft', JSON.stringify(draftData))
      toast({
        title: "Draft saved",
        description: "Your work has been saved as a draft.",
      })
    } catch (error) {
      console.error('Save failed:', error)
      toast({
        title: "Save failed",
        description: "Failed to save draft.",
        variant: "destructive",
      })
    }
  }

  const handleSubmitToOwlin = async () => {
    setIsSubmitting(true)
    try {
      const result = await submitDocuments()
      if (result.success) {
        await loadData() // Refresh data
        toast({
          title: "Submitted to Owlin",
          description: "Documents have been submitted successfully.",
        })
      } else {
        throw new Error(result.errors?.join(', ') || 'Submission failed')
      }
    } catch (error) {
      console.error('Submission failed:', error)
      toast({
        title: "Submission failed",
        description: "Failed to submit documents to Owlin.",
        variant: "destructive",
      })
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div className="min-h-screen bg-[var(--ow-bg)]">
      {/* Sticky filters header */}
      <PageHeader 
        onFilterChange={handleFilterChange}
        issuesCount={issuesCount}
        unmatchedCount={unmatchedCount}
      />

      {/* Main content with proper grid layout */}
      <div className="max-w-[1280px] mx-auto px-6 pt-4 pb-24">
        <div className="grid grid-cols-1 lg:grid-cols-[minmax(0,1fr),360px] gap-6">
          <section className="min-w-0">
            <UploadArea onFiles={handleFiles} isUploading={isUploading} />
            
            {/* Invoices List */}
            <div className="space-y-4 mt-6">
              <div className="flex items-center justify-between">
                <h2 className="text-lg font-semibold text-[var(--ow-ink)]">
                  Recent Invoices {filters.q && `(${visibleInvoices.length} results)`}
                </h2>
                <CreateInvoiceModal onCreated={handleCreateInvoice}>
                  <Button size="sm">
                    <Plus className="h-4 w-4 mr-2" />
                    Create Invoice
                  </Button>
                </CreateInvoiceModal>
              </div>
              {visibleInvoices.length === 0 ? (
                <div className="text-center py-8">
                  <p className="text-[var(--ow-ink-dim)]">
                    {invoices.length === 0 
                      ? "No invoices found. Upload a document to get started."
                      : "No invoices match your filters."
                    }
                  </p>
                </div>
              ) : (
                <div className="grid gap-4">
                  {visibleInvoices.map((invoice) => (
                    <InvoiceCard
                      key={invoice.id}
                      invoice={invoice}
                      items={itemsById[invoice.id]}
                      isSelected={selectedInvoice?.id === invoice.id}
                      onClick={() => handleInvoiceSelect(invoice)}
                      onChange={(patch) => handleInvoiceChange(invoice.id, patch)}
                      onRetry={() => handleRetry(invoice.id)}
                    />
                  ))}
                </div>
              )}
            </div>
          </section>

          <aside className="lg:sticky lg:top-[64px] lg:self-start order-first lg:order-last" data-testid="dn-panel">
            {/* Debug info */}
            <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">
              <strong>Debug Info:</strong><br/>
              Delivery Notes: {deliveryNotes.length}<br/>
              Selected Invoice: {selectedInvoice?.id || 'none'}<br/>
              Issues Count: {issuesCount}<br/>
              Unmatched Count: {unmatchedCount}
            </div>
            <UnmatchedDeliveryNotesSidebar
              deliveryNotes={deliveryNotes}
              selectedInvoice={selectedInvoice}
              onPair={handlePair}
              onCreateDeliveryNote={handleCreateDeliveryNote}
            />
          </aside>
        </div>
      </div>

      {/* Action Bar */}
      <div className="fixed bottom-0 left-0 right-0 bg-[var(--ow-card)] border-t border-[var(--ow-border)] p-4 z-10">
        <div className="max-w-[1280px] mx-auto flex items-center justify-between">
          <div className="text-sm text-[var(--ow-ink-dim)]">
            {invoices.length} invoices • {deliveryNotes.length} delivery notes ready
          </div>
          <div className="flex items-center gap-2">
            <Button variant="ghost" onClick={handleClearAll}>
              <Trash2 className="h-4 w-4 mr-2" />
              Clear All
            </Button>
            <Button variant="ghost" onClick={handleSaveDraft}>
              <Save className="h-4 w-4 mr-2" />
              Save Draft
            </Button>
            <Button 
              onClick={handleSubmitToOwlin}
              disabled={isSubmitting}
            >
              <Send className="h-4 w-4 mr-2" />
              {isSubmitting ? 'Submitting...' : 'Submit to Owlin'}
            </Button>
          </div>
        </div>
      </div>
    </div>
  )
} 