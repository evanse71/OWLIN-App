import { useCallback, useState, useRef } from 'react'
import { Upload, FileText, Sparkles } from 'lucide-react'
import './ProminentUploadZone.css'

interface ProminentUploadZoneProps {
  onUpload: (files: FileList) => void
  isVisible: boolean
  viewMode: 'scanned' | 'manual'
}

export function ProminentUploadZone({ onUpload, isVisible, viewMode }: ProminentUploadZoneProps) {
  const [isDragging, setIsDragging] = useState(false)
  const [dragCounter, setDragCounter] = useState(0)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const handleDragEnter = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setDragCounter((prev) => prev + 1)
    if (e.dataTransfer.types.includes('Files')) {
      setIsDragging(true)
    }
  }, [])

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setDragCounter((prev) => {
      const newCount = prev - 1
      if (newCount === 0) {
        setIsDragging(false)
      }
      return newCount
    })
  }, [])

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    if (e.dataTransfer.types.includes('Files')) {
      e.dataTransfer.dropEffect = 'copy'
    }
  }, [])

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setIsDragging(false)
    setDragCounter(0)
    
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      onUpload(e.dataTransfer.files)
    }
  }, [onUpload])

  const handleClick = useCallback(() => {
    fileInputRef.current?.click()
  }, [])

  const handleFileInput = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      onUpload(e.target.files)
    }
    // Reset input so same file can be selected again
    if (fileInputRef.current) {
      fileInputRef.current.value = ''
    }
  }, [onUpload])

  if (!isVisible) return null

  return (
    <div
      className={`prominent-upload-zone ${isDragging ? 'dragging' : ''}`}
      onDragEnter={handleDragEnter}
      onDragLeave={handleDragLeave}
      onDragOver={handleDragOver}
      onDrop={handleDrop}
      onClick={handleClick}
    >
      <div className="upload-zone-content">
        <div className="upload-zone-icon-wrapper">
          {isDragging ? (
            <div className="upload-zone-icon-drag">
              <FileText size={48} />
            </div>
          ) : (
            <div className="upload-zone-icon">
              <Upload size={48} />
              <div className="upload-zone-sparkle">
                <Sparkles size={24} />
              </div>
            </div>
          )}
        </div>
        
        <h2 className="upload-zone-title">
          {isDragging ? 'Drop files here' : viewMode === 'scanned' ? 'Upload invoices & delivery notes' : 'Create your first invoice'}
        </h2>
        
        <p className="upload-zone-description">
          {viewMode === 'scanned' 
            ? 'Drag and drop PDFs or images, or click to browse. Owlin will automatically extract details and match invoices with delivery notes.'
            : 'Start by creating a manual invoice or upload documents to get started.'}
        </p>

        <div className="upload-zone-features">
          <div className="upload-feature">
            <div className="feature-icon">✨</div>
            <span>Auto-extract details</span>
          </div>
          <div className="upload-feature">
            <div className="feature-icon">🔗</div>
            <span>Smart matching</span>
          </div>
          <div className="upload-feature">
            <div className="feature-icon">⚡</div>
            <span>Instant processing</span>
          </div>
        </div>

        <button className="upload-zone-button" type="button">
          {isDragging ? 'Release to upload' : 'Choose files'}
        </button>

        <p className="upload-zone-formats">
          Supports: PDF, JPG, PNG, HEIC
        </p>
      </div>

      <input
        ref={fileInputRef}
        type="file"
        multiple
        accept=".pdf,.jpg,.jpeg,.png,.heic"
        onChange={handleFileInput}
        style={{ display: 'none' }}
      />
    </div>
  )
}

