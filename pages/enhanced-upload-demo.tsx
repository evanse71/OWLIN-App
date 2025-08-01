import React, { useState } from 'react';
import Layout from '@/components/Layout';
import EnhancedUploadPanel from '@/components/invoices/EnhancedUploadPanel';
import EnhancedInvoiceCard from '@/components/invoices/EnhancedInvoiceCard';

interface UploadResult {
  documentId: string;
  filename: string;
  overallConfidence: number;
  manualReviewRequired: boolean;
  documentType: string;
  processingTime: number;
  parsedInvoice?: any;
  userRole?: string;
}

const EnhancedUploadDemo: React.FC = () => {
  const [uploadResults, setUploadResults] = useState<UploadResult[]>([]);
  const [userRole, setUserRole] = useState<'viewer' | 'finance' | 'admin'>('finance');

  const handleUploadComplete = (results: UploadResult[]) => {
    setUploadResults(prev => [...prev, ...results]);
  };

  const handleEdit = (documentId: string) => {
    console.log('Edit document:', documentId);
    // Implement edit functionality
  };

  const handleApprove = (documentId: string) => {
    console.log('Approve document:', documentId);
    // Implement approve functionality
  };

  const handleReject = (documentId: string) => {
    console.log('Reject document:', documentId);
    // Implement reject functionality
  };

  return (
    <Layout>
      <div className="container mx-auto py-8 px-4">
        <div className="max-w-7xl mx-auto">
          {/* Header */}
          <div className="text-center mb-8">
            <h1 className="text-3xl font-bold text-gray-900 dark:text-gray-100 mb-2">
              🚀 Enhanced Document Upload Demo
            </h1>
            <p className="text-lg text-gray-600 dark:text-gray-400">
              Experience the new unified upload pipeline with confidence scoring and manual review
            </p>
          </div>

          {/* User Role Selector */}
          <div className="mb-6 p-4 bg-blue-50 rounded-lg">
            <h3 className="text-lg font-semibold mb-2">User Role</h3>
            <div className="flex gap-4">
              <label className="flex items-center">
                <input
                  type="radio"
                  name="userRole"
                  value="viewer"
                  checked={userRole === 'viewer'}
                  onChange={(e) => setUserRole(e.target.value as any)}
                  className="mr-2"
                />
                Viewer (Read-only)
              </label>
              <label className="flex items-center">
                <input
                  type="radio"
                  name="userRole"
                  value="finance"
                  checked={userRole === 'finance'}
                  onChange={(e) => setUserRole(e.target.value as any)}
                  className="mr-2"
                />
                Finance (Edit & Approve)
              </label>
              <label className="flex items-center">
                <input
                  type="radio"
                  name="userRole"
                  value="admin"
                  checked={userRole === 'admin'}
                  onChange={(e) => setUserRole(e.target.value as any)}
                  className="mr-2"
                />
                Admin (Full Access)
              </label>
            </div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
            {/* Upload Panel */}
            <div>
              <EnhancedUploadPanel
                userRole={userRole}
                onUploadComplete={handleUploadComplete}
              />
            </div>

            {/* Results Display */}
            <div>
              <div className="bg-white rounded-lg shadow p-6">
                <h3 className="text-lg font-semibold mb-4">Processing Results</h3>
                
                {uploadResults.length === 0 ? (
                  <div className="text-center py-8 text-gray-500">
                    <p>No documents processed yet.</p>
                    <p className="text-sm mt-2">Upload a document to see results here.</p>
                  </div>
                ) : (
                  <div className="space-y-4">
                    {uploadResults.map((result, index) => (
                      <EnhancedInvoiceCard
                        key={index}
                        documentId={result.documentId}
                        filename={result.filename}
                        overallConfidence={result.overallConfidence}
                        manualReviewRequired={result.manualReviewRequired}
                        documentType={result.documentType}
                        processingTime={result.processingTime}
                        parsedInvoice={result.parsedInvoice}
                        userRole={userRole}
                        onEdit={() => handleEdit(result.documentId)}
                        onApprove={() => handleApprove(result.documentId)}
                        onReject={() => handleReject(result.documentId)}
                      />
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Feature Overview */}
          <div className="mt-12 bg-gray-50 rounded-lg p-6">
            <h3 className="text-xl font-semibold mb-4">Enhanced Features</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              <div className="bg-white p-4 rounded-lg shadow">
                <h4 className="font-semibold text-blue-600 mb-2">🎯 Confidence Scoring</h4>
                <p className="text-sm text-gray-600">
                  Automatic confidence scoring with visual indicators for quality assessment.
                </p>
              </div>
              
              <div className="bg-white p-4 rounded-lg shadow">
                <h4 className="font-semibold text-orange-600 mb-2">⚠️ Manual Review</h4>
                <p className="text-sm text-gray-600">
                  Automatic flagging of documents requiring manual review due to low confidence.
                </p>
              </div>
              
              <div className="bg-white p-4 rounded-lg shadow">
                <h4 className="font-semibold text-green-600 mb-2">📊 Template Parsing</h4>
                <p className="text-sm text-gray-600">
                  Intelligent extraction of invoice metadata including supplier, totals, and line items.
                </p>
              </div>
              
              <div className="bg-white p-4 rounded-lg shadow">
                <h4 className="font-semibold text-purple-600 mb-2">🔐 Role-Based Access</h4>
                <p className="text-sm text-gray-600">
                  Different permissions based on user role (Viewer, Finance, Admin).
                </p>
              </div>
              
              <div className="bg-white p-4 rounded-lg shadow">
                <h4 className="font-semibold text-indigo-600 mb-2">🔄 Dual OCR Engine</h4>
                <p className="text-sm text-gray-600">
                  PaddleOCR primary with Tesseract fallback for maximum accuracy.
                </p>
              </div>
              
              <div className="bg-white p-4 rounded-lg shadow">
                <h4 className="font-semibold text-red-600 mb-2">📁 Batch Processing</h4>
                <p className="text-sm text-gray-600">
                  Support for multiple file uploads with individual progress tracking.
                </p>
              </div>
            </div>
          </div>

          {/* Technical Details */}
          <div className="mt-8 bg-blue-50 rounded-lg p-6">
            <h3 className="text-lg font-semibold mb-4">Technical Implementation</h3>
            <div className="space-y-3 text-sm">
              <div className="flex items-start gap-2">
                <span className="font-medium">Backend:</span>
                <span>Unified upload pipeline with enhanced OCR processing</span>
              </div>
              <div className="flex items-start gap-2">
                <span className="font-medium">OCR Engine:</span>
                <span>PaddleOCR primary (70%+ confidence) with Tesseract fallback</span>
              </div>
              <div className="flex items-start gap-2">
                <span className="font-medium">Pre-processing:</span>
                <span>Adaptive thresholding, deskewing, noise removal</span>
              </div>
              <div className="flex items-start gap-2">
                <span className="font-medium">Confidence Thresholds:</span>
                <span>70% for re-processing, 65% for manual review</span>
              </div>
              <div className="flex items-start gap-2">
                <span className="font-medium">File Support:</span>
                <span>PDF, JPG, JPEG, PNG up to 50MB</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </Layout>
  );
};

export default EnhancedUploadDemo; 