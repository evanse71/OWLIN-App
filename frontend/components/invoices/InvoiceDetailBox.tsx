import React from 'react';
import { InvoiceListItem } from '../../hooks/useInvoices';
import ConfidenceBadge from './ConfidenceBadge';

interface InvoiceDetailBoxProps {
  invoice: InvoiceListItem | null;
  onRetryOCR?: () => void;
  onResolveIssue?: (lineId: number, action: string, payload?: any) => void;
}

const InvoiceDetailBox: React.FC<InvoiceDetailBoxProps> = ({
  invoice,
  onRetryOCR,
  onResolveIssue
}) => {
  if (!invoice) {
    return (
      <div className="flex items-center justify-center h-full text-[#6B7280]">
        Select an invoice to view details
      </div>
    );
  }

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-GB', { 
      day: '2-digit', 
      month: 'long', 
      year: 'numeric' 
    });
  };

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-GB', {
      style: 'currency',
      currency: 'GBP'
    }).format(amount);
  };

  return (
    <div className="h-full flex flex-col" data-ui="invoice-detail">
      {/* Header */}
      <div className="border-b border-[#E5E7EB] pb-4 mb-4">
        <div className="flex items-start justify-between mb-3">
          <div className="flex-1">
            <h2 className="text-[18px] font-semibold text-[#1F2937] mb-1">
              {invoice.supplier_name}
            </h2>
            <div className="flex items-center gap-4 text-[13px] text-[#6B7280]">
              <span>Invoice #{invoice.invoice_number}</span>
              <span>{formatDate(invoice.invoice_date)}</span>
              {invoice.page_range && (
                <span className="bg-[#E5E7EB] text-[#374151] rounded-[999px] px-2 py-0.5 text-[11px]">
                  {invoice.page_range}
                </span>
              )}
            </div>
          </div>
          <div className="text-right">
            <div className="text-[20px] font-bold text-[#111827]">
              {formatCurrency(invoice.total_amount)}
            </div>
            <ConfidenceBadge confidence={invoice.confidence} />
          </div>
        </div>

        {/* Actions */}
        <div className="flex items-center gap-2">
          <button className="bg-[#2563EB] hover:bg-[#1D4ED8] text-white rounded-[8px] px-3 py-1.5 text-[13px] font-medium transition-colors">
            Edit
          </button>
          <button className="bg-white border border-[#E5E7EB] hover:bg-[#F9FAFB] text-[#374151] rounded-[8px] px-3 py-1.5 text-[13px] font-medium transition-colors">
            Open PDF
          </button>
          {invoice.status === 'error' && onRetryOCR && (
            <button 
              onClick={onRetryOCR}
              className="bg-white border border-[#E5E7EB] hover:bg-[#F9FAFB] text-[#374151] rounded-[8px] px-3 py-1.5 text-[13px] font-medium transition-colors"
            >
              Retry OCR
            </button>
          )}
        </div>
      </div>

      {/* Invoice Details */}
      <div className="flex-1 overflow-auto">
        <div className="space-y-4">
          <h3 className="text-[14px] font-semibold text-[#1F2937]">Invoice Details</h3>
          
          <div className="bg-[#F9FAFB] rounded-[8px] p-4 space-y-3">
            <div className="grid grid-cols-2 gap-4 text-[13px]">
              <div>
                <span className="text-[#6B7280]">Status:</span>
                <span className="ml-2 font-medium text-[#374151]">{invoice.status}</span>
              </div>
              <div>
                <span className="text-[#6B7280]">Confidence:</span>
                <span className="ml-2 font-medium text-[#374151]">{invoice.confidence}%</span>
              </div>
              <div>
                <span className="text-[#6B7280]">Issues:</span>
                <span className="ml-2 font-medium text-[#374151]">{invoice.issues_count || 0}</span>
              </div>
              <div>
                <span className="text-[#6B7280]">Upload ID:</span>
                <span className="ml-2 font-medium text-[#374151]">{invoice.upload_id}</span>
              </div>
            </div>
            
            {invoice.parent_pdf_filename && (
              <div>
                <span className="text-[#6B7280] text-[13px]">Source file:</span>
                <div className="mt-1 text-[12px] text-[#374151] font-mono bg-white px-2 py-1 rounded-[4px] border">
                  {invoice.parent_pdf_filename}
                </div>
              </div>
            )}
          </div>
          
          {invoice.issues_count > 0 && (
            <div className="bg-[#FEF3C7] border border-[#FDE68A] rounded-[8px] p-3">
              <div className="text-[13px] text-[#92400E] font-medium mb-1">
                ⚠️ {invoice.issues_count} issue{invoice.issues_count !== 1 ? 's' : ''} detected
              </div>
              <div className="text-[12px] text-[#92400E]">
                This invoice has flagged issues that require attention.
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default InvoiceDetailBox; 