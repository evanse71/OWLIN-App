import { useState } from "react";
import InvoiceManualCard from "@/components/manual/InvoiceManualCard";
import DeliveryNoteManualCard from "@/components/manual/DeliveryNoteManualCard";
import PairingPanel from "@/components/manual/PairingPanel";

export default function ManualEntryPage() {
  const [tab, setTab] = useState<"invoice"|"dn">("invoice");
  return (
    <div className="p-6">
      <div className="mb-4 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-slate-800">Manual Entry</h1>
          <p className="text-slate-500 text-sm">Low-stress creation of invoices and delivery notes. Pair on the right.</p>
        </div>
        <div className="flex gap-2">
          <button className={`px-3 py-2 rounded-xl ${tab==="invoice"?"bg-slate-900 text-white":"bg-slate-100"}`} onClick={()=>setTab("invoice")}>Invoice</button>
          <button className={`px-3 py-2 rounded-xl ${tab==="dn"?"bg-slate-900 text-white":"bg-slate-100"}`} onClick={()=>setTab("dn")}>Delivery Note</button>
        </div>
      </div>

      <div className="grid grid-cols-12 gap-6">
        <div className="col-span-12 lg:col-span-8">
          {tab==="invoice" ? <InvoiceManualCard/> : <DeliveryNoteManualCard/>}
        </div>
        <div className="col-span-12 lg:col-span-4">
          <PairingPanel/>
        </div>
      </div>
    </div>
  );
}
