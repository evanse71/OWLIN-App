import React, { useMemo, useState } from "react";
import { apiUpdateLineItem, apiDeleteLineItem } from "@/lib/api";

type Item = {
  id: number | string;
  description?: string;
  quantity?: number;
  unit_price?: number;
  total?: number;
  uom?: string | null;
  vat_rate?: number;
  source?: string;
};

export default function LineItemsTable({
  invoiceId,
  items,
  onChange,
}: {
  invoiceId: string;
  items: Item[];
  onChange?: () => void;
}) {
  const [busyRow, setBusyRow] = useState<number | string | null>(null);
  const sum = useMemo(() => (items || []).reduce((a, r) => a + (Number(r.total) || 0), 0), [items]);

  const update = async (row: Item, patch: Partial<Item>) => {
    const lineId = row.id;
    setBusyRow(lineId);
    try {
      const payload: any = { ...row, ...patch };
      // server will recompute total, but we send a hint
      if (payload.quantity != null && payload.unit_price != null) {
        payload.total = Number(payload.quantity) * Number(payload.unit_price);
      }
      await apiUpdateLineItem(invoiceId, String(lineId), payload);
      onChange?.();
    } finally {
      setBusyRow(null);
    }
  };

  const remove = async (row: Item) => {
    setBusyRow(row.id);
    try {
      await apiDeleteLineItem(invoiceId, String(row.id));
      onChange?.();
    } finally {
      setBusyRow(null);
    }
  };

  if (!items?.length) {
    return <div className="text-xs text-zinc-500">No line items found.</div>;
  }

  return (
    <div className="mt-2 border rounded-xl overflow-hidden">
      <table className="w-full text-sm">
        <thead className="bg-zinc-50">
          <tr>
            <th className="text-left p-2 w-[45%]">Description</th>
            <th className="text-right p-2 w-[10%]">Qty</th>
            <th className="text-right p-2 w-[15%]">Unit</th>
            <th className="text-right p-2 w-[15%]">Total</th>
            <th className="text-left p-2 w-[10%]">UOM</th>
            <th className="text-left p-2 w-[5%]">VAT%</th>
            <th className="p-2 w-[10%]"></th>
          </tr>
        </thead>
        <tbody>
          {items.map((r) => {
            const disabled = busyRow === r.id;
            return (
              <tr key={String(r.id)} className="border-t">
                <td className="p-2">
                  <input
                    className="w-full bg-transparent outline-none"
                    defaultValue={r.description || ""}
                    disabled={disabled}
                    onBlur={(e) => update(r, { description: e.target.value })}
                  />
                </td>
                <td className="p-2 text-right">
                  <input
                    className="w-full bg-transparent text-right outline-none"
                    type="number"
                    step="0.01"
                    defaultValue={r.quantity ?? 0}
                    disabled={disabled}
                    onBlur={(e) => update(r, { quantity: Number(e.target.value) })}
                  />
                </td>
                <td className="p-2 text-right">
                  <input
                    className="w-full bg-transparent text-right outline-none"
                    type="number"
                    step="0.01"
                    defaultValue={r.unit_price ?? 0}
                    disabled={disabled}
                    onBlur={(e) => update(r, { unit_price: Number(e.target.value) })}
                  />
                </td>
                <td className="p-2 text-right">
                  £{Number(r.total ?? ((r.quantity||0)*(r.unit_price||0))).toFixed(2)}
                </td>
                <td className="p-2">
                  <input
                    className="w-full bg-transparent outline-none"
                    defaultValue={r.uom || ""}
                    disabled={disabled}
                    onBlur={(e) => update(r, { uom: e.target.value })}
                  />
                </td>
                <td className="p-2">
                  <input
                    className="w-full bg-transparent outline-none"
                    type="number"
                    step="1"
                    defaultValue={r.vat_rate ?? 0}
                    disabled={disabled}
                    onBlur={(e) => update(r, { vat_rate: Number(e.target.value) })}
                  />
                </td>
                <td className="p-2 text-right">
                  <button
                    className="text-xs text-red-600 underline disabled:opacity-50"
                    disabled={disabled}
                    onClick={() => remove(r)}
                  >
                    Delete
                  </button>
                </td>
              </tr>
            );
          })}
          <tr className="border-t bg-zinc-50">
            <td className="p-2 font-medium" colSpan={3}>Total</td>
            <td className="p-2 text-right font-medium">£{sum.toFixed(2)}</td>
            <td colSpan={3}></td>
          </tr>
        </tbody>
      </table>
    </div>
  );
}
