const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8001";

export async function postManualInvoice(body: any) {
  const r = await fetch(`${API_BASE}/manual/invoices`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}
export async function patchManualInvoice(id: string, body: any) {
  const r = await fetch(`${API_BASE}/manual/invoices/${id}`, { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}
export async function postManualDN(body: any) {
  const r = await fetch(`${API_BASE}/manual/delivery-notes`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}
export async function patchManualDN(id: string, body: any) {
  const r = await fetch(`${API_BASE}/manual/delivery-notes/${id}`, { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}
export async function getUnpaired() {
  const r = await fetch(`${API_BASE}/manual/unpaired`);
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}
export async function postPair(body: { invoice_id: string; delivery_note_id: string }) {
  const r = await fetch(`${API_BASE}/manual/pair`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}