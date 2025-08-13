import React, { useState } from 'react';
import AppShell from '@/components/layout/AppShell';
import MatchingPanel from '@/components/invoices/MatchingPanel';

interface MatchingResult {
  matching_id: string;
  invoice_processing: {
    document_type: string;
    overall_confidence: number;
    manual_review_required: boolean;
    processing_time: number;
  };
  delivery_processing: {
    document_type: string;
    overall_confidence: number;
    manual_review_required: boolean;
    processing_time: number;
  };
  matching_results: {
    document_matching: {
      supplier_match: boolean;
      date_match: boolean;
      overall_confidence: number;
    };
    item_matching: {
      matched_items: Array<{
        invoice_description: string;
        delivery_description: string;
        similarity_score: number;
        quantity_mismatch: boolean;
        price_mismatch: boolean;
        quantity_difference?: number;
        price_difference?: number;
      }>;
      invoice_only_items: Array<{
        description: string;
        quantity: number;
        unit_price: number;
        total_price: number;
      }>;
      delivery_only_items: Array<{
        description: string;
        quantity: number;
        unit: string;
      }>;
      total_matches: number;
      total_discrepancies: number;
      overall_confidence: number;
    };
    summary: {
      total_invoice_items: number;
      total_delivery_items: number;
      matched_percentage: number;
      discrepancy_percentage: number;
    };
  };
  created_at: string;
}

