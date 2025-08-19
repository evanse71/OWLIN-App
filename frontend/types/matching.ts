export interface ConfidenceBreakdown {
  supplier: number;
  date: number;
  line_items: number;
  value: number;
}

export interface MatchCandidate {
  delivery_note_id: string;
  confidence: number;
  breakdown: ConfidenceBreakdown;
  delivery_note?: {
    supplier_name: string;
    delivery_date: string;
    total_amount: number;
    items: Array<{
      description: string;
      qty: number;
      unit_price: number;
      total: number;
    }>;
  };
}

export interface MatchCandidatesResponse {
  invoice_id: string;
  candidate_delivery_notes: MatchCandidate[];
}

export interface MatchConfirmRequest {
  invoice_id: string;
  delivery_note_id: string;
}

export interface MatchRejectRequest {
  invoice_id: string;
  delivery_note_id: string;
}

export interface MatchConfirmResponse {
  status: 'confirmed' | 'rejected';
  confidence: number;
}

export interface MatchRejectResponse {
  status: 'rejected';
}

export interface RetryLateResponse {
  new_matches_found: number;
  message: string;
}

export interface MatchingStats {
  unmatched_invoices: number;
  unmatched_delivery_notes: number;
  confirmed_matches: number;
  rejected_matches: number;
} 

export interface MatchReason {
  code: string;
  detail: string;
  weight: number;
}

export interface LineDiff {
  id: string;
  invoice_line_id?: number;
  delivery_line_id?: number;
  status: "ok" | "qty_mismatch" | "price_mismatch" | "missing_on_dn" | "missing_on_inv";
  confidence: number;
  qty_invoice?: number;
  qty_dn?: number;
  qty_uom?: string;
  price_invoice?: number;
  price_dn?: number;
  reasons: MatchReason[];
}

export interface MatchingPair {
  id: string;
  invoice_id: number;
  delivery_note_id: number;
  status: "matched" | "partial" | "unmatched" | "conflict";
  confidence: number;
  reasons: MatchReason[];
  line_diffs: LineDiff[];
}

export interface MatchingSummary {
  totals: Record<string, number>;
  pairs: MatchingPair[];
}

export interface MatchingConfig {
  date_window_days: number;
  amount_proximity_pct: number;
  qty_tol_rel: number;
  qty_tol_abs: number;
  price_tol_rel: number;
  fuzzy_desc_threshold: number;
} 