import React, { useState } from "react";
import { MoreHorizontal, Link as LinkIcon, Unlink, Eye } from "lucide-react";
import { format } from "date-fns";
import { ConfidenceBadge } from "./ConfidenceBadge";

export interface DeliveryNote {
  id: string;
  supplier_name?: string | null;
  delivery_date?: string | null; // ISO
  created_at?: string | null;    // fallback if no delivery_date
  total_value?: number | null;
  item_count?: number | null;
  status?: "unmatched" | "matched" | "flagged" | "error" | "pending";
  confidence?: number | null; // 0-100
  suggested_invoice?: {
    invoice_id: string;
    score: number; // 0-1
    reason?: string;
  } | null;
}

interface Props {
  note: DeliveryNote;
  compact?: boolean;
  selectedInvoiceId?: string | null;
  onPair?: (noteId: string) => void;
  onUnpair?: (noteId: string) => void;
  onView?: (noteId: string) => void;
  disabledPairingReason?: string | null;
}

function Badge({ children, tone = "default" }: { children: React.ReactNode; tone?: "default" | "success" | "warning" | "error" | "muted" }) {
  const toneClasses =
    tone === "success" ? "bg-emerald-50 text-emerald-700 border-emerald-200" :
    tone === "warning" ? "bg-amber-50 text-amber-700 border-amber-200" :
    tone === "error"   ? "bg-rose-50 text-rose-700 border-rose-200" :
    tone === "muted"   ? "bg-slate-50 text-slate-600 border-slate-200" :
                         "bg-slate-50 text-slate-700 border-slate-200";
  return (
    <span className={`inline-flex items-center rounded-full border px-2 py-0.5 text-xs font-medium ${toneClasses}`}>
      {children}
    </span>
  );
}

export const DeliveryNoteCard: React.FC<Props> = ({
  note,
  compact,
  selectedInvoiceId,
  onPair,
  onUnpair,
  onView,
  disabledPairingReason
}) => {
  const [menuOpen, setMenuOpen] = useState(false);
  const date = note.delivery_date || note.created_at || null;
  const dateLabel = date ? format(new Date(date), "dd MMM yyyy") : "—";

  const statusTone =
    note.status === "matched" ? "success" :
    note.status === "flagged" ? "warning" :
    note.status === "error"   ? "error"   :
    note.status === "unmatched" ? "muted" : "default";

  const canPair = !!selectedInvoiceId && note.status !== "matched";
  const disableText = disabledPairingReason || (selectedInvoiceId ? null : "Select an invoice on the left to enable pairing");

  return (
    <div className={`group rounded-2xl border border-slate-200 bg-white shadow-sm hover:shadow transition ${
      compact ? "p-3" : "p-4"
    }`}>
      <div className="flex items-start justify-between">
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <code className="text-xs text-slate-500">DN-{note.id}</code>
            <Badge tone={statusTone}>{note.status ?? "unknown"}</Badge>
          </div>
          <div className="mt-1 font-semibold text-slate-800 truncate">
            {note.supplier_name || "Unknown supplier"}
          </div>
          <div className="mt-0.5 text-sm text-slate-600">
            {dateLabel}
          </div>
        </div>

        <div className="ml-3 text-right">
          <div className="text-sm font-semibold text-slate-900">
            {typeof note.total_value === "number" ? `£${note.total_value.toFixed(2)}` : "—"}
          </div>
          <div className="text-xs text-slate-500">
            {typeof note.item_count === "number" ? `${note.item_count} items` : "—"}
          </div>
          {typeof note.confidence === "number" && (
            <div className="mt-1">
              <ConfidenceBadge score={note.confidence / 100} size="xs" />
            </div>
          )}
        </div>
      </div>

      {/* Suggested match hint */}
      {note.suggested_invoice && note.status !== "matched" && (
        <div className="mt-3 rounded-xl border border-slate-200 bg-slate-50 p-2">
          <div className="text-xs text-slate-600">
            Suggested invoice: <span className="font-medium">INV-{note.suggested_invoice.invoice_id}</span> · score {(note.suggested_invoice.score * 100).toFixed(0)}%
          </div>
          {note.suggested_invoice.reason && (
            <div className="mt-1 text-xs text-slate-500">Reason: {note.suggested_invoice.reason}</div>
          )}
        </div>
      )}

      <div className="mt-3 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <button
            className="inline-flex items-center rounded-xl border border-slate-200 px-3 py-1.5 text-sm text-slate-700 hover:bg-slate-50"
            onClick={() => onView?.(note.id)}
          >
            <Eye className="mr-1 h-4 w-4" />
            View
          </button>

          <button
            disabled={!canPair}
            title={!canPair ? disableText ?? undefined : undefined}
            onClick={() => canPair && onPair?.(note.id)}
            className={`inline-flex items-center rounded-xl px-3 py-1.5 text-sm ${
              canPair
                ? "bg-slate-800 text-white hover:bg-slate-900"
                : "bg-slate-100 text-slate-400 cursor-not-allowed"
            }`}
          >
            <LinkIcon className="mr-1 h-4 w-4" />
            Pair
          </button>
        </div>

        <div className="relative">
          <button
            onClick={() => setMenuOpen((v) => !v)}
            className="inline-flex items-center rounded-xl border border-slate-200 px-2.5 py-1.5 text-sm text-slate-700 hover:bg-slate-50"
            title="More options"
            aria-label="More options"
          >
            <MoreHorizontal className="h-4 w-4" />
          </button>
          {menuOpen && (
            <div className="absolute right-0 z-10 mt-2 w-40 rounded-xl border border-slate-200 bg-white p-1 shadow-lg">
              <button
                onClick={() => { setMenuOpen(false); onUnpair?.(note.id); }}
                className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-left text-sm text-slate-700 hover:bg-slate-50 disabled:text-slate-300"
                disabled={note.status !== "matched"}
                title={note.status !== "matched" ? "Not matched" : undefined}
              >
                <Unlink className="h-4 w-4" />
                Unpair
              </button>
              <button className="block w-full rounded-lg px-3 py-2 text-left text-sm text-slate-500 hover:bg-slate-50" disabled>
                Flag issue (TBD)
              </button>
              <button className="block w-full rounded-lg px-3 py-2 text-left text-sm text-slate-500 hover:bg-slate-50" disabled>
                Delete (TBD)
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
