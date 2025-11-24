import { CodeBlock } from './CodeBlock'
import { useState } from 'react'

interface ChatMessageProps {
  role: 'user' | 'assistant'
  content: string
  codeReferences?: Array<{
    file: string
    lines?: number[]
    snippet: string
  }>
  error?: boolean
  retryable?: boolean
  requiresOllama?: boolean
  explorationMode?: boolean
  explorationMetadata?: {
    mode?: string
    files_searched?: number
    files_read?: string[]
    searches_executed?: number
    search_terms?: string[]
    findings_count?: number
    exploration_time?: number
    timed_out?: boolean
  }
  onRetry?: () => void
}

export function ChatMessage({ role, content, codeReferences, error, retryable, requiresOllama, explorationMode, explorationMetadata, onRetry }: ChatMessageProps) {
  const isUser = role === 'user'
  const [copied, setCopied] = useState(false)
  const [showCopyButton, setShowCopyButton] = useState(false)

  const copyToClipboard = async () => {
    try {
      await navigator.clipboard.writeText(content)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch (error) {
      console.error('Failed to copy:', error)
    }
  }

  // Enhanced markdown-like rendering
  const renderContent = (text: string) => {
    const parts = text.split('```')
    return parts.map((part, index) => {
      if (index % 2 === 0) {
        // Regular text with markdown-like formatting
        let processed = part
        // Bold **text**
        processed = processed.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
        // Italic *text*
        processed = processed.replace(/\*(.+?)\*/g, '<em>$1</em>')
        // Code inline `code`
        processed = processed.replace(/`(.+?)`/g, '<code style="background: rgba(0,0,0,0.1); padding: 2px 6px; border-radius: 4px; font-family: monospace; font-size: 0.9em;">$1</code>')
        // Headers
        processed = processed.replace(/^### (.+)$/gm, '<h3 style="font-size: 1.1em; font-weight: 600; margin: 12px 0 8px 0;">$1</h3>')
        processed = processed.replace(/^## (.+)$/gm, '<h2 style="font-size: 1.2em; font-weight: 600; margin: 16px 0 10px 0;">$1</h2>')
        processed = processed.replace(/^# (.+)$/gm, '<h1 style="font-size: 1.3em; font-weight: 600; margin: 20px 0 12px 0;">$1</h1>')
        // Lists
        processed = processed.replace(/^[-*] (.+)$/gm, '<li style="margin: 4px 0; padding-left: 8px;">$1</li>')
        processed = processed.replace(/(<li.*<\/li>)/s, '<ul style="margin: 8px 0; padding-left: 20px;">$1</ul>')
        // Numbered lists
        processed = processed.replace(/^\d+\. (.+)$/gm, '<li style="margin: 4px 0; padding-left: 8px;">$1</li>')
        // Line breaks
        processed = processed.replace(/\n/g, '<br />')
        
        return <div key={index} dangerouslySetInnerHTML={{ __html: processed }} style={{ whiteSpace: 'pre-wrap' }} />
      } else {
        // Code block
        const lines = part.split('\n')
        const language = lines[0]?.trim() || 'text'
        const code = lines.slice(1).join('\n')
        return (
          <CodeBlock key={index} snippet={code} language={language} />
        )
      }
    })
  }

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        marginBottom: '20px',
        alignItems: isUser ? 'flex-end' : 'flex-start',
        gap: '4px',
        position: 'relative',
      }}
      onMouseEnter={() => !isUser && setShowCopyButton(true)}
      onMouseLeave={() => !isUser && setShowCopyButton(false)}
    >
      {/* Avatar/Indicator */}
      {!isUser && (
        <div
          style={{
            width: '28px',
            height: '28px',
            borderRadius: '50%',
            background: 'linear-gradient(135deg, rgba(59, 130, 246, 0.2), rgba(37, 99, 235, 0.2))',
            backdropFilter: 'blur(10px)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: '14px',
            marginBottom: '4px',
            border: '1px solid rgba(59, 130, 246, 0.2)',
            boxShadow: '0 2px 8px rgba(59, 130, 246, 0.15)',
          }}
        >
          🤖
        </div>
      )}
      
      <div
        style={{
          maxWidth: '85%',
          padding: '14px 18px',
          borderRadius: isUser ? '20px 20px 4px 20px' : '20px 20px 20px 4px',
          background: error
            ? 'linear-gradient(135deg, rgba(254, 242, 242, 0.95), rgba(254, 226, 226, 0.95))'
            : isUser
            ? 'linear-gradient(135deg, rgba(59, 130, 246, 0.95), rgba(37, 99, 235, 0.95))'
            : 'rgba(255, 255, 255, 0.85)',
          backdropFilter: 'blur(20px) saturate(180%)',
          WebkitBackdropFilter: 'blur(20px) saturate(180%)',
          color: error ? '#dc2626' : (isUser ? '#fff' : '#1f2937'),
          fontSize: '14px',
          lineHeight: '1.6',
          wordWrap: 'break-word',
          border: error
            ? '1px solid rgba(254, 202, 202, 0.5)'
            : isUser
            ? '1px solid rgba(255, 255, 255, 0.2)'
            : '1px solid rgba(0, 0, 0, 0.08)',
          boxShadow: error
            ? '0 4px 12px rgba(220, 38, 38, 0.15)'
            : isUser
            ? '0 4px 16px rgba(59, 130, 246, 0.3), inset 0 1px 0 rgba(255, 255, 255, 0.2)'
            : '0 2px 12px rgba(0, 0, 0, 0.08)',
          transition: 'all 0.2s ease',
          position: 'relative',
        }}
      >
        {/* Copy button - ChatGPT style (top right corner) */}
        {!isUser && (showCopyButton || copied) && (
          <button
            onClick={copyToClipboard}
            style={{
              position: 'absolute',
              top: '8px',
              right: '8px',
              padding: '6px 10px',
              background: copied 
                ? 'rgba(16, 185, 129, 0.1)' 
                : 'rgba(255, 255, 255, 0.8)',
              backdropFilter: 'blur(10px)',
              border: copied
                ? '1px solid rgba(16, 185, 129, 0.3)'
                : '1px solid rgba(0, 0, 0, 0.1)',
              borderRadius: '6px',
              cursor: 'pointer',
              fontSize: '12px',
              color: copied ? '#10b981' : '#6b7280',
              fontWeight: 500,
              transition: 'all 0.2s ease',
              display: 'flex',
              alignItems: 'center',
              gap: '4px',
              opacity: showCopyButton || copied ? 1 : 0,
              transform: showCopyButton || copied ? 'scale(1)' : 'scale(0.9)',
              zIndex: 10,
              boxShadow: '0 2px 8px rgba(0, 0, 0, 0.1)',
            }}
            onMouseEnter={(e) => {
              if (!copied) {
                e.currentTarget.style.background = 'rgba(255, 255, 255, 0.95)'
                e.currentTarget.style.transform = 'scale(1.05)'
              }
            }}
            onMouseLeave={(e) => {
              if (!copied) {
                e.currentTarget.style.background = 'rgba(255, 255, 255, 0.8)'
                e.currentTarget.style.transform = 'scale(1)'
              }
            }}
          >
            {copied ? (
              <>
                <span>✓</span>
                <span>Copied</span>
              </>
            ) : (
              <>
                <span>📋</span>
                <span>Copy</span>
              </>
            )}
          </button>
        )}

        {/* Render content with enhanced markdown */}
        <div style={{ whiteSpace: 'pre-wrap' }}>
          {renderContent(content)}
        </div>
      </div>

      {/* Exploration metadata */}
      {explorationMode && explorationMetadata && (
        <div
          style={{
            marginTop: '10px',
            padding: '12px 16px',
            background: 'linear-gradient(135deg, rgba(239, 246, 255, 0.95), rgba(219, 234, 254, 0.95))',
            backdropFilter: 'blur(20px)',
            borderRadius: '14px',
            fontSize: '12px',
            color: '#1e40af',
            border: '1px solid rgba(191, 219, 254, 0.5)',
            boxShadow: '0 2px 8px rgba(59, 130, 246, 0.15)',
            maxWidth: '85%',
          }}
        >
          <div style={{ 
            fontWeight: 600, 
            marginBottom: '8px', 
            fontSize: '13px',
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
          }}>
            <span style={{
              width: '20px',
              height: '20px',
              borderRadius: '50%',
              background: 'linear-gradient(135deg, #3b82f6, #60a5fa)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: '12px',
              boxShadow: '0 2px 8px rgba(59, 130, 246, 0.3)',
            }}>🔍</span>
            Exploration Mode {explorationMetadata.mode === 'multi_turn' ? '(Multi-turn)' : ''}
          </div>
          <div style={{ 
            display: 'grid', 
            gridTemplateColumns: 'repeat(auto-fit, minmax(120px, 1fr))',
            gap: '8px',
            marginBottom: '8px',
          }}>
            {explorationMetadata.searches_executed !== undefined && (
              <div style={{
                padding: '6px 10px',
                background: 'rgba(255, 255, 255, 0.6)',
                borderRadius: '8px',
                fontSize: '11px',
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
              }}>
                <span>🔎</span>
                <span><strong>{explorationMetadata.searches_executed}</strong> searches</span>
              </div>
            )}
            {explorationMetadata.files_searched !== undefined && (
              <div style={{
                padding: '6px 10px',
                background: 'rgba(255, 255, 255, 0.6)',
                borderRadius: '8px',
                fontSize: '11px',
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
              }}>
                <span>📁</span>
                <span><strong>{explorationMetadata.files_searched}</strong> files</span>
              </div>
            )}
            {explorationMetadata.findings_count !== undefined && (
              <div style={{
                padding: '6px 10px',
                background: 'rgba(255, 255, 255, 0.6)',
                borderRadius: '8px',
                fontSize: '11px',
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
              }}>
                <span>✨</span>
                <span><strong>{explorationMetadata.findings_count}</strong> findings</span>
              </div>
            )}
            {explorationMetadata.exploration_time !== undefined && (
              <div style={{
                padding: '6px 10px',
                background: 'rgba(255, 255, 255, 0.6)',
                borderRadius: '8px',
                fontSize: '11px',
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
              }}>
                <span>⏱️</span>
                <span><strong>{explorationMetadata.exploration_time}s</strong></span>
              </div>
            )}
          </div>
          {explorationMetadata.files_read && explorationMetadata.files_read.length > 0 && (
            <div style={{ 
              marginTop: '8px', 
              padding: '8px 12px',
              background: 'rgba(255, 255, 255, 0.6)',
              borderRadius: '8px',
              fontSize: '11px', 
              color: '#3b82f6' 
            }}>
              <strong style={{ display: 'block', marginBottom: '4px' }}>Files explored:</strong>
              <div style={{ 
                display: 'flex', 
                flexWrap: 'wrap', 
                gap: '4px',
                fontFamily: 'monospace',
                fontSize: '10px',
              }}>
                {explorationMetadata.files_read.slice(0, 5).map((file, idx) => (
                  <span 
                    key={idx}
                    style={{
                      padding: '2px 6px',
                      background: 'rgba(59, 130, 246, 0.1)',
                      borderRadius: '4px',
                      border: '1px solid rgba(59, 130, 246, 0.2)',
                    }}
                  >
                    {file}
                  </span>
                ))}
                {explorationMetadata.files_read.length > 5 && (
                  <span style={{
                    padding: '2px 6px',
                    background: 'rgba(59, 130, 246, 0.1)',
                    borderRadius: '4px',
                    border: '1px solid rgba(59, 130, 246, 0.2)',
                  }}>
                    +{explorationMetadata.files_read.length - 5} more
                  </span>
                )}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Code references */}
      {codeReferences && codeReferences.length > 0 && (
        <div
          style={{
            marginTop: '8px',
            width: '85%',
          }}
        >
          {codeReferences.map((ref, idx) => (
            <CodeBlock
              key={idx}
              file={ref.file}
              snippet={ref.snippet}
            />
          ))}
        </div>
      )}

      {/* Retry button for error messages */}
      {error && retryable && onRetry && (
        <div
          style={{
            marginTop: '12px',
            display: 'flex',
            alignItems: 'center',
            gap: '10px',
            maxWidth: '85%',
          }}
        >
          <button
            onClick={onRetry}
            style={{
              padding: '8px 16px',
              borderRadius: '10px',
              border: '1px solid rgba(220, 38, 38, 0.3)',
              background: 'rgba(255, 255, 255, 0.9)',
              backdropFilter: 'blur(10px)',
              color: '#dc2626',
              fontSize: '13px',
              fontWeight: 600,
              cursor: 'pointer',
              transition: 'all 0.2s',
              boxShadow: '0 2px 8px rgba(220, 38, 38, 0.1)',
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.background = 'rgba(254, 242, 242, 0.95)'
              e.currentTarget.style.transform = 'scale(1.02)'
              e.currentTarget.style.boxShadow = '0 4px 12px rgba(220, 38, 38, 0.2)'
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.background = 'rgba(255, 255, 255, 0.9)'
              e.currentTarget.style.transform = 'scale(1)'
              e.currentTarget.style.boxShadow = '0 2px 8px rgba(220, 38, 38, 0.1)'
            }}
          >
            <span>🔄</span>
            Retry
          </button>
          {requiresOllama && (
            <div style={{ 
              padding: '6px 12px',
              background: 'rgba(255, 255, 255, 0.6)',
              backdropFilter: 'blur(10px)',
              borderRadius: '8px',
              fontSize: '12px', 
              color: '#6b7280',
              border: '1px solid rgba(0, 0, 0, 0.08)',
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
            }}>
              <span>⚠️</span>
              Make sure Ollama is running
            </div>
          )}
        </div>
      )}
    </div>
  )
}

