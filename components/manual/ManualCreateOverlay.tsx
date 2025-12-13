import React, { useEffect, useRef } from "react";
import InvoiceManualCard from "@/components/manual/InvoiceManualCard";
import DeliveryNoteManualCard from "@/components/manual/DeliveryNoteManualCard";

type Mode = "invoice" | "dn";

type Props = {
  open: boolean;
  mode: Mode;
  onClose: () => void;          // Cancel
  onSaved?: (id: string) => void;
};

export default function ManualCreateOverlay({ open, mode, onClose, onSaved }: Props) {
  const panelRef = useRef<HTMLDivElement>(null);

  // Lock body scroll & mark background inert for SRs
  useEffect(() => {
    if (!open) return;
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    const main = document.getElementById("__owlin-main");
    if (main) main.setAttribute("aria-hidden", "true");
    
    // Focus the first input on open
    setTimeout(() => {
      const el = panelRef.current?.querySelector<HTMLElement>(
        'input, select, textarea, button:not([disabled])'
      );
      el?.focus();
    }, 0);
    
    return () => {
      document.body.style.overflow = prev;
      if (main) main.removeAttribute("aria-hidden");
    };
  }, [open]);

  // ESC to cancel
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  // Focus trap - keep focus inside overlay
  useEffect(() => {
    if (!open) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key !== "Tab") return;
      const nodes = panelRef.current?.querySelectorAll(
        'a, button, input, select, textarea, [tabindex]:not([tabindex="-1"])'
      );
      if (!nodes || nodes.length === 0) return;
      const focusables = Array.from(nodes) as HTMLElement[];
      const enabledFocusables = focusables.filter(n => !n.hasAttribute('disabled'));
      const first = enabledFocusables[0];
      const last = enabledFocusables[enabledFocusables.length - 1];
      const active = document.activeElement as HTMLElement | null;
      if (e.shiftKey && active === first) { e.preventDefault(); last?.focus(); }
      else if (!e.shiftKey && active === last) { e.preventDefault(); first?.focus(); }
    };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, [open]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-[1000] flex items-start justify-center bg-black/40"
         role="dialog" aria-modal="true"
         aria-label={mode === "invoice" ? "Create Invoice" : "Create Delivery Note"}>
      {/* backdrop blocks clicks; explicit Cancel only */}
      <div className="absolute inset-0" />

      <div ref={panelRef}
           className="relative mt-8 mb-8 w-[min(1100px,calc(100vw-2rem))] max-h-[calc(100vh-4rem)] overflow-auto rounded-2xl bg-white shadow-xl border border-slate-200">
        <div className="sticky top-0 z-10 flex items-center justify-between px-5 py-3 border-b bg-white/95 backdrop-blur-sm">
          <h2 className="text-lg font-semibold text-slate-800">
            {mode === "invoice" ? "Create Invoice (Manual)" : "Create Delivery Note (Manual)"}
          </h2>
          <button onClick={onClose} className="px-3 py-1.5 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-700">
            Cancel
          </button>
        </div>

        <div className="p-5">
          {mode === "invoice"
            ? <InvoiceManualCard variant="overlay" onSaved={onSaved} onCancel={onClose}/>
            : <DeliveryNoteManualCard variant="overlay" onSaved={onSaved} onCancel={onClose}/>}
        </div>
      </div>
    </div>
  );
}
