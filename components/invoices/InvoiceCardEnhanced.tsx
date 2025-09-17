import React, { useEffect, useState } from "react";
import { apiInvoiceLineItems, apiRescanInvoice } from "@/lib/api";
import LineItemsTable from "./LineItemsTable";

export default function InvoiceCardEnhanced({ item }: {
  item: { type:string; id:string; pages:number[]; page_count:number }
}) {
  const [open, setOpen] = useState(false);
  const [lines, setLines] = useState<any[]|null>(null);
  const [loading, setLoading] = useState(false);
  const [rescanning, setRescanning] = useState(false);

  const rangeLabel = () => {
    if (!item.pages?.length) return "Pages: —";
    const sorted = [...item.pages].sort((a,b)=>a-b);
    if (sorted.length === 1) return `Page ${sorted[0] + 1}`;
    return `Pages ${sorted[0] + 1}–${sorted[sorted.length - 1] + 1}`;
  };

  const load = async () => {
    setLoading(true);
    try {
      const data = await apiInvoiceLineItems(item.id);
      setLines(data.items || []);
    } finally { setLoading(false); }
  };

  useEffect(()=>{ if (open && lines===null) load(); }, [open]);

  const rescan = async () => {
    setRescanning(true);
    try { await apiRescanInvoice(item.id); await load(); }
    finally { setRescanning(false); }
  };

  return (
    <div className="rounded-2xl border bg-white/70 backdrop-blur p-4 mb-3">
      <div className="flex items-center justify-between">
        <div className="font-medium">{rangeLabel()}</div>
        <button className="text-sm text-blue-600 underline" onClick={()=>setOpen(!open)}>{open?"Collapse":"Expand"}</button>
      </div>
      {open && (
        <div className="mt-3">
          {loading ? <div className="text-sm text-zinc-500">Loading line items…</div> : (
            <>
              <LineItemsTable invoiceId={item.id} items={lines || []} onChange={load} />
              {(lines?.length ?? 0) === 0 && (
                <div className="mt-2 text-xs text-zinc-600">
                  No lines detected — try a{" "}
                  <button className="underline text-blue-600 disabled:opacity-50" onClick={rescan} disabled={rescanning}>
                    {rescanning ? "Rescanning…" : "Rescan (OCR)"}
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