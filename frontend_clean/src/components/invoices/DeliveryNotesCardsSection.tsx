import { useState, useEffect, useMemo } from 'react'
import { Package, Loader2, Trash2, AlertTriangle } from 'lucide-react'
import { DeliveryNoteCard, type DeliveryNoteListItem } from './DeliveryNoteCard'
import { fetchUnmatchedDeliveryNotes, fetchInvoiceSuggestionsForDN, fetchDeliveryNoteDetails, linkDeliveryNoteToInvoice, normalizeInvoice, fetchPairingSuggestions, validatePair, deleteDeliveryNotes, fetchDeliveryNotes, fetchPairedInvoicesForDeliveryNote, type UnmatchedDeliveryNote } from '../../lib/api'
import { PairingConfirmationModal, type PairingConfirmationData } from './PairingConfirmationModal'
import { PairingPreviewModal } from './PairingPreviewModal'
import { ClearDeliveryNotesModal } from './ClearDeliveryNotesModal'
import { useToast } from '../common/Toast'
import { API_BASE_URL } from '../../lib/config'
import './DeliveryNotesCardsSection.css'

interface DeliveryNotesCardsSectionProps {
  selectedDNId?: string | null
  onSelectDN: (dnId: string) => void
  pairingMode: 'automatic' | 'manual'
  onPairingModeChange: (mode: 'automatic' | 'manual') => void
  onPairSuccess?: () => void
  refreshTrigger?: number
}

