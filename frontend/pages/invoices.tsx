import React, { useEffect, useState } from "react";
import UploadGlass from "@/components/UploadGlass";
import InvoiceCardEnhanced from "@/components/invoices/InvoiceCardEnhanced";
import BottomActionBar from "@/components/BottomActionBar";
// import DeliveryNotesPanel from "@/components/DeliveryNotesPanel";
import { apiListInvoices, apiExportInvoices } from "@/lib/api";

type Item = { type:string; id:string; pages:number[]; page_count:number };

export default function InvoicesPage() {
  const [items, setItems] = useState<Item[]>([]);
  const [selected, setSelected] = useState<string[]>([]);
  const [selectedInvoiceId, setSelectedInvoiceId] = useState<string | null>(null);
  const [siteId, setSiteId] = useState<string | null>(null);

  const refresh = async () => {
    try {
      const data = await apiListInvoices();
      let items = data.items || [];
      if (!items.length && process.env.NODE_ENV !== "production") {
        items = [
          { id:"dev-1", pages:[3,4,6], page_count:3 },
          { id:"dev-2", pages:[1], page_count:1 },
          { id:"dev-3", pages:[8,9], page_count:2 },
        ];
      }
      setItems(items);
    } catch (e) { 
      console.error(e); 
    }
  };

  useEffect(()=>{ refresh(); }, []);

  const onCreated = (created: Item[]) => {
    // merge newly created at top, unique by id
    const ids = new Set(items.map(i=>i.id));
    const merged = [...created.filter(c=>!ids.has(c.id)), ...items];
    setItems(merged);
  };

  const onSave = () => {
    // Save draft - refetch list and toast
    refresh();
    alert("Draft saved");
  };
  
  const onCancel = () => {
    // Clear All - clear selection and reload
    setSelected([]);
    window.location.reload();
  };

  const onSend = async () => {
    if (selected.length === 0) {
      alert('Please select at least one invoice');
      return;
    }

    try {
      const result = await apiExportInvoices(selected);
      if (result.ok) {
        alert(`Exported to ${result.zip_path}`);
      } else {
        alert('Export failed');
      }
    } catch (error: any) {
      console.error('Export failed:', error);
      alert(`Export failed: ${error.message}`);
    }
  };

  return (
    <div className="max-w-7xl mx-auto p-6 pb-24">
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column - Invoices */}
        <div className="lg:col-span-8">
          <div className="rounded-2xl border p-4 mb-4">
            <div className="text-lg font-semibold mb-3">Upload Invoices</div>
            <UploadGlass docType="invoice" onCreated={onCreated} />
          </div>

          <div className="flex items-center gap-2 mb-3">
            <input className="border rounded-lg px-3 py-2 text-sm w-80" placeholder="Search invoices..." />
            <button className="border rounded-lg px-3 py-2 text-sm" onClick={refresh}>Refresh</button>
            <button className="border rounded-lg px-3 py-2 text-sm">Manual Invoice</button>
          </div>

          {items.length === 0 ? (
            <div className="rounded-2xl border p-4 text-sm text-zinc-600">
              No invoices yet. Upload a PDF or create a manual invoice to get started.
            </div>
          ) : items.map((it)=>(
            <div 
              key={it.id} 
              className={`cursor-pointer transition-all ${
                selected.includes(it.id) ? 'ring-2 ring-blue-500 bg-blue-50' : ''
              }`}
              onClick={()=>{
                setSelected(prev => prev.includes(it.id) ? prev.filter(x=>x!==it.id) : [...prev, it.id])
                setSelectedInvoiceId(prev => prev === it.id ? null : it.id)
              }}
            >
              <InvoiceCardEnhanced item={it} />
            </div>
          ))}
        </div>

        {/* Right Column - Delivery Notes */}
        <div className="lg:col-span-4">
          <div className="rounded-2xl border p-4 mb-4">
            <div className="text-lg font-semibold mb-3">Upload Delivery Notes</div>
            <UploadGlass docType="delivery_note" onCreated={() => {}} />
          </div>

          <div className="p-4 border rounded-lg bg-gray-50">
            <h3 className="font-semibold mb-2">Delivery Notes</h3>
            <p className="text-sm text-gray-600">
              Delivery notes panel for invoice {selectedInvoiceId || 'none selected'}
            </p>
            <p className="text-xs text-gray-500 mt-2">
              Site: {siteId || 'none'}
            </p>
          </div>
        </div>
      </div>

      <BottomActionBar 
        selectedIds={selected} 
        onSave={onSave} 
        onCancel={onCancel} 
      />
    </div>
  );
}