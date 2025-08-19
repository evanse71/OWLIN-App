import React from 'react';
import { InvoiceListItem } from '../../hooks/useInvoices';
import ConfidenceBadge from './ConfidenceBadge';

interface InvoiceCardProps {
  invoice: InvoiceListItem;
  isExpanded: boolean;
  isSelected: boolean;
  onClick: () => void;
  onKeyDown: (e: React.KeyboardEvent) => void;
  tabIndex: number;
  'aria-label': string;
}

const InvoiceCard: React.FC<InvoiceCardProps> = ({
  invoice,
  isExpanded,
  isSelected,
  onClick,
  onKeyDown,
  tabIndex,
  'aria-label': ariaLabel
}) => {
  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-GB', { 
      day: '2-digit', 
      month: 'short', 
      year: '2-digit' 
    });
  };

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-GB', {
      style: 'currency',
      currency: 'GBP'
    }).format(amount);
  };

  const getStatusBadge = () => {
    const baseClasses = "px-2 py-0.5 rounded-[999px] text-[11px] font-medium border";
    
    switch (invoice.status) {
      case 'scanning':
        return (
          <span className={`${baseClasses} bg-[#DBEAFE] text-[#1E40AF] border-[#BFDBFE]`}>
            ⏳ Processing
          </span>
        );
      case 'parsed':
        return (
          <span className={`${baseClasses} bg-[#ECFDF5] text-[#065F46] border-[#D1FAE5]`}>
            ✅ Ready
          </span>
        );
      case 'paired':
        return (
          <span className={`${baseClasses} bg-[#ECFDF5] text-[#065F46] border-[#D1FAE5]`}>
            🔗 Linked
          </span>
        );
      case 'flagged':
        return (
          <span className={`${baseClasses} bg-[#FEE2E2] text-[#7F1D1D] border-[#FECACA]`}>
            ⚠️ Issues
          </span>
        );
      case 'error':
        return (
          <span className={`${baseClasses} bg-[#FEE2E2] text-[#7F1D1D] border-[#FECACA]`}>
            ❌ Failed
          </span>
        );
      default:
        return null;
    }
  };

  const getProgressIndicator = () => {
    if (invoice.status !== 'scanning') return null;
    
    return (
      <div className="mt-2">
        <div className="h-[6px] rounded-[6px] bg-[#E5E7EB] overflow-hidden">
          <div 
            className="h-full bg-[#0284C7] transition-[width] duration-300 ease-in-out"
            style={{ width: '60%' }} // This would come from progress state
            role="progressbar"
            aria-valuenow={60}
            aria-valuemax={100}
            aria-label="Processing progress"
          />
        </div>
        <p className="text-[11px] text-[#6B7280] mt-1">Detecting invoice boundaries...</p>
      </div>
    );
  };

  return (
    <div
      className={`bg-white rounded-[12px] border border-[#E5E7EB] shadow-sm transition-all duration-200 ease-in-out cursor-pointer ${
        isSelected ? 'ring-2 ring-[#2563EB] ring-opacity-50' : 'hover:border-[#D1D5DB]'
      }`}
      onClick={onClick}
      onKeyDown={onKeyDown}
      tabIndex={tabIndex}
      aria-label={ariaLabel}
      role="button"
      aria-expanded={isExpanded}
      data-ui="invoice-card"
      data-expanded={isExpanded ? 'true' : 'false'}
    >
      {/* Header */}
      <div className="flex items-center justify-between px-3 py-2">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <span className="text-[12px] text-[#6B7280] font-mono">
              {invoice.invoice_number || 'No number'}
            </span>
            {invoice.page_range && (
              <span className="bg-[#E5E7EB] text-[#374151] rounded-[999px] px-2 py-0.5 text-[11px]">
                {invoice.page_range}
              </span>
            )}
          </div>
          <h3 className="text-[14px] font-semibold text-[#1F2937] truncate">
            {invoice.supplier_name || 'Unknown supplier'}
          </h3>
        </div>
        
        <div className="flex items-center gap-2">
          <div className="text-right">
            <div className="text-[12px] text-[#6B7280]">
              {formatDate(invoice.invoice_date)}
            </div>
            <div className="text-[14px] font-semibold text-[#111827]">
              {formatCurrency(invoice.total_amount)}
            </div>
          </div>
          
          {/* Chevron */}
          <svg 
            xmlns="http://www.w3.org/2000/svg" 
            width="12" 
            height="12" 
            fill="none" 
            stroke="#6B7280" 
            strokeWidth="2" 
            strokeLinecap="round" 
            strokeLinejoin="round" 
            className={`transition-transform duration-200 ${isExpanded ? 'rotate-180' : ''}`}
            aria-label="Expand"
          >
            <polyline points="3,4 6,8 9,4"/>
          </svg>
        </div>
      </div>

      {/* Status and Badges */}
      <div className="px-3 pb-2">
        <div className="flex items-center justify-between mb-2">
          {getStatusBadge()}
          <ConfidenceBadge confidence={invoice.confidence} />
        </div>
        
        {/* Issues Count */}
        {invoice.issues_count && invoice.issues_count > 0 && (
          <div className="flex items-center gap-2">
            <span className="bg-[#FEF3C7] text-[#92400E] border border-[#FDE68A] rounded-[999px] px-2 py-0.5 text-[11px] font-semibold" data-ui="issues-badge">
              {invoice.issues_count} issue{invoice.issues_count !== 1 ? 's' : ''}
            </span>
          </div>
        )}

        {/* Progress Indicator */}
        {getProgressIndicator()}
      </div>

      {/* Expanded Content */}
      {isExpanded && (
        <div className="px-3 pb-3 border-t border-[#F3F4F6] mt-2 pt-3">
          {/* Parent PDF Info */}
          {invoice.parent_pdf_filename && (
            <div className="mb-3">
              <div className="text-[11px] text-[#6B7280] mb-1">From file:</div>
              <div className="text-[12px] text-[#374151] font-mono bg-[#F9FAFB] px-2 py-1 rounded-[4px]">
                {invoice.parent_pdf_filename}
              </div>
            </div>
          )}

          {/* Manual Review Required */}
          {invoice.confidence < 60 && (
            <div className="bg-[#FEF3C7] border border-[#FDE68A] rounded-[8px] p-2 mb-3">
              <div className="text-[12px] text-[#92400E] font-medium mb-1">
                Manual review recommended
              </div>
              <div className="text-[11px] text-[#92400E]">
                OCR may have split this invoice incorrectly. Please verify the boundaries.
              </div>
            </div>
          )}

          {/* Quick Actions */}
          <div className="flex gap-2">
            <button className="flex-1 bg-[#2563EB] hover:bg-[#1D4ED8] text-white rounded-[8px] px-3 py-1.5 text-[12px] font-medium transition-colors">
              Review Details
            </button>
            {invoice.status === 'error' && (
              <button className="bg-white border border-[#E5E7EB] hover:bg-[#F9FAFB] text-[#374151] rounded-[8px] px-3 py-1.5 text-[12px] font-medium transition-colors">
                Retry OCR
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default InvoiceCard; 