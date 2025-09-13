import React, { useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import LineItemsEditor from "./LineItemsEditor";
import { postManualInvoice } from "@/lib/api";

const LineSchema = z.object({
  description: z.string().min(1),
  outer_qty: z.number().gte(0),
  items_per_outer: z.number().gt(0).nullable().optional(),
  unit_size: z.number().gt(0).nullable().optional(),
  unit_price: z.number().gte(0),
  vat_rate_percent: z.number().gte(0),
});
const FormSchema = z.object({
  supplier_id: z.string().min(1),
  supplier_name: z.string().min(1),
  invoice_date: z.string().length(10),
  invoice_ref: z.string().min(1),
  currency: z.string().length(3).default("GBP"),
  notes: z.string().optional(),
  lines: z.array(LineSchema).min(1),
});
type FormData = z.infer<typeof FormSchema>;

export default function InvoiceManualCard() {
  const [totals, setTotals] = useState({ net: 0, vat: 0, gross: 0, base_units_sum: 0 });
  const form = useForm<FormData>({
    resolver: zodResolver(FormSchema),
    defaultValues: {
      currency: "GBP",
      supplier_id: "",
      supplier_name: "",
      invoice_date: new Date().toISOString().slice(0,10),
      invoice_ref: "",
      notes: "",
      lines: [{ description: "", outer_qty: 1, items_per_outer: 24, unit_size: null, unit_price: 0, vat_rate_percent: 20 }]
    }
  });

  const onSubmit = async (data: FormData, clearAfter = true) => {
    const res = await postManualInvoice(data);
    alert(`Invoice saved: ${res.id}`);
    if (clearAfter) form.reset();
  };

  return (
    <div className="rounded-2xl bg-white border border-slate-200 shadow-sm">
      <div className="px-5 py-4 border-b border-slate-200 flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-slate-800">Manual Invoice</h2>
          <p className="text-sm text-slate-500">Enter line items; totals compute automatically. Unit price is per base unit.</p>
        </div>
        <span className="inline-flex items-center px-2 py-1 rounded-lg bg-emerald-50 text-emerald-700 text-xs border border-emerald-200">Calm Mode</span>
      </div>

      <form onSubmit={form.handleSubmit((d)=>onSubmit(d, true))} className="p-5 space-y-4">
        <div className="grid grid-cols-12 gap-3">
          <div className="col-span-12 md:col-span-3">
            <label className="text-xs text-slate-600">Supplier ID</label>
            <input {...form.register("supplier_id")} className="w-full bg-white border border-slate-200 rounded-xl px-3 py-2 focus:ring-2 focus:ring-emerald-300"/>
          </div>
          <div className="col-span-12 md:col-span-5">
            <label className="text-xs text-slate-600">Supplier Name</label>
            <input {...form.register("supplier_name")} className="w-full bg-white border border-slate-200 rounded-xl px-3 py-2 focus:ring-2 focus:ring-emerald-300"/>
          </div>
          <div className="col-span-6 md:col-span-2">
            <label className="text-xs text-slate-600">Date</label>
            <input type="date" {...form.register("invoice_date")} className="w-full bg-white border border-slate-200 rounded-xl px-3 py-2 focus:ring-2 focus:ring-emerald-300"/>
          </div>
          <div className="col-span-6 md:col-span-2">
            <label className="text-xs text-slate-600">Invoice Ref</label>
            <input {...form.register("invoice_ref")} className="w-full bg-white border border-slate-200 rounded-xl px-3 py-2 focus:ring-2 focus:ring-emerald-300"/>
          </div>
          <div className="col-span-6 md:col-span-1">
            <label className="text-xs text-slate-600">Currency</label>
            <input {...form.register("currency")} className="w-full bg-white border border-slate-200 rounded-xl px-3 py-2 focus:ring-2 focus:ring-emerald-300"/>
          </div>
          <div className="col-span-12">
            <label className="text-xs text-slate-600">Notes (optional)</label>
            <textarea {...form.register("notes")} className="w-full bg-white border border-slate-200 rounded-xl px-3 py-2 focus:ring-2 focus:ring-emerald-300"/>
          </div>
        </div>

        <LineItemsEditor form={form} name="lines" onTotalsChange={setTotals} />

        <div className="sticky bottom-0 mt-2">
          <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-3 rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3">
            <div className="text-sm">
              <div className="text-slate-700">Total Net: <span className="font-semibold">£{totals.net.toFixed(2)}</span></div>
              <div className="text-slate-700">VAT: <span className="font-semibold">£{totals.vat.toFixed(2)}</span></div>
              <div className="text-slate-900">Total Gross: <span className="font-semibold">£{totals.gross.toFixed(2)}</span></div>
            </div>
            <div className="flex gap-2">
              <button type="submit" className="px-4 py-2 rounded-xl bg-slate-900 text-white">Save & Clear</button>
              <button type="button" onClick={form.handleSubmit((d)=>onSubmit(d, false))} className="px-4 py-2 rounded-xl bg-emerald-600 text-white">Save & New Line</button>
              <button type="button" onClick={()=>form.reset()} className="px-4 py-2 rounded-xl bg-slate-100">Reset</button>
            </div>
          </div>
          <div className="text-[11px] text-slate-500 mt-1">Pack rule: base units = outer × items/outer. We show per-crate hint to prevent mistakes.</div>
        </div>
      </form>
    </div>
  );
}
