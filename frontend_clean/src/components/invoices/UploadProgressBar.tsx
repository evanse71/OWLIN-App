import { useEffect, useState } from 'react'
import './UploadProgressBar.css'

export interface UploadProgressBarProps {
  fileName: string
  percentage: number
  isComplete: boolean
  isProcessing?: boolean
  hasError?: boolean // New prop to indicate error state
  errorMessage?: string // Error message to display
  docId?: string // Document ID for retry functionality
  onComplete?: () => void
  onRetry?: (docId: string) => void // Callback when retry button is clicked
  queuePosition?: number // Position in queue (undefined if active)
  queuedCount?: number // Total files in queue
}

export function UploadProgressBar({
  fileName,
  percentage,
  isComplete,
  isProcessing,
  hasError,
  errorMessage,
  docId,
  onComplete,
  onRetry,
  queuePosition,
  queuedCount,
}: UploadProgressBarProps) {
  const [estimatedTimeLeft, setEstimatedTimeLeft] = useState<string>('Calculating...')
  const [startTime] = useState(Date.now())
  const [processingStartTime, setProcessingStartTime] = useState<number | null>(null)
  const [uploadCompleteTime, setUploadCompleteTime] = useState<number | null>(null)
  const [isVisible, setIsVisible] = useState(true)
  const [isFadingOut, setIsFadingOut] = useState(false)

  // Track when processing starts and upload completes
  useEffect(() => {
    if (isProcessing && !processingStartTime) {
      setProcessingStartTime(Date.now())
    }
    // Track when upload completes (around 45% progress)
    if (percentage >= 45 && percentage < 90 && !uploadCompleteTime) {
      setUploadCompleteTime(Date.now())
    }
  }, [isProcessing, processingStartTime, percentage, uploadCompleteTime])

  // Calculate estimated time remaining
  useEffect(() => {
    if (isProcessing) {
      // Show processing time with estimated remaining time
      if (processingStartTime) {
        const elapsed = Math.floor((Date.now() - processingStartTime) / 1000)
        // OCR typically takes 40-80 seconds based on documentation
        // Use adaptive estimation: start with 60s estimate, adjust based on elapsed
        let estimatedTotal = 65 // Conservative estimate: 65s total OCR time
        let estimatedRemaining = Math.max(5, estimatedTotal - elapsed)
        
        // If we've been processing longer than expected, increase estimate
        if (elapsed > 50) {
          estimatedTotal = 80 // Increase to 80s if taking longer
          estimatedRemaining = Math.max(5, estimatedTotal - elapsed)
        } else if (elapsed > 30) {
          estimatedTotal = 70 // Increase to 70s if taking longer
          estimatedRemaining = Math.max(5, estimatedTotal - elapsed)
        }
        
        if (estimatedRemaining > 5) {
          setEstimatedTimeLeft(`${elapsed}s elapsed • ~${Math.ceil(estimatedRemaining)}s remaining`)
        } else {
          setEstimatedTimeLeft(`${elapsed}s elapsed`)
        }
      } else {
        setEstimatedTimeLeft('Processing...')
      }
    } else if (percentage > 0 && percentage < 100) {
      // For staged progress, estimate based on typical upload + processing times
      const elapsed = (Date.now() - startTime) / 1000 // seconds
      
      // Staged progress stages:
      // 0-20%: Upload starting (estimate 5-10s for upload)
      // 20-45%: Upload in progress (estimate 5-10s total for upload)
      // 45-90%: Transition to OCR (estimate 60-70s for OCR)
      // 90%+: OCR processing (estimate 40-60s remaining)
      
      let estimatedRemaining = 0
      
      if (percentage < 20) {
        // Just started: estimate 10s upload + 60s OCR = 70s total
        estimatedRemaining = Math.max(10, 70 - elapsed)
      } else if (percentage < 45) {
        // Upload phase: estimate 8s upload + 60s OCR = 68s total
        estimatedRemaining = Math.max(10, 68 - elapsed)
      } else if (percentage < 90) {
        // Transition phase: upload done, OCR starting
        // Estimate 60-65s for OCR processing
        const uploadTime = uploadCompleteTime ? (uploadCompleteTime - startTime) / 1000 : 8
        const ocrElapsed = elapsed - uploadTime
        estimatedRemaining = Math.max(10, 65 - ocrElapsed)
      } else {
        // At 90%, OCR is in progress
        // Estimate 40-50s remaining for OCR
        const uploadTime = uploadCompleteTime ? (uploadCompleteTime - startTime) / 1000 : 8
        const ocrElapsed = elapsed - uploadTime
        estimatedRemaining = Math.max(10, 50 - ocrElapsed)
      }
      
      // Ensure minimum estimate
      estimatedRemaining = Math.max(10, estimatedRemaining)
      
      if (estimatedRemaining < 60) {
        setEstimatedTimeLeft(`~${Math.ceil(estimatedRemaining)}s`)
      } else {
        const minutes = Math.ceil(estimatedRemaining / 60)
        setEstimatedTimeLeft(`~${minutes}m`)
      }
    } else if (percentage >= 100 && !isProcessing) {
      setEstimatedTimeLeft('Complete')
    }
  }, [percentage, startTime, isComplete, isProcessing, processingStartTime, uploadCompleteTime])

  // Auto-hide after completion with smooth fade-out
  useEffect(() => {
    if (isComplete) {
      // Start fade-out after 1.5 seconds
      const fadeTimer = setTimeout(() => {
        setIsFadingOut(true)
      }, 1500)

      // Actually remove from DOM after fade completes
      const hideTimer = setTimeout(() => {
        setIsVisible(false)
        if (onComplete) {
          onComplete()
        }
      }, 3000) // Total: 1.5s delay + 1.5s fade = 3s

      return () => {
        clearTimeout(fadeTimer)
        clearTimeout(hideTimer)
      }
    }
  }, [isComplete, onComplete])

  if (!isVisible) {
    return null
  }

  // If queued, show queue status instead of progress
  if (queuePosition !== undefined && queuedCount !== undefined) {
    return (
      <div className={`upload-progress-bar queued`}>
        <div className="upload-progress-header">
          <div className="upload-progress-icon">
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
              <circle cx="8" cy="8" r="7" stroke="currentColor" strokeWidth="1.5" opacity="0.3" />
            </svg>
          </div>
          <div className="upload-progress-info">
            <div className="upload-progress-filename">{fileName}</div>
            <div className="upload-progress-stats">
              <span className="upload-progress-status">Queued ({queuePosition} of {queuedCount})</span>
            </div>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className={`upload-progress-bar ${isComplete ? 'complete' : ''} ${isProcessing ? 'processing' : ''} ${isFadingOut ? 'fading-out' : ''}`}>
      <div className="upload-progress-header">
        <div className="upload-progress-icon">
          {isComplete ? (
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
              <circle cx="8" cy="8" r="7" stroke="currentColor" strokeWidth="1.5" />
              <path d="M5 8L7 10L11 6" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          ) : (
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none" className="upload-spinner">
              <circle cx="8" cy="8" r="7" stroke="currentColor" strokeWidth="1.5" opacity="0.2" />
              <path d="M15 8a7 7 0 0 1-7 7" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
            </svg>
          )}
        </div>
        <div className="upload-progress-info">
          <div className="upload-progress-filename">{fileName}</div>
          <div className="upload-progress-stats">
            {isProcessing ? (
              <>
                <span className="upload-progress-status">{hasError ? 'OCR Failed' : 'Processing OCR'}</span>
                <span className="upload-progress-separator">•</span>
                <span className="upload-progress-time" title={errorMessage || undefined}>
                  {hasError ? (errorMessage ? errorMessage.substring(0, 50) + (errorMessage.length > 50 ? '...' : '') : 'Check backend logs') : estimatedTimeLeft}
                </span>
                {hasError && docId && onRetry && (
                  <>
                    <span className="upload-progress-separator">•</span>
                    <button
                      className="upload-progress-retry"
                      onClick={(e) => {
                        e.stopPropagation()
                        onRetry(docId)
                      }}
                      title="Retry OCR processing"
                    >
                      Retry
                    </button>
                  </>
                )}
              </>
            ) : (
              <>
                <span className="upload-progress-percentage">{Math.round(percentage)}%</span>
                <span className="upload-progress-separator">•</span>
                <span className="upload-progress-time">{estimatedTimeLeft}</span>
              </>
            )}
          </div>
        </div>
      </div>
      
      <div className="upload-progress-track">
        <div 
          className={`upload-progress-fill ${isProcessing ? 'processing-pulse' : ''} ${hasError ? 'error' : ''}`}
          style={{ 
            // Show actual percentage, not forced 100% when processing
            // Only show 100% if percentage is actually 100 or if complete
            width: isComplete ? '100%' : `${Math.min(100, Math.max(0, percentage))}%`,
            transition: isComplete ? 'width 0.3s ease-out' : isProcessing ? 'none' : 'width 0.15s linear',
            animation: isProcessing && !hasError ? 'processingPulse 2s ease-in-out infinite' : undefined
          }}
        />
      </div>
    </div>
  )
}

