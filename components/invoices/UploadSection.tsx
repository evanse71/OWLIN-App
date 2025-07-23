import React, { useState, useRef } from 'react';
import { apiService } from '@/services/api';

interface UploadSectionProps {
  onUploadComplete: () => void;
}

const UploadSection: React.FC<UploadSectionProps> = ({ onUploadComplete }) => {
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState<{ [key: string]: number }>({});
  const [error, setError] = useState<string | null>(null);
  
  const invoiceInputRef = useRef<HTMLInputElement>(null);
  const deliveryInputRef = useRef<HTMLInputElement>(null);

  const handleFileUpload = async (file: File, type: 'invoice' | 'delivery') => {
    if (!file) return;

    setIsUploading(true);
    setError(null);
    setUploadProgress(prev => ({ ...prev, [file.name]: 0 }));

    try {
      // Simulate upload progress
      const progressInterval = setInterval(() => {
        setUploadProgress(prev => {
          const current = prev[file.name] || 0;
          if (current >= 90) {
            clearInterval(progressInterval);
            return prev;
          }
          return { ...prev, [file.name]: current + 10 };
        });
      }, 200);

      // Upload file
      if (type === 'invoice') {
        await apiService.uploadInvoice(file);
      } else {
        await apiService.uploadDeliveryNote(file);
      }

      clearInterval(progressInterval);
      setUploadProgress(prev => ({ ...prev, [file.name]: 100 }));

      // Clear progress after a delay
      setTimeout(() => {
        setUploadProgress(prev => {
          const newProgress = { ...prev };
          delete newProgress[file.name];
          return newProgress;
        });
        setIsUploading(false);
        onUploadComplete();
      }, 1000);

    } catch (err) {
      setError(`Failed to upload ${file.name}: ${err instanceof Error ? err.message : 'Unknown error'}`);
      setIsUploading(false);
      setUploadProgress(prev => {
        const newProgress = { ...prev };
        delete newProgress[file.name];
        return newProgress;
      });
    }
  };

  const handleFileSelect = (event: React.ChangeEvent<HTMLInputElement>, type: 'invoice' | 'delivery') => {
    const file = event.target.files?.[0];
    if (file) {
      handleFileUpload(file, type);
    }
    // Reset input
    event.target.value = '';
  };

  const handleDrop = (event: React.DragEvent, type: 'invoice' | 'delivery') => {
    event.preventDefault();
    const file = event.dataTransfer.files[0];
    if (file) {
      handleFileUpload(file, type);
    }
  };

  const handleDragOver = (event: React.DragEvent) => {
    event.preventDefault();
  };

  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 mb-6">
      <h2 className="text-lg font-semibold text-gray-900 mb-4">�� Upload Documents</h2>
      
      {error && (
        <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-md">
          <p className="text-sm text-red-800">{error}</p>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Invoice Upload */}
        <div
          className="border-2 border-dashed border-gray-300 rounded-lg p-6 text-center hover:border-blue-400 transition-colors"
          onDrop={(e) => handleDrop(e, 'invoice')}
          onDragOver={handleDragOver}
        >
          <div className="text-3xl mb-2">��</div>
          <h3 className="text-sm font-medium text-gray-900 mb-2">Upload Invoice</h3>
          <p className="text-xs text-gray-500 mb-4">
            Drag and drop or click to browse
          </p>
          <input
            ref={invoiceInputRef}
            type="file"
            accept=".pdf,.jpg,.jpeg,.png"
            onChange={(e) => handleFileSelect(e, 'invoice')}
            className="hidden"
          />
          <button
            onClick={() => invoiceInputRef.current?.click()}
            disabled={isUploading}
            className="px-4 py-2 bg-blue-600 text-white text-sm rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Browse Files
          </button>
        </div>

        {/* Delivery Note Upload */}
        <div
          className="border-2 border-dashed border-gray-300 rounded-lg p-6 text-center hover:border-green-400 transition-colors"
          onDrop={(e) => handleDrop(e, 'delivery')}
          onDragOver={handleDragOver}
        >
          <div className="text-3xl mb-2">��</div>
          <h3 className="text-sm font-medium text-gray-900 mb-2">Upload Delivery Note</h3>
          <p className="text-xs text-gray-500 mb-4">
            Drag and drop or click to browse
          </p>
          <input
            ref={deliveryInputRef}
            type="file"
            accept=".pdf,.jpg,.jpeg,.png"
            onChange={(e) => handleFileSelect(e, 'delivery')}
            className="hidden"
          />
          <button
            onClick={() => deliveryInputRef.current?.click()}
            disabled={isUploading}
            className="px-4 py-2 bg-green-600 text-white text-sm rounded-md hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Browse Files
          </button>
        </div>
      </div>

      {/* Upload Progress */}
      {Object.keys(uploadProgress).length > 0 && (
        <div className="mt-4 space-y-2">
          {Object.entries(uploadProgress).map(([filename, progress]) => (
            <div key={filename} className="flex items-center space-x-3">
              <div className="flex-1">
                <div className="text-sm text-gray-700">{filename}</div>
                <div className="w-full bg-gray-200 rounded-full h-2">
                  <div 
                    className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                    style={{ width: `${progress}%` }}
                  ></div>
                </div>
              </div>
              <span className="text-xs text-gray-500">{progress}%</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default UploadSection; 