const MatchingDemo: React.FC = () => {
  const [userRole, setUserRole] = useState<'viewer' | 'finance' | 'admin'>('finance');
  const [matchingHistory, setMatchingHistory] = useState<MatchingResult[]>([]);

  const handleMatchingComplete = (result: MatchingResult) => {
    setMatchingHistory(prev => [result, ...prev]);
  };

  return (
    <AppShell>
      <div className="py-8">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">
            Invoice-Delivery Note Matching
          </h1>
          <p className="text-gray-600">
            Upload and match invoices with their corresponding delivery notes using advanced OCR and fuzzy matching.
          </p>
        </div>

        {/* User Role Selector */}
        <div className="mb-6">
          <label className="block text-sm font-medium text-gray-700 mb-2">
            User Role
          </label>
          <select
            value={userRole}
            onChange={(e) => setUserRole(e.target.value as 'viewer' | 'finance' | 'admin')}
            className="px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
          >
            <option value="viewer">Viewer (Read-only)</option>
            <option value="finance">Finance (Can upload and match)</option>
            <option value="admin">Admin (Full access)</option>
          </select>
        </div>

        {/* Main Content */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Matching Panel */}
          <div className="lg:col-span-2">
            <MatchingPanel
              userRole={userRole}
              onMatchingComplete={handleMatchingComplete}
            />
          </div>

          {/* Sidebar */}
          <div className="space-y-6">
            {/* Feature Overview */}
            <div className="bg-white rounded-lg shadow-md p-6">
              <h3 className="text-lg font-semibold mb-4">Feature Overview</h3>
              <div className="space-y-3 text-sm">
                <div className="flex items-start space-x-2">
                  <div className="w-2 h-2 bg-blue-500 rounded-full mt-2"></div>
                  <div>
                    <span className="font-medium">Fuzzy Matching:</span>
                    <p className="text-gray-600">Intelligent product description matching with configurable thresholds</p>
                  </div>
                </div>
                <div className="flex items-start space-x-2">
                  <div className="w-2 h-2 bg-green-500 rounded-full mt-2"></div>
                  <div>
                    <span className="font-medium">Discrepancy Detection:</span>
                    <p className="text-gray-600">Automatic detection of quantity and price mismatches</p>
                  </div>
                </div>
                <div className="flex items-start space-x-2">
                  <div className="w-2 h-2 bg-yellow-500 rounded-full mt-2"></div>
                  <div>
                    <span className="font-medium">Confidence Scoring:</span>
                    <p className="text-gray-600">Visual confidence indicators for all matching results</p>
                  </div>
                </div>
                <div className="flex items-start space-x-2">
                  <div className="w-2 h-2 bg-purple-500 rounded-full mt-2"></div>
                  <div>
                    <span className="font-medium">Role-Based Access:</span>
                    <p className="text-gray-600">Different permissions based on user role</p>
                  </div>
                </div>
              </div>
            </div>

            {/* Matching History */}
            {matchingHistory.length > 0 && (
              <div className="bg-white rounded-lg shadow-md p-6">
                <h3 className="text-lg font-semibold mb-4">Recent Matches</h3>
                <div className="space-y-3">
                  {matchingHistory.slice(0, 5).map((result, index) => (
                    <div key={index} className="border rounded p-3">
                      <div className="flex justify-between items-start mb-2">
                        <div>
                          <div className="font-medium text-sm">Match #{result.matching_id.slice(-6)}</div>
                          <div className="text-xs text-gray-500">
                            {new Date(result.created_at).toLocaleString()}
                          </div>
                        </div>
                        <div className="text-right">
                          <div className="text-sm font-medium">
                            {result.matching_results.summary.matched_percentage.toFixed(1)}% matched
                          </div>
                          <div className="text-xs text-gray-500">
                            {result.matching_results.item_matching.total_discrepancies} discrepancies
                          </div>
                        </div>
                      </div>
                      <div className="text-xs text-gray-600">
                        {result.matching_results.summary.total_invoice_items} invoice items • {result.matching_results.summary.total_delivery_items} delivery items
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Technical Details */}
            <div className="bg-white rounded-lg shadow-md p-6">
              <h3 className="text-lg font-semibold mb-4">Technical Details</h3>
              <div className="space-y-3 text-sm">
                <div>
                  <span className="font-medium">OCR Engine:</span>
                  <p className="text-gray-600">PaddleOCR primary with Tesseract fallback</p>
                </div>
                <div>
                  <span className="font-medium">Matching Algorithm:</span>
                  <p className="text-gray-600">Fuzzy string matching with SequenceMatcher</p>
                </div>
                <div>
                  <span className="font-medium">Confidence Thresholds:</span>
                  <p className="text-gray-600">Configurable from 50% to 100% similarity</p>
                </div>
                <div>
                  <span className="font-medium">Document Types:</span>
                  <p className="text-gray-600">PDF, JPG, JPEG, PNG supported</p>
                </div>
                <div>
                  <span className="font-medium">File Size Limit:</span>
                  <p className="text-gray-600">50MB maximum per file</p>
                </div>
              </div>
            </div>

            {/* API Endpoints */}
            <div className="bg-white rounded-lg shadow-md p-6">
              <h3 className="text-lg font-semibold mb-4">API Endpoints</h3>
              <div className="space-y-2 text-sm">
                <div className="bg-gray-50 p-2 rounded">
                  <div className="font-mono text-xs">
                    POST /api/matching/upload-pair
                  </div>
                  <div className="text-gray-600 text-xs mt-1">
                    Upload and match invoice + delivery note
                  </div>
                </div>
                <div className="bg-gray-50 p-2 rounded">
                  <div className="font-mono text-xs">
                    POST /api/matching/pair-existing
                  </div>
                  <div className="text-gray-600 text-xs mt-1">
                    Pair existing processed documents
                  </div>
                </div>
                <div className="bg-gray-50 p-2 rounded">
                  <div className="font-mono text-xs">
                    GET /api/matching/suggestions/{'{id}'}
                  </div>
                  <div className="text-gray-600 text-xs mt-1">
                    Get manual review suggestions
                  </div>
                </div>
                <div className="bg-gray-50 p-2 rounded">
                  <div className="font-mono text-xs">
                    GET /api/matching/validation/{'{id}'}
                  </div>
                  <div className="text-gray-600 text-xs mt-1">
                    Validate matching quality
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Usage Instructions */}
        <div className="mt-12 bg-blue-50 rounded-lg p-6">
          <h3 className="text-lg font-semibold mb-4 text-blue-900">How to Use</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <h4 className="font-medium mb-2 text-blue-800">1. Configure Matching</h4>
              <ul className="text-sm text-blue-700 space-y-1">
                <li>• Set matching threshold (50-100%)</li>
                <li>• Enable/disable description normalization</li>
                <li>• Choose whether to save debug artifacts</li>
              </ul>
            </div>
            <div>
              <h4 className="font-medium mb-2 text-blue-800">2. Upload Documents</h4>
              <ul className="text-sm text-blue-700 space-y-1">
                <li>• Select invoice document (PDF/image)</li>
                <li>• Select delivery note document (PDF/image)</li>
                <li>• Click &quot;Match Documents&quot; to process</li>
              </ul>
            </div>
            <div>
              <h4 className="font-medium mb-2 text-blue-800">3. Review Results</h4>
              <ul className="text-sm text-blue-700 space-y-1">
                <li>• Check document-level matching (supplier, date)</li>
                <li>• Review item-level matches and discrepancies</li>
                <li>• Identify invoice-only and delivery-only items</li>
              </ul>
            </div>
            <div>
              <h4 className="font-medium mb-2 text-blue-800">4. Take Action</h4>
              <ul className="text-sm text-blue-700 space-y-1">
                <li>• Resolve quantity/price discrepancies</li>
                <li>• Investigate unmatched items</li>
                <li>• Accept or reject matching results</li>
              </ul>
            </div>
          </div>
        </div>

        {/* Role Permissions */}
        <div className="mt-8 bg-gray-50 rounded-lg p-6">
          <h3 className="text-lg font-semibold mb-4">Role Permissions</h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="bg-white rounded p-4">
              <h4 className="font-medium mb-2">Viewer</h4>
              <ul className="text-sm text-gray-600 space-y-1">
                <li>• View matching results</li>
                <li>• Read-only access</li>
                <li>• Cannot upload documents</li>
              </ul>
            </div>
            <div className="bg-white rounded p-4">
              <h4 className="font-medium mb-2">Finance</h4>
              <ul className="text-sm text-gray-600 space-y-1">
                <li>• Upload and match documents</li>
                <li>• Review and resolve discrepancies</li>
                <li>• Accept/reject matching results</li>
              </ul>
            </div>
            <div className="bg-white rounded p-4">
              <h4 className="font-medium mb-2">Admin</h4>
              <ul className="text-sm text-gray-600 space-y-1">
                <li>• All Finance permissions</li>
                <li>• Configure matching thresholds</li>
                <li>• Access debug artifacts</li>
                <li>• Manage matching history</li>
              </ul>
            </div>
          </div>
        </div>
      </div>
    </AppShell>
  );
};

export default MatchingDemo; 