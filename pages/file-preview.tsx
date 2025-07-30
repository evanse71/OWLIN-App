import React, { useState, useEffect } from 'react';
import Layout from '@/components/Layout';

interface FileData {
  id: string;
  filename: string;
  upload_timestamp: string;
  invoice_number: string;
  supplier_name: string;
  total_amount: number;
  status: string;
  confidence: number;
  preview_url: string;
}

export default function FilePreviewPage() {
  const [files, setFiles] = useState<FileData[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedFile, setSelectedFile] = useState<FileData | null>(null);

  useEffect(() => {
    fetchFiles();
  }, []);

  const fetchFiles = async () => {
    try {
      setLoading(true);
      const response = await fetch('/api/files');
      if (!response.ok) {
        throw new Error('Failed to fetch files');
      }
      const data = await response.json();
      setFiles(data.files || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
    } finally {
      setLoading(false);
    }
  };

  const handlePreview = (file: FileData) => {
    setSelectedFile(file);
    // Open preview in new tab
    window.open(`/api/files/${file.id}/preview`, '_blank');
  };

  const formatDate = (timestamp: string) => {
    return new Date(timestamp).toLocaleDateString();
  };

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
    }).format(amount);
  };

  const getStatusColor = (status: string) => {
    switch (status.toLowerCase()) {
      case 'processed':
        return 'bg-green-100 text-green-800';
      case 'processing':
        return 'bg-yellow-100 text-yellow-800';
      case 'error':
        return 'bg-red-100 text-red-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  if (loading) {
    return (
      <Layout>
        <div className="container mx-auto p-6">
          <div className="flex items-center justify-center h-64">
            <div className="text-lg">Loading files...</div>
          </div>
        </div>
      </Layout>
    );
  }

  if (error) {
    return (
      <Layout>
        <div className="container mx-auto p-6">
          <div className="bg-white rounded-lg shadow p-6">
            <div className="text-red-600 text-center">
              <p>Error: {error}</p>
              <button 
                onClick={fetchFiles} 
                className="mt-4 bg-blue-500 text-white px-4 py-2 rounded hover:bg-blue-600"
              >
                Retry
              </button>
            </div>
          </div>
        </div>
      </Layout>
    );
  }

  return (
    <Layout>
      <div className="container mx-auto p-6">
        <div className="mb-6">
          <h1 className="text-3xl font-bold mb-2">File Preview</h1>
          <p className="text-gray-600">
            View and preview uploaded invoice files
          </p>
        </div>

        {files.length === 0 ? (
          <div className="bg-white rounded-lg shadow p-6">
            <div className="text-center text-gray-500">
              <div className="text-4xl mb-4">📄</div>
              <p>No files uploaded yet</p>
            </div>
          </div>
        ) : (
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {files.map((file) => (
              <div key={file.id} className="bg-white rounded-lg shadow hover:shadow-lg transition-shadow">
                <div className="p-4 border-b">
                  <div className="flex items-center justify-between">
                    <h3 className="text-lg font-semibold truncate">
                      {file.filename}
                    </h3>
                    <span className={`px-2 py-1 rounded-full text-xs font-medium ${getStatusColor(file.status)}`}>
                      {file.status}
                    </span>
                  </div>
                </div>
                <div className="p-4">
                  <div className="space-y-3">
                    <div className="flex items-center text-sm text-gray-600">
                      <span className="mr-2">📅</span>
                      {formatDate(file.upload_timestamp)}
                    </div>
                    
                    <div className="flex items-center text-sm text-gray-600">
                      <span className="mr-2">📄</span>
                      {file.invoice_number}
                    </div>
                    
                    <div className="text-sm text-gray-600">
                      <strong>Supplier:</strong> {file.supplier_name}
                    </div>
                    
                    <div className="flex items-center text-sm">
                      <span className="mr-2">💰</span>
                      <span className="font-semibold">
                        {formatCurrency(file.total_amount)}
                      </span>
                    </div>
                    
                    <div className="text-sm text-gray-500">
                      Confidence: {(file.confidence * 100).toFixed(1)}%
                    </div>
                    
                    <div className="flex gap-2 pt-2">
                      <button
                        onClick={() => handlePreview(file)}
                        className="flex-1 bg-blue-500 text-white px-3 py-2 rounded text-sm hover:bg-blue-600"
                      >
                        👁️ Preview
                      </button>
                      <button
                        onClick={() => window.open(`/api/files/${file.id}/preview`, '_blank')}
                        className="bg-gray-100 text-gray-700 px-3 py-2 rounded text-sm hover:bg-gray-200"
                      >
                        ⬇️
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}

        {selectedFile && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
            <div className="bg-white rounded-lg p-6 max-w-2xl w-full mx-4">
              <div className="flex justify-between items-center mb-4">
                <h3 className="text-lg font-semibold">Preview: {selectedFile.filename}</h3>
                <button
                  onClick={() => setSelectedFile(null)}
                  className="bg-gray-100 text-gray-700 px-3 py-2 rounded hover:bg-gray-200"
                >
                  Close
                </button>
              </div>
              <iframe
                src={`/api/files/${selectedFile.id}/preview`}
                className="w-full h-96 border rounded"
                title="File Preview"
              />
            </div>
          </div>
        )}
      </div>
    </Layout>
  );
} 