import React, { useEffect } from "react";
import { useFieldArray, UseFormReturn } from "react-hook-form";

type Line = {
  description: string;
  outer_qty: number;
  items_per_outer?: number | null;
  unit_size?: number | null;
  unit_price: number;           // per unit
  vat_rate_percent: number;     // %
};

type Props = {
  form: UseFormReturn<any>;
  name: string; // "lines"
  onTotalsChange?: (t: { net: number; vat: number; gross: number; base_units_sum: number }) => void;
};

function money(n: number) {
  return Number((Math.round((n + Number.EPSILON) * 100) / 100).toFixed(2));
}

export default function LineItemsEditor({ form, name, onTotalsChange }: Props) {
  const { control, register, watch, setValue } = form;
  const { fields, append, remove } = useFieldArray({ control, name });
  const lines: Line[] = watch(name) || [];

  useEffect(() => {
    if (!lines.length) return;
    let net = 0, vat = 0, gross = 0, base_units_sum = 0;
    lines.forEach((li, idx) => {
      const outer = Number(li.outer_qty || 0);
      const ipo = Number(li.items_per_outer || 1);
      const baseUnits = outer * ipo;
      base_units_sum += baseUnits;
      const unitPrice = Number(li.unit_price || 0);
      const lineNet = money(unitPrice * baseUnits);
      const lineVAT = money(lineNet * Number(li.vat_rate_percent || 0) / 100);
      const lineGross = money(lineNet + lineVAT);
      net += lineNet; vat += lineVAT; gross += lineGross;
      setValue(`${name}.${idx}.__computed_base_units`, baseUnits, { shouldDirty: false });
      setValue(`${name}.${idx}.__computed_net`, lineNet, { shouldDirty: false });
      setValue(`${name}.${idx}.__computed_vat`, lineVAT, { shouldDirty: false });
      setValue(`${name}.${idx}.__computed_gross`, lineGross, { shouldDirty: false });
    });
    onTotalsChange?.({ net: money(net), vat: money(vat), gross: money(gross), base_units_sum });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [JSON.stringify(lines)]);

  function addBlank() {
    append({ description: "", outer_qty: 1, items_per_outer: 24, unit_size: null, unit_price: 0, vat_rate_percent: 20 });
  }

  function onKeyDownAddRow(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === "Enter") { e.preventDefault(); addBlank(); }
  }

  return (
    <div className="rounded-2xl border border-slate-200 overflow-hidden">
      <div className="grid grid-cols-12 bg-slate-50 text-slate-600 text-xs px-3 py-2">
        <div className="col-span-4">Item</div>
        <div className="col-span-1 text-right">Outer</div>
        <div className="col-span-2 text-right">Items/Outer</div>
        <div className="col-span-1 text-right">Unit Size</div>
        <div className="col-span-1 text-right">Unit £</div>
        <div className="col-span-1 text-right">VAT %</div>
        <div className="col-span-2 text-right pr-1">Line</div>
      </div>

      <div>
        {fields.map((f, idx) => {
          const baseUnits = form.getValues(`${name}.${idx}.__computed_base_units`) || 0;
          const net = form.getValues(`${name}.${idx}.__computed_net`) || 0;
          const vat = form.getValues(`${name}.${idx}.__computed_vat`) || 0;
          const gross = form.getValues(`${name}.${idx}.__computed_gross`) || 0;
          const outer = Number(form.getValues(`${name}.${idx}.outer_qty`) || 0);
          const ipo = Number(form.getValues(`${name}.${idx}.items_per_outer`) || 0);
          const unitPrice = Number(form.getValues(`${name}.${idx}.unit_price`) || 0);
          const perCrate = ipo > 0 ? money(unitPrice * ipo) : null;

          return (
            <div key={f.id} className="grid grid-cols-12 items-start px-3 py-2 border-t border-slate-100 hover:bg-slate-50">
              <div className="col-span-4 pr-2">
                <input
                  {...register(`${name}.${idx}.description` as const)}
                  placeholder="e.g. Birra Moretti 330ml"
                  className="w-full bg-white border border-slate-200 rounded-xl px-3 py-2 focus:outline-none focus:ring-2 focus:ring-emerald-300"
                />
                <div className="text-[11px] text-slate-500 mt-1">
                  {ipo > 0 && outer > 0 ? `${outer} × ${ipo} = ${baseUnits} units` : `Set 'Outer' and 'Items/Outer'`}
                </div>
              </div>
              <div className="col-span-1 pr-2">
                <input type="number" step="1" min="0" {...register(`${name}.${idx}.outer_qty` as const, { valueAsNumber: true })}
                  className="w-full text-right bg-white border border-slate-200 rounded-xl px-2 py-2 focus:ring-2 focus:ring-emerald-300" />
              </div>
              <div className="col-span-2 pr-2">
                <input type="number" step="1" min="1" {...register(`${name}.${idx}.items_per_outer` as const, { valueAsNumber: true })}
                  className="w-full text-right bg-white border border-slate-200 rounded-xl px-2 py-2 focus:ring-2 focus:ring-emerald-300" />
                <div className="text-[11px] text-slate-500 mt-1">{perCrate !== null ? `≈ £${perCrate} per crate` : "Set Items/Outer for crate hint"}</div>
              </div>
              <div className="col-span-1 pr-2">
                <input type="number" step="1" min="0" placeholder="ml"
                  {...register(`${name}.${idx}.unit_size` as const, { valueAsNumber: true })}
                  className="w-full text-right bg-white border border-slate-200 rounded-xl px-2 py-2 focus:ring-2 focus:ring-emerald-300" />
              </div>
              <div className="col-span-1 pr-2">
                <input type="number" step="0.01" min="0" {...register(`${name}.${idx}.unit_price` as const, { valueAsNumber: true })}
                  onKeyDown={onKeyDownAddRow}
                  className="w-full text-right bg-white border border-slate-200 rounded-xl px-2 py-2 focus:ring-2 focus:ring-emerald-300" />
              </div>
              <div className="col-span-1 pr-2">
                <input type="number" step="0.1" min="0" {...register(`${name}.${idx}.vat_rate_percent` as const, { valueAsNumber: true })}
                  className="w-full text-right bg-white border border-slate-200 rounded-xl px-2 py-2 focus:ring-2 focus:ring-emerald-300" />
              </div>
              <div className="col-span-2 text-right">
                <div className="text-xs">
                  <div className="text-slate-700">£{net}</div>
                  <div className="text-slate-500">VAT £{vat}</div>
                  <div className="font-semibold text-slate-800">£{gross}</div>
                </div>
                <button type="button" onClick={() => remove(idx)} className="mt-1 text-[11px] text-slate-500 hover:text-slate-700 underline">Remove</button>
              </div>
            </div>
          );
        })}
      </div>

      <div className="px-3 py-2 bg-slate-50 border-t border-slate-200 flex justify-between items-center">
        <button type="button" onClick={() => append({ description: "", outer_qty: 1, items_per_outer: 24, unit_size: null, unit_price: 0, vat_rate_percent: 20 })}
          className="px-3 py-2 rounded-xl bg-slate-100 hover:bg-slate-200">+ Add line</button>
        <div className="text-[11px] text-slate-500">Tip: Press <span className="font-mono">Enter</span> in Unit £ to add a new line.</div>
      </div>
    </div>
  );
}
