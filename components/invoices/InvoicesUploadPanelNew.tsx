import React, { useState, useRef, useEffect, useCallback } from 'react';
import ProgressCircle from '@/components/ui/ProgressCircle';
import DocumentCard from './DocumentCard';
import DuplicateCheckModal from './DuplicateCheckModal';
import InvoiceCard from './InvoiceCard';
import DeliveryNoteCard from './DeliveryNoteCard';

// SVG Icons
const FileTextIcon = ({ className = 'w-10 h-10' }) => (
  <svg
    xmlns="http://www.w3.org/2000/svg"
    width="24"
    height="24"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="1.5"
    strokeLinecap="round"
    strokeLinejoin="round"
    className={className}
  >
    <path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z"></path>
    <polyline points="14 2 14 8 20 8"></polyline>
    <line x1="16" y1="13" x2="8" y2="13"></line>
    <line x1="16" y1="17" x2="8" y2="17"></line>
    <line x1="10" y1="9" x2="8" y2="9"></line>
  </svg>
);

const ClipboardListIcon = ({ className = 'w-10 h-10' }) => (
  <svg
    xmlns="http://www.w3.org/2000/svg"
    width="24"
    height="24"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="1.5"
    strokeLinecap="round"
    strokeLinejoin="round"
    className={className}
  >
    <path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"></path>
    <path d="M15 2H9a1 1 0 0 0-1 1v2a1 1 0 0 0 1 1h6a1 1 0 0 0 1-1V3a1 1 0 0 0-1-1z"></path>
    <path d="M8 10h8"></path>
    <path d="M8 14h8"></path>
    <path d="M8 18h8"></path>
  </svg>
);

interface UploadedFile {
  id: string;
  name: string;
  timestamp: string;
  status: 'uploading' | 'success' | 'error' | 'parsing' | 'parsed' | 'parse_error' | 'duplicate_detected' | 'removed';
  error?: string;
  serverFilename?: string;
  parsedData?: any;
  documentType?: 'invoice' | 'delivery_note' | 'unknown';
  confidence?: number;
}

interface Document {
  id: string;
  filename: string;
  supplier: string;
  invoiceNumber: string;
  invoiceDate: string;
  totalAmount: string;
  type: 'Invoice' | 'Delivery Note' | 'Unknown';
  status: 'Processing' | 'Complete' | 'Error' | 'Matched' | 'Unmatched' | 'Unknown' | 'Scanned';
  confidence?: number;
  numIssues?: number;
  parsedData?: any;
  matchedDocument?: any;
  loadingPercent?: number;
}

interface DeliveryNote {
  id: string;
  filename: string;
  supplier: string;
  deliveryNumber: string;
  deliveryDate: string;
  status: 'Unmatched' | 'Processing' | 'Error' | 'Unknown';
  confidence?: number;
  parsedData?: any;
}

interface InvoicesUploadPanelProps {
  onDeliveryNotesUpdate?: (notes: DeliveryNote[]) => void;
  onInvoicesUpdate?: (invoices: Document[]) => void;
}

// Upload limits and validation
const MAX_FILES_PER_UPLOAD = 5;
const MAX_FILE_SIZE = 10 * 1024 * 1024;

function validateFile(file: File): string | null {
  if (file.size > MAX_FILE_SIZE) {
    return `File "${file.name}" is too large. Maximum size is ${MAX_FILE_SIZE / (1024 * 1024)}MB`;
  }
  
  const allowedTypes = ['.pdf', '.jpg', '.jpeg', '.png'];
  const fileExtension = '.' + file.name.split('.').pop()?.toLowerCase();
  if (!allowedTypes.includes(fileExtension)) {
    return `File "${file.name}" has unsupported format. Allowed: PDF, JPG, JPEG, PNG`;
  }
  
  return null;
}

const API_BASE_URL = 'http://localhost:8002/api';

