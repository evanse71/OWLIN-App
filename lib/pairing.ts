export type PairSuggestion = { 
  score: number; 
  delivery_note: {
    id: string | number; 
    code?: string; 
    supplier?: string; 
    date?: string; 
    amount?: number;
  };
};

export async function fetchPairingSuggestions(invoiceId: string) {
  const res = await fetch(`/api/invoices/${invoiceId}/pairing_suggestions`);
  if (!res.ok) return [];
  const data: PairSuggestion[] = await res.json();
  return data ?? [];
} 