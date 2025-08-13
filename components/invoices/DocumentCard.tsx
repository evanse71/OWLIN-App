import React, { useState } from 'react';
import { FileStatus, Invoice, DeliveryNote } from '@/services/api';
import ConfidenceBadge from '@/components/common/ConfidenceBadge';
import SupplierInsights from './SupplierInsights';
import DeliveryNotePairing from './DeliveryNotePairing';

// Local Document type from InvoicesUploadPanel
interface LocalDocument {
  id: string;
  filename: string;
  supplier: string;
  invoiceNumber: string;
  invoiceDate: string;
  totalAmount: string;
  type: 'Invoice' | 'Delivery Note' | 'Unknown';
  status: 'Processing' | 'Complete' | 'Error' | 'Matched' | 'Unmatched' | 'Unknown' | 'Scanned';
  confidence?: number;
  numIssues?: number;
  parsedData?: any;
  matchedDocument?: any;
  loadingPercent?: number;
  multipleInvoices?: boolean;
  invoiceCount?: number;
  delivery_note_required?: boolean;
}

interface DocumentCardProps {
  document: FileStatus | Invoice | DeliveryNote | LocalDocument;
  onClick?: () => void;
  onRetry?: () => void;
  onCancel?: () => void;
  onEdit?: (field: string, value: any) => void;
  onComment?: (message: string) => void;
  onCreditNote?: () => void;
  onPairDeliveryNote?: (deliveryNoteId: string) => void;
  onReOCR?: () => void;
  // Utility invoice props
  isUtilityInvoice?: boolean;
  deliveryNoteRequired?: boolean;
  multipleInvoices?: boolean;
  invoiceCount?: number;
}

