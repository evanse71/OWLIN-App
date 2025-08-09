import React, { useState, useRef } from 'react';
import { apiService } from '@/services/api';
import { useToast } from '@/utils/toast';
import SmartDocumentReviewModal from '@/components/document-queue/SmartDocumentReviewModal';
import ConfidenceBadge from '@/components/common/ConfidenceBadge';

interface DocumentUploadResult {
  id: string;
  type: 'invoice' | 'delivery_note' | 'receipt' | 'utility' | 'unknown';
  confidence: number;
  supplier_name: string;
  pages: number[];
  preview_urls: string[];
  metadata: {
    invoice_date?: string;
    delivery_date?: string;
    total_amount?: number;
    invoice_number?: string;
    delivery_note_number?: string;
  };
  status: 'scanning' | 'processed' | 'error' | 'manual_review';
  originalFile: File;
  page_range?: string; // Page range for multi-invoice PDFs
  // ✅ New OCR debug properties
  word_count?: number;
  psm_used?: string; // Changed from number to string for PaddleOCR
  was_retried?: boolean;
  raw_ocr_text?: string;
  ocr_pages?: Array<{
    page: number;
    text: string;
    avg_confidence: number;
    word_count: number;
    psm_used?: number;
  }>;
}

interface UploadSectionProps {
  onDocumentsSubmitted?: (documents: DocumentUploadResult[]) => void;
}

