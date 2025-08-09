import React, { useState } from 'react';
import { useDocuments } from '@/hooks/useDocuments';
import InvoiceCard from './InvoiceCard';
import InvoiceDetailDrawer from './InvoiceDetailDrawer';
import InvoiceExport from './InvoiceExport';
import { Invoice, DeliveryNote } from '@/services/api';
import { useToast } from '@/utils/toast';
import { apiService } from '@/services/api';

interface InvoiceCardsPanelProps {
  title?: string;
  showScannedOnly?: boolean;
  showMatchedOnly?: boolean;
  showUnmatchedOnly?: boolean;
}

const InvoiceCardsPanel: React.FC<InvoiceCardsPanelProps> = ({
  title = "Invoice Documents",
  showScannedOnly = false,
  showMatchedOnly = false,
  showUnmatchedOnly = false,
}) => {
  const { documents, loading, error, refetch } = useDocuments();
  const { showToast } = useToast();
  
  // State for detail drawer
  const [selectedInvoice, setSelectedInvoice] = useState<Invoice | null>(null);
  const [selectedDeliveryNote, setSelectedDeliveryNote] = useState<DeliveryNote | null>(null);
  const [isDetailDrawerOpen, setIsDetailDrawerOpen] = useState(false);
  
  // State for export modal
  const [showExportModal, setShowExportModal] = useState(false);

  // ✅ Update the document filter to include scanned invoices
  const getVisibleDocuments = () => {
    let visibleDocs: (Invoice | DeliveryNote)[] = [];

    // ✅ Add safe fallbacks for documents
    const safeDocuments = documents || {
      scannedAwaitingMatch: [],
      matchedDocuments: [],
      recentlyUploaded: [],
      failedDocuments: []
    };

    if (showScannedOnly) {
      // Show only scanned documents
      visibleDocs = (safeDocuments.scannedAwaitingMatch || []).filter(doc => 
        doc?.status === 'scanned'
      );
    } else if (showMatchedOnly) {
      // Show only matched documents
      visibleDocs = safeDocuments.matchedDocuments || [];
    } else if (showUnmatchedOnly) {
      // Show only unmatched documents
      visibleDocs = (safeDocuments.scannedAwaitingMatch || []).filter(doc => 
        doc?.status === 'unmatched'
      );
    } else {
      // Show all scanned awaiting match documents (includes scanned, unmatched, waiting, utility)
      visibleDocs = safeDocuments.scannedAwaitingMatch || [];
    }

    return visibleDocs;
  };

  const docs = (typeof getVisibleDocuments === "function")
    ? getVisibleDocuments()
    : (documents ?? []);
  if (!Array.isArray(docs)) return null;

  // DEV banner so we can see it's mounted
  if (typeof window !== "undefined") {
    console.info("[InvoiceCardsPanel] mounted • count:", docs.length, "sample:", docs[0]);
    (window as any).__OWLIN_PANEL__ = "InvoiceCardsPanel";
    (window as any).__OWLIN_DOCS__ = docs.length;
  }

  // Handle document click to open detail drawer
  const handleDocumentClick = (document: Invoice | DeliveryNote) => {
    if ('invoice_number' in document) {
      // It's an invoice
      setSelectedInvoice(document);
      // Find matching delivery note if any
      const matchingDeliveryNote = documents?.matchedDocuments?.find(doc => 
        'delivery_number' in doc && doc.invoice?.id === document.id
      ) as DeliveryNote | undefined;
      setSelectedDeliveryNote(matchingDeliveryNote || null);
    } else {
      // It's a delivery note
      setSelectedDeliveryNote(document);
      setSelectedInvoice(null);
    }
    setIsDetailDrawerOpen(true);
  };

  const handleSave = (invoiceId: string, data: any) => {
    // Handle save logic here
    showToast('success', 'Invoice updated successfully');
  };

  const handleMarkReviewed = (invoiceId: string) => {
    // Handle mark reviewed logic here
    showToast('success', 'Invoice marked as reviewed');
  };

  const handleFlagIssues = (invoiceId: string) => {
    // Handle flag issues logic here
    showToast('warning', 'Issues flagged for review');
  };

  const handleSplitMerge = (invoiceId: string) => {
    // Handle split/merge logic here
    showToast('info', 'Split/merge functionality coming soon');
  };

  const handleOpenPDF = (invoiceId: string) => {
    // Handle open PDF logic here
    showToast('info', 'Opening PDF...');
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-center py-8">
        <p className="text-red-600">Error loading documents: {error}</p>
        <button 
          onClick={() => refetch()} 
          className="mt-4 px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
        >
          Retry
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold text-gray-900">{title}</h2>
        <div className="flex items-center space-x-2">
          <button
            onClick={() => setShowExportModal(true)}
            className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors"
          >
            Export
          </button>

        </div>
      </div>

      {/* Document Cards Grid */}
      {docs.length === 0 ? (
        <div className="text-center py-12">
          <div className="text-gray-400 mb-4">
            <svg className="mx-auto h-12 w-12" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
          </div>
          <h3 className="text-lg font-medium text-gray-900 mb-2">No documents found</h3>
          <p className="text-gray-500">Upload some documents to get started.</p>
        </div>
      ) : (
        <div className="flex flex-col gap-4">
          {docs.map((doc: any) => (
            <InvoiceCard
              key={doc.id || doc.document_id || doc.invoice_id}
              docId={doc.id || doc.document_id || doc.invoice_id}
              supplier={doc.supplier_name ?? ""}
              invoiceNumber={doc.invoice_number ?? ""}
              date={doc.invoice_date ?? ""}
              total={Number(doc.total_amount ?? 0)}
              docType={doc.doc_type ?? "invoice"}
              pageRange={doc.page_range ?? ""}
              fieldConfidence={doc.field_confidence ?? {}}
              status={doc.status ?? "processed"}
              addresses={doc.addresses ?? { supplier_address: "", delivery_address: "" }}
              signatureRegions={doc.signature_regions ?? []}
              lineItems={doc.line_items ?? doc.items ?? []}
              onEditLineItem={(row: number, patch: any) =>
                apiService.patchLineItem((doc.id||doc.document_id||doc.invoice_id), row, patch)
              }
              onToggleFlag={(payload: any) =>
                apiService.patchInvoiceFlags((doc.id||doc.document_id||doc.invoice_id), payload)
              }
              onMarkReviewed={() =>
                apiService.patchVerificationStatus((doc.id||doc.document_id||doc.invoice_id), "reviewed")
              }
            />
          ))}
        </div>
      )}

      {/* Detail Drawer */}
      {isDetailDrawerOpen && (selectedInvoice || selectedDeliveryNote) && (
        <InvoiceDetailDrawer
          isOpen={isDetailDrawerOpen}
          onClose={() => setIsDetailDrawerOpen(false)}
          invoice={selectedInvoice}
          deliveryNote={selectedDeliveryNote}
        />
      )}

      {/* Export Modal */}
      {showExportModal && (
        <InvoiceExport
          invoice={docs.find((doc: any) => 'invoice_number' in doc) as Invoice || {} as Invoice}
          deliveryNote={docs.find((doc: any) => 'delivery_number' in doc) as DeliveryNote || null}
          onClose={() => setShowExportModal(false)}
        />
      )}
    </div>
  );
};

export default InvoiceCardsPanel; 