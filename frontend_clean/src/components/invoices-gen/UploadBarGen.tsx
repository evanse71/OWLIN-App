import React from 'react'
import './UploadBarGen.css'

interface UploadBarGenProps {
  onUploadClick?: () => void
  onCreateInvoiceClick?: () => void
  onCreateDeliveryNoteClick?: () => void
}

export function UploadBarGen(props: UploadBarGenProps) {
  const {
    onUploadClick = () => {},
    onCreateInvoiceClick = () => {},
    onCreateDeliveryNoteClick = () => {},
  } = props

  const [isDragOver, setIsDragOver] = React.useState(false)

  return (
    <div className="upload-bar-gen">
      <div
        className={
          'upload-bar-gen__dropzone invoices-gen-card invoices-gen-card--subtle' +
          (isDragOver ? ' upload-bar-gen__dropzone--active' : '')
        }
        onDragOver={(e) => {
          e.preventDefault()
          setIsDragOver(true)
        }}
        onDragLeave={(e) => {
          e.preventDefault()
          setIsDragOver(false)
        }}
        onDrop={(e) => {
          e.preventDefault()
          setIsDragOver(false)
          // in future we will read e.dataTransfer.files here
          if (onUploadClick) {
            onUploadClick()
          }
        }}
        onClick={onUploadClick}
      >
        <div className="upload-bar-gen__left">
          <div className="upload-bar-gen__title invoices-gen__h1">
            Invoices &amp; Delivery Notes
          </div>
          <div className="upload-bar-gen__subtitle invoices-gen__body invoices-gen__text-muted">
            Drop your PDFs and photos here. Owlin will scan, match, and flag issues automatically.
          </div>
          <div className="upload-bar-gen__hint invoices-gen__micro invoices-gen__text-soft">
            Drag &amp; drop anywhere in this card, or click to choose files.
          </div>
        </div>
      </div>

      <div className="upload-bar-gen__right">
        <button
          className="owlin-btn owlin-btn--primary"
          type="button"
          onClick={onUploadClick}
        >
          Upload documents
        </button>
        <button
          className="owlin-btn owlin-btn--ghost"
          type="button"
          onClick={onCreateInvoiceClick}
        >
          Create manual invoice
        </button>
        <button
          className="owlin-btn owlin-btn--ghost"
          type="button"
          onClick={onCreateDeliveryNoteClick}
        >
          Create delivery note
        </button>
      </div>
    </div>
  )
}

