import { memo, useEffect } from 'react'
import './KeyboardShortcutsModal.css'

interface Shortcut {
  keys: string[]
  description: string
}

interface KeyboardShortcutsModalProps {
  isOpen: boolean
  onClose: () => void
}

const shortcuts: Shortcut[] = [
  { keys: ['/'], description: 'Focus search' },
  { keys: ['j', '↓'], description: 'Navigate down' },
  { keys: ['k', '↑'], description: 'Navigate up' },
  { keys: ['Enter'], description: 'Open selected invoice' },
  { keys: ['Esc'], description: 'Close detail panel' },
  { keys: ['f'], description: 'Toggle filters' },
  { keys: ['u'], description: 'Open upload' },
  { keys: ['?'], description: 'Show keyboard shortcuts' },
]

export const KeyboardShortcutsModal = memo(function KeyboardShortcutsModal({
  isOpen,
  onClose,
}: KeyboardShortcutsModalProps) {
  useEffect(() => {
    if (!isOpen) return

    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose()
      }
    }

    window.addEventListener('keydown', handleEscape)
    return () => window.removeEventListener('keydown', handleEscape)
  }, [isOpen, onClose])

  if (!isOpen) return null

  return (
    <>
      <div className="keyboard-shortcuts-overlay" onClick={onClose} />
      <div className="keyboard-shortcuts-modal">
        <div className="keyboard-shortcuts-header">
          <h2 className="keyboard-shortcuts-title">Keyboard Shortcuts</h2>
          <button
            className="keyboard-shortcuts-close"
            onClick={onClose}
            aria-label="Close"
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
        </div>
        <div className="keyboard-shortcuts-list">
          {shortcuts.map((shortcut, index) => (
            <div key={index} className="keyboard-shortcut-item">
              <div className="keyboard-shortcut-keys">
                {shortcut.keys.map((key, keyIndex) => (
                  <span key={keyIndex} className="keyboard-shortcut-key">
                    {key}
                  </span>
                ))}
              </div>
              <div className="keyboard-shortcut-description">{shortcut.description}</div>
            </div>
          ))}
        </div>
      </div>
    </>
  )
})

