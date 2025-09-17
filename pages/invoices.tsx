import React, { useEffect, useState } from "react";
import UploadGlass from "@/components/UploadGlass";
import InvoiceCardEnhanced from "@/components/invoices/InvoiceCardEnhanced";
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

  const onCreated = (newItems: any[]) => {
    const mapped = newItems.map((x:any)=>({ type:"invoice", id:x.id, pages:x.pages || [], page_count:x.page_count || 0 }));
    setItems(prev => [...mapped, ...prev]);
  };

  const onSave = () => {
    console.log("Save selected:", selected);
    // TODO: implement save logic
  };

  const onCancel = () => {
    setSelected([]);
  };

  return (
    <div className="space-y-6">
      {/* Upload Box */}
      <div className="card rounded-2xl">
        <div className="card-header p-4 sm:p-6">
          <h3 className="card-title text-lg font-semibold">Upload Documents</h3>
        </div>
        <div className="card-content p-4 sm:p-6 pt-0">
          <UploadGlass onCreated={onCreated} />
        </div>
      </div>

      {/* Search and Actions */}
      <div className="card rounded-2xl">
        <div className="card-content p-4 sm:p-6">
          <div className="flex items-center gap-4">
            <div className="relative flex-1">
              <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="lucide lucide-search absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4">
                <circle cx="11" cy="11" r="8"></circle>
                <path d="m21 21-4.3-4.3"></path>
              </svg>
              <input placeholder="Search invoices..." className="w-full h-10 pl-10 pr-4 rounded-lg border border-gray-200 focus:ring-2 focus:ring-blue-500 focus:border-transparent" />
            </div>
            <button className="btn btn-outline btn-default" onClick={refresh}>Refresh</button>
            <button className="btn btn-outline btn-default">
              <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="lucide lucide-file-text w-4 h-4 mr-2">
                <path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z"></path>
                <polyline points="14 2 14 8 20 8"></polyline>
                <line x1="16" x2="8" y1="13" y2="13"></line>
                <line x1="16" x2="8" y1="17" y2="17"></line>
                <line x1="10" x2="8" y1="9" y2="9"></line>
              </svg>
              Manual Invoice
            </button>
            <button className="btn btn-outline btn-default">
              <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="lucide lucide-package w-4 h-4 mr-2">
                <path d="m7.5 4.27 9 5.15"></path>
                <path d="M21 8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16Z"></path>
                <path d="m3.3 7 8.7 5 8.7-5"></path>
                <path d="M12 22V12"></path>
              </svg>
              Manual DN
            </button>
          </div>
        </div>
      </div>

      {/* Invoice Cards */}
      <div className="space-y-4">
        {items.length === 0 ? (
          <div className="card rounded-2xl">
            <div className="card-content py-12 text-center">
              <div className="text-gray-500">
                <div>
                  <p>No invoices yet. Upload a PDF or create a manual invoice to get started.</p>
                </div>
              </div>
            </div>
          </div>
        ) : (
          items.map((item) => (
            <InvoiceCardEnhanced
              key={item.id}
              item={item}
              selected={selected.includes(item.id)}
              onSelect={(id, checked) => {
                if (checked) {
                  setSelected(prev => [...prev, id]);
                } else {
                  setSelected(prev => prev.filter(x => x !== id));
                }
              }}
            />
          ))
        )}
      </div>

      {/* Bottom Action Bar */}
      {selected.length > 0 && (
        <BottomActionBar
          selectedIds={selected}
          onSave={onSave}
          onCancel={onCancel}
        />
      )}
    </div>
  );
}