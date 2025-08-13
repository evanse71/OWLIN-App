import React, { useState, useEffect } from 'react';
import { DocumentQueueItem } from './DocumentQueueCard';

export interface ReviewData {
  document_type: 'invoice' | 'delivery_note' | 'receipt' | 'utility';
  supplier_name: string;
  invoice_number?: string;
  delivery_note_number?: string;
  invoice_date?: string;
  delivery_date?: string;
  total_amount?: number;
  confidence: number; // percent 0-100
  extracted_text?: string;
  line_items?: Array<{ description: string; quantity: number; unit_price?: number; total_price?: number }>;
  vat_included?: boolean;
  comments?: string;
}

export interface EscalationData {
  reason: string;
}

interface DocumentReviewModalProps {
  isOpen: boolean;
  onClose: () => void;
  document: DocumentQueueItem;
  onApprove: (document: DocumentQueueItem, reviewData: ReviewData) => void;
  onEscalate: (document: DocumentQueueItem, escalationData: EscalationData) => void;
  onDelete: (document: DocumentQueueItem) => void;
}

const DocumentReviewModal: React.FC<DocumentReviewModalProps> = ({
  isOpen,
  onClose,
  document,
  onApprove,
  onEscalate,
  onDelete
}) => {
  const [isEditing, setIsEditing] = useState(false);
  const [formData, setFormData] = useState<ReviewData>({
    document_type: document.document_type_guess as any || 'invoice',
    supplier_name: document.supplier_guess,
    invoice_number: '',
    delivery_note_number: '',
    invoice_date: '',
    delivery_date: '',
    total_amount: 0,
    confidence: document.confidence,
    extracted_text: document.extracted_text || '',
    line_items: [],
    vat_included: false,
    comments: ''
  });
  const [escalationReason, setEscalationReason] = useState('');
  const [loading, setLoading] = useState(false);
  
  // File preview states
  const [previewLoading, setPreviewLoading] = useState(true);
  const [previewError, setPreviewError] = useState<string | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);

  useEffect(() => {
    if (isOpen) {
      setFormData({
        document_type: document.document_type_guess as any || 'invoice',
        supplier_name: document.supplier_guess,
        invoice_number: '',
        delivery_note_number: '',
        invoice_date: '',
        delivery_date: '',
        total_amount: 0,
        confidence: document.confidence,
        extracted_text: document.extracted_text || '',
        line_items: [],
        vat_included: false,
        comments: ''
      });
      setIsEditing(false);
      setEscalationReason('');
      
      // Reset preview states
      setPreviewLoading(true);
      setPreviewError(null);
      setPreviewUrl(getFilePreviewUrl());
    }
  }, [isOpen, document]);

  const handleInputChange = (field: keyof ReviewData, value: any) => {
    setFormData(prev => ({
      ...prev,
      [field]: value
    }));
  };

  const handleLineItemChange = (index: number, field: string, value: any) => {
    setFormData(prev => ({
      ...prev,
      line_items: prev.line_items?.map((item, i) => 
        i === index ? { ...item, [field]: value } : item
      ) || []
    }));
  };

  const addLineItem = () => {
    setFormData(prev => ({
      ...prev,
      line_items: [...(prev.line_items || []), {
        description: '',
        quantity: 1,
        unit_price: 0,
        total_price: 0
      }]
    }));
  };

  const removeLineItem = (index: number) => {
    setFormData(prev => ({
      ...prev,
      line_items: prev.line_items?.filter((_, i) => i !== index) || []
    }));
  };

  const handleApprove = async () => {
    setLoading(true);
    try {
      await onApprove(document, formData);
    } finally {
      setLoading(false);
    }
  };

  const handleEscalate = async () => {
    if (!escalationReason.trim()) {
      alert('Please provide a reason for escalation');
      return;
    }
    
    setLoading(true);
    try {
      await onEscalate(document, { reason: escalationReason });
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async () => {
    if (!confirm('Are you sure you want to delete this document? This action cannot be undone.')) {
      return;
    }
    
    setLoading(true);
    try {
      await onDelete(document);
    } finally {
      setLoading(false);
    }
  };

  const getFilePreviewUrl = () => {
    // In a real implementation, you would serve the file from the backend
    // For now, we'll show a placeholder
    return `/api/files/${document.id}/preview`;
  };

  const getFileExtension = () => {
    return document.filename.split('.').pop()?.toLowerCase() || '';
  };

  const isImageFile = () => {
    const ext = getFileExtension();
    return ['jpg', 'jpeg', 'png'].includes(ext);
  };

  const isPdfFile = () => {
    return getFileExtension() === 'pdf';
  };

  const handlePreviewLoad = () => {
    setPreviewLoading(false);
    setPreviewError(null);
  };

  const handlePreviewError = () => {
    setPreviewLoading(false);
    setPreviewError('Failed to load preview');
  };

  const renderFilePreview = () => {
    if (previewLoading) {
      return (
        <div className="flex items-center justify-center h-64 bg-gray-50 dark:bg-gray-700 rounded-lg">
          <div className="text-center">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto mb-2"></div>
            <p className="text-sm text-gray-600 dark:text-gray-400">Loading preview...</p>
          </div>
        </div>
      );
    }

    if (previewError) {
      return (
        <div className="flex items-center justify-center h-64 bg-gray-50 dark:bg-gray-700 rounded-lg">
          <div className="text-center">
            <div className="text-4xl mb-2">⚠️</div>
            <p className="text-sm text-gray-600 dark:text-gray-400 mb-2">Preview not available</p>
            <p className="text-xs text-gray-500 dark:text-gray-500">{previewError}</p>
          </div>
        </div>
      );
    }

    if (isPdfFile()) {
      return (
        <div className="relative">
          <iframe
            src={previewUrl || ''}
            className="w-full h-96 border border-gray-300 dark:border-gray-600 rounded-lg"
            onLoad={handlePreviewLoad}
            onError={handlePreviewError}
            title={`Preview of ${document.filename}`}
          />
        </div>
      );
    }

    if (isImageFile()) {
      return (
        <div className="relative">
          <img
            src={previewUrl || ''}
            alt={`Preview of ${document.filename}`}
            className="w-full max-h-96 object-contain border border-gray-300 dark:border-gray-600 rounded-lg"
            onLoad={handlePreviewLoad}
            onError={handlePreviewError}
          />
        </div>
      );
    }

    // Fallback for unsupported file types
    return (
      <div className="flex items-center justify-center h-64 bg-gray-50 dark:bg-gray-700 rounded-lg">
        <div className="text-center">
          <div className="text-4xl mb-4">
            {document.document_type_guess === 'invoice' ? '📄' : 
             document.document_type_guess === 'delivery_note' ? '📦' : 
             document.document_type_guess === 'receipt' ? '🧾' : '📋'}
          </div>
          <p className="text-gray-600 dark:text-gray-400 mb-2">{document.filename}</p>
          <p className="text-sm text-gray-500 dark:text-gray-500">
            File size: {(document.file_size / 1024).toFixed(1)} KB
          </p>
          <p className="text-xs text-gray-400 dark:text-gray-500 mt-2">
            Preview not available for this file type
          </p>
        </div>
      </div>
    );
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-6xl w-full max-h-[90vh] overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200 dark:border-gray-700">
          <div>
            <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100">
              Review Document: {document.filename}
            </h2>
            <p className="text-sm text-gray-600 dark:text-gray-400">
              {document.document_type_guess.replace('_', ' ').toUpperCase()} • {Math.round(document.confidence)}% confidence
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

        <div className="flex h-[calc(90vh-120px)]">
          {/* Left Side - File Preview */}
          <div className="w-1/2 border-r border-gray-200 dark:border-gray-700 p-6 overflow-y-auto">
            <h3 className="text-lg font-medium text-gray-900 dark:text-gray-100 mb-4">Document Preview</h3>
            
            {/* File Preview */}
            {renderFilePreview()}

            {/* OCR Text Preview */}
            {document.extracted_text && (
              <div className="mt-6">
                <h4 className="text-sm font-medium text-gray-900 dark:text-gray-100 mb-2">Extracted Text</h4>
                <div className="bg-gray-50 dark:bg-gray-700 rounded-lg p-4 max-h-64 overflow-y-auto">
                  <pre className="text-xs text-gray-700 dark:text-gray-300 whitespace-pre-wrap">
                    {document.extracted_text}
                  </pre>
                </div>
              </div>
            )}
          </div>

          {/* Right Side - Editable Form */}
          <div className="w-1/2 p-6 overflow-y-auto">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-medium text-gray-900 dark:text-gray-100">Document Details</h3>
              <button
                onClick={() => setIsEditing(!isEditing)}
                className="px-3 py-1 text-sm bg-blue-600 text-white rounded hover:bg-blue-700"
              >
                {isEditing ? 'View' : 'Edit'}
              </button>
            </div>

            <form className="space-y-4">
              {/* Document Type */}
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Document Type
                </label>
                <select
                  value={formData.document_type}
                  onChange={(e) => handleInputChange('document_type', e.target.value)}
                  disabled={!isEditing}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-100 dark:disabled:bg-gray-800"
                >
                  <option value="invoice">Invoice</option>
                  <option value="delivery_note">Delivery Note</option>
                  <option value="receipt">Receipt</option>
                  <option value="utility">Utility</option>
                </select>
              </div>

              {/* Supplier Name */}
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Supplier Name
                </label>
                <input
                  type="text"
                  value={formData.supplier_name}
                  onChange={(e) => handleInputChange('supplier_name', e.target.value)}
                  disabled={!isEditing}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-100 dark:disabled:bg-gray-800"
                />
              </div>

              {/* Document Number */}
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  {formData.document_type === 'invoice' ? 'Invoice Number' : 
                   formData.document_type === 'delivery_note' ? 'Delivery Note Number' : 'Document Number'}
                </label>
                <input
                  type="text"
                  value={formData.document_type === 'invoice' ? formData.invoice_number : formData.delivery_note_number}
                  onChange={(e) => handleInputChange(
                    formData.document_type === 'invoice' ? 'invoice_number' : 'delivery_note_number', 
                    e.target.value
                  )}
                  disabled={!isEditing}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-100 dark:disabled:bg-gray-800"
                />
              </div>

              {/* Date */}
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  {formData.document_type === 'invoice' ? 'Invoice Date' : 
                   formData.document_type === 'delivery_note' ? 'Delivery Date' : 'Document Date'}
                </label>
                <input
                  type="date"
                  value={formData.document_type === 'invoice' ? formData.invoice_date : formData.delivery_date}
                  onChange={(e) => handleInputChange(
                    formData.document_type === 'invoice' ? 'invoice_date' : 'delivery_date', 
                    e.target.value
                  )}
                  disabled={!isEditing}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-100 dark:disabled:bg-gray-800"
                />
              </div>

              {/* Total Amount */}
              {formData.document_type === 'invoice' && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                    Total Amount
                  </label>
                  <input
                    type="number"
                    step="0.01"
                    value={formData.total_amount}
                    onChange={(e) => handleInputChange('total_amount', parseFloat(e.target.value) || 0)}
                    disabled={!isEditing}
                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-100 dark:disabled:bg-gray-800"
                  />
                </div>
              )}

              {/* VAT Included Checkbox */}
              {formData.document_type === 'invoice' && (
                <div className="flex items-center">
                  <input
                    type="checkbox"
                    checked={formData.vat_included}
                    onChange={(e) => handleInputChange('vat_included', e.target.checked)}
                    disabled={!isEditing}
                    className="rounded border-gray-300 text-blue-600 focus:ring-blue-500 disabled:bg-gray-100"
                  />
                  <label className="ml-2 text-sm text-gray-700 dark:text-gray-300">
                    VAT included in unit price
                  </label>
                </div>
              )}

              {/* Line Items */}
              {formData.document_type === 'invoice' && (
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                      Line Items
                    </label>
                    {isEditing && (
                      <button
                        type="button"
                        onClick={addLineItem}
                        className="text-sm text-blue-600 hover:text-blue-700"
                      >
                        + Add Item
                      </button>
                    )}
                  </div>
                  
                  {formData.line_items?.map((item, index) => (
                    <div key={index} className="border border-gray-200 dark:border-gray-600 rounded-lg p-3 mb-2">
                      <div className="grid grid-cols-2 gap-2">
                        <input
                          type="text"
                          placeholder="Description"
                          value={item.description}
                          onChange={(e) => handleLineItemChange(index, 'description', e.target.value)}
                          disabled={!isEditing}
                          className="px-2 py-1 text-sm border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-1 focus:ring-blue-500 disabled:bg-gray-100 dark:disabled:bg-gray-800"
                        />
                        <input
                          type="number"
                          placeholder="Qty"
                          value={item.quantity}
                          onChange={(e) => handleLineItemChange(index, 'quantity', parseFloat(e.target.value) || 0)}
                          disabled={!isEditing}
                          className="px-2 py-1 text-sm border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-1 focus:ring-blue-500 disabled:bg-gray-100 dark:disabled:bg-gray-800"
                        />
                        <input
                          type="number"
                          step="0.01"
                          placeholder="Unit Price"
                          value={item.unit_price}
                          onChange={(e) => handleLineItemChange(index, 'unit_price', parseFloat(e.target.value) || 0)}
                          disabled={!isEditing}
                          className="px-2 py-1 text-sm border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-1 focus:ring-blue-500 disabled:bg-gray-100 dark:disabled:bg-gray-800"
                        />
                        <div className="flex items-center space-x-1">
                          <input
                            type="number"
                            step="0.01"
                            placeholder="Total"
                            value={item.total_price}
                            onChange={(e) => handleLineItemChange(index, 'total_price', parseFloat(e.target.value) || 0)}
                            disabled={!isEditing}
                            className="px-2 py-1 text-sm border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-1 focus:ring-blue-500 disabled:bg-gray-100 dark:disabled:bg-gray-800"
                          />
                          {isEditing && (
                            <button
                              type="button"
                              onClick={() => removeLineItem(index)}
                              className="text-red-600 hover:text-red-700"
                            >
                              ×
                            </button>
                          )}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {/* Comments */}
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Comments
                </label>
                <textarea
                  value={formData.comments}
                  onChange={(e) => handleInputChange('comments', e.target.value)}
                  disabled={!isEditing}
                  rows={3}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-100 dark:disabled:bg-gray-800"
                  placeholder="Add any additional comments..."
                />
              </div>
            </form>

            {/* Action Buttons */}
            <div className="flex items-center justify-between pt-6 border-t border-gray-200 dark:border-gray-700 mt-6">
              <div className="flex space-x-2">
                <button
                  onClick={handleDelete}
                  disabled={loading}
                  className="px-4 py-2 text-sm font-medium text-red-700 bg-red-100 border border-red-300 rounded-md hover:bg-red-200 focus:outline-none focus:ring-2 focus:ring-red-500 disabled:opacity-50"
                >
                  {loading ? 'Deleting...' : 'Delete'}
                </button>
              </div>
              
              <div className="flex space-x-2">
                <button
                  onClick={onClose}
                  className="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 border border-gray-300 rounded-md hover:bg-gray-200 focus:outline-none focus:ring-2 focus:ring-gray-500"
                >
                  Cancel
                </button>
                
                <button
                  onClick={handleEscalate}
                  disabled={loading}
                  className="px-4 py-2 text-sm font-medium text-orange-700 bg-orange-100 border border-orange-300 rounded-md hover:bg-orange-200 focus:outline-none focus:ring-2 focus:ring-orange-500 disabled:opacity-50"
                >
                  {loading ? 'Escalating...' : 'Escalate to GM'}
                </button>
                
                <button
                  onClick={handleApprove}
                  disabled={loading}
                  className="px-4 py-2 text-sm font-medium text-white bg-green-600 border border-transparent rounded-md hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-green-500 disabled:opacity-50"
                >
                  {loading ? 'Approving...' : 'Approve'}
                </button>
              </div>
            </div>

            {/* Escalation Reason Input */}
            <div className="mt-4 p-4 bg-orange-50 dark:bg-orange-900/20 border border-orange-200 dark:border-orange-800 rounded-lg">
              <label className="block text-sm font-medium text-orange-800 dark:text-orange-200 mb-1">
                Escalation Reason
              </label>
              <input
                type="text"
                value={escalationReason}
                onChange={(e) => setEscalationReason(e.target.value)}
                placeholder="Enter reason for escalation..."
                className="w-full px-3 py-2 border border-orange-300 dark:border-orange-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-orange-500"
              />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default DocumentReviewModal; 