import { CodeBlock } from './CodeBlock'
import { useState } from 'react'
import { Bot, Copy, Check } from 'lucide-react'

// OWLIN Design System Tokens - Dark UI Palette
const OWLIN_COLORS = {
  // Dark backgrounds
  backgroundLevel1: '#101214',
  backgroundLevel2: '#16191F',
  
  // Primary accent
  primary: '#4CA3FF',
  
  // Borders
  border: 'rgba(255, 255, 255, 0.05)',
  borderSoft: 'rgba(255, 255, 255, 0.08)',
  
  // Text colors
  textPrimary: 'rgba(255, 255, 255, 0.87)',
  textSecondary: 'rgba(255, 255, 255, 0.6)',
  textMuted: 'rgba(255, 255, 255, 0.4)',
  textSlate: '#cbd5e1',
  
  // Interactive states
  hover: 'rgba(255, 255, 255, 0.03)',
  
  // Legacy (for compatibility)
  navy: '#2B3A55',
  sageGreen: '#7B9E87',
  sageGreenLight: 'rgba(123, 158, 135, 0.15)',
  sageGreenBorder: 'rgba(123, 158, 135, 0.2)',
  navyDark: '#101214',
  navyCard: '#16191F',
  backgroundSoft: 'rgba(255, 255, 255, 0.03)',
  backgroundCard: '#16191F',
}

const OWLIN_TYPOGRAPHY = {
  fontFamily: 'Inter, "Work Sans", -apple-system, BlinkMacSystemFont, sans-serif',
  weights: {
    body: 400,
    label: 500,
    title: 600,
  }
}

