import React, { useState } from 'react';
import InvoiceLineItemTable from './InvoiceLineItemTable';

// --- Icon Components ---
const CheckIcon: React.FC = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24"
    fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"
    className="w-3 h-3 text-emerald-500">
    <polyline points="20 6 9 17 4 12"></polyline>
  </svg>
);

const ClockIcon: React.FC = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24"
    fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"
    className="w-3 h-3 text-amber-500">
    <circle cx="12" cy="12" r="10"></circle>
    <polyline points="12 6 12 12 16 14"></polyline>
  </svg>
);

const ErrorIcon: React.FC = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24"
    fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"
    className="w-3 h-3 text-red-500">
    <circle cx="12" cy="12" r="10"></circle>
    <line x1="15" y1="9" x2="9" y2="15"></line>
    <line x1="9" y1="9" x2="15" y2="15"></line>
  </svg>
);

const CancelIcon: React.FC = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24"
    fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"
    className="w-4 h-4">
    <line x1="18" y1="6" x2="6" y2="18"></line>
    <line x1="6" y1="6" x2="18" y2="18"></line>
  </svg>
);

// --- Progress Circle Component ---
interface ProgressCircleProps {
  progress: number;
  label?: string;
  color?: string;
  isProcessing?: boolean;
}

const ProgressCircle: React.FC<ProgressCircleProps> = ({ progress, label, color, isProcessing = false }) => {
  const radius = 20;
  const circumference = 2 * Math.PI * radius;
  const clampedProgress = Math.min(100, Math.max(0, progress));
  const strokeDashoffset = circumference - (clampedProgress / 100) * circumference;

  const progressColorClass = color || (
    clampedProgress >= 85 ? 'text-emerald-500' :
    clampedProgress >= 60 ? 'text-amber-500' :
    'text-red-500'
  );

  return (
    <div className="relative w-16 h-16 flex items-center justify-center">
      <svg className={`w-full h-full transform -rotate-90 ${isProcessing ? 'animate-spin' : ''}`} viewBox="0 0 44 44">
        <circle
          className="text-gray-200"
          strokeWidth="4"
          stroke="currentColor"
          fill="transparent"
          r={radius}
          cx="22"
          cy="22"
        />
        <circle
          className={`${progressColorClass} transition-all duration-300 ease-out`}
          strokeWidth="4"
          strokeDasharray={circumference}
          strokeDashoffset={strokeDashoffset}
          strokeLinecap="round"
          stroke="currentColor"
          fill="transparent"
          r={radius}
          cx="22"
          cy="22"
        />
      </svg>
      <span className={`absolute text-sm font-semibold ${color ? color : 'text-gray-800'}`}>
        {label || `${Math.round(clampedProgress)}%`}
      </span>
    </div>
  );
};

// --- Status Badge Component ---
const StatusBadge = ({ status }: { status: 'SUCCESS' | 'OCR_FAILED' | 'processing' | 'matched' | 'unmatched' | 'error' | 'complete' }) => {
  const getBadgeConfig = () => {
    switch (status) {
      case 'SUCCESS':
        return { color: 'bg-green-100 text-green-800', label: 'Success', icon: <CheckIcon /> };
      case 'OCR_FAILED':
        return { color: 'bg-red-100 text-red-800', label: 'OCR Failed', icon: <ErrorIcon /> };
      case 'matched':
        return { color: 'bg-emerald-100 text-emerald-800', label: '✅ Matched', icon: <CheckIcon /> };
      case 'unmatched':
        return { color: 'bg-amber-100 text-amber-800', label: '📄 Unmatched', icon: <ClockIcon /> };
      case 'error':
        return { color: 'bg-red-100 text-red-800', label: '❌ Error', icon: <ErrorIcon /> };
      case 'complete':
        return { color: 'bg-blue-100 text-blue-800', label: '✅ Complete', icon: <CheckIcon /> };
      case 'processing':
      default:
        return { color: 'bg-blue-100 text-blue-800', label: '⏳ Scanning...', icon: <ClockIcon /> };
    }
  };

  const config = getBadgeConfig();
  return (
    <span className={`text-xs rounded-full px-2 py-0.5 font-semibold flex items-center gap-1 ${config.color}`}>
      {config.icon}
      <span>{config.label}</span>
    </span>
  );
};