const DocumentCard: React.FC<DocumentCardProps> = ({ 
  document, 
  onClick, 
  onRetry, 
  onCancel,
  onEdit,
  onComment,
  onCreditNote,
  onPairDeliveryNote,
  onReOCR,
  isUtilityInvoice = false,
  deliveryNoteRequired = true,
  multipleInvoices = false,
  invoiceCount = 1,
}) => {
  const [showSupplierInsights, setShowSupplierInsights] = useState(false);
  const [showDeliveryNotePairing, setShowDeliveryNotePairing] = useState(false);

  const isFileStatus = 'processing_status' in document;
  const isInvoice = 'invoice_number' in document;
  const isDeliveryNote = 'delivery_note_number' in document;
  const isLocalDocument = 'filename' in document && 'supplier' in document && 'invoiceNumber' in document;

  // Get supplier name for insights
  const getSupplierName = () => {
    if (isInvoice) return document.supplier_name;
    if (isDeliveryNote) return document.supplier_name;
    if (isLocalDocument) return document.supplier;
    return 'Unknown Supplier';
  };

  // Get invoice number for pairing
  const getInvoiceNumber = () => {
    if (isInvoice) return document.invoice_number;
    if (isLocalDocument) return document.invoiceNumber;
    return undefined;
  };

  // Get document ID
  const getDocumentId = () => {
    return document.id;
  };

  const getStatusBadge = () => {
    if (isFileStatus) {
      const status = document.processing_status;
      switch (status) {
        case 'pending':
          return <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-yellow-100 text-yellow-800">⏳ Pending</span>;
        case 'processing':
          return <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">🔄 Processing</span>;
        case 'completed':
          return <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">✅ Completed</span>;
        case 'failed':
          return <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800">❌ Failed</span>;
        default:
          return <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800">Unknown</span>;
      }
    } else if (isLocalDocument) {
      const status = document.status;
      switch (status) {
        case 'Matched':
          return <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">✅ Matched</span>;
        case 'Unmatched':
          return <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-orange-100 text-orange-800">⚠️ Awaiting Match</span>;
        case 'Scanned':
          return <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">📄 Scanned</span>;
        case 'Error':
          return <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800">❌ Error</span>;
        case 'Processing':
          return <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">🔄 Processing</span>;
        default:
          return <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800">Unknown</span>;
      }
    } else {
      const status = document.status;
      switch (status) {
        case 'matched':
          return <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">✅ Matched</span>;
        case 'unmatched':
          return <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-orange-100 text-orange-800">⚠️ Awaiting Match</span>;
        case 'scanned':
          return <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">📄 Scanned</span>;
        case 'waiting':
          return <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">⏳ Waiting</span>;
        case 'utility':
          return <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-purple-100 text-purple-800">🧾 Utility Invoice</span>;
        case 'error':
          return <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800">❌ Error</span>;
        default:
          return <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800">Unknown</span>;
      }
    }
  };

  const getDocumentInfo = () => {
    if (isFileStatus) {
      return {
        title: document.original_filename,
        subtitle: `${document.file_type} • ${new Date(document.upload_timestamp).toLocaleDateString()}`,
        details: document.error_message ? `Error: ${document.error_message}` : undefined,
        confidence: document.confidence,
      };
    } else if (isLocalDocument) {
      return {
        title: document.invoiceNumber || 'Invoice',
        subtitle: `${document.supplier || 'Unknown Supplier'} • ${document.invoiceDate || 'No date'}`,
        details: document.totalAmount ? `£${document.totalAmount}` : undefined,
        confidence: document.confidence,
        matched: document.matchedDocument ? `Matched with ${document.matchedDocument.invoiceNumber || document.matchedDocument.deliveryNumber}` : undefined,
      };
    } else if (isInvoice) {
      return {
        title: document.invoice_number || 'Invoice',
        subtitle: `${document.supplier_name || 'Unknown Supplier'} • ${document.invoice_date || 'No date'}`,
        details: document.total_amount ? `£${document.total_amount.toFixed(2)}` : undefined,
        confidence: document.confidence,
        matched: (document as any).delivery_note ? `Matched with ${(document as any).delivery_note.delivery_note_number}` : undefined,
      };
    } else if (isDeliveryNote) {
      return {
        title: document.delivery_note_number || 'Delivery Note',
        subtitle: `${document.supplier_name || 'Unknown Supplier'} • ${document.delivery_date || 'No date'}`,
        details: undefined,
        confidence: document.confidence,
        matched: document.invoice ? `Matched with ${document.invoice.invoice_number}` : undefined,
      };
    }
    return { title: 'Unknown Document', subtitle: '', details: undefined, confidence: undefined };
  };

  const info = getDocumentInfo();

  return (
    <div className="relative">
      <div 
        className={`bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4 hover:shadow-lg transition-all duration-200 cursor-pointer ${
          onClick ? 'hover:border-blue-300 dark:hover:border-blue-600' : ''
        }`}
        onClick={onClick}
      >
        {/* Multiple Invoices Badge */}
        {multipleInvoices && (
          <div className="absolute top-2 left-2 z-10">
            <div className="bg-blue-100 text-blue-600 text-xs px-2 py-1 rounded-full border border-blue-200 flex items-center gap-1">
              <span>📄</span>
              <span>Invoice {invoiceCount > 1 ? `1/${invoiceCount}` : '1'} from PDF</span>
            </div>
          </div>
        )}

        <div className="flex justify-between items-start mb-3">
          <div className="flex-1 min-w-0">
            <div className="flex items-center space-x-2">
              <h3 className="text-sm font-medium text-gray-900 truncate">
                {info.title}
              </h3>
              
              {/* Supplier Insights Icon */}
              {getSupplierName() && getSupplierName() !== 'Unknown Supplier' && (
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    setShowSupplierInsights(!showSupplierInsights);
                  }}
                  className="text-gray-400 hover:text-blue-600 transition-colors"
                  title="View supplier insights"
                >
                  📊
                </button>
              )}
            </div>
            
            <p className="text-xs text-gray-500 mt-1">
              {info.subtitle}
            </p>
            
            {/* Delivery Note Status for Invoices */}
            {isInvoice && !isUtilityInvoice && (
              <p className="text-xs text-gray-500 mt-1">
                Delivery Note: {deliveryNoteRequired ? 'Required' : 'Not Required'}
              </p>
            )}
            
            {/* Delivery Note Status for Local Documents */}
            {isLocalDocument && document.type === 'Invoice' && !isUtilityInvoice && (
              <p className="text-xs text-gray-500 mt-1">
                Delivery Note: {deliveryNoteRequired ? 'Required' : 'Not Required'}
              </p>
            )}
          </div>
          
          <div className="flex items-center space-x-2">
            {getStatusBadge()}
            
            {/* Confidence Badge */}
            {info.confidence !== undefined && (
              <ConfidenceBadge 
                confidence={Math.round(info.confidence * 100)}
              />
            )}
            
            {/* Action Buttons */}
            <div className="flex items-center space-x-1">
              {/* Pair Delivery Note Button */}
              {isInvoice && document.status === 'scanned' && onPairDeliveryNote && (
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    setShowDeliveryNotePairing(true);
                  }}
                  className="text-gray-400 hover:text-blue-600 transition-colors"
                  title="Pair with delivery note"
                >
                  🔗
                </button>
              )}
              
              {/* Credit Note Button */}
              {isInvoice && onCreditNote && (
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    onCreditNote();
                  }}
                  className="text-gray-400 hover:text-orange-600 transition-colors"
                  title="Suggest credit note"
                >
                  💰
                </button>
              )}
              
              {/* Re-OCR Button for Low Confidence */}
              {info.confidence !== undefined && info.confidence < 0.7 && onReOCR && (
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    onReOCR();
                  }}
                  className="text-gray-400 hover:text-yellow-600 transition-colors"
                  title="Re-run OCR"
                >
                  🔄
                </button>
              )}
              
              {onCancel && (
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    onCancel();
                  }}
                  className="text-gray-400 hover:text-red-500 transition-colors"
                >
                  ×
                </button>
              )}
            </div>
          </div>
        </div>

        {info.details && (
          <p className="text-sm text-gray-700 mb-2">
            {info.details}
          </p>
        )}

        {info.matched && (
          <p className="text-xs text-green-600 mb-2">
            {info.matched}
          </p>
        )}

        {/* Click to View Details Hint */}
        {onClick && (
          <div className="mt-2 text-xs text-blue-600 dark:text-blue-400">
            Click to view details →
          </div>
        )}

        {isFileStatus && document.processing_status === 'processing' && (
          <div className="mt-3">
            <div className="w-full bg-gray-200 rounded-full h-2">
              <div className="bg-blue-600 h-2 rounded-full animate-pulse" style={{ width: '60%' }}></div>
            </div>
          </div>
        )}
      </div>

      {/* Supplier Insights Popup */}
      {showSupplierInsights && (
        <div className="absolute top-0 left-0 z-50">
          <SupplierInsights
            supplierName={getSupplierName() || ''}
            isVisible={showSupplierInsights}
            onClose={() => setShowSupplierInsights(false)}
          />
        </div>
      )}

      {/* Delivery Note Pairing Modal */}
      <DeliveryNotePairing
        isOpen={showDeliveryNotePairing}
        onClose={() => setShowDeliveryNotePairing(false)}
        invoiceId={getDocumentId()}
        invoiceNumber={getInvoiceNumber()}
        supplierName={getSupplierName()}
        onPair={(deliveryNoteId) => {
          onPairDeliveryNote?.(deliveryNoteId);
          setShowDeliveryNotePairing(false);
        }}
      />
    </div>
  );
};

export default DocumentCard; 