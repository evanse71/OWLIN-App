import React from "react";
import { apiExportInvoices } from "@/lib/api";

export default function BottomActionBar({
  selectedIds, onSave, onCancel
}: {
  selectedIds: string[];
  onSave: () => void;
  onCancel: () => void;
}) {
  const onSend = async () => {
    const r = await apiExportInvoices(selectedIds);
    alert(r.ok ? `Exported to ${r.zip_path}` : "Export failed");
  };
  return (
    <div className="fixed bottom-4 left-1/2 -translate-x-1/2 z-40">
      <div className="rounded-2xl shadow-lg border bg-white/90 backdrop-blur flex gap-3 px-4 py-2">
        <button onClick={onCancel} className="px-3 py-1 rounded-lg border">Cancel</button>
        <button onClick={onSave} className="px-3 py-1 rounded-lg border bg-black text-white">Save</button>
        <button onClick={onSend} className="px-3 py-1 rounded-lg border">Send to Owlin</button>
      </div>
    </div>
  );
}
