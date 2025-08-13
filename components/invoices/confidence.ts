export type FieldConf = Record<string, number | undefined>;
export function computeOverallConfidence(field_confidence: FieldConf, line_items?: any[]) {
  // Weights to bias important fields; adjust if needed
  const weights: Record<string, number> = {
    supplier_name: 2,
    invoice_number: 2,
    invoice_date: 2,
    total_amount: 3,
    addresses: 1.5,
    line_items: 3,
  };

  const entries: Array<{k:string; v:number; w:number}> = [];
  for (const [k, v] of Object.entries(field_confidence || {})) {
    const val = typeof v === "number" ? Math.max(0, Math.min(1, v)) : 0;
    entries.push({ k, v: val, w: weights[k] ?? 1 });
  }

  // If items have per-row confidence, blend average as line_items
  if (line_items && line_items.length) {
    const vals = line_items
      .map((li: any) => typeof li?.confidence === "number" ? Math.max(0, Math.min(1, li.confidence)) : undefined)
      .filter((x: number | undefined): x is number => typeof x === "number");
    if (vals.length) {
      const avg = vals.reduce((a,b)=>a+b,0) / vals.length;
      entries.push({ k: "line_items", v: avg, w: weights["line_items"] ?? 3 });
    }
  }

  const num = entries.reduce((acc, e) => acc + e.v * e.w, 0);
  const den = entries.reduce((acc, e) => acc + e.w, 0) || 1;
  const overall = num / den;

  // pick 3 weakest signals for tooltip
  const weakest = entries
    .filter(e => isFinite(e.v))
    .sort((a,b)=>a.v-b.v)
    .slice(0, 3)
    .map(e => `${e.k}: ${(e.v*100).toFixed(0)}%`);

  return { overall, weakest };
} 