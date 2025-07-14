import React, { useState, useRef, useEffect, useCallback } from 'react';
import ProgressCircle from '@/components/ui/ProgressCircle';
import { DocumentCard } from './DocumentCard';
import DuplicateCheckModal from './DuplicateCheckModal';

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
  name: string;
  timestamp: string;
  status: 'uploading' | 'success' | 'error' | 'parsing' | 'parsed' | 'parse_error' | 'duplicate_detected';
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
  parsedData?: any; // Added for DocumentCard
  matchedDocument?: any; // Changed from string to any to match the object structure
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
const MAX_FILES_PER_UPLOAD = 5; // Limit files per upload
const MAX_FILE_SIZE = 10 * 1024 * 1024; // 10MB

// Validate file before upload
function validateFile(file: File): string | null {
  // Check file size
  if (file.size > MAX_FILE_SIZE) {
    return `File "${file.name}" is too large. Maximum size is ${MAX_FILE_SIZE / (1024 * 1024)}MB`;
  }
  
  // Check file type
  const allowedTypes = ['.pdf', '.jpg', '.jpeg', '.png'];
  const fileExtension = '.' + file.name.split('.').pop()?.toLowerCase();
  if (!allowedTypes.includes(fileExtension)) {
    return `File "${file.name}" has unsupported format. Allowed: PDF, JPG, JPEG, PNG`;
  }
  
  return null; // File is valid
}

// Utility: Resize/optimize image files before upload (JPEG/PNG only)
async function optimizeImageFile(file: File, maxWidth = 1600, maxHeight = 1600, quality = 0.8): Promise<File> {
  return new Promise((resolve, reject) => {
    if (!file.type.startsWith('image/')) return resolve(file); // Only process images
    const img = new window.Image();
    const url = URL.createObjectURL(file);
    img.onload = () => {
      let { width, height } = img;
      let newWidth = width;
      let newHeight = height;
      if (width > maxWidth || height > maxHeight) {
        const ratio = Math.min(maxWidth / width, maxHeight / height);
        newWidth = Math.round(width * ratio);
        newHeight = Math.round(height * ratio);
      }
      const canvas = document.createElement('canvas');
      canvas.width = newWidth;
      canvas.height = newHeight;
      const ctx = canvas.getContext('2d');
      if (!ctx) return resolve(file);
      ctx.drawImage(img, 0, 0, newWidth, newHeight);
      canvas.toBlob(
        (blob) => {
          if (blob) {
            const optimized = new File([blob], file.name, { type: file.type });
            resolve(optimized);
          } else {
            resolve(file);
          }
        },
        file.type,
        quality
      );
    };
    img.onerror = () => {
      URL.revokeObjectURL(url);
      resolve(file); // fallback to original
    };
    img.src = url;
  });
}

// API base URL - adjust if your FastAPI server runs on a different port
const API_BASE_URL = 'http://localhost:8001/api';

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
  
  const response = await fetch('/api/ocr/parse', {
    method: 'POST',
    body: formData,
  });

  const result = await response.json();
  console.log('OCR result', result);

  if (!response.ok) {
    throw new Error(result.detail || 'OCR failed');
  }

  return result;
};