const UploadSection: React.FC<UploadSectionProps> = ({ onDocumentsSubmitted }) => {
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState<{ [key: string]: number }>({});
  const [pendingUploads, setPendingUploads] = useState<DocumentUploadResult[]>([]);
  const [showReviewModal, setShowReviewModal] = useState(false);
  const [currentFile, setCurrentFile] = useState<File | null>(null);
  const [showLowConfidenceOnly, setShowLowConfidenceOnly] = useState(false);
  
  const fileInputRef = useRef<HTMLInputElement>(null);
  const { showToast } = useToast();

  // ✅ Smart Filtering for Low-Confidence Docs (only for preview cards)
  const filteredDocuments = pendingUploads.filter(doc => {
    if (showLowConfidenceOnly && doc.status === 'processed') {
      return doc.confidence < 70;
    }
    return true;
  });

  // ✅ Get count of processed documents for submit button
  const processedCount = pendingUploads.filter(doc => doc.status === 'processed').length;

  // Helper function to create a timeout promise
  const createTimeoutPromise = (timeoutMs: number) => {
    return new Promise((_, reject) => {
      setTimeout(() => {
        reject(new Error(`Request timed out after ${timeoutMs / 1000} seconds`));
      }, timeoutMs);
    });
  };

  // Enhanced progress tracking with specific stages
  const updateProgress = (file: string, progress: number, stage: string) => {
    setUploadProgress(prev => ({ ...prev, [file]: progress }));
    setPendingUploads(prev => prev.map(doc => 
      doc.originalFile.name === file 
        ? { ...doc, supplier_name: `${stage}...` }
        : doc
    ));
  };

  // File validation with helpful messages
  const validateFile = (file: File) => {
    const allowedTypes = ["application/pdf", "image/jpeg", "image/png"];
    if (!allowedTypes.includes(file.type)) {
      throw new Error("Please upload PDF, JPEG, or PNG files only");
    }
    if (file.size > 50 * 1024 * 1024) {
      throw new Error("File size must be less than 50MB");
    }
  };

  // Upload with retry logic
  const uploadWithRetry = async (file: File, maxRetries = 3) => {
    for (let attempt = 1; attempt <= maxRetries; attempt++) {
      try {
        return await apiService.uploadInvoice(file);
      } catch (error) {
        if (attempt === maxRetries) throw error;
        console.log(`Retry attempt ${attempt} for ${file.name}`);
        await new Promise(resolve => setTimeout(resolve, 1000 * attempt));
      }
    }
  };
  const handleFileUpload = async (file: File) => {
    if (!file) return;

    console.log(`🚀 Starting upload for file: ${file.name} (${file.size} bytes)`);
    
    setIsUploading(true);
    setCurrentFile(file);
    updateProgress(file.name, 0, "Starting");

    // ✅ Create small preview card (ChatGPT-style)
    const tempDocId = crypto.randomUUID();
    const tempCard: DocumentUploadResult = {
      id: tempDocId,
      type: 'unknown',
      confidence: 0,
      supplier_name: file.name, // Show filename instead of "Scanning document..."
      pages: [],
      preview_urls: [],
      metadata: {
        invoice_number: 'Processing...',
        total_amount: undefined,
        invoice_date: undefined
      },
      status: 'scanning',
      originalFile: file
    };

    // ✅ Add small preview card
    setPendingUploads(prev => [...prev, tempCard]);

    let progressInterval: NodeJS.Timeout | null = null;
    let timeoutId: NodeJS.Timeout | null = null;

    try {
      // ✅ Simulate progress up to 90%
      progressInterval = setInterval(() => {
        setUploadProgress(prev => {
          const current = prev[file.name] || 0;
          if (current >= 90) {
            if (progressInterval) {
              clearInterval(progressInterval);
              progressInterval = null;
            }
            return prev;
          }
          return { ...prev, [file.name]: current + 10 };
        });
      }, 200);

      // Set up 90-second timeout (increased from 30s for PaddleOCR)
      timeoutId = setTimeout(() => {
        console.error(`⏰ Upload timeout for ${file.name} after 90 seconds`);
        throw new Error('Upload timed out after 90 seconds');
      }, 45000);

      // Try direct upload first
      let response: any;
      try {
        updateProgress(file.name, 10, "Validating");
        validateFile(file);
        updateProgress(file.name, 30, "Converting");
        console.log(`📤 Attempting direct upload for ${file.name}...`);
        updateProgress(file.name, 60, "OCR Processing");
        
        // Check if LLM is enabled
        const privacySettings = localStorage.getItem('privacy_settings');
        const useLocalAI = privacySettings ? JSON.parse(privacySettings).useLocalAI : true;
        
        if (useLocalAI) {
          updateProgress(file.name, 70, "Parsing with Local AI...");
        }
        
        response = await Promise.race([
          apiService.uploadInvoice(file),
          createTimeoutPromise(300000) // Increased timeout to 5 minutes for large files
        ]);
        
        console.log(`✅ Direct upload successful for ${file.name}:`, response);
        updateProgress(file.name, 90, "Finalizing");
        
        // ✅ Handle multi-invoice PDF response
        if (Array.isArray(response.saved_invoices) && response.saved_invoices.length >= 1) {
          console.log(`📄 Multi-invoice PDF detected! Processing ${response.saved_invoices.length} invoices`);
          
          // Convert each invoice to DocumentUploadResult format
          const processedDocs: DocumentUploadResult[] = response.saved_invoices.map((invoice: any, index: number) => ({
            id: invoice.invoice_id || `invoice-${Date.now()}-${index}`,
            type: 'invoice',
            confidence: Math.round(invoice.confidence || 0),
            supplier_name: invoice.supplier_name || 'Unknown Supplier',
            pages: invoice.page_numbers || [1],
            preview_urls: [],
            metadata: {
              invoice_number: invoice.metadata?.invoice_number || 'Unknown',
              total_amount: invoice.metadata?.total_amount || 0,
              invoice_date: invoice.metadata?.invoice_date || new Date().toISOString().split('T')[0]
            },
            status: 'processed',
            originalFile: file,
            // Add page range for display
            page_range: invoice.page_range,
            // ✅ Add OCR debug data
            word_count: response.word_count,
            psm_used: response.psm_used,
            was_retried: response.was_retried,
            raw_ocr_text: response.raw_ocr_text,
            ocr_pages: response.pages
          }));

          // ✅ Replace temp card with multiple processed results
          setPendingUploads(prev => {
            const filtered = prev.filter(doc => doc.id !== tempCard.id);
            return [...filtered, ...processedDocs];
          });

          showToast('success', `Successfully processed ${response.saved_invoices.length} invoices from ${file.name}`);
          updateProgress(file.name, 100, 'Complete');
        } else {
          // ✅ Force single-invoice behavior
          const pd = response.parsed_data || response.data || {};
          const processedDoc: DocumentUploadResult = {
            id: response.invoice_id || tempDocId,
            type: 'invoice',
            confidence: Math.round(pd.confidence ?? response.confidence ?? 0),
            supplier_name: pd.supplier_name || 'Unknown Supplier',
            pages: [1],
            preview_urls: [],
            metadata: {
              invoice_number: pd.invoice_number || 'Unknown',
              total_amount: pd.total_amount || 0,
              invoice_date: pd.invoice_date || new Date().toISOString().split('T')[0]
            },
            status: 'processed',
            originalFile: file,
            // ✅ Add OCR debug data
            word_count: response.word_count,
            psm_used: response.psm_used,
            was_retried: response.was_retried,
            raw_ocr_text: response.raw_ocr_text,
            ocr_pages: response.pages
          };

          // ✅ Replace temp card with processed result only once
          setPendingUploads(prev => {
            const filtered = prev.filter(doc => doc.id !== tempCard.id);
            return [...filtered, processedDoc];
          });

          showToast('success', `Successfully processed ${file.name}`);
        }

        if (progressInterval) {
          clearInterval(progressInterval);
          progressInterval = null;
        }
        if (timeoutId) {
          clearTimeout(timeoutId);
          timeoutId = null;
        }
        
        // ✅ Ensure progress reaches 100%
        setUploadProgress(prev => ({ ...prev, [file.name]: 100 }));
        
      } catch (error) {
        console.error(`❌ Direct upload failed for ${file.name}:`, error);
        
        // Clear progress interval on error
        if (progressInterval) {
          clearInterval(progressInterval);
          progressInterval = null;
        }
        if (timeoutId) {
          clearTimeout(timeoutId);
          timeoutId = null;
        }
        
        // Fallback to smart processing
        try {
          console.log(`🔄 Attempting smart processing fallback for ${file.name}...`);
          updateProgress(file.name, 60, "OCR Processing");
        response = await Promise.race([
            apiService.uploadDocumentForReview(file),
            createTimeoutPromise(300000) // Increased timeout to 5 minutes for PaddleOCR
          ]);
          
          console.log(`✅ Smart processing successful for ${file.name}:`, response);
          
          if (response.suggested_documents && response.suggested_documents.length > 0) {
            // Convert suggested documents to our format
            const processedDocs: DocumentUploadResult[] = response.suggested_documents.map((doc: any, index: number) => ({
              id: doc.invoice_id || doc.id || `doc-${Date.now()}-${index}`,
              type: doc.type || 'unknown',
              confidence: doc.confidence || 0,
              supplier_name: doc.supplier_name || 'Unknown',
              pages: doc.pages || [1],
              preview_urls: doc.preview_urls || [],
              metadata: doc.metadata || {},
              status: 'processed',
              originalFile: file
            }));

            // ✅ Replace temp card with processed results
            setPendingUploads(prev => {
              const filtered = prev.filter(doc => doc.id !== tempCard.id);
              return [...filtered, ...processedDocs];
            });
            
            // ✅ Ensure progress reaches 100%
            setUploadProgress(prev => ({ ...prev, [file.name]: 100 }));
            
            showToast('success', `Successfully processed ${file.name} (${processedDocs.length} documents found)`);
          } else {
            // No documents found
            setPendingUploads(prev => {
              const filtered = prev.filter(doc => doc.id !== tempCard.id);
              return [...filtered, {
                ...tempCard,
                status: 'error',
                supplier_name: 'No documents found',
                metadata: {
                  invoice_number: 'Processing failed',
                  total_amount: 0,
                  invoice_date: undefined
                }
              }];
            });
            
            // ✅ Set progress to 100% even on error
            setUploadProgress(prev => ({ ...prev, [file.name]: 100 }));
            
            showToast('error', `No documents found in ${file.name}`);
          }
        } catch (fallbackError) {
          console.error(`❌ Smart processing also failed for ${file.name}:`, fallbackError);
          
          // ✅ Replace temp card with error state
          setPendingUploads(prev => {
            const filtered = prev.filter(doc => doc.id !== tempCard.id);
            return [...filtered, {
              ...tempCard,
              status: 'error',
              supplier_name: 'Processing failed',
              metadata: {
                invoice_number: 'Error',
                total_amount: 0,
                invoice_date: undefined
              }
            }];
          });
          
          // ✅ Set progress to 100% on error
          setUploadProgress(prev => ({ ...prev, [file.name]: 100 }));
          
          showToast('error', `Failed to process ${file.name}`);
        }
      }
    } catch (error) {
      console.error(`❌ Upload failed for ${file.name}:`, error);
      
      // Clear intervals and timeouts
      if (progressInterval) {
        clearInterval(progressInterval);
        progressInterval = null;
      }
      if (timeoutId) {
        clearTimeout(timeoutId);
        timeoutId = null;
      }
      
      // ✅ Replace temp card with error state
      setPendingUploads(prev => {
        const filtered = prev.filter(doc => doc.id !== tempCard.id);
        return [...filtered, {
          ...tempCard,
          status: 'error',
          supplier_name: 'Upload failed',
          metadata: {
            invoice_number: 'Error',
            total_amount: 0,
            invoice_date: undefined
          }
        }];
      });
      
      // ✅ Set progress to 100% on error
      setUploadProgress(prev => ({ ...prev, [file.name]: 100 }));
      
      showToast('error', `Upload failed for ${file.name}`);
    } finally {
      setIsUploading(false);
      setCurrentFile(null);
    }
  };

  const handleFileSelect = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = event.target.files;
    if (files && files.length > 0) {
      console.log("Total files selected:", files.length);
      const filesArray = Array.from(files);
      for (const file of filesArray) {
        await handleFileUpload(file); // ensure async handling
      }
    }
    // Reset input
    if (event.target) {
      event.target.value = '';
    }
  };

  const [dragActive, setDragActive] = useState(false);
  const [preview, setPreview] = useState<string | null>(null);

  const handleDrop = async (event: React.DragEvent) => {
    event.preventDefault();
    const files = event.dataTransfer.files;
    if (files && files.length > 0) {
      console.log("Total files dropped:", files.length);
      const filesArray = Array.from(files);
      for (const file of filesArray) {
        await handleFileUpload(file);
      }
    }
  };

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const handleDragOver = (event: React.DragEvent) => {
    event.preventDefault();
  };

  // ✅ Updated handleSubmit() logic - Only save to DB when user confirms
  const handleSubmit = async () => {
    try {
      // Filter out error documents and only submit processed ones
      const documentsToSubmit = pendingUploads.filter(doc => doc.status === 'processed');
      
      if (documentsToSubmit.length === 0) {
        showToast('warning', 'No valid documents to submit');
        return;
      }

      // ✅ Log what is being submitted
      console.log('Submitting to Owlin:', documentsToSubmit);

      // TODO: Implement actual API call to save to database
      // await apiService.submitDocuments(documentsToSubmit);
      
      showToast('success', `Successfully submitted ${documentsToSubmit.length} document${documentsToSubmit.length !== 1 ? 's' : ''} to archive`);
      
      // ✅ Clear pending uploads (temporary preview cards)
      setPendingUploads([]);
      
      // ✅ Notify parent component to refresh the main invoice list
      if (onDocumentsSubmitted) {
        onDocumentsSubmitted(documentsToSubmit);
      }
    } catch (error) {
      console.error('Submit failed:', error);
      showToast('error', 'Failed to submit documents');
    }
  };

  // ✅ Updated handleClear() - Only clears upload queue, not archived invoices
  const handleClear = () => {
    setPendingUploads([]);
    showToast('success', 'Upload queue cleared');
  };

  const handleConfirmDocuments = async (documents: DocumentUploadResult[]) => {
    try {
      // TODO: Implement document confirmation logic
      console.log('Confirming documents:', documents);
      
      showToast('success', 'Documents confirmed successfully');
      setShowReviewModal(false);
    } catch (error) {
      console.error('Document confirmation failed:', error);
      showToast('error', 'Failed to confirm documents');
    }
  };

  const handleCancelReview = () => {
    setShowReviewModal(false);
  };

  const handleEditDocument = (documentId: string) => {
    console.log('Edit document:', documentId);
    // TODO: Implement edit functionality
  };

  const handleRemoveDocument = (documentId: string) => {
    setPendingUploads(prev => prev.filter(doc => doc.id !== documentId));
    showToast('success', 'Document removed from queue');
  };

  const handleConfidenceBadgeClick = (documentId: string) => {
    console.log('Confidence badge clicked:', documentId);
    // TODO: Implement confidence review functionality
  };

  const getDocumentIcon = (doc: DocumentUploadResult) => {
    switch (doc.type) {
      case 'invoice':
        return '🧾';
      case 'delivery_note':
        return '📦';
      case 'receipt':
        return '🧾';
      case 'utility':
        return '⚡';
      default:
        return '📄';
    }
  };

  const formatCurrency = (amount: number | undefined) => {
    if (amount === undefined || amount === null) return '£0.00';
    return new Intl.NumberFormat('en-GB', {
      style: 'currency',
      currency: 'GBP',
    }).format(amount);
  };

  const formatDate = (dateString: string | undefined) => {
    if (!dateString) return 'N/A';
    try {
      return new Date(dateString).toLocaleDateString('en-GB', {
        day: '2-digit',
        month: 'short',
        year: 'numeric',
      });
    } catch {
      return 'Invalid Date';
    }
  };

  return (
    <div className="space-y-6">
      {/* File Upload Area */}
      <div
        className="border-2 border-dashed border-gray-300 rounded-lg p-8 text-center hover:border-blue-400 transition-colors cursor-pointer"
        onClick={() => fileInputRef.current?.click()}
        onDrop={handleDrop}
        onDragOver={handleDragOver}
      >
        <input
          ref={fileInputRef}
          type="file"
          multiple
          accept=".pdf,.jpg,.jpeg,.png"
          onChange={handleFileSelect}
          className="hidden"
        />
        <div className="space-y-4">
          <div className="text-4xl">📄</div>
          <div>
            <h3 className="text-lg font-semibold text-gray-900 mb-2">
              Upload Documents
            </h3>
            <p className="text-gray-600">
              Drag and drop files here, or click to browse
            </p>
            <p className="text-sm text-gray-500 mt-1">
              Supports PDF, JPG, JPEG, PNG files
            </p>
          </div>
        </div>
      </div>

      {/* Upload Progress */}
      {Object.keys(uploadProgress).length > 0 && (
        <div className="space-y-3">
          {Object.entries(uploadProgress).map(([fileName, progress]) => (
            <div key={fileName} className="bg-gray-50 rounded-lg p-4">
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-medium text-gray-700 truncate">
                  {fileName}
                </span>
                <span className="text-sm text-gray-500">{progress}%</span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-2">
                <div
                  className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                  style={{ width: `${progress}%` }}
                />
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Pending Uploads */}
      {pendingUploads.length > 0 && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-lg font-semibold text-gray-900">
              Pending Documents ({pendingUploads.length})
            </h3>
            <div className="flex items-center space-x-2">
              <label className="flex items-center space-x-2 text-sm">
                <input
                  type="checkbox"
                  checked={showLowConfidenceOnly}
                  onChange={(e) => setShowLowConfidenceOnly(e.target.checked)}
                  className="rounded"
                />
                <span>Show low confidence only</span>
              </label>
            </div>
          </div>

          {/* ✅ Improved card layout with horizontal scroll */}
          <div className="overflow-x-auto">
            <div className="flex space-x-4 min-w-max pb-2">
              {filteredDocuments.map((doc) => (
                <div
                  key={doc.id}
                  className="relative bg-white rounded-lg border border-gray-200 p-4 min-w-[280px] max-w-[320px] shadow-sm hover:shadow-md transition-shadow group"
                >
                  {/* ✅ Delete button on hover */}
                  <button
                    onClick={() => handleRemoveDocument(doc.id)}
                    className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity p-1 rounded-full hover:bg-red-50 text-red-500 hover:text-red-700"
                    title="Remove document"
                  >
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  </button>

                  {/* Card Header */}
                  <div className="flex items-start space-x-3 mb-3">
                    <div className="text-2xl">{getDocumentIcon(doc)}</div>
                    <div className="flex-1 min-w-0">
                      {/* ✅ Enhanced supplier name and filename display */}
                      <h4 className="text-sm font-semibold text-gray-900 truncate">
                        {doc.supplier_name || 'Unknown Supplier'}
                      </h4>
                      <p className="text-xs text-gray-500 truncate">
                        {doc.originalFile?.name || doc.metadata.invoice_number || 'Processing...'}
                      </p>
                      {/* Page Range Badge (only for multi-invoice documents) */}
                      {doc.page_range && doc.page_range !== 'Page 1' && (
                        <span className="inline-block bg-blue-100 text-blue-800 text-xs font-medium px-2 py-0.5 rounded-full border border-blue-200 mt-1">
                          {doc.page_range}
                        </span>
                      )}
                    </div>
                    {/* ✅ Confidence Badge (always visible, top-right) */}
                    {doc.confidence !== undefined && (
                      <div className="flex-shrink-0">
                        <ConfidenceBadge confidence={Math.round(doc.confidence)} />
                      </div>
                    )}
                  </div>

                  {/* Card Content */}
                  <div className="space-y-2">
                    {/* Card Status */}
                    <div className="flex items-center justify-between mb-2">
                      <span className={`text-xs px-2 py-1 rounded-full ${
                        doc.status === 'processed' 
                          ? 'bg-green-100 text-green-800' 
                          : doc.status === 'error'
                          ? 'bg-red-100 text-red-800'
                          : doc.status === 'manual_review'
                          ? 'bg-orange-100 text-orange-800'
                          : 'bg-yellow-100 text-yellow-800'
                      }`}>
                        {doc.status === 'processed' ? 'Processed' : 
                         doc.status === 'error' ? 'Error' :
                         doc.status === 'manual_review' ? 'Review Required' :
                         'Processing...'}
                      </span>
                      <span className="text-xs text-gray-500">
                        {doc.type}
                      </span>
                    </div>
                    
                    {/* ✅ Enhanced metadata display */}
                    {doc.metadata && (
                      <div className="mb-3">
                        {doc.metadata.total_amount && (
                          <div className="text-sm font-semibold text-gray-900">
                            Total: £{doc.metadata.total_amount.toFixed(2)}
                          </div>
                        )}
                        {doc.metadata.invoice_number && doc.metadata.invoice_number !== 'Unknown' && (
                          <div className="text-xs text-gray-500">
                            Invoice: {doc.metadata.invoice_number}
                          </div>
                        )}
                        {doc.metadata.invoice_date && doc.metadata.invoice_date !== 'Unknown' && (
                          <div className="text-xs text-gray-500">
                            Date: {doc.metadata.invoice_date}
                          </div>
                        )}
                      </div>
                    )}
                  </div>

                  {/* Progress Bar for Processing */}
                  {doc.status === 'scanning' && (
                    <div className="mt-3">
                      <div className="w-full bg-gray-200 rounded-full h-1">
                        <div className="bg-blue-600 h-1 rounded-full transition-all duration-300 animate-pulse" style={{ width: '60%' }} />
                      </div>
                      <p className="text-xs text-gray-500 mt-1">Processing...</p>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      <SmartDocumentReviewModal
        isOpen={showReviewModal}
        onClose={() => setShowReviewModal(false)}
        suggestedDocuments={pendingUploads.map(doc => ({
          id: doc.id,
          type: doc.type,
          confidence: doc.confidence,
          supplier_name: doc.supplier_name,
          pages: doc.pages,
          preview_urls: doc.preview_urls,
          metadata: doc.metadata
        }))}
        onConfirm={async (documents) => {
          await handleConfirmDocuments(documents.map(doc => ({
            ...doc,
            status: 'processed' as const,
            originalFile: pendingUploads.find(p => p.id === doc.id)?.originalFile || new File([], 'unknown')
          })));
        }}
        fileName="Uploaded Documents"
      />
    </div>
  );
};

export default UploadSection; 