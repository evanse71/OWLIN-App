"use client";
import React, { useEffect, useMemo, useState } from "react";
import { DeliveryNote, DeliveryNoteCard } from "./DeliveryNoteCard";
import { DocumentPairingSuggestionCard } from "./DocumentPairingSuggestionCard";
import { ConfidenceBadge } from "./ConfidenceBadge";
import { ChevronDown, ChevronUp, RefreshCcw, Search, Filter, AlertTriangle } from "lucide-react";
import { formatISO } from "date-fns";

interface DeliveryNotesPanelProps {
  selectedInvoiceId?: string | null;
  siteId?: string | null;
  onPaired?: (dnId: string, invoiceId: string) => void;
}

type FetchState = "idle" | "loading" | "error" | "ready";


export const DeliveryNotesPanel: React.FC<DeliveryNotesPanelProps> = ({
  selectedInvoiceId,
  siteId,
  onPaired
}) => {
  const [query, setQuery] = useState("");
  const [supplier, setSupplier] = useState<string | null>(null);
  const [onlyUnmatched, setOnlyUnmatched] = useState(true);
  const [onlyWithIssues, setOnlyWithIssues] = useState(false);
  const [fromDate, setFromDate] = useState<string | null>(null);
  const [toDate, setToDate] = useState<string | null>(null);

  const [unmatched, setUnmatched] = useState<DeliveryNote[]>([]);
  const [recentMatched, setRecentMatched] = useState<DeliveryNote[]>([]);
  const [state, setState] = useState<FetchState>("idle");
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [showMatched, setShowMatched] = useState(false);

  const filters = useMemo(() => ({
    query,
    supplier,
    onlyUnmatched,
    onlyWithIssues,
    fromDate,
    toDate,
    siteId: siteId ?? null
  }), [query, supplier, onlyUnmatched, onlyWithIssues, fromDate, toDate, siteId]);

  const load = async () => {
    try {
      setState("loading");
      setErrorMsg(null);

      // Mock data for now - replace with actual API calls
      const mockUnmatched: DeliveryNote[] = [
        {
          id: "123",
          supplier_name: "Booker",
          delivery_date: "2025-01-15",
          total_value: 126.45,
          item_count: 14,
          status: "unmatched",
          confidence: 92,
          suggested_invoice: {
            invoice_id: "987",
            score: 0.86,
            reason: "Date+Supplier+Total within tolerance"
          }
        },
        {
          id: "124",
          supplier_name: "Tesco",
          delivery_date: "2025-01-14",
          total_value: 89.30,
          item_count: 8,
          status: "unmatched",
          confidence: 78
        }
      ];

      const mockMatched: DeliveryNote[] = [
        {
          id: "121",
          supplier_name: "Sainsbury's",
          delivery_date: "2025-01-13",
          total_value: 156.20,
          item_count: 12,
          status: "matched",
          confidence: 95
        }
      ];

      // Simulate API delay
      await new Promise(resolve => setTimeout(resolve, 500));

      setUnmatched(mockUnmatched);
      setRecentMatched(mockMatched);
      setState("ready");
    } catch (err: any) {
      setState("error");
      setErrorMsg(err?.message || "Failed to fetch delivery notes");
    }
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filters.query, filters.supplier, filters.onlyWithIssues, filters.fromDate, filters.toDate, filters.siteId, filters.onlyUnmatched]);

  const handlePair = async (noteId: string) => {
    if (!selectedInvoiceId) return;
    try {
      // Mock pairing - replace with actual API call
      await new Promise(resolve => setTimeout(resolve, 300));
      
      // optimistic update
      setUnmatched((prev) => prev.filter(n => n.id !== noteId));
      onPaired?.(noteId, selectedInvoiceId);
    } catch (err: any) {
      setErrorMsg(err?.message || "Pairing failed");
    }
  };

  const handleUnpair = async (noteId: string) => {
    try {
      // Mock unpairing - replace with actual API call
      await new Promise(resolve => setTimeout(resolve, 300));
      
      // refresh lists
      await load();
    } catch (err: any) {
      setErrorMsg(err?.message || "Unpair failed");
    }
  };

  const disabledPairingReason = !selectedInvoiceId ? "Select an invoice on the left to enable pairing" : null;

  return (
    <aside className="lg:sticky lg:top-20 lg:h-[calc(100vh-6rem)] lg:overflow-auto">
      <div className="rounded-2xl border border-slate-200 bg-white shadow-sm">
        {/* Header */}
        <div className="flex items-center justify-between rounded-t-2xl border-b border-slate-200 px-4 py-3">
          <div className="font-semibold text-slate-800">Delivery Notes</div>
          <button
            onClick={load}
            className="inline-flex items-center gap-1 rounded-xl border border-slate-200 px-2 py-1.5 text-xs text-slate-700 hover:bg-slate-50"
            title="Refresh"
          >
            <RefreshCcw className="h-3.5 w-3.5" />
            Refresh
          </button>
        </div>

        {/* Filters */}
        <div className="px-4 pt-3 pb-2">
          <div className="flex items-center gap-2">
            <div className="relative flex-1">
              <Search className="pointer-events-none absolute left-2 top-2.5 h-4 w-4 text-slate-400" />
              <input
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Search delivery notes…"
                className="w-full rounded-xl border border-slate-200 bg-white py-2 pl-8 pr-3 text-sm text-slate-800 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-slate-200"
              />
            </div>
            <button
              className="inline-flex items-center gap-1 rounded-xl border border-slate-200 px-3 py-2 text-sm text-slate-700 hover:bg-slate-50"
              title="Filters"
            >
              <Filter className="h-4 w-4" />
              Filters
            </button>
          </div>

          <div className="mt-2 grid grid-cols-2 gap-2">
            <input
              type="date"
              value={fromDate ?? ""}
              onChange={(e) => setFromDate(e.target.value ? formatISO(new Date(e.target.value), { representation: "date" }) : null)}
              className="w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm text-slate-800 focus:outline-none focus:ring-2 focus:ring-slate-200"
              aria-label="From date"
            />
            <input
              type="date"
              value={toDate ?? ""}
              onChange={(e) => setToDate(e.target.value ? formatISO(new Date(e.target.value), { representation: "date" }) : null)}
              className="w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm text-slate-800 focus:outline-none focus:ring-2 focus:ring-slate-200"
              aria-label="To date"
            />
          </div>

          <div className="mt-2 flex items-center justify-between">
            <label className="inline-flex items-center gap-2 text-sm text-slate-700">
              <input 
                type="checkbox" 
                checked={onlyUnmatched} 
                onChange={(e) => setOnlyUnmatched(e.target.checked)}
                aria-label="Show only unmatched delivery notes"
              />
              Only unmatched
            </label>
            <label className="inline-flex items-center gap-2 text-sm text-slate-700">
              <input 
                type="checkbox" 
                checked={onlyWithIssues} 
                onChange={(e) => setOnlyWithIssues(e.target.checked)}
                aria-label="Show only delivery notes with issues"
              />
              Only with issues
            </label>
          </div>
        </div>

        {/* Error Banner */}
        {state === "error" && (
          <div className="mx-4 mb-2 rounded-xl border border-amber-200 bg-amber-50 p-2 text-sm text-amber-800">
            <div className="flex items-center gap-2">
              <AlertTriangle className="h-4 w-4" />
              {errorMsg || "Something went wrong"}
            </div>
          </div>
        )}

        {/* Unmatched List */}
        <div className="px-4 pb-2">
          <div className="mt-1 text-xs font-medium uppercase tracking-wide text-slate-500">Unmatched</div>

          {state === "loading" && (
            <div className="mt-3 space-y-2">
              {[...Array(4)].map((_, i) => (
                <div key={i} className="h-20 animate-pulse rounded-2xl bg-slate-100" />
              ))}
            </div>
          )}

          {state === "ready" && unmatched.length === 0 && (
            <div className="mt-3 rounded-xl border border-slate-200 bg-slate-50 p-3 text-sm text-slate-600">
              Nothing here. New delivery notes will appear as they're scanned.  
              {selectedInvoiceId ? "" : " Select an invoice to enable quick pairing."}
            </div>
          )}

          {state === "ready" && unmatched.length > 0 && (
            <div className="mt-3 space-y-3">
              {unmatched.map((n) => (
                <div key={n.id} className="space-y-2">
                  {/* Suggestion card if present */}
                  {n.suggested_invoice && selectedInvoiceId && n.suggested_invoice.invoice_id !== selectedInvoiceId && (
                    <DocumentPairingSuggestionCard
                      left={{
                        title: `DN-${n.id}`,
                        subtitle: n.supplier_name || "Unknown supplier",
                        meta: `${n.item_count ?? 0} items · £${(n.total_value ?? 0).toFixed(2)}`
                      }}
                      right={{
                        title: `INV-${n.suggested_invoice.invoice_id}`,
                        subtitle: "Suggested by Owlin",
                        meta: `Score ${(n.suggested_invoice.score * 100).toFixed(0)}%`
                      }}
                      score={n.suggested_invoice.score}
                      onConfirm={async () => {
                        // Mock pairing - replace with actual API call
                        await new Promise(resolve => setTimeout(resolve, 300));
                        setUnmatched((prev) => prev.filter(x => x.id !== n.id));
                      }}
                      onReject={() => {
                        // hide suggestion locally (simple client-side dismiss)
                        setUnmatched((prev) => prev.map(x => x.id === n.id ? ({ ...x, suggested_invoice: null }) : x));
                      }}
                    />
                  )}

                  <DeliveryNoteCard
                    note={n}
                    compact
                    selectedInvoiceId={selectedInvoiceId}
                    onPair={handlePair}
                    onUnpair={handleUnpair}
                    onView={() => {/* open right-side detail modal or drawer if you have it */}}
                    disabledPairingReason={disabledPairingReason}
                  />
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Recently Matched */}
        <div className="mt-2 border-t border-slate-200 px-4 pb-4">
          <button
            onClick={() => setShowMatched((v) => !v)}
            className="mt-3 inline-flex w-full items-center justify-between rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-700 hover:bg-slate-100"
          >
            <span className="font-medium">Recently matched</span>
            {showMatched ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
          </button>

          {showMatched && (
            <div className="mt-3 space-y-3">
              {recentMatched.length === 0 ? (
                <div className="rounded-xl border border-slate-200 bg-white p-3 text-sm text-slate-600">
                  No recent matches.
                </div>
              ) : recentMatched.map((n) => (
                <DeliveryNoteCard
                  key={n.id}
                  note={n}
                  compact
                  selectedInvoiceId={selectedInvoiceId}
                  onPair={handlePair}
                  onUnpair={handleUnpair}
                  onView={() => {}}
                  disabledPairingReason={null}
                />
              ))}
            </div>
          )}
        </div>
      </div>
    </aside>
  );
};