const checkForDuplicate = async (file: File): Promise<any> => {
  const formData = new FormData();
  formData.append('file', file);
  
  const response = await fetch(`${API_BASE_URL}/ocr/check-duplicate`, {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    const errorData = await response.json();
    throw new Error(errorData.detail || 'Duplicate check failed');
  }

  return await response.json();
};

// Concurrency queue for file processing
const MAX_CONCURRENT = 2;
const BATCH_DELAY = 200; // ms delay between batches

// Utility to process promises in batches
async function processInBatches<T>(
  tasks: (() => Promise<T>)[],
  batchSize: number
): Promise<T[]> {
  const results: T[] = [];
  for (let i = 0; i < tasks.length; i += batchSize) {
    const batch = tasks.slice(i, i + batchSize).map(task => task());
    const batchResults = await Promise.all(batch);
    results.push(...batchResults);
    
    // Add delay between batches (except for the last batch)
    if (i + batchSize < tasks.length) {
      await new Promise(resolve => setTimeout(resolve, BATCH_DELAY));
    }
  }
  return results;
}

async function processFilesWithConcurrency(
  files: File[],
  addFileToState: (file: UploadedFile, type: 'invoices' | 'delivery' | 'unknown') => void,
  updateFileStatus: (name: string, status: Partial<UploadedFile>) => void,
  onError: (message: string) => void,
  checkDuplicates: boolean = true
) {
  async function uploadAndClassifyFile(file: File) {
    // Add file to state as uploading
    addFileToState({
      name: file.name,
      timestamp: new Date().toLocaleString(),
      status: 'uploading',
    }, 'unknown');
    
    try {
      // Step 0: Optimize image if needed
      let fileToUpload = file;
      if (file.type.startsWith('image/')) {
        try {
          fileToUpload = await optimizeImageFile(file);
        } catch (optimizeError) {
          console.warn(`Image optimization failed for ${file.name}:`, optimizeError);
          // Continue with original file
        }
      }
      
      // Step 1: Check for duplicates if enabled
      if (checkDuplicates) {
        try {
          const duplicateCheck = await checkForDuplicate(fileToUpload);
          if (duplicateCheck.is_duplicate) {
            // Return special status to trigger modal
            updateFileStatus(file.name, { 
              status: 'duplicate_detected',
              parsedData: duplicateCheck.parsed_data,
              documentType: duplicateCheck.document_type,
              confidence: duplicateCheck.confidence_score
            });
            return { type: 'duplicate', data: duplicateCheck };
          }
        } catch (error) {
          console.error('Error in duplicate check:', error);
          // Continue with normal processing if duplicate check fails
        }
      }
      
      // Step 2: Upload file
      const uploadResult = await uploadFile(fileToUpload);
      updateFileStatus(file.name, { status: 'success', serverFilename: uploadResult.filename });
      
      // Step 3: Classify and parse with OCR
      updateFileStatus(file.name, { status: 'parsing' });
      const classificationResult = await classifyAndParseFile(fileToUpload);
      
      // Determine document type and confidence
      const docType = classificationResult.type || 'unknown';
      const confidence = classificationResult.confidence || 0;
      
      // Update file with classification results
      updateFileStatus(file.name, { 
        status: 'parsed', 
        parsedData: classificationResult.parsed_data,
        documentType: docType,
        confidence: confidence
      });
      
      // Move file to appropriate list based on classification
      if (docType === 'invoice') {
        addFileToState({
          name: file.name,
          timestamp: new Date().toLocaleString(),
          status: 'parsed',
          parsedData: classificationResult.parsed_data,
          documentType: docType,
          confidence: confidence,
          serverFilename: uploadResult.filename
        }, 'invoices');
      } else if (docType === 'delivery_note') {
        addFileToState({
          name: file.name,
          timestamp: new Date().toLocaleString(),
          status: 'parsed',
          parsedData: classificationResult.parsed_data,
          documentType: docType,
          confidence: confidence,
          serverFilename: uploadResult.filename
        }, 'delivery');
      } else {
        // Unknown type - keep in current list but mark as unknown
        updateFileStatus(file.name, { 
          documentType: 'unknown',
          confidence: confidence
        });
      }
      
      return { type: 'success', data: classificationResult };
      
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Processing failed';
      updateFileStatus(file.name, {
        status: errorMessage.includes('OCR') || errorMessage.includes('Classification') ? 'parse_error' : 'error',
        error: errorMessage,
      });
      
      // Show error notification
      onError(`Failed to process "${file.name}": ${errorMessage}`);
      return { type: 'error', data: errorMessage };
    }
  }

  // Create upload tasks
  const uploadTasks = files.map(file => async () => {
    return await uploadAndClassifyFile(file);
  });

  // Process in batches of MAX_CONCURRENT
  return await processInBatches(uploadTasks, MAX_CONCURRENT);
}

const InvoicesUploadPanel: React.FC<InvoicesUploadPanelProps> = ({ onDeliveryNotesUpdate, onInvoicesUpdate }) => {
  const [invoiceFiles, setInvoiceFiles] = useState<UploadedFile[]>([]);
  const [deliveryFiles, setDeliveryFiles] = useState<UploadedFile[]>([]);
  const [unknownFiles, setUnknownFiles] = useState<UploadedFile[]>([]);
  const [documents, setDocuments] = useState<Document[]>([]);
  const [isDragOver, setIsDragOver] = useState(false);
  const [dragTargetArea, setDragTargetArea] = useState<'invoices' | 'delivery' | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  
  // Duplicate detection state
  const [duplicateModalOpen, setDuplicateModalOpen] = useState(false);
  const [duplicateInfo, setDuplicateInfo] = useState<any>(null);
  const [pendingFile, setPendingFile] = useState<File | null>(null);
  const [pendingFileType, setPendingFileType] = useState<'invoices' | 'delivery' | 'unknown'>('unknown');

  const invoiceInputRef = useRef<HTMLInputElement>(null);
  const deliveryInputRef = useRef<HTMLInputElement>(null);
  const invoiceBoxRef = useRef<HTMLDivElement>(null);
  const deliveryBoxRef = useRef<HTMLDivElement>(null);

  // Show error notification
  const showError = (message: string) => {
    setErrorMessage(message);
    // Auto-hide after 5 seconds
    setTimeout(() => setErrorMessage(null), 5000);
  };

  // Cancel document handler
  const handleCancelDocument = (documentId: string) => {
    // Remove from documents state
    setDocuments(prev => prev.filter(doc => doc.id !== documentId));
    
    // Remove from invoice files state (match by timestamp)
    setInvoiceFiles(prev => prev.filter(file => {
      const fileTimestamp = new Date(file.timestamp).getTime().toString();
      return fileTimestamp !== documentId;
    }));
    
    // Remove from delivery files state (match by timestamp)
    setDeliveryFiles(prev => prev.filter(file => {
      const fileTimestamp = new Date(file.timestamp).getTime().toString();
      return fileTimestamp !== documentId;
    }));
    
    // Remove from unknown files state (match by timestamp)
    setUnknownFiles(prev => prev.filter(file => {
      const fileTimestamp = new Date(file.timestamp).getTime().toString();
      return fileTimestamp !== documentId;
    }));
  };

  // Helper function to create delivery note from OCR result
  const createDeliveryNoteFromOCR = (file: UploadedFile): DeliveryNote => {
    const parsedData = file.parsedData || {};
    const timestamp = new Date().getTime().toString();
    
    // Determine status for delivery note
    let noteStatus: DeliveryNote['status'];
    if (file.status === 'parsed') {
      noteStatus = 'Unmatched'; // All parsed delivery notes start as unmatched
    } else if (file.status === 'error' || file.status === 'parse_error') {
      noteStatus = 'Error';
    } else if (file.status === 'uploading' || file.status === 'parsing') {
      noteStatus = 'Processing';
    } else {
      noteStatus = 'Unknown';
    }
    
    return {
      id: timestamp,
      filename: file.name,
      supplier: parsedData.supplier_name || 'Unknown Supplier',
      deliveryNumber: parsedData.delivery_note_number || 'N/A',
      deliveryDate: parsedData.delivery_date || 'N/A',
      status: noteStatus,
      confidence: file.confidence,
      parsedData: file.parsedData,
    };
  };

  // Update delivery notes when delivery files change
  useEffect(() => {
    const deliveryNotes = deliveryFiles
      .filter(file => file.status === 'parsed' || file.status === 'error' || file.status === 'parse_error' || file.status === 'uploading' || file.status === 'parsing')
      .map(createDeliveryNoteFromOCR);
    
    if (onDeliveryNotesUpdate) {
      onDeliveryNotesUpdate(deliveryNotes);
    }
  }, [deliveryFiles, onDeliveryNotesUpdate]);

  // Helper function to create document from OCR result (for invoices only)
  const createDocumentFromOCR = (file: UploadedFile): Document => {
    const parsedData = file.parsedData || {};
    const timestamp = new Date().getTime().toString();
    
    // Determine status for DocumentCard
    let cardStatus: Document['status'];
    if (file.status === 'parsed') {
      // Check if this invoice has been matched with a delivery note
      // For now, we'll set all parsed invoices as 'Unmatched' since they need to be paired
      cardStatus = 'Unmatched';
    } else if (file.status === 'error' || file.status === 'parse_error') {
      cardStatus = 'Error';
    } else if (file.status === 'uploading' || file.status === 'parsing') {
      cardStatus = 'Processing';
    } else {
      cardStatus = 'Unknown';
    }
    
    // Mock matched document for demo purposes
    const mockMatchedDocument = file.documentType === 'invoice' ? {
      filename: 'delivery_note_2024_001.pdf',
      parsedData: {
        supplier_name: parsedData.supplier_name,
        delivery_note_number: 'DN-2024-001',
        delivery_date: parsedData.invoice_date,
        total_items: '3 items'
      }
    } : undefined;
    
    return {
      id: timestamp,
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
      parsedData: file.parsedData, // Pass parsedData to Document
      matchedDocument: mockMatchedDocument // Add mock matched document
    };
  };

  // Update documents when invoice files change (only show invoices in main area)
  useEffect(() => {
    const invoiceDocuments = invoiceFiles
      .filter(file => file.status === 'parsed' || file.status === 'error' || file.status === 'parse_error' || file.status === 'uploading' || file.status === 'parsing')
      .map(createDocumentFromOCR);
    
    setDocuments(invoiceDocuments);
    
    // Notify parent component of invoice updates
    if (onInvoicesUpdate) {
      onInvoicesUpdate(invoiceDocuments);
    }
  }, [invoiceFiles, onInvoicesUpdate]);

  // Unified upload handler for both invoice and delivery note uploads
  const handleUpload = async (files: File[]) => {
    // Validate number of files
    if (files.length > MAX_FILES_PER_UPLOAD) {
      showError(`Too many files. Maximum ${MAX_FILES_PER_UPLOAD} files allowed per upload.`);
      return;
    }

    // Validate each file
    const validationErrors: string[] = [];
    files.forEach(file => {
      const error = validateFile(file);
      if (error) {
        validationErrors.push(error);
      }
    });

    if (validationErrors.length > 0) {
      validationErrors.forEach(error => showError(error));
      return;
    }

    setIsUploading(true);
    
    // Helper to add file to state based on classification
    const addFileToState = (file: UploadedFile, type: 'invoices' | 'delivery' | 'unknown') => {
      if (type === 'invoices') {
        setInvoiceFiles(prev => [...prev, file]);
      } else if (type === 'delivery') {
        setDeliveryFiles(prev => [...prev, file]);
      } else {
        setUnknownFiles(prev => [...prev, file]);
      }
    };
    
    // Helper to update file status (searches in all lists)
    const updateFileStatus = (name: string, status: Partial<UploadedFile>) => {
      setInvoiceFiles(prev => prev.map(f => f.name === name ? { ...f, ...status } : f));
      setDeliveryFiles(prev => prev.map(f => f.name === name ? { ...f, ...status } : f));
      setUnknownFiles(prev => prev.map(f => f.name === name ? { ...f, ...status } : f));
    };
    
    try {
      const results = await processFilesWithConcurrency(files, addFileToState, updateFileStatus, showError, true);
      
      // Check for duplicates in results
      for (let i = 0; i < results.length; i++) {
        const result = results[i];
        if (result.type === 'duplicate') {
          // Show duplicate modal for this file
          setDuplicateInfo(result.data.duplicate_info);
          setPendingFile(files[i]);
          setPendingFileType('unknown'); // Will be determined by classification
          setDuplicateModalOpen(true);
          break; // Show modal for first duplicate found
        }
      }
      
    } catch (error) {
      showError(`Upload failed: ${error instanceof Error ? error.message : 'Unknown error'}`);
    } finally {
      setIsUploading(false);
    }
  };

  // Unified file change handler
  const handleFileChange = async (event: React.ChangeEvent<HTMLInputElement>) => {
    if (event.target.files) {
      const files = Array.from(event.target.files);
      await handleUpload(files);
      event.target.value = '';
    }
  };

  const triggerFileInput = useCallback((inputRef: React.RefObject<HTMLInputElement>) => {
    inputRef.current?.click();
  }, []);

  // Global Drag and Drop Handlers
  useEffect(() => {
    let dragCounter = 0;

    const handleDragEnter = (e: DragEvent) => {
      e.preventDefault();
      e.stopPropagation();
      dragCounter++;
      if (e.dataTransfer?.types.includes('Files') && dragCounter === 1) {
        setIsDragOver(true);
      }
    };

    const handleDragLeave = (e: DragEvent) => {
      e.preventDefault();
      e.stopPropagation();
      dragCounter--;
      if (dragCounter === 0) {
        setIsDragOver(false);
        setDragTargetArea(null);
      }
    };

    const handleDragOver = (e: DragEvent) => {
      e.preventDefault();
      e.stopPropagation();
      if (!isDragOver) return; // Ensure overlay is active

      const x = e.clientX;
      const invoiceRect = invoiceBoxRef.current?.getBoundingClientRect();
      const deliveryRect = deliveryBoxRef.current?.getBoundingClientRect();

      let targetArea: 'invoices' | 'delivery' | null = null;
      if (invoiceRect && x >= invoiceRect.left && x <= invoiceRect.right && e.clientY >= invoiceRect.top && e.clientY <= invoiceRect.bottom) {
        targetArea = 'invoices';
      } else if (deliveryRect && x >= deliveryRect.left && x <= deliveryRect.right && e.clientY >= deliveryRect.top && e.clientY <= deliveryRect.bottom) {
        targetArea = 'delivery';
      } else if (window.innerWidth >= 768) { // Only split the global overlay visually on wider screens
        if (x < window.innerWidth / 2) {
          targetArea = 'invoices';
        } else {
          targetArea = 'delivery';
        }
      }
      setDragTargetArea(targetArea);
    };

    const handleDrop = (e: DragEvent) => {
      e.preventDefault();
      e.stopPropagation();
      setIsDragOver(false);
      setDragTargetArea(null);
      dragCounter = 0;

      if (e.dataTransfer?.files && e.dataTransfer.files.length > 0) {
        const files = Array.from(e.dataTransfer.files);
        handleUpload(files);
      }
    };

    document.body.addEventListener('dragenter', handleDragEnter);
    document.body.addEventListener('dragleave', handleDragLeave);
    document.body.addEventListener('dragover', handleDragOver);
    document.body.addEventListener('drop', handleDrop);

    return () => {
      document.body.removeEventListener('dragenter', handleDragEnter);
      document.body.removeEventListener('dragleave', handleDragLeave);
      document.body.removeEventListener('dragover', handleDragOver);
      document.body.removeEventListener('drop', handleDrop);
    };
  }, [isDragOver]); // Re-run effect if isDragOver state changes

  // Handle duplicate modal actions
  const handleDuplicateConfirm = () => {
    if (pendingFile) {
      // Continue with upload - process the file normally without duplicate check
      const addFileToState = (file: UploadedFile, type: 'invoices' | 'delivery' | 'unknown') => {
        if (type === 'invoices') {
          setInvoiceFiles(prev => [...prev, file]);
        } else if (type === 'delivery') {
          setDeliveryFiles(prev => [...prev, file]);
        } else {
          setUnknownFiles(prev => [...prev, file]);
        }
      };
      
      const updateFileStatus = (name: string, status: Partial<UploadedFile>) => {
        setInvoiceFiles(prev => prev.map(f => f.name === name ? { ...f, ...status } : f));
        setDeliveryFiles(prev => prev.map(f => f.name === name ? { ...f, ...status } : f));
        setUnknownFiles(prev => prev.map(f => f.name === name ? { ...f, ...status } : f));
      };
      
      processFilesWithConcurrency([pendingFile], addFileToState, updateFileStatus, showError, false);
    }
    setDuplicateModalOpen(false);
    setDuplicateInfo(null);
    setPendingFile(null);
    setPendingFileType('unknown');
  };

  const handleDuplicateReject = () => {
    // Remove the file - don't process it
    setDuplicateModalOpen(false);
    setDuplicateInfo(null);
    setPendingFile(null);
    setPendingFileType('unknown');
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
      className={`
        owlin-glass-box
        relative
        bg-white/95 backdrop-blur-xl border-2 border-dashed border-slate-400/40
        rounded-2xl shadow-md p-8 sm:p-10 min-h-48 sm:min-h-56
        flex flex-col items-center justify-center text-center
        transition-all duration-300 ease-in-out
        hover:border-blue-600/60 hover:shadow-xl hover:-translate-y-0.5
        group
        focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-opacity-75
        ${isUploading ? 'opacity-75 cursor-not-allowed' : ''}
      `}
      role="button"
      tabIndex={0}
      onClick={() => !isUploading && triggerFileInput(inputRef)}
      onKeyDown={(e) => !isUploading && e.key === 'Enter' && triggerFileInput(inputRef)}
      title={tooltip}
    >
      {icon}
      <h3 className="text-xl font-semibold text-slate-900 mb-2 mt-2">{title}</h3>
      <p className="text-sm text-slate-600 mb-6">PDF, PNG, JPG, JPEG — Max 10MB per file</p>
      <p className="text-xs text-slate-500 mb-4 italic">Owlin will auto-classify documents</p>
      <button
        className={`
          owlin-browse-btn
          bg-blue-600 text-white border-none py-3 px-6 rounded-lg
          text-sm font-medium cursor-pointer shadow-md
          transition-all duration-200 ease-in-out
          hover:bg-blue-700 hover:-translate-y-px hover:shadow-lg
          focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-opacity-75
          flex items-center gap-2
          ${isUploading ? 'opacity-50 cursor-not-allowed' : ''}
        `}
        onClick={(e) => { 
          e.stopPropagation(); 
          if (!isUploading) triggerFileInput(inputRef); 
        }}
        aria-label={ariaLabel}
        disabled={isUploading}
      >
        {isUploading && <ProgressCircle duration={5000} color="#2563eb" size={16} />}
        {isUploading ? 'Uploading...' : 'Browse Files'}
      </button>
      <input
        type="file"
        ref={inputRef}
        onChange={onFileChange}
        className="stFileUploader hidden" // Hide the default file input
        accept={accept}
        multiple={multiple}
        aria-hidden="true" // Hide from screen readers, as we have a visible button
        tabIndex={-1} // Prevent tabbing to hidden input
        disabled={isUploading}
      />
    </div>
  );

  const FileStatusIcon = ({ status, confidence }: { status: UploadedFile['status'], confidence?: number }) => {
    switch (status) {
      case 'uploading':
        return <ProgressCircle duration={3000} size={20} color="#2563eb" />;
      case 'success':
        return <span className="text-green-600">✓</span>;
      case 'parsing':
        return <ProgressCircle duration={5000} size={20} color="#f59e42" />;
      case 'parsed':
        return confidence && confidence < 60 ? (
          <span className="text-orange-600" title={`Low confidence: ${confidence}%`}>⚠</span>
        ) : (
          <span className="text-green-600">✓</span>
        );
      case 'parse_error':
        return <span className="text-orange-600">⚠</span>;
      case 'error':
        return <span className="text-red-600">✗</span>;
      case 'duplicate_detected':
        return <span className="text-yellow-600">⚠</span>; // Indicate duplicate
      default:
        return null;
    }
  };

  return (
    <div className="p-8"> {/* Overall page padding */}
      {/* Error Notification */}
      {errorMessage && (
        <div className="fixed top-4 right-4 z-50 bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded shadow-lg max-w-md">
          <div className="flex items-center justify-between">
            <div className="flex items-center">
              <span className="text-red-500 mr-2">⚠</span>
              <span className="text-sm">{errorMessage}</span>
            </div>
            <button
              onClick={() => setErrorMessage(null)}
              className="text-red-500 hover:text-red-700 ml-4"
            >
              ×
            </button>
          </div>
        </div>
      )}

      {/* Duplicate Check Modal */}
      {duplicateInfo && (
        <DuplicateCheckModal
          isOpen={duplicateModalOpen}
          onClose={() => setDuplicateModalOpen(false)}
          onConfirm={handleDuplicateConfirm}
          onReject={handleDuplicateReject}
          newDocument={{
            filename: pendingFile?.name || '',
            parsed_data: duplicateInfo.parsed_data || {},
            document_type: duplicateInfo.document_type || 'unknown',
            confidence_score: duplicateInfo.confidence_score || 0
          }}
          duplicateInfo={duplicateInfo}
        />
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

      {/* Document Cards */}
      {documents.length > 0 && (
        <div className="mt-8">
          <h2 className="text-xl font-semibold text-slate-900 mb-4">📄 Processed Invoices ({documents.length})</h2>
          <div className="max-h-96 overflow-y-auto pr-2 scrollbar-thin scrollbar-thumb-gray-300 scrollbar-track-gray-100">
            <div className="space-y-3">
              {documents.map((doc) => (
                <DocumentCard
                  key={doc.id}
                  supplier={doc.supplier}
                  invoiceId={doc.invoiceNumber}
                  invoiceDate={doc.invoiceDate}
                  totalAmount={doc.totalAmount}
                  status={doc.status}
                  numIssues={doc.numIssues}
                  loadingPercent={doc.status === 'Processing' ? 75 : 100}
                  parsedData={doc.parsedData}
                  documentType={doc.type === 'Invoice' ? 'invoice' : 
                               doc.type === 'Delivery Note' ? 'delivery_note' : 'unknown'}
                  confidence={doc.confidence}
                  matchedDocument={doc.matchedDocument}
                  onCancel={handleCancelDocument}
                  documentId={doc.id}
                />
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Uploaded Files Summary */}
      {(invoiceFiles.length > 0 || deliveryFiles.length > 0 || unknownFiles.length > 0) && (
        <div className="mt-8">
          <h2 className="text-xl font-semibold text-slate-900 mb-4">📁 Uploaded Files</h2>

          {invoiceFiles.length > 0 && (
            <div className="bg-gray-50 rounded-lg p-4 mb-4">
              <h3 className="text-lg font-medium text-slate-800 mb-2">📄 Invoices ({invoiceFiles.length}):</h3>
              <ul className="list-none p-0 m-0">
                {invoiceFiles.map((file, index) => (
                  <li key={`invoice-${index}`} className="flex justify-between items-center text-sm text-slate-700 py-1 border-b border-gray-200 last:border-b-0">
                    <div className="flex items-center gap-2 flex-1 min-w-0">
                      <FileStatusIcon status={file.status} confidence={file.confidence} />
                      <span className="truncate">{file.name}</span>
                      {file.error && (
                        <span className="text-xs text-red-600 ml-2" title={file.error}>
                          Error: {file.error}
                        </span>
                      )}
                      {file.confidence && file.confidence < 60 && (
                        <span className="text-xs text-orange-600 ml-2" title={`Low confidence: ${file.confidence}%`}>
                          ⚠ Low confidence
                        </span>
                      )}
                      {file.status === 'duplicate_detected' && (
                        <span className="text-xs text-yellow-600 ml-2" title="Duplicate document detected">
                          ⚠ Duplicate
                        </span>
                      )}
                    </div>
                    <span className="text-xs text-slate-500 ml-4">{file.timestamp}</span>
                  </li>
                ))}
              </ul>
              
              {/* Show parsed data for successfully parsed files */}
              {invoiceFiles.some(f => f.status === 'parsed' && f.parsedData) && (
                <div className="mt-4 p-3 bg-green-50 rounded border border-green-200">
                  <h4 className="text-sm font-medium text-green-800 mb-2">📊 Parsed Invoice Data:</h4>
                  {invoiceFiles
                    .filter(f => f.status === 'parsed' && f.parsedData)
                    .map((file, index) => (
                      <div key={`parsed-invoice-${index}`} className="text-xs text-green-700 mb-2 last:mb-0">
                        <div className="font-medium">{file.name}:</div>
                        <div className="ml-2">
                          <div>Supplier: {file.parsedData.supplier_name}</div>
                          <div>Invoice #: {file.parsedData.invoice_number}</div>
                          <div>Amount: ${file.parsedData.total_amount} {file.parsedData.currency}</div>
                          <div>Date: {file.parsedData.invoice_date}</div>
                          {file.confidence && (
                            <div>Confidence: {file.confidence}%</div>
                          )}
                        </div>
                      </div>
                    ))}
                </div>
              )}
            </div>
          )}

          {deliveryFiles.length > 0 && (
            <div className="bg-gray-50 rounded-lg p-4 mb-4">
              <h3 className="text-lg font-medium text-slate-800 mb-2">📋 Delivery Notes ({deliveryFiles.length}):</h3>
              <ul className="list-none p-0 m-0">
                {deliveryFiles.map((file, index) => (
                  <li key={`delivery-${index}`} className="flex justify-between items-center text-sm text-slate-700 py-1 border-b border-gray-200 last:border-b-0">
                    <div className="flex items-center gap-2 flex-1 min-w-0">
                      <FileStatusIcon status={file.status} confidence={file.confidence} />
                      <span className="truncate">{file.name}</span>
                      {file.error && (
                        <span className="text-xs text-red-600 ml-2" title={file.error}>
                          Error: {file.error}
                        </span>
                      )}
                      {file.confidence && file.confidence < 60 && (
                        <span className="text-xs text-orange-600 ml-2" title={`Low confidence: ${file.confidence}%`}>
                          ⚠ Low confidence
                        </span>
                      )}
                      {file.status === 'duplicate_detected' && (
                        <span className="text-xs text-yellow-600 ml-2" title="Duplicate document detected">
                          ⚠ Duplicate
                        </span>
                      )}
                    </div>
                    <span className="text-xs text-slate-500 ml-4">{file.timestamp}</span>
                  </li>
                ))}
              </ul>
              
              {/* Show parsed data for successfully parsed files */}
              {deliveryFiles.some(f => f.status === 'parsed' && f.parsedData) && (
                <div className="mt-4 p-3 bg-blue-50 rounded border border-blue-200">
                  <h4 className="text-sm font-medium text-blue-800 mb-2">📊 Parsed Delivery Data:</h4>
                  {deliveryFiles
                    .filter(f => f.status === 'parsed' && f.parsedData)
                    .map((file, index) => (
                      <div key={`parsed-delivery-${index}`} className="text-xs text-blue-700 mb-2 last:mb-0">
                        <div className="font-medium">{file.name}:</div>
                        <div className="ml-2">
                          <div>Supplier: {file.parsedData.supplier_name}</div>
                          <div>Delivery #: {file.parsedData.delivery_note_number}</div>
                          <div>Items: {file.parsedData.total_items}</div>
                          <div>Date: {file.parsedData.delivery_date}</div>
                          {file.confidence && (
                            <div>Confidence: {file.confidence}%</div>
                          )}
                        </div>
                      </div>
                    ))}
                </div>
              )}
            </div>
          )}

          {unknownFiles.length > 0 && (
            <div className="bg-yellow-50 rounded-lg p-4 mb-4">
              <h3 className="text-lg font-medium text-slate-800 mb-2">❓ Unknown Documents ({unknownFiles.length}):</h3>
              <p className="text-sm text-slate-600 mb-2">These documents couldn't be automatically classified. Please review them manually.</p>
              <ul className="list-none p-0 m-0">
                {unknownFiles.map((file, index) => (
                  <li key={`unknown-${index}`} className="flex justify-between items-center text-sm text-slate-700 py-1 border-b border-gray-200 last:border-b-0">
                    <div className="flex items-center gap-2 flex-1 min-w-0">
                      <FileStatusIcon status={file.status} confidence={file.confidence} />
                      <span className="truncate">{file.name}</span>
                      {file.error && (
                        <span className="text-xs text-red-600 ml-2" title={file.error}>
                          Error: {file.error}
                        </span>
                      )}
                      {file.confidence && (
                        <span className="text-xs text-orange-600 ml-2" title={`Classification confidence: ${file.confidence}%`}>
                          ⚠ {file.confidence}% confidence
                        </span>
                      )}
                      {file.status === 'duplicate_detected' && (
                        <span className="text-xs text-yellow-600 ml-2" title="Duplicate document detected">
                          ⚠ Duplicate
                        </span>
                      )}
                    </div>
                    <span className="text-xs text-slate-500 ml-4">{file.timestamp}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {/* Global Drag Overlay */}
      {isDragOver && (
        <div
          id="global-drop"
          className={`
            fixed inset-0 z-50 bg-blue-100/70 backdrop-blur-sm
            flex items-center justify-center
            transition-opacity duration-300 ease-in-out
            ${isDragOver ? 'opacity-100' : 'opacity-0 pointer-events-none'}
            animate-pulse-subtle
          `}
        >
          <div className="absolute left-0 top-0 w-1/2 h-full border-r border-blue-300/50 flex flex-col items-center justify-center text-center">
            <FileTextIcon className={`w-12 h-12 text-blue-700 mb-2 ${dragTargetArea === 'invoices' ? 'scale-110' : ''} transition-transform duration-200`} />
            <span className={`text-blue-700 font-semibold text-lg ${dragTargetArea === 'invoices' ? 'scale-105' : ''} transition-transform duration-200`}>Invoices</span>
          </div>
          <div className="absolute right-0 top-0 w-1/2 h-full flex flex-col items-center justify-center text-center">
            <ClipboardListIcon className={`w-12 h-12 text-blue-700 mb-2 ${dragTargetArea === 'delivery' ? 'scale-110' : ''} transition-transform duration-200`} />
            <span className={`text-blue-700 font-semibold text-lg ${dragTargetArea === 'delivery' ? 'scale-105' : ''} transition-transform duration-200`}>Delivery Notes</span>
          </div>
        </div>
      )}

      {/* Custom CSS for pulse animation - typically in a global CSS file or <style> tag */}
      <style jsx>{`
        @keyframes pulse-subtle {
          0%, 100% { background-color: rgba(219, 234, 254, 0.7); } /* blue-100/70 */
          50% { background-color: rgba(191, 219, 254, 0.8); } /* blue-200/80 */
        }
        .animate-pulse-subtle {
          animation: pulse-subtle 3s infinite ease-in-out;
        }

        /* Specific shadow overrides for .owlin-glass-box to match requested rgba value */
        .owlin-glass-box {
            box-shadow: 0 4px 30px rgba(0, 0, 0, 0.08);
        }
        .owlin-glass-box:hover {
            box-shadow: 0 8px 40px rgba(37, 99, 235, 0.15);
        }
      `}</style>
    </div>
  );
};

export default InvoicesUploadPanel; 