export function DeliveryNotesCardsSection({
  selectedDNId,
  onSelectDN,
  pairingMode,
  onPairingModeChange,
  onPairSuccess,
  refreshTrigger,
}: DeliveryNotesCardsSectionProps) {
  const toast = useToast()
  const [deliveryNotes, setDeliveryNotes] = useState<UnmatchedDeliveryNote[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [pairingSuggestions, setPairingSuggestions] = useState<Map<string, any>>(new Map())
  const [pairedStatusMap, setPairedStatusMap] = useState<Map<string, boolean>>(new Map())
  const [confirmationData, setConfirmationData] = useState<PairingConfirmationData | null>(null)
  const [showConfirmationModal, setShowConfirmationModal] = useState(false)
  const [pairingLoading, setPairingLoading] = useState(false)
  const [previewModalOpen, setPreviewModalOpen] = useState(false)
  const [previewData, setPreviewData] = useState<{ invoiceId: string; deliveryNoteId: string; validation: any } | null>(null)
  const [showClearAllModal, setShowClearAllModal] = useState(false)
  const [deletingDNs, setDeletingDNs] = useState(false)

  // Function to load delivery notes (can be called after deletion to refresh)
  const loadDeliveryNotes = async () => {
    setLoading(true)
    setError(null)
    try {
      // Fetch ALL delivery notes (not just unmatched)
      console.log('[DEBUG] DeliveryNotesCardsSection: Fetching delivery notes...')
      const allDNs = await fetchDeliveryNotes()
      console.log('[DEBUG] DeliveryNotesCardsSection: Fetched', allDNs?.length || 0, 'delivery notes', allDNs)
      
      // If no delivery notes exist, that's fine - just set empty array and continue
      // This is not an error, just an empty state
      if (!allDNs || allDNs.length === 0) {
        setDeliveryNotes([])
        setPairedStatusMap(new Map())
        setPairingSuggestions(new Map())
        setLoading(false)
        return
      }
      
      // Deduplicate by ID and filter out invalid entries
      const seenIds = new Set<string>()
      const uniqueDNs = allDNs.filter((dn: any) => {
        const id = dn.id || dn.docId || ''
        // Filter out entries with empty IDs
        if (!id || id.trim() === '') {
          return false
        }
        // Filter out duplicates
        if (seenIds.has(id)) {
          return false
        }
        seenIds.add(id)
        return true
      })
      
      // Convert to UnmatchedDeliveryNote format for compatibility
      const dns: UnmatchedDeliveryNote[] = uniqueDNs.map((dn: any) => {
        // Get supplier - prioritize actual supplier value, only use 'Unknown Supplier' if truly missing
        const supplierValue = dn.supplier || dn.supplierName || dn.supplier_name
        const mapped = {
          id: dn.id || dn.docId || '',
          noteNumber: dn.deliveryNo || dn.delivery_no || dn.deliveryNoteNumber || dn.noteNumber || dn.note_number || '',
          supplier: supplierValue && supplierValue !== 'Unknown Supplier' ? supplierValue : (supplierValue || 'Unknown Supplier'),
          date: dn.docDate || dn.doc_date || dn.date || '',
          total: dn.total || 0,
          venue: dn.venue || dn.venueId || undefined, // Include venue if available
          deliveryNo: dn.deliveryNo || dn.delivery_no || dn.deliveryNoteNumber || dn.noteNumber || '',
          docDate: dn.docDate || dn.doc_date || dn.date || '',
        }
        console.log('[DEBUG] DeliveryNotesCardsSection: Mapped DN', {
          id: mapped.id,
          supplier: mapped.supplier,
          noteNumber: mapped.noteNumber,
          date: mapped.date,
          venue: mapped.venue,
          raw: dn
        })
        return mapped
      }).filter(dn => dn.id && dn.id.trim() !== '') // Final filter to ensure no empty IDs
      
      // Check pairing status for each delivery note (using the normalized ID)
      // Deduplicate by ID first to avoid checking the same DN twice
      const uniqueDnsById = new Map<string, UnmatchedDeliveryNote>()
      for (const dn of dns) {
        if (dn.id && dn.id.trim() !== '') {
          // If we already have this ID, keep the one with more complete data
          const existing = uniqueDnsById.get(dn.id)
          if (!existing || (!existing.supplier && dn.supplier) || (!existing.noteNumber && dn.noteNumber)) {
            uniqueDnsById.set(dn.id, dn)
          }
        }
      }
      
      const finalDns = Array.from(uniqueDnsById.values())
      const pairedMap = new Map<string, boolean>()
      for (const dn of finalDns) {
        if (!dn.id) continue
        try {
          const pairedInvoices = await fetchPairedInvoicesForDeliveryNote(dn.id)
          pairedMap.set(dn.id, pairedInvoices.length > 0)
        } catch (err) {
          console.warn(`Failed to check pairing status for DN ${dn.id}:`, err)
          pairedMap.set(dn.id, false)
        }
      }
      setPairedStatusMap(pairedMap)
      
      console.log('[DEBUG] DeliveryNotesCardsSection: Setting', finalDns.length, 'delivery notes to state')
      setDeliveryNotes(finalDns)
      
      // Fetch pairing suggestions for each DN (use finalDns to avoid duplicates)
      const suggestionsMap = new Map()
      for (const dn of finalDns) {
        if (!dn.id) continue
        try {
          const suggestions = await fetchInvoiceSuggestionsForDN(dn.id)
          if (suggestions.suggestions && suggestions.suggestions.length > 0) {
            suggestionsMap.set(dn.id, suggestions.suggestions[0]) // Get the best suggestion
          }
        } catch (err) {
          console.warn(`Failed to fetch suggestions for DN ${dn.id}:`, err)
        }
      }
      setPairingSuggestions(suggestionsMap)
    } catch (err) {
      // Only set error for actual failures (network errors, 500s, etc.)
      // Empty arrays are handled above and are not errors
      const errorMessage = err instanceof Error ? err.message : 'Unknown error occurred'
      console.error('Failed to fetch delivery notes:', err)
      setError(`Failed to load delivery notes: ${errorMessage}`)
      // Only show toast for actual errors, not for empty states
      toast.error(`Failed to load delivery notes: ${errorMessage}`)
    } finally {
      setLoading(false)
    }
  }

  // Fetch delivery notes on mount and when refreshTrigger changes
  useEffect(() => {
    loadDeliveryNotes()
  }, [refreshTrigger])

  // Transform delivery notes to list items with pairing info
  const deliveryNoteListItems = useMemo((): DeliveryNoteListItem[] => {
    return deliveryNotes.map((dn) => {
      const suggestion = pairingSuggestions.get(dn.id)
      const confidence = suggestion?.confidence || suggestion?.similarity
      const isPaired = pairedStatusMap.get(dn.id) || false
      
      // Determine pairing type based on mode and confidence
      // In automatic mode with high confidence, show as "pending_confirmation" instead of "automatic"
      let pairingType: 'automatic' | 'manual' | 'suggested' | 'pending_confirmation' = 'suggested'
      if (pairingMode === 'automatic' && confidence && confidence >= 0.9) {
        pairingType = 'pending_confirmation' // Changed from 'automatic' to require confirmation
      } else if (pairingMode === 'manual') {
        pairingType = 'manual'
      }

      return {
        id: dn.id,
        noteNumber: dn.noteNumber || dn.deliveryNo || `DN-${dn.id.slice(0, 8)}`,
        supplier: dn.supplier,
        date: dn.date || dn.docDate,
        total: dn.total,
        venue: dn.venue, // Include venue if available
        isPaired,
        recommendedInvoice: suggestion
          ? {
              id: suggestion.invoiceId || suggestion.id,
              invoiceNumber: suggestion.invoiceNumber,
              confidence: confidence,
            }
          : undefined,
        pairingType,
      }
    })
  }, [deliveryNotes, pairingSuggestions, pairingMode, pairedStatusMap])

  // Filter based on pairing mode
  // Note: We now show ALL delivery notes (paired and unpaired) in manual mode
  const filteredDeliveryNotes = useMemo(() => {
    if (pairingMode === 'automatic') {
      // Show only high-confidence pairings in automatic mode (but still show paired ones)
      return deliveryNoteListItems.filter((dn) => {
        const confidence = dn.recommendedInvoice?.confidence
        return confidence !== undefined && confidence >= 0.9
      })
    } else {
      // Show all in manual mode (including paired delivery notes)
      return deliveryNoteListItems
    }
  }, [deliveryNoteListItems, pairingMode])

  // Handle delivery note selection - show confirmation for automatic pairings
  const handleDNClick = async (dn: DeliveryNoteListItem) => {
    // If it's a pending confirmation pairing, show confirmation modal
    if (dn.pairingType === 'pending_confirmation' && dn.recommendedInvoice) {
      await showPairingConfirmation(dn)
    } else {
      // Otherwise, just select the DN normally
      onSelectDN(dn.id)
    }
  }

  const showPairingConfirmation = async (dn: DeliveryNoteListItem) => {
    if (!dn.recommendedInvoice) return

    setPairingLoading(true)
    setShowConfirmationModal(false) // Hide any existing modal
    try {
      // Fetch delivery note details
      const dnDetails = await fetchDeliveryNoteDetails(dn.id)
      
      // Fetch invoice details
      let invoiceResponse = await fetch(`${API_BASE_URL}/api/invoices/${dn.recommendedInvoice.id}`)
      let isManual = false
      
      if (!invoiceResponse.ok) {
        invoiceResponse = await fetch(`${API_BASE_URL}/api/manual/invoices/${dn.recommendedInvoice.id}`)
        isManual = true
      }

      if (!invoiceResponse.ok) {
        throw new Error(`Failed to fetch invoice details: ${invoiceResponse.status} ${invoiceResponse.statusText}`)
      }

      const invoiceData = await invoiceResponse.json()
      const rawInvoice = invoiceData.invoice || invoiceData
      const inv = normalizeInvoice(rawInvoice)

      // Get suggestion details for quantity differences
      const suggestion = pairingSuggestions.get(dn.id)
      let quantityDifferences = suggestion?.quantityDifferences || []
      let hasQuantityMismatch = suggestion?.hasQuantityMismatch || false

      // If quantity differences not available, try to fetch them
      if (quantityDifferences.length === 0 && inv.id) {
        try {
          const suggestionsResponse = await fetchPairingSuggestions(String(inv.id))
          const matchingSuggestion = suggestionsResponse.suggestions?.find(
            s => s.deliveryNoteId === dn.id
          )
          if (matchingSuggestion) {
            quantityDifferences = matchingSuggestion.quantityDifferences || []
            hasQuantityMismatch = matchingSuggestion.hasQuantityMismatch || false
          }
        } catch (err) {
          console.warn('Failed to fetch quantity differences:', err)
          // Continue with empty differences
        }
      }

      // Build confirmation data
      const confirmation: PairingConfirmationData = {
        invoiceId: String(inv.id || inv.docId),
        invoiceNumber: String(inv.id || inv.docId || dn.recommendedInvoice.id || ''),
        invoiceSupplier: inv.supplier || 'Unknown Supplier',
        invoiceDate: inv.invoiceDate || '',
        invoiceTotal: inv.totalValue || 0,
        invoiceLineItems: inv.lineItems || [],
        deliveryNoteId: dn.id,
        deliveryNoteNumber: dn.noteNumber || dnDetails.noteNumber || `DN-${dn.id.slice(0, 8)}`,
        deliveryNoteSupplier: dn.supplier || dnDetails.supplier || 'Unknown Supplier',
        deliveryNoteDate: dn.date || dnDetails.date || '',
        deliveryNoteTotal: dn.total || dnDetails.total || 0,
        deliveryNoteLineItems: dnDetails.lineItems || [],
        confidence: dn.recommendedInvoice.confidence || 0.9,
        reason: suggestion?.reason || `High confidence match (${Math.round((dn.recommendedInvoice.confidence || 0.9) * 100)}%)`,
        quantityDifferences,
        hasQuantityMismatch,
      }

      setConfirmationData(confirmation)
      setShowConfirmationModal(true)
    } catch (err) {
      console.error('Failed to load pairing confirmation data:', err)
      const errorMessage = err instanceof Error ? err.message : 'Unknown error'
      toast.error(`Failed to load pairing confirmation: ${errorMessage}`)
      // Fall back to normal selection if confirmation fails
      onSelectDN(dn.id)
    } finally {
      setPairingLoading(false)
    }
  }

  const handleConfirmPairing = async () => {
    if (!confirmationData) return

    setPairingLoading(true)
    try {
      // Validate before pairing
      const validation = await validatePair(confirmationData.invoiceId, confirmationData.deliveryNoteId)
      
      // If validation shows warnings or low match score, show preview modal
      if (!validation.isValid || validation.matchScore < 0.8 || validation.warnings.length > 0) {
        setPreviewData({
          invoiceId: confirmationData.invoiceId,
          deliveryNoteId: confirmationData.deliveryNoteId,
          validation
        })
        setPreviewModalOpen(true)
        setShowConfirmationModal(false)
        setPairingLoading(false)
        return
      }
      
      // If validation passes, proceed with pairing directly
      await linkDeliveryNoteToInvoice(confirmationData.invoiceId, confirmationData.deliveryNoteId)
      setShowConfirmationModal(false)
      setConfirmationData(null)
      // Refresh delivery notes list
      const dns = await fetchUnmatchedDeliveryNotes()
      setDeliveryNotes(dns)
      
      // Refresh pairing suggestions for all delivery notes
      const suggestionsMap = new Map()
      for (const dn of dns) {
        try {
          const suggestions = await fetchInvoiceSuggestionsForDN(dn.id)
          if (suggestions.suggestions && suggestions.suggestions.length > 0) {
            suggestionsMap.set(dn.id, suggestions.suggestions[0]) // Get the best suggestion
          }
        } catch (err) {
          console.warn(`Failed to fetch suggestions for DN ${dn.id}:`, err)
        }
      }
      setPairingSuggestions(suggestionsMap)
      
      // Also trigger parent refresh if needed
      onSelectDN(confirmationData.deliveryNoteId)
      // Notify parent to refresh discrepancy analysis
      if (onPairSuccess) {
        onPairSuccess()
      }
    } catch (err) {
      console.error('Failed to pair:', err)
      // Error will be shown via toast in parent component or handled by onPairSuccess
      console.error('Failed to pair:', err)
    } finally {
      setPairingLoading(false)
    }
  }

  const handleRejectPairing = () => {
    setShowConfirmationModal(false)
    setConfirmationData(null)
  }

  // Handle batch clear all delivery notes
  const handleClearAllDNs = async () => {
    if (filteredDeliveryNotes.length === 0) return

    setDeletingDNs(true)
    try {
      const dnIds = filteredDeliveryNotes.map(dn => dn.id)
      const result = await deleteDeliveryNotes(dnIds)
      
      // Refresh delivery notes list
      await loadDeliveryNotes()
      
      // Clear selected DN if it was deleted
      if (selectedDNId && dnIds.includes(selectedDNId)) {
        onSelectDN('') // Clear selection
      }
      
      // Show success message
      let message = `Successfully deleted ${result.deleted_count} delivery note${result.deleted_count !== 1 ? 's' : ''}!`
      if (result.skipped_count && result.skipped_count > 0) {
        message += ` (${result.skipped_count} paired delivery note${result.skipped_count !== 1 ? 's' : ''} were skipped)`
      }
      toast.success(message)
      
      // Trigger parent refresh if needed
      if (onPairSuccess) {
        onPairSuccess()
      }
    } catch (err) {
      console.error('Failed to delete delivery notes:', err)
      const errorMessage = err instanceof Error ? err.message : 'Unknown error'
      toast.error(`Failed to delete delivery notes: ${errorMessage}`)
    } finally {
      setDeletingDNs(false)
      setShowClearAllModal(false)
    }
  }

  // Handle single delivery note deletion
  const handleDeleteSingleDN = async (dnId: string) => {
    setDeletingDNs(true)
    try {
      console.log('[DEBUG] Deleting delivery note:', dnId)
      const result = await deleteDeliveryNotes([dnId])
      console.log('[DEBUG] Delete result:', result)
      
      // Optimistically remove from state immediately if deletion succeeded
      if (result.deleted_count > 0) {
        setDeliveryNotes(prev => prev.filter(dn => dn.id !== dnId))
        // Clear selected DN if it was deleted
        if (selectedDNId === dnId) {
          onSelectDN('') // Clear selection
        }
        toast.success('Delivery note deleted successfully!')
      } else if (result.skipped_count && result.skipped_count > 0) {
        // Show the specific reason why it was skipped
        const errorMsg = result.errors && result.errors.length > 0 
          ? result.errors[0] 
          : 'This delivery note is paired and cannot be deleted.'
        toast.warning(errorMsg)
      } else {
        // If deleted_count is 0 and skipped_count is 0, something went wrong
        console.error('[DEBUG] Delete failed - deleted_count:', result.deleted_count, 'skipped_count:', result.skipped_count, 'result:', result)
        const errorMsg = result.errors && result.errors.length > 0
          ? result.errors[0]
          : (result.message || 'Please try again.')
        toast.error(`Failed to delete delivery note: ${errorMsg}`)
      }
      
      // Refresh delivery notes list to ensure consistency (even if we optimistically removed)
      // Use a small delay to ensure database commit is visible
      setTimeout(async () => {
        try {
          await loadDeliveryNotes()
        } catch (err) {
          console.error('Failed to refresh after deletion:', err)
        }
      }, 100)
      
      // Trigger parent refresh if needed
      if (onPairSuccess) {
        onPairSuccess()
      }
    } catch (err) {
      console.error('Failed to delete delivery note:', err)
      const errorMessage = err instanceof Error ? err.message : 'Unknown error'
      toast.error(`Failed to delete delivery note: ${errorMessage}`)
    } finally {
      setDeletingDNs(false)
    }
  }

  return (
    <div className="discrepancy-card delivery-notes-cards-section">
      <div className="discrepancy-card-header">
        <Package size={20} />
        <h3 className="discrepancy-card-title">Delivery Notes</h3>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginLeft: 'auto' }}>
          {filteredDeliveryNotes.length > 0 && (
            <div className="discrepancy-badge">{filteredDeliveryNotes.length}</div>
          )}
          {filteredDeliveryNotes.length > 0 && (
            <button
              className="delivery-notes-clear-all-btn"
              onClick={() => setShowClearAllModal(true)}
              disabled={loading || pairingLoading || deletingDNs}
              title="Clear all non-paired delivery notes"
              aria-label="Clear all non-paired delivery notes"
            >
              <Trash2 size={16} />
            </button>
          )}
        </div>
      </div>
      <div className="delivery-notes-cards-section-content">
        {/* Pairing Mode Toggle */}
        <div className="delivery-notes-toggle-section">
        <div className="delivery-notes-toggle-label">Pairing Mode:</div>
        <div className="delivery-notes-toggle-container">
          <button
            className={`delivery-notes-toggle-option ${pairingMode === 'automatic' ? 'active' : ''}`}
            onClick={() => onPairingModeChange('automatic')}
          >
            Automatic
          </button>
          <button
            className={`delivery-notes-toggle-option ${pairingMode === 'manual' ? 'active' : ''}`}
            onClick={() => onPairingModeChange('manual')}
          >
            Manual (Recommended)
          </button>
        </div>
      </div>

      {/* Delivery Notes Cards */}
      <div className="delivery-notes-cards-container">
        {error ? (
          <div className="delivery-notes-empty" style={{ padding: '16px' }}>
            <AlertTriangle size={32} style={{ color: 'var(--accent-red)', marginBottom: '8px' }} />
            <div style={{ fontSize: '13px', color: 'var(--text-secondary)', textAlign: 'center', marginBottom: '12px' }}>
              {error}
            </div>
            <button
              className="glass-button"
              onClick={() => loadDeliveryNotes()}
              style={{ fontSize: '12px', padding: '6px 12px' }}
            >
              Retry
            </button>
          </div>
        ) : loading || pairingLoading ? (
          <div className="delivery-notes-loading">
            <Loader2 size={20} className="spinner" />
            <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '8px' }}>
              {loading ? 'Loading delivery notes...' : 'Loading pairing confirmation...'}
            </div>
          </div>
        ) : filteredDeliveryNotes.length === 0 ? (
          <div className="delivery-notes-empty">
            <Package size={32} style={{ opacity: 0.3, marginBottom: '8px' }} />
            <div style={{ fontSize: '13px', color: 'var(--text-muted)', textAlign: 'center' }}>
              {deliveryNotes.length === 0
                ? 'Waiting on delivery notes to display cards'
                : pairingMode === 'automatic'
                ? 'No high-confidence pairings available'
                : 'No unmatched delivery notes'}
            </div>
            {deliveryNotes.length === 0 && (
              <div style={{ fontSize: '11px', color: 'var(--text-muted)', textAlign: 'center', marginTop: '8px', opacity: 0.7 }}>
                Upload or create delivery notes to get started
              </div>
            )}
          </div>
        ) : (
          <div className="delivery-notes-cards-list">
            {filteredDeliveryNotes.map((dn) => (
              <DeliveryNoteCard
                key={dn.id}
                deliveryNote={dn}
                isSelected={selectedDNId === dn.id}
                onClick={() => handleDNClick(dn)}
                onDelete={handleDeleteSingleDN}
              />
            ))}
          </div>
        )}
      </div>
      </div>

      {/* Pairing Confirmation Modal */}
      <PairingConfirmationModal
        isOpen={showConfirmationModal}
        onClose={handleRejectPairing}
        onConfirm={handleConfirmPairing}
        onReject={handleRejectPairing}
        data={confirmationData}
        loading={pairingLoading}
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
            if (onPairSuccess) {
              onPairSuccess()
            }
          }}
          invoiceId={previewData.invoiceId}
          deliveryNoteId={previewData.deliveryNoteId}
          initialValidation={previewData.validation}
        />
      )}

      {/* Clear All Delivery Notes Modal */}
      <ClearDeliveryNotesModal
        isOpen={showClearAllModal}
        onClose={() => setShowClearAllModal(false)}
        onConfirm={handleClearAllDNs}
        count={filteredDeliveryNotes.length}
        loading={deletingDNs}
      />
    </div>
  )
}

