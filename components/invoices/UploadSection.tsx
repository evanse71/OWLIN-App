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

  const handleFileUpload = async (file: File) => {
    if (!file) return;

    setIsUploading(true);
    setCurrentFile(file);
    setUploadProgress(prev => ({ ...prev, [file.name]: 0 }));

    // ✅ Create temporary DocumentUploadResult object when file is uploaded
    const tempDocId = `temp-${Date.now()}`;
    const tempCard: DocumentUploadResult = {
      id: tempDocId,
      type: 'unknown',
      confidence: 0,
      supplier_name: 'Scanning document...',
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

    // ✅ Push this object into the pendingUploads state (temporary preview only)
    setPendingUploads(prev => [...prev, tempCard]);

    try {
      // ✅ Track upload progress using uploadProgress state
      // ✅ Simulate a 10% increment every 200ms up to 90% while waiting for backend response
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

      // Try direct upload first (simpler OCR processing)
      let response: any;
      try {
        response = await apiService.uploadInvoice(file);
        
        // Convert the response to the expected format
        const processedDoc: DocumentUploadResult = {
          id: response.invoice_id || tempDocId,
          type: 'invoice',
          confidence: Math.round((response.parsed_data?.confidence || 0.75) * 100),
          supplier_name: response.parsed_data?.supplier_name || 'Unknown',
          pages: [1], // Single page for direct upload
          preview_urls: [],
          metadata: {
            invoice_number: response.parsed_data?.invoice_number || 'Unknown',
            total_amount: response.parsed_data?.total_amount || 0,
            invoice_date: response.parsed_data?.invoice_date || new Date().toISOString().split('T')[0]
          },
          status: 'processed',
          originalFile: file
        };

        // ✅ Replace temp card with processed results (still temporary preview only)
        setPendingUploads(prev => {
          const filtered = prev.filter(doc => !doc.id.startsWith('temp-'));
          return [...filtered, processedDoc];
        });

        clearInterval(progressInterval);
        setUploadProgress(prev => ({ ...prev, [file.name]: 100 }));
        
        showToast('success', `Successfully processed ${file.name}`);
      } catch (error) {
        console.error('Direct upload failed:', error);
        
        // Fallback to smart processing
        try {
          response = await apiService.uploadDocumentForReview(file);
          
          if (response.suggested_documents && response.suggested_documents.length > 0) {
            // Convert suggested documents to our format
            const processedDocs: DocumentUploadResult[] = response.suggested_documents.map((doc: any, index: number) => ({
              id: doc.id || `doc-${Date.now()}-${index}`,
              type: doc.type || 'unknown',
              confidence: doc.confidence || 0,
              supplier_name: doc.supplier_name || 'Unknown',
              pages: doc.pages || [1],
              preview_urls: doc.preview_urls || [],
              metadata: doc.metadata || {},
              status: 'processed',
              originalFile: file
            }));

            // ✅ Replace temp card with processed results (still temporary preview only)
            setPendingUploads(prev => {
              const filtered = prev.filter(doc => !doc.id.startsWith('temp-'));
              return [...filtered, ...processedDocs];
            });
          } else {
            // No documents found
            setPendingUploads(prev => {
              const filtered = prev.filter(doc => !doc.id.startsWith('temp-'));
              return [...filtered, {
                ...tempCard,
                status: 'error',
                supplier_name: 'No documents detected'
              }];
            });
          }
        } catch (smartError) {
          console.error('Smart processing also failed:', smartError);
          
          // Mark as error
          setPendingUploads(prev => {
            const filtered = prev.filter(doc => !doc.id.startsWith('temp-'));
            return [...filtered, {
              ...tempCard,
              status: 'error',
              supplier_name: 'Processing failed'
            }];
          });
        }
        
        clearInterval(progressInterval);
        setUploadProgress(prev => ({ ...prev, [file.name]: 100 }));
      }
    } catch (error) {
      console.error('Upload failed:', error);
      
      // Mark as error
      setPendingUploads(prev => {
        const filtered = prev.filter(doc => !doc.id.startsWith('temp-'));
        return [...filtered, {
          ...tempCard,
          status: 'error',
          supplier_name: 'Upload failed'
        }];
      });
      
      showToast('error', `Failed to process ${file.name}`);
    } finally {
      setIsUploading(false);
      setCurrentFile(null);
      setUploadProgress(prev => {
        const { [file.name]: _, ...rest } = prev;
        return rest;
      });
    }
  };

  const handleFileSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = event.target.files;
    if (files && files.length > 0) {
      Array.from(files).forEach(handleFileUpload);
    }
    // Reset input
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const handleDrop = (event: React.DragEvent) => {
    event.preventDefault();
    const files = event.dataTransfer.files;
    if (files && files.length > 0) {
      Array.from(files).forEach(handleFileUpload);
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
      {/* Upload Dropzone */}
      <div className="bg-white rounded-lg border-2 border-dashed border-gray-300 p-8 text-center hover:border-blue-400 transition-colors">
        <div className="space-y-4">
          <div className="text-4xl">📄</div>
          <div>
            <h3 className="text-lg font-medium text-gray-900 mb-2">
              Upload Invoice Documents
            </h3>
            <p className="text-gray-600 mb-4">
              Drag and drop PDF files here, or click to browse
            </p>
            <p className="text-sm text-gray-500">
              📄 Upload a single PDF with multiple invoices — we'll detect and split them for you automatically.
            </p>
          </div>
          
          <div className="flex justify-center">
            <button
              onClick={() => fileInputRef.current?.click()}
              disabled={isUploading}
              className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {isUploading ? 'Processing...' : 'Choose Files'}
            </button>
          </div>
          
          <input
            ref={fileInputRef}
            type="file"
            multiple
            accept=".pdf"
            onChange={handleFileSelect}
            className="hidden"
          />
        </div>
        
        <div
          className="absolute inset-0"
          onDrop={handleDrop}
          onDragOver={handleDragOver}
        />
      </div>

      {/* Upload Progress */}
      {Object.keys(uploadProgress).length > 0 && (
        <div className="space-y-2">
          {Object.entries(uploadProgress).map(([filename, progress]) => (
            <div key={filename} className="bg-white rounded-lg p-4 border">
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-medium text-gray-700">{filename}</span>
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

      {/* ✅ Temporary Preview Cards Section */}
      {pendingUploads.length > 0 && (
        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-medium text-gray-900">
              📋 Upload Preview ({filteredDocuments.length})
            </h3>
            <label className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={showLowConfidenceOnly}
                onChange={(e) => setShowLowConfidenceOnly(e.target.checked)}
                className="rounded border-gray-300"
              />
              Show only low-confidence documents
            </label>
          </div>

          {/* ✅ Temporary Preview Cards */}
          <div className="space-y-4">
            {filteredDocuments.map((doc) => (
              <div
                key={doc.id}
                className="bg-white rounded-lg border border-gray-200 p-4 hover:shadow-md transition-shadow"
              >
                <div className="flex items-start justify-between">
                  <div className="flex items-start space-x-3">
                    <div className="text-2xl">{getDocumentIcon(doc)}</div>
                    <div className="flex-1">
                      <div className="flex items-center space-x-2 mb-1">
                        <h4 className="font-medium text-gray-900">
                          {doc.supplier_name}
                        </h4>
                        {doc.confidence !== undefined && (
                          <ConfidenceBadge confidence={doc.confidence} />
                        )}
                      </div>
                      <div className="text-sm text-gray-600 space-y-1">
                        {doc.metadata.invoice_number && (
                          <div>Invoice: {doc.metadata.invoice_number}</div>
                        )}
                        {doc.metadata.invoice_date && (
                          <div>Date: {formatDate(doc.metadata.invoice_date)}</div>
                        )}
                        {doc.metadata.total_amount && (
                          <div>Amount: {formatCurrency(doc.metadata.total_amount)}</div>
                        )}
                      </div>
                    </div>
                  </div>
                  
                  <div className="flex items-center space-x-2">
                    {doc.status === 'error' && (
                      <span className="text-red-600 text-sm">❌ Error</span>
                    )}
                    {doc.status === 'scanning' && (
                      <span className="text-blue-600 text-sm">⏳ Scanning...</span>
                    )}
                    <button
                      onClick={() => handleRemoveDocument(doc.id)}
                      className="text-gray-400 hover:text-red-600 transition-colors"
                      title="Remove from queue"
                    >
                      ✕
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>

          {/* ✅ Submit and Clear Buttons - Only visible when there are pending uploads */}
          <div className="flex gap-4 justify-center mt-6">
            <button
              onClick={handleSubmit}
              className="bg-emerald-600 text-white px-6 py-3 rounded-lg hover:bg-emerald-700 transition font-medium"
            >
              ✅ Submit Documents ({processedCount})
            </button>
            <button
              onClick={handleClear}
              className="bg-slate-200 text-slate-700 px-6 py-3 rounded-lg hover:bg-slate-300 transition font-medium"
            >
              🧼 Clear All
            </button>
          </div>
        </div>
      )}

      {/* Review Modal */}
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