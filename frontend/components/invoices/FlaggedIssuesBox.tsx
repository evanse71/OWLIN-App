import React from 'react';
import { InvoiceListItem } from '../../hooks/useInvoices';

interface FlaggedIssuesBoxProps {
  flaggedInvoices: InvoiceListItem[];
  onExportCSV?: () => void;
}

const FlaggedIssuesBox: React.FC<FlaggedIssuesBoxProps> = ({
  flaggedInvoices,
  onExportCSV
}) => {
  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-GB', {
      style: 'currency',
      currency: 'GBP'
    }).format(amount);
  };

  const totalValue = flaggedInvoices.reduce((sum, inv) => sum + inv.total_amount, 0);
  const totalIssues = flaggedInvoices.reduce((sum, inv) => sum + (inv.issues_count || 0), 0);

  if (flaggedInvoices.length === 0) {
    return (
      <div className="bg-white rounded-[12px] border border-[#E5E7EB] p-4">
        <h3 className="text-[14px] font-semibold text-[#1F2937] mb-2">Flagged Issues</h3>
        <div className="text-[13px] text-[#6B7280] text-center py-4">
          No flagged issues at this time.
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-[12px] border border-[#E5E7EB] p-4">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-[14px] font-semibold text-[#1F2937]">
          Flagged Issues ({flaggedInvoices.length})
        </h3>
        {onExportCSV && (
          <button
            onClick={onExportCSV}
            className="bg-[#2563EB] hover:bg-[#1D4ED8] text-white rounded-[8px] px-3 py-1.5 text-[12px] font-medium transition-colors"
          >
            Export CSV
          </button>
        )}
      </div>

      {/* Summary Stats */}
      <div className="grid grid-cols-3 gap-4 mb-4 p-3 bg-[#F9FAFB] rounded-[8px]">
        <div className="text-center">
          <div className="text-[16px] font-bold text-[#111827]">{flaggedInvoices.length}</div>
          <div className="text-[11px] text-[#6B7280]">Invoices</div>
        </div>
        <div className="text-center">
          <div className="text-[16px] font-bold text-[#111827]">{totalIssues}</div>
          <div className="text-[11px] text-[#6B7280]">Total Issues</div>
        </div>
        <div className="text-center">
          <div className="text-[16px] font-bold text-[#111827]">{formatCurrency(totalValue)}</div>
          <div className="text-[11px] text-[#6B7280]">Total Value</div>
        </div>
      </div>

      {/* Issues Table */}
      <div className="max-h-48 overflow-y-auto">
        <table className="w-full text-[12px]">
          <thead className="sticky top-0 bg-white">
            <tr className="border-b border-[#E5E7EB]">
              <th className="text-left py-2 px-2 font-medium text-[#6B7280]">Invoice</th>
              <th className="text-left py-2 px-2 font-medium text-[#6B7280]">Supplier</th>
              <th className="text-right py-2 px-2 font-medium text-[#6B7280]">Value</th>
              <th className="text-center py-2 px-2 font-medium text-[#6B7280]">Issues</th>
            </tr>
          </thead>
          <tbody>
            {flaggedInvoices.map((invoice) => (
              <tr key={invoice.id} className="border-b border-[#F3F4F6] hover:bg-[#F9FAFB]">
                <td className="py-2 px-2">
                  <div className="font-medium text-[#374151]">#{invoice.invoice_number}</div>
                  <div className="text-[11px] text-[#6B7280]">
                    {new Date(invoice.invoice_date).toLocaleDateString('en-GB')}
                  </div>
                </td>
                <td className="py-2 px-2">
                  <div className="text-[#374151] truncate max-w-32">{invoice.supplier_name}</div>
                </td>
                <td className="py-2 px-2 text-right">
                  <div className="font-medium text-[#374151]">{formatCurrency(invoice.total_amount)}</div>
                </td>
                <td className="py-2 px-2 text-center">
                  <span className="bg-[#FEE2E2] text-[#7F1D1D] border border-[#FECACA] rounded-[999px] px-2 py-0.5 text-[11px] font-semibold">
                    {invoice.issues_count}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Action Summary */}
      <div className="mt-4 pt-3 border-t border-[#E5E7EB]">
        <div className="flex items-center justify-between text-[12px] text-[#6B7280]">
          <span>Average issues per invoice: {(totalIssues / flaggedInvoices.length).toFixed(1)}</span>
          <span>Average value: {formatCurrency(totalValue / flaggedInvoices.length)}</span>
        </div>
      </div>
    </div>
  );
};

export default FlaggedIssuesBox; 