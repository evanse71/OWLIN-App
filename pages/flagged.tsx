import React, { useState, useEffect } from 'react';
import AppShell from '@/components/layout/AppShell';

interface FlaggedIssue {
  id: number;
  item: string;
  qty: number;
  price: number;
  flagged: boolean;
  source: string;
  upload_timestamp: string;
  invoice_number: string;
  supplier: string;
  invoice_date: string;
  venue: string;
  total_value: number;
}

interface FlaggedSummary {
  total_issues: number;
  total_error_value: number;
  affected_invoices: number;
  affected_suppliers: number;
  supplier_breakdown: Array<{
    supplier: string;
    issue_count: number;
    total_error: number;
  }>;
}

const FlaggedIssuesPage: React.FC = () => {
  const [flaggedIssues, setFlaggedIssues] = useState<FlaggedIssue[]>([]);
  const [summary, setSummary] = useState<FlaggedSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [resolvingIssue, setResolvingIssue] = useState<number | null>(null);

  useEffect(() => {
    fetchFlaggedIssues();
    fetchSummary();
  }, []);

  const fetchFlaggedIssues = async () => {
    try {
      const response = await fetch('/api/flagged-issues/', { cache: 'no-store' });
      if (!response.ok) {
        throw new Error('Failed to fetch flagged issues');
      }
      const data = await response.json();
      setFlaggedIssues(data.flagged_issues);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
    } finally {
      setLoading(false);
    }
  };

  const fetchSummary = async () => {
    try {
      const response = await fetch('/api/flagged-issues/summary', { cache: 'no-store' });
      if (!response.ok) {
        throw new Error('Failed to fetch summary');
      }
      const data = await response.json();
      setSummary(data);
    } catch (err) {
      console.error('Error fetching summary:', err);
    }
  };

  const handleResolveIssue = async (issueId: number) => {
    try {
      setResolvingIssue(issueId);
      const response = await fetch(`/api/flagged-issues/${issueId}/resolve`, {
        method: 'POST',
      });
      
      if (!response.ok) {
        throw new Error('Failed to resolve issue');
      }
      
      // Remove the resolved issue from the list
      setFlaggedIssues(prev => prev.filter(issue => issue.id !== issueId));
      
      // Refresh summary
      fetchSummary();
      
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to resolve issue');
    } finally {
      setResolvingIssue(null);
    }
  };

  const handleEscalateIssue = async (issueId: number) => {
    try {
      setResolvingIssue(issueId);
      const response = await fetch(`/api/flagged-issues/${issueId}/escalate`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ reason: 'Manual escalation' }),
      });
      
      if (!response.ok) {
        throw new Error('Failed to escalate issue');
      }
      
      alert('Issue escalated successfully');
      
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to escalate issue');
    } finally {
      setResolvingIssue(null);
    }
  };

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-GB', {
      style: 'currency',
      currency: 'GBP'
    }).format(amount);
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-GB');
  };

  if (loading) {
    return (
      <AppShell>
        <div className="py-8 max-w-7xl mx-auto">
          <div className="flex items-center justify-center h-64">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-owlin-cerulean"></div>
          </div>
        </div>
      </AppShell>
    );
  }

  if (error) {
    return (
      <AppShell>
        <div className="py-8 max-w-7xl mx-auto">
          <div className="bg-owlin-card border border-owlin-stroke rounded-owlin p-4">
            <p className="text-red-700">Error loading flagged issues: {error}</p>
            <button 
              onClick={() => {
                setError(null);
                fetchFlaggedIssues();
                fetchSummary();
              }}
              className="mt-2 px-4 py-2 bg-[var(--owlin-sapphire)] text-white rounded-owlin hover:brightness-110"
            >
              Retry
            </button>
          </div>
        </div>
      </AppShell>
    );
  }

  return (
    <AppShell>
      <div className="py-6">
        <div className="max-w-7xl mx-auto px-4">
          <div className="max-w-7xl mx-auto">
            {/* Header */}
            <div className="mb-8">
              <h1 className="text-3xl font-semibold text-owlin-text mb-2">Flagged Issues</h1>
              <p className="text-owlin-muted">
                Review and resolve discrepancies between invoices and delivery notes
              </p>
            </div>

            {/* Summary Cards */}
            {summary && (
              <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
                <div className="bg-owlin-card rounded-owlin shadow-owlin p-6 border border-owlin-stroke">
                  <div className="flex items-center">
                    <div className="p-3 rounded-owlin bg-[color-mix(in_oklab,var(--owlin-sapphire)_12%,transparent)]">
                      <svg className="w-8 h-8 text-owlin-cerulean" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.732 16.5c-.77.833.192 2.5 1.732 2.5z" />
                      </svg>
                    </div>
                    <div className="ml-4">
                      <p className="text-sm font-medium text-owlin-muted">Total Issues</p>
                      <p className="text-2xl font-semibold text-owlin-text">{summary.total_issues}</p>
                    </div>
                  </div>
                </div>

                <div className="bg-owlin-card rounded-owlin shadow-owlin p-6 border border-owlin-stroke">
                  <div className="flex items-center">
                    <div className="p-3 rounded-owlin bg-[color-mix(in_oklab,var(--owlin-sapphire)_12%,transparent)]">
                      <svg className="w-8 h-8 text-owlin-cerulean" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1" />
                      </svg>
                    </div>
                    <div className="ml-4">
                      <p className="text-sm font-medium text-owlin-muted">Total Error Value</p>
                      <p className="text-2xl font-semibold text-owlin-text">{formatCurrency(summary.total_error_value)}</p>
                    </div>
                  </div>
                </div>

                <div className="bg-owlin-card rounded-owlin shadow-owlin p-6 border border-owlin-stroke">
                  <div className="flex items-center">
                    <div className="p-3 rounded-owlin bg-[color-mix(in_oklab,var(--owlin-sapphire)_12%,transparent)]">
                      <svg className="w-8 h-8 text-owlin-cerulean" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                      </svg>
                    </div>
                    <div className="ml-4">
                      <p className="text-sm font-medium text-owlin-muted">Affected Invoices</p>
                      <p className="text-2xl font-semibold text-owlin-text">{summary.affected_invoices}</p>
                    </div>
                  </div>
                </div>

                <div className="bg-owlin-card rounded-owlin shadow-owlin p-6 border border-owlin-stroke">
                  <div className="flex items-center">
                    <div className="p-3 rounded-owlin bg-[color-mix(in_oklab,var(--owlin-sapphire)_12%,transparent)]">
                      <svg className="w-8 h-8 text-owlin-cerulean" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
                      </svg>
                    </div>
                    <div className="ml-4">
                      <p className="text-sm font-medium text-owlin-muted">Affected Suppliers</p>
                      <p className="text-2xl font-semibold text-owlin-text">{summary.affected_suppliers}</p>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* Supplier Breakdown */}
            {summary && summary.supplier_breakdown.length > 0 && (
              <div className="bg-owlin-card rounded-owlin shadow-owlin p-6 mb-8 border border-owlin-stroke">
                <h3 className="text-lg font-semibold text-owlin-text mb-4">Issues by Supplier</h3>
                <div className="overflow-x-auto">
                  <table className="min-w-full">
                    <thead className="sticky top-0 z-[1] bg-owlin-card border-b border-owlin-stroke">
                      <tr>
                        <th className="px-6 py-3 text-left text-xs font-medium text-owlin-muted uppercase tracking-wider">
                          Supplier
                        </th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-owlin-muted uppercase tracking-wider">
                          Issue Count
                        </th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-owlin-muted uppercase tracking-wider">
                          Total Error Value
                        </th>
                      </tr>
                    </thead>
                    <tbody className="bg-owlin-card divide-y divide-owlin-stroke">
                      {summary.supplier_breakdown.map((supplier, index) => (
                        <tr key={index} className="odd:bg-[color-mix(in_oklab,var(--owlin-bg)_52%,transparent)]">
                          <td className="px-6 py-3 whitespace-nowrap text-sm font-medium text-owlin-text">
                            {supplier.supplier}
                          </td>
                          <td className="px-6 py-3 whitespace-nowrap text-sm text-owlin-muted">
                            {supplier.issue_count}
                          </td>
                          <td className="px-6 py-3 whitespace-nowrap text-sm text-owlin-muted">
                            {formatCurrency(supplier.total_error)}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {/* Flagged Issues List */}
            <div className="bg-owlin-card rounded-owlin shadow-owlin border border-owlin-stroke">
              <div className="px-6 py-4 border-b border-owlin-stroke">
                <h3 className="text-lg font-semibold text-owlin-text">
                  Flagged Issues ({flaggedIssues.length})
                </h3>
              </div>
              
              {flaggedIssues.length === 0 ? (
                <div className="p-8 text-center">
                  <div className="text-owlin-muted mb-4">
                    <svg className="mx-auto h-12 w-12" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                  </div>
                  <h3 className="text-lg font-medium text-owlin-text mb-2">No flagged issues</h3>
                  <p className="text-owlin-muted">All invoices are processing correctly.</p>
                </div>
              ) : (
                <div className="divide-y divide-owlin-stroke">
                  {flaggedIssues.map((issue) => (
                    <div key={issue.id} className="p-6">
                      <div className="flex items-start justify-between">
                        <div className="flex-1">
                          <div className="flex items-center mb-2">
                            <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-[color-mix(in_oklab,var(--owlin-sapphire)_12%,transparent)] text-owlin-cerulean">
                              Discrepancy
                            </span>
                            <span className="ml-2 text-sm text-owlin-muted">
                              Invoice #{issue.invoice_number}
                            </span>
                          </div>
                          
                          <h4 className="text-lg font-medium text-owlin-text mb-2">{issue.item}</h4>
                          
                          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                            <div>
                              <span className="text-owlin-muted">Quantity:</span>
                              <span className="ml-1 font-medium text-owlin-text">{issue.qty}</span>
                            </div>
                            <div>
                              <span className="text-owlin-muted">Price:</span>
                              <span className="ml-1 font-medium text-owlin-text">{formatCurrency(issue.price)}</span>
                            </div>
                            <div>
                              <span className="text-owlin-muted">Total:</span>
                              <span className="ml-1 font-medium text-owlin-text">{formatCurrency(issue.total_value)}</span>
                            </div>
                            <div>
                              <span className="text-owlin-muted">Source:</span>
                              <span className="ml-1 font-medium text-owlin-text">{issue.source}</span>
                            </div>
                          </div>
                          
                          <div className="mt-3 text-sm text-owlin-muted">
                            <span>Supplier: {issue.supplier}</span>
                            <span className="mx-2">•</span>
                            <span>Venue: {issue.venue}</span>
                            <span className="mx-2">•</span>
                            <span>Date: {formatDate(issue.invoice_date)}</span>
                          </div>
                        </div>
                        
                        <div className="ml-6 flex flex-col space-y-2">
                          <button
                            onClick={() => handleResolveIssue(issue.id)}
                            disabled={resolvingIssue === issue.id}
                            className="inline-flex items-center px-3 py-2 border border-transparent text-sm leading-4 font-medium rounded-owlin text-white bg-[var(--owlin-sapphire)] hover:brightness-110 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-owlin-sapphire focus-visible:ring-offset-2 disabled:opacity-50"
                          >
                            {resolvingIssue === issue.id ? (
                              <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                            ) : (
                              'Resolve'
                            )}
                          </button>
                          
                          <button
                            onClick={() => handleEscalateIssue(issue.id)}
                            disabled={resolvingIssue === issue.id}
                            className="inline-flex items-center px-3 py-2 border border-owlin-stroke text-sm leading-4 font-medium rounded-owlin text-owlin-text bg-owlin-card hover:bg-[color-mix(in_oklab,var(--owlin-card)_92%,transparent)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-owlin-sapphire focus-visible:ring-offset-2 disabled:opacity-50"
                          >
                            Escalate
                          </button>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </AppShell>
  );
};

export default FlaggedIssuesPage; 