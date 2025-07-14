import React from 'react';

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

// --- Main Component ---
interface InvoiceCardProps {
  invoiceId: string;
  supplierName: string;
  invoiceDate: string;
  totalAmount: string;
  progress: number;
  status: 'processing' | 'matched' | 'unmatched' | 'error' | 'complete';
  errorMessage?: string;
  onClick?: () => void;
  onCancel?: () => void;
  isProcessing?: boolean;
  confidence?: number;
  parsedData?: any;
}

const InvoiceCard: React.FC<InvoiceCardProps> = ({
  invoiceId,
  supplierName,
  invoiceDate,
  totalAmount,
  progress,
  status,
  errorMessage,
  onClick,
  onCancel,
  isProcessing = false,
  confidence,
  parsedData,
}) => {
  const getStatusBadge = () => {
    switch (status) {
      case 'matched':
        return (
          <span className="bg-emerald-100 text-emerald-800 text-xs font-semibold px-2.5 py-0.5 rounded-full flex items-center gap-1">
            <CheckIcon />
            <span>✅ Matched</span>
          </span>
        );
      case 'unmatched':
        return (
          <span className="bg-amber-100 text-amber-800 text-xs font-semibold px-2.5 py-0.5 rounded-full flex items-center gap-1">
            <ClockIcon />
            <span>📄 Unmatched</span>
          </span>
        );
      case 'error':
        return (
          <span className="bg-red-100 text-red-800 text-xs font-semibold px-2.5 py-0.5 rounded-full flex items-center gap-1">
            <ErrorIcon />
            <span>❌ Error: {errorMessage || 'OCR failed'}</span>
          </span>
        );
      case 'complete':
        return (
          <span className="bg-blue-100 text-blue-800 text-xs font-semibold px-2.5 py-0.5 rounded-full flex items-center gap-1">
            <CheckIcon />
            <span>✅ Complete</span>
          </span>
        );
      case 'processing':
      default:
        return (
          <span className="bg-blue-100 text-blue-800 text-xs font-semibold px-2.5 py-0.5 rounded-full flex items-center gap-1">
            <ClockIcon />
            <span>⏳ Scanning...</span>
          </span>
        );
    }
  };

  const isError = status === 'error';
  const isProcessingState = status === 'processing' || isProcessing;

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

      <div className="flex flex-col space-y-4">
        {/* Header */}
        <div className="flex justify-between items-start">
          <div className="flex-1 min-w-0">
            <h3 className="text-xs font-medium uppercase text-gray-500">Invoice</h3>
            <p className="text-sm text-gray-900 font-semibold truncate">
              {isError ? '⚠ Failed to scan' : supplierName || 'Processing...'}
            </p>
            <p className="text-sm text-gray-700">Date: {invoiceDate || 'Extracting...'}</p>
            <p className="text-sm text-gray-700">Total: {isError ? 'N/A' : (totalAmount || 'Calculating...')}</p>
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

        {/* Status Badge */}
        <div className="flex justify-between items-center">
          {getStatusBadge()}
          {confidence && (
            <span className="text-xs text-gray-500">
              Confidence: {confidence}%
            </span>
          )}
        </div>

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
                <div>Amount: ${parsedData.total_amount} {parsedData.currency}</div>
              )}
              {parsedData.invoice_date && (
                <div>Date: {parsedData.invoice_date}</div>
              )}
            </div>
          </div>
        )}

        {/* Action Buttons - only show for completed/error states */}
        {!isProcessingState && (
          <div className="flex justify-end gap-3 pt-4 border-t border-gray-100">
            {isError ? (
              <button 
                onClick={onClick}
                className="px-4 py-2 text-sm font-medium rounded-md bg-gray-100 text-gray-700 hover:bg-gray-200 transition-colors duration-200 ease-in-out"
              >
                🔍 Review
              </button>
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