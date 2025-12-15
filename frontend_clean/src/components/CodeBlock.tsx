import { useState } from 'react'

interface CodeBlockProps {
  file?: string
  snippet: string
  language?: string
}

export function CodeBlock({ file, snippet, language = 'text' }: CodeBlockProps) {
  const [copied, setCopied] = useState(false)

  const copyToClipboard = () => {
    navigator.clipboard.writeText(snippet)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div
      style={{
        margin: '16px 0',
        borderRadius: '12px',
        overflow: 'hidden',
        border: '1px solid rgba(255, 255, 255, 0.1)',
        background: 'linear-gradient(135deg, #1e1e1e, #2a2a2a)',
        boxShadow: '0 4px 16px rgba(0, 0, 0, 0.3), inset 0 1px 0 rgba(255, 255, 255, 0.05)',
      }}
    >
      {file && (
        <div
          style={{
            padding: '10px 14px',
            background: 'linear-gradient(135deg, #2d2d2d, #252525)',
            borderBottom: '1px solid rgba(255, 255, 255, 0.1)',
            fontSize: '12px',
            color: 'rgba(255, 255, 255, 0.6)',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
          }}
        >
          <span style={{ 
            fontFamily: 'monospace',
            fontWeight: 500,
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
          }}>
            <span style={{ fontSize: '14px' }}>📄</span>
            {file}
          </span>
          <button
            onClick={copyToClipboard}
            style={{
              padding: '6px 12px',
              background: copied 
                ? 'rgba(20, 184, 166, 0.2)'
                : 'rgba(61, 61, 61, 0.8)',
              backdropFilter: 'blur(10px)',
              color: copied ? '#14b8a6' : 'rgba(255, 255, 255, 0.87)',
              border: copied 
                ? '1px solid rgba(20, 184, 166, 0.4)'
                : '1px solid rgba(255, 255, 255, 0.1)',
              borderRadius: '6px',
              cursor: 'pointer',
              fontSize: '11px',
              fontWeight: 500,
              transition: 'all 0.2s',
              display: 'flex',
              alignItems: 'center',
              gap: '4px',
            }}
            onMouseEnter={(e) => {
              if (!copied) {
                e.currentTarget.style.background = 'rgba(61, 61, 61, 1)'
                e.currentTarget.style.transform = 'scale(1.05)'
              }
            }}
            onMouseLeave={(e) => {
              if (!copied) {
                e.currentTarget.style.background = 'rgba(61, 61, 61, 0.8)'
                e.currentTarget.style.transform = 'scale(1)'
              }
            }}
          >
            {copied ? '✓ Copied' : '📋 Copy'}
          </button>
        </div>
      )}
      <pre
        style={{
          margin: 0,
          padding: '18px',
          overflow: 'auto',
          fontSize: '13px',
          lineHeight: '1.6',
          color: '#e5e5e5',
          fontFamily: '"SF Mono", "Monaco", "Consolas", "Courier New", monospace',
          background: '#1e1e1e',
        }}
      >
        <code style={{ color: '#e5e5e5' }}>{snippet}</code>
      </pre>
      {!file && (
        <div
          style={{
            padding: '8px 14px',
            background: 'linear-gradient(135deg, #2d2d2d, #252525)',
            borderTop: '1px solid rgba(255, 255, 255, 0.1)',
            display: 'flex',
            justifyContent: 'flex-end',
          }}
        >
          <button
            onClick={copyToClipboard}
            style={{
              padding: '6px 12px',
              background: copied 
                ? 'rgba(20, 184, 166, 0.2)'
                : 'rgba(61, 61, 61, 0.8)',
              backdropFilter: 'blur(10px)',
              color: copied ? '#14b8a6' : 'rgba(255, 255, 255, 0.87)',
              border: copied 
                ? '1px solid rgba(20, 184, 166, 0.4)'
                : '1px solid rgba(255, 255, 255, 0.1)',
              borderRadius: '6px',
              cursor: 'pointer',
              fontSize: '11px',
              fontWeight: 500,
              transition: 'all 0.2s',
              display: 'flex',
              alignItems: 'center',
              gap: '4px',
            }}
            onMouseEnter={(e) => {
              if (!copied) {
                e.currentTarget.style.background = 'rgba(61, 61, 61, 1)'
                e.currentTarget.style.transform = 'scale(1.05)'
              }
            }}
            onMouseLeave={(e) => {
              if (!copied) {
                e.currentTarget.style.background = 'rgba(61, 61, 61, 0.8)'
                e.currentTarget.style.transform = 'scale(1)'
              }
            }}
          >
            {copied ? '✓ Copied' : '📋 Copy'}
          </button>
        </div>
      )}
    </div>
  )
}

