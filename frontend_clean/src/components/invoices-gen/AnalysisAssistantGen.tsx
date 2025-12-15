import React from 'react'
import {
  AlertTriangle,
  AlertCircle,
  DollarSign,
  FileText,
  MessageSquare,
  TrendingUp,
  CheckCircle2,
  Loader2,
  ArrowRight,
  ChevronDown,
  ChevronUp,
} from 'lucide-react'
import './AnalysisAssistantGen.css'

export type IssueSeverity = 'info' | 'warning' | 'error' | 'success'
export type StatusState = 'clear' | 'scanning' | 'issues-found'

export interface AnalysisIssue {
  id: string
  type: 'price-mismatch' | 'missing-dn' | 'quantity-mismatch' | 'credit-suggestion' | 'duplicate' | 'low-confidence'
  severity: IssueSeverity
  title: string
  context: string
  aiNote?: string
  confidence?: number
  invoiceId?: string
  lineItemId?: string
  onView?: () => void
}

interface AnalysisAssistantGenProps {
  status?: StatusState
  issueCount?: number
  issues?: AnalysisIssue[]
  onIssueClick?: (issue: AnalysisIssue) => void
}

export function AnalysisAssistantGen({
  status = 'clear',
  issueCount = 0,
  issues = [],
  onIssueClick,
}: AnalysisAssistantGenProps) {
  const [collapsedGroups, setCollapsedGroups] = React.useState<Set<string>>(new Set())
  const [visibleIssuesPerGroup, setVisibleIssuesPerGroup] = React.useState<Record<string, number>>({})
  const MAX_VISIBLE_ISSUES = 5

  const toggleGroup = (groupName: string) => {
    setCollapsedGroups((prev) => {
      const next = new Set(prev)
      if (next.has(groupName)) {
        next.delete(groupName)
      } else {
        next.add(groupName)
      }
      return next
    })
  }

  const getStatusPill = () => {
    switch (status) {
      case 'clear':
        return (
          <div className="analysis-assistant-gen__status-pill analysis-assistant-gen__status-pill--success">
            <CheckCircle2 className="analysis-assistant-gen__status-icon" />
            All clear
          </div>
        )
      case 'scanning':
        return (
          <div className="analysis-assistant-gen__status-pill analysis-assistant-gen__status-pill--scanning">
            <Loader2 className="analysis-assistant-gen__status-icon analysis-assistant-gen__status-icon--spinning" />
            Scanning…
          </div>
        )
      case 'issues-found':
        return (
          <div className="analysis-assistant-gen__status-pill analysis-assistant-gen__status-pill--warning">
            {issueCount} {issueCount === 1 ? 'issue' : 'issues'} found
          </div>
        )
    }
  }

  const getIssueIcon = (type: AnalysisIssue['type']) => {
    switch (type) {
      case 'price-mismatch':
        return <DollarSign className="analysis-assistant-gen__issue-icon" />
      case 'missing-dn':
        return <FileText className="analysis-assistant-gen__issue-icon" />
      case 'quantity-mismatch':
        return <AlertTriangle className="analysis-assistant-gen__issue-icon" />
      case 'credit-suggestion':
        return <MessageSquare className="analysis-assistant-gen__issue-icon" />
      case 'duplicate':
        return <AlertCircle className="analysis-assistant-gen__issue-icon" />
      case 'low-confidence':
        return <TrendingUp className="analysis-assistant-gen__issue-icon" />
    }
  }

  const getSeverityPill = (severity: IssueSeverity) => {
    const config = {
      success: { label: 'All clear', className: 'analysis-assistant-gen__severity-pill--success' },
      info: { label: 'Suggestion', className: 'analysis-assistant-gen__severity-pill--info' },
      warning: { label: 'Review', className: 'analysis-assistant-gen__severity-pill--warning' },
      error: { label: 'Action needed', className: 'analysis-assistant-gen__severity-pill--error' },
    }
    const { label, className } = config[severity]
    return <div className={`analysis-assistant-gen__severity-pill ${className}`}>{label}</div>
  }

  const groupedIssues = React.useMemo(() => {
    const groups: Record<string, AnalysisIssue[]> = {
      'Price issues': [],
      'Quantity mismatches': [],
      'Missing notes': [],
      'Suggestions': [],
      'Other': [],
    }

    issues.forEach((issue) => {
      if (issue.type === 'price-mismatch') {
        groups['Price issues'].push(issue)
      } else if (issue.type === 'quantity-mismatch') {
        groups['Quantity mismatches'].push(issue)
      } else if (issue.type === 'missing-dn') {
        groups['Missing notes'].push(issue)
      } else if (issue.severity === 'info' || issue.type === 'credit-suggestion') {
        groups['Suggestions'].push(issue)
      } else {
        groups['Other'].push(issue)
      }
    })

    return Object.entries(groups).filter(([_, items]) => items.length > 0)
  }, [issues])

  const handleIssueClick = (issue: AnalysisIssue) => {
    if (onIssueClick) {
      onIssueClick(issue)
    } else if (issue.onView) {
      issue.onView()
    }
  }

  return (
    <aside className="analysis-assistant-gen">
      {/* Header */}
      <div className="analysis-assistant-gen__header">
        <div className="analysis-assistant-gen__title">Analysis Assistant</div>
        {getStatusPill()}
      </div>

      {/* System Summary - Only show when expanded */}
      {status === 'clear' && (
        <div className="analysis-assistant-gen__summary">
          Monitoring invoices and delivery notes for discrepancies.
        </div>
      )}

      {/* Issue Cards */}
      {status === 'scanning' && (
        <div className="analysis-assistant-gen__scanning">
          <div className="analysis-assistant-gen__scanning-stage">
            <Loader2 className="analysis-assistant-gen__scanning-icon" />
            Extracting text…
          </div>
          <div className="analysis-assistant-gen__scanning-stage">
            <Loader2 className="analysis-assistant-gen__scanning-icon" />
            Detecting supplier…
          </div>
          <div className="analysis-assistant-gen__scanning-stage">
            <Loader2 className="analysis-assistant-gen__scanning-icon" />
            Analysing prices…
          </div>
        </div>
      )}

      {status === 'issues-found' && issues.length > 0 && (
        <div className="analysis-assistant-gen__issues">
          {groupedIssues.map(([groupName, groupIssues]) => {
            const isCollapsed = collapsedGroups.has(groupName)
            const showAll = visibleIssuesPerGroup[groupName] === groupIssues.length
            const visibleCount = showAll ? groupIssues.length : Math.min(MAX_VISIBLE_ISSUES, groupIssues.length)
            const visibleIssues = groupIssues.slice(0, visibleCount)
            const hasMore = groupIssues.length > MAX_VISIBLE_ISSUES

            return (
              <div key={groupName} className="analysis-assistant-gen__issue-group">
                <button
                  type="button"
                  className="analysis-assistant-gen__group-header-button"
                  onClick={() => toggleGroup(groupName)}
                >
                  <div className="analysis-assistant-gen__group-header">
                    {groupName} ({groupIssues.length})
                  </div>
                  {isCollapsed ? (
                    <ChevronDown className="analysis-assistant-gen__group-chevron" />
                  ) : (
                    <ChevronUp className="analysis-assistant-gen__group-chevron" />
                  )}
                </button>
                {!isCollapsed && (
                  <div className="analysis-assistant-gen__group-cards">
                    {visibleIssues.map((issue) => (
                      <div
                        key={issue.id}
                        className="analysis-assistant-gen__issue-card"
                        onClick={() => handleIssueClick(issue)}
                      >
                        {/* Title row */}
                        <div className="analysis-assistant-gen__issue-title-row">
                          <div className="analysis-assistant-gen__issue-title-left">
                            {getIssueIcon(issue.type)}
                            <span className="analysis-assistant-gen__issue-title">{issue.title}</span>
                          </div>
                          {getSeverityPill(issue.severity)}
                        </div>

                        {/* Context line */}
                        <div className="analysis-assistant-gen__issue-context">{issue.context}</div>

                        {/* AI Note / Additional Intelligence */}
                        {issue.aiNote && (
                          <div className="analysis-assistant-gen__issue-ai-note">
                            {issue.aiNote}
                          </div>
                        )}

                        {/* CTA */}
                        <div className="analysis-assistant-gen__issue-cta">
                          <span className="analysis-assistant-gen__cta-text">View</span>
                          <ArrowRight className="analysis-assistant-gen__cta-icon" />
                        </div>
                      </div>
                    ))}
                    {hasMore && !showAll && (
                      <button
                        type="button"
                        className="analysis-assistant-gen__show-more"
                        onClick={(e) => {
                          e.stopPropagation()
                          setVisibleIssuesPerGroup((prev) => ({
                            ...prev,
                            [groupName]: groupIssues.length,
                          }))
                        }}
                      >
                        Show {groupIssues.length - MAX_VISIBLE_ISSUES} more
                      </button>
                    )}
                  </div>
                )}
              </div>
            )
          })}
        </div>
      )}

      {status === 'clear' && (
        <div className="analysis-assistant-gen__empty">
          <CheckCircle2 className="analysis-assistant-gen__empty-icon" />
          <div className="analysis-assistant-gen__empty-text">
            All checks passed. No action required.
          </div>
        </div>
      )}

      {/* Soft Footer - Only show when expanded */}
      {status === 'clear' && (
        <div className="analysis-assistant-gen__footer">
          Most invoices require zero review.
        </div>
      )}
    </aside>
  )
}
