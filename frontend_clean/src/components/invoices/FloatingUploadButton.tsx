import { useState, useRef, useCallback } from 'react'
import './FloatingUploadButton.css'

interface FloatingUploadButtonProps {
  onUpload: (files: FileList) => void
  isUploading?: boolean
}

export function FloatingUploadButton({ onUpload, isUploading = false }: FloatingUploadButtonProps) {
  const [isExpanded, setIsExpanded] = useState(false)
  const [isDragging, setIsDragging] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const handleClick = useCallback(() => {
    if (!isExpanded) {
      setIsExpanded(true)
    } else {
      fileInputRef.current?.click()
    }
  }, [isExpanded])

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    if (!isDragging) {
      setIsDragging(true)
      setIsExpanded(true)
    }
  }, [isDragging])

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    // Only hide if we're leaving the entire drop zone
    if (!e.currentTarget.contains(e.relatedTarget as Node)) {
      setIsDragging(false)
      setIsExpanded(false)
    }
  }, [])

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setIsDragging(false)
    setIsExpanded(false)
    
    const files = e.dataTransfer.files
    if (files.length > 0) {
      onUpload(files)
    }
  }, [onUpload])

  const handleFileInput = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files
    if (files && files.length > 0) {
      onUpload(files)
      setIsExpanded(false)
    }
    // Reset input
    if (fileInputRef.current) {
      fileInputRef.current.value = ''
    }
  }, [onUpload])

  const handleClose = useCallback((e: React.MouseEvent) => {
    e.stopPropagation()
    setIsExpanded(false)
    setIsDragging(false)
  }, [])

  return (
    <>
      {/* Floating Action Button */}
      {!isExpanded && (
        <button
          className="fab-button"
          onClick={handleClick}
          disabled={isUploading}
          aria-label="Upload invoices"
        >
          <svg
            width="24"
            height="24"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
            <polyline points="17 8 12 3 7 8" />
            <line x1="12" y1="3" x2="12" y2="15" />
          </svg>
        </button>
      )}

      {/* Upload Overlay */}
      {isExpanded && (
        <div
          className={`upload-overlay ${isDragging ? 'dragging' : ''}`}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          onClick={handleClose}
        >
          <div
            className="upload-overlay-content"
            onClick={(e) => e.stopPropagation()}
          >
            <button
              className="upload-overlay-close"
              onClick={handleClose}
              aria-label="Close upload"
            >
              <svg
                width="20"
                height="20"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <line x1="18" y1="6" x2="6" y2="18" />
                <line x1="6" y1="6" x2="18" y2="18" />
              </svg>
            </button>

            <div className="upload-overlay-body">
              <div className="upload-icon">
                <svg
                  width="64"
                  height="64"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="1.5"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                  <polyline points="17 8 12 3 7 8" />
                  <line x1="12" y1="3" x2="12" y2="15" />
                </svg>
              </div>

              <h2 className="upload-title">
                {isDragging ? 'Drop files here' : 'Upload Invoices'}
              </h2>

              <p className="upload-subtitle">
                Drag and drop PDFs or images here, or click to select files
              </p>

              <button
                className="upload-button-primary"
                onClick={() => fileInputRef.current?.click()}
                disabled={isUploading}
              >
                {isUploading ? 'Uploading...' : 'Choose Files'}
              </button>

              <p className="upload-hint">
                Supports PDF, PNG, JPG, JPEG, HEIC
              </p>
            </div>
          </div>
        </div>
      )}

      <input
        ref={fileInputRef}
        type="file"
        multiple
        accept=".pdf,.png,.jpg,.jpeg,.heic,.tiff,.tif"
        onChange={handleFileInput}
        style={{ display: 'none' }}
        aria-label="Upload invoice files"
      />
    </>
  )
}

