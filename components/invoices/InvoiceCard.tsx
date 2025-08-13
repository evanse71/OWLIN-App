import React, { useState } from 'react';
import LineItemsTable from './LineItemsTable';
import SignatureStrip from './SignatureStrip';
import ProgressDial from './ProgressDial';
import { computeOverallConfidence } from './confidence';

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
  _localFile?: File;
  _appearIndex?: number;
}

interface InvoiceCardProps {
  doc: Invoice;
  isActive: boolean;
  onToggle: () => void;
  onEditLineItem?: (rowIdx: number, patch: any) => void;
}

export default function InvoiceCard({
  doc,
  isActive,
  onToggle,
  onEditLineItem
}: InvoiceCardProps) {
  const [editMode, setEditMode] = useState(false);
  const docId = doc.id;

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      onToggle();
    } else if (e.key === 'e' && isActive) {
      e.preventDefault();
      setEditMode(!editMode);
    } else if (e.key === 'Escape' && isActive && editMode) {
      setEditMode(false);
    }
  };

  const isProcessing = doc.status === "processing";
  const isUnknownSupplier = !doc.supplier_name || doc.supplier_name === "Unknown";
  const showRoutingNotice = doc.doc_type !== "invoice";

  const getRoutingMessage = () => {
    switch (doc.doc_type) {
      case "delivery_note": return "Will move to Deliveries after submission";
      case "receipt": return "Will move to Receipts after submission";
      case "utility": return "Will move to Utilities after submission";
      default: return "Will move to Other Documents after submission";
    }
  };

  const renderProgressIndicator = () => {
    return (
      <div className="absolute bottom-3 right-3">
        <ProgressDial
          progress={doc.progress ?? null}
          status={doc.status === "processing" ? "processing" : "processed"}
          size={28}
        />
      </div>
    );
  };

  return (
    <div
      id={`card-${docId}`}
      className="relative grid grid-cols-1 lg:grid-cols-[minmax(320px,420px)_1fr] rounded-[var(--owlin-radius)] bg-[var(--owlin-card)] border border-[var(--owlin-stroke)] shadow-[var(--owlin-shadow)] hover:shadow-[var(--owlin-shadow-lg)] hover:-translate-y-[1px] transition-[box-shadow,transform] duration-[var(--dur-fast)] ease-[var(--ease-out)]"
      data-invoice-id={doc.id}
    >
      {/* Summary (LEFT column) */}
      <div className="p-4 lg:p-5 relative">
        <div
          role="button"
          tabIndex={0}
          aria-expanded={isActive}
          onClick={onToggle}
          onKeyDown={handleKeyDown}
          className="text-left outline-none focus:ring-2 focus:ring-[var(--owlin-sapphire)] focus:ring-offset-2 focus:ring-offset-[var(--owlin-card)] rounded-[var(--owlin-radius)]"
        >
          {/* Top line - filename */}
          <div className="text-[12px] text-[var(--owlin-muted)] truncate mb-1">
            {doc._localFile ? doc._localFile.name : (doc as any).original_filename || doc.invoice_number || `Invoice ${doc.id}`}
          </div>

          {/* Main line - supplier, date, caret */}
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center flex-1 min-w-0 gap-2">
              <span className={`text-[16px] font-semibold ${isUnknownSupplier ? 'text-[var(--owlin-muted)]' : 'text-[var(--owlin-text)]'}`}>
                {doc.supplier_name || 'Unknown Supplier'}
              </span>
              <span className="text-[13px] text-[var(--owlin-muted)] truncate">
                {doc.invoice_date}
              </span>
            </div>
            <svg
              className={`w-4 h-4 text-[var(--owlin-muted)] transition-transform duration-[var(--dur-fast)] ${isActive ? 'rotate-90' : 'rotate-0'}`}
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
              aria-hidden="true"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
            </svg>
          </div>

          {/* Chips row */}
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="h-[22px] rounded-full px-2 bg-[#F1F5FF] text-[var(--owlin-cerulean)] text-[12px] font-semibold inline-flex items-center">
                {doc.doc_type.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())}
              </span>
              {doc.page_range && (
                <span className="h-[22px] rounded-full px-2 bg-[var(--owlin-bg)] text-[var(--owlin-muted)] text-[12px] inline-flex items-center">
                  Pages {doc.page_range}
                </span>
              )}
              <span className="h-[22px] rounded-full px-2 bg-[var(--owlin-bg)] text-[12px] inline-flex items-center gap-1">
                <span className="text-[var(--owlin-muted)]">Total:</span>
                <span className="tabular font-semibold text-[var(--owlin-text)]">{isProcessing ? '—' : `£${doc.total_amount.toFixed(2)}`}</span>
              </span>
            </div>

            {/* right-aligned chip group */}
            <div className="ml-auto flex items-center gap-2">
              {!isProcessing && (() => {
                const { overall: ocrScore, weakest } = computeOverallConfidence(doc.field_confidence || {}, doc.line_items || []);
                const ocrPct = Math.round((ocrScore || 0) * 100);
                const tone = ocrScore >= 0.85
                  ? 'bg-[color-mix(in_oklab,var(--owlin-success)_20%,white)] text-[var(--owlin-rich-black)]'
                  : ocrScore >= 0.70
                    ? 'bg-[color-mix(in_oklab,var(--owlin-warning)_25%,white)] text-[var(--owlin-rich-black)]'
                    : 'bg-[var(--owlin-stroke)] text-[var(--owlin-muted)]';
                return (
                  <span
                    className={`h-[22px] rounded-full px-2 text-[12px] font-semibold inline-flex items-center ${tone}`}
                    title={`OCR confidence • ${ocrPct}%\n${weakest.length ? 'Low signals: ' + weakest.join(', ') : ''}`}
                  >
                    OCR {ocrPct}%
                  </span>
                );
              })()}
              <span className={`h-[22px] rounded-full px-2 text-[12px] inline-flex items-center ${isProcessing ? 'bg-[var(--owlin-stroke)] text-[var(--owlin-muted)]' : 'bg-[color-mix(in_oklab,var(--owlin-success)_18%,white)] text-[var(--owlin-rich-black)]'}`}>
                {isProcessing ? 'Processing' : 'Processed'}
              </span>
            </div>
          </div>

          {/* Routing notice */}
          {showRoutingNotice && (
            <div className="text-[12px] text-[var(--owlin-muted)] mt-2">
              {getRoutingMessage()}
            </div>
          )}
        </div>
      </div>

      {/* Details pane (RIGHT column) */}
      <div className={`overflow-hidden transition-[max-height,opacity] duration-[var(--dur-med)] ease-[var(--ease-out)] ${isActive ? 'opacity-100 max-h-[2000px]' : 'opacity-0 max-h-0'}`}>
        <div className="p-4 lg:p-5 space-y-4 border-t lg:border-t-0 lg:border-l border-[var(--owlin-stroke)]">
          {/* Action bar */}
          <div className="flex items-center justify-end gap-2">
            <button
              onClick={() => setEditMode(!editMode)}
              className="min-h-[40px] rounded-[12px] px-3 bg-[var(--owlin-sapphire)] text-white hover:brightness-110 transition duration-[var(--dur-fast)]"
            >
              {editMode ? 'Done' : 'Edit'}
            </button>
            <button className="min-h-[40px] rounded-[12px] px-3 border border-[var(--owlin-stroke)] text-[var(--owlin-cerulean)] bg-transparent hover:bg-[#F9FAFF] transition duration-[var(--dur-fast)]">
              Open PDF
            </button>
            <button className="min-h-[40px] rounded-[12px] px-3 border border-[var(--owlin-stroke)] text-[var(--owlin-cerulean)] bg-transparent hover:bg-[#F9FAFF] transition duration-[var(--dur-fast)]">
              Split/Merge
            </button>
            <button className="min-h-[40px] rounded-[12px] px-3 border border-[var(--owlin-stroke)] text-[var(--owlin-cerulean)] bg-transparent hover:bg-[#F9FAFF] transition duration-[var(--dur-fast)]">
              ✓ Mark reviewed
            </button>
          </div>

          {/* Addresses */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <div className="text-[12px] text-[var(--owlin-muted)] mb-1">Deliver to</div>
              <div className="text-[13px] text-[var(--owlin-text)] whitespace-pre-wrap line-clamp-3">
                {doc.addresses.delivery_address || 'Not specified'}
              </div>
            </div>
            <div>
              <div className="text-[12px] text-[var(--owlin-muted)] mb-1">Supplier address</div>
              <div className="text-[13px] text-[var(--owlin-text)] whitespace-pre-wrap line-clamp-3">
                {doc.addresses.supplier_address || 'Not specified'}
              </div>
            </div>
          </div>

          {/* Line items */}
          <LineItemsTable
            lineItems={doc.line_items}
            editable={editMode}
            onEditLineItem={onEditLineItem}
          />

          {/* Signature strip */}
          <SignatureStrip regions={doc.signature_regions} />
        </div>
      </div>

      {/* Progress indicator */}
      {renderProgressIndicator()}
    </div>
  );
}; 