import { memo, useCallback, useState } from 'react'
import './DualUploadBoxes.css'

interface DualUploadBoxesProps {
  onInvoiceUpload: (files: FileList) => void
  onDeliveryNoteUpload: (files: FileList) => void
  invoiceInputRef: React.RefObject<HTMLInputElement>
  deliveryNoteInputRef: React.RefObject<HTMLInputElement>
  onFileInput: (e: React.ChangeEvent<HTMLInputElement>, isDeliveryNote: boolean) => void
}

export const DualUploadBoxes = memo(function DualUploadBoxes({
  onInvoiceUpload,
  onDeliveryNoteUpload,
  invoiceInputRef,
  deliveryNoteInputRef,
  onFileInput,
}: DualUploadBoxesProps) {
  const [isDraggingInvoice, setIsDraggingInvoice] = useState(false)
  const [isDraggingDeliveryNote, setIsDraggingDeliveryNote] = useState(false)

  const handleDragOver = useCallback((e: React.DragEvent, isDeliveryNote: boolean) => {
    e.preventDefault()
    e.stopPropagation()
    if (isDeliveryNote) {
      setIsDraggingDeliveryNote(true)
    } else {
      setIsDraggingInvoice(true)
    }
  }, [])

  const handleDragLeave = useCallback((e: React.DragEvent, isDeliveryNote: boolean) => {
    e.preventDefault()
    e.stopPropagation()
    if (isDeliveryNote) {
      setIsDraggingDeliveryNote(false)
    } else {
      setIsDraggingInvoice(false)
    }
  }, [])

  const handleDrop = useCallback((e: React.DragEvent, isDeliveryNote: boolean) => {
    e.preventDefault()
    e.stopPropagation()
    if (isDeliveryNote) {
      setIsDraggingDeliveryNote(false)
      if (e.dataTransfer.files.length > 0) {
        onDeliveryNoteUpload(e.dataTransfer.files)
      }
    } else {
      setIsDraggingInvoice(false)
      if (e.dataTransfer.files.length > 0) {
        onInvoiceUpload(e.dataTransfer.files)
      }
    }
  }, [onInvoiceUpload, onDeliveryNoteUpload])

  return (
    <div className="dual-upload-boxes">
      <div
        className={`upload-box ${isDraggingInvoice ? 'dragging' : ''}`}
        onDragOver={(e) => handleDragOver(e, false)}
        onDragLeave={(e) => handleDragLeave(e, false)}
        onDrop={(e) => handleDrop(e, false)}
        onClick={() => invoiceInputRef.current?.click()}
      >
        <div className="upload-box-icon">📄</div>
        <h3 className="upload-box-title">Invoices Upload</h3>
        <p className="upload-box-subtitle">Click to select or drag and drop</p>
        <p className="upload-box-formats">.pdf, .jpg, .png</p>
        <p className="upload-box-hint">Files stay local — nothing leaves your device.</p>
        <input
          ref={invoiceInputRef}
          type="file"
          multiple
          accept=".pdf,.jpg,.jpeg,.png,.heic"
          onChange={(e) => onFileInput(e, false)}
          style={{ display: 'none' }}
        />
      </div>

      <div
        className={`upload-box ${isDraggingDeliveryNote ? 'dragging' : ''}`}
        onDragOver={(e) => handleDragOver(e, true)}
        onDragLeave={(e) => handleDragLeave(e, true)}
        onDrop={(e) => handleDrop(e, true)}
        onClick={() => deliveryNoteInputRef.current?.click()}
      >
        <div className="upload-box-icon">🚚</div>
        <h3 className="upload-box-title">Delivery Notes Upload</h3>
        <p className="upload-box-subtitle">Click to select or drag and drop</p>
        <p className="upload-box-formats">.pdf, .jpg, .png</p>
        <p className="upload-box-hint">Files stay local — nothing leaves your device.</p>
        <input
          ref={deliveryNoteInputRef}
          type="file"
          multiple
          accept=".pdf,.jpg,.jpeg,.png,.heic"
          onChange={(e) => onFileInput(e, true)}
          style={{ display: 'none' }}
        />
      </div>
    </div>
  )
})

