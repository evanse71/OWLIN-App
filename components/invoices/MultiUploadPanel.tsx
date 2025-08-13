import React, { useState, useRef, useCallback } from 'react';

// Inlined UI components for demo purposes
const Card = ({ children, className = "" }: { children: React.ReactNode; className?: string }) => (
  <div className={`bg-white rounded-lg shadow-md p-6 border ${className}`}>
    {children}
  </div>
);

const Button = ({ 
  children, 
  onClick, 
  disabled = false, 
  variant = "primary",
  size = "md",
  className = "" 
}: { 
  children: React.ReactNode; 
  onClick?: () => void; 
  disabled?: boolean;
  variant?: "primary" | "secondary" | "danger";
  size?: "sm" | "md" | "lg";
  className?: string;
}) => {
  const baseClasses = "rounded-md font-medium transition-colors";
  const variantClasses = {
    primary: "bg-blue-600 text-white hover:bg-blue-700 disabled:bg-gray-400",
    secondary: "bg-gray-200 text-gray-800 hover:bg-gray-300 disabled:bg-gray-100",
    danger: "bg-red-600 text-white hover:bg-red-700 disabled:bg-red-400"
  };
  const sizeClasses = {
    sm: "px-2 py-1 text-sm",
    md: "px-4 py-2",
    lg: "px-6 py-3 text-lg"
  };
  
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className={`${baseClasses} ${variantClasses[variant]} ${sizeClasses[size]} ${className}`}
    >
      {children}
    </button>
  );
};

const Progress = ({ value, max = 100, className = "" }: { value: number; max?: number; className?: string }) => (
  <div className={`w-full bg-gray-200 rounded-full h-2 ${className}`}>
    <div 
      className="bg-blue-600 h-2 rounded-full transition-all duration-300"
      style={{ width: `${(value / max) * 100}%` }}
    />
  </div>
);

