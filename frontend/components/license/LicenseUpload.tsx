import React, { useState, useRef } from 'react';
import { licenseClient, LicenseUploadResponse } from '../../lib/licenseClient';

interface LicenseUploadProps {
  onUploadSuccess: (response: LicenseUploadResponse) => void;
}

export default function LicenseUpload({ onUploadSuccess }: LicenseUploadProps) {
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

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
    
    const files = e.dataTransfer.files;
    if (files.length > 0) {
      handleFileUpload(files[0]);
    }
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      handleFileUpload(file);
    }
  };

  const handleFileUpload = async (file: File) => {
    if (!file.name.endsWith('.lic')) {
      setMessage({ type: 'error', text: 'Please select a .lic file' });
      return;
    }

    setIsUploading(true);
    setMessage(null);

    try {
      const response = await licenseClient.uploadLicense(file);
      
      if (response.ok) {
        setMessage({ type: 'success', text: response.message });
        onUploadSuccess(response);
      } else {
        setMessage({ type: 'error', text: response.message });
      }
    } catch (error) {
      setMessage({ type: 'error', text: 'Failed to upload license file' });
    } finally {
      setIsUploading(false);
    }
  };

  const handleReplaceClick = () => {
    fileInputRef.current?.click();
  };

  return (
    <div className="bg-white border border-[#E5E7EB] rounded-[12px] p-4">
      <div className="flex items-center gap-2 mb-4">
        <svg 
          xmlns="http://www.w3.org/2000/svg" 
          width="18" 
          height="18" 
          fill="none" 
          stroke="#1F2937" 
          strokeWidth="2" 
          strokeLinecap="round" 
          strokeLinejoin="round" 
          aria-label="Upload license"
        >
          <circle cx="6" cy="12" r="2"/>
          <path d="M8 12h8l-2 2 2 2"/>
        </svg>
        <h3 className="text-[16px] font-semibold text-[#1F2937]">License Upload</h3>
      </div>

      {/* Drag and Drop Area */}
      <div
        className={`border-2 border-dashed rounded-[12px] p-6 text-center transition-colors ${
          isDragging 
            ? 'border-[#3B82F6] bg-[#EFF6FF]' 
            : 'border-[#D1D5DB] hover:border-[#9CA3AF]'
        }`}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
      >
        <div className="space-y-2">
          <svg 
            className="mx-auto h-12 w-12 text-[#9CA3AF]" 
            stroke="currentColor" 
            fill="none" 
            viewBox="0 0 48 48"
          >
            <path 
              d="M28 8H12a4 4 0 00-4 4v20m32-12v8m0 0v8a4 4 0 01-4 4H12a4 4 0 01-4-4v-4m32-4l-3.172-3.172a4 4 0 00-5.656 0L28 28M8 32l9.172-9.172a4 4 0 015.656 0L28 28m0 0l4 4m4-24h8m-4-4v8m-12 4h.02" 
              strokeWidth={2} 
              strokeLinecap="round" 
              strokeLinejoin="round" 
            />
          </svg>
          <div className="text-[#6B7280]">
            <p className="text-sm">
              Drag and drop your <code className="text-xs bg-[#F3F4F6] px-1 py-0.5 rounded">owlin.lic</code> file here, or{' '}
              <button
                type="button"
                onClick={handleReplaceClick}
                className="text-[#3B82F6] hover:text-[#2563EB] font-medium"
                disabled={isUploading}
              >
                browse
              </button>
            </p>
          </div>
        </div>
      </div>

      {/* Hidden file input */}
      <input
        ref={fileInputRef}
        type="file"
        accept=".lic"
        onChange={handleFileSelect}
        className="hidden"
        disabled={isUploading}
      />

      {/* Upload button */}
      <div className="mt-4">
        <button
          type="button"
          onClick={handleReplaceClick}
          disabled={isUploading}
          className="w-full px-4 py-2 bg-[#1F2937] text-white rounded-[6px] font-medium text-sm hover:bg-[#111827] disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {isUploading ? 'Uploading...' : 'Replace License'}
        </button>
      </div>

      {/* Message */}
      {message && (
        <div className={`mt-4 p-3 rounded-[6px] text-sm ${
          message.type === 'success' 
            ? 'bg-[#D1FAE5] text-[#065F46] border border-[#A7F3D0]' 
            : 'bg-[#FEE2E2] text-[#991B1B] border border-[#FCA5A5]'
        }`}>
          {message.text}
        </div>
      )}

      {/* Signature details link */}
      <div className="mt-4 text-center">
        <button
          type="button"
          className="text-[#6B7280] text-sm hover:text-[#374151] underline"
          onClick={() => {
            // TODO: Open signature details modal
            console.log('Show signature details');
          }}
        >
          View signature details
        </button>
      </div>
    </div>
  );
} 