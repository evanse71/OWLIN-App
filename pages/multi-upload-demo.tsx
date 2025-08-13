import React, { useState } from 'react';
import AppShell from '@/components/layout/AppShell';
import MultiUploadPanel from '@/components/invoices/MultiUploadPanel';

interface FileUpload {
  file: File;
  id: string;
  status: 'pending' | 'processing' | 'success' | 'error' | 'warning';
  progress: number;
  message: string;
  validation?: any;
  processing?: any;
}

const MultiUploadDemo: React.FC = () => {
  const [userRole, setUserRole] = useState<'viewer' | 'finance' | 'admin'>('finance');
  const [uploadHistory, setUploadHistory] = useState<FileUpload[]>([]);
  const [showAdvanced, setShowAdvanced] = useState(false);

  const handleUploadComplete = (results: FileUpload[]) => {
    setUploadHistory(prev => [...results.filter(r => r.status === 'success' || r.status === 'warning'), ...prev]);
  };

  const getRolePermissions = (role: string) => {
    switch (role) {
      case 'admin':
        return ['Upload files', 'Process files', 'Clear completed uploads', 'View all details', 'Manage settings'];
      case 'finance':
        return ['Upload files', 'Process files', 'View validation details', 'Access upload history'];
      case 'viewer':
        return ['View upload status', 'Read-only access'];
      default:
        return [];
    }
  };

  return (
    <AppShell>
      <div className="py-8">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">Multi-File Upload Demo</h1>
          <p className="text-gray-600 mb-4">
            Comprehensive multi-file upload system with OCR processing, field extraction, and validation.
            This demo showcases batch invoice processing with real-time progress feedback.
          </p>
          
          {/* Role Selector */}
          <div className="flex items-center space-x-4 mb-6">
            <label className="text-sm font-medium text-gray-700">User Role:</label>
            <select
              value={userRole}
              onChange={(e) => setUserRole(e.target.value as any)}
              className="border border-gray-300 rounded-md px-3 py-1 text-sm"
            >
              <option value="viewer">Viewer</option>
              <option value="finance">Finance</option>
              <option value="admin">Admin</option>
            </select>
            <div className="text-sm text-gray-500">
              Permissions: {getRolePermissions(userRole).join(', ')}
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Main Upload Panel */}
          <div className="lg:col-span-2">
            <MultiUploadPanel
              userRole={userRole}
              onUploadComplete={handleUploadComplete}
              maxFileSize={50}
              maxFiles={10}
              supportedFormats={['pdf', 'jpg', 'jpeg', 'png', 'tiff']}
            />
          </div>

          {/* Sidebar */}
          <div className="space-y-6">
            {/* Feature Overview */}
            <div className="bg-white rounded-lg shadow-md p-6 border">
              <h3 className="text-lg font-medium text-gray-900 mb-4">Features</h3>
              <div className="space-y-3 text-sm">
                <div className="flex items-center space-x-2">
                  <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                  <span>Drag & drop file upload</span>
                </div>
                <div className="flex items-center space-x-2">
                  <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                  <span>Real-time progress tracking</span>
                </div>
                <div className="flex items-center space-x-2">
                  <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                  <span>OCR processing with field extraction</span>
                </div>
                <div className="flex items-center space-x-2">
                  <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                  <span>Duplicate detection (invoice & file hash)</span>
                </div>
                <div className="flex items-center space-x-2">
                  <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                  <span>File validation (type, size, format)</span>
                </div>
                <div className="flex items-center space-x-2">
                  <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                  <span>Descriptive naming generation</span>
                </div>
                <div className="flex items-center space-x-2">
                  <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                  <span>Role-based access control</span>
                </div>
                <div className="flex items-center space-x-2">
                  <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                  <span>Comprehensive error handling</span>
                </div>
              </div>
            </div>

            {/* Technical Details */}
            <div className="bg-white rounded-lg shadow-md p-6 border">
              <h3 className="text-lg font-medium text-gray-900 mb-4">Technical Details</h3>
              <div className="space-y-3 text-sm">
                <div>
                  <span className="font-medium">Supported Formats:</span>
                  <div className="text-gray-600 mt-1">PDF, JPG, JPEG, PNG, TIFF</div>
                </div>
                <div>
                  <span className="font-medium">Max File Size:</span>
                  <div className="text-gray-600 mt-1">50MB per file</div>
                </div>
                <div>
                  <span className="font-medium">Max Files:</span>
                  <div className="text-gray-600 mt-1">10 files per batch</div>
                </div>
                <div>
                  <span className="font-medium">Processing:</span>
                  <div className="text-gray-600 mt-1">OCR → Field Extraction → Validation → Storage</div>
                </div>
                <div>
                  <span className="font-medium">Validation:</span>
                  <div className="text-gray-600 mt-1">File type, size, duplicates, data integrity</div>
                </div>
              </div>
            </div>

            {/* API Endpoints */}
            <div className="bg-white rounded-lg shadow-md p-6 border">
              <h3 className="text-lg font-medium text-gray-900 mb-4">API Endpoints</h3>
              <div className="space-y-2 text-sm">
                <div>
                  <code className="bg-gray-100 px-2 py-1 rounded text-xs">
                    POST /api/validation/check
                  </code>
                  <div className="text-gray-600 mt-1">Main validation endpoint</div>
                </div>
                <div>
                  <code className="bg-gray-100 px-2 py-1 rounded text-xs">
                    POST /api/validation/quick-check
                  </code>
                  <div className="text-gray-600 mt-1">Fast validation without processing</div>
                </div>
                <div>
                  <code className="bg-gray-100 px-2 py-1 rounded text-xs">
                    POST /api/validation/check-duplicate
                  </code>
                  <div className="text-gray-600 mt-1">Check for duplicate invoice numbers</div>
                </div>
                <div>
                  <code className="bg-gray-100 px-2 py-1 rounded text-xs">
                    GET /api/validation/supported-formats
                  </code>
                  <div className="text-gray-600 mt-1">Get supported file formats</div>
                </div>
              </div>
            </div>

            {/* Advanced Options */}
            <div className="bg-white rounded-lg shadow-md p-6 border">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-medium text-gray-900">Advanced Options</h3>
                <button
                  onClick={() => setShowAdvanced(!showAdvanced)}
                  className="text-sm text-blue-600 hover:text-blue-800"
                >
                  {showAdvanced ? 'Hide' : 'Show'}
                </button>
              </div>
              
              {showAdvanced && (
                <div className="space-y-4 text-sm">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Max File Size (MB)
                    </label>
                    <input
                      type="number"
                      defaultValue={50}
                      className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Max Files per Batch
                    </label>
                    <input
                      type="number"
                      defaultValue={10}
                      className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Processing Timeout (seconds)
                    </label>
                    <input
                      type="number"
                      defaultValue={300}
                      className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm"
                    />
                  </div>
                  <div>
                    <label className="flex items-center">
                      <input type="checkbox" defaultChecked className="mr-2" />
                      <span className="text-sm">Enable debug logging</span>
                    </label>
                  </div>
                  <div>
                    <label className="flex items-center">
                      <input type="checkbox" defaultChecked className="mr-2" />
                      <span className="text-sm">Save processing artifacts</span>
                    </label>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Upload History */}
        {uploadHistory.length > 0 && (
          <div className="mt-8">
            <h2 className="text-2xl font-bold text-gray-900 mb-4">Upload History</h2>
            <div className="bg-white rounded-lg shadow-md border">
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        File Name
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Status
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Supplier
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Invoice #
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Size
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Processing Time
                      </th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {uploadHistory.map((upload) => (
                      <tr key={upload.id}>
                        <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                          {upload.file.name}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                            upload.status === 'success' ? 'bg-green-100 text-green-800' :
                            upload.status === 'warning' ? 'bg-yellow-100 text-yellow-800' :
                            'bg-red-100 text-red-800'
                          }`}>
                            {upload.status}
                          </span>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                          {upload.validation?.summary?.extracted_info?.supplier || 'N/A'}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                          {upload.validation?.summary?.extracted_info?.invoice_number || 'N/A'}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                          {(upload.file.size / (1024 * 1024)).toFixed(1)}MB
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                          {upload.processing?.processing_time ? 
                            `${upload.processing.processing_time.toFixed(1)}s` : 'N/A'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}

        {/* Documentation */}
        <div className="mt-8">
          <h2 className="text-2xl font-bold text-gray-900 mb-4">Documentation</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="bg-white rounded-lg shadow-md p-6 border">
              <h3 className="text-lg font-medium text-gray-900 mb-3">Usage Instructions</h3>
              <div className="space-y-2 text-sm text-gray-600">
                <p>1. Select files using the file picker or drag & drop</p>
                <p>2. Review the upload queue and file validation</p>
                <p>3. Click &quot;Process Files&quot; to start batch processing</p>
                <p>4. Monitor real-time progress and status updates</p>
                <p>5. Review validation results and warnings</p>
                <p>6. Access upload history for completed files</p>
              </div>
            </div>
            
            <div className="bg-white rounded-lg shadow-md p-6 border">
              <h3 className="text-lg font-medium text-gray-900 mb-3">Error Handling</h3>
              <div className="space-y-2 text-sm text-gray-600">
                <p>• Unsupported file types are rejected immediately</p>
                <p>• Files exceeding size limits show clear error messages</p>
                <p>• Duplicate detection provides warnings but allows upload</p>
                <p>• Processing failures are logged with detailed error info</p>
                <p>• Network issues trigger automatic retry logic</p>
                <p>• Invalid data is flagged but doesn&apos;t block processing</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </AppShell>
  );
};

export default MultiUploadDemo; 