// --- Main Component ---
export interface InvoiceCardProps {
  invoiceId: string;
  supplierName: string;
  invoiceNumber: string;
  invoiceDate: string;
  totalAmount: string;
  progress: number;
  status: 'processing' | 'matched' | 'unmatched' | 'error' | 'complete' | 'SUCCESS' | 'OCR_FAILED';
  errorMessage?: string;
  onClick?: () => void;
  onCancel?: () => void;
  onRetry?: () => void;
  isProcessing?: boolean;
  confidence?: number;
  parsedData?: any;
  // New OCR feedback props
  debugPath?: string;
  // Utility invoice props
  isUtilityInvoice?: boolean;
  deliveryNoteRequired?: boolean;
  multipleInvoices?: boolean;
  invoiceCount?: number;
}

const InvoiceCard: React.FC<InvoiceCardProps> = ({
  invoiceId,
  supplierName,
  invoiceNumber,
  invoiceDate,
  totalAmount,
  progress,
  status,
  errorMessage,
  onClick,
  onCancel,
  onRetry,
  isProcessing = false,
  confidence,
  parsedData,
  debugPath,
  isUtilityInvoice = false,
  deliveryNoteRequired = true,
  multipleInvoices = false,
  invoiceCount = 1,
}) => {
  const [isExpanded, setIsExpanded] = useState(false);
  const isError = status === 'error' || status === 'OCR_FAILED';
  const isProcessingState = status === 'processing' || isProcessing;
  const isSuccess = status === 'SUCCESS' || status === 'complete' || status === 'matched';

  // Extract line items from parsedData
  const lineItems = parsedData?.line_items || [];

  return (
    <div className={`
      bg-white rounded-2xl shadow-md border border-gray-200/50 p-4 sm:p-6 mb-6 relative 
      transition-all ease-in duration-500 opacity-0 animate-fade-in max-w-4xl mx-auto w-full
      ${isError ? 'opacity-75' : ''}
      ${isProcessingState ? 'blur-[0.5px]' : ''}
    `}>
      {/* Cancel Button - only show during processing or error */}
      {(isProcessingState || isError) && onCancel && (
        <button
          onClick={(e) => {
            e.stopPropagation();
            onCancel();
          }}
          className="absolute top-2 right-2 z-10 text-gray-400 hover:text-red-500 transition-colors duration-200 p-1 rounded-full hover:bg-red-50"
          title="Cancel/Remove"
        >
          <CancelIcon />
        </button>
      )}

      {/* Utility Invoice Badge */}
      {isUtilityInvoice && (
        <div className="absolute top-2 left-2 z-10">
          <div className="bg-gray-100 text-gray-600 text-xs px-2 py-1 rounded-full border border-gray-200 flex items-center gap-1">
            <span>🧾</span>
            <span>Service Invoice</span>
            <span className="text-gray-400">•</span>
            <span>No Delivery Note Needed</span>
          </div>
        </div>
      )}

      {/* Multiple Invoice Badge */}
      {multipleInvoices && invoiceCount > 1 && (
        <div className="absolute top-2 left-2 z-10">
          <div className="bg-blue-100 text-blue-600 text-xs px-2 py-1 rounded-full border border-blue-200 flex items-center gap-1">
            <span>📄</span>
            <span>Invoice {invoiceCount > 1 ? `1/${invoiceCount}` : '1'} from PDF</span>
          </div>
        </div>
      )}

      <div className="flex flex-col space-y-4">
        {/* Header */}
        <div className="flex justify-between items-start">
          <div className="flex-1 min-w-0">
            <h3 className="text-xs font-medium uppercase text-gray-500">Invoice</h3>
            <div className="flex items-center gap-2">
              <p className="text-sm text-gray-900 font-semibold truncate">
                {isError ? '⚠ Failed to scan' : supplierName || 'Processing...'}
              </p>
              <StatusBadge status={status} />
            </div>
            <p className="text-sm text-gray-700">Date: {invoiceDate || 'Extracting...'}</p>
            <p className="text-sm text-gray-700">Total: {isError ? 'N/A' : (totalAmount || 'Calculating...')}</p>
            <p className="text-sm text-gray-700">Invoice #: {invoiceNumber || 'Extracting...'}</p>
            
            {/* Delivery Note Status */}
            {!isUtilityInvoice && (
              <p className="text-sm text-gray-700">
                Delivery Note: {deliveryNoteRequired ? 'Required' : 'Not Required'}
              </p>
            )}
          </div>
          
          {/* Progress Circle */}
          <div className="flex-shrink-0">
            <ProgressCircle
              progress={progress}
              label={isProcessingState ? 'Scanning' : `${Math.round(progress)}%`}
              color={isError ? 'text-red-500' : undefined}
              isProcessing={isProcessingState}
            />
          </div>
        </div>

        {/* OCR Feedback Messages */}
        {status === 'OCR_FAILED' && (
          <div className="text-red-600 text-xs mt-1">OCR failed — click to retry or upload a clearer file.</div>
        )}

        {isSuccess && (
          <div className="text-xs text-amber-600">
            {supplierName === 'Unknown' || invoiceNumber === 'Unknown' || totalAmount === '0.0'
              ? '⚠️ Partial match: Some fields missing'
              : '✅ OCR complete'}
          </div>
        )}

        {/* Debug Path Link */}
        {debugPath && (
          <a
            href={`file://${debugPath}`}
            className="text-xs underline text-muted-foreground"
            target="_blank"
            rel="noreferrer"
          >
            View raw OCR output
          </a>
        )}

        {/* Confidence Score */}
        {confidence && (
          <div className="flex items-center justify-between">
            <span className="text-xs text-gray-500">
              Confidence: {confidence}%
            </span>
          </div>
        )}

        {/* Processing Message */}
        {isProcessingState && (
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-3">
            <div className="flex items-center gap-2">
              <ClockIcon />
              <span className="text-sm text-blue-700">Extracting invoice data...</span>
            </div>
          </div>
        )}

        {/* Error Message */}
        {isError && errorMessage && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-3">
            <div className="flex items-center gap-2">
              <ErrorIcon />
              <span className="text-sm text-red-700">{errorMessage}</span>
            </div>
          </div>
        )}

        {/* Parsed Data Preview */}
        {parsedData && !isError && (
          <div className="bg-green-50 border border-green-200 rounded-lg p-3">
            <h4 className="text-xs font-medium text-green-800 mb-1">Extracted Data:</h4>
            <div className="text-xs text-green-700 space-y-1">
              {parsedData.supplier_name && (
                <div>Supplier: {parsedData.supplier_name}</div>
              )}
              {parsedData.invoice_number && (
                <div>Invoice #: {parsedData.invoice_number}</div>
              )}
              {parsedData.total_amount && (
                <div>Amount: £{parsedData.total_amount}</div>
              )}
              {parsedData.invoice_date && (
                <div>Date: {parsedData.invoice_date}</div>
              )}
            </div>
          </div>
        )}

        {/* Expandable Line Items */}
        {isSuccess && lineItems.length > 0 && (
          <div className="border-t border-gray-100 pt-4">
            <button
              onClick={() => setIsExpanded(!isExpanded)}
              className="flex items-center justify-between w-full text-left text-sm font-medium text-gray-700 hover:text-gray-900 transition-colors"
            >
              <span>📋 Line Items ({lineItems.length})</span>
              <span className="text-gray-400">
                {isExpanded ? '▼' : '▶'}
              </span>
            </button>
            
            {isExpanded && (
              <div className="mt-4">
                <InvoiceLineItemTable 
                  items={lineItems}
                  className="mt-4"
                />
              </div>
            )}
          </div>
        )}

        {/* Action Buttons - only show for completed/error states */}
        {!isProcessingState && (
          <div className="flex justify-end gap-3 pt-4 border-t border-gray-100">
            {isError ? (
              <>
                <button 
                  onClick={onClick}
                  className="px-4 py-2 text-sm font-medium rounded-md bg-gray-100 text-gray-700 hover:bg-gray-200 transition-colors duration-200 ease-in-out"
                >
                  🔍 Review
                </button>
                {onRetry && (
                  <button 
                    onClick={onRetry}
                    className="px-4 py-2 text-sm font-medium rounded-md bg-blue-600 text-white hover:bg-blue-700 transition-colors duration-200 ease-in-out"
                  >
                    🔄 Retry OCR
                  </button>
                )}
              </>
            ) : (
              <>
                <button 
                  onClick={onClick}
                  className="px-4 py-2 text-sm font-medium rounded-md bg-gray-100 text-gray-700 hover:bg-gray-200 transition-colors duration-200 ease-in-out"
                >
                  👁 View
                </button>
                <button 
                  onClick={onClick}
                  className="px-4 py-2 text-sm font-medium rounded-md bg-emerald-600 text-white hover:bg-emerald-700 transition-colors duration-200 ease-in-out"
                >
                  ✅ Confirm
                </button>
              </>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default InvoiceCard; 