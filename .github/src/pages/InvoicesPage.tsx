// src/pages/InvoicesPage.tsx
import React, { useState } from 'react';
import { UploadCard } from '@/components/invoices/UploadCard';
import { InvoiceCard } from '@/components/invoices/InvoiceCard';
import type { OcrV2Response } from '@/types/ocr';

type ParsedDoc = OcrV2Response & { filename: string };

export default function InvoicesPage() {
  const [parsed, setParsed] = useState<ParsedDoc[]>([]);

  return (
    <div className="mx-auto max-w-6xl p-6">
      <h1 className="text-2xl font-semibold text-slate-900">Invoices</h1>

      <div className="mt-4 grid gap-6 lg:grid-cols-2">
        <UploadCard onParsed={(data) => setParsed((prev) => [data, ...prev])} />
        <div className="space-y-4">
          {parsed.length === 0 ? (
            <div className="rounded-2xl border border-slate-200 bg-white p-4 text-slate-600">
              No OCR v2 results this session. Upload a PDF to begin.
            </div>
          ) : (
            parsed.map((p, idx) => (
              <InvoiceCard key={`${p.filename}-${idx}`} filename={p.filename} ocr={p} />
            ))
          )}
        </div>
      </div>
    </div>
  );
}