const OWLIN_TRANSITIONS = {
  default: 'all 200ms ease-out',
}

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
        processed = processed.replace(/`(.+?)`/g, `<code style="background: ${OWLIN_COLORS.backgroundCard}; padding: 2px 6px; border-radius: 4px; font-family: monospace; font-size: 0.9em; color: ${OWLIN_COLORS.textPrimary}; border: 1px solid ${OWLIN_COLORS.border};">$1</code>`)
        // Headers
        processed = processed.replace(/^### (.+)$/gm, `<h3 style="font-size: 1.1em; font-weight: ${OWLIN_TYPOGRAPHY.weights.title}; margin: 12px 0 8px 0; color: ${OWLIN_COLORS.textPrimary}; font-family: ${OWLIN_TYPOGRAPHY.fontFamily};">$1</h3>`)
        processed = processed.replace(/^## (.+)$/gm, `<h2 style="font-size: 1.2em; font-weight: ${OWLIN_TYPOGRAPHY.weights.title}; margin: 16px 0 10px 0; color: ${OWLIN_COLORS.textPrimary}; font-family: ${OWLIN_TYPOGRAPHY.fontFamily};">$1</h2>`)
        processed = processed.replace(/^# (.+)$/gm, `<h1 style="font-size: 1.3em; font-weight: ${OWLIN_TYPOGRAPHY.weights.title}; margin: 20px 0 12px 0; color: ${OWLIN_COLORS.textPrimary}; font-family: ${OWLIN_TYPOGRAPHY.fontFamily};">$1</h1>`)
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
        flexDirection: 'row',
        marginBottom: '12px',
        alignItems: 'flex-end',
        gap: '8px',
        position: 'relative',
        justifyContent: isUser ? 'flex-end' : 'flex-start',
      }}
      onMouseEnter={() => !isUser && setShowCopyButton(true)}
      onMouseLeave={() => !isUser && setShowCopyButton(false)}
    >
      {/* Avatar/Indicator - Only for assistant, positioned on the left */}
      {!isUser && (
        <div
          style={{
            width: '32px',
            height: '32px',
            minWidth: '32px',
            borderRadius: '50%',
            background: OWLIN_COLORS.backgroundLevel2,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            border: `1px solid ${OWLIN_COLORS.border}`,
            flexShrink: 0,
          }}
        >
          <Bot size={18} strokeWidth={1.5} color={OWLIN_COLORS.textSlate} />
        </div>
      )}
      
      <div
        style={{
          maxWidth: '75%',
          padding: '12px 16px',
          borderRadius: isUser ? '18px 18px 4px 18px' : '18px 18px 18px 4px',
          background: error
            ? 'rgba(239, 68, 68, 0.15)'
            : isUser
            ? OWLIN_COLORS.backgroundLevel2
            : OWLIN_COLORS.backgroundLevel2,
          color: error ? 'rgba(239, 68, 68, 1)' : (isUser ? OWLIN_COLORS.textPrimary : OWLIN_COLORS.textPrimary),
          fontSize: '14px',
          lineHeight: '1.6',
          wordWrap: 'break-word',
          border: error
            ? '1px solid rgba(239, 68, 68, 0.3)'
            : `1px solid ${OWLIN_COLORS.border}`,
          boxShadow: error
            ? '0 1px 2px rgba(0, 0, 0, 0.04)'
            : isUser
            ? '0 1px 2px rgba(0, 0, 0, 0.04)'
            : '0 1px 2px rgba(0, 0, 0, 0.04)',
          transition: OWLIN_TRANSITIONS.default,
          position: 'relative',
          fontFamily: OWLIN_TYPOGRAPHY.fontFamily,
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
                ? OWLIN_COLORS.hover 
                : OWLIN_COLORS.backgroundLevel2,
              border: copied
                ? `1px solid ${OWLIN_COLORS.borderSoft}`
                : `1px solid ${OWLIN_COLORS.border}`,
              borderRadius: '6px',
              cursor: 'pointer',
              fontSize: '12px',
              color: copied ? OWLIN_COLORS.primary : OWLIN_COLORS.textSecondary,
              fontWeight: OWLIN_TYPOGRAPHY.weights.label,
              transition: OWLIN_TRANSITIONS.default,
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              opacity: showCopyButton || copied ? 1 : 0,
              transform: showCopyButton || copied ? 'scale(1)' : 'scale(0.9)',
              zIndex: 10,
              boxShadow: '0 1px 2px rgba(0, 0, 0, 0.04)',
              fontFamily: OWLIN_TYPOGRAPHY.fontFamily,
            }}
            onMouseEnter={(e) => {
              if (!copied) {
                e.currentTarget.style.background = OWLIN_COLORS.hover
                e.currentTarget.style.borderColor = OWLIN_COLORS.borderSoft
                e.currentTarget.style.color = OWLIN_COLORS.textPrimary
                e.currentTarget.style.transform = 'scale(1.05)'
              }
            }}
            onMouseLeave={(e) => {
              if (!copied) {
                e.currentTarget.style.background = OWLIN_COLORS.backgroundLevel2
                e.currentTarget.style.borderColor = OWLIN_COLORS.border
                e.currentTarget.style.color = OWLIN_COLORS.textSecondary
                e.currentTarget.style.transform = 'scale(1)'
              }
            }}
          >
            {copied ? (
              <>
                <Check size={14} strokeWidth={1.5} />
                <span>Copied</span>
              </>
            ) : (
              <>
                <Copy size={14} strokeWidth={1.5} />
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
            background: OWLIN_COLORS.sageGreenLight,
            backdropFilter: 'blur(20px)',
            borderRadius: '6px',
            fontSize: '12px',
            color: OWLIN_COLORS.textPrimary,
            border: `1px solid ${OWLIN_COLORS.sageGreenBorder}`,
            boxShadow: '0 1px 2px rgba(0, 0, 0, 0.04)',
            maxWidth: '85%',
            fontFamily: OWLIN_TYPOGRAPHY.fontFamily,
          }}
        >
          <div style={{ 
            fontWeight: OWLIN_TYPOGRAPHY.weights.title, 
            marginBottom: '8px', 
            fontSize: '13px',
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            color: OWLIN_COLORS.textPrimary,
            fontFamily: OWLIN_TYPOGRAPHY.fontFamily,
          }}>
            <span style={{
              width: '20px',
              height: '20px',
              borderRadius: '50%',
              background: OWLIN_COLORS.sageGreenLight,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: '12px',
              boxShadow: '0 1px 2px rgba(0, 0, 0, 0.04)',
              border: `1px solid ${OWLIN_COLORS.sageGreenBorder}`,
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
                background: OWLIN_COLORS.backgroundCard,
                borderRadius: '6px',
                fontSize: '11px',
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                color: OWLIN_COLORS.textPrimary,
                border: `1px solid ${OWLIN_COLORS.border}`,
                fontFamily: OWLIN_TYPOGRAPHY.fontFamily,
              }}>
                <span>🔎</span>
                <span><strong>{explorationMetadata.searches_executed}</strong> searches</span>
              </div>
            )}
            {explorationMetadata.files_searched !== undefined && (
              <div style={{
                padding: '6px 10px',
                background: OWLIN_COLORS.backgroundCard,
                borderRadius: '6px',
                fontSize: '11px',
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                color: OWLIN_COLORS.textPrimary,
                border: `1px solid ${OWLIN_COLORS.border}`,
                fontFamily: OWLIN_TYPOGRAPHY.fontFamily,
              }}>
                <span>📁</span>
                <span><strong>{explorationMetadata.files_searched}</strong> files</span>
              </div>
            )}
            {explorationMetadata.findings_count !== undefined && (
              <div style={{
                padding: '6px 10px',
                background: OWLIN_COLORS.backgroundCard,
                borderRadius: '6px',
                fontSize: '11px',
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                color: OWLIN_COLORS.textPrimary,
                border: `1px solid ${OWLIN_COLORS.border}`,
                fontFamily: OWLIN_TYPOGRAPHY.fontFamily,
              }}>
                <span>✨</span>
                <span><strong>{explorationMetadata.findings_count}</strong> findings</span>
              </div>
            )}
            {explorationMetadata.exploration_time !== undefined && (
              <div style={{
                padding: '6px 10px',
                background: OWLIN_COLORS.backgroundCard,
                borderRadius: '6px',
                fontSize: '11px',
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                color: OWLIN_COLORS.textPrimary,
                border: `1px solid ${OWLIN_COLORS.border}`,
                fontFamily: OWLIN_TYPOGRAPHY.fontFamily,
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
                background: OWLIN_COLORS.backgroundCard,
                borderRadius: '6px',
                fontSize: '11px', 
                color: OWLIN_COLORS.navy,
                border: `1px solid ${OWLIN_COLORS.border}`,
                fontFamily: OWLIN_TYPOGRAPHY.fontFamily,
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
                      background: OWLIN_COLORS.sageGreenLight,
                      borderRadius: '4px',
                      border: `1px solid ${OWLIN_COLORS.sageGreenBorder}`,
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
              borderRadius: '12px',
              border: '1px solid rgba(239, 68, 68, 0.3)',
              background: 'rgba(239, 68, 68, 0.1)',
              backdropFilter: 'blur(10px)',
              color: 'rgba(239, 68, 68, 1)',
              fontSize: '13px',
              fontWeight: OWLIN_TYPOGRAPHY.weights.title,
              cursor: 'pointer',
              transition: OWLIN_TRANSITIONS.default,
              boxShadow: '0 1px 2px rgba(0, 0, 0, 0.04)',
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              fontFamily: OWLIN_TYPOGRAPHY.fontFamily,
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.background = 'rgba(239, 68, 68, 0.15)'
              e.currentTarget.style.borderColor = 'rgba(239, 68, 68, 0.4)'
              e.currentTarget.style.transform = 'scale(1.02)'
              e.currentTarget.style.boxShadow = '0 2px 4px rgba(239, 68, 68, 0.2)'
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.background = 'rgba(239, 68, 68, 0.1)'
              e.currentTarget.style.borderColor = 'rgba(239, 68, 68, 0.3)'
              e.currentTarget.style.transform = 'scale(1)'
              e.currentTarget.style.boxShadow = '0 1px 2px rgba(0, 0, 0, 0.04)'
            }}
          >
            <span>🔄</span>
            Retry
          </button>
          {requiresOllama && (
            <div style={{ 
              padding: '6px 12px',
              background: OWLIN_COLORS.backgroundCard,
              backdropFilter: 'blur(10px)',
              borderRadius: '6px',
              fontSize: '12px', 
              color: OWLIN_COLORS.textSecondary,
              border: `1px solid ${OWLIN_COLORS.border}`,
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              fontFamily: OWLIN_TYPOGRAPHY.fontFamily,
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