const Badge = ({ children, variant = "default", className = "" }: { 
  children: React.ReactNode; 
  variant?: "success" | "warning" | "error" | "info" | "default";
  className?: string;
}) => {
  const variantClasses = {
    success: "bg-green-100 text-green-800",
    warning: "bg-yellow-100 text-yellow-800",
    error: "bg-red-100 text-red-800",
    info: "bg-blue-100 text-blue-800",
    default: "bg-gray-100 text-gray-800"
  };
  
  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${variantClasses[variant]} ${className}`}>
      {children}
    </span>
  );
};

const Alert = ({ 
  children, 
  variant = "info",
  className = "" 
}: { 
  children: React.ReactNode; 
  variant?: "success" | "warning" | "error" | "info";
  className?: string;
}) => {
  const variantClasses = {
    success: "bg-green-50 border-green-200 text-green-800",
    warning: "bg-yellow-50 border-yellow-200 text-yellow-800",
    error: "bg-red-50 border-red-200 text-red-800",
    info: "bg-blue-50 border-blue-200 text-blue-800"
  };
  
  return (
    <div className={`border rounded-md p-4 ${variantClasses[variant]} ${className}`}>
      {children}
    </div>
  );
};

// Icons
const UploadIcon = () => (
  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
  </svg>
);

const CheckIcon = () => (
  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
  </svg>
);

const WarningIcon = () => (
  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.732 16.5c-.77.833.192 2.5 1.732 2.5z" />
  </svg>
);

const ErrorIcon = () => (
  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
  </svg>
);

const FileIcon = () => (
  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
  </svg>
);

const SpinnerIcon = () => (
  <svg className="w-4 h-4 animate-spin" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
  </svg>
);

interface FileUpload {
  file: File;
  id: string;
  status: 'pending' | 'processing' | 'success' | 'error' | 'warning';
  progress: number;
  message: string;
  validation?: any;
  processing?: any;
}

interface MultiUploadPanelProps {
  userRole?: 'viewer' | 'finance' | 'admin';
  onUploadComplete?: (results: FileUpload[]) => void;
  maxFileSize?: number; // in MB
  maxFiles?: number;
  supportedFormats?: string[];
}

const MultiUploadPanel: React.FC<MultiUploadPanelProps> = ({
  userRole = 'viewer',
  onUploadComplete,
  maxFileSize = 50,
  maxFiles = 10,
  supportedFormats = ['pdf', 'jpg', 'jpeg', 'png', 'tiff']
}) => {
  const [uploads, setUploads] = useState<FileUpload[]>([]);
  const [isUploading, setIsUploading] = useState(false);
  const [overallProgress, setOverallProgress] = useState(0);
  const [dragActive, setDragActive] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Mock API call for demonstration
  const processFile = useCallback(async (file: File): Promise<any> => {
    // Simulate API call delay
    await new Promise(resolve => setTimeout(resolve, 1000 + Math.random() * 2000));
    
    // Mock response based on file type and size
    const fileSizeMB = file.size / (1024 * 1024);
    const isLargeFile = fileSizeMB > 10;
    const hasError = Math.random() < 0.1; // 10% chance of error
    const hasWarning = Math.random() < 0.2; // 20% chance of warning
    
    if (hasError) {
      throw new Error('Processing failed: OCR could not extract text from this file');
    }
    
    return {
      success: true,
      validation: {
        allowed: !hasWarning,
        messages: {
          name: `Invoice – ${file.name.replace(/\.[^/.]+$/, '')} – ${new Date().toLocaleDateString()}`,
          ...(hasWarning && { warning: 'Invoice number already exists in database' })
        },
        validation_data: {
          file_size: file.size,
          mime_type: file.type,
          duplicate_invoice: hasWarning,
          duplicate_file: false,
          suggested_name: `Invoice – ${file.name.replace(/\.[^/.]+$/, '')} – ${new Date().toLocaleDateString()}`
        },
        summary: {
          file_info: {
            name: file.name,
            size_mb: fileSizeMB,
            mime_type: file.type
          },
          extracted_info: {
            supplier: 'ACME Corporation Ltd',
            invoice_number: `INV-${Date.now()}`,
            date: new Date().toLocaleDateString()
          },
          validation_results: {
            duplicate_invoice: hasWarning,
            duplicate_file: false,
            suggested_name: `Invoice – ${file.name.replace(/\.[^/.]+$/, '')} – ${new Date().toLocaleDateString()}`
          }
        }
      },
      processing_results: {
        ocr_results: [],
        confidence_scores: [0.85, 0.92, 0.78],
        document_type: 'invoice',
        processing_time: 1.5 + Math.random(),
        pages_processed: 1,
        overall_confidence: 0.85
      }
    };
  }, []);

  const validateFile = useCallback((file: File): string | null => {
    // Check file size
    const fileSizeMB = file.size / (1024 * 1024);
    if (fileSizeMB > maxFileSize) {
      return `File size (${fileSizeMB.toFixed(1)}MB) exceeds maximum allowed size (${maxFileSize}MB)`;
    }

    // Check file type
    const extension = file.name.split('.').pop()?.toLowerCase();
    if (!extension || !supportedFormats.includes(extension)) {
      return `Unsupported file type. Supported formats: ${supportedFormats.join(', ')}`;
    }

    return null;
  }, [maxFileSize, supportedFormats]);

  const handleFileSelect = useCallback((files: FileList) => {
    const newUploads: FileUpload[] = Array.from(files).map(file => ({
      file,
      id: `${file.name}-${Date.now()}-${Math.random()}`,
      status: 'pending' as const,
      progress: 0,
      message: 'File selected'
    }));

    setUploads(prev => [...prev, ...newUploads]);
  }, []);

  const handleDrag = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFileSelect(e.dataTransfer.files);
    }
  }, [handleFileSelect]);

  const processUploads = useCallback(async () => {
    if (uploads.length === 0) return;

    setIsUploading(true);
    setOverallProgress(0);

    const pendingUploads = uploads.filter(upload => upload.status === 'pending');
    let completedCount = 0;

    for (const upload of pendingUploads) {
      // Update status to processing
      setUploads(prev => prev.map(u => 
        u.id === upload.id 
          ? { ...u, status: 'processing', message: 'Processing file...', progress: 0 }
          : u
      ));

      try {
        // Validate file
        const validationError = validateFile(upload.file);
        if (validationError) {
          setUploads(prev => prev.map(u => 
            u.id === upload.id 
              ? { ...u, status: 'error', message: validationError, progress: 100 }
              : u
          ));
          completedCount++;
          setOverallProgress((completedCount / pendingUploads.length) * 100);
          continue;
        }

        // Simulate processing steps
        const steps = [
          { message: 'Uploading file...', progress: 20 },
          { message: 'Running OCR...', progress: 40 },
          { message: 'Extracting fields...', progress: 60 },
          { message: 'Validating data...', progress: 80 },
          { message: 'Finalizing...', progress: 100 }
        ];

        for (const step of steps) {
          await new Promise(resolve => setTimeout(resolve, 200 + Math.random() * 300));
          setUploads(prev => prev.map(u => 
            u.id === upload.id 
              ? { ...u, message: step.message, progress: step.progress }
              : u
          ));
        }

        // Process file
        const result = await processFile(upload.file);
        
        // Determine final status
        let status: 'success' | 'warning' = 'success';
        if (result.validation.messages.warning) {
          status = 'warning';
        }

        setUploads(prev => prev.map(u => 
          u.id === upload.id 
            ? { 
                ...u, 
                status, 
                message: result.validation.messages.name,
                progress: 100,
                validation: result.validation,
                processing: result.processing_results
              }
            : u
        ));

      } catch (error) {
        setUploads(prev => prev.map(u => 
          u.id === upload.id 
            ? { ...u, status: 'error', message: error instanceof Error ? error.message : 'Processing failed', progress: 100 }
            : u
        ));
      }

      completedCount++;
      setOverallProgress((completedCount / pendingUploads.length) * 100);
    }

    setIsUploading(false);
    
    // Call completion callback
    if (onUploadComplete) {
      onUploadComplete(uploads);
    }
  }, [uploads, validateFile, processFile, onUploadComplete]);

  const removeUpload = useCallback((id: string) => {
    setUploads(prev => prev.filter(upload => upload.id !== id));
  }, []);

  const clearCompleted = useCallback(() => {
    setUploads(prev => prev.filter(upload => upload.status === 'pending'));
  }, []);

  const getStatusIcon = (status: FileUpload['status']) => {
    switch (status) {
      case 'success':
        return <CheckIcon />;
      case 'warning':
        return <WarningIcon />;
      case 'error':
        return <ErrorIcon />;
      case 'processing':
        return <SpinnerIcon />;
      default:
        return <FileIcon />;
    }
  };

  const getStatusColor = (status: FileUpload['status']) => {
    switch (status) {
      case 'success':
        return 'text-green-600';
      case 'warning':
        return 'text-yellow-600';
      case 'error':
        return 'text-red-600';
      case 'processing':
        return 'text-blue-600';
      default:
        return 'text-gray-600';
    }
  };

  const getStatusBadge = (status: FileUpload['status']) => {
    switch (status) {
      case 'success':
        return <Badge variant="success">Success</Badge>;
      case 'warning':
        return <Badge variant="warning">Warning</Badge>;
      case 'error':
        return <Badge variant="error">Error</Badge>;
      case 'processing':
        return <Badge variant="info">Processing</Badge>;
      default:
        return <Badge variant="default">Pending</Badge>;
    }
  };

  const pendingCount = uploads.filter(u => u.status === 'pending').length;
  const processingCount = uploads.filter(u => u.status === 'processing').length;
  const successCount = uploads.filter(u => u.status === 'success').length;
  const warningCount = uploads.filter(u => u.status === 'warning').length;
  const errorCount = uploads.filter(u => u.status === 'error').length;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">Multi-File Upload</h2>
          <p className="text-gray-600 mt-1">
            Upload multiple invoice files for batch processing. Supported formats: {supportedFormats.join(', ')} (max {maxFileSize}MB each)
          </p>
        </div>
        <div className="flex items-center space-x-2">
          {userRole === 'admin' && (
            <Button variant="secondary" onClick={clearCompleted} disabled={successCount + warningCount + errorCount === 0}>
              Clear Completed
            </Button>
          )}
          <Button 
            onClick={() => fileInputRef.current?.click()}
            disabled={isUploading}
          >
            <UploadIcon />
            <span className="ml-2">Select Files</span>
          </Button>
        </div>
      </div>

      {/* File Input */}
      <input
        ref={fileInputRef}
        type="file"
        multiple
        accept={supportedFormats.map(f => `.${f}`).join(',')}
        onChange={(e) => e.target.files && handleFileSelect(e.target.files)}
        className="hidden"
      />

      {/* Drag and Drop Area */}
      <div
        className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors ${
          dragActive ? 'border-blue-400 bg-blue-50' : 'border-gray-300 hover:border-gray-400'
        }`}
        onDragEnter={handleDrag}
        onDragLeave={handleDrag}
        onDragOver={handleDrag}
        onDrop={handleDrop}
      >
        <UploadIcon />
        <h3 className="mt-2 text-sm font-medium text-gray-900">Drop files here</h3>
        <p className="mt-1 text-xs text-gray-500">
          or click to select files
        </p>
      </div>

      {/* Upload Progress */}
      {isUploading && (
        <Card>
          <div className="flex items-center justify-between mb-2">
            <h3 className="text-lg font-medium">Processing Files</h3>
            <span className="text-sm text-gray-500">
              {processingCount} processing • {successCount} completed • {errorCount} failed
            </span>
          </div>
          <Progress value={overallProgress} className="mb-2" />
          <p className="text-sm text-gray-600">
            Overall progress: {Math.round(overallProgress)}%
          </p>
        </Card>
      )}

      {/* File List */}
      {uploads.length > 0 && (
        <Card>
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-medium">Upload Queue</h3>
            <div className="flex items-center space-x-4 text-sm">
              <span className="text-gray-500">
                {pendingCount} pending • {processingCount} processing • {successCount} success • {warningCount} warning • {errorCount} error
              </span>
              {pendingCount > 0 && !isUploading && (
                <Button onClick={processUploads} disabled={isUploading}>
                  Process {pendingCount} Files
                </Button>
              )}
            </div>
          </div>

          <div className="space-y-3">
            {uploads.map((upload) => (
              <div key={upload.id} className="border rounded-lg p-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-3">
                    <div className={getStatusColor(upload.status)}>
                      {getStatusIcon(upload.status)}
                    </div>
                    <div className="flex-1">
                      <div className="flex items-center space-x-2">
                        <span className="font-medium text-gray-900">{upload.file.name}</span>
                        {getStatusBadge(upload.status)}
                      </div>
                      <p className="text-sm text-gray-600 mt-1">{upload.message}</p>
                      {upload.status === 'processing' && (
                        <Progress value={upload.progress} className="mt-2" />
                      )}
                    </div>
                  </div>
                  <div className="flex items-center space-x-2">
                    {(upload.status === 'success' || upload.status === 'warning') && upload.validation && (
                      <Button variant="secondary" size="sm">
                        View Details
                      </Button>
                    )}
                    {upload.status === 'pending' && (
                      <Button 
                        variant="danger" 
                        size="sm"
                        onClick={() => removeUpload(upload.id)}
                      >
                        Remove
                      </Button>
                    )}
                  </div>
                </div>

                {/* Validation Details */}
                {upload.validation && (upload.status === 'success' || upload.status === 'warning') && (
                  <div className="mt-3 pt-3 border-t">
                    <div className="grid grid-cols-2 gap-4 text-sm">
                      <div>
                        <span className="font-medium">File Size:</span> {(upload.file.size / (1024 * 1024)).toFixed(1)}MB
                      </div>
                      <div>
                        <span className="font-medium">Type:</span> {upload.validation.validation_data.mime_type}
                      </div>
                      <div>
                        <span className="font-medium">Supplier:</span> {upload.validation.summary.extracted_info.supplier}
                      </div>
                      <div>
                        <span className="font-medium">Invoice #:</span> {upload.validation.summary.extracted_info.invoice_number}
                      </div>
                    </div>
                    {upload.validation.messages.warning && (
                      <Alert variant="warning" className="mt-2">
                        <WarningIcon />
                        <span className="ml-2">{upload.validation.messages.warning}</span>
                      </Alert>
                    )}
                  </div>
                )}

                {/* Error Details */}
                {upload.status === 'error' && (
                  <Alert variant="error" className="mt-3">
                    <ErrorIcon />
                    <span className="ml-2">{upload.message}</span>
                  </Alert>
                )}
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* Summary */}
      {(successCount > 0 || warningCount > 0 || errorCount > 0) && !isUploading && (
        <Card>
          <h3 className="text-lg font-medium mb-3">Upload Summary</h3>
          <div className="grid grid-cols-4 gap-4 text-center">
            <div>
              <div className="text-2xl font-bold text-green-600">{successCount}</div>
              <div className="text-sm text-gray-600">Successful</div>
            </div>
            <div>
              <div className="text-2xl font-bold text-yellow-600">{warningCount}</div>
              <div className="text-sm text-gray-600">Warnings</div>
            </div>
            <div>
              <div className="text-2xl font-bold text-red-600">{errorCount}</div>
              <div className="text-sm text-gray-600">Errors</div>
            </div>
            <div>
              <div className="text-2xl font-bold text-gray-600">{uploads.length}</div>
              <div className="text-sm text-gray-600">Total</div>
            </div>
          </div>
        </Card>
      )}
    </div>
  );
};

export default MultiUploadPanel; 