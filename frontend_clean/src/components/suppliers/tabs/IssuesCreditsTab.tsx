/**
 * Issues & Credits Tab Component
 * Dispute console for supplier issues and credits
 */

import { useState, useEffect } from 'react'
import { ChevronDown, ChevronUp, Mail, CheckCircle, AlertCircle } from 'lucide-react'
import { fetchSupplierIssues, generateCreditEmail, type SupplierIssue } from '../../../lib/suppliersApi'
import type { SupplierDetail } from '../../../lib/suppliersApi'
import './IssuesCreditsTab.css'

interface IssuesCreditsTabProps {
  supplier: SupplierDetail
  supplierId: string
  currentRole: 'GM' | 'Finance' | 'ShiftLead'
}

export function IssuesCreditsTab({ supplier, supplierId, currentRole }: IssuesCreditsTabProps) {
  const [issues, setIssues] = useState<SupplierIssue[]>([])
  const [loading, setLoading] = useState(true)
  const [expandedIssues, setExpandedIssues] = useState<Set<string>>(new Set())
  const [emailTemplate, setEmailTemplate] = useState<string | null>(null)

  useEffect(() => {
    let mounted = true

    async function loadIssues() {
      setLoading(true)
      try {
        const data = await fetchSupplierIssues(supplierId)
        if (mounted) {
          setIssues(data)
        }
      } catch (e) {
        console.error('Failed to load issues:', e)
        if (mounted) {
          setIssues([])
        }
      } finally {
        if (mounted) {
          setLoading(false)
        }
      }
    }

    loadIssues()
    return () => {
      mounted = false
    }
  }, [supplierId])

  const toggleIssue = (issueId: string) => {
    setExpandedIssues((prev) => {
      const next = new Set(prev)
      if (next.has(issueId)) {
        next.delete(issueId)
      } else {
        next.add(issueId)
      }
      return next
    })
  }

  const handleGenerateEmail = async (issueIds: string[]) => {
    try {
      const template = await generateCreditEmail(supplierId, issueIds)
      setEmailTemplate(template)
    } catch (e) {
      console.error('Failed to generate email:', e)
    }
  }

  const totalFlags = issues.reduce((sum, issue) => sum + issue.count, 0)
  const totalCredits = issues
    .filter((issue) => issue.status === 'Resolved')
    .reduce((sum, issue) => sum + (issue.suggestedCredit || 0), 0)
  const openIssues = issues.filter((issue) => issue.status === 'Open' || issue.status === 'In Review').length

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('en-GB', {
      style: 'currency',
      currency: 'GBP',
      maximumFractionDigits: 2,
    }).format(value)
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'Open':
        return 'red'
      case 'In Review':
        return 'amber'
      case 'Resolved':
        return 'green'
      case 'Escalated':
        return 'orange'
      default:
        return 'gray'
    }
  }

  if (loading) {
    return <div className="issues-credits-tab-loading">Loading issues...</div>
  }

  return (
    <div className="issues-credits-tab">
      {/* Summary Banner */}
      <div className="issues-credits-summary">
        <div className="issues-credits-summary-item">
          <div className="issues-credits-summary-label">Flags</div>
          <div className="issues-credits-summary-value">{totalFlags}</div>
        </div>
        <div className="issues-credits-summary-item">
          <div className="issues-credits-summary-label">Credits Obtained</div>
          <div className="issues-credits-summary-value">{formatCurrency(totalCredits)}</div>
        </div>
        <div className="issues-credits-summary-item">
          <div className="issues-credits-summary-label">Still Open</div>
          <div className="issues-credits-summary-value">{openIssues}</div>
        </div>
      </div>

      {/* Issues List */}
      <div className="issues-credits-list">
        {issues.map((issue) => {
          const isExpanded = expandedIssues.has(issue.id)
          const statusColor = getStatusColor(issue.status)

          return (
            <div key={issue.id} className="issues-credits-issue-card">
              <div
                className="issues-credits-issue-header"
                onClick={() => toggleIssue(issue.id)}
              >
                <div className="issues-credits-issue-main">
                  <div className="issues-credits-issue-type">{issue.type}</div>
                  <div className="issues-credits-issue-meta">
                    <span>{issue.count} occurrences</span>
                    <span>•</span>
                    <span>Latest: {new Date(issue.latestOccurrence).toLocaleDateString('en-GB')}</span>
                    {issue.monetaryImpact > 0 && (
                      <>
                        <span>•</span>
                        <span>{formatCurrency(issue.monetaryImpact)} impact</span>
                      </>
                    )}
                  </div>
                </div>
                <div className="issues-credits-issue-actions">
                  <div className={`issues-credits-issue-status issues-credits-issue-status-${statusColor}`}>
                    {issue.status}
                  </div>
                  {isExpanded ? <ChevronUp size={18} /> : <ChevronDown size={18} />}
                </div>
              </div>

              {isExpanded && (
                <div className="issues-credits-issue-details">
                  {issue.affectedInvoices && issue.affectedInvoices.length > 0 && (
                    <div className="issues-credits-issue-section">
                      <div className="issues-credits-issue-section-title">Affected Invoices</div>
                      <div className="issues-credits-issue-invoices">
                        {issue.affectedInvoices.map((invId) => (
                          <span key={invId} className="issues-credits-issue-invoice">
                            {invId}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}

                  {issue.recommendedAction && (
                    <div className="issues-credits-issue-section">
                      <div className="issues-credits-issue-section-title">Recommended Action</div>
                      <div className="issues-credits-issue-action-text">
                        {issue.recommendedAction}
                      </div>
                    </div>
                  )}

                  {issue.suggestedCredit && issue.suggestedCredit > 0 && (
                    <div className="issues-credits-issue-section">
                      <div className="issues-credits-issue-section-title">Suggested Credit</div>
                      <div className="issues-credits-issue-credit-amount">
                        {formatCurrency(issue.suggestedCredit)}
                      </div>
                    </div>
                  )}

                  <div className="issues-credits-issue-buttons">
                    {currentRole === 'Finance' && (
                      <button
                        className="issues-credits-issue-button"
                        onClick={() => handleGenerateEmail([issue.id])}
                      >
                        <Mail size={16} />
                        Generate credit email
                      </button>
                    )}
                    {currentRole === 'GM' && issue.status !== 'Resolved' && (
                      <button className="issues-credits-issue-button">
                        <AlertCircle size={16} />
                        Escalate to GM
                      </button>
                    )}
                    {issue.status !== 'Resolved' && (
                      <button className="issues-credits-issue-button">
                        <CheckCircle size={16} />
                        Mark as addressed
                      </button>
                    )}
                  </div>
                </div>
              )}
            </div>
          )
        })}
      </div>

      {/* Email Template Modal */}
      {emailTemplate && (
        <div className="issues-credits-email-modal">
          <div className="issues-credits-email-content">
            <div className="issues-credits-email-header">
              <h3>Credit Email Template</h3>
              <button
                onClick={() => setEmailTemplate(null)}
                className="issues-credits-email-close"
              >
                ×
              </button>
            </div>
            <textarea
              value={emailTemplate}
              readOnly
              className="issues-credits-email-textarea"
              rows={10}
            />
            <div className="issues-credits-email-actions">
              <button
                onClick={() => {
                  navigator.clipboard.writeText(emailTemplate)
                  alert('Email copied to clipboard')
                }}
                className="issues-credits-email-button"
              >
                Copy to Clipboard
              </button>
              <button
                onClick={() => setEmailTemplate(null)}
                className="issues-credits-email-button"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

