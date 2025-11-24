import React from 'react'
import type { InvoiceMetadata } from '../lib/upload'

interface InvoiceDebugPanelProps {
  invoice: {
    id: string
    file: File
    metadata?: InvoiceMetadata
    uploadStartTime?: number
    uploadEndTime?: number
    uploadBytes?: number
  }
  requestLog: Array<{
    method: string
    url: string
    status: number
    duration: number
    timestamp: number
  }>
  onSimulateError?: () => void
}

export function InvoiceDebugPanel({ invoice, requestLog, onSimulateError }: InvoiceDebugPanelProps) {
  const metadata = invoice.metadata || {}
  const pages = metadata.pages || []
  const [activeTab, setActiveTab] = React.useState<'raw' | 'ocr'>('raw')

  const formatJSON = (obj: unknown): string => {
    try {
      return JSON.stringify(obj, null, 2)
    } catch (error) {
      return `Error formatting JSON: ${error instanceof Error ? error.message : 'Unknown error'}`
    }
  }

  // Show raw backend response if available, otherwise show normalized metadata
  const rawData = metadata.raw || metadata
  const jsonString = formatJSON(rawData)
  const isLarge = jsonString.length > 200 * 1024 // 200KB
  const [showFullJSON, setShowFullJSON] = React.useState(!isLarge)
  const displayJSON = showFullJSON ? jsonString : jsonString.substring(0, 200 * 1024)

  // Extract OCR Preview text (in priority order)
  const getOCRPreview = (): string => {
    // First, try to concat first 2 pages text
    if (pages && pages.length > 0) {
      const pagesWithText = pages.filter(p => p.text)
      if (pagesWithText.length > 0) {
        return pagesWithText
          .slice(0, 2)
          .map((p, idx) => `=== Page ${p.index ?? idx} ===\n${p.text}`)
          .join('\n\n')
      }
    }

    // Fallback to raw fields
    const raw = metadata.raw || {}
    if (raw.ocr_text) return raw.ocr_text
    if (raw.text) return raw.text
    if (raw.extracted_text) return raw.extracted_text

    return ''
  }

  const ocrPreview = getOCRPreview()

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text).catch(err => {
      console.error('Failed to copy:', err)
    })
  }

  const uploadDuration =
    invoice.uploadStartTime && invoice.uploadEndTime
      ? invoice.uploadEndTime - invoice.uploadStartTime
      : null

  return (
    <div
      className="debug-panel"
      style={{
        padding: '24px',
        backgroundColor: 'rgba(0, 0, 0, 0.02)',
        borderTop: '1px solid rgba(0, 0, 0, 0.1)',
        maxHeight: '400px',
        overflowY: 'auto',
      }}
    >
      <h3 style={{ fontSize: '18px', fontWeight: 600, marginBottom: '16px' }}>Developer Debug Panel</h3>

      {/* Tabs */}
      <div style={{ display: 'flex', gap: '8px', marginBottom: '16px', borderBottom: '1px solid rgba(0, 0, 0, 0.1)' }}>
        <button
          onClick={() => setActiveTab('raw')}
          style={{
            padding: '8px 16px',
            border: 'none',
            backgroundColor: 'transparent',
            cursor: 'pointer',
            fontSize: '14px',
            fontWeight: 500,
            borderBottom: activeTab === 'raw' ? '2px solid rgb(59, 130, 246)' : '2px solid transparent',
            color: activeTab === 'raw' ? 'rgb(59, 130, 246)' : 'rgba(0, 0, 0, 0.6)',
            transition: 'all 0.2s',
          }}
        >
          Raw JSON
        </button>
        <button
          onClick={() => setActiveTab('ocr')}
          style={{
            padding: '8px 16px',
            border: 'none',
            backgroundColor: 'transparent',
            cursor: 'pointer',
            fontSize: '14px',
            fontWeight: 500,
            borderBottom: activeTab === 'ocr' ? '2px solid rgb(59, 130, 246)' : '2px solid transparent',
            color: activeTab === 'ocr' ? 'rgb(59, 130, 246)' : 'rgba(0, 0, 0, 0.6)',
            transition: 'all 0.2s',
          }}
        >
          OCR Preview
        </button>
      </div>

      {/* Tab Content: Raw JSON */}
      {activeTab === 'raw' && (
        <div style={{ marginBottom: '24px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
            <h4 style={{ fontSize: '14px', fontWeight: 600 }}>Raw Backend Response</h4>
            <div style={{ display: 'flex', gap: '8px' }}>
              <button
                onClick={() => copyToClipboard(jsonString)}
                style={{
                  padding: '4px 8px',
                  fontSize: '12px',
                  border: '1px solid rgba(0, 0, 0, 0.1)',
                  borderRadius: '4px',
                  backgroundColor: 'white',
                  cursor: 'pointer',
                }}
              >
                Copy
              </button>
              {isLarge && (
                <button
                  onClick={() => setShowFullJSON(!showFullJSON)}
                  style={{
                    padding: '4px 8px',
                    fontSize: '12px',
                    border: '1px solid rgba(0, 0, 0, 0.1)',
                    borderRadius: '4px',
                    backgroundColor: 'white',
                    cursor: 'pointer',
                  }}
                >
                  {showFullJSON ? 'Show Less' : 'Show More'}
                </button>
              )}
            </div>
          </div>
          <pre
            style={{
              padding: '12px',
              backgroundColor: 'rgba(0, 0, 0, 0.05)',
              borderRadius: '6px',
              fontSize: '12px',
              fontFamily: 'monospace',
              overflowX: 'auto',
              maxHeight: '300px',
              overflowY: 'auto',
              whiteSpace: 'pre-wrap',
              wordBreak: 'break-word',
            }}
          >
            {displayJSON}
            {isLarge && !showFullJSON && '\n\n... (truncated, click "Show More" to view full JSON) ...'}
          </pre>
        </div>
      )}

      {/* Tab Content: OCR Preview */}
      {activeTab === 'ocr' && (
        <div style={{ marginBottom: '24px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
            <h4 style={{ fontSize: '14px', fontWeight: 600 }}>OCR Text Preview</h4>
            {ocrPreview && (
              <button
                onClick={() => copyToClipboard(ocrPreview)}
                style={{
                  padding: '4px 8px',
                  fontSize: '12px',
                  border: '1px solid rgba(0, 0, 0, 0.1)',
                  borderRadius: '4px',
                  backgroundColor: 'white',
                  cursor: 'pointer',
                }}
              >
                Copy
              </button>
            )}
          </div>
          {ocrPreview ? (
            <pre
              style={{
                padding: '12px',
                backgroundColor: 'rgba(0, 0, 0, 0.05)',
                borderRadius: '6px',
                fontSize: '12px',
                fontFamily: 'monospace',
                overflowX: 'auto',
                maxHeight: '300px',
                overflowY: 'auto',
                whiteSpace: 'pre-wrap',
                wordBreak: 'break-word',
              }}
            >
              {ocrPreview}
            </pre>
          ) : (
            <div
              style={{
                padding: '24px',
                backgroundColor: 'rgba(0, 0, 0, 0.05)',
                borderRadius: '6px',
                fontSize: '14px',
                color: 'rgba(0, 0, 0, 0.5)',
                fontStyle: 'italic',
                textAlign: 'center',
              }}
            >
              No OCR text returned by backend.
            </div>
          )}
        </div>
      )}

      {/* Per-page Metrics */}
      <div style={{ marginBottom: '24px' }}>
        <h4 style={{ fontSize: '14px', fontWeight: 600, marginBottom: '8px' }}>Per-page Metrics</h4>
        {pages.length > 0 ? (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {pages.map((page, idx) => (
              <div
                key={idx}
                style={{
                  padding: '8px',
                  backgroundColor: 'white',
                  borderRadius: '4px',
                  fontSize: '12px',
                  fontFamily: 'monospace',
                }}
              >
                Page {page.index ?? idx + 1}: confidence={page.confidence?.toFixed(1) ?? 'N/A'}%, words={page.words ?? 'N/A'}, psm={page.psm ?? 'N/A'}
              </div>
            ))}
          </div>
        ) : (
          <div style={{ padding: '12px', backgroundColor: 'rgba(0, 0, 0, 0.05)', borderRadius: '6px', fontSize: '12px', color: 'rgba(0, 0, 0, 0.6)' }}>
            Unavailable from backend
          </div>
        )}
      </div>

      {/* Network Timings */}
      <div style={{ marginBottom: '24px' }}>
        <h4 style={{ fontSize: '14px', fontWeight: 600, marginBottom: '8px' }}>Network Timings</h4>
        {uploadDuration !== null ? (
          <div
            style={{
              padding: '12px',
              backgroundColor: 'white',
              borderRadius: '6px',
              fontSize: '12px',
              fontFamily: 'monospace',
            }}
          >
            <div>Start: {invoice.uploadStartTime ? new Date(invoice.uploadStartTime).toISOString() : 'N/A'}</div>
            <div>End: {invoice.uploadEndTime ? new Date(invoice.uploadEndTime).toISOString() : 'N/A'}</div>
            <div>Duration: {uploadDuration}ms</div>
            {invoice.uploadBytes && <div>Bytes sent: {invoice.uploadBytes.toLocaleString()}</div>}
          </div>
        ) : (
          <div style={{ padding: '12px', backgroundColor: 'rgba(0, 0, 0, 0.05)', borderRadius: '6px', fontSize: '12px', color: 'rgba(0, 0, 0, 0.6)' }}>
            Timings not available
          </div>
        )}
      </div>

      {/* Last 5 Requests Log */}
      <div style={{ marginBottom: '24px' }}>
        <h4 style={{ fontSize: '14px', fontWeight: 600, marginBottom: '8px' }}>Last 5 Requests</h4>
        {requestLog.length > 0 ? (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
            {requestLog.slice(-5).reverse().map((req, idx) => (
              <div
                key={idx}
                style={{
                  padding: '8px',
                  backgroundColor: 'white',
                  borderRadius: '4px',
                  fontSize: '12px',
                  fontFamily: 'monospace',
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                }}
              >
                <span>
                  {req.method} {req.url} → {req.status}
                </span>
                <span style={{ color: 'rgba(0, 0, 0, 0.6)' }}>{req.duration}ms</span>
              </div>
            ))}
          </div>
        ) : (
          <div style={{ padding: '12px', backgroundColor: 'rgba(0, 0, 0, 0.05)', borderRadius: '6px', fontSize: '12px', color: 'rgba(0, 0, 0, 0.6)' }}>
            No requests logged
          </div>
        )}
      </div>

      {/* Simulate Error Button */}
      {onSimulateError && (
        <div>
          <button
            onClick={onSimulateError}
            style={{
              padding: '8px 16px',
              borderRadius: '6px',
              border: '1px solid rgba(239, 68, 68, 0.3)',
              backgroundColor: 'rgba(239, 68, 68, 0.1)',
              color: 'rgb(220, 38, 38)',
              fontSize: '14px',
              fontWeight: 500,
              cursor: 'pointer',
            }}
          >
            Simulate Error (DEV only)
          </button>
        </div>
      )}
    </div>
  )
}

