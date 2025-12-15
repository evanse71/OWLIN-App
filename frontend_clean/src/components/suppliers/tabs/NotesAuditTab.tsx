/**
 * Notes & Audit Tab Component
 * Staff notes and audit timeline for supplier
 */

import { useState, useEffect } from 'react'
import { FileText, Clock, User } from 'lucide-react'
import { fetchSupplierAudit, addSupplierNote, type SupplierAuditEntry, type SupplierNote } from '../../../lib/suppliersApi'
import type { SupplierDetail } from '../../../lib/suppliersApi'
import './NotesAuditTab.css'

interface NotesAuditTabProps {
  supplier: SupplierDetail
  supplierId: string
  currentRole: 'GM' | 'Finance' | 'ShiftLead'
}

export function NotesAuditTab({ supplier, supplierId, currentRole }: NotesAuditTabProps) {
  const [auditEntries, setAuditEntries] = useState<SupplierAuditEntry[]>([])
  const [notes, setNotes] = useState<SupplierNote[]>([])
  const [loading, setLoading] = useState(true)
  const [newNote, setNewNote] = useState('')
  const [savingNote, setSavingNote] = useState(false)
  const canEdit = currentRole === 'GM' || currentRole === 'Finance'

  useEffect(() => {
    let mounted = true

    async function loadData() {
      setLoading(true)
      try {
        const auditData = await fetchSupplierAudit(supplierId)
        if (mounted) {
          setAuditEntries(auditData)
          // Mock notes for now - in real app would come from API
          setNotes([
            {
              id: 'note-1',
              timestamp: '2025-10-15T10:30:00Z',
              author: 'Finance Team',
              role: 'Finance',
              content: 'Sales rep changed in March. New contact details updated.',
            },
            {
              id: 'note-2',
              timestamp: '2025-09-10T14:20:00Z',
              author: 'GM',
              role: 'GM',
              content: 'New contract signed – fix prices until September 2026.',
            },
          ])
        }
      } catch (e) {
        console.error('Failed to load audit data:', e)
        if (mounted) {
          setAuditEntries([])
          setNotes([])
        }
      } finally {
        if (mounted) {
          setLoading(false)
        }
      }
    }

    loadData()
    return () => {
      mounted = false
    }
  }, [supplierId])

  const handleSaveNote = async () => {
    if (!newNote.trim() || savingNote) return

    setSavingNote(true)
    try {
      await addSupplierNote(supplierId, newNote.trim(), 'Current User', currentRole)
      setNotes([
        {
          id: `note-${Date.now()}`,
          timestamp: new Date().toISOString(),
          author: 'Current User',
          role: currentRole,
          content: newNote.trim(),
        },
        ...notes,
      ])
      setNewNote('')
    } catch (e) {
      console.error('Failed to save note:', e)
    } finally {
      setSavingNote(false)
    }
  }

  if (loading) {
    return <div className="notes-audit-tab-loading">Loading notes and audit data...</div>
  }

  return (
    <div className="notes-audit-tab">
      {/* Staff Notes Section */}
      <div className="notes-audit-section">
        <div className="notes-audit-section-header">
          <h3 className="notes-audit-section-title">Staff Notes</h3>
        </div>

        {/* Add Note Form */}
        {canEdit && (
          <div className="notes-audit-add-note">
            <textarea
              value={newNote}
              onChange={(e) => setNewNote(e.target.value)}
              placeholder="Add a note about this supplier..."
              className="notes-audit-note-input"
              rows={3}
            />
            <button
              onClick={handleSaveNote}
              disabled={!newNote.trim() || savingNote}
              className="notes-audit-save-button"
            >
              {savingNote ? 'Saving...' : 'Save Note'}
            </button>
          </div>
        )}

        {/* Notes List */}
        <div className="notes-audit-notes-list">
          {notes.length === 0 ? (
            <div className="notes-audit-empty">No notes yet</div>
          ) : (
            notes.map((note) => (
              <div key={note.id} className="notes-audit-note">
                <div className="notes-audit-note-header">
                  <div className="notes-audit-note-author">
                    <User size={14} />
                    <span>{note.author}</span>
                    <span className="notes-audit-note-role">({note.role})</span>
                  </div>
                  <div className="notes-audit-note-date">
                    {new Date(note.timestamp).toLocaleDateString('en-GB', {
                      day: 'numeric',
                      month: 'short',
                      year: 'numeric',
                      hour: '2-digit',
                      minute: '2-digit',
                    })}
                  </div>
                </div>
                <div className="notes-audit-note-content">{note.content}</div>
              </div>
            ))
          )}
        </div>
      </div>

      {/* Audit Timeline Section */}
      <div className="notes-audit-section">
        <div className="notes-audit-section-header">
          <h3 className="notes-audit-section-title">Audit Timeline</h3>
        </div>

        <div className="notes-audit-timeline">
          {auditEntries.length === 0 ? (
            <div className="notes-audit-empty">No audit entries yet</div>
          ) : (
            auditEntries.map((entry) => (
              <div key={entry.id} className="notes-audit-timeline-entry">
                <div className="notes-audit-timeline-dot" />
                <div className="notes-audit-timeline-content">
                  <div className="notes-audit-timeline-header">
                    <div className="notes-audit-timeline-actor">{entry.actor}</div>
                    <div className="notes-audit-timeline-time">
                      {new Date(entry.timestamp).toLocaleDateString('en-GB', {
                        day: 'numeric',
                        month: 'short',
                        year: 'numeric',
                        hour: '2-digit',
                        minute: '2-digit',
                      })}
                    </div>
                  </div>
                  <div className="notes-audit-timeline-action">{entry.action}</div>
                  {entry.details && (
                    <div className="notes-audit-timeline-details">{entry.details}</div>
                  )}
                </div>
              </div>
            ))
          )}
        </div>
      </div>

      {/* Attachments Section (placeholder) */}
      {canEdit && (
        <div className="notes-audit-section">
          <div className="notes-audit-section-header">
            <h3 className="notes-audit-section-title">Attachments</h3>
          </div>
          <div className="notes-audit-attachments">
            <div className="notes-audit-empty">
              No attachments. Upload contract documents or other files here.
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

