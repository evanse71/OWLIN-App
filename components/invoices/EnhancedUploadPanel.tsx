import React, { useState, useRef } from 'react';
import { apiService } from '@/services/api';
import { useToast } from '@/utils/toast';

interface EnhancedUploadPanelProps {
  userRole?: string;
  documentType?: 'invoice' | 'delivery_note' | 'receipt' | 'utility';
  onUploadComplete?: (results: any[]) => void;
}

interface UploadProgress {
  [key: string]: {
    progress: number;
    status: 'uploading' | 'processing' | 'success' | 'error';
    message?: string;
    details?: {
      supplier_name?: string;
      invoice_number?: string;
      invoice_date?: string;
      net_amount?: number;
      vat_amount?: number;
      total_amount?: number;
      ocr_confidence?: number;
      processing_time?: number;
      error?: string;
    };
  };
}

const EnhancedUploadPanel: React.FC<EnhancedUploadPanelProps> = ({
  userRole = 'viewer',
  documentType = 'invoice',
  onUploadComplete
}) => {
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState<UploadProgress>({});
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [uploadResults, setUploadResults] = useState<any[]>([]);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const { showToast } = useToast();

  const handleFileSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(event.target.files || []);
    setSelectedFiles(files);
    
    // Initialize progress for each file
    const progress: UploadProgress = {};
    files.forEach(file => {
      progress[file.name] = {
        progress: 0,
        status: 'uploading'
      };
    });
    setUploadProgress(progress);
  };

  const handleUpload = async () => {
    if (selectedFiles.length === 0) {
      showToast('warning', 'Please select files to upload');
      return;
    }

    setIsUploading(true);
    setUploadResults([]);

    try {
      const formData = new FormData();
      selectedFiles.forEach(file => {
        formData.append('file', file);
      });
      formData.append('userRole', userRole);
      formData.append('documentType', documentType);

      // Update progress to show processing
      setUploadProgress(prev => {
        const newProgress = { ...prev };
        Object.keys(newProgress).forEach(filename => {
          newProgress[filename] = {
            ...newProgress[filename],
            progress: 50,
            status: 'processing',
            message: 'Processing with OCR...'
          };
        });
        return newProgress;
      });

      // Call the enhanced upload API
      const response = await fetch('/api/upload-enhanced', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`Upload failed: ${response.statusText} - ${errorText}`);
      }

      const result = await response.json();
      console.log('Upload result:', result);

      // Update progress with detailed results
      setUploadProgress(prev => {
        const newProgress = { ...prev };
        
        if (result.data?.results) {
          result.data.results.forEach((fileResult: any) => {
            const filename = fileResult.filename;
            if (newProgress[filename]) {
              newProgress[filename] = {
                progress: 100,
                status: fileResult.success ? 'success' : 'error',
                message: fileResult.success ? 'Processing completed' : fileResult.error,
                details: {
                  supplier_name: fileResult.supplier_name,
                  invoice_number: fileResult.invoice_number,
                  invoice_date: fileResult.invoice_date,
                  net_amount: fileResult.net_amount,
                  vat_amount: fileResult.vat_amount,
                  total_amount: fileResult.total_amount,
                  ocr_confidence: fileResult.ocr_confidence,
                  processing_time: fileResult.processing_time,
                  error: fileResult.error
                }
              };
            }
          });
        }
        
        return newProgress;
      });

      // Store results for display
      if (result.data?.results) {
        setUploadResults(result.data.results);
      }

      const successCount = result.data?.summary?.successful || 0;
      const totalCount = result.data?.summary?.total || 0;
      
      if (successCount > 0) {
        showToast('success', `✅ Successfully processed ${successCount}/${totalCount} files`);
      } else {
        showToast('error', `❌ Failed to process any files`);
      }
      
      if (onUploadComplete && result.data?.results) {
        onUploadComplete(result.data.results);
      }

      // Clear selected files after successful upload
      setTimeout(() => {
        setSelectedFiles([]);
        setUploadProgress({});
        setUploadResults([]);
        if (fileInputRef.current) {
          fileInputRef.current.value = '';
        }
      }, 5000);

    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Upload failed';
      
      // Update progress to show error
      setUploadProgress(prev => {
        const newProgress = { ...prev };
        Object.keys(newProgress).forEach(filename => {
          newProgress[filename] = {
            progress: 100,
            status: 'error',
            message: errorMessage
          };
        });
        return newProgress;
      });

      showToast('error', `🚨 ${errorMessage}`);
    } finally {
      setIsUploading(false);
    }
  };

  const handleDrop = (event: React.DragEvent) => {
    event.preventDefault();
    const files = Array.from(event.dataTransfer.files);
    setSelectedFiles(files);
    
    // Initialize progress for each file
    const progress: UploadProgress = {};
    files.forEach(file => {
      progress[file.name] = {
        progress: 0,
        status: 'uploading'
      };
    });
    setUploadProgress(progress);
  };

  const handleDragOver = (event: React.DragEvent) => {
    event.preventDefault();
  };

  const removeFile = (filename: string) => {
    setSelectedFiles(prev => prev.filter(file => file.name !== filename));
    setUploadProgress(prev => {
      const newProgress = { ...prev };
      delete newProgress[filename];
      return newProgress;
    });
  };

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
      <div className="text-center mb-6">
        <div className="text-4xl mb-2">📤</div>
        <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-1">
          Enhanced Upload
        </h2>
        <p className="text-sm text-gray-600 dark:text-gray-400">
          Multi-file upload with OCR processing and validation
        </p>
        <div className="mt-2 text-xs text-gray-500 dark:text-gray-400">
          Role: {userRole} | Type: {documentType}
        </div>
      </div>

      {/* File Selection */}
      <div
        className={`border-2 border-dashed rounded-lg p-6 text-center transition-colors ${
          selectedFiles.length > 0
            ? 'border-green-400 dark:border-green-500 bg-green-50 dark:bg-green-900/10'
            : 'border-gray-300 dark:border-gray-600 hover:border-blue-400 dark:hover:border-blue-500 hover:bg-blue-50 dark:hover:bg-blue-900/10'
        }`}
        onDrop={handleDrop}
        onDragOver={handleDragOver}
      >
        <div className="text-2xl mb-3">📁</div>
        <h3 className="text-sm font-medium text-gray-900 dark:text-gray-100 mb-2">
          {selectedFiles.length > 0 
            ? `${selectedFiles.length} file(s) selected` 
            : 'Drop files here or click to browse'
          }
        </h3>
        <p className="text-xs text-gray-500 dark:text-gray-400 mb-4">
          Supports PDF, JPG, JPEG, PNG files (max 50MB each)
        </p>
        <input
          ref={fileInputRef}
          type="file"
          multiple
          accept=".pdf,.jpg,.jpeg,.png"
          onChange={handleFileSelect}
          className="hidden"
          disabled={isUploading}
        />
        <button
          onClick={() => fileInputRef.current?.click()}
          disabled={isUploading}
          className="px-6 py-2 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          Browse Files
        </button>
      </div>

      {/* Selected Files */}
      {selectedFiles.length > 0 && (
        <div className="mt-4">
          <h4 className="text-sm font-medium text-gray-900 dark:text-gray-100 mb-2">
            Selected Files ({selectedFiles.length})
          </h4>
          <div className="space-y-2">
            {selectedFiles.map((file, index) => (
              <div key={index} className="flex items-center justify-between p-2 bg-gray-50 dark:bg-gray-700 rounded">
                <div className="flex items-center space-x-2">
                  <span className="text-sm text-gray-700 dark:text-gray-300">
                    {file.name}
                  </span>
                  <span className="text-xs text-gray-500 dark:text-gray-400">
                    ({(file.size / 1024 / 1024).toFixed(2)} MB)
                  </span>
                </div>
                <button
                  onClick={() => removeFile(file.name)}
                  disabled={isUploading}
                  className="text-red-500 hover:text-red-700 disabled:opacity-50"
                >
                  ✕
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Upload Button */}
      {selectedFiles.length > 0 && (
        <div className="mt-4">
          <button
            onClick={handleUpload}
            disabled={isUploading}
            className="w-full px-6 py-3 bg-green-600 text-white text-sm font-medium rounded-lg hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {isUploading ? 'Uploading...' : `Upload ${selectedFiles.length} File(s)`}
          </button>
        </div>
      )}

      {/* Upload Progress */}
      {Object.keys(uploadProgress).length > 0 && (
        <div className="mt-4">
          <h4 className="text-sm font-medium text-gray-900 dark:text-gray-100 mb-2">
            Upload Progress
          </h4>
          <div className="space-y-3">
            {Object.entries(uploadProgress).map(([filename, progress]) => (
              <div key={filename} className="space-y-1">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-700 dark:text-gray-300">
                    {filename}
                  </span>
                  <span className={`text-xs ${
                    progress.status === 'success' ? 'text-green-600' :
                    progress.status === 'error' ? 'text-red-600' :
                    'text-gray-500'
                  }`}>
                    {progress.status === 'success' ? '✅' :
                     progress.status === 'error' ? '❌' :
                     '⏳'} {progress.progress}%
                  </span>
                </div>
                <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
                  <div 
                    className={`h-2 rounded-full transition-all duration-300 ${
                      progress.status === 'success' ? 'bg-green-600' :
                      progress.status === 'error' ? 'bg-red-600' :
                      'bg-blue-600'
                    }`}
                    style={{ width: `${progress.progress}%` }}
                  ></div>
                </div>
                {progress.message && (
                  <p className="text-xs text-gray-500 dark:text-gray-400">
                    {progress.message}
                  </p>
                )}
                
                {/* Detailed Results */}
                {progress.details && progress.status === 'success' && (
                  <div className="mt-2 p-3 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg">
                    <h5 className="text-xs font-medium text-green-800 dark:text-green-200 mb-2">
                      📋 Extracted Data
                    </h5>
                    <div className="grid grid-cols-2 gap-2 text-xs">
                      {progress.details.supplier_name && (
                        <div>
                          <span className="text-green-700 dark:text-green-300">Supplier:</span>
                          <span className="ml-1 text-gray-700 dark:text-gray-300">{progress.details.supplier_name}</span>
                        </div>
                      )}
                      {progress.details.invoice_number && (
                        <div>
                          <span className="text-green-700 dark:text-green-300">Invoice #:</span>
                          <span className="ml-1 text-gray-700 dark:text-gray-300">{progress.details.invoice_number}</span>
                        </div>
                      )}
                      {progress.details.invoice_date && (
                        <div>
                          <span className="text-green-700 dark:text-green-300">Date:</span>
                          <span className="ml-1 text-gray-700 dark:text-gray-300">{progress.details.invoice_date}</span>
                        </div>
                      )}
                      {progress.details.total_amount && (
                        <div>
                          <span className="text-green-700 dark:text-green-300">Total:</span>
                          <span className="ml-1 text-gray-700 dark:text-gray-300">£{progress.details.total_amount}</span>
                        </div>
                      )}
                      {progress.details.ocr_confidence && (
                        <div>
                          <span className="text-green-700 dark:text-green-300">OCR Confidence:</span>
                          <span className="ml-1 text-gray-700 dark:text-gray-300">{progress.details.ocr_confidence.toFixed(1)}%</span>
                        </div>
                      )}
                      {progress.details.processing_time && (
                        <div>
                          <span className="text-green-700 dark:text-green-300">Processing Time:</span>
                          <span className="ml-1 text-gray-700 dark:text-gray-300">{progress.details.processing_time.toFixed(2)}s</span>
                        </div>
                      )}
                    </div>
                  </div>
                )}
                
                {/* Error Details */}
                {progress.details?.error && progress.status === 'error' && (
                  <div className="mt-2 p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
                    <h5 className="text-xs font-medium text-red-800 dark:text-red-200 mb-2">
                      ❌ Error Details
                    </h5>
                    <p className="text-xs text-red-700 dark:text-red-300">
                      {progress.details.error}
                    </p>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Processing Results Summary */}
      {uploadResults.length > 0 && (
        <div className="mt-4">
          <h4 className="text-sm font-medium text-gray-900 dark:text-gray-100 mb-2">
            📊 Processing Summary
          </h4>
          <div className="bg-gray-50 dark:bg-gray-700 rounded-lg p-3">
            <div className="grid grid-cols-3 gap-4 text-xs">
              <div className="text-center">
                <div className="text-lg font-semibold text-blue-600 dark:text-blue-400">
                  {uploadResults.filter(r => r.success).length}
                </div>
                <div className="text-gray-600 dark:text-gray-400">Successful</div>
              </div>
              <div className="text-center">
                <div className="text-lg font-semibold text-red-600 dark:text-red-400">
                  {uploadResults.filter(r => !r.success).length}
                </div>
                <div className="text-gray-600 dark:text-gray-400">Failed</div>
              </div>
              <div className="text-center">
                <div className="text-lg font-semibold text-green-600 dark:text-green-400">
                  {uploadResults.length}
                </div>
                <div className="text-gray-600 dark:text-gray-400">Total</div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Info Section */}
      <div className="mt-6 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
        <div className="flex items-start space-x-3">
          <div className="text-blue-600 dark:text-blue-400 text-xl">ℹ️</div>
          <div>
            <h3 className="text-sm font-medium text-blue-900 dark:text-blue-100 mb-1">
              Enhanced Processing
            </h3>
            <p className="text-sm text-blue-800 dark:text-blue-200">
              Files will be processed with OCR, field extraction, validation, and stored in the database. 
              Duplicate detection and role-based access control are enforced.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default EnhancedUploadPanel; 