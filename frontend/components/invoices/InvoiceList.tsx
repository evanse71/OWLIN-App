import React, { useState, useEffect } from 'react';
import { InvoiceListItem } from '../../hooks/useInvoices';
import InvoiceCard from './InvoiceCard';

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
  // Multi-invoice support fields
  requires_manual_review?: boolean;
  parent_pdf_filename?: string;
  boundary_confidence?: number;
  retry_count?: number;
  // Add missing properties for InvoiceListItem
  confidence?: number;
  issues_count?: number;
  upload_id?: string;
  matched_delivery_note_id?: string;
}

interface InvoiceListProps {
  documents: Invoice[];
  loading?: boolean;
  error?: string | null;
  refetch?: () => void;
  onEditLineItem?: (invoiceId: string, rowIdx: number, patch: any) => void;
  onRetryOCR?: (invoiceId: string) => void;
}

interface InvoiceGroup {
  parentPdf: string;
  invoices: Invoice[];
  totalInvoices: number;
  requiresManualReview: boolean;
}

const InvoiceCardsPanel: React.FC<InvoiceListProps> = ({
  documents,
  loading = false,
  error = null,
  refetch,
  onEditLineItem,
  onRetryOCR
}) => {
  const [activeId, setActiveId] = useState<string | null>(null);
  const [groupedInvoices, setGroupedInvoices] = useState<InvoiceGroup[]>([]);

  // Group invoices by parent PDF filename
  useEffect(() => {
    const groups: { [key: string]: Invoice[] } = {};
    
    documents.forEach(doc => {
      const parentPdf = doc.parent_pdf_filename || 'Unknown Source';
      if (!groups[parentPdf]) {
        groups[parentPdf] = [];
      }
      groups[parentPdf].push(doc);
    });
    
    const grouped: InvoiceGroup[] = Object.entries(groups).map(([parentPdf, invoices]) => ({
      parentPdf,
      invoices,
      totalInvoices: invoices.length,
      requiresManualReview: invoices.some(inv => inv.requires_manual_review)
    }));
    
    setGroupedInvoices(grouped);
  }, [documents]);

  const handleToggle = (id: string) => {
    setActiveId(activeId === id ? null : id);
  };

  const handleEditLineItem = (invoiceId: string, rowIdx: number, patch: any) => {
    onEditLineItem?.(invoiceId, rowIdx, patch);
  };

  const handleRetryOCR = (invoiceId: string) => {
    onRetryOCR?.(invoiceId);
  };

  const getVisibleDocuments = (docs: Invoice[]) => {
    // For now, show all documents
    // In the future, this could filter by status, date range, etc.
    return docs;
  };

  const convertToDoc = (doc: any): InvoiceListItem => {
    const id = Number(doc.id || doc.document_id || doc.invoice_id || 0);
    return {
      id,
      supplier_name: doc.supplier_name || '',
      invoice_number: doc.invoice_number || '',
      invoice_date: doc.invoice_date || '',
      total_amount: Number(doc.total_amount || 0),
      status: doc.status || 'processed',
      confidence: doc.confidence || doc.boundary_confidence || 1.0,
      page_range: doc.page_range || '',
      parent_pdf_filename: doc.parent_pdf_filename || '',
      issues_count: doc.issues_count || 0,
      upload_id: doc.upload_id || String(doc.id || ''),
      matched_delivery_note_id: doc.matched_delivery_note_id,
    };
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-8">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-center py-8">
        <p className="text-red-600 mb-4">Error loading documents: {error}</p>
        <button
          onClick={refetch}
          className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
        >
          Retry
        </button>
      </div>
    );
  }

  if (groupedInvoices.length === 0) {
    return (
      <div className="text-center py-8">
        <p className="text-gray-500">No documents found</p>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {groupedInvoices.map((group, groupIndex) => (
        <div key={groupIndex} className="space-y-4">
          {/* Group Header */}
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <h3 className="text-lg font-semibold text-gray-900">
                {group.parentPdf}
              </h3>
              <span className="text-sm text-gray-500">
                {group.totalInvoices} invoice{group.totalInvoices !== 1 ? 's' : ''}
              </span>
              {group.requiresManualReview && (
                <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-yellow-100 text-yellow-800">
                  Manual Review Required
                </span>
              )}
            </div>
          </div>
          
          {/* Invoice Cards */}
          <div className="space-y-4">
            {group.invoices.map((doc: any) => {
              const mapped = convertToDoc(doc);
              return (
                <InvoiceCard
                  key={mapped.id}
                  invoice={mapped}
                  isExpanded={Number(activeId) === mapped.id}
                  isSelected={Number(activeId) === mapped.id}
                  onClick={() => handleToggle(String(mapped.id))}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' || e.key === ' ') {
                      e.preventDefault();
                      handleToggle(String(mapped.id));
                    }
                  }}
                  tabIndex={0}
                  aria-label={`Invoice ${mapped.invoice_number} from ${mapped.supplier_name}, ${mapped.status}`}
                />
              );
            })}
          </div>
        </div>
      ))}
    </div>
  );
};

export default InvoiceCardsPanel; 