import React from 'react';

export interface DocumentQueueItem {
  id: string;
  filename: string;
  file_type: string;
  file_path: string;
  file_size: number;
  upload_timestamp: string;
  processing_status: string;
  confidence: number; // percent 0-100
  extracted_text?: string;
  error_message?: string;
  supplier_guess: string;
  document_type_guess: string;
  status_badge: string;
  status: string;
  invoice_number?: string;
  invoice_date?: string;
  total_amount?: number;
}

interface DocumentQueueCardProps {
  document: DocumentQueueItem;
  onClick?: () => void;
  isSelected?: boolean;
  onSelectChange?: (selected: boolean) => void;
  showCheckbox?: boolean;
}

const DocumentQueueCard: React.FC<DocumentQueueCardProps> = ({ 
  document, 
  onClick, 
  isSelected = false, 
  onSelectChange,
  showCheckbox = false 
}) => {
  const getStatusBadge = () => {
    switch (document.status_badge) {
      case 'Unclassified':
        return <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-200">⏳ Unclassified</span>;
      case 'Needs Review':
        return <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-200">⚠️ Needs Review</span>;
      case 'Low Confidence':
        return <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-200">⚠️ Low Confidence</span>;
      case 'Awaiting Confirmation':
        return <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-200">⏳ Awaiting Confirmation</span>;
      default:
        return <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-200">{document.status_badge}</span>;
    }
  };

  const getDocumentTypeIcon = () => {
    switch (document.document_type_guess) {
      case 'invoice':
        return '📄';
      case 'delivery_note':
        return '📦';
      case 'receipt':
        return '🧾';
      case 'utility':
        return '⚡';
      default:
        return '📋';
    }
  };

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-GB', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const needsReview = document.status === 'pending' || document.status === 'failed' || document.confidence < 70;
  const hasLowConfidence = document.confidence < 70;
  const hasError = !!document.error_message;

  const handleCardClick = (e: React.MouseEvent) => {
    // Don't trigger card click if clicking on checkbox
    if ((e.target as HTMLElement).closest('.checkbox-container')) {
      return;
    }
    onClick?.();
  };

  const handleCheckboxChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    e.stopPropagation();
    onSelectChange?.(e.target.checked);
  };

  return (
    <div
      className={`relative bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-4 cursor-pointer transition-all duration-300 group ${
        isSelected 
          ? 'ring-2 ring-blue-500 shadow-lg border-blue-300 dark:border-blue-600' 
          : 'hover:shadow-lg hover:border-blue-300 dark:hover:border-blue-600 hover:ring-2 hover:ring-blue-200 dark:hover:ring-blue-800'
      } ${
        needsReview ? 'ring-2 ring-yellow-200 dark:ring-yellow-800' : ''
      }`}
      onClick={handleCardClick}
    >
      {/* Selection Checkbox */}
      {showCheckbox && (
        <div className="checkbox-container absolute top-3 left-3 z-10">
          <input
            type="checkbox"
            checked={isSelected}
            onChange={handleCheckboxChange}
            className="w-4 h-4 text-blue-600 bg-gray-100 border-gray-300 rounded focus:ring-blue-500 dark:focus:ring-blue-600 dark:ring-offset-gray-800 focus:ring-2 dark:bg-gray-700 dark:border-gray-600"
          />
        </div>
      )}

      {/* Warning Indicators */}
      <div className="absolute top-3 right-3 flex space-x-1">
        {hasLowConfidence && (
          <div 
            className="w-2 h-2 bg-yellow-500 rounded-full animate-pulse"
            title={`Low OCR confidence: ${Math.round(document.confidence)}%`}
          />
        )}
        {hasError && (
          <div 
            className="w-2 h-2 bg-red-500 rounded-full animate-pulse"
            title={`Error: ${document.error_message}`}
          />
        )}
      </div>

      {/* Header */}
      <div className={`flex items-start justify-between mb-3 ${showCheckbox ? 'ml-6' : ''}`}>
        <div className="flex items-center space-x-3">
          <div className="text-2xl">{getDocumentTypeIcon()}</div>
          <div className="min-w-0 flex-1">
            <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-100 truncate">
              {document.filename}
            </h3>
            <p className="text-xs text-gray-500 dark:text-gray-400">
              {document.document_type_guess.replace('_', ' ').toUpperCase()}
            </p>
          </div>
        </div>
        <div className="flex flex-col items-end space-y-1 ml-2">
          {getStatusBadge()}
          <span className={`text-xs ${
            hasLowConfidence 
              ? 'text-yellow-600 dark:text-yellow-400 font-medium' 
              : 'text-gray-500 dark:text-gray-400'
          }`}>
            {Math.round(document.confidence)}% confidence
          </span>
        </div>
      </div>

      {/* Content */}
      <div className="space-y-2">
        <div>
          <p className="text-sm text-gray-700 dark:text-gray-300">
            <span className="font-medium">Supplier:</span> {document.supplier_guess}
          </p>
        </div>

        <div className="flex justify-between text-sm text-gray-600 dark:text-gray-400">
          <span>Uploaded: {formatDate(document.upload_timestamp)}</span>
          <span>{formatFileSize(document.file_size)}</span>
        </div>

        {document.error_message && (
          <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-md p-2">
            <p className="text-xs text-red-700 dark:text-red-300">
              <span className="font-medium">Error:</span> {document.error_message}
            </p>
          </div>
        )}

        {needsReview && !hasError && (
          <div className="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-md p-2">
            <p className="text-xs text-yellow-700 dark:text-yellow-300 font-medium">
              ⚠️ Needs review - Click to open
            </p>
          </div>
        )}
      </div>

      {/* Hover overlay effect */}
      <div className="absolute inset-0 bg-blue-500 opacity-0 group-hover:opacity-5 rounded-lg transition-opacity duration-300 pointer-events-none" />
    </div>
  );
};

export default DocumentQueueCard; 