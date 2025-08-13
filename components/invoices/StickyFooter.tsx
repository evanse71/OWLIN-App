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

interface StickyFooterProps {
  docs: Invoice[];
  unseenChanges: boolean;
  onClearAll: () => void;
  onSubmit: () => void;
}

export default function StickyFooter({
  docs,
  unseenChanges,
  onClearAll,
  onSubmit
}: StickyFooterProps) {
  const processed = docs.filter(d => d.status === "processed" && d.doc_type === "invoice");
  const hasBlocking = processed.some(d => d.flags?.total_mismatch);
  const ready = processed.length > 0 && !hasBlocking;

  return (
    <div className="fixed bottom-0 left-0 right-0 z-[var(--z-sticky)] bg-gradient-to-t from-[var(--owlin-bg)] to-transparent pt-6 pb-3">
      <div className="max-w-[1280px] mx-auto px-6 lg:px-8">
        <div className="rounded-[var(--owlin-radius)] bg-[var(--owlin-card)] border border-[var(--owlin-stroke)] shadow-[var(--owlin-shadow)] px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <button
              onClick={onClearAll}
              className="min-h-[40px] rounded-[12px] px-4 border border-[var(--owlin-stroke)] text-[var(--owlin-cerulean)] bg-transparent hover:bg-[#F9FAFF] transition duration-[var(--dur-fast)]"
            >
              Clear All
            </button>
            {unseenChanges && (
              <span className="text-[13px] text-[var(--owlin-muted)]">• Unsaved changes</span>
            )}
          </div>
          <button
            onClick={ready ? onSubmit : undefined}
            disabled={!ready}
            className={`min-h-[40px] rounded-[12px] px-4 text-white transition duration-[var(--dur-fast)] ${
              ready
                ? `${unseenChanges ? 'animate-[softPulse_var(--dur-slow)_ease-in-out_infinite]' : ''} bg-[var(--owlin-sapphire)] hover:brightness-110`
                : 'bg-[var(--owlin-stroke)] text-[var(--owlin-muted)] opacity-60 cursor-not-allowed'
            }`}
            aria-live="polite"
          >
            Submit to Owlin
          </button>
        </div>
      </div>
    </div>
  );
} 