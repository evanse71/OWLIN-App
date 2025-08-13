import React, { useState } from 'react';

interface SupplierSummary {
  supplier_id: string;
  supplier_name: string;
  total_invoices: number;
  total_flagged_items: number;
  estimated_credit: number;
  common_issues: string[];
  top_flagged_items: string[];
  flagged_dates: string[];
  summary_message: string;
  date_range: {
    from: string;
    to: string;
  };
  credit_breakdown: Array<{
    item_name: string;
    invoice_id: string;
    issue_type: string;
    suggested_credit: number;
    date: string;
  }>;
}

interface SupplierSummaryBoxProps {
  summary: SupplierSummary | null;
  onCopySummary: (summary: SupplierSummary) => void;
  onExportPDF: (summary: SupplierSummary) => void;
  onOpenEscalation: (summary: SupplierSummary) => void;
  userRole: 'gm' | 'finance' | 'shift';
  isLoading?: boolean;
}

const SupplierSummaryBox: React.FC<SupplierSummaryBoxProps> = ({
  summary,
  onCopySummary,
  onExportPDF,
  onOpenEscalation,
  userRole,
  isLoading = false
}) => {
  const [isCopied, setIsCopied] = useState(false);

  // Only show for GM or Finance users
  if (userRole !== 'gm' && userRole !== 'finance') {
    return null;
  }

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-GB', {
      day: 'numeric',
      month: 'short'
    });
  };

  const formatDateRange = (from: string, to: string) => {
    const fromDate = new Date(from);
    const toDate = new Date(to);
    
    const fromFormatted = fromDate.toLocaleDateString('en-GB', {
      day: 'numeric',
      month: 'short'
    });
    
    const toFormatted = toDate.toLocaleDateString('en-GB', {
      day: 'numeric',
      month: 'short',
      year: 'numeric'
    });
    
    return `${fromFormatted} – ${toFormatted}`;
  };

  const handleCopySummary = async () => {
    if (!summary) return;
    
    try {
      const summaryText = `
Supplier Summary: ${summary.supplier_name}
Date Range: ${formatDateRange(summary.date_range.from, summary.date_range.to)}

📊 Overview:
- Total Invoices: ${summary.total_invoices}
- Flagged Issues: ${summary.total_flagged_items} items
- Estimated Credit Due: £${summary.estimated_credit.toFixed(2)}

🛠 Common Problems:
${summary.common_issues.map(issue => `- ${issue}`).join('\n')}

🔥 Top Affected Items:
${summary.top_flagged_items.map(item => `- ${item}`).join('\n')}

✏️ Summary:
${summary.summary_message}
      `.trim();
      
      await navigator.clipboard.writeText(summaryText);
      setIsCopied(true);
      onCopySummary(summary);
      
      // Reset copied state after 3 seconds
      setTimeout(() => setIsCopied(false), 3000);
    } catch (error) {
      console.error('Failed to copy to clipboard:', error);
    }
  };

  const handleExportPDF = () => {
    if (!summary) return;
    onExportPDF(summary);
  };

  const handleOpenEscalation = () => {
    if (!summary) return;
    onOpenEscalation(summary);
  };

  if (isLoading) {
    return (
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
        <div className="flex items-center space-x-3 mb-4">
          <div className="w-6 h-6 bg-blue-100 rounded-full flex items-center justify-center">
            <svg className="w-4 h-4 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
          </div>
          <h3 className="text-lg font-semibold text-gray-900">Generating Supplier Summary...</h3>
        </div>
        <div className="animate-pulse">
          <div className="h-4 bg-gray-200 rounded mb-2"></div>
          <div className="h-4 bg-gray-200 rounded mb-2 w-3/4"></div>
          <div className="h-4 bg-gray-200 rounded mb-2 w-1/2"></div>
        </div>
      </div>
    );
  }

  if (!summary) {
    return (
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
        <div className="flex items-center space-x-3 mb-4">
          <div className="w-6 h-6 bg-green-100 rounded-full flex items-center justify-center">
            <svg className="w-4 h-4 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
          </div>
          <h3 className="text-lg font-semibold text-gray-900">No Issues Found</h3>
        </div>
        <p className="text-gray-600">
          No flagged issues found in the selected date range. You&apos;re good to go! 🎉
        </p>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
      {/* Header */}
      <div className="flex items-center space-x-3 mb-6">
        <div className="w-6 h-6 bg-blue-100 rounded-full flex items-center justify-center">
          <svg className="w-4 h-4 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
          </svg>
        </div>
        <h3 className="text-lg font-semibold text-gray-900">Supplier Summary</h3>
      </div>

      {/* Overview Section */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <div className="bg-blue-50 rounded-lg p-4">
          <div className="flex items-center space-x-2 mb-2">
            <span className="text-2xl">📦</span>
            <span className="text-sm font-medium text-blue-900">Supplier</span>
          </div>
          <p className="text-lg font-semibold text-blue-900">{summary.supplier_name}</p>
        </div>
        
        <div className="bg-green-50 rounded-lg p-4">
          <div className="flex items-center space-x-2 mb-2">
            <span className="text-2xl">🧾</span>
            <span className="text-sm font-medium text-green-900">Total Invoices</span>
          </div>
          <p className="text-lg font-semibold text-green-900">{summary.total_invoices}</p>
        </div>
        
        <div className="bg-red-50 rounded-lg p-4">
          <div className="flex items-center space-x-2 mb-2">
            <span className="text-2xl">⚠️</span>
            <span className="text-sm font-medium text-red-900">Flagged Issues</span>
          </div>
          <p className="text-lg font-semibold text-red-900">{summary.total_flagged_items} items</p>
        </div>
        
        <div className="bg-yellow-50 rounded-lg p-4">
          <div className="flex items-center space-x-2 mb-2">
            <span className="text-2xl">💸</span>
            <span className="text-sm font-medium text-yellow-900">Estimated Credit</span>
          </div>
          <p className="text-lg font-semibold text-yellow-900">£{summary.estimated_credit.toFixed(2)}</p>
        </div>
      </div>

      {/* Date Range */}
      <div className="mb-6">
        <div className="flex items-center space-x-2 mb-2">
          <span className="text-lg">📅</span>
          <span className="text-sm font-medium text-gray-700">Dates Affected</span>
        </div>
        <p className="text-gray-900">{formatDateRange(summary.date_range.from, summary.date_range.to)}</p>
      </div>

      {/* Common Problems */}
      {summary.common_issues.length > 0 && (
        <div className="mb-6">
          <div className="flex items-center space-x-2 mb-3">
            <span className="text-lg">🛠</span>
            <span className="text-sm font-medium text-gray-700">Common Problems</span>
          </div>
          <div className="space-y-1">
            {summary.common_issues.map((issue, index) => (
              <div key={index} className="flex items-center space-x-2">
                <span className="text-red-500">•</span>
                <span className="text-gray-900">{issue}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Top Affected Items */}
      {summary.top_flagged_items.length > 0 && (
        <div className="mb-6">
          <div className="flex items-center space-x-2 mb-3">
            <span className="text-lg">🔥</span>
            <span className="text-sm font-medium text-gray-700">Top Affected Items</span>
          </div>
          <div className="space-y-1">
            {summary.top_flagged_items.map((item, index) => (
              <div key={index} className="flex items-center space-x-2">
                <span className="text-orange-500">•</span>
                <span className="text-gray-900">{item}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Summary Preview */}
      <div className="mb-6">
        <div className="flex items-center space-x-2 mb-3">
          <span className="text-lg">✏️</span>
          <span className="text-sm font-medium text-gray-700">Summary Preview</span>
        </div>
        <div className="bg-gray-50 rounded-lg p-4">
          <p className="text-gray-900 text-sm leading-relaxed">{summary.summary_message}</p>
        </div>
      </div>

      {/* Credit Breakdown */}
      {summary.credit_breakdown.length > 0 && (
        <div className="mb-6">
          <div className="flex items-center space-x-2 mb-3">
            <span className="text-lg">💰</span>
            <span className="text-sm font-medium text-gray-700">Credit Breakdown</span>
          </div>
          <div className="bg-gray-50 rounded-lg p-4 max-h-40 overflow-y-auto">
            <div className="space-y-2">
              {summary.credit_breakdown.slice(0, 5).map((credit, index) => (
                <div key={index} className="flex justify-between items-center text-sm">
                  <span className="text-gray-900">{credit.item_name}</span>
                  <span className="text-green-600 font-medium">£{credit.suggested_credit.toFixed(2)}</span>
                </div>
              ))}
              {summary.credit_breakdown.length > 5 && (
                <div className="text-xs text-gray-500 text-center pt-2 border-t border-gray-200">
                  +{summary.credit_breakdown.length - 5} more items
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Action Buttons */}
      <div className="flex flex-wrap gap-3">
        <button
          onClick={handleCopySummary}
          className="px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 transition-colors"
        >
          {isCopied ? '📋 Copied!' : '📋 Copy Summary to Clipboard'}
        </button>
        
        <button
          onClick={handleExportPDF}
          className="px-4 py-2 bg-white border border-gray-300 text-gray-700 text-sm font-medium rounded-md hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-gray-500 focus:ring-offset-2 transition-colors"
        >
          📄 Export PDF
        </button>
        
        <button
          onClick={handleOpenEscalation}
          className="px-4 py-2 bg-red-600 text-white text-sm font-medium rounded-md hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-offset-2 transition-colors"
        >
          📧 Open Escalation Message
        </button>
      </div>
    </div>
  );
};

export default SupplierSummaryBox; 