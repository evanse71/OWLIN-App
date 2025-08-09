import React, { useState, useEffect } from 'react';
import Head from 'next/head';
import Link from 'next/link';
import UploadSection from '@/components/invoices/UploadSection';
import { apiService } from '@/services/api';

interface HealthCheck {
  status: string;
  backend_running: boolean;
  ocr_available: boolean;
}

const InvoicesPage: React.FC = () => {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [healthStatus, setHealthStatus] = useState<HealthCheck | null>(null);
  const [connectionError, setConnectionError] = useState<string | null>(null);
  const [documentsChanged, setDocumentsChanged] = useState(0);

  // Handle redirect for trailing slash
  useEffect(() => {
    if (window.location.pathname === '/invoices' && !window.location.pathname.endsWith('/')) {
      window.history.replaceState(null, '', '/invoices/');
    }
  }, []);

  // Check backend health on component mount
  useEffect(() => {
    const checkBackendHealth = async () => {
      try {
        const response = await fetch('http://localhost:8002/health');
        if (response.ok) {
          const health = await response.json();
          setHealthStatus({
            status: health.status || 'ok',
            backend_running: true,
            ocr_available: true,
          });
          setConnectionError(null);
        } else {
          throw new Error(`HTTP ${response.status}`);
        }
      } catch (error) {
        console.error('Backend health check failed:', error);
        setConnectionError('Cannot connect to backend');
        setHealthStatus({
          status: 'error',
          backend_running: false,
          ocr_available: false,
        });
      }
    };

    checkBackendHealth();
    
    // Check every 30 seconds
    const interval = setInterval(checkBackendHealth, 30000);
    
    return () => clearInterval(interval);
  }, []);

  if (connectionError) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <h1 className="text-2xl font-bold text-gray-900 mb-4">Connection Error</h1>
          <p className="text-red-600">Cannot connect to backend</p>
          <p className="text-red-600">Please check if the backend is running on port 8002</p>
          <button 
            onClick={() => window.location.reload()} 
            className="mt-4 px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600"
          >
            Retry Connection
          </button>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <h1 className="text-2xl font-bold text-gray-900 mb-4">Error</h1>
          <p className="text-red-600">Please check if the backend is running on port 8002</p>
          <button 
            onClick={() => window.location.reload()} 
            className="mt-4 px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  const handleDocumentsSubmitted = (documents: any[]) => {
    console.log('Documents submitted:', documents);
    setDocumentsChanged(prev => prev + 1);
  };

  return (
    <>
      <Head>
        <title>Invoice Management - OWLIN</title>
        <meta name="description" content="Upload and manage invoices with advanced OCR processing" />
      </Head>

      <div className="min-h-screen bg-gray-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          {/* Header */}
          <div className="mb-8">
            <div className="flex items-center justify-between">
              <div>
                <h1 className="text-3xl font-bold text-gray-900">Invoice Management</h1>
                <p className="text-gray-600 mt-1">Upload and process invoices with advanced OCR</p>
              </div>
              
              <div className="flex items-center space-x-4">
                {healthStatus && (
                  <div className={`px-3 py-1 rounded-full text-sm ${
                    healthStatus.backend_running 
                      ? 'bg-green-100 text-green-800' 
                      : 'bg-red-100 text-red-800'
                  }`}>
                    {healthStatus.backend_running ? '🟢 Backend Connected' : '🔴 Backend Offline'}
                  </div>
                )}
                
                <Link 
                  href="/" 
                  className="text-blue-600 hover:text-blue-500 font-medium"
                >
                  ← Back to Dashboard
                </Link>
              </div>
            </div>
          </div>

          {/* Upload Section */}
          <div className="bg-white rounded-lg shadow mb-8">
            <div className="p-6">
              <h2 className="text-xl font-semibold text-gray-900 mb-4">Upload Invoices</h2>
              <UploadSection onDocumentsSubmitted={handleDocumentsSubmitted} />
            </div>
          </div>

          {/* Status Section */}
          <div className="bg-white rounded-lg shadow">
            <div className="p-6">
              <h2 className="text-xl font-semibold text-gray-900 mb-4">Processing Status</h2>
              <p className="text-gray-600">
                Documents are processed with advanced OCR technology. 
                Results will appear here after processing completes.
              </p>
              {healthStatus?.backend_running && (
                <div className="mt-4 p-4 bg-green-50 border border-green-200 rounded-lg">
                  <p className="text-green-800 font-medium">✅ Advanced OCR Backend Active</p>
                  <p className="text-green-600 text-sm mt-1">
                    Ready for high-speed document processing with enhanced field extraction
                  </p>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </>
  );
};

export default InvoicesPage; 