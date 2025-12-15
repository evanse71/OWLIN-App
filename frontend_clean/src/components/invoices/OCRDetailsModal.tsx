import { useState, useEffect } from 'react'
import { X } from 'lucide-react'
import { fetchOCRDetails } from '../../lib/api'
import './Modal.css'

interface OCRDetails {
  confidence?: number
  extractedText?: string
  processingTime?: number
  pages?: number
  ocrEngine?: string
  metadata?: Record<string, any>
}

interface OCRDetailsModalProps {
  isOpen: boolean
  onClose: () => void
  invoiceId: string
}

export function OCRDetailsModal({ isOpen, onClose, invoiceId }: OCRDetailsModalProps) {
  const [ocrDetails, setOcrDetails] = useState<OCRDetails | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (isOpen && invoiceId) {
      loadOCRDetails()
    }
  }, [isOpen, invoiceId])

  const loadOCRDetails = async () => {
    setLoading(true)
    setError(null)
    try {
      const details = await fetchOCRDetails(invoiceId)
      setOcrDetails(details)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load OCR details')
    } finally {
      setLoading(false)
    }
  }

  if (!isOpen) return null

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-container large" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2 className="modal-title">OCR Processing Details</h2>
          <button className="modal-close-button" onClick={onClose}>
            <X size={20} />
          </button>
        </div>

        <div className="modal-body">
          {loading ? (
            <div className="modal-loading">Loading OCR details...</div>
          ) : error ? (
            <div className="modal-error">{error}</div>
          ) : ocrDetails ? (
            <>
              <div className="modal-form-row">
                {ocrDetails.confidence !== undefined && (
                  <div className="modal-form-group">
                    <label className="modal-form-label">Confidence Score</label>
                    <div style={{ padding: '10px 14px', background: 'var(--bg-secondary)', borderRadius: '8px', fontSize: '14px' }}>
                      {Math.round(ocrDetails.confidence * 100)}%
                    </div>
                  </div>
                )}

                {ocrDetails.pages !== undefined && (
                  <div className="modal-form-group">
                    <label className="modal-form-label">Pages Processed</label>
                    <div style={{ padding: '10px 14px', background: 'var(--bg-secondary)', borderRadius: '8px', fontSize: '14px' }}>
                      {ocrDetails.pages}
                    </div>
                  </div>
                )}
              </div>

              {ocrDetails.processingTime !== undefined && (
                <div className="modal-form-group">
                  <label className="modal-form-label">Processing Time</label>
                  <div style={{ padding: '10px 14px', background: 'var(--bg-secondary)', borderRadius: '8px', fontSize: '14px' }}>
                    {ocrDetails.processingTime.toFixed(2)}s
                  </div>
                </div>
              )}

              {ocrDetails.ocrEngine && (
                <div className="modal-form-group">
                  <label className="modal-form-label">OCR Engine</label>
                  <div style={{ padding: '10px 14px', background: 'var(--bg-secondary)', borderRadius: '8px', fontSize: '14px' }}>
                    {ocrDetails.ocrEngine}
                  </div>
                </div>
              )}

              {ocrDetails.extractedText && (
                <div className="modal-form-group">
                  <label className="modal-form-label">Extracted Text</label>
                  <textarea
                    className="modal-form-textarea"
                    value={ocrDetails.extractedText}
                    readOnly
                    style={{ minHeight: '200px', fontFamily: 'monospace', fontSize: '12px' }}
                  />
                </div>
              )}

              {ocrDetails.metadata && Object.keys(ocrDetails.metadata).length > 0 && (
                <div className="modal-form-group">
                  <label className="modal-form-label">Additional Metadata</label>
                  <pre
                    style={{
                      padding: '12px',
                      background: 'var(--bg-secondary)',
                      borderRadius: '8px',
                      fontSize: '12px',
                      overflow: 'auto',
                      maxHeight: '300px',
                      fontFamily: 'monospace',
                    }}
                  >
                    {JSON.stringify(ocrDetails.metadata, null, 2)}
                  </pre>
                </div>
              )}
            </>
          ) : null}
        </div>

        <div className="modal-footer">
          <button className="modal-button-secondary" onClick={onClose}>
            Close
          </button>
        </div>
      </div>
    </div>
  )
}

