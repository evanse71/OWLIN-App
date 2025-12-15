// src/components/invoices/OCRDebugPanel.tsx
import React, { useState } from 'react';
import type { OcrPage, OcrBlock } from '@/types/ocr';
import { pct } from '@/lib/ui/format';

type Props = {
  pages: OcrPage[];
  artifactDir?: string;
  collapsedByDefault?: boolean;
};

export const OCRDebugPanel: React.FC<Props> = ({
  pages,
  artifactDir,
  collapsedByDefault = true,
}) => {
  const [open, setOpen] = useState(!collapsedByDefault);

  return (
    <div className="rounded-2xl border border-slate-200 bg-white">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center justify-between rounded-2xl px-4 py-3 text-left hover:bg-slate-50"
      >
        <div className="flex items-center gap-2">
          <span className="text-sm font-semibold text-slate-900">OCR Debug</span>
          <span className="rounded-full bg-slate-200 px-2 py-0.5 text-xs text-slate-700">pages {pages.length}</span>
        </div>
        <span className="text-slate-500">{open ? '▾' : '▸'}</span>
      </button>

      {open && (
        <div className="divide-y divide-slate-100">
          {artifactDir && (
            <div className="px-4 py-3 text-xs text-slate-600">
              Artifacts: <code className="select-all">{artifactDir}</code>
            </div>
          )}

          {pages.map((p) => (
            <div key={p.page_num} className="px-4 py-3">
              <div className="mb-2 flex items-center justify-between">
                <div className="text-sm font-medium text-slate-900">Page {p.page_num}</div>
                <div className="rounded-full bg-slate-200 px-2 py-0.5 text-xs text-slate-700">
                  conf {pct(p.confidence)}
                </div>
              </div>
              <div className="space-y-2">
                {p.blocks.length === 0 && (
                  <div className="rounded-lg border border-slate-200 bg-slate-50 p-2 text-xs text-slate-600">
                    No blocks.
                  </div>
                )}
                {p.blocks.map((b: OcrBlock, i: number) => (
                  <div
                    key={i}
                    className="rounded-lg border border-slate-200 bg-slate-50 p-2"
                  >
                    <div className="mb-1 flex items-center justify-between">
                      <div className="text-xs font-semibold text-slate-800">{b.type}</div>
                      <div className="rounded bg-slate-200 px-2 py-0.5 text-[10px] text-slate-700">
                        conf {pct(b.confidence)}
                      </div>
                    </div>
                    <div className="mb-1 text-[10px] text-slate-500">
                      bbox [{b.bbox.join(', ')}]
                    </div>
                    <pre className="whitespace-pre-wrap break-words text-xs text-slate-900">
                      {b.ocr_text || '—'}
                    </pre>
                    {Array.isArray(b.table_data) && b.table_data.length > 0 && (
                      <div className="mt-2 overflow-x-auto">
                        <table className="w-full min-w-[360px] text-left text-xs">
                          <tbody>
                            {b.table_data.map((row, ri) => (
                              <tr key={ri} className="border-t border-slate-200">
                                {row.map((cell, ci) => (
                                  <td key={ci} className="px-2 py-1 align-top">{cell}</td>
                                ))}
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
