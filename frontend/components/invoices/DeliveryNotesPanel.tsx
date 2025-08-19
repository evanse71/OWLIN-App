import React from 'react';
import { InvoiceListItem } from '../../hooks/useInvoices';

interface DeliveryNotesPanelProps {
  unmatchedDeliveryNotes: InvoiceListItem[];
  onPairDeliveryNote: (deliveryNoteId: number, invoiceId: number) => void;
  currentInvoiceId?: number;
}

const DeliveryNotesPanel: React.FC<DeliveryNotesPanelProps> = ({
  unmatchedDeliveryNotes,
  onPairDeliveryNote,
  currentInvoiceId
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

  if (unmatchedDeliveryNotes.length === 0) {
    return (
      <div className="bg-[#F9FAFB] rounded-[12px] border border-[#E5E7EB] p-4">
        <h3 className="text-[14px] font-semibold text-[#1F2937] mb-2">Unmatched Delivery Notes</h3>
        <div className="text-[13px] text-[#6B7280] text-center py-4">
          No unmatched delivery notes at this time.
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-[12px] border border-[#E5E7EB] p-4">
      <h3 className="text-[14px] font-semibold text-[#1F2937] mb-3">
        Unmatched Delivery Notes ({unmatchedDeliveryNotes.length})
      </h3>
      
      <div className="space-y-2 max-h-64 overflow-y-auto">
        {unmatchedDeliveryNotes.map((note) => (
          <div
            key={note.id}
            className={`p-3 rounded-[8px] border border-[#E5E7EB] cursor-pointer transition-colors ${
              currentInvoiceId ? 'hover:border-[#2563EB] hover:bg-[#EFF6FF]' : ''
            }`}
            onClick={() => currentInvoiceId && onPairDeliveryNote(note.id, currentInvoiceId)}
            role="button"
            tabIndex={0}
            aria-label={`Pair delivery note ${note.invoice_number} with current invoice`}
          >
            <div className="flex items-start justify-between mb-2">
              <div className="flex-1 min-w-0">
                <div className="text-[13px] font-medium text-[#1F2937] truncate">
                  {note.supplier_name}
                </div>
                <div className="text-[11px] text-[#6B7280]">
                  DN #{note.invoice_number} • {formatDate(note.invoice_date)}
                </div>
              </div>
              <div className="text-right ml-2">
                <div className="text-[13px] font-semibold text-[#111827]">
                  {formatCurrency(note.total_amount)}
                </div>
                <div className="text-[11px] text-[#6B7280]">
                  {note.confidence}% confidence
                </div>
              </div>
            </div>
            
            {currentInvoiceId && (
              <div className="text-[11px] text-[#2563EB] font-medium">
                Click to pair with current invoice
              </div>
            )}
          </div>
        ))}
      </div>
      
      {currentInvoiceId && (
        <div className="mt-3 pt-3 border-t border-[#E5E7EB]">
          <p className="text-[11px] text-[#6B7280] text-center">
            Click a delivery note above to pair it with the selected invoice
          </p>
        </div>
      )}
    </div>
  );
};

export default DeliveryNotesPanel; 