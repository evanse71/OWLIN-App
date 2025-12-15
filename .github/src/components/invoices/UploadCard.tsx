// src/components/invoices/UploadCard.tsx
import React, { useRef, useState } from 'react';
import { FRONTEND_FEATURE_OCR_V2, API_BASE_URL } from '@/lib/featureFlags';
import { postOcrV2 } from '@/lib/api/ocrV2';
import type { OcrV2Response } from '@/types/ocr';
import { ErrorNotice } from '@/components/common/ErrorNotice';

type Props = {
  onParsed?: (data: OcrV2Response & { filename: string }) => void; // bubble result upward for cards list
};

export const UploadCard: React.FC<Props> = ({ onParsed }) => {
  const fileInput = useRef<HTMLInputElement | null>(null);
  const [fileName, setFileName] = useState<string>('');
  const [progress, setProgress] = useState<0 | 25 | 50 | 75 | 100>(0);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<OcrV2Response | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const onChooseFile = () => fileInput.current?.click();

  const onFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0];
    if (!f) return;
    setFileName(f.name);
    setError(null);
    setResult(null);

    if (!FRONTEND_FEATURE_OCR_V2) {
      // Default behavior: do NOT call OCR v2; show info so user knows why nothing happened
      setError('OCR v2 is disabled (FRONTEND flag). Enable VITE_FEATURE_OCR_V2=true / NEXT_PUBLIC_FEATURE_OCR_V2=true.');
      return;
    }

    setBusy(true);
    setProgress(25);
    const ac = new AbortController();
    abortRef.current = ac;

    try {
      setProgress(50);
      const json = await postOcrV2(API_BASE_URL, f, ac.signal);
      setProgress(75);

      if (json.status === 'disabled') {
        setError('Backend flag disabled: set FEATURE_OCR_PIPELINE_V2=true on server.');
      } else {
        setResult(json);
        onParsed?.({ ...json, filename: f.name });
      }
      setProgress(100);
    } catch (err: any) {
      setError(err?.message ?? String(err));
      setProgress(0);
    } finally {
      setBusy(false);
      abortRef.current = null;
    }
  };

  const onCancel = () => {
    abortRef.current?.abort();
    setBusy(false);
    setProgress(0);
  };

  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
      {FRONTEND_FEATURE_OCR_V2 ? (
        <div className="mb-3 rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-emerald-800">
          OCR v2 (feature) enabled — uploads will run the new pipeline.
        </div>
      ) : (
        <div className="mb-3 rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-slate-700">
          OCR v2 is off. Toggle <code>VITE_FEATURE_OCR_V2</code>/<code>NEXT_PUBLIC_FEATURE_OCR_V2</code> to test.
        </div>
      )}

      <div className="flex items-center justify-between">
        <div>
          <div className="text-sm text-slate-500">Select a PDF/image</div>
          <div className="text-base font-medium text-slate-900">{fileName || 'No file selected'}</div>
        </div>
        <div className="flex gap-2">
          {!busy ? (
            <button onClick={onChooseFile} className="rounded-xl border px-3 py-2 hover:bg-slate-50">
              Choose file
            </button>
          ) : (
            <button onClick={onCancel} className="rounded-xl border px-3 py-2 hover:bg-slate-50">
              Cancel
            </button>
          )}
        </div>
      </div>

      <input
        ref={fileInput}
        type="file"
        accept=".pdf,image/*"
        className="hidden"
        onChange={onFileChange}
      />

      {/* Progress */}
      <div className="mt-4 h-2 w-full rounded-full bg-slate-100">
        <div
          className="h-2 rounded-full bg-slate-400 transition-all"
          style={{ width: `${progress}%` }}
        />
      </div>

      {/* Result / Error */}
      <div className="mt-4 space-y-3">
        {error && <ErrorNotice error={error} onClear={() => setError(null)} />}
        {result && (
          <div className="rounded-xl border border-slate-200 bg-slate-50 p-3 text-slate-800">
            <div className="flex items-center justify-between">
              <div className="font-semibold">OCR v2 Result</div>
              <div className="rounded-full bg-slate-200 px-2 py-1 text-xs">
                {typeof result.overall_confidence === 'number'
                  ? `Confidence ${(result.overall_confidence * 100).toFixed(0)}%`
                  : 'Confidence n/a'}
              </div>
            </div>
            <div className="mt-2 text-sm">
              {result.artifact_dir ? (
                <div>Artifacts saved under: <code>{result.artifact_dir}</code></div>
              ) : (
                <div>No artifacts path reported.</div>
              )}
              <div className="mt-1">Pages parsed: {result.pages?.length ?? 0}</div>
              {result.trace_id && <div className="mt-1 text-xs text-slate-500">Trace: {result.trace_id}</div>}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