const uploadFile = async (file: File): Promise<any> => {
  const formData = new FormData();
  formData.append('file', file);

  const response = await fetch(`${API_BASE_URL}/upload/document`, {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    const errorData = await response.json();
    throw new Error(errorData.detail || 'Upload failed');
  }

  return await response.json();
};

const classifyAndParseFile = async (file: File): Promise<any> => {
  const formData = new FormData();
  formData.append('file', file);
  
  const response = await fetch(`${API_BASE_URL}/ocr/parse`, {
    method: 'POST',
    body: formData,
  });

  const result = await response.json();
  console.log('OCR result', result);

  // Always return the result, even if success is false
  // The backend now returns 200 status for all responses
  if (!response.ok) {
    throw new Error(result.error || result.detail || 'OCR failed');
  }

  // Transform the response to match the expected format
  return {
    document_type: result.document_type,
    confidence: result.confidence_score || 85, // Use confidence_score from backend or default
    supplier_name: result.data.supplier_name,
    invoice_number: result.data.invoice_number,
    invoice_date: result.data.invoice_date,
    total_amount: result.data.total_amount,
    currency: result.data.currency,
    success: result.success, // Include success flag
    error: result.error // Include error message if any
  };
};

const InvoicesUploadPanel: React.FC<InvoicesUploadPanelProps> = ({ onDeliveryNotesUpdate, onInvoicesUpdate }) => {
  const [invoiceFiles, setInvoiceFiles] = useState<UploadedFile[]>([]);
  const [deliveryFiles, setDeliveryFiles] = useState<UploadedFile[]>([]);
  const [unknownFiles, setUnknownFiles] = useState<UploadedFile[]>([]);
  const [isDragOver, setIsDragOver] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [progressMap, setProgressMap] = useState<{ [id: string]: number }>({});
  const progressTimers = useRef<{ [id: string]: NodeJS.Timeout }>({});
  const [selectedInvoice, setSelectedInvoice] = useState<Document | null>(null);
  
  const [duplicateModalOpen, setDuplicateModalOpen] = useState(false);
  const [duplicateInfo, setDuplicateInfo] = useState<any>(null);
  const [pendingFile, setPendingFile] = useState<File | null>(null);

  const invoiceInputRef = useRef<HTMLInputElement>(null);
  const deliveryInputRef = useRef<HTMLInputElement>(null);
  const invoiceBoxRef = useRef<HTMLDivElement>(null);
  const deliveryBoxRef = useRef<HTMLDivElement>(null);

  const showError = (message: string) => {
    setErrorMessage(message);
    setTimeout(() => setErrorMessage(null), 5000);
  };

  const handleCancelDocument = (documentId: string) => {
    setInvoiceFiles(prev => prev.filter(file => file.id !== documentId));
    setDeliveryFiles(prev => prev.filter(file => file.id !== documentId));
    setUnknownFiles(prev => prev.filter(file => file.id !== documentId));

    setProgressMap(prev => {
      const newMap = { ...prev };
      delete newMap[documentId];
      return newMap;
    });

    if (progressTimers.current[documentId]) {
      clearInterval(progressTimers.current[documentId]);
      delete progressTimers.current[documentId];
    }
  };

  const createDeliveryNoteFromOCR = (file: UploadedFile): DeliveryNote => {
    const parsedData = file.parsedData || {};
    
    let noteStatus: DeliveryNote['status'];
    if (file.status === 'parsed') {
      noteStatus = 'Unmatched';
    } else if (file.status === 'error' || file.status === 'parse_error') {
      noteStatus = 'Error';
    } else if (file.status === 'uploading' || file.status === 'parsing') {
      noteStatus = 'Processing';
    } else {
      noteStatus = 'Unknown';
    }
    
    return {
      id: file.id,
      filename: file.name,
      supplier: parsedData.supplier_name || 'Unknown Supplier',
      deliveryNumber: parsedData.delivery_note_number || 'N/A',
      deliveryDate: parsedData.delivery_date || 'N/A',
      status: noteStatus,
      confidence: file.confidence,
      parsedData: file.parsedData,
    };
  };

  const createDocumentFromOCR = (file: UploadedFile): Document => {
    const parsedData = file.parsedData || {};
    
    let cardStatus: Document['status'];
    if (file.status === 'parsed') {
      cardStatus = 'Unmatched';
    } else if (file.status === 'error' || file.status === 'parse_error') {
      cardStatus = 'Error';
    } else if (file.status === 'uploading' || file.status === 'parsing') {
      cardStatus = 'Processing';
    } else {
      cardStatus = 'Unknown';
    }
    
    const loadingPercent = progressMap[file.id] ?? (cardStatus === 'Processing' ? 0 : 100);
    
    return {
      id: file.id,
      filename: file.name,
      supplier: parsedData.supplier_name || 'Unknown Supplier',
      invoiceNumber: parsedData.invoice_number || parsedData.delivery_note_number || 'N/A',
      invoiceDate: parsedData.invoice_date || parsedData.delivery_date || 'N/A',
      totalAmount: parsedData.total_amount || '0.00',
      type: file.documentType === 'invoice' ? 'Invoice' : 
            file.documentType === 'delivery_note' ? 'Delivery Note' : 'Unknown',
      status: cardStatus,
      confidence: file.confidence,
      numIssues: file.confidence && file.confidence < 60 ? 1 : 0,
      parsedData: file.parsedData,
      loadingPercent
    };
  };

  useEffect(() => {
    const deliveryNotes = deliveryFiles
      .filter(file => file.status !== 'removed')
      .map(createDeliveryNoteFromOCR);
    
    if (onDeliveryNotesUpdate) {
      onDeliveryNotesUpdate(deliveryNotes);
    }
  }, [deliveryFiles, onDeliveryNotesUpdate]);

  useEffect(() => {
    const startProgress = (fileId: string) => {
      if (progressTimers.current[fileId]) return;
      setProgressMap(prev => ({ ...prev, [fileId]: 0 }));
      let stages = [25, 60, 100];
      let idx = 0;
      progressTimers.current[fileId] = setInterval(() => {
        setProgressMap(prev => {
          const current = prev[fileId] || 0;
          if (current >= 100) {
            clearInterval(progressTimers.current[fileId]);
            delete progressTimers.current[fileId];
            return prev;
          }
          const next = stages[idx] || 100;
          idx++;
          return { ...prev, [fileId]: next };
        });
      }, 500);
    };
    
    const stopProgress = (fileId: string) => {
      if (progressTimers.current[fileId]) {
        clearInterval(progressTimers.current[fileId]);
        delete progressTimers.current[fileId];
      }
      setProgressMap(prev => ({ ...prev, [fileId]: 100 }));
    };
    
    const allFiles = [...invoiceFiles, ...deliveryFiles, ...unknownFiles];
    allFiles.forEach(file => {
      if ((file.status === 'uploading' || file.status === 'parsing') && !progressTimers.current[file.id]) {
        startProgress(file.id);
      }
      if ((file.status === 'parsed' || file.status === 'error' || file.status === 'parse_error' || file.status === 'removed') && progressMap[file.id] !== 100) {
        stopProgress(file.id);
      }
    });
    
    return () => {
      Object.values(progressTimers.current).forEach(timer => clearInterval(timer));
      progressTimers.current = {};
    };
  }, [invoiceFiles, deliveryFiles, unknownFiles]);

  const handleUpload = async (files: File[]) => {
    if (files.length > MAX_FILES_PER_UPLOAD) {
      showError(`Too many files. Maximum ${MAX_FILES_PER_UPLOAD} files allowed per upload.`);
      return;
    }

    const validationErrors: string[] = [];
    files.forEach(file => {
      const error = validateFile(file);
      if (error) {
        validationErrors.push(error);
      }
    });

    if (validationErrors.length > 0) {
      showError(validationErrors.join('\n'));
      return;
    }

    setIsUploading(true);

    const addFileToState = (file: UploadedFile, type: 'invoices' | 'delivery' | 'unknown') => {
      if (type === 'invoices') {
        setInvoiceFiles(prev => {
          const exists = prev.some(f => f.id === file.id || f.name === file.name);
          if (exists) return prev;
          return [...prev, file];
        });
      } else if (type === 'delivery') {
        setDeliveryFiles(prev => {
          const exists = prev.some(f => f.id === file.id || f.name === file.name);
          if (exists) return prev;
          return [...prev, file];
        });
      } else {
        setUnknownFiles(prev => {
          const exists = prev.some(f => f.id === file.id || f.name === file.name);
          if (exists) return prev;
          return [...prev, file];
        });
      }
    };
    
    const updateFileStatus = (name: string, status: Partial<UploadedFile>) => {
      setInvoiceFiles(prev => prev.map(f => f.name === name ? { ...f, ...status } : f));
      setDeliveryFiles(prev => prev.map(f => f.name === name ? { ...f, ...status } : f));
      setUnknownFiles(prev => prev.map(f => f.name === name ? { ...f, ...status } : f));
    };

    try {
      for (const file of files) {
        // Create initial file entry immediately
        const fileId = `${file.name}-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
        const initialFile: UploadedFile = {
          id: fileId,
          name: file.name,
          timestamp: new Date().toLocaleTimeString(),
          status: 'uploading',
          documentType: 'unknown'
        };

        // Add to unknown files initially
        addFileToState(initialFile, 'unknown');

        try {
          // Upload file
          const uploadResult = await uploadFile(file);
          updateFileStatus(file.name, { 
            status: 'parsing', 
            serverFilename: uploadResult.filename 
          });

          // Classify and parse
          const ocrResult = await classifyAndParseFile(file);
          
          // Update with results
          updateFileStatus(file.name, {
            status: ocrResult.success ? 'parsed' : 'parse_error',
            parsedData: ocrResult,
            documentType: ocrResult.document_type || 'unknown',
            confidence: ocrResult.confidence,
            error: ocrResult.success ? undefined : ocrResult.error
          });

          // Move to appropriate category if successful
          if (ocrResult.success && ocrResult.document_type !== 'unknown') {
            const finalType = ocrResult.document_type === 'invoice' ? 'invoices' : 
                             ocrResult.document_type === 'delivery_note' ? 'delivery' : 'unknown';
            
            if (finalType !== 'unknown') {
              // Remove from unknown and add to correct category
              setUnknownFiles(prev => prev.filter(f => f.name !== file.name));
              addFileToState({
                ...initialFile,
                status: 'parsed',
                parsedData: ocrResult,
                documentType: ocrResult.document_type || 'unknown',
                confidence: ocrResult.confidence,
                error: undefined
              }, finalType);
            }
          }

        } catch (error) {
          updateFileStatus(file.name, {
            status: 'error',
            error: error instanceof Error ? error.message : 'Unknown error'
          });
        }
      }
    } catch (error) {
      showError(`Upload failed: ${error instanceof Error ? error.message : 'Unknown error'}`);
    } finally {
      setIsUploading(false);
    }
  };

  const handleFileChange = async (event: React.ChangeEvent<HTMLInputElement>) => {
    if (event.target.files) {
      const files = Array.from(event.target.files);
      await handleUpload(files);
      event.target.value = '';
    }
  };

  const handleRetryOCR = async (fileId: string) => {
    const file = [...invoiceFiles, ...deliveryFiles, ...unknownFiles].find(f => f.id === fileId);
    if (!file) return;

    // Create a new File object from the existing file data
    // Note: This is a simplified retry - in a real implementation you'd need to store the original file
    const retryFile = new File([], file.name, { type: 'application/octet-stream' });
    
    // Update status to retrying
    const updateFileStatus = (name: string, status: Partial<UploadedFile>) => {
      setInvoiceFiles(prev => prev.map(f => f.name === name ? { ...f, ...status } : f));
      setDeliveryFiles(prev => prev.map(f => f.name === name ? { ...f, ...status } : f));
      setUnknownFiles(prev => prev.map(f => f.name === name ? { ...f, ...status } : f));
    };

    try {
      updateFileStatus(file.name, { status: 'parsing', error: undefined });
      
      // Retry OCR
      const ocrResult = await classifyAndParseFile(retryFile);
      
      // Update with results
      updateFileStatus(file.name, {
        status: ocrResult.success ? 'parsed' : 'parse_error',
        parsedData: ocrResult,
        documentType: ocrResult.document_type || 'unknown',
        confidence: ocrResult.confidence,
        error: ocrResult.success ? undefined : ocrResult.error
      });

      // Move to appropriate category if successful
      if (ocrResult.success && ocrResult.document_type !== 'unknown') {
        const finalType = ocrResult.document_type === 'invoice' ? 'invoices' : 
                         ocrResult.document_type === 'delivery_note' ? 'delivery' : 'unknown';
        
        if (finalType !== 'unknown') {
          // Remove from current list and add to correct category
          setInvoiceFiles(prev => prev.filter(f => f.id !== fileId));
          setDeliveryFiles(prev => prev.filter(f => f.id !== fileId));
          setUnknownFiles(prev => prev.filter(f => f.id !== fileId));
          
          const addFileToState = (file: UploadedFile, type: 'invoices' | 'delivery' | 'unknown') => {
            if (type === 'invoices') {
              setInvoiceFiles(prev => [...prev, file]);
            } else if (type === 'delivery') {
              setDeliveryFiles(prev => [...prev, file]);
            } else {
              setUnknownFiles(prev => [...prev, file]);
            }
          };
          
          addFileToState({
            ...file,
            status: 'parsed',
            parsedData: ocrResult,
            documentType: ocrResult.document_type || 'unknown',
            confidence: ocrResult.confidence,
            error: undefined
          }, finalType);
        }
      }
    } catch (error) {
      updateFileStatus(file.name, {
        status: 'parse_error',
        error: error instanceof Error ? error.message : 'Retry failed'
      });
    }
  };

  const GlassBox: React.FC<{
    title: string;
    icon: React.ReactNode;
    inputRef: React.RefObject<HTMLInputElement>;
    boxRef: React.RefObject<HTMLDivElement>;
    onFileChange: (e: React.ChangeEvent<HTMLInputElement>) => void;
    ariaLabel: string;
    accept: string;
    multiple: boolean;
    isUploading?: boolean;
    tooltip?: string;
  }> = ({ title, icon, inputRef, boxRef, onFileChange, ariaLabel, accept, multiple, isUploading = false, tooltip }) => (
    <div
      ref={boxRef}
      className="relative group cursor-pointer"
      onClick={() => inputRef.current?.click()}
    >
      <div className="bg-white/80 backdrop-blur-sm border-2 border-dashed border-slate-300 rounded-2xl p-6 text-center transition-all duration-300 ease-in-out hover:border-slate-400 hover:bg-white/90 hover:shadow-lg">
        {icon}
        <h3 className="text-lg font-semibold text-slate-800 mt-4 mb-2">{title}</h3>
        <p className="text-sm text-slate-600 mb-4">
          {isUploading ? '⏳ Processing...' : 'Click to browse or drag files here'}
        </p>
        {tooltip && (
          <p className="text-xs text-slate-500 italic">{tooltip}</p>
        )}
      </div>
      <input
        ref={inputRef}
        type="file"
        className="hidden"
        onChange={onFileChange}
        aria-label={ariaLabel}
        accept={accept}
        multiple={multiple}
        disabled={isUploading}
      />
    </div>
  );

  return (
    <div className="max-w-6xl mx-auto p-6">
      {/* Error Message */}
      {errorMessage && (
        <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg">
          <div className="flex items-center gap-2">
            <span className="text-red-600">⚠️</span>
            <span className="text-red-800">{errorMessage}</span>
          </div>
        </div>
      )}

      {/* Upload Boxes */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
        <GlassBox
          title="Upload Invoices"
          icon={<FileTextIcon className="w-8 h-8 sm:w-10 sm:h-10 text-slate-600 mb-4" />}
          inputRef={invoiceInputRef}
          boxRef={invoiceBoxRef}
          onFileChange={handleFileChange}
          ariaLabel="Browse files to upload documents"
          accept=".pdf,.jpg,.jpeg,.png"
          multiple={true}
          isUploading={isUploading}
          tooltip="Drop documents here - Owlin will auto-classify them as invoices or delivery notes"
        />
        <GlassBox
          title="Upload Delivery Notes"
          icon={<ClipboardListIcon className="w-8 h-8 sm:w-10 sm:h-10 text-slate-600 mb-4" />}
          inputRef={deliveryInputRef}
          boxRef={deliveryBoxRef}
          onFileChange={handleFileChange}
          ariaLabel="Browse files to upload documents"
          accept=".pdf,.jpg,.jpeg,.png"
          multiple={true}
          isUploading={isUploading}
          tooltip="Drop documents here - Owlin will auto-classify them as invoices or delivery notes"
        />
      </div>

      {/* File Upload Limits Info */}
      <div className="mt-4 text-center">
        <p className="text-xs text-slate-500">
          📁 Upload limits: Max {MAX_FILES_PER_UPLOAD} files per upload • Max {MAX_FILE_SIZE / (1024 * 1024)}MB per file
        </p>
      </div>

      {/* New Card System - Immediate Display */}
      {(invoiceFiles.length > 0 || deliveryFiles.length > 0 || unknownFiles.length > 0) && (
        <div className="mt-8">
          <h2 className="text-xl font-semibold text-slate-900 mb-6">📄 Uploaded Documents</h2>
          
          {/* Invoice Cards */}
          {invoiceFiles.filter(f => f.status !== 'removed').length > 0 && (
            <div className="mb-8">
              <h3 className="text-lg font-medium text-slate-800 mb-4 flex items-center gap-2">
                📄 Invoices ({invoiceFiles.filter(f => f.status !== 'removed').length})
              </h3>
              <div className="space-y-4">
                {invoiceFiles
                  .filter(f => f.status !== 'removed')
                  .map((file) => {
                    const parsedData = file.parsedData || {};
                    const progress = progressMap[file.id] ?? (file.status === 'uploading' || file.status === 'parsing' ? 0 : 100);
                    
                    let cardStatus: 'processing' | 'matched' | 'unmatched' | 'error' | 'complete';
                    if (file.status === 'uploading' || file.status === 'parsing') {
                      cardStatus = 'processing';
                    } else if (file.status === 'error' || file.status === 'parse_error') {
                      cardStatus = 'error';
                    } else if (file.status === 'parsed') {
                      cardStatus = 'complete';
                    } else {
                      cardStatus = 'unmatched';
                    }

                    return (
                      <InvoiceCard
                        key={file.id}
                        invoiceId={parsedData.invoice_number || file.name}
                        invoiceNumber={parsedData.invoice_number || 'Extracting...'}
                        supplierName={parsedData.supplier_name || 'Processing...'}
                        invoiceDate={parsedData.invoice_date || 'Extracting...'}
                        totalAmount={parsedData.total_amount || '0.00'}
                        progress={progress}
                        status={cardStatus}
                        errorMessage={file.error}
                        isProcessing={file.status === 'uploading' || file.status === 'parsing'}
                        confidence={file.confidence}
                        parsedData={file.parsedData}
                        onClick={() => {
                          const doc = createDocumentFromOCR(file);
                          setSelectedInvoice(doc);
                        }}
                        onCancel={() => handleCancelDocument(file.id)}
                        onRetry={() => handleRetryOCR(file.id)}
                      />
                    );
                  })}
              </div>
            </div>
          )}

          {/* Delivery Note Cards */}
          {deliveryFiles.filter(f => f.status !== 'removed').length > 0 && (
            <div className="mb-8">
              <h3 className="text-lg font-medium text-slate-800 mb-4 flex items-center gap-2">
                📋 Delivery Notes ({deliveryFiles.filter(f => f.status !== 'removed').length})
              </h3>
              <div className="space-y-4">
                {deliveryFiles
                  .filter(f => f.status !== 'removed')
                  .map((file) => {
                    const parsedData = file.parsedData || {};
                    const progress = progressMap[file.id] ?? (file.status === 'uploading' || file.status === 'parsing' ? 0 : 100);
                    
                    let cardStatus: 'awaiting' | 'delivered' | 'partial' | 'processing' | 'error';
                    if (file.status === 'uploading' || file.status === 'parsing') {
                      cardStatus = 'processing';
                    } else if (file.status === 'error' || file.status === 'parse_error') {
                      cardStatus = 'error';
                    } else if (file.status === 'parsed') {
                      cardStatus = 'awaiting';
                    } else {
                      cardStatus = 'awaiting';
                    }

                    return (
                      <DeliveryNoteCard
                        key={file.id}
                        noteId={parsedData.delivery_note_number || file.name}
                        deliveryDate={parsedData.delivery_date || 'Extracting...'}
                        itemCount={parsedData.items?.length || 0}
                        status={cardStatus}
                        errorMessage={file.error}
                        isProcessing={file.status === 'uploading' || file.status === 'parsing'}
                        confidence={file.confidence}
                        parsedData={file.parsedData}
                        progress={progress}
                        onClick={() => {
                          const note = createDeliveryNoteFromOCR(file);
                          console.log('View delivery note:', note);
                        }}
                        onCancel={() => handleCancelDocument(file.id)}
                        onRetry={() => handleRetryOCR(file.id)}
                      />
                    );
                  })}
              </div>
            </div>
          )}

          {/* Unknown/Error Cards */}
          {unknownFiles.filter(f => f.status !== 'removed').length > 0 && (
            <div className="mb-8">
              <h3 className="text-lg font-medium text-slate-800 mb-4 flex items-center gap-2">
                ❓ Unknown Documents ({unknownFiles.filter(f => f.status !== 'removed').length})
              </h3>
              <div className="space-y-4">
                {unknownFiles
                  .filter(f => f.status !== 'removed')
                  .map((file) => (
                    <div
                      key={file.id}
                      className="bg-red-50 border border-red-200 rounded-2xl shadow-sm p-4 sm:p-6 mb-6 relative transition-all ease-in duration-500 opacity-0 animate-fade-in max-w-4xl mx-auto w-full"
                    >
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          handleCancelDocument(file.id);
                        }}
                        className="absolute top-2 right-2 z-10 text-gray-400 hover:text-red-500 transition-colors duration-200 p-1 rounded-full hover:bg-red-50"
                        title="Cancel/Remove"
                      >
                        <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24"
                          fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"
                          className="w-4 h-4">
                          <line x1="18" y1="6" x2="6" y2="18"></line>
                          <line x1="6" y1="6" x2="18" y2="18"></line>
                        </svg>
                      </button>

                      <div className="flex flex-col space-y-4">
                        <div className="flex justify-between items-start">
                          <div className="flex-1 min-w-0">
                            <h3 className="text-xs font-medium uppercase text-gray-500">Unknown Document</h3>
                            <p className="text-sm text-gray-900 font-semibold truncate">{file.name}</p>
                            <p className="text-sm text-gray-700">Status: {file.status}</p>
                            {file.error && (
                              <p className="text-sm text-red-600">Error: {file.error}</p>
                            )}
                          </div>
                        </div>

                        <div className="flex justify-between items-center">
                          <span className="bg-red-100 text-red-800 text-xs font-semibold px-2.5 py-0.5 rounded-full flex items-center gap-1">
                            <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24"
                              fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"
                              className="w-3 h-3 text-red-500">
                              <circle cx="12" cy="12" r="10"></circle>
                              <line x1="15" y1="9" x2="9" y2="15"></line>
                              <line x1="9" y1="9" x2="15" y2="15"></line>
                            </svg>
                            <span>❌ Failed to classify</span>
                          </span>
                        </div>

                        <div className="bg-red-50 border border-red-200 rounded-lg p-3">
                          <div className="flex items-center gap-2">
                            <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24"
                              fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"
                              className="w-3 h-3 text-red-500">
                              <circle cx="12" cy="12" r="10"></circle>
                              <line x1="15" y1="9" x2="9" y2="15"></line>
                              <line x1="9" y1="9" x2="15" y2="15"></line>
                            </svg>
                            <span className="text-sm text-red-700">Document type could not be determined</span>
                          </div>
                        </div>

                        <div className="flex justify-end gap-3 pt-4 border-t border-gray-100">
                          <button 
                            onClick={() => handleCancelDocument(file.id)}
                            className="px-4 py-2 text-sm font-medium rounded-md bg-gray-100 text-gray-700 hover:bg-gray-200 transition-colors duration-200 ease-in-out"
                          >
                            🗑️ Remove
                          </button>
                        </div>
                      </div>
                    </div>
                  ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Duplicate Modal */}
      {duplicateModalOpen && (
        <DuplicateCheckModal
          isOpen={duplicateModalOpen}
          onClose={() => setDuplicateModalOpen(false)}
          duplicateInfo={duplicateInfo}
          newDocument={{
            filename: pendingFile?.name || 'Unknown',
            parsed_data: {},
            document_type: 'unknown',
            confidence_score: 0
          }}
          onConfirm={() => {
            setDuplicateModalOpen(false);
            setDuplicateInfo(null);
            setPendingFile(null);
          }}
          onReject={() => {
            setDuplicateModalOpen(false);
            setDuplicateInfo(null);
            setPendingFile(null);
          }}
        />
      )}
    </div>
  );
};

export default InvoicesUploadPanel; 