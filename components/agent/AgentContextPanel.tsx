import React, { useState } from 'react';

interface LineItem {
  id: string;
  name: string;
  quantity: number;
  unit_price: number;
  total: number;
  status?: 'flagged' | 'missing' | 'mismatched' | 'normal';
  expected_quantity?: number;
  actual_quantity?: number;
  notes?: string;
}

interface InvoiceData {
  id: string;
  supplier_name: string;
  invoice_number: string;
  invoice_date: string;
  subtotal: number;
  vat: number;
  total: number;
  confidence: number;
  manual_review_required: boolean;
  line_items: LineItem[];
  status: 'pending' | 'reviewed' | 'approved' | 'flagged';
}

interface DeliveryNoteData {
  id: string;
  delivery_number: string;
  delivery_date: string;
  supplier_name: string;
  items: LineItem[];
  matching_status: 'matched' | 'unmatched' | 'partial';
  match_confidence: number;
}

interface AgentContextPanelProps {
  invoiceData: InvoiceData;
  deliveryNote?: DeliveryNoteData;
  isCollapsed?: boolean;
  onToggle?: (collapsed: boolean) => void;
}

const AgentContextPanel: React.FC<AgentContextPanelProps> = ({
  invoiceData,
  deliveryNote,
  isCollapsed = false,
  onToggle
}) => {
  const [showTooltips, setShowTooltips] = useState(false);

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'flagged':
      case 'missing':
      case 'mismatched':
        return 'bg-red-50 border-red-200 text-red-800';
      case 'normal':
        return 'bg-green-50 border-green-200 text-green-800';
      default:
        return 'bg-gray-50 border-gray-200 text-gray-800';
    }
  };

  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 80) return 'bg-green-100 text-green-800';
    if (confidence >= 60) return 'bg-yellow-100 text-yellow-800';
    return 'bg-red-100 text-red-800';
  };

  const getMatchingStatusColor = (status: string) => {
    switch (status) {
      case 'matched':
        return 'bg-green-100 text-green-800';
      case 'partial':
        return 'bg-yellow-100 text-yellow-800';
      case 'unmatched':
        return 'bg-red-100 text-red-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-GB', {
      style: 'currency',
      currency: 'GBP'
    }).format(amount);
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-GB', {
      day: '2-digit',
      month: 'short',
      year: 'numeric'
    });
  };

  const renderTooltip = (text: string) => (
    <div className="group relative">
      <svg className="w-4 h-4 text-gray-400 cursor-help" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
      <div className="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 px-3 py-2 bg-gray-900 text-white text-xs rounded-lg opacity-0 group-hover:opacity-100 transition-opacity duration-200 whitespace-nowrap z-10">
        {text}
        <div className="absolute top-full left-1/2 transform -translate-x-1/2 w-0 h-0 border-l-4 border-r-4 border-t-4 border-transparent border-t-gray-900"></div>
      </div>
    </div>
  );

  if (isCollapsed) {
    return (
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-semibold text-gray-900">Agent Context</h3>
          <button
            onClick={() => onToggle?.(false)}
            className="text-gray-400 hover:text-gray-600 transition-colors"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
            </svg>
          </button>
        </div>
        <div className="mt-2 text-xs text-gray-500">
          {invoiceData.line_items.length} items • {formatCurrency(invoiceData.total)}
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center space-x-2">
          <h3 className="text-sm font-semibold text-gray-900">Agent Context</h3>
          {renderTooltip("This panel shows the invoice data the agent is using to make suggestions")}
        </div>
        <button
          onClick={() => onToggle?.(true)}
          className="text-gray-400 hover:text-gray-600 transition-colors"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 15l7-7 7 7" />
          </svg>
        </button>
      </div>

      {/* Invoice Overview */}
      <div className="mb-4">
        <div className="flex items-center justify-between mb-2">
          <h4 className="text-xs font-medium text-gray-700">Invoice Overview</h4>
          {renderTooltip("Basic invoice information and confidence level")}
        </div>
        <div className="space-y-2 text-xs">
          <div className="flex justify-between">
            <span className="text-gray-600">Supplier:</span>
            <span className="font-medium text-gray-900">{invoiceData.supplier_name}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-600">Invoice #:</span>
            <span className="font-medium text-gray-900">{invoiceData.invoice_number}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-600">Date:</span>
            <span className="font-medium text-gray-900">{formatDate(invoiceData.invoice_date)}</span>
          </div>
          <div className="flex justify-between items-center">
            <span className="text-gray-600">Confidence:</span>
            <span className={`px-2 py-1 rounded-full text-xs font-medium ${getConfidenceColor(invoiceData.confidence)}`}>
              {invoiceData.confidence}%
            </span>
          </div>
          {invoiceData.manual_review_required && (
            <div className="flex justify-between items-center">
              <span className="text-gray-600">Review:</span>
              <span className="px-2 py-1 rounded-full text-xs font-medium bg-yellow-100 text-yellow-800">
                Manual Review Required
              </span>
            </div>
          )}
        </div>
      </div>

      {/* Key Financials */}
      <div className="mb-4">
        <div className="flex items-center justify-between mb-2">
          <h4 className="text-xs font-medium text-gray-700">Key Financials</h4>
          {renderTooltip("Financial breakdown of the invoice")}
        </div>
        <div className="space-y-1 text-xs">
          <div className="flex justify-between">
            <span className="text-gray-600">Subtotal:</span>
            <span className="font-medium text-gray-900">{formatCurrency(invoiceData.subtotal)}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-600">VAT:</span>
            <span className="font-medium text-gray-900">{formatCurrency(invoiceData.vat)}</span>
          </div>
          <div className="flex justify-between border-t border-gray-200 pt-1">
            <span className="text-gray-600 font-medium">Total:</span>
            <span className="font-bold text-gray-900">{formatCurrency(invoiceData.total)}</span>
          </div>
        </div>
      </div>

      {/* Line Items Summary */}
      <div className="mb-4">
        <div className="flex items-center justify-between mb-2">
          <h4 className="text-xs font-medium text-gray-700">Line Items</h4>
          {renderTooltip("Key items from the invoice with any issues highlighted")}
        </div>
        <div className="space-y-2">
          {invoiceData.line_items.slice(0, 5).map((item, index) => (
            <div
              key={item.id || index}
              className={`p-2 rounded border text-xs ${getStatusColor(item.status || 'normal')}`}
            >
              <div className="flex justify-between items-start">
                <div className="flex-1">
                  <div className="font-medium text-gray-900">
                    {item.quantity}x {item.name}
                  </div>
                  <div className="text-gray-600">
                    @ {formatCurrency(item.unit_price)} = {formatCurrency(item.total)}
                  </div>
                  {item.status && item.status !== 'normal' && (
                    <div className="text-xs mt-1">
                      {item.status === 'flagged' && '⚠️ Price discrepancy detected'}
                      {item.status === 'missing' && '❌ Item not received'}
                      {item.status === 'mismatched' && '⚠️ Quantity mismatch'}
                      {item.notes && ` - ${item.notes}`}
                    </div>
                  )}
                </div>
              </div>
            </div>
          ))}
          {invoiceData.line_items.length > 5 && (
            <div className="text-xs text-gray-500 text-center py-1">
              +{invoiceData.line_items.length - 5} more items
            </div>
          )}
        </div>
      </div>

      {/* Delivery Note */}
      {deliveryNote && (
        <div className="mb-4">
          <div className="flex items-center justify-between mb-2">
            <h4 className="text-xs font-medium text-gray-700">Delivery Note</h4>
            {renderTooltip("Matching delivery note information if available")}
          </div>
          <div className="space-y-2 text-xs">
            <div className="flex justify-between">
              <span className="text-gray-600">Delivery #:</span>
              <span className="font-medium text-gray-900">{deliveryNote.delivery_number}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600">Date:</span>
              <span className="font-medium text-gray-900">{formatDate(deliveryNote.delivery_date)}</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-gray-600">Match Status:</span>
              <span className={`px-2 py-1 rounded-full text-xs font-medium ${getMatchingStatusColor(deliveryNote.matching_status)}`}>
                {deliveryNote.matching_status.charAt(0).toUpperCase() + deliveryNote.matching_status.slice(1)}
              </span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-gray-600">Match Confidence:</span>
              <span className={`px-2 py-1 rounded-full text-xs font-medium ${getConfidenceColor(deliveryNote.match_confidence)}`}>
                {deliveryNote.match_confidence}%
              </span>
            </div>
            
            {/* Key delivery items */}
            {deliveryNote.items.length > 0 && (
              <div className="mt-2">
                <div className="text-xs text-gray-600 mb-1">Key Items:</div>
                <div className="space-y-1">
                  {deliveryNote.items.slice(0, 3).map((item, index) => (
                    <div key={index} className="text-xs text-gray-700">
                      {item.quantity}x {item.name}
                    </div>
                  ))}
                  {deliveryNote.items.length > 3 && (
                    <div className="text-xs text-gray-500">
                      +{deliveryNote.items.length - 3} more items
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Footer */}
      <div className="text-xs text-gray-500 text-center pt-2 border-t border-gray-100">
        Data used by Owlin Agent for suggestions
      </div>
    </div>
  );
};

export default AgentContextPanel; 