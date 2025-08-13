import React from 'react';

interface Invoice {
  id: string;
  filename: string;
  supplier: string;
  invoiceNumber: string;
  invoiceDate: string;
  totalAmount: string;
  type: 'Invoice' | 'Delivery Note' | 'Unknown';
  status: 'Processing' | 'Complete' | 'Error' | 'Matched' | 'Unmatched' | 'Unknown' | 'Scanned';
  confidence?: number;
  numIssues?: number;
  parsedData?: any;
  matchedDocument?: any;
}

interface UnpairedInvoicesPanelProps {
  invoices: Invoice[];
  onManualPair?: (invoice: Invoice) => void;
}

const UnpairedInvoicesPanel: React.FC<UnpairedInvoicesPanelProps> = ({ invoices, onManualPair }) => {
  // Filter for unpaired invoices (not matched, not errored, not processing)
  const unpairedInvoices = invoices.filter(invoice => 
    invoice.status === 'Unmatched' && 
    invoice.type === 'Invoice'
  );
  
  const getStatusIcon = (status: Invoice['status']) => {
    switch (status) {
      case 'Processing':
        return <div className="w-4 h-4 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />;
      case 'Error':
        return <span className="text-red-600">✗</span>;
      case 'Unknown':
        return <span className="text-gray-600">?</span>;
      case 'Matched':
        return <span className="text-green-600">✓</span>;
      default:
        return <span className="text-orange-600">⚠</span>;
    }
  };

  const getStatusColor = (status: Invoice['status']) => {
    switch (status) {
      case 'Processing':
        return 'bg-blue-100 text-blue-800';
      case 'Error':
        return 'bg-red-100 text-red-800';
      case 'Unknown':
        return 'bg-gray-100 text-gray-800';
      case 'Matched':
        return 'bg-green-100 text-green-800';
      default:
        return 'bg-orange-100 text-orange-800';
    }
  };

  const handleManualPair = (invoice: Invoice) => {
    if (onManualPair) {
      onManualPair(invoice);
    }
  };

  return (
    <div className="w-80 bg-white border-l border-gray-200 p-6">
      <div className="sticky top-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
          <span>🧾</span>
          <span>Invoices Waiting to be Paired</span>
          {unpairedInvoices.length > 0 && (
            <span className="bg-orange-100 text-orange-800 text-xs px-2 py-1 rounded-full font-medium">
              {unpairedInvoices.length}
            </span>
          )}
        </h2>

        {invoices.length === 0 ? (
          <div className="text-center py-8">
            <div className="text-gray-400 mb-2">
              <svg className="w-12 h-12 mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
            </div>
            <p className="text-sm text-gray-500 mb-1">No invoices uploaded</p>
            <p className="text-xs text-gray-400">Upload invoices to see them here</p>
          </div>
        ) : unpairedInvoices.length === 0 ? (
          <div className="text-center py-8">
            <div className="text-green-400 mb-2">
              <svg className="w-12 h-12 mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
            <p className="text-sm text-gray-500 mb-1">All invoices are matched</p>
            <p className="text-xs text-gray-400">All invoices have been paired with delivery notes</p>
          </div>
        ) : (
          <div className="space-y-3 max-h-[600px] overflow-y-auto pr-2 scrollbar-thin scrollbar-thumb-gray-300 scrollbar-track-gray-100">
            {unpairedInvoices.map((invoice) => (
              <div
                key={invoice.id}
                className="bg-white/95 backdrop-blur-sm rounded-xl p-4 border border-gray-200 hover:border-gray-300 transition-colors duration-200 cursor-pointer group shadow-sm"
                title="Invoice data has been extracted and is being used in Owlin. Awaiting delivery note to confirm quantities."
              >
                <div className="flex justify-between items-start mb-2">
                  <span className="text-xs text-gray-500 truncate">#{invoice.invoiceNumber}</span>
                  <span className="text-xs text-gray-500 flex-shrink-0 ml-2">{invoice.invoiceDate}</span>
                </div>
                
                <div className="flex justify-between items-start">
                  <div className="flex-1 min-w-0">
                    <h3 className="text-sm font-semibold text-gray-800 truncate">{invoice.supplier}</h3>
                    <p className="text-xs text-gray-600 mt-1 truncate">{invoice.filename}</p>
                  </div>
                  <div className="flex-shrink-0 ml-3">
                    <span
                      className={`text-xs px-2 py-1 rounded-full font-medium flex items-center gap-1 ${getStatusColor(invoice.status)}`}
                    >
                      {getStatusIcon(invoice.status)}
                      Awaiting Delivery Note
                    </span>
                  </div>
                </div>

                {/* Show total amount prominently */}
                <div className="mt-2 flex items-center justify-between">
                  <span className="text-xs text-gray-500">Total Amount:</span>
                  <span className="text-sm font-semibold text-gray-800">💷 {invoice.totalAmount}</span>
                </div>

                {/* Show confidence if available */}
                {invoice.confidence && (
                  <div className="mt-2 flex items-center gap-2">
                    <span className="text-xs text-gray-500">Confidence:</span>
                    <span className={`text-xs font-medium ${
                      invoice.confidence >= 80 ? 'text-green-600' : 
                      invoice.confidence >= 60 ? 'text-yellow-600' : 'text-red-600'
                    }`}>
                      {invoice.confidence}%
                    </span>
                  </div>
                )}

                {/* Show parsed data summary if available */}
                {invoice.parsedData && (
                  <div className="mt-2 p-2 bg-gray-50 rounded-lg border border-gray-200">
                    <div className="text-xs text-gray-600">
                      {invoice.parsedData.total_amount && (
                        <div className="mb-1">
                          <span className="font-medium">Amount:</span> {invoice.parsedData.total_amount}
                        </div>
                      )}
                      {invoice.parsedData.invoice_date && (
                        <div className="mb-1">
                          <span className="font-medium">Date:</span> {invoice.parsedData.invoice_date}
                        </div>
                      )}
                      {invoice.parsedData.currency && (
                        <div className="mb-1">
                          <span className="font-medium">Currency:</span> {invoice.parsedData.currency}
                        </div>
                      )}
                    </div>
                  </div>
                )}

                {/* Manual Pair Button */}
                <div className="mt-3 pt-2 border-t border-gray-200">
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      handleManualPair(invoice);
                    }}
                    className="w-full bg-blue-50 hover:bg-blue-100 text-blue-700 text-xs font-medium py-2 px-3 rounded-md transition-colors duration-200 flex items-center justify-center gap-1 group-hover:bg-blue-100"
                    title="Manually pair this invoice with a delivery note"
                  >
                    <span>🔗</span>
                    Pair Manually
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Footer with summary */}
        <div className="mt-6 pt-4 border-t border-gray-200">
          <div className="text-xs text-gray-500 text-center">
            {invoices.length > 0 ? (
              <>
                <p>Invoices that haven&apos;t been paired with delivery notes</p>
                <p className="mt-1">Click to view details or manually pair</p>
              </>
            ) : (
              <>
                <p>Upload invoices to see them here</p>
                <p className="mt-1">They&apos;ll appear in this panel when unpaired</p>
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default UnpairedInvoicesPanel; 