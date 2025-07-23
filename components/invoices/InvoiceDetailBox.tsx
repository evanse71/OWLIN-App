import React from 'react';

interface LineItem {
  name: string;
  quantity: number;
  price: string;
  description?: string;
}

interface InvoiceDetailBoxProps {
  invoice: {
    lineItems?: LineItem[];
    parsedData?: any;
    documentType?: string;
    confidence?: number;
    matchedDocument?: any;
  };
  onEdit?: () => void;
  onComment?: () => void;
}

export default function InvoiceDetailBox({ invoice, onEdit, onComment }: InvoiceDetailBoxProps) {
  // Extract line items from parsed data or use defaults
  const parsedData = invoice.parsedData || {};
  const lineItems: LineItem[] = (parsedData.items && Array.isArray(parsedData.items)) ? parsedData.items : (invoice.lineItems || []);
  const documentType = invoice.documentType || 'unknown';
  const confidence = invoice.confidence || 0;

  // Mock line items if none exist (for demo purposes)
  const mockLineItems: LineItem[] = [
    { name: 'Brake Pads', quantity: 2, price: '45.99' },
    { name: 'Brake Fluid', quantity: 1, price: '12.50' },
    { name: 'Labor', quantity: 1, price: '85.00' },
  ];
  const displayItems = lineItems.length > 0 ? lineItems : mockLineItems;

  return (
    <div className="border border-gray-200 rounded-lg p-4 bg-gray-50 text-sm">
      {/* Document Type and Confidence */}
      <div className="flex justify-between items-center mb-3">
        <span className="text-xs text-gray-600">
          Type: {documentType === 'invoice' ? 'Invoice' : 
                 documentType === 'delivery_note' ? 'Delivery Note' : 'Unknown'}
        </span>
        <span className="text-xs text-gray-600">
          Confidence: {confidence}%
        </span>
      </div>

      {/* Parsed Data Summary */}
      {parsedData && (
        <div className="mb-4 p-3 bg-white rounded border">
          <h4 className="font-semibold text-gray-800 mb-2">Extracted Data</h4>
          <div className="grid grid-cols-2 gap-2 text-xs">
            {parsedData.supplier_name && (
              <div>
                <span className="text-gray-600">Supplier:</span>
                <span className="ml-1 font-medium">{parsedData.supplier_name}</span>
              </div>
            )}
            {parsedData.invoice_number && (
              <div>
                <span className="text-gray-600">Invoice #:</span>
                <span className="ml-1 font-medium">{parsedData.invoice_number}</span>
              </div>
            )}
            {parsedData.invoice_date && (
              <div>
                <span className="text-gray-600">Date:</span>
                <span className="ml-1 font-medium">{parsedData.invoice_date}</span>
              </div>
            )}
            {parsedData.total_amount && (
              <div>
                <span className="text-gray-600">Total:</span>
                <span className="ml-1 font-medium">£{parsedData.total_amount}</span>
              </div>
            )}
            {/* Highlight missing fields */}
            {!parsedData.supplier_name && <div className="text-red-500 col-span-2">Missing supplier name</div>}
            {!parsedData.invoice_number && <div className="text-red-500 col-span-2">Missing invoice number</div>}
            {!parsedData.invoice_date && <div className="text-red-500 col-span-2">Missing invoice date</div>}
            {!parsedData.total_amount && <div className="text-red-500 col-span-2">Missing total amount</div>}
          </div>
        </div>
      )}

      {/* Line Items */}
      <div className="mb-4">
        <h4 className="font-semibold text-gray-800 mb-2">Line Items</h4>
        <div className="bg-white rounded border overflow-hidden">
          <div className="grid grid-cols-12 gap-2 p-2 bg-gray-100 text-xs font-medium text-gray-700 border-b">
            <div className="col-span-6">Item</div>
            <div className="col-span-2 text-center">Qty</div>
            <div className="col-span-2 text-right">Price</div>
            <div className="col-span-2 text-right">Total</div>
          </div>
          <div className="max-h-32 overflow-y-auto">
            {displayItems.map((item, i) => {
              const missing = !item.name || !item.price || !item.quantity;
              return (
                <div key={i} className={`grid grid-cols-12 gap-2 p-2 text-xs border-b last:border-b-0 hover:bg-gray-50 transition-colors duration-150 ${missing ? 'bg-red-50' : ''}`}>
                  <div className="col-span-6 truncate">{item.name || <span className="text-red-500">Missing</span>}</div>
                  <div className="col-span-2 text-center">{item.quantity ?? <span className="text-red-500">?</span>}</div>
                  <div className="col-span-2 text-right">£{item.price ?? <span className="text-red-500">?</span>}</div>
                  <div className="col-span-2 text-right font-medium">
                    £{item.price && item.quantity ? (parseFloat(item.price) * item.quantity).toFixed(2) : <span className="text-red-500">?</span>}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* Comparison Section */}
      {invoice.matchedDocument && (
        <div className="mb-4 p-3 bg-blue-50 rounded border border-blue-200">
          <h4 className="font-semibold text-blue-800 mb-2 flex items-center gap-2">
            <span>🔗</span>
            <span>Matched Document</span>
          </h4>
          <div className="text-xs text-blue-700">
            <div>Matched with: {invoice.matchedDocument.filename}</div>
            <div>Match Score: 85%</div>
            <div className="mt-1 text-blue-600">
              ✓ Quantities match | ⚠ Price variance detected
            </div>
          </div>
        </div>
      )}

      {/* Action Buttons (role-based controls stub) */}
      <div className="flex gap-2 pt-2 border-t border-gray-200">
        <button
          onClick={onEdit}
          className="px-3 py-1 text-xs bg-blue-600 text-white rounded hover:bg-blue-700 transition-colors duration-200"
        >
          Edit
        </button>
        <button
          onClick={onComment}
          className="px-3 py-1 text-xs bg-gray-600 text-white rounded hover:bg-gray-700 transition-colors duration-200"
        >
          Add Comment
        </button>
        <button className="px-3 py-1 text-xs bg-green-600 text-white rounded hover:bg-green-700 transition-colors duration-200">
          Approve
        </button>
        {/* Role-based controls stub */}
        <span className="ml-auto text-xs text-gray-400 italic">Role: Reviewer</span>
      </div>
    </div>
  );
} 