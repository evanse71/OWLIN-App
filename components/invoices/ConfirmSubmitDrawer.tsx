import React from 'react';

interface Invoice {
  id: string;
  supplier_name: string;
  invoice_number: string;
  invoice_date: string;
  total_amount: number;
  doc_type: "invoice" | "delivery_note" | "receipt" | "utility" | "other";
  page_range: string;
  line_items: any[];
  addresses: { supplier_address?: string; delivery_address?: string };
  signature_regions: any[];
  field_confidence: Record<string, number>;
  status: "processing" | "processed" | "reviewed";
  progress?: { processed_pages: number; total_pages: number };
  flags?: { total_mismatch?: boolean; [key: string]: any };
}

interface ConfirmSubmitDrawerProps {
  open: boolean;
  onClose: () => void;
  docs: Invoice[];
  onSubmit: () => void;
}

export default function ConfirmSubmitDrawer({
  open,
  onClose,
  docs,
  onSubmit
}: ConfirmSubmitDrawerProps) {
  if (!open) return null;

  const processedInvoices = docs.filter(d => d.status === "processed" && d.doc_type === "invoice");
  const hasBlockingIssues = processedInvoices.some(d => d.flags?.total_mismatch);

  const handleSubmit = () => {
    onSubmit();
    onClose();
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Escape') {
      onClose();
    }
  };

  return (
    <div
      className="drawer-overlay fixed inset-0 z-50 flex justify-end"
      onClick={onClose}
      onKeyDown={handleKeyDown}
      tabIndex={-1}
    >
      <div
        className="drawer-panel bg-white shadow-xl flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-[#E7EAF0]">
          <h2 className="text-lg font-semibold text-[#2B2F36]">
            Confirm Submission
          </h2>
          <button
            onClick={onClose}
            className="text-[#5B6470] hover:text-[#2B2F36] transition-colors"
            aria-label="Close confirmation drawer"
          >
            ×
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {/* Summary */}
          <div className="space-y-2">
            <h3 className="text-[15px] font-medium text-[#2B2F36]">
              Submitting {processedInvoices.length} invoices
            </h3>
            <p className="text-[13px] text-[#5B6470]">
              These documents will be processed and added to your Owlin system.
            </p>
          </div>

          {/* Invoice List */}
          <div className="space-y-3">
            <h4 className="text-[13px] font-medium text-[#5B6470] uppercase tracking-wide">
              Invoices to Submit
            </h4>
            <div className="space-y-2 max-h-64 overflow-y-auto">
              {processedInvoices.map((invoice) => (
                <div
                  key={invoice.id}
                  className="flex items-center justify-between p-3 rounded-lg border border-[#E7EAF0] bg-[#F8FAFC]"
                >
                  <div className="flex-1 min-w-0">
                    <div className="text-[13px] font-medium text-[#2B2F36] truncate">
                      {invoice.supplier_name || 'Unknown Supplier'}
                    </div>
                    <div className="text-[12px] text-[#5B6470]">
                      {invoice.invoice_number} • {invoice.invoice_date}
                    </div>
                  </div>
                  <div className="text-[13px] font-semibold text-[#2B2F36] tabular">
                    £{invoice.total_amount.toFixed(2)}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Blocking Issues */}
          {hasBlockingIssues && (
            <div className="space-y-2">
              <h4 className="text-[13px] font-medium text-[#DC2626] uppercase tracking-wide">
                ⚠️ Blocking Issues
              </h4>
              <div className="p-3 rounded-lg border border-[#FECACA] bg-[#FEF2F2]">
                <div className="text-[13px] text-[#DC2626]">
                  Some invoices have total amount mismatches that need to be resolved before submission.
                </div>
              </div>
            </div>
          )}

          {/* Non-invoice Documents */}
          {docs.filter(d => d.doc_type !== "invoice").length > 0 && (
            <div className="space-y-2">
              <h4 className="text-[13px] font-medium text-[#5B6470] uppercase tracking-wide">
                Other Documents
              </h4>
              <div className="text-[13px] text-[#5B6470]">
                {docs.filter(d => d.doc_type === "delivery_note").length} delivery notes will move to Deliveries
                {docs.filter(d => d.doc_type === "receipt").length > 0 && (
                  <span>, {docs.filter(d => d.doc_type === "receipt").length} receipts will move to Receipts</span>
                )}
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="p-6 border-t border-[#E7EAF0] space-y-3">
          <button
            onClick={handleSubmit}
            disabled={hasBlockingIssues}
            className={`w-full rounded-[10px] px-4 py-2.5 text-[13px] font-medium transition-colors ${
              hasBlockingIssues
                ? "bg-[#F3F4F6] text-[#9CA3AF] cursor-not-allowed"
                : "bg-[#10B981] text-white hover:bg-[#059669]"
            }`}
          >
            Send Now
          </button>
          <button
            onClick={onClose}
            className="w-full rounded-[10px] border border-[#E7EAF0] px-4 py-2.5 text-[13px] text-[#5B6470] hover:bg-[#F6F8FB] transition-colors"
          >
            Cancel
          </button>
        </div>
      </div>
    </div>
  );
}; 