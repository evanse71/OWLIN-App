import React, { useEffect, useState } from "react";
import UploadGlass from "@/components/UploadGlass";
import InvoiceCardEnhanced from "@/components/InvoiceCardEnhanced";
import BottomActionBar from "@/components/BottomActionBar";
import { apiListInvoices } from "@/lib/api";

type Item = { type:string; id:string; pages:number[]; page_count:number };

export default function InvoicesPage() {
  const [items, setItems] = useState<Item[]>([]);
  const [selected, setSelected] = useState<string[]>([]);

  const refresh = async () => {
    const data = await apiListInvoices();
    // Map list to card items
    const mapped = (data.items || []).map((x:any)=>({ type:"invoice", id:x.id, pages:x.pages || [], page_count:x.page_count || 0 }));
    setItems(mapped);
  };

  useEffect(()=>{ refresh(); }, []);

  const onCreated = (created: Item[]) => {
    // merge newly created at top, unique by id
    const ids = new Set(items.map(i=>i.id));
    const merged = [...created.filter(c=>!ids.has(c.id)), ...items];
    setItems(merged);
  };

  const onSave = () => {
    // if you have a save/finalise endpoint, call it. For now, just toast.
    alert("Saved changes");
    refresh();
  };
  const onCancel = () => window.location.reload();

  return (
    <div className="max-w-6xl mx-auto p-6">
      <div className="rounded-2xl border p-4 mb-4">
        <div className="text-lg font-semibold mb-3">Upload Documents</div>
        <UploadGlass docType="invoice" onCreated={onCreated} />
      </div>

      <div className="flex items-center gap-2 mb-3">
        <input className="border rounded-lg px-3 py-2 text-sm w-80" placeholder="Search invoices..." />
        <button className="border rounded-lg px-3 py-2 text-sm" onClick={refresh}>Refresh</button>
        <button className="border rounded-lg px-3 py-2 text-sm">Manual Invoice</button>
        <button className="border rounded-lg px-3 py-2 text-sm">Manual DN</button>
      </div>

      {items.length === 0 ? (
        <div className="rounded-2xl border p-4 text-sm text-zinc-600">
          No invoices yet. Upload a PDF or create a manual invoice to get started.
        </div>
      ) : items.map((it)=>(
        <div key={it.id} onClick={()=>{
          setSelected(prev => prev.includes(it.id) ? prev.filter(x=>x!==it.id) : [...prev, it.id])
        }}>
          <InvoiceCardEnhanced item={it} />
        </div>
      ))}

      <BottomActionBar selectedIds={selected} onSave={onSave} onCancel={onCancel} />
    </div>
  );
}