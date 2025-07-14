import React, { useState } from 'react';
import InvoiceDetailBox from './InvoiceDetailBox';

interface DocumentCardProps {
  supplier: string;
  invoiceId: string;
  invoiceDate: string;
  totalAmount: string;
  status: 'Processing' | 'Scanned' | 'Matched' | 'Unmatched' | 'Error' | 'Unknown' | 'Complete';
  numIssues?: number;
  loadingPercent?: number;
  // Add new props for detail functionality
  parsedData?: any;
  documentType?: string;
  confidence?: number;
  matchedDocument?: any;
  // Add cancel functionality
  onCancel?: (id: string) => void;
  documentId?: string;
}

export const DocumentCard: React.FC<DocumentCardProps> = ({
  supplier,
  invoiceId,
  invoiceDate,
  totalAmount,
  status,
  numIssues = 0,
  loadingPercent = 100,
  parsedData,
  documentType,
  confidence,
  matchedDocument,
  onCancel,
  documentId,
}) => {
  const [isExpanded, setIsExpanded] = useState(false);

  const statusColors: Record<string, string> = {
    Processing: 'bg-yellow-100 text-yellow-800',
    Scanned: 'bg-green-100 text-green-800',
    Matched: 'bg-green-100 text-green-800',
    Complete: 'bg-green-100 text-green-800',
    Unmatched: 'bg-red-100 text-red-800',
    Error: 'bg-red-200 text-red-900',
    Unknown: 'bg-gray-100 text-gray-800',
  };

  const getStatusIcon = (status: string) => {
    switch (status.toLowerCase()) {
      case 'processing':
        return (
          <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4 animate-spin text-yellow-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 4v5h.582M20 20v-5h-.581M4.21 15.89A9 9 0 1112 21v-1.5" />
          </svg>
        );
      case 'complete':
      case 'scanned':
        return (
          <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M5 13l4 4L19 7" />
          </svg>
        );
      case 'matched':
        return (
          <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 13l3 3 4-4M11 13l3 3 6-6" />
          </svg>
        );
      case 'error':
      case 'flagged':
        return (
          <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4 text-red-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 9v2m0 4h.01M12 5a7 7 0 100 14 7 7 0 000-14z" />
          </svg>
        );
      case 'unknown':
      case 'unclassified':
        return (
          <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 8c.667-2 4-1.333 4 1 0 2-2 2-2 4m0 4h.01" />
          </svg>
        );
      default:
        return (
          <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 8c.667-2 4-1.333 4 1 0 2-2 2-2 4m0 4h.01" />
          </svg>
        );
    }
  };

  const StatusBadge = () => (
    <span
      className={`text-xs px-2 py-1 rounded-full font-medium flex items-center gap-1 ${statusColors[status] || 'bg-gray-200 text-gray-700'}`}
    >
      {getStatusIcon(status)}
      <span>{status === 'Complete' || status === 'Scanned' ? 'Scanned' : status}</span>
    </span>
  );

  const ProgressBar = () => {
    if (status === 'Processing') {
      return (
        <div className="w-full h-2 mt-2 bg-gray-200 rounded-full overflow-hidden">
          <div
            className="h-full bg-blue-500 transition-all duration-300 ease-out"
            style={{ width: `${loadingPercent}%` }}
          />
        </div>
      );
    }
    return null;
  };

  const handleEdit = () => {
    console.log('Edit invoice:', invoiceId);
    // TODO: Implement edit functionality
  };

  const handleComment = () => {
    console.log('Add comment to invoice:', invoiceId);
    // TODO: Implement comment functionality
  };

  const toggleExpanded = () => {
    setIsExpanded(!isExpanded);
  };

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 mb-3 w-full transition-all duration-300 hover:shadow-md hover:border-gray-300 relative">
      {/* Cancel Button - only show during processing */}
      {status === 'Processing' && onCancel && documentId && (
        <button
          onClick={(e) => {
            e.stopPropagation(); // Prevent card expansion
            onCancel(documentId);
          }}
          className="absolute top-2 right-2 z-10 text-gray-400 hover:text-red-500 transition-colors duration-200 p-1 rounded-full hover:bg-red-50"
          title="Cancel upload"
        >
          <svg xmlns="http://www.w3.org/2000/svg" className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      )}
      
      {/* Main card content - clickable */}
      <div 
        className="p-4 cursor-pointer hover:bg-gray-50 transition-colors duration-200"
        onClick={toggleExpanded}
      >
        <div className="flex justify-between items-start mb-2">
          <span className="text-sm text-gray-500 truncate">#{invoiceId}</span>
          <span className="text-sm text-gray-500 flex-shrink-0 ml-2">{invoiceDate}</span>
        </div>
        <div className="flex justify-between items-start">
          <div className="flex-1 min-w-0">
            <h3 className="text-lg font-semibold text-gray-800 truncate">{supplier}</h3>
            
            {/* Pairing Status Badge */}
            <div className="mt-2">
              {status === 'Matched' || status === 'Complete' ? (
                <span className="inline-block px-2 py-1 text-xs rounded bg-green-100 text-green-800">
                  ✅ Paired with Delivery Note
                </span>
              ) : (
                <span className="inline-block px-2 py-1 text-xs rounded bg-yellow-100 text-yellow-800">
                  ⚠️ Unpaired
                </span>
              )}
            </div>
            
            <p className="text-md font-bold text-gray-900 mt-1">£{totalAmount}</p>
            {numIssues > 0 && (
              <p className="text-sm text-red-600 mt-1">
                {numIssues} issue{numIssues > 1 ? 's' : ''}
              </p>
            )}
          </div>
          <div className="flex-shrink-0 ml-4">
            <StatusBadge />
          </div>
        </div>
        <ProgressBar />
        
        {/* Expand/collapse indicator */}
        <div className="mt-3 flex items-center justify-center">
          <div className={`w-6 h-6 transition-transform duration-300 ${isExpanded ? 'rotate-180' : ''}`}>
            <svg className="w-full h-full text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
            </svg>
          </div>
        </div>
      </div>
      
      {/* Expandable detail section */}
      <div 
        className={`overflow-hidden transition-all duration-300 ease-in-out ${
          isExpanded ? 'max-h-[400px] opacity-100 translate-y-0' : 'max-h-0 opacity-0 -translate-y-2'
        }`}
      >
        <div className="px-4 pb-4">
          {/* Invoice Detail Box - only show for completed documents */}
          {(status === 'Complete' || status === 'Matched' || status === 'Error') && (
            <InvoiceDetailBox
              invoice={{
                lineItems: [],
                parsedData,
                documentType,
                confidence,
                matchedDocument,
              }}
              onEdit={handleEdit}
              onComment={handleComment}
            />
          )}
          
          {/* Show a message for processing or other statuses */}
          {status === 'Processing' && (
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
              <div className="flex items-center gap-2">
                {getStatusIcon('processing')}
                <span className="text-sm text-blue-700">Processing document...</span>
              </div>
              <p className="text-xs text-blue-600 mt-1">Details will be available once processing is complete</p>
            </div>
          )}
          
          {status === 'Unknown' && (
            <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
              <div className="flex items-center gap-2">
                {getStatusIcon('unknown')}
                <span className="text-sm text-gray-700">Document type unknown</span>
              </div>
              <p className="text-xs text-gray-600 mt-1">This document couldn't be classified automatically</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}; 