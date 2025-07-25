import React, { useState, useRef } from 'react';
import Layout from '@/components/Layout';
import { apiService } from '@/services/api';
import { useToast } from '@/utils/toast';

interface UploadPageProps {}

const UploadPage: React.FC<UploadPageProps> = () => {
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState<{ [key: string]: number }>({});
  const [selectedDocumentType, setSelectedDocumentType] = useState<'invoice' | 'delivery_note' | 'receipt' | 'utility'>('invoice');
  
  const invoiceInputRef = useRef<HTMLInputElement>(null);
  const deliveryInputRef = useRef<HTMLInputElement>(null);

  const { showToast } = useToast();

  const handleFileUpload = async (file: File, type: 'invoice' | 'delivery') => {
    if (!file) return;

    setIsUploading(true);
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

      // Upload file with document type
      await apiService.uploadDocument(file, selectedDocumentType);

      clearInterval(progressInterval);
      setUploadProgress(prev => ({ ...prev, [file.name]: 100 }));

      // Clear progress after a delay and show success toast
      setTimeout(() => {
        setUploadProgress(prev => {
          const newProgress = { ...prev };
          delete newProgress[file.name];
          return newProgress;
        });
        setIsUploading(false);
        showToast('success', '✅ Upload complete — document sent for review');
      }, 1000);

    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Unknown error';
      setUploadProgress(prev => {
        const newProgress = { ...prev };
        delete newProgress[file.name];
        return newProgress;
      });
      setIsUploading(false);
      showToast('error', `🚨 Upload failed: ${errorMessage}`);
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

  const documentTypeOptions = [
    { value: 'invoice', label: 'Invoice', icon: '📄' },
    { value: 'receipt', label: 'Receipt', icon: '🧾' },
    { value: 'utility', label: 'Utility', icon: '⚡' },
  ];

  return (
    <Layout>
      <div className="container mx-auto py-8 px-4">
        <div className="max-w-6xl mx-auto">
          {/* Header */}
          <div className="text-center mb-8">
            <h1 className="text-3xl font-bold text-gray-900 dark:text-gray-100 mb-2">
              📤 Upload Documents
            </h1>
            <p className="text-gray-600 dark:text-gray-400">
              Upload your documents for processing and review
            </p>
          </div>

          {/* Document Type Selector */}
          <div className="bg-white dark:bg-gray-800 rounded-lg p-4 border border-gray-200 dark:border-gray-700 mb-6">
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">
              Document Type
            </label>
            <div className="flex flex-wrap gap-2">
              {documentTypeOptions.map((option) => (
                <button
                  key={option.value}
                  onClick={() => setSelectedDocumentType(option.value as any)}
                  className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                    selectedDocumentType === option.value
                      ? 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300 border border-blue-300 dark:border-blue-700'
                      : 'bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300 border border-gray-300 dark:border-gray-600 hover:bg-gray-200 dark:hover:bg-gray-600'
                  }`}
                >
                  <span className="mr-2">{option.icon}</span>
                  {option.label}
                </button>
              ))}
            </div>
          </div>

          {/* Upload Panels */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Invoices & Receipts Panel */}
            <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
              <div className="text-center mb-4">
                <div className="text-4xl mb-2">📄</div>
                <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-1">
                  Invoices & Receipts
                </h2>
                <p className="text-sm text-gray-600 dark:text-gray-400">
                  Upload invoices, receipts, and utility bills
                </p>
              </div>

              <div
                className={`border-2 border-dashed rounded-lg p-6 text-center transition-colors ${
                  isUploading
                    ? 'border-gray-300 dark:border-gray-600 bg-gray-50 dark:bg-gray-700'
                    : 'border-gray-300 dark:border-gray-600 hover:border-blue-400 dark:hover:border-blue-500 hover:bg-blue-50 dark:hover:bg-blue-900/10'
                }`}
                onDrop={(e) => handleDrop(e, 'invoice')}
                onDragOver={handleDragOver}
              >
                <div className="text-2xl mb-3">📤</div>
                <h3 className="text-sm font-medium text-gray-900 dark:text-gray-100 mb-2">
                  {isUploading ? 'Uploading...' : 'Drop files here or click to browse'}
                </h3>
                <p className="text-xs text-gray-500 dark:text-gray-400 mb-4">
                  Supports PDF, JPG, JPEG, PNG files
                </p>
                <input
                  ref={invoiceInputRef}
                  type="file"
                  accept=".pdf,.jpg,.jpeg,.png"
                  onChange={(e) => handleFileSelect(e, 'invoice')}
                  className="hidden"
                  disabled={isUploading}
                />
                <button
                  onClick={() => invoiceInputRef.current?.click()}
                  disabled={isUploading}
                  className="px-6 py-2 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  Browse Files
                </button>
              </div>
            </div>

            {/* Delivery Notes Panel */}
            <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
              <div className="text-center mb-4">
                <div className="text-4xl mb-2">📦</div>
                <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-1">
                  Delivery Notes
                </h2>
                <p className="text-sm text-gray-600 dark:text-gray-400">
                  Upload delivery notes and packing slips
                </p>
              </div>

              <div
                className={`border-2 border-dashed rounded-lg p-6 text-center transition-colors ${
                  isUploading
                    ? 'border-gray-300 dark:border-gray-600 bg-gray-50 dark:bg-gray-700'
                    : 'border-gray-300 dark:border-gray-600 hover:border-green-400 dark:hover:border-green-500 hover:bg-green-50 dark:hover:bg-green-900/10'
                }`}
                onDrop={(e) => handleDrop(e, 'delivery')}
                onDragOver={handleDragOver}
              >
                <div className="text-2xl mb-3">📤</div>
                <h3 className="text-sm font-medium text-gray-900 dark:text-gray-100 mb-2">
                  {isUploading ? 'Uploading...' : 'Drop files here or click to browse'}
                </h3>
                <p className="text-xs text-gray-500 dark:text-gray-400 mb-4">
                  Supports PDF, JPG, JPEG, PNG files
                </p>
                <input
                  ref={deliveryInputRef}
                  type="file"
                  accept=".pdf,.jpg,.jpeg,.png"
                  onChange={(e) => handleFileSelect(e, 'delivery')}
                  className="hidden"
                  disabled={isUploading}
                />
                <button
                  onClick={() => deliveryInputRef.current?.click()}
                  disabled={isUploading}
                  className="px-6 py-2 bg-green-600 text-white text-sm rounded-lg hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  Browse Files
                </button>
              </div>
            </div>
          </div>

          {/* Upload Progress */}
          {Object.keys(uploadProgress).length > 0 && (
            <div className="mt-6 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4">
              <h3 className="text-sm font-medium text-gray-900 dark:text-gray-100 mb-3">
                Upload Progress
              </h3>
              <div className="space-y-3">
                {Object.entries(uploadProgress).map(([filename, progress]) => (
                  <div key={filename} className="flex items-center space-x-3">
                    <div className="flex-1">
                      <div className="text-sm text-gray-700 dark:text-gray-300 mb-1">{filename}</div>
                      <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
                        <div 
                          className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                          style={{ width: `${progress}%` }}
                        ></div>
                      </div>
                    </div>
                    <span className="text-xs text-gray-500 dark:text-gray-400 min-w-[3rem] text-right">
                      {progress}%
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Info Section */}
          <div className="mt-8 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
            <div className="flex items-start space-x-3">
              <div className="text-blue-600 dark:text-blue-400 text-xl">ℹ️</div>
              <div>
                <h3 className="text-sm font-medium text-blue-900 dark:text-blue-100 mb-1">
                  What happens next?
                </h3>
                <p className="text-sm text-blue-800 dark:text-blue-200">
                  Your uploaded documents will be automatically processed and sent to the Document Queue for review. 
                  You can view and manage all documents in the{' '}
                  <a href="/document-queue" className="underline hover:no-underline font-medium">
                    Document Queue
                  </a>{' '}
                  page.
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </Layout>
  );
};

export default UploadPage; 