import React, { useState, useRef, useEffect, useCallback } from 'react';

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

const LoadingSpinner = ({ className = 'w-4 h-4' }) => (
  <svg
    className={`animate-spin ${className}`}
    xmlns="http://www.w3.org/2000/svg"
    fill="none"
    viewBox="0 0 24 24"
  >
    <circle
      className="opacity-25"
      cx="12"
      cy="12"
      r="10"
      stroke="currentColor"
      strokeWidth="4"
    ></circle>
    <path
      className="opacity-75"
      fill="currentColor"
      d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
    ></path>
  </svg>
);

interface UploadedFile {
  name: string;
  timestamp: string;
  status: 'uploading' | 'success' | 'error' | 'parsing' | 'parsed' | 'parse_error';
  error?: string;
  serverFilename?: string;
  parsedData?: any;
}

const InvoicesUploadPanel: React.FC = () => {
  const [invoiceFiles, setInvoiceFiles] = useState<UploadedFile[]>([]);
  const [deliveryFiles, setDeliveryFiles] = useState<UploadedFile[]>([]);
  const [isDragOver, setIsDragOver] = useState(false);
  const [dragTargetArea, setDragTargetArea] = useState<'invoices' | 'delivery' | null>(null);
  const [isUploading, setIsUploading] = useState(false);

  const invoiceInputRef = useRef<HTMLInputElement>(null);
  const deliveryInputRef = useRef<HTMLInputElement>(null);
  const invoiceBoxRef = useRef<HTMLDivElement>(null);
  const deliveryBoxRef = useRef<HTMLDivElement>(null);

  // API base URL - adjust if your FastAPI server runs on a different port
  const API_BASE_URL = 'http://localhost:8000/api';

  const uploadFile = async (file: File, type: 'invoices' | 'delivery'): Promise<any> => {
    const formData = new FormData();
    formData.append('file', file);

    const endpoint = type === 'invoices' ? '/upload/invoice' : '/upload/delivery';
    
    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.detail || 'Upload failed');
    }

    return await response.json();
  };

  const parseFileWithOCR = async (file: File): Promise<any> => {
    const formData = new FormData();
    formData.append('file', file);
    
    const response = await fetch(`${API_BASE_URL}/ocr/parse`, {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.detail || 'OCR parsing failed');
    }

    return await response.json();
  };

  const handleFileChange = async (
    event: React.ChangeEvent<HTMLInputElement>,
    target: 'invoices' | 'delivery'
  ) => {
    if (event.target.files) {
      const files = Array.from(event.target.files);
      setIsUploading(true);

      for (const file of files) {
        // Add file to state with uploading status
        const newFile: UploadedFile = {
          name: file.name,
          timestamp: new Date().toLocaleString(),
          status: 'uploading'
        };

        if (target === 'invoices') {
          setInvoiceFiles(prev => [...prev, newFile]);
        } else {
          setDeliveryFiles(prev => [...prev, newFile]);
        }

        try {
          // Step 1: Upload file to backend
          const uploadResult = await uploadFile(file, target);
          
          // Update file status to success after upload
          const updateFileAfterUpload = (files: UploadedFile[]) => 
            files.map(f => 
              f.name === file.name 
                ? { ...f, status: 'success' as const, serverFilename: uploadResult.filename }
                : f
            );

          if (target === 'invoices') {
            setInvoiceFiles(updateFileAfterUpload);
          } else {
            setDeliveryFiles(updateFileAfterUpload);
          }

          // Step 2: Parse file with OCR
          const updateFileToParsing = (files: UploadedFile[]) => 
            files.map(f => 
              f.name === file.name 
                ? { ...f, status: 'parsing' as const }
                : f
            );

          if (target === 'invoices') {
            setInvoiceFiles(updateFileToParsing);
          } else {
            setDeliveryFiles(updateFileToParsing);
          }

          const parseResult = await parseFileWithOCR(file);
          
          // Update file status to parsed with OCR data
          const updateFileAfterParse = (files: UploadedFile[]) => 
            files.map(f => 
              f.name === file.name 
                ? { ...f, status: 'parsed' as const, parsedData: parseResult.parsed_data }
                : f
            );

          if (target === 'invoices') {
            setInvoiceFiles(updateFileAfterParse);
          } else {
            setDeliveryFiles(updateFileAfterParse);
          }

        } catch (error) {
          // Update file status to error
          const updateFile = (files: UploadedFile[]) => 
            files.map(f => 
              f.name === file.name 
                ? { 
                    ...f, 
                    status: (f.status === 'parsing' ? 'parse_error' : 'error') as 'parse_error' | 'error', 
                    error: error instanceof Error ? error.message : 'Processing failed' 
                  }
                : f
            );

          if (target === 'invoices') {
            setInvoiceFiles(updateFile);
          } else {
            setDeliveryFiles(updateFile);
          }
        }
      }

      setIsUploading(false);
      // Clear the input value to allow re-uploading the same file
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
        const files = e.dataTransfer.files;
        const x = e.clientX;

        let targetInputRef: React.RefObject<HTMLInputElement> | null = null;
        const invoiceRect = invoiceBoxRef.current?.getBoundingClientRect();
        const deliveryRect = deliveryBoxRef.current?.getBoundingClientRect();

        if (invoiceRect && x >= invoiceRect.left && x <= invoiceRect.right && e.clientY >= invoiceRect.top && e.clientY <= invoiceRect.bottom) {
          targetInputRef = invoiceInputRef;
        } else if (deliveryRect && x >= deliveryRect.left && x <= deliveryRect.right && e.clientY >= deliveryRect.top && e.clientY <= deliveryRect.bottom) {
          targetInputRef = deliveryInputRef;
        } else if (window.innerWidth >= 768) { // Fallback to horizontal split for global drop
          if (x < window.innerWidth / 2) {
            targetInputRef = invoiceInputRef;
          } else {
            targetInputRef = deliveryInputRef;
          }
        } else { // On mobile, if dropped anywhere, assume invoices
            targetInputRef = invoiceInputRef;
        }


        if (targetInputRef?.current) {
          const dataTransfer = new DataTransfer();
          Array.from(files).forEach(file => dataTransfer.items.add(file));
          targetInputRef.current.files = dataTransfer.files;
          targetInputRef.current.dispatchEvent(new Event('change', { bubbles: true }));
        }
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
  }> = ({ title, icon, inputRef, boxRef, onFileChange, ariaLabel, accept, multiple, isUploading = false }) => (
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
    >
      {icon}
      <h3 className="text-xl font-semibold text-slate-900 mb-2 mt-2">{title}</h3>
      <p className="text-sm text-slate-600 mb-6">PDF, PNG, JPG, JPEG — Max 10MB per file</p>
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
        {isUploading && <LoadingSpinner className="w-4 h-4" />}
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

  const FileStatusIcon = ({ status }: { status: UploadedFile['status'] }) => {
    switch (status) {
      case 'uploading':
        return <LoadingSpinner className="w-4 h-4 text-blue-600" />;
      case 'success':
        return <span className="text-green-600">✓</span>;
      case 'parsing':
        return <LoadingSpinner className="w-4 h-4 text-yellow-600" />;
      case 'parsed':
        return <span className="text-green-600">🔍</span>;
      case 'parse_error':
        return <span className="text-orange-600">⚠</span>;
      case 'error':
        return <span className="text-red-600">✗</span>;
      default:
        return null;
    }
  };

  return (
    <div className="p-8"> {/* Overall page padding */}
      {/* Upload Boxes */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
        <GlassBox
          title="Upload Invoices"
          icon={<FileTextIcon className="w-8 h-8 sm:w-10 sm:h-10 text-slate-600 mb-4" />}
          inputRef={invoiceInputRef}
          boxRef={invoiceBoxRef}
          onFileChange={(e) => handleFileChange(e, 'invoices')}
          ariaLabel="Browse files to upload invoices"
          accept=".pdf,.jpg,.jpeg,.png"
          multiple={true}
          isUploading={isUploading}
        />
        <GlassBox
          title="Upload Delivery Notes"
          icon={<ClipboardListIcon className="w-8 h-8 sm:w-10 sm:h-10 text-slate-600 mb-4" />}
          inputRef={deliveryInputRef}
          boxRef={deliveryBoxRef}
          onFileChange={(e) => handleFileChange(e, 'delivery')}
          ariaLabel="Browse files to upload delivery notes"
          accept=".pdf,.jpg,.jpeg,.png"
          multiple={true}
          isUploading={isUploading}
        />
      </div>

      {/* Uploaded Files Summary */}
      {(invoiceFiles.length > 0 || deliveryFiles.length > 0) && (
        <div className="mt-8">
          <h2 className="text-xl font-semibold text-slate-900 mb-4">📁 Uploaded Files</h2>

          {invoiceFiles.length > 0 && (
            <div className="bg-gray-50 rounded-lg p-4 mb-4">
              <h3 className="text-lg font-medium text-slate-800 mb-2">📄 Invoices:</h3>
              <ul className="list-none p-0 m-0">
                {invoiceFiles.map((file, index) => (
                  <li key={`invoice-${index}`} className="flex justify-between items-center text-sm text-slate-700 py-1 border-b border-gray-200 last:border-b-0">
                    <div className="flex items-center gap-2 flex-1 min-w-0">
                      <FileStatusIcon status={file.status} />
                      <span className="truncate">{file.name}</span>
                      {file.error && (
                        <span className="text-xs text-red-600 ml-2" title={file.error}>
                          Error: {file.error}
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
                        </div>
                      </div>
                    ))}
                </div>
              )}
            </div>
          )}

          {deliveryFiles.length > 0 && (
            <div className="bg-gray-50 rounded-lg p-4">
              <h3 className="text-lg font-medium text-slate-800 mb-2">📋 Delivery Notes:</h3>
              <ul className="list-none p-0 m-0">
                {deliveryFiles.map((file, index) => (
                  <li key={`delivery-${index}`} className="flex justify-between items-center text-sm text-slate-700 py-1 border-b border-gray-200 last:border-b-0">
                    <div className="flex items-center gap-2 flex-1 min-w-0">
                      <FileStatusIcon status={file.status} />
                      <span className="truncate">{file.name}</span>
                      {file.error && (
                        <span className="text-xs text-red-600 ml-2" title={file.error}>
                          Error: {file.error}
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
                        </div>
                      </div>
                    ))}
                </div>
              )}
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