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
  status: 'scanning' | 'processed' | 'error';
  originalFile: File;
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

  const handleFileUpload = async (file: File) => {
    if (!file) return;

    console.log(`🚀 Starting upload for file: ${file.name} (${file.size} bytes)`);
    
    setIsUploading(true);
    setCurrentFile(file);
    setUploadProgress(prev => ({ ...prev, [file.name]: 0 }));

    // ✅ Create small preview card (ChatGPT-style)
    const tempDocId = `temp-${Date.now()}`;
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

      // Set up 30-second timeout
      timeoutId = setTimeout(() => {
        console.error(`⏰ Upload timeout for ${file.name} after 30 seconds`);
        throw new Error('Upload timed out after 30 seconds');
      }, 30000);

      // Try direct upload first
      let response: any;
      try {
        console.log(`📤 Attempting direct upload for ${file.name}...`);
        response = await Promise.race([
          apiService.uploadInvoice(file),
          createTimeoutPromise(30000)
        ]);
        
        console.log(`✅ Direct upload successful for ${file.name}:`, response);
        
        // ✅ Convert to processed document format
        const processedDoc: DocumentUploadResult = {
          id: response.invoice_id || tempDocId,
          type: 'invoice',
          confidence: Math.round(response.parsed_data?.confidence || response.confidence || 0),
          supplier_name: response.parsed_data?.supplier_name || 'Unknown',
          pages: [1],
          preview_urls: [],
          metadata: {
            invoice_number: response.parsed_data?.invoice_number || 'Unknown',
            total_amount: response.parsed_data?.total_amount || 0,
            invoice_date: response.parsed_data?.invoice_date || new Date().toISOString().split('T')[0]
          },
          status: 'processed',
          originalFile: file
        };

        // ✅ Replace temp card with processed results
        setPendingUploads(prev => {
          const filtered = prev.filter(doc => doc.id !== tempCard.id);
          return [...filtered, processedDoc];
        });

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
        
        showToast('success', `Successfully processed ${file.name}`);
        
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
          response = await Promise.race([
            apiService.uploadDocumentForReview(file),
            createTimeoutPromise(30000)
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

          <div className="grid gap-4">
            {filteredDocuments.map((doc) => (
              <div
                key={doc.id}
                className={`bg-white rounded-lg border p-4 ${
                  doc.status === 'error' ? 'border-red-200 bg-red-50' : 'border-gray-200'
                }`}
              >
                <div className="flex items-start justify-between">
                  <div className="flex items-start space-x-3 flex-1">
                    <div className="text-2xl">{getDocumentIcon(doc)}</div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center space-x-2 mb-1">
                        <h4 className="font-medium text-gray-900 truncate">
                          {doc.status === 'scanning' ? doc.supplier_name : doc.supplier_name}
                        </h4>
                        {doc.status === 'processed' && (
                          <ConfidenceBadge
                            confidence={doc.confidence}
                          />
                        )}
                      </div>
                      <div className="text-sm text-gray-600 space-y-1">
                        {doc.status === 'scanning' && (
                          <div className="flex items-center space-x-2">
                            <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600"></div>
                            <span>Processing document...</span>
                          </div>
                        )}
                        {doc.status === 'processed' && (
                          <>
                            <div>Invoice: {doc.metadata.invoice_number}</div>
                            {doc.metadata.total_amount && (
                              <div>Amount: {formatCurrency(doc.metadata.total_amount)}</div>
                            )}
                            {doc.metadata.invoice_date && (
                              <div>Date: {formatDate(doc.metadata.invoice_date)}</div>
                            )}
                          </>
                        )}
                        {doc.status === 'error' && (
                          <div className="text-red-600">❌ {doc.supplier_name}</div>
                        )}
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center space-x-2">
                    {doc.status === 'processed' && (
                      <button
                        onClick={() => handleEditDocument(doc.id)}
                        className="text-blue-600 hover:text-blue-800 text-sm"
                      >
                        Edit
                      </button>
                    )}
                    <button
                      onClick={() => handleRemoveDocument(doc.id)}
                      className="text-red-600 hover:text-red-800 text-sm"
                    >
                      Remove
                    </button>
                  </div>
                </div>
                
                {/* ✅ Show progress bar for scanning documents */}
                {doc.status === 'scanning' && (
                  <div className="mt-3">
                    <div className="w-full bg-gray-200 rounded-full h-2">
                      <div
                        className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                        style={{ width: `${uploadProgress[doc.originalFile.name] || 0}%` }}
                      />
                    </div>
                    <div className="text-xs text-gray-500 mt-1">
                      {uploadProgress[doc.originalFile.name] || 0}% complete
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>

          {/* Action Buttons */}
          <div className="flex items-center justify-between pt-4 border-t border-gray-200">
            <button
              onClick={handleClear}
              className="px-4 py-2 text-gray-600 hover:text-gray-800 text-sm"
            >
              Clear All
            </button>
            <div className="flex items-center space-x-3">
              <span className="text-sm text-gray-600">
                {processedCount} of {pendingUploads.length} processed
              </span>
              <button
                onClick={handleSubmit}
                disabled={processedCount === 0 || isUploading}
                className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Submit to Owlin ({processedCount})
              </button>
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