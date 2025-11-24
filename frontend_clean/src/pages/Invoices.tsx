import { useState, useCallback, useRef, useEffect } from 'react'
import { InvoiceDebugPanel } from '../components/InvoiceDebugPanel'
import { uploadFile, type InvoiceMetadata, type UploadProgress } from '../lib/upload'
import {
  isDevModeEnabled,
  toggleDevMode,
  getSelectedIdFromHash,
  setHashForId,
} from '../lib/ui_state'
import { InvoiceCard } from '../components/invoices/InvoiceCardReceipt'
import { InvoiceDetailPanel } from '../components/invoices/InvoiceDetailPanelNew'
import { HealthStatusIndicator } from '../components/invoices/HealthStatusIndicator'
import { FilterDrawer } from '../components/invoices/FilterDrawer'
import { SearchBar } from '../components/invoices/SearchBar'
import { SingleUploadBox } from '../components/invoices/SingleUploadBox'
import { StatsWidget } from '../components/invoices/StatsWidget'
import { DeliveryNotesBox } from '../components/invoices/DeliveryNotesBox'
import { ChatAssistant } from '../components/ChatAssistant'
import './Invoices.css'

export interface FileItem {
  id: string
  file: File
  status: 'pending' | 'uploading' | 'scanned' | 'error' | 'submitted'
  progress: number
  metadata?: InvoiceMetadata
  error?: string
  uploadStartTime?: number
  uploadEndTime?: number
  uploadBytes?: number
  submitted?: boolean
}

export interface RequestLogEntry {
  method: string
  url: string
  status: number
  duration: number
  timestamp: number
}


