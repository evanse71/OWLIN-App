import React, { useState } from 'react';
import { Invoice, DeliveryNote } from '@/services/api';
import ConfidenceBadge from '@/components/common/ConfidenceBadge';
import { AlertTriangle, FileText, Calculator, TrendingUp, Eye, EyeOff } from 'lucide-react';

interface LineItem {
  item?: string; // New primary field
  description?: string; // Legacy field
  name?: string; // Legacy field
  quantity: number;
  unit_price?: number; // Legacy field
  total_price?: number; // Legacy field
  unit_price_excl_vat?: number;
  unit_price_incl_vat?: number;
  line_total_excl_vat?: number;
  line_total_incl_vat?: number;
  price_excl_vat?: number;
  price_incl_vat?: number;
  price_per_unit?: number;
  vat_rate?: number;
  flagged?: boolean;
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
  const [showVATBreakdown, setShowVATBreakdown] = useState(true);

  if (!invoice) return null;

  // Use real line items from invoice or fallback to mock data
  const lineItems: LineItem[] = invoice.line_items || [
    { 
      item: 'Brake Pads', 
      quantity: 2, 
      unit_price: 45.99, 
      total_price: 91.98,
      price_excl_vat: 91.98,
      price_incl_vat: 110.38,
      price_per_unit: 55.19,
      vat_rate: 0.2
    },
    { 
      item: 'Brake Fluid', 
      quantity: 1, 
      unit_price: 12.50, 
      total_price: 12.50,
      price_excl_vat: 12.50,
      price_incl_vat: 15.00,
      price_per_unit: 15.00,
      vat_rate: 0.2
    },
    { 
      item: 'Labor', 
      quantity: 1, 
      unit_price: 85.00, 
      total_price: 85.00,
      price_excl_vat: 85.00,
      price_incl_vat: 102.00,
      price_per_unit: 102.00,
      vat_rate: 0.2
    },
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

  // Calculate VAT totals from line items
  const vatTotals = lineItems.reduce((acc, item) => {
    const priceExclVAT = item.price_excl_vat || item.total_price || 0;
    const priceInclVAT = item.price_incl_vat || (priceExclVAT * 1.2);
    const vatAmount = priceInclVAT - priceExclVAT;
    
    return {
      subtotal: acc.subtotal + priceExclVAT,
      vat: acc.vat + vatAmount,
      total: acc.total + priceInclVAT
    };
  }, { subtotal: 0, vat: 0, total: 0 });

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-GB', {
      style: 'currency',
      currency: 'GBP',
    }).format(amount);
  };

  const formatVATRate = (rate: number = 0.2) => {
    return `${(rate * 100).toFixed(0)}%`;
  };

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
    <div className={`fixed inset-y-0 right-0 w-96 bg-white dark:bg-gray-800 shadow-xl transform transition-transform duration-300 ease-in-out ${isOpen ? 'translate-x-0' : 'translate-x-full'} z-50`}>
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-700">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
          Invoice Details
        </h2>
        <button
          onClick={onClose}
          className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
        >
          ✕
        </button>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-gray-200 dark:border-gray-700">
        {[
          { id: 'details', label: 'Details', icon: '📋' },
          { id: 'line-items', label: 'Line Items', icon: '📄' },
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
                      {formatCurrency(invoice.total_amount || 0)}
                    </span>
                  )}
                </div>
              </div>

              {/* VAT Information */}
              {invoice.subtotal && invoice.vat && (
                <div className="bg-blue-50 dark:bg-blue-900/20 rounded-lg p-3 space-y-2">
                  <div className="flex items-center text-sm font-medium text-blue-900 dark:text-blue-100">
                    <Calculator className="w-4 h-4 mr-2" />
                    VAT Breakdown
                  </div>
                  <div className="grid grid-cols-2 gap-2 text-xs">
                    <span className="text-gray-600 dark:text-gray-400">Subtotal (ex. VAT):</span>
                    <span className="text-gray-900 dark:text-gray-100 font-medium">
                      {formatCurrency(invoice.subtotal)}
                    </span>
                    <span className="text-gray-600 dark:text-gray-400">VAT ({formatVATRate(invoice.vat_rate)}):</span>
                    <span className="text-gray-900 dark:text-gray-100 font-medium">
                      {formatCurrency(invoice.vat)}
                    </span>
                    <span className="text-gray-600 dark:text-gray-400">Total (incl. VAT):</span>
                    <span className="text-gray-900 dark:text-gray-100 font-medium">
                      {formatCurrency(invoice.total_incl_vat || invoice.total_amount || 0)}
                    </span>
                  </div>
                </div>
              )}
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
            {/* Header with VAT Toggle */}
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-medium text-gray-900 dark:text-gray-100 flex items-center">
                <FileText className="w-4 h-4 mr-2" />
                Invoice Line Items
                <span className="ml-2 text-xs text-gray-500">
                  ({lineItems.length} items)
                </span>
              </h3>
              <button
                onClick={() => setShowVATBreakdown(!showVATBreakdown)}
                className="flex items-center text-xs text-blue-600 hover:text-blue-700 dark:text-blue-400"
              >
                {showVATBreakdown ? <EyeOff className="w-3 h-3 mr-1" /> : <Eye className="w-3 h-3 mr-1" />}
                {showVATBreakdown ? 'Hide VAT' : 'Show VAT'}
              </button>
            </div>

            {/* Line Items Table */}
            {lineItems.length > 0 ? (
              <div className="space-y-3">
                {/* Desktop Table */}
                <div className="hidden md:block">
                  <div className="bg-gray-50 dark:bg-gray-700 rounded-lg overflow-hidden">
                    <table className="w-full text-xs">
                      <thead className="bg-gray-100 dark:bg-gray-600">
                        <tr>
                          <th className="px-3 py-2 text-left font-medium text-gray-700 dark:text-gray-300">
                            Item
                          </th>
                          <th className="px-3 py-2 text-right font-medium text-gray-700 dark:text-gray-300">
                            Qty
                          </th>
                          {showVATBreakdown && (
                            <>
                              <th className="px-3 py-2 text-right font-medium text-gray-700 dark:text-gray-300">
                                Unit (ex. VAT)
                              </th>
                              <th className="px-3 py-2 text-right font-medium text-gray-700 dark:text-gray-300">
                                Unit (incl. VAT)
                              </th>
                            </>
                          )}
                          <th className="px-3 py-2 text-right font-medium text-gray-700 dark:text-gray-300">
                            Total
                          </th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-gray-200 dark:divide-gray-600">
                        {lineItems.map((item, index) => {
                          const itemName = item.item || item.description || item.name || 'Unknown Item';
                          const unitPriceExclVAT = item.unit_price_excl_vat || item.unit_price || 0;
                          const unitPriceInclVAT = item.unit_price_incl_vat || (unitPriceExclVAT * 1.2);
                          const lineTotal = item.price_excl_vat || item.line_total_excl_vat || item.total_price || 0;
                          const lineTotalInclVAT = item.price_incl_vat || item.line_total_incl_vat || (lineTotal * 1.2);
                          
                          return (
                            <tr key={index} className={`${item.flagged ? 'bg-red-50 dark:bg-red-900/20' : 'hover:bg-gray-100 dark:hover:bg-gray-600'}`}>
                              <td className="px-3 py-2 text-gray-900 dark:text-gray-100">
                                <div className="flex items-center">
                                  <span className="truncate max-w-32">{itemName}</span>
                                  {item.flagged && (
                                    <AlertTriangle className="w-3 h-3 text-red-500 ml-1 flex-shrink-0" />
                                  )}
                                </div>
                              </td>
                              <td className="px-3 py-2 text-right text-gray-900 dark:text-gray-100 font-medium">
                                {item.quantity}
                              </td>
                              {showVATBreakdown && (
                                <>
                                  <td className="px-3 py-2 text-right text-gray-600 dark:text-gray-400">
                                    {formatCurrency(unitPriceExclVAT)}
                                  </td>
                                  <td className="px-3 py-2 text-right text-gray-600 dark:text-gray-400">
                                    {formatCurrency(unitPriceInclVAT)}
                                  </td>
                                </>
                              )}
                              <td className="px-3 py-2 text-right text-gray-900 dark:text-gray-100 font-medium">
                                {formatCurrency(showVATBreakdown ? lineTotalInclVAT : lineTotal)}
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                      <tfoot className="bg-gray-100 dark:bg-gray-600">
                        <tr className="border-t border-gray-200 dark:border-gray-500">
                          <td colSpan={showVATBreakdown ? 2 : 1} className="px-3 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 text-right">
                            Subtotal (ex. VAT):
                          </td>
                          <td className="px-3 py-2 text-sm font-medium text-gray-900 dark:text-gray-100 text-right">
                            {formatCurrency(vatTotals.subtotal)}
                          </td>
                        </tr>
                        {showVATBreakdown && (
                          <>
                            <tr>
                              <td colSpan={3} className="px-3 py-1 text-xs font-medium text-gray-700 dark:text-gray-300 text-right">
                                VAT ({formatVATRate()}):
                              </td>
                              <td className="px-3 py-1 text-xs font-medium text-gray-900 dark:text-gray-100 text-right">
                                {formatCurrency(vatTotals.vat)}
                              </td>
                            </tr>
                            <tr className="border-t border-gray-200 dark:border-gray-500">
                              <td colSpan={3} className="px-3 py-2 text-sm font-bold text-gray-900 dark:text-gray-100 text-right">
                                Total (incl. VAT):
                              </td>
                              <td className="px-3 py-2 text-sm font-bold text-gray-900 dark:text-gray-100 text-right">
                                {formatCurrency(vatTotals.total)}
                              </td>
                            </tr>
                          </>
                        )}
                      </tfoot>
                    </table>
                  </div>
                </div>

                {/* Mobile Cards */}
                <div className="md:hidden space-y-3">
                  {lineItems.map((item, index) => {
                    const itemName = item.item || item.description || item.name || 'Unknown Item';
                    const unitPriceExclVAT = item.unit_price_excl_vat || item.unit_price || 0;
                    const unitPriceInclVAT = item.unit_price_incl_vat || (unitPriceExclVAT * 1.2);
                    const lineTotal = item.price_excl_vat || item.line_total_excl_vat || item.total_price || 0;
                    const lineTotalInclVAT = item.price_incl_vat || item.line_total_incl_vat || (lineTotal * 1.2);
                    
                    return (
                      <div key={index} className={`p-3 rounded-lg border ${item.flagged ? 'bg-red-50 border-red-200 dark:bg-red-900/20 dark:border-red-700' : 'bg-gray-50 border-gray-200 dark:bg-gray-700 dark:border-gray-600'}`}>
                        <div className="flex justify-between items-start mb-2">
                          <div className="flex-1">
                            <div className="font-medium text-sm text-gray-900 dark:text-gray-100 flex items-center">
                              {itemName}
                              {item.flagged && (
                                <AlertTriangle className="w-3 h-3 text-red-500 ml-2" />
                              )}
                            </div>
                            <div className="text-xs text-gray-500 dark:text-gray-400">
                              Qty: {item.quantity}
                            </div>
                          </div>
                          <div className="text-sm font-medium text-gray-900 dark:text-gray-100">
                            {formatCurrency(showVATBreakdown ? lineTotalInclVAT : lineTotal)}
                          </div>
                        </div>
                        
                        {showVATBreakdown && (
                          <div className="grid grid-cols-2 gap-2 text-xs text-gray-600 dark:text-gray-400">
                            <div>
                              <span>Unit (ex. VAT):</span>
                              <div className="font-medium text-gray-900 dark:text-gray-100">
                                {formatCurrency(unitPriceExclVAT)}
                              </div>
                            </div>
                            <div>
                              <span>Unit (incl. VAT):</span>
                              <div className="font-medium text-gray-900 dark:text-gray-100">
                                {formatCurrency(unitPriceInclVAT)}
                              </div>
                            </div>
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>

                {/* VAT Summary */}
                {showVATBreakdown && (
                  <div className="bg-blue-50 dark:bg-blue-900/20 rounded-lg p-3">
                    <div className="flex items-center text-sm font-medium text-blue-900 dark:text-blue-100 mb-2">
                      <TrendingUp className="w-4 h-4 mr-2" />
                      VAT Summary
                    </div>
                    <div className="grid grid-cols-2 gap-2 text-xs">
                      <div>
                        <span className="text-gray-600 dark:text-gray-400">Subtotal (ex. VAT):</span>
                        <div className="font-medium text-gray-900 dark:text-gray-100">
                          {formatCurrency(vatTotals.subtotal)}
                        </div>
                      </div>
                      <div>
                        <span className="text-gray-600 dark:text-gray-400">VAT ({formatVATRate()}):</span>
                        <div className="font-medium text-gray-900 dark:text-gray-100">
                          {formatCurrency(vatTotals.vat)}
                        </div>
                      </div>
                      <div className="col-span-2">
                        <span className="text-gray-600 dark:text-gray-400">Total (incl. VAT):</span>
                        <div className="font-bold text-gray-900 dark:text-gray-100">
                          {formatCurrency(vatTotals.total)}
                        </div>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <div className="text-center py-8">
                <FileText className="w-12 h-12 text-gray-400 mx-auto mb-3" />
                <p className="text-gray-600 dark:text-gray-400 mb-1">No line items found</p>
                <p className="text-sm text-gray-500 dark:text-gray-500">This invoice may need manual review.</p>
              </div>
            )}

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
              Comments & Notes
            </h3>
            
            {/* Add Comment */}
            <div className="space-y-2">
              <textarea
                value={newComment}
                onChange={(e) => setNewComment(e.target.value)}
                placeholder="Add a comment or note about this invoice..."
                className="w-full p-3 text-sm border border-gray-300 dark:border-gray-600 rounded-lg resize-none focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent dark:bg-gray-700 dark:text-gray-100"
                rows={3}
              />
              <button
                onClick={handleComment}
                disabled={!newComment.trim()}
                className="w-full px-3 py-2 text-sm bg-blue-600 text-white rounded hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Add Comment
              </button>
            </div>

            {/* Comments List */}
            <div className="space-y-3">
              {comments.map((comment) => (
                <div key={comment.id} className="p-3 bg-gray-50 dark:bg-gray-700 rounded-lg">
                  <div className="flex justify-between items-start mb-2">
                    <span className="text-sm font-medium text-gray-900 dark:text-gray-100">
                      {comment.user}
                    </span>
                    <span className="text-xs text-gray-500 dark:text-gray-400">
                      {comment.timestamp}
                    </span>
                  </div>
                  <p className="text-sm text-gray-700 dark:text-gray-300">
                    {comment.message}
                  </p>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default InvoiceDetailDrawer; 