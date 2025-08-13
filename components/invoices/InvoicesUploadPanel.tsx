import React, { useState, useRef, useCallback, useEffect } from 'react';
import { useToast } from '@/utils/toast';

// Upload Panel Component for Invoice Processing
const API_BASE_URL = 'http://localhost:8002/api';

interface UploadResult {
  success: boolean;
  filename: string;
  message: string;
  data?: {
    supplier_name?: string;
    invoice_number?: string;
    total_amount?: number;
    confidence?: number;
    saved_invoices?: Array<{
      invoice_id: string;
      supplier_name: string;
      invoice_number: string;
      invoice_date: string;
      total_amount: number;
      confidence: number;
      page_range: string;
      invoice_text: string;
      page_numbers: number[];
      metadata: any;
      line_items: Array<{
        quantity?: number;
        description?: string;
        item?: string;
        price?: number;
        unit_price?: number;
        total?: number;
      }>;
    }>;
  };
}

interface UploadProgress {
  [filename: string]: number;
}

const InvoicesUploadPanel: React.FC = () => {
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState<UploadProgress>({});
  const [uploadResults, setUploadResults] = useState<UploadResult[]>([]);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const { showToast } = useToast();

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
  }, []);

  const handleDragEnter = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    
    const files = Array.from(e.dataTransfer.files);
    handleFileUpload(files);
  }, []);

  const handleFileInput = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || []);
    handleFileUpload(files);
  }, []);

  const handleFileUpload = async (files: File[]) => {
    if (files.length === 0) return;

    setIsUploading(true);
    setUploadResults([]);
    
    for (const file of files) {
      try {
        // Initialize progress
        setUploadProgress(prev => ({ ...prev, [file.name]: 0 }));

        const formData = new FormData();
        formData.append('file', file);

        const xhr = new XMLHttpRequest();

        // Track upload progress
        xhr.upload.addEventListener('progress', (event) => {
          if (event.lengthComputable) {
            const progress = Math.round((event.loaded / event.total) * 100);
            setUploadProgress(prev => ({ ...prev, [file.name]: progress }));
          }
        });

        const uploadPromise = new Promise<UploadResult>((resolve, reject) => {
          xhr.addEventListener('load', () => {
            try {
              const response = JSON.parse(xhr.responseText);
              if (xhr.status >= 200 && xhr.status < 300) {
                resolve({
                  success: true,
                  filename: file.name,
                  message: response.message || 'Upload successful',
                  data: response.data
                });
              } else {
                resolve({
                  success: false,
                  filename: file.name,
                  message: response.error || `HTTP ${xhr.status}`,
                });
              }
            } catch (error) {
              reject(new Error('Failed to parse response'));
            }
          });

          xhr.addEventListener('error', () => {
            reject(new Error('Network error'));
          });
        });

        xhr.open('POST', `${API_BASE_URL}/upload`);
        xhr.send(formData);

        const result = await uploadPromise;
        setUploadResults(prev => [...prev, result]);

        if (result.success) {
          showToast('success', `Successfully uploaded ${file.name}`);
        } else {
          showToast('error', `Failed to upload ${file.name}: ${result.message}`);
        }

      } catch (error) {
        const errorMessage = error instanceof Error ? error.message : 'Unknown error';
        setUploadResults(prev => [...prev, {
          success: false,
          filename: file.name,
          message: errorMessage
        }]);
        showToast('error', `Failed to upload ${file.name}: ${errorMessage}`);
      } finally {
        // Complete progress
        setUploadProgress(prev => ({ ...prev, [file.name]: 100 }));
      }
    }

    setIsUploading(false);
  };

  const clearResults = () => {
    setUploadResults([]);
    setUploadProgress({});
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const triggerFileInput = () => {
    fileInputRef.current?.click();
  };

  return (
    <div className="w-full max-w-4xl mx-auto p-6">
      <div className="bg-white rounded-lg shadow-lg border border-gray-200">
        <div className="p-6 border-b border-gray-200">
          <h2 className="text-2xl font-semibold text-gray-900">
            Invoice Upload Panel
          </h2>
          <p className="text-gray-600 mt-1">
            Upload invoice documents for processing with advanced OCR
          </p>
        </div>

        <div className="p-6">
          {/* Upload Area */}
          <div
            className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors ${
              isUploading
                ? 'border-blue-300 bg-blue-50'
                : 'border-gray-300 hover:border-gray-400 hover:bg-gray-50'
            }`}
            onDragOver={handleDragOver}
            onDragEnter={handleDragEnter}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
          >
            <div className="space-y-4">
              <div className="text-4xl">📄</div>
              <div>
                <p className="text-lg font-medium text-gray-900">
                  Drop files here or click to browse
                </p>
                <p className="text-sm text-gray-500 mt-1">
                  Supports PDF, JPG, PNG files up to 50MB
                </p>
              </div>
              <button
                onClick={triggerFileInput}
                disabled={isUploading}
                className="px-6 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed font-medium"
              >
                {isUploading ? 'Uploading...' : 'Choose Files'}
              </button>
            </div>
          </div>

          <input
            ref={fileInputRef}
            type="file"
            multiple
            accept=".pdf,.jpg,.jpeg,.png"
            onChange={handleFileInput}
            className="hidden"
          />

          {/* Upload Progress */}
          {Object.keys(uploadProgress).length > 0 && (
            <div className="mt-6">
              <h3 className="text-lg font-medium text-gray-900 mb-3">
                Upload Progress
              </h3>
              <div className="space-y-3">
                {Object.entries(uploadProgress).map(([filename, progress]) => (
                  <div key={filename} className="bg-gray-50 rounded-lg p-3">
                    <div className="flex justify-between items-center mb-2">
                      <span className="text-sm font-medium text-gray-700">
                        {filename}
                      </span>
                      <span className="text-sm text-gray-500">
                        {progress}%
                      </span>
                    </div>
                    <div className="w-full bg-gray-200 rounded-full h-2">
                      <div
                        className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                        style={{ width: `${progress}%` }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Upload Results */}
          {uploadResults.length > 0 && (
            <div className="mt-6">
              <div className="flex justify-between items-center mb-3">
                <h3 className="text-lg font-medium text-gray-900">
                  Upload Results
                </h3>
                <button
                  onClick={clearResults}
                  className="text-sm text-gray-500 hover:text-gray-700"
                >
                  Clear Results
                </button>
              </div>
              
              <div className="space-y-3">
                {uploadResults.map((result, index) => (
                  <div
                    key={index}
                    className={`p-4 rounded-lg border ${
                      result.success
                        ? 'border-green-200 bg-green-50'
                        : 'border-red-200 bg-red-50'
                    }`}
                  >
                    <div className="flex justify-between items-start">
                      <div className="flex-1">
                        <h4 className="font-medium text-gray-900">
                          {result.filename}
                        </h4>
                        <p className="text-sm text-gray-600 mt-1">
                          {result.message}
                        </p>
                        
                        {result.success && result.data && (
                          <>
                            {result.data.saved_invoices && Array.isArray(result.data.saved_invoices) ? (
                              <div className="mt-3 space-y-3">
                                {result.data.saved_invoices.map((inv: any, idx: number) => {
                                  const [open, setOpen] = React.useState(false);
                                  return (
                                    <div key={inv.invoice_id || idx} className="border rounded p-3 bg-white">
                                      <div className="flex justify-between items-center">
                                        <div className="text-sm">
                                          <div><span className="text-gray-500">Supplier:</span> <span className="font-medium">{inv.supplier_name}</span></div>
                                          <div><span className="text-gray-500">Invoice #:</span> <span className="font-medium">{inv.invoice_number}</span></div>
                                          <div><span className="text-gray-500">Amount:</span> <span className="font-medium">£{Number(inv.total_amount || 0).toFixed(2)}</span></div>
                                          <div><span className="text-gray-500">Confidence:</span> <span className="font-medium">{Math.round(Number(inv.confidence || 0) * 100)}%</span></div>
                                          {inv.page_range && <div className="text-xs text-gray-500">{inv.page_range}</div>}
                                        </div>
                                        <button onClick={() => setOpen(!open)} className="px-3 py-1 text-xs rounded bg-gray-100 hover:bg-gray-200">
                                          {open ? 'Hide line items' : 'Show line items'}
                                        </button>
                                      </div>
                                      {open && Array.isArray(inv.line_items) && inv.line_items.length > 0 && (
                                        <div className="mt-3 overflow-x-auto">
                                          <table className="min-w-full text-sm">
                                            <thead>
                                              <tr className="text-left text-gray-500">
                                                <th className="py-1 pr-4">Qty</th>
                                                <th className="py-1 pr-4">Description</th>
                                                <th className="py-1 pr-4">Unit</th>
                                                <th className="py-1">Total</th>
                                              </tr>
                                            </thead>
                                            <tbody>
                                              {inv.line_items.map((li: any, i: number) => (
                                                <tr key={i} className="border-t">
                                                  <td className="py-1 pr-4">{li.quantity ?? '-'}</td>
                                                  <td className="py-1 pr-4">{li.description ?? li.item ?? '-'}</td>
                                                  <td className="py-1 pr-4">{li.price ?? li.unit_price ?? '-'}</td>
                                                  <td className="py-1">{li.total ?? '-'}</td>
                                                </tr>
                                              ))}
                                            </tbody>
                                          </table>
                                        </div>
                                      )}
                                    </div>
                                  );
                                })}
                              </div>
                            ) : (
                              <div className="mt-3 grid grid-cols-2 gap-4 text-sm">
                                {result.data.supplier_name && (
                                  <div>
                                    <span className="text-gray-500">Supplier:</span>
                                    <span className="ml-1 font-medium">
                                      {result.data.supplier_name}
                                    </span>
                                  </div>
                                )}
                                {result.data.invoice_number && (
                                  <div>
                                    <span className="text-gray-500">Invoice #:</span>
                                    <span className="ml-1 font-medium">
                                      {result.data.invoice_number}
                                    </span>
                                  </div>
                                )}
                                {result.data.total_amount && (
                                  <div>
                                    <span className="text-gray-500">Amount:</span>
                                    <span className="ml-1 font-medium">
                                      £{result.data.total_amount.toFixed(2)}
                                    </span>
                                  </div>
                                )}
                                {result.data.confidence && (
                                  <div>
                                    <span className="text-gray-500">Confidence:</span>
                                    <span className="ml-1 font-medium">
                                      {Math.round(result.data.confidence * 100)}%
                                    </span>
                                  </div>
                                )}
                              </div>
                            )}
                          </>
                        )}
                      </div>
                      
                      <div className={`px-2 py-1 rounded text-xs font-medium ${
                        result.success
                          ? 'bg-green-100 text-green-800'
                          : 'bg-red-100 text-red-800'
                      }`}>
                        {result.success ? 'SUCCESS' : 'FAILED'}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default InvoicesUploadPanel; 