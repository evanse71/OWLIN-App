import React, { useState } from 'react';
import { useDocuments } from '@/hooks/useDocuments';
import InvoiceCard from './InvoiceCard';

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
  const [activeId, setActiveId] = useState<string | null>(null);
  const { documents, loading, error, refetch } = useDocuments();

  const handleToggle = (id: string) => {
    setActiveId(prev => (prev === id ? null : id));
  };

  const handleEditLineItem = (invoiceId: string, rowIdx: number, patch: any) => {
    // TODO: Implement line item editing wired to API
    console.log('Edit line item:', invoiceId, rowIdx, patch);
  };

  // DEV banner so we can see it's mounted
  if (typeof window !== "undefined") {
    const totalDocs = documents.recentlyUploaded.length + documents.scannedAwaitingMatch.length + documents.matchedDocuments.length + documents.failedDocuments.length;
    console.info("[InvoiceCardsPanel] mounted • count:", totalDocs, "sample:", documents.recentlyUploaded[0]);
    (window as any).__OWLIN_PANEL__ = "InvoiceCardsPanel";
    (window as any).__OWLIN_DOCS__ = totalDocs;
  }

  const getVisibleDocuments = (docs: any) => {
    let visibleDocs: any[] = [];
    
    if (showScannedOnly) {
      visibleDocs = [...docs.scannedAwaitingMatch];
    } else if (showMatchedOnly) {
      visibleDocs = [...docs.matchedDocuments];
    } else if (showUnmatchedOnly) {
      visibleDocs = [...docs.scannedAwaitingMatch];
    } else {
      // Show all documents
      visibleDocs = [
        ...docs.recentlyUploaded,
        ...docs.scannedAwaitingMatch,
        ...docs.matchedDocuments,
        ...docs.failedDocuments
      ];
    }
    
    return visibleDocs;
  };

  const docs = getVisibleDocuments(documents);

  // Convert old document format to new InvoiceCard `doc` shape
  const convertToDoc = (doc: any) => {
    const id = String(doc.id || doc.document_id || doc.invoice_id);
    return {
      id,
      supplier_name: doc.supplier_name || '',
      invoice_number: doc.invoice_number || '',
      invoice_date: doc.invoice_date || '',
      total_amount: Number(doc.total_amount || 0),
      doc_type: (doc.doc_type || 'invoice') as any,
      page_range: doc.page_range || '',
      line_items: doc.line_items || doc.items || [],
      addresses: doc.addresses || {},
      signature_regions: doc.signature_regions || [],
      field_confidence: doc.field_confidence || {},
      status: doc.status || 'processed',
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

  if (docs.length === 0) {
    return (
      <div className="text-center py-8">
        <p className="text-gray-500">No documents found</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-4">
      {docs.map((doc: any) => {
        const mapped = convertToDoc(doc);
        return (
          <InvoiceCard
            key={mapped.id}
            doc={mapped}
            isActive={activeId === mapped.id}
            onToggle={() => handleToggle(mapped.id)}
            onEditLineItem={(rowIdx, patch) => handleEditLineItem(mapped.id, rowIdx, patch)}
          />
        );
      })}
    </div>
  );
};

export default InvoiceCardsPanel; 