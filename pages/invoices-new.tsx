import React, { useState, useEffect } from 'react';
import AppShell from '@/components/layout/AppShell';
import { useToast } from '@/utils/toast';
import InvoiceCardsPanel from '@/components/invoices/InvoiceCardsPanel';
import UploadSection from '@/components/invoices/UploadSection';
import { apiService } from '@/services/api';

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
}

const InvoicesPage: React.FC = () => {
  const { showToast } = useToast();
  
  // ✅ State to trigger refresh of archived documents
  const [documentsChanged, setDocumentsChanged] = useState(0);

  // ✅ Dev-only useEffect hook to clear all documents on page load
  useEffect(() => {
    if (process.env.NODE_ENV === 'development') {
      const resetData = async () => {
        try {
          await apiService.clearAllDocuments();
          console.log('[Dev Reset] Cleared all invoices on load');
        } catch (err) {
          console.warn('[Dev Reset] Failed to clear documents:', err);
        }
      };
      resetData();
    }
  }, []);

  // ✅ Handle documents submitted from UploadSection
  const handleDocumentsSubmitted = (documents: DocumentUploadResult[]) => {
    showToast('success', `Successfully submitted ${documents.length} document${documents.length !== 1 ? 's' : ''} to the archive`);
    
    // ✅ Trigger refresh of the InvoiceCardsPanel to show newly archived documents
    setDocumentsChanged(prev => prev + 1);
  };

  return (
    <AppShell>
      <div className="py-8">
        <div className="max-w-7xl mx-auto space-y-8">
          {/* Page Header */}
          <div className="text-center">
            <h1 className="text-3xl font-bold text-gray-900 mb-2">
              Invoice Management
            </h1>
            <p className="text-gray-600">
              Upload, review, and manage your invoice documents
            </p>
          </div>

          {/* ✅ Upload Section - Temporary Preview Only */}
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
            <h2 className="text-xl font-semibold text-gray-900 mb-4">
              📤 Upload Documents
            </h2>
            <p className="text-sm text-gray-600 mb-4">
              Upload documents for processing. They will appear in the preview below for review before being submitted to the archive.
            </p>
            <UploadSection onDocumentsSubmitted={handleDocumentsSubmitted} />
          </div>

          {/* ✅ Invoice Cards Panel - Archived Documents Only */}
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
            <div className="mb-4">
              <h2 className="text-xl font-semibold text-gray-900">
                📋 Scanned Invoices
              </h2>
              <p className="text-sm text-gray-600">
                Documents that have been submitted and saved to the archive.
              </p>
            </div>
            <InvoiceCardsPanel 
              title="Scanned Invoices"
              showScannedOnly={true}
              key={documentsChanged} // ✅ Force refresh when documents are submitted
            />
          </div>
        </div>
      </div>
    </AppShell>
  );
};

export default InvoicesPage; 