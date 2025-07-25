import React, { useState } from 'react';

interface SuggestedDocument {
  id: string;
  type: 'invoice' | 'delivery_note' | 'receipt' | 'utility' | 'unknown';
  confidence: number;
  supplier_name: string;
  pages: number[];
  preview_urls: string[];
  metadata: {
    invoice_date?: string;
    delivery_date?: string;
    total_amount?: number;
    invoice_number?: string;
    delivery_note_number?: string;
  };
}

interface SmartDocumentReviewModalProps {
  isOpen: boolean;
  onClose: () => void;
  suggestedDocuments: SuggestedDocument[];
  onConfirm: (documents: SuggestedDocument[]) => Promise<void>;
  fileName: string;
}

const SmartDocumentReviewModal: React.FC<SmartDocumentReviewModalProps> = ({
  isOpen,
  onClose,
  suggestedDocuments,
  onConfirm,
  fileName
}) => {
  const [documents, setDocuments] = useState<SuggestedDocument[]>(suggestedDocuments);
  const [isSubmitting, setIsSubmitting] = useState(false);

  if (!isOpen) return null;

  const handleDocumentTypeChange = (documentId: string, newType: SuggestedDocument['type']) => {
    setDocuments(prev => prev.map(doc => 
      doc.id === documentId ? { ...doc, type: newType } : doc
    ));
  };

  const handleSupplierChange = (documentId: string, newSupplier: string) => {
    setDocuments(prev => prev.map(doc => 
      doc.id === documentId ? { ...doc, supplier_name: newSupplier } : doc
    ));
  };

  const handleRemoveDocument = (documentId: string) => {
    setDocuments(prev => prev.filter(doc => doc.id !== documentId));
  };

  const handleConfirm = async () => {
    setIsSubmitting(true);
    try {
      await onConfirm(documents);
    } catch (error) {
      console.error('Failed to confirm documents:', error);
    } finally {
      setIsSubmitting(false);
    }
  };

  const getDocumentTypeIcon = (type: string) => {
    switch (type) {
      case 'invoice': return '📄';
      case 'delivery_note': return '📦';
      case 'receipt': return '🧾';
      case 'utility': return '⚡';
      default: return '❓';
    }
  };

  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 90) return 'text-green-600 dark:text-green-400';
    if (confidence >= 70) return 'text-yellow-600 dark:text-yellow-400';
    return 'text-red-600 dark:text-red-400';
  };

  const getConfidenceBadge = (confidence: number) => {
    if (confidence >= 90) return 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-200';
    if (confidence >= 70) return 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-200';
    return 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-200';
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
      <div className="bg-white dark:bg-gray-800 rounded-lg max-w-4xl w-full max-h-[90vh] overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200 dark:border-gray-700">
          <div>
            <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100">
              Review Document Splits
            </h2>
            <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
              {fileName} • {suggestedDocuments.length} suggested document(s)
            </p>
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Content */}
        <div className="p-6 overflow-y-auto max-h-[calc(90vh-140px)]">
          <div className="space-y-4">
            {documents.map((document, index) => (
              <div
                key={document.id}
                className="bg-gray-50 dark:bg-gray-700 rounded-lg p-4 border border-gray-200 dark:border-gray-600"
              >
                {/* Document Header */}
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center space-x-3">
                    <span className="text-2xl">{getDocumentTypeIcon(document.type)}</span>
                    <div>
                      <h3 className="font-medium text-gray-900 dark:text-gray-100">
                        Document {index + 1}
                      </h3>
                      <p className="text-sm text-gray-600 dark:text-gray-400">
                        Pages {document.pages.join(', ')}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center space-x-2">
                    <span className={`px-2 py-1 rounded-full text-xs font-medium ${getConfidenceBadge(document.confidence)}`}>
                      {document.confidence}% confident
                    </span>
                    <button
                      onClick={() => handleRemoveDocument(document.id)}
                      className="text-red-500 hover:text-red-700 dark:hover:text-red-400"
                    >
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                      </svg>
                    </button>
                  </div>
                </div>

                {/* Document Details */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {/* Document Type */}
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                      Document Type
                    </label>
                    <select
                      value={document.type}
                      onChange={(e) => handleDocumentTypeChange(document.id, e.target.value as any)}
                      className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500"
                    >
                      <option value="invoice">📄 Invoice</option>
                      <option value="delivery_note">📦 Delivery Note</option>
                      <option value="receipt">🧾 Receipt</option>
                      <option value="utility">⚡ Utility Bill</option>
                      <option value="unknown">❓ Unknown</option>
                    </select>
                  </div>

                  {/* Supplier Name */}
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                      Supplier Name
                    </label>
                    <input
                      type="text"
                      value={document.supplier_name}
                      onChange={(e) => handleSupplierChange(document.id, e.target.value)}
                      className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500"
                      placeholder="Enter supplier name"
                    />
                  </div>
                </div>

                {/* Metadata Display */}
                {document.metadata && Object.keys(document.metadata).length > 0 && (
                  <div className="mt-3 p-3 bg-blue-50 dark:bg-blue-900/20 rounded-md">
                    <h4 className="text-sm font-medium text-blue-900 dark:text-blue-100 mb-2">
                      Detected Information
                    </h4>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-xs">
                      {document.metadata.invoice_date && (
                        <div>
                          <span className="text-blue-700 dark:text-blue-300">Date:</span>
                          <span className="ml-1 text-gray-700 dark:text-gray-300">{document.metadata.invoice_date}</span>
                        </div>
                      )}
                      {document.metadata.total_amount && (
                        <div>
                          <span className="text-blue-700 dark:text-blue-300">Amount:</span>
                          <span className="ml-1 text-gray-700 dark:text-gray-300">£{document.metadata.total_amount}</span>
                        </div>
                      )}
                      {document.metadata.invoice_number && (
                        <div>
                          <span className="text-blue-700 dark:text-blue-300">Invoice #:</span>
                          <span className="ml-1 text-gray-700 dark:text-gray-300">{document.metadata.invoice_number}</span>
                        </div>
                      )}
                      {document.metadata.delivery_note_number && (
                        <div>
                          <span className="text-blue-700 dark:text-blue-300">DN #:</span>
                          <span className="ml-1 text-gray-700 dark:text-gray-300">{document.metadata.delivery_note_number}</span>
                        </div>
                      )}
                    </div>
                  </div>
                )}

                {/* Page Previews */}
                <div className="mt-3">
                  <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    Page Previews
                  </h4>
                  <div className="flex space-x-2 overflow-x-auto">
                    {document.preview_urls.map((url, pageIndex) => (
                      <div key={pageIndex} className="flex-shrink-0">
                        <img
                          src={url}
                          alt={`Page ${document.pages[pageIndex]}`}
                          className="w-16 h-20 object-cover border border-gray-300 dark:border-gray-600 rounded"
                        />
                        <p className="text-xs text-center text-gray-500 dark:text-gray-400 mt-1">
                          Page {document.pages[pageIndex]}
                        </p>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            ))}
          </div>

          {documents.length === 0 && (
            <div className="text-center py-8">
              <div className="text-gray-400 dark:text-gray-500 text-4xl mb-4">📋</div>
              <p className="text-gray-600 dark:text-gray-400">
                No documents to review. All documents have been removed.
              </p>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between p-6 border-t border-gray-200 dark:border-gray-700">
          <div className="text-sm text-gray-600 dark:text-gray-400">
            {documents.length} document(s) ready for submission
          </div>
          <div className="flex space-x-3">
            <button
              onClick={onClose}
              className="px-4 py-2 text-gray-700 dark:text-gray-300 hover:text-gray-900 dark:hover:text-gray-100 transition-colors"
            >
              Cancel
            </button>
            <button
              onClick={handleConfirm}
              disabled={isSubmitting || documents.length === 0}
              className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {isSubmitting ? 'Confirming...' : `Confirm ${documents.length} Document(s)`}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default SmartDocumentReviewModal; 