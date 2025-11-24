import { memo } from 'react'
import './FilePreviewCard.css'

interface FilePreviewCardProps {
  file: File
  progress?: number
  status: 'pending' | 'uploading' | 'scanned' | 'error'
  metadata?: {
    supplier?: string
    value?: number
    date?: string
  }
  error?: string
  onRemove?: () => void
}

function getFileTypeIcon(fileName: string): string {
  const ext = fileName.split('.').pop()?.toLowerCase()
  if (ext === 'pdf') return '📄'
  if (['jpg', 'jpeg', 'png', 'heic', 'tiff', 'tif'].includes(ext || '')) return '🖼️'
  return '📎'
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

function isSupermarketReceipt(fileName: string, supplier?: string): boolean {
  const name = fileName.toLowerCase()
  const supplierLower = supplier?.toLowerCase() || ''
  const supermarketKeywords = ['tesco', 'sainsbury', 'asda', 'morrisons', 'aldi', 'lidl', 'co-op', 'waitrose', 'm&s', 'marks and spencer']
  return supermarketKeywords.some(keyword => name.includes(keyword) || supplierLower.includes(keyword))
}

export const FilePreviewCard = memo(function FilePreviewCard({
  file,
  progress = 0,
  status,
  metadata,
  error,
  onRemove,
}: FilePreviewCardProps) {
  const isReceipt = isSupermarketReceipt(file.name, metadata?.supplier)
  const isDualPurpose = isReceipt && status === 'scanned'

  return (
    <div className={`file-preview-card ${status} ${isDualPurpose ? 'dual-purpose' : ''}`}>
      <div className="file-preview-header">
        <div className="file-preview-icon">
          {getFileTypeIcon(file.name)}
        </div>
        <div className="file-preview-info">
          <div className="file-preview-name" title={file.name}>
            {file.name}
          </div>
          <div className="file-preview-meta">
            {formatFileSize(file.size)}
            {metadata?.supplier && (
              <>
                <span className="file-preview-separator">•</span>
                {metadata.supplier}
              </>
            )}
          </div>
        </div>
        {onRemove && status !== 'uploading' && (
          <button
            className="file-preview-remove"
            onClick={onRemove}
            aria-label="Remove file"
          >
            <svg
              width="16"
              height="16"
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
        )}
      </div>

      {status === 'uploading' && (
        <div className="file-preview-progress">
          <div className="file-preview-progress-bar">
            <div
              className="file-preview-progress-fill"
              style={{ width: `${progress}%` }}
            />
          </div>
          <div className="file-preview-progress-text">{progress}%</div>
        </div>
      )}

      {status === 'scanned' && metadata && (
        <div className="file-preview-details">
          {metadata.value !== undefined && (
            <div className="file-preview-detail">
              <span className="file-preview-detail-label">Value:</span>
              <span className="file-preview-detail-value">
                {new Intl.NumberFormat('en-GB', {
                  style: 'currency',
                  currency: 'GBP',
                }).format(metadata.value)}
              </span>
            </div>
          )}
          {metadata.date && (
            <div className="file-preview-detail">
              <span className="file-preview-detail-label">Date:</span>
              <span className="file-preview-detail-value">
                {new Date(metadata.date).toLocaleDateString('en-GB')}
              </span>
            </div>
          )}
        </div>
      )}

      {isDualPurpose && (
        <div className="file-preview-badges">
          <span className="file-preview-badge invoice-badge">Invoice</span>
          <span className="file-preview-badge delivery-badge">Delivery Note</span>
        </div>
      )}

      {status === 'error' && error && (
        <div className="file-preview-error">
          <svg
            width="16"
            height="16"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <circle cx="12" cy="12" r="10" />
            <line x1="12" y1="8" x2="12" y2="12" />
            <line x1="12" y1="16" x2="12.01" y2="16" />
          </svg>
          {error}
        </div>
      )}

      <div className={`file-preview-status status-${status}`}>
        {status === 'pending' && 'Pending'}
        {status === 'uploading' && 'Uploading...'}
        {status === 'scanned' && 'Scanned'}
        {status === 'error' && 'Error'}
      </div>
    </div>
  )
})

