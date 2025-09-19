import React, { useRef, useState } from "react";
import type { InvoiceDTO } from "@/types/invoice";
import { apiUpload, apiGetInvoice } from "@/lib/api";

interface UploadGlassProps {
  docType?: "invoice" | "delivery_note";
  onCreated: (items: InvoiceDTO[]) => void;
}

export default function UploadGlass({ docType = "invoice", onCreated }: UploadGlassProps) {
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [uploadStatus, setUploadStatus] = useState<string>("");
  const [error, setError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFile = async (file: File) => {
    if (!file) return;

    // Check file type
    const allowedTypes = ['application/pdf', 'image/png', 'image/jpeg', 'image/jpg'];
    if (!allowedTypes.includes(file.type)) {
      setError('Please upload a PDF, PNG, or JPG file');
      return;
    }

    setIsUploading(true);
    setError(null);
    setUploadProgress(0);
    setUploadStatus("Uploading...");

    try {
      console.debug("apiUpload ->", file.name, file.type);
      
      // Simulate progress
      const progressInterval = setInterval(() => {
        setUploadProgress(prev => Math.min(prev + 10, 90));
      }, 200);

      const result = await apiUpload(file, docType);
      clearInterval(progressInterval);
      setUploadProgress(100);

      // Stage the progress bar - poll for completion
      if (result.items && result.items.length > 0) {
        const newId = result.items[0].id;
        setUploadStatus("OCR...");
        
        const started = Date.now();
        let done = false;
        
        while (!done && Date.now() - started < 20000) {
          await new Promise(r => setTimeout(r, 800));
          try {
            const d = await apiGetInvoice(newId);
            if (!d) continue;
            
            if (["parsed", "scanned", "manual"].includes(d.status ?? "")) {
              done = true;
              setUploadStatus("Grouped");
              onCreated([{ id: newId, pages: d.pages ?? [0], page_count: d.page_count ?? 1, status: 'ocr' }]);
            } else {
              setUploadStatus(d.status === "ocr" ? "OCR..." : "Parsing...");
            }
          } catch (e) {
            // Continue polling on error
            continue;
          }
        }
        
        if (!done) {
          setUploadStatus("Complete");
          onCreated([{ id: newId, pages: [0], page_count: 1, status: 'ocr' }]);
        }
      } else {
        onCreated(result.items || []);
      }

      // Wait a moment to show completion
      setTimeout(() => {
        setIsUploading(false);
        setUploadProgress(0);
        setUploadStatus("");
      }, 500);

    } catch (err: any) {
      setIsUploading(false);
      setUploadProgress(0);
      setUploadStatus("");
      
      // Error message is already cleaned by fetchJSON
      setError(err.message || 'Upload failed');
    }
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    
    const files = Array.from(e.dataTransfer.files);
    if (files.length > 0) {
      handleFile(files[0]);
    }
  };

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (files && files.length > 0) {
      handleFile(files[0]);
    }
  };

  const openFileDialog = () => {
    fileInputRef.current?.click();
  };

  return (
    <div className="relative">
      <div
        className={`
          border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors
          ${isDragging ? 'border-blue-400 bg-blue-50' : 'border-gray-300 hover:border-gray-400'}
          ${isUploading ? 'pointer-events-none' : ''}
        `}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={openFileDialog}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf,.png,.jpg,.jpeg"
          onChange={handleFileInput}
          className="hidden"
          aria-label="Upload file"
        />

        {isUploading ? (
          <div className="space-y-4">
            <div className="text-lg font-medium">
              {uploadStatus || (uploadProgress < 90 ? 'Uploading...' : uploadProgress < 100 ? 'Scanning...' : 'Complete')}
            </div>
            <div className="text-xs text-gray-500">
              {uploadStatus === "OCR..." ? "Processing 1/1 page..." : 
               uploadStatus === "Parsing..." ? "Extracting data..." :
               uploadStatus === "Grouped" ? "Complete!" : "Uploading file..."}
            </div>
            <div
              role="progressbar"
              aria-valuenow={uploadProgress}
              aria-valuemin={0}
              aria-valuemax={100}
              className="h-1 w-full rounded bg-gray-100"
            >
              <div 
                className={`h-1 rounded transition-all duration-300 ${
                  uploadStatus === "Grouped" ? "bg-green-500" : "bg-gray-400"
                }`}
                style={{ width: `${uploadProgress}%` }} 
              />
            </div>
          </div>
        ) : (
          <div className="space-y-2">
            <div className="text-4xl text-gray-400">📄</div>
            <div className="text-lg font-medium">
              Drop your {docType === 'invoice' ? 'invoice' : 'delivery note'} here
            </div>
            <div className="text-sm text-gray-500">
              or click to browse (PDF, PNG, JPG)
            </div>
          </div>
        )}

        {error && (
          <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded text-red-700 text-sm">
            {error}
          </div>
        )}
      </div>
    </div>
  );
}
