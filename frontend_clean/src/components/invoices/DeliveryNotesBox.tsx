import { memo, useRef } from 'react'
import { SingleUploadBox } from './SingleUploadBox'
import './DeliveryNotesBox.css'

import type { FileItem } from '../../pages/Invoices'

interface DeliveryNotesBoxProps {
  onUpload: (files: FileList) => void
  onFileInput: (e: React.ChangeEvent<HTMLInputElement>) => void
  deliveryNotes: FileItem[]
}

export const DeliveryNotesBox = memo(function DeliveryNotesBox({
  onUpload,
  onFileInput,
  deliveryNotes,
}: DeliveryNotesBoxProps) {
  const fileInputRef = useRef<HTMLInputElement>(null)

  return (
    <div className="delivery-notes-box">
      <div className="delivery-notes-header">
        <h3 className="delivery-notes-title">Delivery Notes</h3>
        <span className="delivery-notes-count">{deliveryNotes.length} uploaded</span>
      </div>
      
      <div className="delivery-notes-upload-section">
        <SingleUploadBox
          onUpload={onUpload}
          fileInputRef={fileInputRef}
          onFileInput={onFileInput}
          compact={true}
        />
      </div>

      <div className="delivery-notes-list">
        {deliveryNotes.length === 0 ? (
          <div className="delivery-notes-empty">
            <p>No delivery notes uploaded yet</p>
            <p className="delivery-notes-hint">Upload delivery notes to match with invoices</p>
          </div>
        ) : (
          <div className="delivery-notes-items">
            {deliveryNotes.map((note, idx) => (
              <div key={note.id || idx} className="delivery-note-item">
                <div className="delivery-note-name">{note.file?.name || note.metadata?.id || `DN-${idx + 1}`}</div>
                <div className="delivery-note-status">
                  {note.status === 'scanned' ? 'Processed' : note.status === 'submitted' ? 'Matched' : 'Pending match'}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
})

