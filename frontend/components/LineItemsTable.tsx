import React, { useState } from "react";
import type { LineItemDTO, UpdateLineItemRequest } from "@/types/invoice";
import { apiUpdateLineItem, apiDeleteLineItem } from "@/lib/api";

interface LineItemsTableProps {
  invoiceId: string;
  items: LineItemDTO[];
  onChange: () => void;
}

export default function LineItemsTable({ invoiceId, items, onChange }: LineItemsTableProps) {
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editData, setEditData] = useState<UpdateLineItemRequest>({
    description: '',
    quantity: 0,
    unit_price: 0,
    uom: '',
    vat_rate: 0,
  });
  const [isSaving, setIsSaving] = useState(false);

  const handleEdit = (item: LineItemDTO) => {
    setEditingId(item.id);
    setEditData({
      description: item.description || '',
      quantity: item.quantity || 0,
      unit_price: item.unit_price || 0,
      uom: item.uom || '',
      vat_rate: item.vat_rate || 0,
    });
  };

  const handleSave = async () => {
    if (!editingId) return;
    
    setIsSaving(true);
    try {
      await apiUpdateLineItem(invoiceId, editingId, editData);
      setEditingId(null);
      setEditData({});
      onChange();
    } catch (error) {
      console.error('Failed to update line item:', error);
      alert('Failed to update line item');
    } finally {
      setIsSaving(false);
    }
  };

  const handleCancel = () => {
    setEditingId(null);
    setEditData({
      description: '',
      quantity: 0,
      unit_price: 0,
      uom: '',
      vat_rate: 0,
    });
  };

  const handleDelete = async (item: LineItemDTO) => {
    if (!confirm('Are you sure you want to delete this line item?')) return;
    
    try {
      await apiDeleteLineItem(invoiceId, item.id);
      onChange();
    } catch (error) {
      console.error('Failed to delete line item:', error);
      alert('Failed to delete line item');
    }
  };

  const calculateTotal = (item: LineItemDTO) => {
    const quantity = parseFloat(String(item.quantity || 0));
    const unitPrice = parseFloat(String(item.unit_price || 0));
    const vatRate = parseFloat(String(item.vat_rate || 0));
    
    const subtotal = quantity * unitPrice;
    const vat = subtotal * (vatRate / 100);
    return subtotal + vat;
  };

  if (items.length === 0) {
    return (
      <div className="text-gray-500 text-sm py-4 text-center">
        No line items available
      </div>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b">
            <th className="text-left py-2">Description</th>
            <th className="text-right py-2">Qty</th>
            <th className="text-right py-2">Unit Price</th>
            <th className="text-left py-2">UOM</th>
            <th className="text-right py-2">VAT %</th>
            <th className="text-right py-2">Total</th>
            <th className="text-center py-2">Actions</th>
          </tr>
        </thead>
        <tbody>
          {items.map((item, index) => {
            const isEditing = editingId === item.id;
            const total = calculateTotal(item);
            
            return (
              <tr key={item.id || index} className="border-b">
                <td className="py-2">
                  {isEditing ? (
                    <input
                      type="text"
                      value={editData.description}
                      onChange={(e) => setEditData({...editData, description: e.target.value})}
                      className="w-full px-2 py-1 border rounded"
                      aria-label="Description"
                    />
                  ) : (
                    item.description || '—'
                  )}
                </td>
                <td className="py-2 text-right">
                  {isEditing ? (
                    <>
                      <label htmlFor={`qty-${item.id || index}`} className="sr-only">Quantity</label>
                      <input
                        id={`qty-${item.id || index}`}
                        type="number"
                        step="0.01"
                        value={editData.quantity}
                        onChange={(e) => setEditData({...editData, quantity: parseFloat(e.target.value) || 0})}
                        className="w-20 px-2 py-1 border rounded text-right"
                        aria-label="Quantity"
                      />
                    </>
                  ) : (
                    item.quantity || '—'
                  )}
                </td>
                <td className="py-2 text-right">
                  {isEditing ? (
                    <>
                      <label htmlFor={`price-${item.id || index}`} className="sr-only">Unit price</label>
                      <input
                        id={`price-${item.id || index}`}
                        type="number"
                        step="0.01"
                        value={editData.unit_price}
                        onChange={(e) => setEditData({...editData, unit_price: parseFloat(e.target.value) || 0})}
                        className="w-24 px-2 py-1 border rounded text-right"
                        aria-label="Unit price"
                      />
                    </>
                  ) : (
                    item.unit_price ? `£${parseFloat(String(item.unit_price)).toFixed(2)}` : '—'
                  )}
                </td>
                <td className="py-2">
                  {isEditing ? (
                    <input
                      type="text"
                      value={editData.uom}
                      onChange={(e) => setEditData({...editData, uom: e.target.value})}
                      className="w-16 px-2 py-1 border rounded"
                      aria-label="Unit of Measure"
                    />
                  ) : (
                    item.uom || '—'
                  )}
                </td>
                <td className="py-2 text-right">
                  {isEditing ? (
                    <input
                      type="number"
                      step="0.01"
                      value={editData.vat_rate}
                      onChange={(e) => setEditData({...editData, vat_rate: parseFloat(e.target.value) || 0})}
                      className="w-16 px-2 py-1 border rounded text-right"
                      aria-label="VAT Rate"
                    />
                  ) : (
                    item.vat_rate ? `${item.vat_rate}%` : '—'
                  )}
                </td>
                <td className="py-2 text-right font-medium">
                  £{total.toFixed(2)}
                </td>
                <td className="py-2 text-center">
                  {isEditing ? (
                    <div className="flex gap-1 justify-center">
                      <button
                        onClick={handleSave}
                        disabled={isSaving}
                        className="px-2 py-1 text-xs bg-green-100 text-green-800 rounded hover:bg-green-200 disabled:opacity-50"
                      >
                        {isSaving ? 'Saving...' : 'Save'}
                      </button>
                      <button
                        onClick={handleCancel}
                        className="px-2 py-1 text-xs bg-gray-100 text-gray-800 rounded hover:bg-gray-200"
                      >
                        Cancel
                      </button>
                    </div>
                  ) : (
                    <div className="flex gap-1 justify-center">
                      <button
                        onClick={() => handleEdit(item)}
                        className="px-2 py-1 text-xs bg-blue-100 text-blue-800 rounded hover:bg-blue-200"
                      >
                        Edit
                      </button>
                      <button
                        onClick={() => handleDelete(item)}
                        className="px-2 py-1 text-xs bg-red-100 text-red-800 rounded hover:bg-red-200"
                      >
                        Delete
                      </button>
                    </div>
                  )}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
