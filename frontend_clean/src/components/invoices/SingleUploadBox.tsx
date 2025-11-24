import { memo, useCallback, useState } from 'react'
import './SingleUploadBox.css'

interface SingleUploadBoxProps {
  onUpload: (files: FileList) => void
  fileInputRef: React.RefObject<HTMLInputElement>
  onFileInput: (e: React.ChangeEvent<HTMLInputElement>) => void
  compact?: boolean
}

export const SingleUploadBox = memo(function SingleUploadBox({
  onUpload,
  fileInputRef,
  onFileInput,
  compact = false,
}: SingleUploadBoxProps) {
  const [isDragging, setIsDragging] = useState(false)

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setIsDragging(true)
  }, [])

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    if (!e.currentTarget.contains(e.relatedTarget as Node)) {
      setIsDragging(false)
    }
  }, [])

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setIsDragging(false)
    if (e.dataTransfer.files.length > 0) {
      onUpload(e.dataTransfer.files)
    }
  }, [onUpload])

  if (compact) {
    return (
      <div
        className="single-upload-box single-upload-box-compact"
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
      >
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
          <polyline points="17 8 12 3 7 8" />
          <line x1="12" y1="3" x2="12" y2="15" />
        </svg>
        <span>Upload Files</span>
        <input
          ref={fileInputRef}
          type="file"
          multiple
          accept=".pdf,.jpg,.jpeg,.png,.heic"
          onChange={onFileInput}
          style={{ display: 'none' }}
        />
      </div>
    )
  }

  return (
    <div
      className={`single-upload-box ${isDragging ? 'dragging' : ''}`}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
      onClick={() => fileInputRef.current?.click()}
    >
      <div className="single-upload-icon">📤</div>
      <h3 className="single-upload-title">Upload Invoices & Delivery Notes</h3>
      <p className="single-upload-subtitle">Click to select or drag and drop</p>
      <p className="single-upload-formats">.pdf, .jpg, .png, .heic</p>
      <p className="single-upload-hint">Files stay local — nothing leaves your device.</p>
      <input
        ref={fileInputRef}
        type="file"
        multiple
        accept=".pdf,.jpg,.jpeg,.png,.heic"
        onChange={onFileInput}
        style={{ display: 'none' }}
      />
    </div>
  )
})

