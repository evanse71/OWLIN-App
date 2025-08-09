import React from 'react';
import { AlertTriangle } from 'lucide-react';

interface LineItem {
  item?: string; // New primary field
  description?: string; // Legacy field
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

interface InvoiceLineItemTableProps {
  items: LineItem[];
  className?: string;
  // VAT calculations for totals
  subtotal?: number;
  vat?: number;
  vat_rate?: number;
  total_incl_vat?: number;
}

const InvoiceLineItemTable: React.FC<InvoiceLineItemTableProps> = ({ 
  items, 
  className = '',
  subtotal,
  vat,
  vat_rate = 0.2,
  total_incl_vat
}) => {
  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-GB', {
      style: 'currency',
      currency: 'GBP',
    }).format(amount);
  };

  const formatQuantity = (quantity: number) => {
    return Number.isInteger(quantity) ? quantity.toString() : quantity.toFixed(2);
  };

  const formatVATRate = (rate: number) => {
    return `${(rate * 100).toFixed(0)}%`;
  };

  // Calculate totals from line items if not provided
  const calculatedSubtotal = subtotal || items.reduce((sum, item) => 
    sum + (item.price_excl_vat || item.line_total_excl_vat || item.total_price || 0), 0);
  
  const calculatedVAT = vat || (calculatedSubtotal * vat_rate);
  const calculatedTotal = total_incl_vat || (calculatedSubtotal + calculatedVAT);

  if (!items || items.length === 0) {
    return (
      <div className={`bg-white rounded-lg border border-slate-200 p-6 text-center ${className}`}>
        <div className="text-slate-400 mb-2">
          <svg className="w-8 h-8 mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
          </svg>
        </div>
        <p className="text-slate-600 mb-1">No line items found</p>
        <p className="text-sm text-slate-500">This invoice may need manual review.</p>
      </div>
    );
  }

  return (
    <div className={`bg-white rounded-lg border border-slate-200 overflow-hidden ${className}`}>
      <table className="w-full">
        <thead className="bg-slate-50">
          <tr>
            <th className="px-4 py-3 text-left text-xs font-medium text-slate-600 uppercase tracking-wider">
              Item Description
            </th>
            <th className="px-4 py-3 text-right text-xs font-medium text-slate-600 uppercase tracking-wider">
              Quantity
            </th>
            <th className="px-4 py-3 text-right text-xs font-medium text-slate-600 uppercase tracking-wider">
              Unit Price (ex. VAT)
            </th>
            <th className="px-4 py-3 text-right text-xs font-medium text-slate-600 uppercase tracking-wider">
              Unit Price (incl. VAT)
            </th>
            <th className="px-4 py-3 text-right text-xs font-medium text-slate-600 uppercase tracking-wider">
              Line Total
            </th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-200">
          {items.map((item, index) => {
            // Use new VAT fields or fall back to legacy fields
            const unitPriceExclVAT = item.unit_price_excl_vat || item.unit_price || 0;
            const unitPriceInclVAT = item.unit_price_incl_vat || (unitPriceExclVAT * (1 + vat_rate));
            const lineTotal = item.line_total_excl_vat || item.total_price || 0;
            const itemName = item.item || item.description || 'Unknown Item';
            
            return (
              <tr
                key={index}
                className={`${item.flagged ? 'bg-red-50' : 'hover:bg-slate-50'} transition-colors`}
              >
                <td className="px-4 py-3 text-sm text-slate-900">
                  <div className="flex items-center">
                    <span className="truncate max-w-xs">{itemName}</span>
                    {item.flagged && (
                      <AlertTriangle className="w-3 h-3 text-red-500 ml-2 flex-shrink-0" />
                    )}
                  </div>
                </td>
                <td className="px-4 py-3 text-sm text-slate-900 text-right font-medium">
                  {formatQuantity(item.quantity)}
                </td>
                <td className="px-4 py-3 text-sm text-slate-900 text-right">
                  {formatCurrency(unitPriceExclVAT)}
                </td>
                <td className="px-4 py-3 text-sm text-slate-900 text-right">
                  {formatCurrency(unitPriceInclVAT)}
                </td>
                <td className="px-4 py-3 text-sm font-medium text-slate-900 text-right">
                  {formatCurrency(lineTotal)}
                </td>
              </tr>
            );
          })}
        </tbody>
        <tfoot className="bg-slate-50">
          <tr className="border-t border-slate-200">
            <td colSpan={4} className="px-4 py-3 text-sm font-medium text-slate-700 text-right">
              Subtotal (ex. VAT)
            </td>
            <td className="px-4 py-3 text-sm font-medium text-slate-900 text-right">
              {formatCurrency(calculatedSubtotal)}
            </td>
          </tr>
          <tr>
            <td colSpan={4} className="px-4 py-2 text-sm font-medium text-slate-700 text-right">
              VAT ({formatVATRate(vat_rate)})
            </td>
            <td className="px-4 py-2 text-sm font-medium text-slate-900 text-right">
              {formatCurrency(calculatedVAT)}
            </td>
          </tr>
          <tr className="border-t border-slate-300 bg-slate-100">
            <td colSpan={4} className="px-4 py-3 text-sm font-bold text-slate-800 text-right">
              Total (incl. VAT)
            </td>
            <td className="px-4 py-3 text-sm font-bold text-slate-900 text-right">
              {formatCurrency(calculatedTotal)}
            </td>
          </tr>
        </tfoot>
      </table>
    </div>
  );
};

export default InvoiceLineItemTable; 