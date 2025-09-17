import React, { useState, useEffect } from 'react';
import { apiGetInvoice, apiInvoiceLineItems, apiRescanInvoice, getPageThumbnailUrl } from '@/lib/api';
import LineItemsTable from './LineItemsTable';

interface InvoiceCardEnhancedProps {
  item: {
    id: string;
    pages: number[];
    page_count: number;
  };
}

export default function InvoiceCardEnhanced({ item }: InvoiceCardEnhancedProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const [invoiceData, setInvoiceData] = useState<any>(null);
  const [lineItems, setLineItems] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isRescanning, setIsRescanning] = useState(false);
  const [displayTotal, setDisplayTotal] = useState<number | undefined>(undefined);
  const [confidence, setConfidence] = useState<number | undefined>(undefined);

  const loadInvoiceData = async () => {
    if (invoiceData) return; // Already loaded
    
    setIsLoading(true);
    try {
      const data = await apiGetInvoice(item.id);
      setInvoiceData(data);
    } catch (error) {
      console.error('Failed to load invoice data:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const loadLineItems = async () => {
    setIsLoading(true);
    try {
      const data = await apiInvoiceLineItems(item.id);
      setLineItems(data.items || []);
      
      // Compute display total when total_value is null
      const calc = Array.isArray(data.items) ? data.items.reduce(
        (s, li) => s + (Number(li.quantity||0) * Number(li.unit_price||0)), 0
      ) : 0;
      const computedTotal = Number.isFinite(Number(invoiceData?.total_value))
        ? Number(invoiceData?.total_value) : calc || undefined;
      setDisplayTotal(computedTotal);
      
      // Fallback confidence from line items
      const itemConf = (data.items || [])
        .map(li => Number(li.confidence))
        .filter(n => Number.isFinite(n) && n > 0);
      const computedConf = Number.isFinite(invoiceData?.confidence) ? invoiceData?.confidence
        : (itemConf.length ? Math.min(...itemConf) : undefined);
      setConfidence(computedConf);
      
    } catch (error) {
      console.error('Failed to load line items:', error);
      setLineItems([]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleRescan = async () => {
    setIsRescanning(true);
    try {
      await apiRescanInvoice(item.id);
      // Reload line items after rescan
      await loadLineItems();
    } catch (error) {
      console.error('Failed to rescan invoice:', error);
    } finally {
      setIsRescanning(false);
    }
  };

  const handleLineItemsChange = () => {
    loadLineItems();
  };

  useEffect(() => {
    let alive = true;
    apiGetInvoice(item.id).then(v => { if (alive) setInvoiceData(v); }).catch(()=>{});
    return () => { alive = false; };
  }, [item.id]);

  useEffect(() => {
    if (isExpanded) {
      loadLineItems();
    }
  }, [isExpanded]);

  function formatPages(pages: number[], count: number) {
    if (count === 0) return "—";
    const uniqSorted = [...new Set(pages)].sort((a,b)=>a-b).map(n=>n+1);
    return uniqSorted.length === 1
      ? `${uniqSorted[0]}`
      : `${uniqSorted[0]}–${uniqSorted[uniqSorted.length-1]}`;
  }

  return (
    <div className="border rounded-lg p-4 mb-4 bg-white shadow-sm hover:shadow-md transition-shadow">
      {/* Header */}
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="font-medium truncate">{invoiceData?.supplier ?? "Unknown"}</div>
          <div className="text-xs text-gray-500 truncate">
            {invoiceData?.invoice_date ?? "—"} · Pages {formatPages(item.pages ?? [], item.page_count ?? 0)}
          </div>
        </div>
        <div className="flex items-center gap-3">
          {displayTotal !== undefined && (
            <span className="font-semibold">
              {invoiceData?.total_value ? `£${displayTotal.toFixed(2)}` : `≈ £${displayTotal.toFixed(2)}`}
            </span>
          )}
          {confidence !== undefined && (
            <span className="inline-flex items-center rounded-full px-2 py-0.5 text-xs bg-blue-50 text-blue-600">
              {Math.round(confidence*100)}%
            </span>
          )}
          {item.pages.length > 0 && (
            <img 
              src={getPageThumbnailUrl(item.id, Math.min(...item.pages))} 
              alt="" 
              height={64} 
              onError={(e)=>{ (e.currentTarget as HTMLImageElement).style.display='none'; }}
            />
          )}
        </div>
        
        <div className="flex items-center gap-2">
          <button
            onClick={handleRescan}
            disabled={isRescanning}
            className="px-3 py-1 text-xs bg-yellow-100 text-yellow-800 rounded hover:bg-yellow-200 disabled:opacity-50"
          >
            {isRescanning ? 'Rescanning...' : 'Rescan (OCR)'}
          </button>
          
          <button
            onClick={() => setIsExpanded(!isExpanded)}
            className="px-3 py-1 text-xs bg-blue-100 text-blue-800 rounded hover:bg-blue-200"
          >
            {isExpanded ? 'Collapse' : 'Expand'}
          </button>
        </div>
      </div>

      {/* Expanded Content */}
      {isExpanded && (
        <div className="border-t pt-4">
          {isLoading ? (
            <div className="text-center py-4 text-gray-500">
              Loading invoice details...
            </div>
          ) : (
            <div className="space-y-4">
              {/* Invoice Summary */}
              {invoiceData && (
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                  <div>
                    <div className="text-gray-500">Total</div>
                    <div className="font-medium">
                      {invoiceData.total ? `£${parseFloat(invoiceData.total).toFixed(2)}` : '—'}
                    </div>
                  </div>
                  <div>
                    <div className="text-gray-500">VAT</div>
                    <div className="font-medium">
                      {invoiceData.vat ? `£${parseFloat(invoiceData.vat).toFixed(2)}` : '—'}
                    </div>
                  </div>
                  <div>
                    <div className="text-gray-500">Subtotal</div>
                    <div className="font-medium">
                      {invoiceData.subtotal ? `£${parseFloat(invoiceData.subtotal).toFixed(2)}` : '—'}
                    </div>
                  </div>
                  <div>
                    <div className="text-gray-500">Status</div>
                    <div className="font-medium">
                      {invoiceData.status || 'Unknown'}
                    </div>
                  </div>
                </div>
              )}

              {/* Line Items */}
              <div>
                <h4 className="font-medium mb-2">Line Items</h4>
                {lineItems.length > 0 ? (
                  <LineItemsTable
                    invoiceId={item.id}
                    items={lineItems}
                    onChange={handleLineItemsChange}
                  />
                ) : (
                  <div className="text-gray-500 text-sm py-2">
                    No line items found. Try rescanning the invoice.
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
