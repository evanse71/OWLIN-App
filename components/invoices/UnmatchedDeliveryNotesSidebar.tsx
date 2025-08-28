import { useState, useEffect } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Plus, Link, AlertTriangle } from 'lucide-react'
import type { DeliveryNote, InvoiceSummary, LineItem } from '@/types'
import { getDeliveryNote, compareDN } from '@/lib/api'
import { usePairingSuggestions } from '@/hooks/usePairingSuggestions'
import CreateDeliveryNoteModal from './CreateDeliveryNoteModal'

interface UnmatchedDeliveryNotesSidebarProps {
  deliveryNotes: DeliveryNote[]
  selectedInvoice: InvoiceSummary | null
  onPair: (noteId: string) => void
  onCreateDeliveryNote: (deliveryNote: any) => void
}

export default function UnmatchedDeliveryNotesSidebar({
  deliveryNotes,
  selectedInvoice,
  onPair,
  onCreateDeliveryNote
}: UnmatchedDeliveryNotesSidebarProps) {
  const [expandedNote, setExpandedNote] = useState<string | null>(null)
  const [noteItems, setNoteItems] = useState<Record<string, LineItem[]>>({})
  const [comparisonDiffs, setComparisonDiffs] = useState<Record<string, any[]>>({})
  
  // Add pairing suggestions hook
  const { loading, top } = usePairingSuggestions(selectedInvoice?.id)

  const handlePair = (noteId: string) => {
    onPair(noteId)
  }

  const loadNoteDetails = async (noteId: string) => {
    try {
      const noteDetail = await getDeliveryNote(noteId)
      if (noteDetail && noteDetail.items) {
        setNoteItems(prev => ({
          ...prev,
          [noteId]: noteDetail.items
        }))
      }
    } catch (error) {
      console.error(`Failed to load note details for ${noteId}:`, error)
    }
  }

  const loadComparison = async (noteId: string, invoiceId: string) => {
    try {
      const comparison = await compareDN(noteId, invoiceId)
      setComparisonDiffs(prev => ({
        ...prev,
        [noteId]: comparison.diffs || []
      }))
    } catch (error) {
      console.error(`Failed to load comparison for ${noteId}:`, error)
    }
  }

  useEffect(() => {
    if (expandedNote) {
      loadNoteDetails(expandedNote)
      if (selectedInvoice) {
        loadComparison(expandedNote, selectedInvoice.id)
      }
    }
  }, [expandedNote, selectedInvoice])

  const getDiffIcon = (noteId: string, field: string) => {
    const diffs = comparisonDiffs[noteId] || []
    const hasDiff = diffs.some(diff => 
      diff.kind === 'qty_diff' || 
      diff.kind === 'price_diff' || 
      diff.kind === 'vat_diff' ||
      diff.kind === 'missing_on_invoice' ||
      diff.kind === 'extra_on_invoice'
    )
    return hasDiff ? <AlertTriangle className="h-3 w-3 text-yellow-500" /> : null
  }

  return (
    <Card className="ow-card">
      <CardHeader className="flex flex-col space-y-1.5 p-6 pb-4">
        <div className="flex items-center justify-between">
          <CardTitle className="tracking-tight text-lg font-semibold text-[var(--ow-ink)]">
            Delivery Notes
          </CardTitle>
          <CreateDeliveryNoteModal onCreated={onCreateDeliveryNote}>
            <Button size="sm">
              <Plus className="h-4 w-4 mr-2" />
              Create
            </Button>
          </CreateDeliveryNoteModal>
        </div>
      </CardHeader>
      <CardContent className="p-6 pt-0">
        {/* Pairing Suggestions */}
        <div className="px-0 pb-3">
          {loading ? (
            <div className="text-xs text-neutral-500">Finding delivery note suggestions…</div>
          ) : top ? (
            <div className="flex items-center justify-between text-xs rounded-md bg-neutral-50 border border-neutral-200 px-3 py-2">
              <div className="min-w-0">
                <span className="text-neutral-600">Suggest:</span>{" "}
                <span className="font-medium text-neutral-800">
                  {top.delivery_note.code ?? `DN-${top.delivery_note.id}`}
                </span>{" "}
                <span className="text-neutral-600">
                  • {top.delivery_note.supplier ?? "Unknown"} • {top.delivery_note.date ?? "—"} • {top.score.toFixed(2)}
                </span>
              </div>
              <button
                className="shrink-0 ml-2 rounded-md border border-neutral-300 px-2 py-1 hover:bg-neutral-100"
                onClick={async () => {
                  try {
                    // If you already have a link endpoint, call it here:
                    // await fetch(`/api/invoices/${selectedInvoice!.id}/link_delivery_note`, { method: "POST", body: JSON.stringify({ delivery_note_id: top.delivery_note.id }) });
                    console.log("Confirm pairing", { invoiceId: selectedInvoice?.id, deliveryNoteId: top.delivery_note.id });
                  } catch (e) {
                    console.error(e);
                  }
                }}
              >
                Confirm
              </button>
            </div>
          ) : selectedInvoice ? (
            <div className="text-xs text-neutral-500">No suggestions yet.</div>
          ) : null}
        </div>
        
        <div className="space-y-3">
          {deliveryNotes.length === 0 ? (
            <div className="text-center py-4">
              <p className="text-sm text-[var(--ow-ink-dim)]">No delivery notes</p>
            </div>
          ) : (
            deliveryNotes.map((note) => (
              <div
                key={note.id}
                className={`p-3 rounded-lg border cursor-pointer transition-colors hover:bg-[var(--ow-muted)]/50 ${
                  expandedNote === note.id ? 'bg-[var(--ow-muted)]/30' : ''
                }`}
                onClick={() => setExpandedNote(expandedNote === note.id ? null : note.id)}
              >
                <div className="flex items-center justify-between">
                  <div className="flex-1">
                    <h4 className="font-medium text-sm text-[var(--ow-ink)]">
                      {note.note_number || 'DN-' + note.id.slice(-6)}
                    </h4>
                    <p className="text-xs text-[var(--ow-ink-dim)]">
                      {note.supplier_name}
                    </p>
                    <p className="text-xs text-[var(--ow-ink-dim)]">
                      {new Date(note.date).toLocaleDateString()}
                    </p>
                  </div>
                  <div className="flex items-center gap-2">
                    <Badge variant="secondary" className="text-xs">
                      {note.status}
                    </Badge>
                    {selectedInvoice && (
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={(e) => {
                          e.stopPropagation()
                          handlePair(note.id)
                        }}
                        className="h-6 px-2"
                      >
                        <Link className="h-3 w-3 mr-1" />
                        Pair
                      </Button>
                    )}
                  </div>
                </div>
                
                {expandedNote === note.id && (
                  <div className="mt-3 pt-3 border-t border-[var(--ow-border)]">
                    <div className="space-y-2">
                      <div className="flex items-center justify-between text-xs">
                        <span className="text-[var(--ow-ink-dim)]">Note Number:</span>
                        <span className="font-medium">{note.note_number}</span>
                      </div>
                      <div className="flex items-center justify-between text-xs">
                        <span className="text-[var(--ow-ink-dim)]">Date:</span>
                        <span>{new Date(note.date).toLocaleDateString()}</span>
                      </div>
                      <div className="flex items-center justify-between text-xs">
                        <span className="text-[var(--ow-ink-dim)]">Supplier:</span>
                        <span>{note.supplier_name}</span>
                      </div>
                      
                      {/* Show note items */}
                      {noteItems[note.id] && noteItems[note.id].length > 0 && (
                        <div className="mt-3">
                          <h5 className="text-xs font-medium text-[var(--ow-ink)] mb-2">Items:</h5>
                          <div className="space-y-1">
                            {noteItems[note.id].map((item, index) => (
                              <div key={index} className="flex items-center justify-between text-xs p-1 bg-[var(--ow-muted)]/20 rounded">
                                <div className="flex-1">
                                  <span className="font-medium">{item.description}</span>
                                  <div className="text-[var(--ow-ink-dim)]">
                                    Qty: {item.qty} × £{(item.unit_price || 0) / 100}
                                  </div>
                                </div>
                                <div className="flex items-center gap-1">
                                  {getDiffIcon(note.id, item.description)}
                                  <span className="font-medium">£{(item.total || 0) / 100}</span>
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                      
                      {selectedInvoice && (
                        <div className="mt-3 p-2 bg-[var(--ow-muted)]/30 rounded border">
                          <div className="flex items-center gap-2 mb-2">
                            <AlertTriangle className="h-3 w-3 text-yellow-500" />
                            <span className="text-xs font-medium text-[var(--ow-ink)]">
                              Compare with {selectedInvoice.invoice_number || selectedInvoice.id}
                            </span>
                          </div>
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={(e) => {
                              e.stopPropagation()
                              handlePair(note.id)
                            }}
                            className="w-full h-7 text-xs"
                          >
                            <Link className="h-3 w-3 mr-1" />
                            Pair with {selectedInvoice.invoice_number || selectedInvoice.id}
                          </Button>
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </div>
            ))
          )}
        </div>
      </CardContent>
    </Card>
  )
} 