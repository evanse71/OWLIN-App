// src/components/common/ErrorNotice.tsx
import React from 'react';

type Props = { title?: string; error: string; onClear?: () => void };

export const ErrorNotice: React.FC<Props> = ({ title = 'Something went wrong', error, onClear }) => {
  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(error);
      alert('Error copied to clipboard');
    } catch {
      // ignore
    }
  };
  return (
    <div className="rounded-xl border border-red-200 bg-red-50 p-3 text-red-800">
      <div className="flex items-start justify-between">
        <div>
          <div className="font-semibold">{title}</div>
          <pre className="mt-1 whitespace-pre-wrap text-sm">{error}</pre>
        </div>
        <div className="ml-3 flex gap-2">
          <button onClick={handleCopy} className="rounded-lg border px-2 py-1 text-xs hover:bg-white">
            Copy error
          </button>
          {onClear && (
            <button onClick={onClear} className="rounded-lg border px-2 py-1 text-xs hover:bg-white">
              Dismiss
            </button>
          )}
        </div>
      </div>
    </div>
  );
};
