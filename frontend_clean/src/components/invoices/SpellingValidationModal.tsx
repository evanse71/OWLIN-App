import { useState } from 'react'
import { AlertCircle, Check, X, Edit2 } from 'lucide-react'
import type { SpellCheckResult } from '../../lib/spellchecker'
import './Modal.css'

interface SpellingValidationModalProps {
  isOpen: boolean
  onClose: () => void
  onConfirm: (corrections: Map<number, string>) => void
  errors: Array<{
    index: number
    itemDescription: string
    result: SpellCheckResult
  }>
}

export function SpellingValidationModal({
  isOpen,
  onClose,
  onConfirm,
  errors
}: SpellingValidationModalProps) {
  const [corrections, setCorrections] = useState<Map<number, string>>(new Map())
  const [editingIndex, setEditingIndex] = useState<number | null>(null)
  const [editValue, setEditValue] = useState<string>('')

  if (!isOpen) return null

  const handleUseSuggestion = (errorIndex: number, suggestion: string, originalText: string) => {
    const error = errors[errorIndex]
    if (!error) return

    // Replace the first misspelled word with the suggestion
    const firstError = error.result.errors[0]
    if (!firstError) return

    const errorWord = firstError.word
    // Use a more robust replacement that handles word boundaries
    const wordRegex = new RegExp(`\\b${errorWord.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}\\b`, 'gi')
    const correctedText = originalText.replace(wordRegex, (match, offset) => {
      // Only replace the first occurrence
      if (offset === firstError.position) {
        return suggestion
      }
      return match
    })

    const newCorrections = new Map(corrections)
    newCorrections.set(error.index, correctedText)
    setCorrections(newCorrections)
  }

  const handleKeepAsIs = (errorIndex: number) => {
    const error = errors[errorIndex]
    if (!error) return

    // Mark as confirmed (keep original)
    const newCorrections = new Map(corrections)
    newCorrections.set(error.index, error.itemDescription)
    setCorrections(newCorrections)
  }

  const handleEdit = (errorIndex: number) => {
    const error = errors[errorIndex]
    if (!error) return

    setEditingIndex(errorIndex)
    setEditValue(error.itemDescription)
  }

  const handleSaveEdit = (errorIndex: number) => {
    const error = errors[errorIndex]
    if (!error) return

    const newCorrections = new Map(corrections)
    newCorrections.set(error.index, editValue)
    setCorrections(newCorrections)
    setEditingIndex(null)
    setEditValue('')
  }

  const handleCancelEdit = () => {
    setEditingIndex(null)
    setEditValue('')
  }

  const handleConfirmAll = () => {
    // For items without explicit corrections, use original text
    const finalCorrections = new Map(corrections)
    errors.forEach(error => {
      if (!finalCorrections.has(error.index)) {
        finalCorrections.set(error.index, error.itemDescription)
      }
    })
    onConfirm(finalCorrections)
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-container" onClick={(e) => e.stopPropagation()} style={{ maxWidth: '700px' }}>
        <div className="modal-header">
          <h2 className="modal-title" style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <AlertCircle size={24} style={{ color: 'var(--accent-orange)' }} />
            Spelling Check Required
          </h2>
          <button className="modal-close-button" onClick={onClose} aria-label="Close modal">
            <X size={20} />
          </button>
        </div>

        <div className="modal-body" style={{ maxHeight: '60vh', overflowY: 'auto' }}>
          <div style={{ 
            padding: '16px', 
            background: 'rgba(245, 158, 11, 0.1)', 
            border: '1px solid rgba(245, 158, 11, 0.3)', 
            borderRadius: '8px', 
            marginBottom: '20px',
            fontSize: '14px',
            color: 'var(--text-secondary)'
          }}>
            Please review the following items with potential spelling errors. You can accept suggestions, keep the original text, or edit manually.
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            {errors.map((error, errorIndex) => {
              const correctedText = corrections.get(error.index) || error.itemDescription
              const isEditing = editingIndex === errorIndex
              const firstError = error.result.errors[0]

              return (
                <div
                  key={error.index}
                  style={{
                    padding: '16px',
                    border: '1px solid var(--border-color)',
                    borderRadius: '8px',
                    background: 'var(--bg-secondary)'
                  }}
                >
                  <div style={{ marginBottom: '12px' }}>
                    <div style={{ 
                      fontSize: '12px', 
                      fontWeight: '600', 
                      color: 'var(--text-secondary)',
                      marginBottom: '4px'
                    }}>
                      Item #{error.index + 1}
                    </div>
                    {isEditing ? (
                      <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                        <input
                          type="text"
                          value={editValue}
                          onChange={(e) => setEditValue(e.target.value)}
                          className="modal-form-input"
                          style={{ flex: 1 }}
                          autoFocus
                          onKeyDown={(e) => {
                            if (e.key === 'Enter') {
                              handleSaveEdit(errorIndex)
                            } else if (e.key === 'Escape') {
                              handleCancelEdit()
                            }
                          }}
                        />
                        <button
                          type="button"
                          className="glass-button"
                          onClick={() => handleSaveEdit(errorIndex)}
                          style={{ padding: '6px 12px' }}
                        >
                          <Check size={16} />
                        </button>
                        <button
                          type="button"
                          className="glass-button"
                          onClick={handleCancelEdit}
                          style={{ padding: '6px 12px' }}
                        >
                          <X size={16} />
                        </button>
                      </div>
                    ) : (
                      <div style={{ 
                        fontSize: '14px', 
                        color: 'var(--text-primary)',
                        padding: '8px',
                        background: 'rgba(255, 255, 255, 0.05)',
                        borderRadius: '4px',
                        wordBreak: 'break-word'
                      }}>
                        {correctedText}
                      </div>
                    )}
                  </div>

                  {firstError && !isEditing && (
                    <div style={{ marginTop: '12px' }}>
                      <div style={{ 
                        fontSize: '12px', 
                        color: 'var(--accent-red)',
                        marginBottom: '8px',
                        fontWeight: '500'
                      }}>
                        Potential error: "{firstError.word}"
                      </div>
                      
                      {firstError.suggestions.length > 0 && (
                        <div style={{ marginBottom: '12px' }}>
                          <div style={{ 
                            fontSize: '11px', 
                            color: 'var(--text-secondary)',
                            marginBottom: '6px'
                          }}>
                            Suggestions:
                          </div>
                          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                            {firstError.suggestions.slice(0, 5).map((suggestion, idx) => (
                              <button
                                key={idx}
                                type="button"
                                className="glass-button"
                                onClick={() => handleUseSuggestion(errorIndex, suggestion, error.itemDescription)}
                                style={{ 
                                  fontSize: '12px', 
                                  padding: '4px 10px',
                                  background: 'rgba(59, 130, 246, 0.1)',
                                  borderColor: 'var(--accent-blue)'
                                }}
                              >
                                {suggestion}
                              </button>
                            ))}
                          </div>
                        </div>
                      )}

                      <div style={{ display: 'flex', gap: '8px' }}>
                        <button
                          type="button"
                          className="glass-button"
                          onClick={() => handleKeepAsIs(errorIndex)}
                          style={{ 
                            fontSize: '12px', 
                            padding: '6px 12px',
                            background: corrections.has(error.index) && correctedText === error.itemDescription
                              ? 'rgba(34, 197, 94, 0.2)'
                              : undefined
                          }}
                        >
                          <Check size={14} style={{ marginRight: '4px' }} />
                          Keep as is
                        </button>
                        <button
                          type="button"
                          className="glass-button"
                          onClick={() => handleEdit(errorIndex)}
                          style={{ fontSize: '12px', padding: '6px 12px' }}
                        >
                          <Edit2 size={14} style={{ marginRight: '4px' }} />
                          Edit
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        </div>

        <div className="modal-footer">
          <button 
            type="button" 
            className="modal-button-secondary" 
            onClick={onClose}
          >
            Cancel
          </button>
          <button 
            type="button" 
            className="modal-button-primary" 
            onClick={handleConfirmAll}
          >
            Confirm All & Continue
          </button>
        </div>
      </div>
    </div>
  )
}

