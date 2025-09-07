export type Line = { desc: string; qty: number; unit_price: number; line_total: number; flags: string[] };
export type MatchSuggestion = { invoice_line_idx: number; dn_line_idx: number; score: number };
export type DNCandidate = { id: string; supplier_name?: string; date?: string; score: number };
export type InvoiceBundle = { id: string; meta: Record<string, unknown>; lines: Line[]; dn_candidates: DNCandidate[]; suggestions: MatchSuggestion[]; doc_flags: string[]; }; 