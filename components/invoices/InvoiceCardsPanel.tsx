import React, { useState } from 'react';
import { useDocuments } from '@/hooks/useDocuments';
import InvoiceCardAccordion from './InvoiceCardAccordion';
import InvoiceDetailDrawer from './InvoiceDetailDrawer';
import InvoiceExport from './InvoiceExport';
import { Invoice, DeliveryNote } from '@/services/api';
import { useToast } from '@/utils/toast';

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

    // ✅ Enhanced debug logging to confirm results
    console.log("=== InvoiceCardsPanel Debug Info ===", new Date().toISOString());
    console.log("Filter criteria:", { showScannedOnly, showMatchedOnly, showUnmatchedOnly });
    console.log("All scannedAwaitingMatch documents:", (safeDocuments.scannedAwaitingMatch || []).length);
    console.log("All matchedDocuments:", (safeDocuments.matchedDocuments || []).length);
    console.log("Visible documents after filtering:", visibleDocs.length);
    
    // Log status breakdown
    const statusBreakdown = (safeDocuments.scannedAwaitingMatch || []).reduce((acc, doc) => {
      acc[doc?.status || 'unknown'] = (acc[doc?.status || 'unknown'] || 0) + 1;
      return acc;
    }, {} as Record<string, number>);
    console.log("Status breakdown:", statusBreakdown);
    
    // Log scanned documents specifically
    const scannedDocs = (safeDocuments.scannedAwaitingMatch || []).filter(doc => doc?.status === 'scanned');
    console.log("Documents with 'scanned' status:", scannedDocs.length);
    if (scannedDocs.length > 0) {
      console.log("Scanned document details:", scannedDocs.map(doc => ({
        id: doc?.id || 'unknown',
        invoice_number: 'invoice_number' in doc ? doc.invoice_number : 'N/A',
        supplier_name: 'supplier_name' in doc ? doc.supplier_name : 'N/A',
        confidence: doc?.confidence || 0
      })));
    }
    console.log("=== End Debug Info ===");

    return visibleDocs;
  };

  const visibleDocuments = getVisibleDocuments();

  // Handle document click to open detail drawer
  const handleDocumentClick = (document: Invoice | DeliveryNote) => {
    if ('invoice_number' in document) {
      // It's an invoice
      setSelectedInvoice(document);
      // Find matching delivery note if any
      const matchingDeliveryNote = documents.matchedDocuments.find(doc => 
        'delivery_note_number' in doc && (doc as any).invoice?.id === document.id
      );
      setSelectedDeliveryNote(matchingDeliveryNote as DeliveryNote | null);
    } else {
      // It's a delivery note
      setSelectedDeliveryNote(document as DeliveryNote);
      // Find matching invoice if any
      const matchingInvoice = documents.matchedDocuments.find(doc => 
        'invoice_number' in doc && (doc as any).delivery_note?.id === document.id
      );
      setSelectedInvoice(matchingInvoice as Invoice | null);
    }
    setIsDetailDrawerOpen(true);
  };

  // Handle accordion expand callback
  const handleAccordionExpand = (id: string) => {
    console.log('Invoice accordion expanded:', id);
    // You can add additional logic here if needed
  };

  // Handle edit field changes
  const handleEdit = (field: string, value: any) => {
    if (selectedInvoice) {
      setSelectedInvoice(prev => prev ? { ...prev, [field]: value } : null);
      showToast('success', 'Field updated successfully');
    }
  };

  // Handle comment submission
  const handleComment = (message: string) => {
    showToast('success', 'Comment added successfully');
    // TODO: Implement comment saving to backend
  };

  // Handle credit note suggestion
  const handleCreditNote = () => {
    showToast('success', 'Credit note suggestion created');
    // TODO: Implement credit note creation
  };

  // Handle delivery note pairing
  const handlePairDeliveryNote = (deliveryNoteId: string) => {
    showToast('success', 'Delivery note paired successfully');
    // TODO: Implement delivery note pairing logic
  };

  // Handle re-OCR request
  const handleReOCR = () => {
    showToast('success', 'Re-OCR request submitted');
    // TODO: Implement re-OCR logic
  };

  // Handle export
  const handleExport = (format: 'pdf' | 'email') => {
    showToast('success', `${format.toUpperCase()} export generated`);
    setShowExportModal(false);
    // TODO: Implement export logic
  };

  if (loading) {
    return (
      <div className="bg-white rounded-lg shadow p-6">
        <div className="flex items-center justify-center py-8">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
          <span className="ml-2 text-gray-600">Loading documents...</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-white rounded-lg shadow p-6">
        <div className="text-center py-8">
          <div className="text-red-600 mb-2">Error loading documents</div>
          <button 
            onClick={refetch}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg shadow">
      {/* Header */}
      <div className="px-6 py-4 border-b border-gray-200">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-semibold text-gray-900">{title}</h2>
          <div className="flex items-center space-x-2">
            <span className="text-sm text-gray-500">
              {visibleDocuments.length} document{visibleDocuments.length !== 1 ? 's' : ''}
            </span>
            <button
              onClick={refetch}
              className="p-2 text-gray-400 hover:text-gray-600 transition-colors"
              title="Refresh"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
            </button>
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="p-6">
        {visibleDocuments.length === 0 ? (
          <div className="text-center py-8">
            <div className="text-gray-500 mb-2">No documents found</div>
            <div className="text-sm text-gray-400">
              {showScannedOnly && "No scanned documents available"}
              {showMatchedOnly && "No matched documents available"}
              {showUnmatchedOnly && "No unmatched documents available"}
              {!showScannedOnly && !showMatchedOnly && !showUnmatchedOnly && "No documents available"}
            </div>
          </div>
        ) : (
          <div className="space-y-4">
            {visibleDocuments.map((document) => {
              // Only render InvoiceCardAccordion for invoices
              if ('invoice_number' in document) {
                const invoice = document as Invoice;
                // Find matching delivery note if any
                const matchingDeliveryNote = documents.matchedDocuments.find(doc => 
                  'delivery_note_number' in doc && doc.invoice?.id === invoice.id
                ) as DeliveryNote | null;

                return (
                  <InvoiceCardAccordion
                      key={invoice.id}
                      invoice={invoice}
                      onExpand={handleAccordionExpand}
                    />
                );
              }
              // For delivery notes, we could add a separate component later
              return null;
            })}
          </div>
        )}
      </div>

      {/* Detail Drawer */}
      {selectedInvoice && (
        <InvoiceDetailDrawer
          isOpen={isDetailDrawerOpen}
          onClose={() => setIsDetailDrawerOpen(false)}
          invoice={selectedInvoice}
          deliveryNote={selectedDeliveryNote}
          onEdit={handleEdit}
          onComment={handleComment}
          onCreditNote={handleCreditNote}
          onPairDeliveryNote={handlePairDeliveryNote}
          onReOCR={handleReOCR}
        />
      )}

      {/* Export Modal */}
      {showExportModal && selectedInvoice && (
        <InvoiceExport
          invoice={selectedInvoice}
          onClose={() => setShowExportModal(false)}
        />
      )}
    </div>
  );
};

export default InvoiceCardsPanel; 