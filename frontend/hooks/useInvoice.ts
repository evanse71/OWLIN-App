import useSWR from "swr";
import type { InvoiceBundle } from "@/types/invoice";
const fetcher = (u: string) => fetch(u).then(r => { if (!r.ok) throw new Error(`HTTP ${r.status}`); return r.json(); });
export function useInvoice(id: string) {
  const { data, error, isLoading, mutate } = useSWR<InvoiceBundle>(`/api/invoices/${id}`, fetcher);
  return { invoice: data, error, isLoading, refresh: mutate };
} 