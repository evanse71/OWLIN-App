import React, { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';

// Utility functions
const formatCurrency = (amount: number): string => {
  return new Intl.NumberFormat('en-GB', {
    style: 'currency',
    currency: 'GBP'
  }).format(amount);
};

const formatDate = (dateString: string): string => {
  return new Date(dateString).toLocaleDateString('en-GB');
};

interface FlaggedIssue {
  id: string;
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
  severity?: string;
  assignee_id?: string;
  resolved_by?: string;
  resolved_at?: string;
  last_comment_at?: string;
}

interface FlaggedIssuesTableProps {
  issues: FlaggedIssue[];
  selectedIds: string[];
  onSelectionChange: (selectedIds: string[]) => void;
  onResolveIssue: (issueId: string) => void;
  onEscalateIssue: (issueId: string) => void;
  userRole: 'gm' | 'finance' | 'shift_lead';
  isLoading?: boolean;
}

export default function FlaggedIssuesTable({
  issues,
  selectedIds,
  onSelectionChange,
  onResolveIssue,
  onEscalateIssue,
  userRole,
  isLoading = false
}: FlaggedIssuesTableProps) {
  const [resolvingIssue, setResolvingIssue] = useState<string | null>(null);

  const handleSelectAll = (checked: boolean) => {
    if (checked) {
      onSelectionChange(issues.map(issue => issue.id));
    } else {
      onSelectionChange([]);
    }
  };

  const handleSelectIssue = (issueId: string, checked: boolean) => {
    if (checked) {
      onSelectionChange([...selectedIds, issueId]);
    } else {
      onSelectionChange(selectedIds.filter(id => id !== issueId));
    }
  };

  const handleResolveIssue = async (issueId: string) => {
    setResolvingIssue(issueId);
    try {
      await onResolveIssue(issueId);
    } finally {
      setResolvingIssue(null);
    }
  };

  const handleEscalateIssue = async (issueId: string) => {
    setResolvingIssue(issueId);
    try {
      await onEscalateIssue(issueId);
    } finally {
      setResolvingIssue(null);
    }
  };

  const isAllSelected = issues.length > 0 && selectedIds.length === issues.length;
  const isIndeterminate = selectedIds.length > 0 && selectedIds.length < issues.length;

  const canResolve = userRole === 'gm' || userRole === 'finance';
  const canEscalate = userRole === 'gm';

  return (
    <div className="overflow-x-auto">
      <table className="min-w-full divide-y divide-gray-200">
        <thead className="bg-gray-50">
          <tr>
            <th className="w-12 px-3 py-3">
              <input
                type="checkbox"
                checked={isAllSelected}
                onChange={(e) => handleSelectAll(e.target.checked)}
                disabled={isLoading}
                className="w-4 h-4 text-blue-600 rounded focus:ring-blue-500"
              />
            </th>
            <th className="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Item
            </th>
            <th className="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Quantity
            </th>
            <th className="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Price
            </th>
            <th className="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Total
            </th>
            <th className="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Supplier
            </th>
            <th className="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Venue
            </th>
            <th className="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Date
            </th>
            <th className="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Status
            </th>
            <th className="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Actions
            </th>
          </tr>
        </thead>
        <tbody className="bg-white divide-y divide-gray-200">
          {issues.map((issue) => (
            <tr key={issue.id} className="hover:bg-gray-50">
              <td className="px-3 py-4">
                <input
                  type="checkbox"
                  checked={selectedIds.includes(issue.id)}
                  onChange={(e) => handleSelectIssue(issue.id, e.target.checked)}
                  disabled={isLoading}
                  className="w-4 h-4 text-blue-600 rounded focus:ring-blue-500"
                />
              </td>
              <td className="px-3 py-4">
                <div className="text-sm font-medium text-gray-900">{issue.item}</div>
                <div className="text-sm text-gray-500">#{issue.invoice_number}</div>
              </td>
              <td className="px-3 py-4 text-sm text-gray-900">
                {issue.qty}
              </td>
              <td className="px-3 py-4 text-sm text-gray-900">
                {formatCurrency(issue.price)}
              </td>
              <td className="px-3 py-4 text-sm font-medium text-gray-900">
                {formatCurrency(issue.total_value)}
              </td>
              <td className="px-3 py-4 text-sm text-gray-900">
                {issue.supplier}
              </td>
              <td className="px-3 py-4 text-sm text-gray-900">
                {issue.venue}
              </td>
              <td className="px-3 py-4 text-sm text-gray-900">
                {formatDate(issue.invoice_date)}
              </td>
              <td className="px-3 py-4">
                <div className="flex flex-col space-y-1">
                  {issue.severity && (
                    <Badge variant={issue.severity === 'high' ? 'destructive' : 'secondary'}>
                      {issue.severity}
                    </Badge>
                  )}
                  {issue.resolved_by && (
                    <Badge variant="outline" className="text-xs">
                      Resolved
                    </Badge>
                  )}
                </div>
              </td>
              <td className="px-3 py-4">
                <div className="flex space-x-2">
                  {canResolve && !issue.resolved_by && (
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => handleResolveIssue(issue.id)}
                      disabled={resolvingIssue === issue.id || isLoading}
                      className="text-green-600 border-green-600 hover:bg-green-50"
                    >
                      {resolvingIssue === issue.id ? 'Resolving...' : 'Resolve'}
                    </Button>
                  )}
                  {canEscalate && !issue.resolved_by && (
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => handleEscalateIssue(issue.id)}
                      disabled={resolvingIssue === issue.id || isLoading}
                      className="text-amber-600 border-amber-600 hover:bg-amber-50"
                    >
                      {resolvingIssue === issue.id ? 'Escalating...' : 'Escalate'}
                    </Button>
                  )}
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      
      {issues.length === 0 && (
        <div className="text-center py-8 text-gray-500">
          No flagged issues found
        </div>
      )}
    </div>
  );
} 