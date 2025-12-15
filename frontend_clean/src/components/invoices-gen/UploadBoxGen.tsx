import React from 'react'
import { Upload, X, FileText, Image, CheckCircle2 } from 'lucide-react'
import './UploadBoxGen.css'

export interface UploadFile {
  id: string
  name: string
  size: number
  type: string
  progress: number
  status: 'uploading' | 'completed' | 'error'
  speed?: number
}

interface UploadBoxGenProps {
  onFilesSelected?: (files: File[]) => void
}

export function UploadBoxGen({ onFilesSelected }: UploadBoxGenProps) {
  const [isDragOver, setIsDragOver] = React.useState(false)
  const [uploadFiles, setUploadFiles] = React.useState<UploadFile[]>([])
  const fileInputRef = React.useRef<HTMLInputElement>(null)

  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return '0 Bytes'
    const k = 1024
    const sizes = ['Bytes', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + ' ' + sizes[i]
  }

  const getFileIcon = (type: string) => {
    if (type.startsWith('image/')) {
      return <Image className="upload-box-gen__file-icon" />
    }
    return <FileText className="upload-box-gen__file-icon" />
  }

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setIsDragOver(true)
  }

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setIsDragOver(false)
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setIsDragOver(false)

    const files = Array.from(e.dataTransfer.files)
    handleFiles(files)
  }

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      const files = Array.from(e.target.files)
      handleFiles(files)
    }
  }

  const handleFiles = (files: File[]) => {
    const newUploadFiles: UploadFile[] = files.map((file) => ({
      id: `${file.name}-${Date.now()}-${Math.random()}`,
      name: file.name,
      size: file.size,
      type: file.type,
      progress: 0,
      status: 'uploading',
      speed: Math.floor(Math.random() * 100) + 50, // Mock speed
    }))

    setUploadFiles((prev) => [...prev, ...newUploadFiles])

    // Simulate upload progress
    newUploadFiles.forEach((uploadFile) => {
      simulateUpload(uploadFile.id)
    })

    if (onFilesSelected) {
      onFilesSelected(files)
    }
  }

  const simulateUpload = (fileId: string) => {
    let progress = 0
    const interval = setInterval(() => {
      progress += Math.random() * 15
      if (progress >= 100) {
        progress = 100
        setUploadFiles((prev) =>
          prev.map((file) =>
            file.id === fileId
              ? { ...file, progress: 100, status: 'completed' }
              : file
          )
        )
        clearInterval(interval)
      } else {
        setUploadFiles((prev) =>
          prev.map((file) =>
            file.id === fileId ? { ...file, progress: Math.round(progress) } : file
          )
        )
      }
    }, 200)
  }

  const handleRemoveFile = (fileId: string) => {
    setUploadFiles((prev) => prev.filter((file) => file.id !== fileId))
  }

  const handleClick = () => {
    fileInputRef.current?.click()
  }

  return (
    <div className="upload-box-gen">
      {/* Left: Drag & Drop Zone */}
      <div
        className={`upload-box-gen__dropzone ${isDragOver ? 'upload-box-gen__dropzone--active' : ''}`}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={handleClick}
      >
        <input
          ref={fileInputRef}
          type="file"
          multiple
          className="upload-box-gen__file-input"
          onChange={handleFileInput}
          accept=".pdf,.jpg,.jpeg,.png,.heic"
        />
        <div className="upload-box-gen__dropzone-content">
          <div className="upload-box-gen__icon-wrapper">
            <Upload className="upload-box-gen__upload-icon" />
          </div>
          <div className="upload-box-gen__dropzone-text invoices-gen__body invoices-gen__text-muted">
            Drag files to upload
          </div>
          <button
            type="button"
            className="upload-box-gen__choose-button owlin-btn owlin-btn--primary"
            onClick={(e) => {
              e.stopPropagation()
              handleClick()
            }}
          >
            Choose File
          </button>
        </div>
      </div>

      {/* Right: Upload Progress List */}
      {uploadFiles.length > 0 && (
        <div className="upload-box-gen__progress-list">
          <div className="upload-box-gen__progress-title invoices-gen__label">
            Uploading
          </div>
          <div className="upload-box-gen__progress-items">
            {uploadFiles.map((file) => (
              <div key={file.id} className="upload-box-gen__progress-item">
                <div className="upload-box-gen__progress-item-left">
                  {getFileIcon(file.type)}
                  <div className="upload-box-gen__progress-item-info">
                    <div className="upload-box-gen__progress-item-name invoices-gen__body">
                      {file.name}
                    </div>
                    <div className="upload-box-gen__progress-item-meta invoices-gen__micro invoices-gen__text-soft">
                      {formatFileSize(file.size)}
                    </div>
                  </div>
                </div>
                <div className="upload-box-gen__progress-item-right">
                  {file.status === 'uploading' && (
                    <>
                      <div className="upload-box-gen__progress-bar">
                        <div
                          className="upload-box-gen__progress-bar-fill"
                          style={{ width: `${file.progress}%` }}
                        />
                      </div>
                      <div className="upload-box-gen__progress-status invoices-gen__micro invoices-gen__text-muted">
                        {file.progress}% done • {file.speed}KB/sec
                      </div>
                    </>
                  )}
                  {file.status === 'completed' && (
                    <div className="upload-box-gen__progress-status upload-box-gen__progress-status--completed invoices-gen__micro">
                      <CheckCircle2 className="upload-box-gen__check-icon" />
                      Completed
                    </div>
                  )}
                  <button
                    type="button"
                    className="upload-box-gen__remove-button"
                    onClick={() => handleRemoveFile(file.id)}
                    aria-label="Remove file"
                  >
                    <X className="upload-box-gen__remove-icon" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

