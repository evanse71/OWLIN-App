import React, { useState, useEffect } from "react";
import { apiInvoiceLineItems, apiRescanInvoice } from "@/lib/api";
import LineItemsTable from "./LineItemsTable";

type CreatedItem = { 
  type: string; 
  id: string | null; 
  page: number; 
};

export default function InvoiceCardEnhanced({ item }: { item: CreatedItem }) {
  const [open, setOpen] = useState(false);
  const [lines, setLines] = useState<any[]|null>(null);
  const [loading, setLoading] = useState(false);
  const [rescanLoading, setRescanLoading] = useState(false);

  const load = async () => {
    if (!item.id) return;
    setLoading(true);
    try {
      const data = await apiInvoiceLineItems(item.id);
      setLines(data.items || []);
    } catch (e) { /* Error handling */ }
    finally { setLoading(false); }
  };

  useEffect(()=>{ if (open && lines===null) load(); }, [open]);

  const rescan = async () => {
    if (!item.id) return;
    setRescanLoading(true);
    try { await apiRescanInvoice(item.id); await load(); }
    finally { setRescanLoading(false); }
  };

  return (
    <div className="rounded-2xl border bg-white/70 backdrop-blur p-4 mb-3">
      <div className="flex items-center justify-between">
        <div className="font-medium">
          {item.type === "invoice" ? "Invoice" : item.type === "delivery_note" ? "Delivery Note" : "Unknown"} — Page {item.page+1}
        </div>
        <button className="text-sm text-blue-600 underline" onClick={()=>setOpen(!open)}>
          {open ? "Collapse" : "Expand"}
        </button>
      </div>

      {open && (
        <div className="mt-3">
          {loading ? (
            <div className="text-sm text-zinc-500">Loading line items…</div>
          ) : (
            <>
              <LineItemsTable
                invoiceId={item.id || ""}
                items={lines || []}
                onChange={load}
              />
              {(lines?.length ?? 0) === 0 && (
                <div className="mt-2 text-xs text-zinc-600">
                  No lines detected — try a{" "}
                  <button className="underline text-blue-600 disabled:opacity-50" onClick={rescan} disabled={rescanLoading}>
                    {rescanLoading ? "Rescanning…" : "Rescan (OCR)"}
                  </button>
                </div>
              )}
            </>
          )}
        </div>
      )}
    </div>
  );
}