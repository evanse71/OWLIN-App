import React, { useState, useEffect } from 'react';
import { apiGetInvoice, apiInvoiceLineItems, apiRescanInvoice } from '@/lib/api';
import LineItemsTable from '../LineItemsTable';

interface InvoiceCardEnhancedProps {
  item: {
    id: string;
    pages: number[];
    page_count: number;
  };
}

export default function InvoiceCardEnhanced({ item }: InvoiceCardEnhancedProps) {
  const [invoiceData, setInvoiceData] = useState<any>(null);
  const [lineItems, setLineItems] = useState<any[]>([]);
  const [displayTotal, setDisplayTotal] = useState<number | undefined>();
  const [confidence, setConfidence] = useState<number | undefined>();
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const getPageThumbnailUrl = (invoiceId: string, pageNo: number) => {
    const base = process.env.NEXT_PUBLIC_API_BASE || process.env.NEXT_PUBLIC_API_BASE_URL || "";
    return `${base}/api/invoices/${invoiceId}/pages/${pageNo}/thumb`;
  };

  useEffect(() => {
    loadInvoiceData();
  }, [item.id]);

  const loadInvoiceData = async () => {
    try {
      setIsLoading(true);
      setError(null);
      
      const [invoice, data] = await Promise.all([
        apiGetInvoice(item.id),
        apiInvoiceLineItems(item.id)
      ]);
      
      setInvoiceData(invoice);
      setLineItems(data.items || []);
      
      // Compute display total when total_value is null
      const calc = Array.isArray(data.items) ? data.items.reduce(
        (s: number, li: any) => s + (Number(li.quantity||0) * Number(li.unit_price||0)), 0
      ) : 0;
      const computedTotal = Number.isFinite(Number(invoice?.total_value))
        ? Number(invoice?.total_value) : calc || undefined;
      setDisplayTotal(computedTotal);
      
      // Fallback confidence from line items
      const itemConf = (data.items || [])
        .map((li: any) => Number(li.confidence))
        .filter((n: any) => Number.isFinite(n) && n > 0);
      const computedConf = Number.isFinite(invoice?.confidence) ? invoice?.confidence
        : (itemConf.length ? Math.min(...itemConf) : undefined);
      setConfidence(computedConf);
      
    } catch (error) {
      console.error('Failed to load invoice data:', error);
      setError('Failed to load invoice data');
    } finally {
      setIsLoading(false);
    }
  };

  const handleRescan = async () => {
    try {
      await apiRescanInvoice(item.id);
      await loadInvoiceData();
    } catch (error) {
      console.error('Failed to rescan invoice:', error);
    }
  };

  if (isLoading) {
    return (
      <div className="p-4 border rounded-lg">
        <div className="animate-pulse">
          <div className="h-4 bg-gray-200 rounded w-3/4 mb-2"></div>
          <div className="h-4 bg-gray-200 rounded w-1/2"></div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-4 border rounded-lg border-red-200 bg-red-50">
        <p className="text-red-600">{error}</p>
        <button 
          onClick={loadInvoiceData}
          className="mt-2 px-3 py-1 bg-red-600 text-white rounded text-sm"
        >
          Retry
        </button>
      </div>
    );
  }

  return (
    <div className="p-4 border rounded-lg bg-white shadow-sm">
      <div className="flex items-start justify-between mb-4">
        <div>
          <h3 className="font-semibold text-lg">
            {invoiceData?.supplier || 'Unknown Supplier'}
          </h3>
          <p className="text-sm text-gray-600">
            Invoice #{invoiceData?.reference || item.id}
          </p>
          {invoiceData?.invoice_date && (
            <p className="text-sm text-gray-500">
              {new Date(invoiceData.invoice_date).toLocaleDateString()}
            </p>
          )}
        </div>
        <div className="text-right">
          {displayTotal && (
            <p className="text-lg font-semibold">
              £{displayTotal.toFixed(2)}
            </p>
          )}
          {confidence && (
            <p className="text-sm text-gray-500">
              Confidence: {(confidence * 100).toFixed(1)}%
            </p>
          )}
        </div>
      </div>

      {item.pages && item.pages.length > 0 && (
        <div className="mb-4">
          <img
            className="w-full h-32 object-contain border rounded"
            src={getPageThumbnailUrl(item.id, Math.min(...item.pages))}
            alt={`Invoice ${item.id} page ${Math.min(...item.pages)}`}
          />
        </div>
      )}

      <div className="mb-4">
        <h4 className="font-medium mb-2">Line Items</h4>
        <LineItemsTable
          invoiceId={item.id}
          items={lineItems}
          onChange={loadInvoiceData}
        />
      </div>

      <div className="flex gap-2">
        <button
          onClick={handleRescan}
          className="px-3 py-1 bg-blue-600 text-white rounded text-sm hover:bg-blue-700"
        >
          Rescan
        </button>
        <button
          onClick={loadInvoiceData}
          className="px-3 py-1 bg-gray-600 text-white rounded text-sm hover:bg-gray-700"
        >
          Refresh
        </button>
      </div>
    </div>
  );
}