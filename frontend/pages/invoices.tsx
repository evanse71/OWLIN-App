import React, { useState } from "react";
import UploadGlass from "@/components/invoices/UploadGlass";
import InvoiceCardEnhanced from "@/components/invoices/InvoiceCardEnhanced";

type CreatedItem = { type:string; id:string|null; page:number };

export default function InvoicesPage() {
  const [created, setCreated] = useState<CreatedItem[]>([]);

  const onCreated = (items: CreatedItem[], jobId: string) => {
    // Merge new items at top
    setCreated(prev => [...items, ...prev]);
  };

  return (
    <div className="max-w-6xl mx-auto p-6">
      <div className="grid md:grid-cols-2 gap-6">
        <UploadGlass onCreated={onCreated} docType="invoice" />
        <UploadGlass onCreated={onCreated} docType="delivery_note" />
      </div>

      <div className="mt-8">
        <h2 className="text-lg font-semibold mb-3">Processed Documents</h2>
        {created.length === 0 && <div className="text-sm text-zinc-500">No documents yet. Upload on the left.</div>}
        {created.map((it, idx) => <InvoiceCardEnhanced key={idx} item={it} />)}
      </div>
    </div>
  );
}
