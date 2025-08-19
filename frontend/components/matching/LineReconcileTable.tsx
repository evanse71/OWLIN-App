import React from 'react';
import { LineDiff } from '../../types/matching';

interface LineReconcileTableProps {
  lineDiffs: LineDiff[];
}

const LineReconcileTable: React.FC<LineReconcileTableProps> = ({ lineDiffs }) => {
  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'ok':
        return (
          <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" fill="none" stroke="#16A34A" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-label="OK">
            <path d="M3 7l3 3 5-5"/>
          </svg>
        );
      case 'qty_mismatch':
      case 'price_mismatch':
        return (
          <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" fill="none" stroke="#D97706" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-label="Mismatch">
            <path d="M2 7h10"/>
          </svg>
        );
      case 'missing_on_dn':
      case 'missing_on_inv':
        return (
          <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" fill="none" stroke="#EF4444" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-label="Missing">
            <circle cx="7" cy="7" r="5"/>
          </svg>
        );
      default:
        return null;
    }
  };

  const getCellBackground = (status: string, field: 'qty' | 'price') => {
    if (status === 'qty_mismatch' && field === 'qty') return 'bg-[#FEF3C7]';
    if (status === 'price_mismatch' && field === 'price') return 'bg-[#FCE7F3]';
    if (status.includes('missing')) return 'bg-[#FFE4E6]';
    return 'bg-white';
  };

  return (
    <div className="space-y-4">
      <h5 className="font-medium text-gray-900">Line Item Reconciliation</h5>
      
      <div className="overflow-x-auto">
        <table className="w-full border-collapse">
          <thead>
            <tr className="border-b border-gray-200">
              <th className="text-left p-2 text-sm font-medium text-gray-700">Status</th>
              <th className="text-left p-2 text-sm font-medium text-gray-700">SKU</th>
              <th className="text-left p-2 text-sm font-medium text-gray-700">Description</th>
              <th className="text-left p-2 text-sm font-medium text-gray-700">Qty (Invoice)</th>
              <th className="text-left p-2 text-sm font-medium text-gray-700">Qty (DN)</th>
              <th className="text-left p-2 text-sm font-medium text-gray-700">Price (Invoice)</th>
              <th className="text-left p-2 text-sm font-medium text-gray-700">Price (DN)</th>
              <th className="text-left p-2 text-sm font-medium text-gray-700">Confidence</th>
              <th className="text-left p-2 text-sm font-medium text-gray-700">Actions</th>
            </tr>
          </thead>
          <tbody>
            {lineDiffs.map((lineDiff) => (
              <tr key={lineDiff.id} className="border-b border-gray-100 hover:bg-gray-50">
                <td className="p-2">
                  <div className="flex items-center gap-2">
                    {getStatusIcon(lineDiff.status)}
                    <span className="text-xs font-medium capitalize">{lineDiff.status}</span>
                  </div>
                </td>
                <td className="p-2 text-sm text-gray-900">
                  {lineDiff.invoice_line_id || lineDiff.delivery_line_id || 'N/A'}
                </td>
                <td className="p-2 text-sm text-gray-900">
                  {lineDiff.invoice_line_id ? 'Invoice Item' : 'DN Item'}
                </td>
                <td className={`p-2 text-sm ${getCellBackground(lineDiff.status, 'qty')}`}>
                  {lineDiff.qty_invoice ? `${lineDiff.qty_invoice} ${lineDiff.qty_uom || ''}` : '-'}
                </td>
                <td className={`p-2 text-sm ${getCellBackground(lineDiff.status, 'qty')}`}>
                  {lineDiff.qty_dn ? `${lineDiff.qty_dn} ${lineDiff.qty_uom || ''}` : '-'}
                </td>
                <td className={`p-2 text-sm ${getCellBackground(lineDiff.status, 'price')}`}>
                  {lineDiff.price_invoice ? `£${lineDiff.price_invoice.toFixed(2)}` : '-'}
                </td>
                <td className={`p-2 text-sm ${getCellBackground(lineDiff.status, 'price')}`}>
                  {lineDiff.price_dn ? `£${lineDiff.price_dn.toFixed(2)}` : '-'}
                </td>
                <td className="p-2">
                  <div 
                    className="text-xs px-2 py-1 rounded text-white font-medium"
                    style={{ 
                      backgroundColor: lineDiff.confidence >= 75 ? '#10B981' : 
                                   lineDiff.confidence >= 50 ? '#F59E0B' : '#EF4444' 
                    }}
                  >
                    {Math.round(lineDiff.confidence)}%
                  </div>
                </td>
                <td className="p-2">
                  <div className="flex gap-1">
                    {lineDiff.status === 'qty_mismatch' && (
                      <button className="text-xs px-2 py-1 bg-blue-100 text-blue-700 rounded hover:bg-blue-200">
                        Accept Qty
                      </button>
                    )}
                    {lineDiff.status === 'price_mismatch' && (
                      <button className="text-xs px-2 py-1 bg-blue-100 text-blue-700 rounded hover:bg-blue-200">
                        Accept Price
                      </button>
                    )}
                    {lineDiff.status.includes('missing') && (
                      <button className="text-xs px-2 py-1 bg-gray-100 text-gray-700 rounded hover:bg-gray-200">
                        Write-off
                      </button>
                    )}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      
      {lineDiffs.length === 0 && (
        <div className="text-center py-8 text-gray-500">
          <p>No line items to reconcile</p>
        </div>
      )}
    </div>
  );
};

export default LineReconcileTable; 