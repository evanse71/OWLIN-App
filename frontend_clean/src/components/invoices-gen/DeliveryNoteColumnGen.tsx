import './DeliveryNoteColumnGen.css'

export interface DeliveryNoteSummary {
  id: string
  supplierName?: string | null
  noteNumber?: string | null
  status?: 'unlinked' | 'suggested' | 'linked'
}

interface DeliveryNoteColumnGenProps {
  deliveryNotes: DeliveryNoteSummary[]
  selectedDeliveryNoteId: string | null
  onSelectDeliveryNote: (id: string) => void
}

export function DeliveryNoteColumnGen({
  deliveryNotes,
  selectedDeliveryNoteId,
  onSelectDeliveryNote,
}: DeliveryNoteColumnGenProps) {
  const hasNotes = deliveryNotes && deliveryNotes.length > 0

  return (
    <div className="delivery-column-gen">
      <div className="delivery-column-gen__header">
        <div className="delivery-column-gen__title invoices-gen__label">
          Delivery notes
        </div>
        <div className="delivery-column-gen__count invoices-gen__micro invoices-gen__text-soft">
          {hasNotes ? `${deliveryNotes.length} notes` : 'None pending'}
        </div>
      </div>

      <div className="delivery-column-gen__list">
        {!hasNotes && (
          <div className="delivery-column-gen__empty">
            <div className="delivery-column-gen__empty-text">
              Unmatched delivery notes will wait here until paired with invoices.
            </div>
          </div>
        )}

        {hasNotes &&
          deliveryNotes.map((note) => {
            const isSelected = selectedDeliveryNoteId === note.id
            return (
              <button
                key={note.id}
                type="button"
                className={
                  'delivery-card-gen invoices-gen-card invoices-gen-card--subtle' +
                  (isSelected ? ' delivery-card-gen--selected' : '')
                }
                onClick={() => onSelectDeliveryNote(note.id)}
              >
                <div className="delivery-card-gen__top-row">
                  <div className="delivery-card-gen__supplier invoices-gen__body">
                    {note.supplierName || 'Supplier'}
                  </div>
                  <span className="delivery-card-gen__status-pill">
                    {note.status || 'Unlinked'}
                  </span>
                </div>

                <div className="delivery-card-gen__meta-row">
                  <span className="delivery-card-gen__id invoices-gen__micro invoices-gen__text-soft">
                    {note.noteNumber || 'Delivery note'}
                  </span>
                </div>
              </button>
            )
          })}
      </div>
    </div>
  )
}

