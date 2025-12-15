// src/components/invoices/InvoiceCard.tsx
import React, { useState } from 'react';
import type { OcrV2Response } from '@/types/ocr';
import { pct, timeStampISO } from '@/lib/ui/format';
import { OCRDebugPanel } from '@/components/invoices/OCRDebugPanel';

type Props = {
  filename: string;
  ocr?: OcrV2Response | null;   // If present, show OCR summary + debug accordion
};

export const InvoiceCard: React.FC<Props> = ({ filename, ocr }) => {
  const [open, setOpen] = useState(false);

  const overall = ocr?.overall_confidence ?? null;
  const pages = ocr?.pages ?? [];
  const artifact = ocr?.artifact_dir;

  const statusBadge = (() => {
    if (!ocr) return <span className="rounded-full bg-slate-200 px-2 py-0.5 text-xs">uploaded</span>;
    if (ocr.status === 'disabled') return <span className="rounded-full bg-amber-100 px-2 py-0.5 text-xs text-amber-800">OCR off</span>;
    if (ocr.status === 'error') return <span className="rounded-full bg-red-100 px-2 py-0.5 text-xs text-red-800">error</span>;
    return <span className="rounded-full bg-emerald-100 px-2 py-0.5 text-xs text-emerald-800">scanned</span>;
  })();

  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
      <div className="flex items-start justify-between">
        <div>
          <div className="text-sm text-slate-500">Invoice</div>
          <div className="font-medium text-slate-900">{filename}</div>
          <div className="mt-1 text-xs text-slate-500">{timeStampISO()}</div>
        </div>
        <div className="flex items-center gap-2">
          {statusBadge}
          <button
            type="button"
            onClick={() => setOpen((v) => !v)}
            className="rounded-xl border px-2 py-1 text-xs hover:bg-slate-50"
          >
            {open ? 'Hide' : 'Details'}
          </button>
        </div>
      </div>

      {ocr && (
        <div className="mt-3 grid grid-cols-2 gap-3 text-sm">
          <div className="rounded-xl border border-slate-200 bg-slate-50 p-3">
            <div className="text-slate-500">Confidence</div>
            <div className="text-slate-900">{pct(overall)}</div>
          </div>
          <div className="rounded-xl border border-slate-200 bg-slate-50 p-3">
            <div className="text-slate-500">Pages</div>
            <div className="text-slate-900">{pages.length}</div>
          </div>
          <div className="col-span-2 rounded-xl border border-slate-200 bg-slate-50 p-3 text-xs text-slate-700">
            {artifact ? (
              <>
                Artifacts:&nbsp;<code className="select-all">{artifact}</code>
              </>
            ) : (
              'Artifacts path not reported.'
            )}
          </div>
        </div>
      )}

      {open && ocr && pages.length > 0 && (
        <div className="mt-4">
          <OCRDebugPanel pages={pages} artifactDir={artifact} collapsedByDefault={false} />
        </div>
      )}
    </div>
  );
};
