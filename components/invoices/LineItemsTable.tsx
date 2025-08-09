import React, { useState, useRef, useEffect } from 'react';
import { 
  AlertTriangle, 
  CheckCircle, 
  Edit3, 
  X,
  Calculator,
  DollarSign
} from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { cn } from '@/lib/utils';

export interface LineItem {
  id?: string;
  description: string;
  quantity: number;
  unit: string;
  unit_price: number;
  vat_rate: number;
  line_total: number;
  page: number;
  row_idx: number;
  confidence: number;
  flags: string[];
}

interface LineItemsTableProps {
  lineItems: LineItem[];
  onLineItemUpdate: (rowIndex: number, field: keyof LineItem, value: any) => void;
  totals: { subtotal: number; vat: number; total: number };
  hasMismatch: boolean;
  className?: string;
}

const LineItemsTable: React.FC<LineItemsTableProps> = ({
  lineItems,
  onLineItemUpdate,
  totals,
  hasMismatch,
  className
}) => {
  const [editingCell, setEditingCell] = useState<{ row: number; field: keyof LineItem } | null>(null);
  const [editValue, setEditValue] = useState<string>('');
  const inputRef = useRef<HTMLInputElement>(null);

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-GB', {
      style: 'currency',
      currency: 'GBP',
    }).format(amount);
  };

  const formatNumber = (num: number) => {
    return num.toString();
  };

  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 0.8) return 'border-green-300 bg-green-50';
    if (confidence >= 0.6) return 'border-yellow-300 bg-yellow-50';
    return 'border-red-300 bg-red-50';
  };

  const getFlagColor = (flag: string) => {
    switch (flag) {
      case 'needs_check': return 'bg-yellow-100 text-yellow-800';
      case 'unit?': return 'bg-blue-100 text-blue-800';
      case 'qty_suspicious': return 'bg-orange-100 text-orange-800';
      case 'vat_missing': return 'bg-red-100 text-red-800';
      case 'sum_mismatch': return 'bg-purple-100 text-purple-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  const startEditing = (row: number, field: keyof LineItem, currentValue: any) => {
    setEditingCell({ row, field });
    setEditValue(currentValue?.toString() || '');
  };

  const saveEdit = () => {
    if (editingCell) {
      const { row, field } = editingCell;
      let parsedValue: any = editValue;

      // Parse value based on field type
      if (field === 'quantity' || field === 'unit_price' || field === 'vat_rate') {
        parsedValue = parseFloat(editValue) || 0;
      } else if (field === 'page' || field === 'row_idx') {
        parsedValue = parseInt(editValue) || 0;
      }

      onLineItemUpdate(row, field, parsedValue);
      setEditingCell(null);
      setEditValue('');
    }
  };

  const cancelEdit = () => {
    setEditingCell(null);
    setEditValue('');
  };

  const handleKeyPress = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      saveEdit();
    } else if (e.key === 'Escape') {
      cancelEdit();
    }
  };

  useEffect(() => {
    if (editingCell && inputRef.current) {
      inputRef.current.focus();
      inputRef.current.select();
    }
  }, [editingCell]);

  const renderCell = (item: LineItem, field: keyof LineItem, rowIndex: number) => {
    const isEditing = editingCell?.row === rowIndex && editingCell?.field === field;
    const value = item[field];
    const confidence = item.confidence;

    if (isEditing) {
      return (
        <Input
          ref={inputRef}
          value={editValue}
          onChange={(e) => setEditValue(e.target.value)}
          onKeyDown={handleKeyPress}
          onBlur={saveEdit}
          className="h-8 text-sm"
          type={field === 'quantity' || field === 'unit_price' || field === 'vat_rate' ? 'number' : 'text'}
          step={field === 'vat_rate' ? '0.01' : '1'}
          min="0"
        />
      );
    }

    const cellContent = () => {
      switch (field) {
        case 'description':
          return (
            <div className="flex items-center justify-between">
              <span className="flex-1">{value}</span>
              {confidence < 0.6 && (
                <AlertTriangle className="w-3 h-3 text-yellow-500 ml-1" />
              )}
            </div>
          );
        case 'quantity':
        case 'unit_price':
        case 'vat_rate':
          return formatNumber(value as number);
        case 'line_total':
          return formatCurrency(value as number);
        case 'page':
        case 'row_idx':
          return value?.toString() || '-';
        default:
          return value?.toString() || '';
      }
    };

    return (
      <div 
        className={cn(
          "cursor-pointer hover:bg-gray-50 p-2 rounded transition-colors",
          confidence < 0.6 && getConfidenceColor(confidence)
        )}
        onClick={() => startEditing(rowIndex, field, value)}
      >
        <div className="flex items-center justify-between">
          {cellContent()}
          <Edit3 className="w-3 h-3 text-gray-400 opacity-0 group-hover:opacity-100 transition-opacity" />
        </div>
        {confidence < 0.8 && (
          <div className="text-xs text-gray-500 mt-1">
            Confidence: {Math.round(confidence * 100)}%
          </div>
        )}
      </div>
    );
  };

  return (
    <div className={cn("bg-white rounded-lg border border-gray-200 overflow-hidden", className)}>
      {/* Header */}
      <div className="bg-gray-50 px-4 py-3 border-b border-gray-200">
        <div className="flex items-center justify-between">
          <h4 className="font-medium text-gray-900">Line Items ({lineItems.length})</h4>
          {hasMismatch && (
            <Badge className="bg-red-100 text-red-800" variant="outline">
              <AlertTriangle className="w-3 h-3 mr-1" />
              Total Mismatch
            </Badge>
          )}
        </div>
      </div>

      {/* Table */}
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Item / Description
              </th>
              <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                QTY
              </th>
              <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                Unit
              </th>
              <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                Unit Price
              </th>
              <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                VAT %
              </th>
              <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                Line Total
              </th>
              <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                Page
              </th>
              <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                Row
              </th>
              <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                Flags
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200">
            {lineItems.map((item, index) => (
              <tr key={item.id || index} className="group hover:bg-gray-50">
                <td className="px-4 py-3">
                  {renderCell(item, 'description', index)}
                </td>
                <td className="px-4 py-3 text-right">
                  {renderCell(item, 'quantity', index)}
                </td>
                <td className="px-4 py-3 text-right">
                  {renderCell(item, 'unit', index)}
                </td>
                <td className="px-4 py-3 text-right">
                  {renderCell(item, 'unit_price', index)}
                </td>
                <td className="px-4 py-3 text-right">
                  {renderCell(item, 'vat_rate', index)}
                </td>
                <td className="px-4 py-3 text-right font-medium">
                  {renderCell(item, 'line_total', index)}
                </td>
                <td className="px-4 py-3 text-center">
                  {renderCell(item, 'page', index)}
                </td>
                <td className="px-4 py-3 text-center">
                  {renderCell(item, 'row_idx', index)}
                </td>
                <td className="px-4 py-3 text-center">
                  <div className="flex flex-wrap gap-1 justify-center">
                    {item.flags?.map((flag, flagIndex) => (
                      <Badge key={flagIndex} className={getFlagColor(flag)} variant="outline">
                        {flag.replace('_', ' ')}
                      </Badge>
                    ))}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Footer with Totals */}
      <div className="bg-gray-50 px-4 py-3 border-t border-gray-200">
        <div className="flex justify-between items-center">
          <div className="flex items-center space-x-6">
            <div className="flex items-center space-x-2">
              <span className="text-sm font-medium text-gray-700">Subtotal:</span>
              <span className="text-sm text-gray-900">{formatCurrency(totals.subtotal)}</span>
            </div>
            <div className="flex items-center space-x-2">
              <span className="text-sm font-medium text-gray-700">VAT:</span>
              <span className="text-sm text-gray-900">{formatCurrency(totals.vat)}</span>
            </div>
            <div className="flex items-center space-x-2">
              <span className="text-sm font-medium text-gray-700">Total:</span>
              <span className={cn(
                "text-sm font-bold",
                hasMismatch ? "text-red-600" : "text-gray-900"
              )}>
                {formatCurrency(totals.total)}
              </span>
            </div>
          </div>
          {hasMismatch && (
            <Badge className="bg-red-100 text-red-800" variant="outline">
              <Calculator className="w-3 h-3 mr-1" />
              Mismatch Detected
            </Badge>
          )}
        </div>
      </div>
    </div>
  );
};

export default LineItemsTable; 