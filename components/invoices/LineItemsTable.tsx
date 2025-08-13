import React, { useState, useEffect } from 'react';

interface LineItem {
  description: string;
  quantity: number;
  unit?: string;
  unit_price?: number;
  vat_percent?: number;
  line_total?: number;
  page?: number;
  row_idx?: number;
  flags?: string[];
  confidence?: number;
}

interface LineItemsTableProps {
  lineItems: LineItem[];
  editable?: boolean;
  onEditLineItem?: (rowIdx: number, patch: Partial<LineItem>) => void;
  reviewOnly?: boolean;
}

export default function LineItemsTable({
  lineItems,
  editable = false,
  onEditLineItem,
  reviewOnly = false
}: LineItemsTableProps) {
  const [editingRow, setEditingRow] = useState<number | null>(null);
  const [editData, setEditData] = useState<Partial<LineItem>>({});
  const [savedMessage, setSavedMessage] = useState<string>('');
  const [filteredItems, setFilteredItems] = useState<LineItem[]>(lineItems);

  useEffect(() => {
    if (reviewOnly) {
      setFilteredItems(lineItems.filter(item => item.flags && item.flags.length > 0));
    } else {
      setFilteredItems(lineItems);
    }
  }, [lineItems, reviewOnly]);

  const handleEditStart = (rowIdx: number) => {
    setEditingRow(rowIdx);
    setEditData(filteredItems[rowIdx]);
  };

  const handleEditSave = () => {
    if (editingRow !== null && onEditLineItem) {
      onEditLineItem(editingRow, editData);
      setSavedMessage('Saved ✓');
      setTimeout(() => setSavedMessage(''), 2000);
      setEditingRow(null);
      setEditData({});
    }
  };

  const handleEditCancel = () => {
    setEditingRow(null);
    setEditData({});
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
      e.preventDefault();
      handleEditSave();
    } else if (e.key === 'Escape') {
      handleEditCancel();
    }
  };

  const sanitizeNumericInput = (value: string, field: keyof LineItem): number => {
    const num = parseFloat(value.replace(/[^\d.-]/g, ''));
    if (isNaN(num) || num < 0) return 0;
    if (field === 'quantity' && num > 100000) return 100000;
    if (field === 'unit_price' && num > 1e7) return 1e7;
    return num;
  };

  const calculateTotals = () => {
    // Prefer line_total when provided; otherwise quantity*unit_price
    const subtotal = filteredItems.reduce((sum, item) => {
      const lt = typeof item.line_total === 'number' ? item.line_total : ((item.quantity || 0) * (item.unit_price || 0));
      return sum + (isFinite(lt) ? lt : 0);
    }, 0);
    const vatTotal = filteredItems.reduce((sum, item) => {
      const lt = typeof item.line_total === 'number' ? item.line_total : ((item.quantity || 0) * (item.unit_price || 0));
      const vatPct = typeof item.vat_percent === 'number' ? item.vat_percent : 0;
      return sum + (isFinite(lt) ? (lt * vatPct / 100) : 0);
    }, 0);
    const total = subtotal + vatTotal;
    return { subtotal, vatTotal, total };
  };

  const { subtotal, vatTotal, total } = calculateTotals();

  const renderCell = (item: LineItem, field: keyof LineItem, rowIdx: number) => {
    const isEditing = editingRow === rowIdx;
    const value = (isEditing ? (editData as any)[field] : (item as any)[field]);
    const confidence = item.confidence || 1;

    const rightAligned = field === 'line_total' || field === 'unit_price' || field === 'quantity' || field === 'vat_percent';
    const cellClasses = `py-2 px-3 ${rightAligned ? 'text-right tabular' : ''}`;
    const lowConfidence = confidence < 0.7;

    if (isEditing && editable) {
      const inputType = typeof value === 'number' ? 'number' : 'text';
      return (
        <input
          type={inputType}
          value={value ?? ''}
          onChange={(e) => {
            const newValue = inputType === 'number' 
              ? sanitizeNumericInput(e.target.value, field)
              : e.target.value;
            setEditData(prev => ({ ...prev, [field]: newValue }));
          }}
          onKeyDown={handleKeyDown}
          className={`w-full px-2 py-1 border border-[#E7EAF0] rounded text-sm focus:focus-ring`}
          autoFocus
        />
      );
    }

    const display = typeof value === 'number'
      ? (field === 'unit_price' || field === 'line_total' ? `£${value.toFixed(2)}` : value.toFixed(2))
      : (value ?? '');

    return (
      <div className={`${cellClasses} ${lowConfidence ? 'border-b border-amber-300/60' : ''}`}>
        {display}
        {lowConfidence && (
          <span 
            className="ml-1 text-amber-600 text-xs"
            title={`Low confidence (${confidence.toFixed(2)})`}
          >
            ⚠
          </span>
        )}
      </div>
    );
  };

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="sticky top-0 z-[1] bg-white border-b border-[#E7EAF0] py-2">
        <div className="grid grid-cols-6 gap-2 text-[13px] text-[#5B6470] font-medium">
          <div className="px-3">Description</div>
          <div className="px-3 text-right">Qty</div>
          <div className="px-3">Unit</div>
          <div className="px-3 text-right">Unit Price</div>
          <div className="px-3 text-right">VAT %</div>
          <div className="px-3 text-right">Line Total</div>
        </div>
      </div>

      {/* Rows */}
      <div className="space-y-0">
        {filteredItems.map((item, rowIdx) => (
          <div 
            key={rowIdx}
            className={`grid grid-cols-6 gap-2 table-zebra ${rowIdx < 6 ? 'fade-up' : ''}`}
            style={{ animationDelay: `${rowIdx * 30}ms` }}
          >
            {renderCell(item, 'description', rowIdx)}
            {renderCell(item, 'quantity', rowIdx)}
            {renderCell(item, 'unit', rowIdx)}
            {renderCell(item, 'unit_price', rowIdx)}
            {renderCell(item, 'vat_percent', rowIdx)}
            {renderCell(item, 'line_total', rowIdx)}
          </div>
        ))}
      </div>

      {/* Totals */}
      <div className="border-t border-[#E7EAF0] pt-4 space-y-2">
        <div className="flex justify-between text-sm">
          <span>Subtotal:</span>
          <span className="tabular font-semibold">£{subtotal.toFixed(2)}</span>
        </div>
        <div className="flex justify-between text-sm">
          <span>VAT:</span>
          <span className="tabular font-semibold">£{vatTotal.toFixed(2)}</span>
        </div>
        <div className="flex justify-between text-base font-semibold border-t border-[#E7EAF0] pt-2">
          <span>Total:</span>
          <span className="tabular">£{total.toFixed(2)}</span>
          {savedMessage && (
            <span className="text-green-600 text-sm ml-2">{savedMessage}</span>
          )}
        </div>
      </div>
    </div>
  );
} 