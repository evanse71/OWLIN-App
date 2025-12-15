import { useState, useEffect } from 'react'
import { X, Search, ChevronDown, ChevronUp, Loader2 } from 'lucide-react'
import { fetchDeliveryNotes, linkDeliveryNoteToInvoice, validatePair, fetchPairingSuggestions, fetchDeliveryNoteDetails } from '../../lib/api'
import { PairingPreviewModal } from './PairingPreviewModal'
import './Modal.css'

interface DeliveryNote {
  id: string
  noteNumber?: string
  date?: string
  supplier?: string
  venue?: string
}

interface DeliveryNoteDetails {
  id: string
  noteNumber?: string
  date?: string
  supplier?: string
  venue?: string
  lineItems?: Array<{
    description?: string
    qty?: number
    quantity?: number
    unit?: string
    uom?: string
  }>
}

interface LinkDeliveryNoteModalProps {
  isOpen: boolean
  onClose: () => void
  onSuccess: () => void
  invoiceId: string
}

export function LinkDeliveryNoteModal({ isOpen, onClose, onSuccess, invoiceId }: LinkDeliveryNoteModalProps) {
  const [deliveryNotes, setDeliveryNotes] = useState<DeliveryNote[]>([])
  const [filteredNotes, setFilteredNotes] = useState<DeliveryNote[]>([])
  const [searchQuery, setSearchQuery] = useState('')
  const [loading, setLoading] = useState(false)
  const [linking, setLinking] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [previewModalOpen, setPreviewModalOpen] = useState(false)
  const [previewDNId, setPreviewDNId] = useState<string | null>(null)
  const [previewValidation, setPreviewValidation] = useState<any>(null)
  
  // New state for confidence scores and expandable cards
  const [confidenceScores, setConfidenceScores] = useState<Map<string, number>>(new Map())
  const [loadingSuggestions, setLoadingSuggestions] = useState(false)
  const [expandedDNId, setExpandedDNId] = useState<string | null>(null)
  const [expandedDNDetails, setExpandedDNDetails] = useState<Map<string, DeliveryNoteDetails>>(new Map())
  const [loadingDNDetails, setLoadingDNDetails] = useState<Set<string>>(new Set())
  const [loadingScores, setLoadingScores] = useState<Set<string>>(new Set())

  useEffect(() => {
    if (isOpen) {
      loadDeliveryNotes().then(() => {
        // Load pairing suggestions after delivery notes are loaded
        loadPairingSuggestions()
      })
    } else {
      // Reset state when modal closes
      setExpandedDNId(null)
      setExpandedDNDetails(new Map())
      setConfidenceScores(new Map())
    }
  }, [isOpen, invoiceId])

  useEffect(() => {
    if (searchQuery.trim() === '') {
      setFilteredNotes(deliveryNotes)
    } else {
      const query = searchQuery.toLowerCase()
      setFilteredNotes(
        deliveryNotes.filter(
          (dn) =>
            dn.noteNumber?.toLowerCase().includes(query) ||
            dn.supplier?.toLowerCase().includes(query) ||
            String(dn.id).toLowerCase().includes(query)
        )
      )
    }
  }, [searchQuery, deliveryNotes])

  const loadDeliveryNotes = async () => {
    setLoading(true)
    setError(null)
    try {
      const notes = await fetchDeliveryNotes()
      setDeliveryNotes(notes)
      setFilteredNotes(notes)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load delivery notes')
    } finally {
      setLoading(false)
    }
  }

  const loadPairingSuggestions = async () => {
    setLoadingSuggestions(true)
    try {
      const response = await fetchPairingSuggestions(invoiceId)
      const scoresMap = new Map<string, number>()
      
      if (response.suggestions) {
        response.suggestions.forEach((suggestion) => {
          // Try multiple possible field names for delivery note ID
          const dnId = suggestion.deliveryNoteId || (suggestion as any).delivery_note_id || (suggestion as any).deliveryNote?.id || (suggestion as any).delivery_id
          
          // Use quantity match score as the percentage to display
          // Try multiple field name variations
          let quantityMatchScore = suggestion.quantityMatchScore || 
                                   (suggestion as any).quantity_match_score || 
                                   (suggestion as any).quantityMatch || 
                                   (suggestion as any).match_score
          
          // If quantity match score is not available, use confidence as fallback
          if (quantityMatchScore === undefined || quantityMatchScore === null || quantityMatchScore === 0) {
            quantityMatchScore = suggestion.confidence || suggestion.probability || suggestion.similarity
          }
          
          // Only add to map if we have a valid score (even if it's 0)
          if (dnId && quantityMatchScore !== undefined && quantityMatchScore !== null) {
            // Normalize ID to string for consistent matching
            const normalizedId = String(dnId)
            scoresMap.set(normalizedId, quantityMatchScore)
          }
        })
      }
      
      // Debug logging
      console.log('[LinkDeliveryNoteModal] Pairing suggestions loaded:', {
        invoiceId,
        suggestionCount: response.suggestions?.length || 0,
        scoresMapSize: scoresMap.size,
        scoresMap: Array.from(scoresMap.entries()),
        deliveryNoteCount: deliveryNotes.length,
        deliveryNoteIds: deliveryNotes.map(dn => dn.id),
        suggestions: response.suggestions?.map(s => ({
          deliveryNoteId: s.deliveryNoteId,
          quantityMatchScore: s.quantityMatchScore || (s as any).quantity_match_score,
          confidence: s.confidence,
          probability: s.probability,
          similarity: s.similarity,
          allFields: Object.keys(s)
        }))
      })
      
      setConfidenceScores(scoresMap)
      
      // Fetch scores for delivery notes that don't have scores from suggestions
      // This ensures we always try to show a percentage instead of N/A
      const notesWithoutScores = deliveryNotes.filter(dn => !scoresMap.has(String(dn.id)))
      
      if (notesWithoutScores.length > 0) {
        console.log('[LinkDeliveryNoteModal] Fetching scores for', notesWithoutScores.length, 'delivery notes without scores')
        // Fetch scores for delivery notes without scores in parallel (limit to first 20 to avoid overwhelming API)
        const notesToFetch = notesWithoutScores.slice(0, 20)
        const scorePromises = notesToFetch.map(async (dn) => {
          try {
            setLoadingScores(prev => new Set(prev).add(dn.id))
            const score = await fetchQuantityMatchScore(dn.id)
            if (score !== null && score !== undefined) {
              return { dnId: dn.id, score }
            }
          } catch (err) {
            console.warn(`Failed to fetch score for DN ${dn.id}:`, err)
          } finally {
            setLoadingScores(prev => {
              const next = new Set(prev)
              next.delete(dn.id)
              return next
            })
          }
          return null
        })
        
        const scoreResults = await Promise.all(scorePromises)
        const newScoresMap = new Map(scoresMap)
        scoreResults.forEach((result) => {
          if (result && result.score !== null && result.score !== undefined) {
            newScoresMap.set(String(result.dnId), result.score)
          }
        })
        
        if (newScoresMap.size > scoresMap.size) {
          console.log('[LinkDeliveryNoteModal] Fetched', newScoresMap.size - scoresMap.size, 'additional scores:', 
            Array.from(newScoresMap.entries()).filter(([id]) => !scoresMap.has(id)))
          setConfidenceScores(newScoresMap)
        }
      }
    } catch (err) {
      console.warn('Failed to load pairing suggestions:', err)
      // Don't show error to user, just continue without scores
    } finally {
      setLoadingSuggestions(false)
    }
  }
  
  // Fetch quantity match score for a specific delivery note
  const fetchQuantityMatchScore = async (dnId: string): Promise<number | null> => {
    try {
      const validation = await validatePair(invoiceId, dnId)
      return validation.matchScore || null
    } catch (err) {
      console.warn(`Failed to fetch quantity match score for DN ${dnId}:`, err)
      return null
    }
  }

  const handleCardClick = async (dnId: string, e: React.MouseEvent) => {
    // Don't expand if clicking the Link button
    if ((e.target as HTMLElement).closest('button')) {
      return
    }

    if (expandedDNId === dnId) {
      // Collapse
      setExpandedDNId(null)
    } else {
      // Expand
      setExpandedDNId(dnId)
      
      // Fetch details if not already loaded
      if (!expandedDNDetails.has(dnId) && !loadingDNDetails.has(dnId)) {
        setLoadingDNDetails(prev => new Set(prev).add(dnId))
        try {
          const details = await fetchDeliveryNoteDetails(dnId)
          if (details) {
            setExpandedDNDetails(prev => {
              const newMap = new Map(prev)
              newMap.set(dnId, details)
              return newMap
            })
          }
        } catch (err) {
          console.warn('Failed to load delivery note details:', err)
        } finally {
          setLoadingDNDetails(prev => {
            const newSet = new Set(prev)
            newSet.delete(dnId)
            return newSet
          })
        }
      }
    }
  }

  const getConfidenceColor = (quantityMatchScore: number) => {
    // Quantity match score is already a percentage (0-1), so use same thresholds
    if (quantityMatchScore >= 0.8) {
      return {
        background: 'rgba(34, 197, 94, 0.2)',
        border: 'rgba(34, 197, 94, 0.3)',
        color: 'var(--accent-green)',
      }
    } else if (quantityMatchScore >= 0.6) {
      return {
        background: 'rgba(251, 191, 36, 0.2)',
        border: 'rgba(251, 191, 36, 0.3)',
        color: 'var(--accent-yellow)',
      }
    } else {
      return {
        background: 'rgba(239, 68, 68, 0.2)',
        border: 'rgba(239, 68, 68, 0.3)',
        color: 'var(--accent-red)',
      }
    }
  }

  const handleLink = async (dnId: string) => {
    setLinking(dnId)
    setError(null)
    try {
      // Validate before pairing
      const validation = await validatePair(invoiceId, dnId)
      
      // If validation shows warnings or low match score, show preview modal
      if (!validation.isValid || validation.matchScore < 0.8 || validation.warnings.length > 0) {
        setPreviewDNId(dnId)
        setPreviewValidation(validation)
        setPreviewModalOpen(true)
        setLinking(null)
        return
      }
      
      // If validation passes, proceed with pairing directly
      const result = await linkDeliveryNoteToInvoice(invoiceId, dnId)
      onSuccess()
      handleClose()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to link delivery note')
    } finally {
      setLinking(null)
    }
  }
  
  const handlePreviewConfirm = () => {
    onSuccess()
    handleClose()
    setPreviewModalOpen(false)
    setPreviewDNId(null)
    setPreviewValidation(null)
  }

  const handleClose = () => {
    setSearchQuery('')
    setError(null)
    setLinking(null)
    onClose()
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

  if (!isOpen) return null

  return (
    <div className="modal-overlay" onClick={handleClose}>
      <div className="modal-container" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2 className="modal-title">Link Delivery Note</h2>
          <button className="modal-close-button" onClick={handleClose}>
            <X size={20} />
          </button>
        </div>

        <div className="modal-body">
          {error && <div className="modal-error">{error}</div>}

          <div className="modal-form-group">
            <div style={{ position: 'relative' }}>
              <Search size={16} style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
              <input
                type="text"
                className="modal-form-input"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search by note number, supplier, or ID..."
                style={{ paddingLeft: '36px' }}
              />
            </div>
          </div>

          {loading ? (
            <div className="modal-loading">Loading delivery notes...</div>
          ) : filteredNotes.length === 0 ? (
            <div className="modal-loading" style={{ color: 'var(--text-muted)' }}>
              {searchQuery ? 'No delivery notes found matching your search.' : 'No delivery notes available.'}
            </div>
          ) : (
            <div style={{ maxHeight: '400px', overflowY: 'auto' }}>
              {filteredNotes.map((dn) => {
                // Try to match quantity match score - check both exact ID and normalized versions
                const dnId = String(dn.id)
                let quantityMatchScore = confidenceScores.get(dnId)
                
                // If not found, try matching by checking all possible ID variations
                if (quantityMatchScore === undefined) {
                  // Try to find by iterating through all scores
                  for (const [suggestionId, score] of confidenceScores.entries()) {
                    // Check if IDs match (handling different formats)
                    const normalizedSuggestionId = String(suggestionId)
                    if (normalizedSuggestionId === dnId || 
                        normalizedSuggestionId.includes(dnId) || 
                        dnId.includes(normalizedSuggestionId)) {
                      quantityMatchScore = score
                      break
                    }
                  }
                }
                
                const isExpanded = expandedDNId === dn.id
                const details = expandedDNDetails.get(dn.id)
                const isLoadingDetails = loadingDNDetails.has(dn.id)
                const colorScheme = quantityMatchScore !== undefined ? getConfidenceColor(quantityMatchScore) : null
                
                return (
                  <div key={dn.id}>
                    <div
                      style={{
                        padding: '16px',
                        border: '1px solid rgba(255, 255, 255, 0.1)',
                        borderRadius: '12px',
                        marginBottom: '12px',
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center',
                        transition: 'all 0.2s ease',
                        background: 'rgba(255, 255, 255, 0.03)',
                        backdropFilter: 'blur(10px)',
                        cursor: 'pointer',
                      }}
                      onClick={(e) => handleCardClick(dn.id, e)}
                      onMouseEnter={(e) => {
                        e.currentTarget.style.borderColor = 'rgba(255, 255, 255, 0.2)'
                        e.currentTarget.style.background = 'rgba(255, 255, 255, 0.05)'
                      }}
                      onMouseLeave={(e) => {
                        e.currentTarget.style.borderColor = 'rgba(255, 255, 255, 0.1)'
                        e.currentTarget.style.background = 'rgba(255, 255, 255, 0.03)'
                      }}
                    >
                      <div style={{ flex: 1, display: 'flex', alignItems: 'center', gap: '12px' }}>
                        <div style={{ flex: 1 }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '6px' }}>
                            <div style={{ fontWeight: '600', fontSize: '14px' }}>
                              {dn.noteNumber || `DN-${dn.id.slice(0, 8)}`}
                            </div>
                            {quantityMatchScore !== undefined && colorScheme ? (
                              <div
                                style={{
                                  fontSize: '13px',
                                  padding: '4px 10px',
                                  borderRadius: '16px',
                                  fontWeight: '700',
                                  background: colorScheme.background,
                                  border: `1px solid ${colorScheme.border}`,
                                  color: colorScheme.color,
                                  backdropFilter: 'blur(10px)',
                                  minWidth: '50px',
                                  textAlign: 'center',
                                  letterSpacing: '0.3px',
                                }}
                              >
                                {Math.round(quantityMatchScore * 100)}%
                              </div>
                            ) : (
                              <div
                                style={{
                                  fontSize: '13px',
                                  padding: '4px 10px',
                                  borderRadius: '16px',
                                  fontWeight: '700',
                                  background: 'rgba(255, 255, 255, 0.05)',
                                  border: '1px solid rgba(255, 255, 255, 0.1)',
                                  color: 'var(--text-muted)',
                                  backdropFilter: 'blur(10px)',
                                  minWidth: '50px',
                                  textAlign: 'center',
                                }}
                              >
                                N/A
                              </div>
                            )}
                          </div>
                          <div style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
                            {dn.supplier || 'Unknown Supplier'} · {formatDate(dn.date)}
                          </div>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                          {isExpanded ? <ChevronUp size={16} style={{ color: 'var(--text-muted)' }} /> : <ChevronDown size={16} style={{ color: 'var(--text-muted)' }} />}
                          <button
                            className="modal-button-primary"
                            onClick={(e) => {
                              e.stopPropagation()
                              handleLink(dn.id)
                            }}
                            disabled={linking === dn.id}
                            style={{ 
                              padding: '8px 20px', 
                              fontSize: '13px',
                              minWidth: '80px',
                              flexShrink: 0,
                            }}
                          >
                            {linking === dn.id ? 'Linking...' : 'Link'}
                          </button>
                        </div>
                      </div>
                    </div>
                    
                    {/* Expanded Details Section */}
                    {isExpanded && (
                      <div
                        style={{
                          marginTop: '-12px',
                          marginBottom: '12px',
                          marginLeft: '0',
                          marginRight: '0',
                          padding: '16px',
                          border: '1px solid rgba(255, 255, 255, 0.1)',
                          borderTop: 'none',
                          borderTopLeftRadius: '0',
                          borderTopRightRadius: '0',
                          borderBottomLeftRadius: '12px',
                          borderBottomRightRadius: '12px',
                          background: 'rgba(255, 255, 255, 0.02)',
                          backdropFilter: 'blur(10px)',
                          animation: 'fadeIn 0.2s ease-out',
                        }}
                      >
                        {isLoadingDetails ? (
                          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '20px', gap: '8px', color: 'var(--text-muted)' }}>
                            <Loader2 size={16} style={{ animation: 'spin 1s linear infinite' }} />
                            <span style={{ fontSize: '13px' }}>Loading details...</span>
                          </div>
                        ) : details ? (
                          <div>
                            {/* Key Details */}
                            <div style={{ marginBottom: '16px' }}>
                              <div style={{ fontSize: '12px', fontWeight: '600', marginBottom: '8px', color: 'var(--text-secondary)' }}>Key Details</div>
                              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px', fontSize: '13px' }}>
                                <div>
                                  <div style={{ color: 'var(--text-muted)', fontSize: '11px', marginBottom: '2px' }}>Supplier</div>
                                  <div style={{ color: 'var(--text-primary)' }}>{details.supplier || 'Unknown Supplier'}</div>
                                </div>
                                <div>
                                  <div style={{ color: 'var(--text-muted)', fontSize: '11px', marginBottom: '2px' }}>Date</div>
                                  <div style={{ color: 'var(--text-primary)' }}>{formatDate(details.date)}</div>
                                </div>
                                {details.venue && (
                                  <div>
                                    <div style={{ color: 'var(--text-muted)', fontSize: '11px', marginBottom: '2px' }}>Site/Venue</div>
                                    <div style={{ color: 'var(--text-primary)' }}>{details.venue}</div>
                                  </div>
                                )}
                              </div>
                            </div>
                            
                            {/* Line Items */}
                            {details.lineItems && details.lineItems.length > 0 && (
                              <div>
                                <div style={{ fontSize: '12px', fontWeight: '600', marginBottom: '8px', color: 'var(--text-secondary)' }}>Line Items</div>
                                <div style={{ maxHeight: '200px', overflowY: 'auto' }}>
                                  {details.lineItems.map((item, idx) => (
                                    <div
                                      key={idx}
                                      style={{
                                        padding: '10px',
                                        marginBottom: '8px',
                                        background: 'rgba(255, 255, 255, 0.03)',
                                        borderRadius: '8px',
                                        border: '1px solid rgba(255, 255, 255, 0.05)',
                                        fontSize: '12px',
                                      }}
                                    >
                                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '12px' }}>
                                        <div style={{ flex: 1, color: 'var(--text-primary)' }}>
                                          {item.description || 'No description'}
                                        </div>
                                        <div style={{ color: 'var(--text-secondary)', whiteSpace: 'nowrap' }}>
                                          Qty: {item.qty || item.quantity || 0} {item.unit || item.uom || ''}
                                        </div>
                                      </div>
                                    </div>
                                  ))}
                                </div>
                              </div>
                            )}
                          </div>
                        ) : (
                          <div style={{ padding: '20px', textAlign: 'center', color: 'var(--text-muted)', fontSize: '13px' }}>
                            No details available
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                )
              })}
            </div>
          )}
        </div>

        <div className="modal-footer">
          <button className="modal-button-secondary" onClick={handleClose}>
            Cancel
          </button>
        </div>
      </div>
      
      {/* Pairing Preview Modal */}
      {previewDNId && (
        <PairingPreviewModal
          isOpen={previewModalOpen}
          onClose={() => {
            setPreviewModalOpen(false)
            setPreviewDNId(null)
            setPreviewValidation(null)
          }}
          onConfirm={handlePreviewConfirm}
          invoiceId={invoiceId}
          deliveryNoteId={previewDNId}
          initialValidation={previewValidation}
        />
      )}
    </div>
  )
}

