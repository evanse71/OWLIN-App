import React, { useRef, useState } from 'react';

interface ParsedField {
  value: string;
  confidence: number;
}

interface UploadedReceipt {
  file: File;
  status: 'uploading' | 'success' | 'parsing' | 'parsed' | 'error';
  error?: string;
  parsedData?: {
    store_name?: string;
    store_name_confidence?: number;
    purchase_date?: string;
    purchase_date_confidence?: number;
    total_amount?: string;
    total_amount_confidence?: number;
    confidence_score?: number;
  };
  corrections?: {
    store_name?: string;
    purchase_date?: string;
    total_amount?: string;
  };
}

const ReceiptsUploadPanel: React.FC = () => {
  const [receipts, setReceipts] = useState<UploadedReceipt[]>([]);
  const [submitted, setSubmitted] = useState<UploadedReceipt[]>([]);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files) return;
    const newReceipts: UploadedReceipt[] = Array.from(files).map((file) => ({ file, status: 'uploading' }));
    setReceipts((prev) => [...prev, ...newReceipts]);
    for (let i = 0; i < files.length; i++) {
      await uploadAndParseReceipt(files[i]);
    }
  };

  const uploadAndParseReceipt = async (file: File) => {
    updateReceiptStatus(file, 'uploading');
    const formData = new FormData();
    formData.append('file', file);
    try {
      const uploadRes = await fetch('/api/upload/receipt', {
        method: 'POST',
        body: formData,
      });
      if (!uploadRes.ok) throw new Error('Upload failed');
      updateReceiptStatus(file, 'success');
      updateReceiptStatus(file, 'parsing');
      const parseForm = new FormData();
      parseForm.append('file', file);
      const parseRes = await fetch('/api/ocr/parse-receipt', {
        method: 'POST',
        body: parseForm,
      });
      if (!parseRes.ok) throw new Error('OCR parsing failed');
      const data = await parseRes.json();
      // Simulate per-field confidence (for demo; replace with real backend values if available)
      const parsedData = {
        ...data,
        store_name_confidence: data.confidence_score || 100,
        purchase_date_confidence: data.confidence_score || 100,
        total_amount_confidence: data.confidence_score || 100,
      };
      updateReceiptStatus(file, 'parsed', undefined, parsedData);
    } catch (err: any) {
      updateReceiptStatus(file, 'error', err.message || 'Unknown error');
    }
  };

  const updateReceiptStatus = (
    file: File,
    status: UploadedReceipt['status'],
    error?: string,
    parsedData?: any
  ) => {
    setReceipts((prev) =>
      prev.map((r) =>
        r.file === file
          ? { ...r, status, error, parsedData }
          : r
      )
    );
  };

  const handleCorrectionChange = (file: File, field: string, value: string) => {
    setReceipts((prev) =>
      prev.map((r) =>
        r.file === file
          ? { ...r, corrections: { ...r.corrections, [field]: value } }
          : r
      )
    );
  };

  const triggerFileInput = () => {
    inputRef.current?.click();
  };

  const handleSubmit = (file: File) => {
    const receipt = receipts.find((r) => r.file === file);
    if (receipt) {
      setSubmitted((prev) => [...prev, receipt]);
    }
  };

  const isFieldLowConfidence = (confidence?: number) => confidence !== undefined && confidence < 70;

  return (
    <div className="p-8">
      <div className="bg-white/95 backdrop-blur-xl border-2 border-dashed border-slate-400/40 rounded-2xl shadow-md p-8 flex flex-col items-center justify-center text-center transition-all duration-300 ease-in-out hover:border-blue-600/60 hover:shadow-xl group focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-opacity-75">
        <h3 className="text-xl font-semibold text-slate-900 mb-2">Upload Receipts</h3>
        <p className="text-sm text-slate-600 mb-6">PDF, PNG, JPG — Max 10MB per file</p>
        <button
          className="bg-blue-600 text-white border-none py-3 px-6 rounded-lg text-sm font-medium cursor-pointer shadow-md transition-all duration-200 ease-in-out hover:bg-blue-700 hover:-translate-y-px hover:shadow-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-opacity-75 flex items-center gap-2"
          onClick={triggerFileInput}
        >
          Browse Files
        </button>
        <input
          type="file"
          ref={inputRef}
          onChange={handleFileChange}
          className="hidden"
          accept=".pdf,.jpg,.jpeg,.png"
          multiple
        />
      </div>
      {receipts.length > 0 && (
        <div className="mt-8">
          <h2 className="text-xl font-semibold text-slate-900 mb-4">📁 Uploaded Receipts</h2>
          <ul className="list-none p-0 m-0">
            {receipts.map((r, idx) => (
              <li key={idx} className="flex flex-col md:flex-row justify-between items-start md:items-center text-sm text-slate-700 py-2 border-b border-gray-200 last:border-b-0">
                <div className="flex-1 min-w-0">
                  <div className="font-medium truncate">{r.file.name}</div>
                  <div className="text-xs text-slate-500">{(r.file.size / 1024).toFixed(1)} KB</div>
                  {r.status === 'uploading' && <span className="text-blue-600">Uploading...</span>}
                  {r.status === 'success' && <span className="text-green-600">Uploaded</span>}
                  {r.status === 'parsing' && <span className="text-yellow-600">Parsing...</span>}
                  {r.status === 'parsed' && r.parsedData && (
                    <div className="mt-2 bg-green-50 border border-green-200 rounded p-2">
                      <div>
                        <b>Store:</b>{' '}
                        {isFieldLowConfidence(r.parsedData.store_name_confidence) ? (
                          <input
                            className="border rounded px-1 text-sm ml-1"
                            value={r.corrections?.store_name ?? r.parsedData.store_name ?? ''}
                            onChange={e => handleCorrectionChange(r.file, 'store_name', e.target.value)}
                          />
                        ) : (
                          <span>{r.parsedData.store_name || '-'}</span>
                        )}
                        <span className="ml-2 text-xs text-gray-500">({r.parsedData.store_name_confidence || '-'}%)</span>
                      </div>
                      <div>
                        <b>Date:</b>{' '}
                        {isFieldLowConfidence(r.parsedData.purchase_date_confidence) ? (
                          <input
                            className="border rounded px-1 text-sm ml-1"
                            value={r.corrections?.purchase_date ?? r.parsedData.purchase_date ?? ''}
                            onChange={e => handleCorrectionChange(r.file, 'purchase_date', e.target.value)}
                          />
                        ) : (
                          <span>{r.parsedData.purchase_date || '-'}</span>
                        )}
                        <span className="ml-2 text-xs text-gray-500">({r.parsedData.purchase_date_confidence || '-'}%)</span>
                      </div>
                      <div>
                        <b>Amount:</b>{' '}
                        {isFieldLowConfidence(r.parsedData.total_amount_confidence) ? (
                          <input
                            className="border rounded px-1 text-sm ml-1"
                            value={r.corrections?.total_amount ?? r.parsedData.total_amount ?? ''}
                            onChange={e => handleCorrectionChange(r.file, 'total_amount', e.target.value)}
                          />
                        ) : (
                          <span>{r.parsedData.total_amount || '-'}</span>
                        )}
                        <span className="ml-2 text-xs text-gray-500">({r.parsedData.total_amount_confidence || '-'}%)</span>
                      </div>
                      <div><b>Confidence:</b> {r.parsedData.confidence_score || '-'}%</div>
                      <button
                        className="mt-2 bg-blue-600 text-white px-3 py-1 rounded text-xs font-medium hover:bg-blue-700"
                        onClick={() => handleSubmit(r.file)}
                        disabled={submitted.some(s => s.file === r.file)}
                      >
                        {submitted.some(s => s.file === r.file) ? 'Submitted' : 'Submit to Owlin'}
                      </button>
                    </div>
                  )}
                  {r.status === 'error' && (
                    <div className="mt-2 text-red-600">
                      Error: {r.error}
                      <button
                        className="ml-2 text-xs text-blue-600 underline"
                        onClick={() => uploadAndParseReceipt(r.file)}
                      >
                        Retry
                      </button>
                    </div>
                  )}
                </div>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
};

export default ReceiptsUploadPanel; 