import React, { useState, useCallback, useRef, useEffect } from 'react';
import { UploadIcon } from '../icons';
import { useOfflineQueue } from '../../hooks/useOfflineQueue';

interface UploadSectionProps {
  onFilesUpload: (files: File[]) => Promise<void>;
  disabled?: boolean;
  reason?: string;
}

const UploadSection: React.FC<UploadSectionProps> = ({ 
  onFilesUpload, 
  disabled = false,
  reason
}) => {
  const [isDragOver, setIsDragOver] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [isOnline, setIsOnline] = useState(true);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const { queueStats, addToQueue, processQueue } = useOfflineQueue();

  // Check online status
  useEffect(() => {
    const handleOnline = () => setIsOnline(true);
    const handleOffline = () => setIsOnline(false);
    
    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);
    setIsOnline(navigator.onLine);
    
    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, []);

  // Process queue when back online
  useEffect(() => {
    if (isOnline && queueStats.total > 0) {
      processQueue(async (files: File[]) => {
        await onFilesUpload(files);
      });
    }
  }, [isOnline, queueStats.total, processQueue, onFilesUpload]);

  const handleFiles = useCallback(async (files: FileList | File[]) => {
    if (disabled) return;
    
    const fileArray = Array.from(files);
    if (fileArray.length === 0) return;

    if (!isOnline) {
      // Queue for later
      fileArray.forEach(file => addToQueue(file));
      return;
    }

    setIsUploading(true);
    try {
      await onFilesUpload(fileArray);
    } catch (error) {
      console.error('Upload failed:', error);
      // Queue failed uploads for retry
      fileArray.forEach(file => addToQueue(file));
    } finally {
      setIsUploading(false);
    }
  }, [disabled, isOnline, onFilesUpload, addToQueue]);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    if (!disabled) setIsDragOver(true);
  }, [disabled]);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
    if (!disabled) {
      handleFiles(e.dataTransfer.files);
    }
  }, [disabled, handleFiles]);

  const handleClick = useCallback(() => {
    if (!disabled && isOnline) {
      fileInputRef.current?.click();
    }
  }, [disabled, isOnline]);

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  return (
    <div className="mb-4" data-ui="upload-section">
      {/* Disabled Banner */}
      {disabled && reason && (
        <div className="mb-4 p-3 bg-yellow-50 border border-yellow-200 rounded-lg">
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 bg-yellow-500 rounded-full"></div>
            <span className="text-sm text-yellow-800">{reason}</span>
          </div>
        </div>
      )}

      {/* Offline Queue Status */}
      {queueStats.total > 0 && (
        <div className="mb-4 p-3 bg-blue-50 border border-blue-200 rounded-lg" data-ui="offline-queue">
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 bg-blue-500 rounded-full animate-pulse"></div>
              <span className="text-sm font-medium text-blue-800">
                {queueStats.isProcessing ? 'Processing queue...' : 'Files queued'}
              </span>
            </div>
            <span className="text-xs text-blue-600">
              {queueStats.total} file{queueStats.total !== 1 ? 's' : ''}
            </span>
          </div>
          
          {queueStats.pending > 0 && (
            <div className="text-xs text-blue-600">
              {queueStats.pending} pending
            </div>
          )}
          
          {queueStats.retrying > 0 && (
            <div className="text-xs text-orange-600">
              {queueStats.retrying} retrying
            </div>
          )}
          
          {queueStats.failed > 0 && (
            <div className="text-xs text-red-600">
              {queueStats.failed} failed
            </div>
          )}
        </div>
      )}

      {/* Upload Area */}
      <div
        className={`border-2 border-dashed rounded-[12px] p-6 text-center transition-colors ${
          isDragOver
            ? 'border-[#2563EB] bg-[#EFF6FF]'
            : 'border-[#E5E7EB] bg-[#F9FAFB] hover:border-[#D1D5DB]'
        } ${(disabled || (!isOnline && queueStats.total === 0)) ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}`}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={handleClick}
        role="button"
        tabIndex={0}
        aria-label={
          disabled 
            ? "Upload disabled"
            : !isOnline 
            ? "Offline - drop files to queue for later" 
            : queueStats.total > 0
            ? "Drop more files or click to browse"
            : "Drop invoices or delivery notes here"
        }
        data-ui="upload-area"
      >
        <div className="flex flex-col items-center">
          {isUploading ? (
            <div className="w-12 h-12 mb-4">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-[#2563EB]"></div>
            </div>
          ) : (
            <UploadIcon className="w-12 h-12 mb-4 text-[#6B7280]" />
          )}
          
          <h3 className="text-[16px] font-medium text-[#374151] mb-2">
            {isUploading 
              ? 'Scanning your document...' 
              : disabled
              ? 'Upload disabled'
              : !isOnline 
              ? 'Offline - files will be queued'
              : queueStats.total > 0
              ? 'Drop more files or click to browse'
              : 'Drop invoices or delivery notes here'
            }
          </h3>
          
          <p className="text-[14px] text-[#6B7280] mb-4">
            {disabled
              ? 'Enable license to upload documents'
              : !isOnline 
              ? 'Will process when back online'
              : 'Supports PDF files up to 50MB'
            }
          </p>
          
          {!disabled && isOnline && (
            <button
              className="bg-[#2563EB] hover:bg-[#1D4ED8] text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors"
              onClick={(e) => {
                e.stopPropagation();
                fileInputRef.current?.click();
              }}
              data-ui="browse-button"
            >
              Browse Files
            </button>
          )}
        </div>
      </div>

      <input
        ref={fileInputRef}
        type="file"
        multiple
        accept=".pdf,.png,.jpg,.jpeg"
        onChange={(e) => {
          if (e.target.files) {
            handleFiles(e.target.files);
          }
        }}
        className="hidden"
        data-ui="file-input"
      />

      {/* Queued Files */}
      {queueStats.total > 0 && (
        <div className="mt-4 space-y-2">
          <h4 className="text-sm font-medium text-gray-700">Queued Files</h4>
          {Array.from({ length: queueStats.total }, (_, i) => (
            <div key={i} className="flex items-center justify-between p-2 bg-gray-50 rounded text-xs" data-ui="queued-file">
              <span className="text-gray-600">File {i + 1}</span>
              <span className="text-gray-500">Queued</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default UploadSection; 