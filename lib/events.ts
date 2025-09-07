export type OwlinEvent = { type: "INVOICES_SUBMITTED"; payload: { count: number; total_cents: number; at: string } };
export type Listener = (e: OwlinEvent) => void;

const listeners = new Set<Listener>();

export const emit = (e: OwlinEvent) => {
  listeners.forEach(l => {
    try { l(e); } catch {}
  });
};

export const on = (l: Listener) => {
  listeners.add(l);
  return () => { listeners.delete(l); };
}; 