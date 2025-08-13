import React from 'react';

interface ParsedData {
  supplier_name?: string;
  invoice_number?: string;
  invoice_date?: string;
  total_amount?: string;
  currency?: string;
  delivery_note_number?: string;
  delivery_date?: string;
  [key: string]: any;
}

interface ExistingDocument {
  filename: string;
  type: string;
  status: string;
  uploaded_at: string;
  parsed_data: ParsedData;
}

interface DuplicateInfo {
  existing_doc: ExistingDocument;
  similarity_score: number;
  matching_fields: string[];
  differences: {
    [key: string]: {
      new: any;
      existing: any;
      similarity: number;
    };
  };
}

interface DuplicateCheckModalProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: () => void;
  onReject: () => void;
  newDocument: {
    filename: string;
    parsed_data: ParsedData;
    document_type: string;
    confidence_score: number;
  };
  duplicateInfo: DuplicateInfo;
}

const DuplicateCheckModal: React.FC<DuplicateCheckModalProps> = ({
  isOpen,
  onClose,
  onConfirm,
  onReject,
  newDocument,
  duplicateInfo
}) => {
  if (!isOpen) return null;

  const { existing_doc, similarity_score, matching_fields, differences } = duplicateInfo;
  const newData = newDocument.parsed_data;
  const existingData = existing_doc.parsed_data;

  const renderFieldComparison = (fieldName: string, label: string) => {
    const newValue = newData[fieldName] || 'N/A';
    const existingValue = existingData[fieldName] || 'N/A';
    const isMatching = matching_fields.includes(fieldName);
    const hasDifference = differences[fieldName];

    return (
      <div key={fieldName} className="mb-4">
        <h4 className="text-sm font-semibold text-gray-700 mb-2">{label}</h4>
        <div className="grid grid-cols-2 gap-4">
          {/* New Document */}
          <div className="bg-blue-50 p-3 rounded-lg border border-blue-200">
            <div className="text-xs text-blue-600 font-medium mb-1">New Document</div>
            <div className={`text-sm ${
              isMatching ? 'text-green-700' : 
              hasDifference ? 'text-orange-700' : 'text-gray-700'
            }`}>
              {newValue}
            </div>
          </div>
          
          {/* Existing Document */}
          <div className="bg-gray-50 p-3 rounded-lg border border-gray-200">
            <div className="text-xs text-gray-600 font-medium mb-1">Existing Document</div>
            <div className={`text-sm ${
              isMatching ? 'text-green-700' : 
              hasDifference ? 'text-orange-700' : 'text-gray-700'
            }`}>
              {existingValue}
            </div>
          </div>
        </div>
        
        {/* Show similarity score for differences */}
        {hasDifference && (
          <div className="mt-2 text-xs text-orange-600">
            Similarity: {(hasDifference.similarity * 100).toFixed(1)}%
          </div>
        )}
        
        {/* Show match indicator */}
        {isMatching && (
          <div className="mt-2 text-xs text-green-600 flex items-center gap-1">
            <span>✓</span>
            <span>Fields match</span>
          </div>
        )}
      </div>
    );
  };

  const getSimilarityColor = (score: number) => {
    if (score >= 0.95) return 'text-red-600';
    if (score >= 0.9) return 'text-orange-600';
    return 'text-yellow-600';
  };

  const getSimilarityLabel = (score: number) => {
    if (score >= 0.95) return 'Very High';
    if (score >= 0.9) return 'High';
    return 'Moderate';
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg shadow-xl max-w-4xl w-full max-h-[90vh] overflow-hidden">
        {/* Header */}
        <div className="bg-gradient-to-r from-orange-500 to-red-500 text-white p-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-white bg-opacity-20 rounded-full flex items-center justify-center">
                <span className="text-xl">⚠️</span>
              </div>
              <div>
                <h2 className="text-xl font-semibold">Possible Duplicate Detected</h2>
                <p className="text-orange-100 text-sm">
                  This document looks similar to one already uploaded
                </p>
              </div>
            </div>
            <button
              onClick={onClose}
              className="text-white hover:text-orange-100 transition-colors"
            >
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="p-6 overflow-y-auto max-h-[calc(90vh-200px)]">
          {/* Similarity Score */}
          <div className="mb-6 p-4 bg-orange-50 border border-orange-200 rounded-lg">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-lg font-semibold text-orange-800">
                  Similarity Analysis
                </h3>
                <p className="text-sm text-orange-600">
                  Overall similarity score: <span className={`font-semibold ${getSimilarityColor(similarity_score)}`}>
                    {(similarity_score * 100).toFixed(1)}% ({getSimilarityLabel(similarity_score)})
                  </span>
                </p>
              </div>
              <div className="text-right">
                <div className="text-2xl font-bold text-orange-600">
                  {(similarity_score * 100).toFixed(0)}%
                </div>
                <div className="text-xs text-orange-500">Match Score</div>
              </div>
            </div>
          </div>

          {/* Document Info */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
            {/* New Document */}
            <div className="bg-blue-50 p-4 rounded-lg border border-blue-200">
              <h3 className="text-lg font-semibold text-blue-800 mb-3 flex items-center gap-2">
                <span>📄</span>
                New Document
              </h3>
              <div className="space-y-2 text-sm">
                <div><span className="font-medium">Filename:</span> {newDocument.filename}</div>
                <div><span className="font-medium">Type:</span> {newDocument.document_type}</div>
                <div><span className="font-medium">Confidence:</span> {newDocument.confidence_score}%</div>
              </div>
            </div>

            {/* Existing Document */}
            <div className="bg-gray-50 p-4 rounded-lg border border-gray-200">
              <h3 className="text-lg font-semibold text-gray-800 mb-3 flex items-center gap-2">
                <span>📋</span>
                Existing Document
              </h3>
              <div className="space-y-2 text-sm">
                <div><span className="font-medium">Filename:</span> {existing_doc.filename}</div>
                <div><span className="font-medium">Type:</span> {existing_doc.type}</div>
                <div><span className="font-medium">Status:</span> {existing_doc.status}</div>
                <div><span className="font-medium">Uploaded:</span> {new Date(existing_doc.uploaded_at).toLocaleDateString()}</div>
              </div>
            </div>
          </div>

          {/* Field Comparison */}
          <div className="mb-6">
            <h3 className="text-lg font-semibold text-gray-800 mb-4">Field Comparison</h3>
            <div className="space-y-4">
              {renderFieldComparison('supplier_name', 'Supplier Name')}
              {renderFieldComparison('invoice_number', 'Invoice Number')}
              {renderFieldComparison('total_amount', 'Total Amount')}
              {renderFieldComparison('invoice_date', 'Invoice Date')}
              {renderFieldComparison('currency', 'Currency')}
            </div>
          </div>

          {/* Matching Fields Summary */}
          {matching_fields.length > 0 && (
            <div className="mb-6 p-4 bg-green-50 border border-green-200 rounded-lg">
              <h4 className="text-sm font-semibold text-green-800 mb-2">Matching Fields:</h4>
              <div className="flex flex-wrap gap-2">
                {matching_fields.map(field => (
                  <span key={field} className="px-2 py-1 bg-green-100 text-green-700 text-xs rounded-full">
                    {field.replace('_', ' ')}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Warning */}
          <div className="mb-6 p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
            <div className="flex items-start gap-3">
              <span className="text-yellow-600 text-lg">⚠️</span>
              <div>
                <h4 className="text-sm font-semibold text-yellow-800 mb-1">Important</h4>
                <p className="text-sm text-yellow-700">
                  Please carefully review the differences above. If this is a duplicate, 
                  you should remove the uploaded document. If it&apos;s a different document 
                  with similar details, you can continue with the upload.
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="bg-gray-50 px-6 py-4 border-t border-gray-200">
          <div className="flex items-center justify-between">
            <div className="text-sm text-gray-600">
              <span className="font-medium">Tip:</span> Check for differences in dates, amounts, or line items
            </div>
            <div className="flex gap-3">
              <button
                onClick={onReject}
                className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors font-medium"
              >
                Remove Upload (Duplicate)
              </button>
              <button
                onClick={onConfirm}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium"
              >
                Continue Upload (Not Duplicate)
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default DuplicateCheckModal; 