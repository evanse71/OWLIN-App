import React, { useState } from 'react';
import { Invoice, DeliveryNote } from '@/services/api';
import ConfidenceBadge from '@/components/common/ConfidenceBadge';

interface LineItem {
  name: string;
  quantity: number;
  unit_price: number;
  total_price: number;
  description?: string;
}

interface Comment {
  id: string;
  user: string;
  timestamp: string;
  message: string;
  type: 'info' | 'warning' | 'error' | 'success';
}

interface StatusTimeline {
  status: string;
  timestamp: string;
  user?: string;
  comment?: string;
}

interface InvoiceDetailDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  invoice: Invoice | null;
  deliveryNote?: DeliveryNote | null;
  onEdit?: (field: string, value: any) => void;
  onComment?: (message: string) => void;
  onCreditNote?: () => void;
  onPairDeliveryNote?: (deliveryNoteId: string) => void;
  onReOCR?: () => void;
  onExport?: (format: 'pdf' | 'email') => void;
}

const InvoiceDetailDrawer: React.FC<InvoiceDetailDrawerProps> = ({
  isOpen,
  onClose,
  invoice,
  deliveryNote,
  onEdit,
  onComment,
  onCreditNote,
  onPairDeliveryNote,
  onReOCR,
  onExport,
}) => {
  const [activeTab, setActiveTab] = useState<'details' | 'line-items' | 'timeline' | 'comments'>('details');
  const [newComment, setNewComment] = useState('');
  const [isEditing, setIsEditing] = useState(false);
  const [showExportMenu, setShowExportMenu] = useState(false);
  const [showMatchDropdown, setShowMatchDropdown] = useState(false);

  if (!invoice) return null;

  // Mock data for demonstration
  const lineItems: LineItem[] = [
    { name: 'Brake Pads', quantity: 2, unit_price: 45.99, total_price: 91.98 },
    { name: 'Brake Fluid', quantity: 1, unit_price: 12.50, total_price: 12.50 },
    { name: 'Labor', quantity: 1, unit_price: 85.00, total_price: 85.00 },
  ];

  const comments: Comment[] = [
    { id: '1', user: 'John Smith', timestamp: '2024-01-15 14:30', message: 'Invoice processed successfully', type: 'success' },
    { id: '2', user: 'System', timestamp: '2024-01-15 14:25', message: 'OCR confidence: 93%', type: 'info' },
    { id: '3', user: 'Sarah Wilson', timestamp: '2024-01-15 14:35', message: 'Price mismatch detected with delivery note', type: 'warning' },
  ];

  const timeline: StatusTimeline[] = [
    { status: 'Uploaded', timestamp: '2024-01-15 14:20', user: 'John Smith' },
    { status: 'Processing', timestamp: '2024-01-15 14:22', user: 'System' },
    { status: 'Scanned', timestamp: '2024-01-15 14:25', user: 'System' },
    { status: 'Delivery Note Matched', timestamp: '2024-01-15 14:28', user: 'System' },
    { status: 'Price Mismatch Flagged', timestamp: '2024-01-15 14:30', user: 'Sarah Wilson' },
  ];

  // Calculate price mismatch for credit note
  const hasPriceMismatch = invoice.total_amount && deliveryNote && 
    Math.abs((invoice.total_amount || 0) - (deliveryNote?.total_amount || 0)) > 0.01;
  const priceDifference = hasPriceMismatch ? 
    (invoice.total_amount || 0) - (deliveryNote?.total_amount || 0) : 0;

  const handleEdit = (field: string, value: any) => {
    if (onEdit) {
      onEdit(field, value);
    }
  };

  const handleComment = () => {
    if (newComment.trim() && onComment) {
      onComment(newComment);
      setNewComment('');
    }
  };

  const handleExport = (format: 'pdf' | 'email') => {
    if (onExport) {
      onExport(format);
    }
    setShowExportMenu(false);
  };

  const handleReOCR = () => {
    if (onReOCR) {
      onReOCR();
    }
  };

  const handleCreditNote = () => {
    if (onCreditNote) {
      onCreditNote();
    }
  };

  return (
    <>
      {/* Backdrop */}
      {isOpen && (
        <div 
          className="fixed inset-0 bg-black bg-opacity-50 z-40"
          onClick={onClose}
        />
      )}

      {/* Drawer */}
      <div className={`fixed right-0 top-0 h-full w-96 bg-white dark:bg-gray-800 shadow-xl transform transition-transform duration-300 ease-in-out z-50 ${
        isOpen ? 'translate-x-0' : 'translate-x-full'
      }`}>
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-700">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
            Invoice Details
          </h2>
          <div className="flex items-center space-x-2">
            {/* Export Menu */}
            <div className="relative">
              <button
                onClick={() => setShowExportMenu(!showExportMenu)}
                className="text-gray-400 hover:text-blue-600 dark:hover:text-blue-400 transition-colors"
                title="Export invoice"
              >
                📤
              </button>
              {showExportMenu && (
                <div className="absolute right-0 top-8 w-48 bg-white dark:bg-gray-700 rounded-lg shadow-lg border border-gray-200 dark:border-gray-600 py-2 z-10">
                  <button
                    onClick={() => handleExport('pdf')}
                    className="w-full px-4 py-2 text-left text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-600"
                  >
                    📄 Export as PDF
                  </button>
                  <button
                    onClick={() => handleExport('email')}
                    className="w-full px-4 py-2 text-left text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-600"
                  >
                    📧 Copy Email Template
                  </button>
                </div>
              )}
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
        </div>

        {/* Content */}
        <div className="h-full flex flex-col">
          {/* Tabs */}
          <div className="flex border-b border-gray-200 dark:border-gray-700">
            {[
              { id: 'details', label: 'Details', icon: '📄' },
              { id: 'line-items', label: 'Line Items', icon: '📋' },
              { id: 'timeline', label: 'Timeline', icon: '⏱️' },
              { id: 'comments', label: 'Comments', icon: '💬' },
            ].map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id as any)}
                className={`flex-1 px-3 py-2 text-sm font-medium transition-colors ${
                  activeTab === tab.id
                    ? 'text-blue-600 border-b-2 border-blue-600 dark:text-blue-400 dark:border-blue-400'
                    : 'text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-300'
                }`}
              >
                <span className="mr-1">{tab.icon}</span>
                {tab.label}
              </button>
            ))}
          </div>

          {/* Tab Content */}
          <div className="flex-1 overflow-y-auto p-4">
            {activeTab === 'details' && (
              <div className="space-y-4">
                {/* Status and Confidence */}
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                    Status: {invoice.status}
                  </span>
                  <ConfidenceBadge confidence={invoice.confidence || 0} />
                </div>

                {/* Action Buttons */}
                <div className="space-y-2">
                  {/* Re-OCR Button for Low Confidence */}
                  {(invoice.confidence || 0) < 70 && (
                    <button
                      onClick={handleReOCR}
                      className="w-full px-3 py-2 text-sm bg-yellow-600 text-white rounded hover:bg-yellow-700 transition-colors flex items-center justify-center"
                      title="Low confidence — try reprocessing"
                    >
                      🔄 Re-run OCR
                    </button>
                  )}

                  {/* Credit Note Button */}
                  {hasPriceMismatch && (
                    <button
                      onClick={handleCreditNote}
                      className="w-full px-3 py-2 text-sm bg-orange-600 text-white rounded hover:bg-orange-700 transition-colors flex items-center justify-center"
                    >
                      💰 Suggest Credit Note (£{Math.abs(priceDifference).toFixed(2)})
                    </button>
                  )}

                  {/* Manual Match Button */}
                  {!deliveryNote && (
                    <button
                      onClick={() => setShowMatchDropdown(!showMatchDropdown)}
                      className="w-full px-3 py-2 text-sm bg-blue-600 text-white rounded hover:bg-blue-700 transition-colors flex items-center justify-center"
                    >
                      🔗 Match with Delivery Note
                    </button>
                  )}
                </div>

                {/* Basic Information */}
                <div className="space-y-3">
                  <div className="grid grid-cols-2 gap-2">
                    <label className="text-xs text-gray-500 dark:text-gray-400">Invoice Number</label>
                    <div className="text-sm">
                      {isEditing ? (
                        <input
                          type="text"
                          value={invoice.invoice_number || ''}
                          onChange={(e) => handleEdit('invoice_number', e.target.value)}
                          className="w-full px-2 py-1 text-sm border rounded"
                        />
                      ) : (
                        <span className="text-gray-900 dark:text-gray-100">
                          {invoice.invoice_number || 'Not found'}
                        </span>
                      )}
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-2">
                    <label className="text-xs text-gray-500 dark:text-gray-400">Supplier</label>
                    <div className="text-sm">
                      {isEditing ? (
                        <input
                          type="text"
                          value={invoice.supplier_name || ''}
                          onChange={(e) => handleEdit('supplier_name', e.target.value)}
                          className="w-full px-2 py-1 text-sm border rounded"
                        />
                      ) : (
                        <span className="text-gray-900 dark:text-gray-100">
                          {invoice.supplier_name || 'Not found'}
                        </span>
                      )}
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-2">
                    <label className="text-xs text-gray-500 dark:text-gray-400">Date</label>
                    <div className="text-sm">
                      {isEditing ? (
                        <input
                          type="date"
                          value={invoice.invoice_date || ''}
                          onChange={(e) => handleEdit('invoice_date', e.target.value)}
                          className="w-full px-2 py-1 text-sm border rounded"
                        />
                      ) : (
                        <span className="text-gray-900 dark:text-gray-100">
                          {invoice.invoice_date || 'Not found'}
                        </span>
                      )}
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-2">
                    <label className="text-xs text-gray-500 dark:text-gray-400">Total Amount</label>
                    <div className="text-sm">
                      {isEditing ? (
                        <input
                          type="number"
                          step="0.01"
                          value={invoice.total_amount || ''}
                          onChange={(e) => handleEdit('total_amount', parseFloat(e.target.value))}
                          className="w-full px-2 py-1 text-sm border rounded"
                        />
                      ) : (
                        <span className="text-gray-900 dark:text-gray-100 font-medium">
                          £{invoice.total_amount?.toFixed(2) || '0.00'}
                        </span>
                      )}
                    </div>
                  </div>
                </div>

                {/* Edit Toggle */}
                <button
                  onClick={() => setIsEditing(!isEditing)}
                  className="w-full px-3 py-2 text-sm bg-blue-600 text-white rounded hover:bg-blue-700 transition-colors"
                >
                  {isEditing ? 'Save Changes' : 'Edit Details'}
                </button>
              </div>
            )}

            {activeTab === 'line-items' && (
              <div className="space-y-4">
                <h3 className="text-sm font-medium text-gray-900 dark:text-gray-100">
                  Invoice Line Items
                </h3>
                <div className="space-y-2">
                  {lineItems.map((item, index) => (
                    <div key={index} className="p-3 bg-gray-50 dark:bg-gray-700 rounded">
                      <div className="flex justify-between items-start">
                        <div className="flex-1">
                          <div className="font-medium text-sm text-gray-900 dark:text-gray-100">
                            {item.name}
                          </div>
                          <div className="text-xs text-gray-500 dark:text-gray-400">
                            Qty: {item.quantity} × £{item.unit_price.toFixed(2)}
                          </div>
                        </div>
                        <div className="text-sm font-medium text-gray-900 dark:text-gray-100">
                          £{item.total_price.toFixed(2)}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>

                {deliveryNote && (
                  <>
                    <h3 className="text-sm font-medium text-gray-900 dark:text-gray-100 mt-6">
                      Delivery Note Line Items
                    </h3>
                    <div className="text-xs text-gray-500 dark:text-gray-400">
                      Matched delivery note: {deliveryNote.delivery_note_number}
                    </div>
                  </>
                )}
              </div>
            )}

            {activeTab === 'timeline' && (
              <div className="space-y-4">
                <h3 className="text-sm font-medium text-gray-900 dark:text-gray-100">
                  Status Timeline
                </h3>
                <div className="space-y-3">
                  {timeline.map((event, index) => (
                    <div key={index} className="flex items-start space-x-3">
                      <div className="w-2 h-2 bg-blue-500 rounded-full mt-2"></div>
                      <div className="flex-1">
                        <div className="text-sm font-medium text-gray-900 dark:text-gray-100">
                          {event.status}
                        </div>
                        <div className="text-xs text-gray-500 dark:text-gray-400">
                          {event.timestamp} {event.user && `by ${event.user}`}
                        </div>
                        {event.comment && (
                          <div className="text-xs text-gray-600 dark:text-gray-300 mt-1">
                            {event.comment}
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {activeTab === 'comments' && (
              <div className="space-y-4">
                <h3 className="text-sm font-medium text-gray-900 dark:text-gray-100">
                  Comments
                </h3>
                
                {/* Comments List */}
                <div className="space-y-3 max-h-48 overflow-y-auto">
                  {comments.map((comment) => (
                    <div key={comment.id} className="p-3 bg-gray-50 dark:bg-gray-700 rounded">
                      <div className="flex justify-between items-start mb-1">
                        <span className="text-xs font-medium text-gray-900 dark:text-gray-100">
                          {comment.user}
                        </span>
                        <span className="text-xs text-gray-500 dark:text-gray-400">
                          {comment.timestamp}
                        </span>
                      </div>
                      <div className="text-sm text-gray-700 dark:text-gray-300">
                        {comment.message}
                      </div>
                    </div>
                  ))}
                </div>

                {/* Add Comment */}
                <div className="space-y-2">
                  <textarea
                    value={newComment}
                    onChange={(e) => setNewComment(e.target.value)}
                    placeholder="Add a comment..."
                    className="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded resize-none"
                    rows={3}
                  />
                  <button
                    onClick={handleComment}
                    disabled={!newComment.trim()}
                    className="w-full px-3 py-2 text-sm bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                  >
                    Add Comment
                  </button>
                </div>
              </div>
            )}
          </div>

          {/* Sticky Timeline/Activity Bar */}
          <div className="border-t border-gray-200 dark:border-gray-700 p-4 bg-gray-50 dark:bg-gray-700">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <span className="text-xs text-gray-500 dark:text-gray-400">Activity:</span>
                <span className="text-xs font-medium text-gray-900 dark:text-gray-100">
                  {timeline.length} events
                </span>
              </div>
              <div className="flex items-center space-x-2">
                <span className="text-xs text-gray-500 dark:text-gray-400">Comments:</span>
                <span className="text-xs font-medium text-gray-900 dark:text-gray-100">
                  {comments.length}
                </span>
              </div>
            </div>
            {/* Quick Add Comment */}
            <div className="mt-2">
              <input
                type="text"
                placeholder="Quick comment..."
                className="w-full px-2 py-1 text-xs border border-gray-300 dark:border-gray-600 rounded"
                onKeyPress={(e) => {
                  if (e.key === 'Enter' && e.currentTarget.value.trim()) {
                    onComment?.(e.currentTarget.value.trim());
                    e.currentTarget.value = '';
                  }
                }}
              />
            </div>
          </div>
        </div>
      </div>
    </>
  );
};

export default InvoiceDetailDrawer; 