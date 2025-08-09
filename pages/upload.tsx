import React, { useState } from 'react';
import Layout from '@/components/Layout';
import EnhancedUploadPanel from '@/components/invoices/EnhancedUploadPanel';
import { useToast } from '@/utils/toast';

interface UploadPageProps {}

const UploadPage: React.FC<UploadPageProps> = () => {
  const [selectedDocumentType, setSelectedDocumentType] = useState<'invoice' | 'delivery_note' | 'receipt' | 'utility'>('invoice');
  const [userRole, setUserRole] = useState<'viewer' | 'finance' | 'admin' | 'GM'>('finance');

  const { showToast } = useToast();

  const handleUploadComplete = (results: any[]) => {
    showToast('success', `✅ Successfully processed ${results.length} document(s)`);
  };

  const documentTypeOptions = [
    { value: 'invoice', label: 'Invoice', icon: '📄' },
    { value: 'receipt', label: 'Receipt', icon: '🧾' },
    { value: 'utility', label: 'Utility', icon: '⚡' },
  ];

  return (
    <Layout>
      <div className="container mx-auto py-8 px-4">
        <div className="max-w-6xl mx-auto">
          {/* Header */}
          <div className="text-center mb-8">
            <h1 className="text-3xl font-bold text-gray-900 dark:text-gray-100 mb-2">
              📤 Enhanced Upload
            </h1>
            <p className="text-gray-600 dark:text-gray-400">
              Upload documents with OCR processing, validation, and database storage
            </p>
          </div>

          {/* Configuration Panel */}
          <div className="bg-white dark:bg-gray-800 rounded-lg p-6 border border-gray-200 dark:border-gray-700 mb-6">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">
              Configuration
            </h2>
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* Document Type Selector */}
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">
                  Document Type
                </label>
                <div className="flex flex-wrap gap-2">
                  {documentTypeOptions.map((option) => (
                    <button
                      key={option.value}
                      onClick={() => setSelectedDocumentType(option.value as any)}
                      className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                        selectedDocumentType === option.value
                          ? 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300 border border-blue-300 dark:border-blue-700'
                          : 'bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300 border border-gray-300 dark:border-gray-600 hover:bg-gray-200 dark:hover:bg-gray-600'
                      }`}
                    >
                      <span className="mr-2">{option.icon}</span>
                      {option.label}
                    </button>
                  ))}
                </div>
              </div>

              {/* User Role Selector */}
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">
                  User Role
                </label>
                <select
                  value={userRole}
                  onChange={(e) => setUserRole(e.target.value as any)}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
                >
                  <option value="viewer">Viewer</option>
                  <option value="finance">Finance</option>
                  <option value="admin">Admin</option>
                  <option value="GM">GM</option>
                </select>
              </div>
            </div>
          </div>

          {/* Enhanced Upload Panel */}
          <EnhancedUploadPanel
            userRole={userRole}
            documentType={selectedDocumentType}
            onUploadComplete={handleUploadComplete}
          />

          {/* Info Section */}
          <div className="mt-8 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
            <div className="flex items-start space-x-3">
              <div className="text-blue-600 dark:text-blue-400 text-xl">ℹ️</div>
              <div>
                <h3 className="text-sm font-medium text-blue-900 dark:text-blue-100 mb-1">
                  Enhanced Processing Features
                </h3>
                <p className="text-sm text-blue-800 dark:text-blue-200">
                  Your uploaded documents will be processed with OCR, field extraction, validation, 
                  and stored in the database with duplicate detection and role-based access control. 
                  You can view and manage all documents in the{' '}
                  <a href="/document-queue" className="underline hover:no-underline font-medium">
                    Document Queue
                  </a>{' '}
                  page.
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </Layout>
  );
};

export default UploadPage; 