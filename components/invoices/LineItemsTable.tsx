import React from "react";

interface LineItem {
  id: string;
  description: string;
  quantity: number;
  unit_price: number;
  total: number;
  uom?: string;
  vat_rate?: number;
  source?: string;
  confidence?: number;
  flagged?: boolean;
}

interface LineItemsTableProps {
  items: LineItem[];
}

export default function LineItemsTable({ items }: LineItemsTableProps) {
  if (!items?.length) {
    return <div className="text-xs text-zinc-500">No line items found.</div>;
  }
  return (
    <div className="mt-2 border rounded-xl overflow-hidden">
      <table className="w-full text-sm">
        <thead className="bg-zinc-50">
          <tr>
            <th className="text-left p-2">Description</th>
            <th className="text-right p-2">Qty</th>
            <th className="text-right p-2">Unit</th>
            <th className="text-right p-2">Total</th>
            <th className="text-left p-2">Source</th>
          </tr>
        </thead>
        <tbody>
          {items.map((r, i) => (
            <tr key={i} className="border-t">
              <td className="p-2">{r.description}</td>
              <td className="p-2 text-right">{Number(r.quantity).toFixed(2)}</td>
              <td className="p-2 text-right">£{Number(r.unit_price).toFixed(2)}</td>
              <td className="p-2 text-right">£{Number(r.total).toFixed(2)}</td>
              <td className="p-2">{r.source || "ocr"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
