import React from 'react';
import { InvoiceListItem } from '../../hooks/useInvoices';
import InvoiceCard from './InvoiceCard';

interface InvoiceCardsPanelProps {
  invoices: InvoiceListItem[];
  expandedId: number | null;
  onCardClick: (id: number) => void;
  onCardKeyDown: (e: React.KeyboardEvent, id: number) => void;
}

const InvoiceCardsPanel: React.FC<InvoiceCardsPanelProps> = ({
  invoices,
  expandedId,
  onCardClick,
  onCardKeyDown
}) => {
  if (invoices.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-64 text-center">
        <div className="w-16 h-16 mb-4 text-[#9CA3AF]">
          <svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M16 8H48C50.2091 8 52 9.79086 52 12V52C52 54.2091 50.2091 56 48 56H16C13.7909 56 12 54.2091 12 52V12C12 9.79086 13.7909 8 16 8Z" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
            <path d="M20 20H44" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
            <path d="M20 28H44" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
            <path d="M20 36H36" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
            <path d="M20 44H32" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
        </div>
        <h3 className="text-[16px] font-medium text-[#374151] mb-2">Upload invoices to begin auditing</h3>
        <p className="text-[14px] text-[#6B7280] mb-4">Drop PDF files here or click to browse</p>
        <button className="bg-[#2563EB] hover:bg-[#1D4ED8] text-white rounded-[8px] px-4 py-2 text-[14px] font-medium transition-colors">
          Upload Documents
        </button>
      </div>
    );
  }

  return (
    <div 
      className="sticky top-[72px] max-h-[calc(100vh-96px)] overflow-y-auto pr-2"
      role="navigation"
      aria-label="Invoice list"
      data-ui="invoice-cards"
    >
      <div className="space-y-3">
        {invoices.map((invoice, index) => (
          <InvoiceCard
            key={invoice.id}
            invoice={invoice}
            isExpanded={expandedId === invoice.id}
            isSelected={expandedId === invoice.id}
            onClick={() => onCardClick(invoice.id)}
            onKeyDown={(e) => onCardKeyDown(e, invoice.id)}
            tabIndex={0}
            aria-label={`Invoice ${invoice.invoice_number} from ${invoice.supplier_name}, ${invoice.status}`}
          />
        ))}
      </div>
    </div>
  );
};

export default InvoiceCardsPanel; 