export function Invoices() {
  const [files, setFiles] = useState<FileItem[]>([])
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [devMode, setDevMode] = useState(isDevModeEnabled())
  const [requestLog, setRequestLog] = useState<RequestLogEntry[]>([])
  const [searchQuery, setSearchQuery] = useState('')
  const [showFilters, setShowFilters] = useState(false)
  const [activeFilters, setActiveFilters] = useState<Set<string>>(new Set())

  const fileInputRef = useRef<HTMLInputElement>(null)
  const deliveryNoteInputRef = useRef<HTMLInputElement>(null)

  // Generate stable ID
  const generateId = useCallback((file: File, metadata?: InvoiceMetadata): string => {
    if (metadata?.id !== undefined) {
      return String(metadata.id)
    }
    return `${file.name}-${file.size}-${Date.now()}`
  }, [])

  // Sync hash on selection change
  useEffect(() => {
    if (selectedId) {
      setHashForId(selectedId)
    } else {
      setHashForId(null)
    }
  }, [selectedId])

  // Load selection from hash on mount
  useEffect(() => {
    const hashId = getSelectedIdFromHash()
    if (hashId) {
      const exists = files.some((f) => f.id === hashId)
      if (exists) {
        setSelectedId(hashId)
      }
    }
  }, [])

  // Sync dev mode
  useEffect(() => {
    const checkDevMode = () => {
      setDevMode(isDevModeEnabled())
    }
    checkDevMode()
    window.addEventListener('popstate', checkDevMode)
    return () => window.removeEventListener('popstate', checkDevMode)
  }, [])

  // Filter files based on search
  const filteredFiles = files.filter((file) => {
    if (searchQuery) {
      const query = searchQuery.toLowerCase()
      const matchesName = file.file.name.toLowerCase().includes(query)
      const matchesSupplier = file.metadata?.supplier?.toLowerCase().includes(query)
      if (!matchesName && !matchesSupplier) return false
    }
    return true
  })

  const handleUpload = useCallback(async (fileList: FileList, isDeliveryNote: boolean = false) => {
    const fileArray = Array.from(fileList)
    
    for (const file of fileArray) {
      const newItem: FileItem = {
        id: generateId(file),
        file,
        status: 'pending' as const,
        progress: 0,
        metadata: { isDeliveryNote },
      }

      setFiles((prev) => [...prev, newItem])

      // Auto-upload immediately
      const startTime = Date.now()
      setFiles((prev) =>
        prev.map((f) =>
          f.id === newItem.id
            ? { ...f, status: 'uploading' as const, progress: 0, uploadStartTime: startTime, metadata: { ...f.metadata, isDeliveryNote } }
            : f
        )
      )

      try {
        const result = await uploadFile(file, {
          onProgress: (progress: UploadProgress) => {
            setFiles((prev) =>
              prev.map((f) =>
                f.id === newItem.id ? { ...f, progress: progress.percentage } : f
              )
            )
          },
          onComplete: (completeMetadata: InvoiceMetadata) => {
            setFiles((prev) =>
              prev.map((f) =>
                f.id === newItem.id
                  ? { ...f, metadata: { ...completeMetadata, isDeliveryNote }, status: 'scanned' as const }
                  : f
              )
            )
          },
        })

        const endTime = Date.now()
        const newId = result.metadata?.id ? String(result.metadata.id) : newItem.id

        setFiles((prev) =>
          prev.map((f) =>
            f.id === newItem.id
              ? {
                  ...f,
                  id: newId,
                  status: result.success ? ('scanned' as const) : ('error' as const),
                  metadata: result.metadata ? { ...result.metadata, isDeliveryNote } : { isDeliveryNote },
                  error: result.error,
                  progress: result.success ? 100 : f.progress,
                  uploadEndTime: endTime,
                  uploadBytes: file.size,
                }
              : f
          )
        )
      } catch (error) {
        setFiles((prev) =>
          prev.map((f) =>
            f.id === newItem.id
              ? {
                  ...f,
                  status: 'error' as const,
                  error: error instanceof Error ? error.message : 'Unknown error',
                }
              : f
          )
        )
      }
    }
  }, [generateId])

  const handleFileInput = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      if (e.target.files) {
        handleUpload(e.target.files, false)
      }
      if (fileInputRef.current) {
        fileInputRef.current.value = ''
      }
    },
    [handleUpload]
  )

  const handleDeliveryNoteInput = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      if (e.target.files) {
        handleUpload(e.target.files, true)
      }
      if (deliveryNoteInputRef.current) {
        deliveryNoteInputRef.current.value = ''
      }
    },
    [handleUpload]
  )

  const handleCardClick = useCallback((id: string) => {
    // Toggle selection - if clicking the same card, deselect it
    setSelectedId(id === selectedId ? null : id)
  }, [selectedId])

  const handleCloseDetail = useCallback(() => {
    setSelectedId(null)
  }, [])

  // Separate invoices and delivery notes
  const invoices = files.filter((f) => !f.metadata?.isDeliveryNote)
  const deliveryNotes = files.filter((f) => f.metadata?.isDeliveryNote)

  const handleClearUploaded = useCallback(() => {
    setFiles((prev) => prev.filter((f) => f.status !== 'pending' && f.status !== 'uploading' && !f.submitted))
  }, [])

  const handleSubmitInvoices = useCallback(() => {
    const pendingFiles = files.filter((f) => f.status === 'scanned' && !f.submitted)
    setFiles((prev) =>
      prev.map((f) =>
        pendingFiles.some(pf => pf.id === f.id)
          ? { ...f, submitted: true, status: 'submitted' as const }
          : f
      )
    )
    // Show toast notification
    console.log(`${pendingFiles.length} invoices submitted successfully.`)
  }, [files])

  const pendingCount = files.filter((f) => f.status === 'pending' || f.status === 'uploading').length
  const submittedCount = files.filter((f) => f.submitted).length
  const totalCount = files.length

  const selectedInvoice = selectedId ? files.find((f) => f.id === selectedId) : null

  return (
    <div className="invoices-page">
      {/* Fixed Header */}
      <header className="invoices-header">
        <div className="invoices-header-content">
          <h1 className="invoices-page-title">Invoices</h1>
          <div className="invoices-header-utils">
            <HealthStatusIndicator />
            <button
              className="invoices-filter-button"
              onClick={() => setShowFilters(!showFilters)}
              aria-label="Toggle filters"
            >
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <polygon points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3" />
              </svg>
            </button>
            <SearchBar value={searchQuery} onChange={setSearchQuery} />
            {/* Chat Assistant embedded in header */}
            <div className="invoices-header-chat">
              <ChatAssistant />
            </div>
          </div>
        </div>
        {showFilters && (
          <FilterDrawer
            activeFilters={activeFilters}
            onFilterChange={setActiveFilters}
            onClose={() => setShowFilters(false)}
          />
        )}
      </header>

      {/* Upload Box - Below Header */}
      <div className="invoices-upload-section">
        <SingleUploadBox
          onUpload={(files) => handleUpload(files, false)}
          fileInputRef={fileInputRef}
          onFileInput={handleFileInput}
        />
      </div>

      {/* Main Content - Two Column Layout */}
      <div className="invoices-main">
        {/* Left Column - Invoice Cards */}
        <div className="invoices-list-panel">
          {invoices.length > 0 && (
            <div className="invoices-stats-section">
              <StatsWidget files={invoices} />
            </div>
          )}
          <div className="invoices-list-scrollable">
            {filteredFiles.filter(f => !f.metadata?.isDeliveryNote).length === 0 ? (
              <div className="invoices-list-empty">
                <p>No invoices uploaded yet</p>
                <p className="invoices-list-empty-hint">Upload invoices using the box above</p>
              </div>
            ) : (
              filteredFiles
                .filter(f => !f.metadata?.isDeliveryNote)
                .map((fileItem) => (
                  <InvoiceCard
                    key={fileItem.id}
                    invoice={fileItem}
                    isSelected={selectedId === fileItem.id}
                    onClick={() => handleCardClick(fileItem.id)}
                  />
                ))
            )}
          </div>
        </div>

        {/* Right Column - Delivery Notes Box or Invoice Detail */}
        <div className="invoices-delivery-notes-panel">
          {selectedInvoice ? (
            <div className="invoices-detail-wrapper">
              <div className="invoices-detail-header-actions">
                <button
                  className="invoices-detail-close"
                  onClick={handleCloseDetail}
                  aria-label="Close detail view"
                >
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <line x1="18" y1="6" x2="6" y2="18" />
                    <line x1="6" y1="6" x2="18" y2="18" />
                  </svg>
                </button>
              </div>
              <InvoiceDetailPanel
                invoice={selectedInvoice}
                requestLog={requestLog}
                devMode={devMode}
              />
            </div>
          ) : (
            <DeliveryNotesBox
              onUpload={(files) => handleUpload(files, true)}
              onFileInput={handleDeliveryNoteInput}
              deliveryNotes={deliveryNotes}
            />
          )}
        </div>
      </div>

      {/* Fixed Footer */}
      <footer className="invoices-footer">
        <div className="invoices-footer-content">
          <div className="invoices-footer-left">
            <span className="invoices-footer-summary">
              {totalCount > 0
                ? `${totalCount} invoice${totalCount !== 1 ? 's' : ''} uploaded`
                : 'No pending invoices'}
              {submittedCount > 0 && ` · ${submittedCount} submitted`}
            </span>
            {totalCount > 0 && (
              <span className="invoices-footer-timestamp">
                Last save: {new Date().toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' })}
              </span>
            )}
          </div>
          <div className="invoices-footer-right">
            <button
              className="invoices-footer-button invoices-footer-button-secondary"
              onClick={handleClearUploaded}
              disabled={pendingCount === 0}
              title="This will only clear unsubmitted invoices."
            >
              Clear Uploaded
            </button>
            <button
              className="invoices-footer-button invoices-footer-button-primary"
              onClick={handleSubmitInvoices}
              disabled={files.filter((f) => f.status === 'scanned' && !f.submitted).length === 0}
              title="Once submitted, these invoices can't be cleared."
            >
              Submit Invoices
            </button>
          </div>
        </div>
      </footer>
    </div>
  )
}
