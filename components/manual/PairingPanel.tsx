import { useEffect, useState } from "react";
import { getUnpaired, postPair } from "@/lib/api";

export default function PairingPanel() {
  const [data, setData] = useState<{invoices:any[], delivery_notes:any[]}>({invoices:[], delivery_notes:[]});
  const [invoiceId, setInvoiceId] = useState("");
  const [dnId, setDnId] = useState("");
  const [busy, setBusy] = useState(false);

  const refresh = async ()=> setData(await getUnpaired());
  useEffect(()=>{ refresh(); },[]);

  const pair = async ()=> {
    if (!invoiceId || !dnId) return;
    setBusy(true);
    try {
      await postPair({invoice_id: invoiceId, delivery_note_id: dnId});
      setInvoiceId(""); setDnId("");
      await refresh();
      alert("Paired successfully");
    } catch (e: any) {
      alert(`Pair failed: ${e.message || e}`);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="rounded-2xl border border-slate-200 p-4 bg-white shadow-sm">
      <h2 className="font-semibold mb-2 text-slate-800">Pairing</h2>
      <p className="text-sm text-slate-500 mb-3">Select an invoice and a delivery note to confirm pairing.</p>

      <div className="mb-3">
        <label className="block text-xs text-slate-600">Invoice</label>
        <select className="w-full border border-slate-200 rounded-lg p-2 bg-white" value={invoiceId} onChange={e=>setInvoiceId(e.target.value)}>
          <option value="">Select invoice</option>
          {data.invoices.map(i=><option key={i.id} value={i.id}>{i.id} · {i.supplier_name} · {i.date}</option>)}
        </select>
      </div>

      <div className="mb-3">
        <label className="block text-xs text-slate-600">Delivery Note</label>
        <select className="w-full border border-slate-200 rounded-lg p-2 bg-white" value={dnId} onChange={e=>setDnId(e.target.value)}>
          <option value="">Select delivery note</option>
          {data.delivery_notes.map(d=><option key={d.id} value={d.id}>{d.id} · {d.supplier_name} · {d.date}</option>)}
        </select>
      </div>

      <button disabled={!invoiceId||!dnId||busy} onClick={pair} className="w-full py-2 rounded-xl bg-emerald-600 text-white disabled:opacity-50">
        {busy ? "Pairing..." : "Confirm Pair"}
      </button>
      <button onClick={refresh} className="w-full mt-2 py-2 rounded-xl bg-slate-100">Refresh</button>
    </div>
  );
}
