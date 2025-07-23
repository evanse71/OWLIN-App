import React, { useState } from 'react';
import Layout from '@/components/Layout';
import UploadSection from '@/components/invoices/UploadSection';
import DocumentSection from '@/components/invoices/DocumentSection';
import { useDocuments } from '@/hooks/useDocuments';
import { FileStatus, Invoice, DeliveryNote } from '@/services/api';

const InvoicesPage: React.FC = () => {
  const { documents, loading, error, refetch } = useDocuments(10000);
  const [selectedDocument, setSelectedDocument] = useState<FileStatus | Invoice | DeliveryNote | null>(null);

  const handleUploadComplete = () => {
    // Refresh documents after upload
    refetch();
  };

  const handleDocumentClick = (document: FileStatus | Invoice | DeliveryNote) => {
    setSelectedDocument(document);
  };

  const handleRetry = async (document: FileStatus | Invoice | DeliveryNote) => {
    // TODO: Implement retry logic
    console.log('Retry clicked for:', document);
  };

  const handleCancel = async (document: FileStatus | Invoice | DeliveryNote) => {
    // TODO: Implement cancel logic
    console.log('Cancel clicked for:', document);
  };

  if (loading) {
    return (
      <Layout>
        <div className="container mx-auto py-8">
          <div className="flex items-center justify-center h-64">
            <div className="text-center">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
              <p className="text-gray-600">Loading documents...</p>
            </div>
          </div>
        </div>
      </Layout>
    );
  }

  return (
    <Layout>
      <div className="container mx-auto py-8 px-4">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900 text-center mb-2">
            📄 Invoice Management
          </h1>
          <p className="text-gray-600 text-center">
            Upload, scan, and match invoices with delivery notes
          </p>
        </div>

        {error && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <svg className="h-5 w-5 text-red-400" viewBox="0 0 20 20" fill="currentColor">
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                </svg>
              </div>
              <div className="ml-3">
                <h3 className="text-sm font-medium text-red-800">
                  Connection Error
                </h3>
                <div className="mt-2 text-sm text-red-700">
                  <p>{error}</p>
                  <p className="mt-1">
                    Showing sample data. Please check your backend connection.
                  </p>
                </div>
              </div>
            </div>
          </div>
        )}

        <UploadSection onUploadComplete={handleUploadComplete} />

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mt-8">
          <DocumentSection
            title="📂 Recently Uploaded"
            icon="📂"
            documents={documents.recentlyUploaded}
            emptyMessage="No files currently uploading"
            onDocumentClick={handleDocumentClick}
            onRetry={handleRetry}
            onCancel={handleCancel}
          />

          <DocumentSection
            title="📄 Scanned - Awaiting Match"
            icon="📄"
            documents={documents.scannedAwaitingMatch}
            emptyMessage="No documents awaiting matching"
            onDocumentClick={handleDocumentClick}
            onRetry={handleRetry}
            onCancel={handleCancel}
          />

          <DocumentSection
            title="✅ Matched Documents"
            icon="✅"
            documents={documents.matchedDocuments}
            emptyMessage="No matched documents yet"
            onDocumentClick={handleDocumentClick}
            onRetry={handleRetry}
            onCancel={handleCancel}
          />

          <DocumentSection
            title="❗ Failed or Error"
            icon="❗"
            documents={documents.failedDocuments}
            emptyMessage="No failed documents"
            onDocumentClick={handleDocumentClick}
            onRetry={handleRetry}
            onCancel={handleCancel}
          />
        </div>

        {selectedDocument && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
            <div className="bg-white rounded-lg p-6 max-w-2xl w-full max-h-[80vh] overflow-y-auto">
              <div className="flex justify-between items-center mb-4">
                <h3 className="text-lg font-semibold">Document Details</h3>
                <button
                  onClick={() => setSelectedDocument(null)}
                  className="text-gray-400 hover:text-gray-600"
                >
                  <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
              <pre className="text-sm bg-gray-100 p-4 rounded overflow-auto">
                {JSON.stringify(selectedDocument, null, 2)}
              </pre>
            </div>
          </div>
        )}
      </div>
    </Layout>
  );
};

export default InvoicesPage; 