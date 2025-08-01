import React, { useState, useRef } from 'react';

// Inlined UI components for demo purposes
const Card = ({ children, className = "" }: { children: React.ReactNode; className?: string }) => (
  <div className={`bg-white rounded-lg shadow-md p-6 ${className}`}>
    {children}
  </div>
);

const Button = ({ 
  children, 
  onClick, 
  disabled = false, 
  variant = "primary",
  className = "" 
}: { 
  children: React.ReactNode; 
  onClick?: () => void; 
  disabled?: boolean;
  variant?: "primary" | "secondary" | "danger";
  className?: string;
}) => {
  const baseClasses = "px-4 py-2 rounded-md font-medium transition-colors";
  const variantClasses = {
    primary: "bg-blue-600 text-white hover:bg-blue-700 disabled:bg-gray-400",
    secondary: "bg-gray-200 text-gray-800 hover:bg-gray-300 disabled:bg-gray-100",
    danger: "bg-red-600 text-white hover:bg-red-700 disabled:bg-red-400"
  };
  
  return (
    <button 
      className={`${baseClasses} ${variantClasses[variant]} ${className}`}
      onClick={onClick}
      disabled={disabled}
    >
      {children}
    </button>
  );
};

const Badge = ({ 
  children, 
  variant = "default" 
}: { 
  children: React.ReactNode; 
  variant?: "default" | "success" | "warning" | "danger";
}) => {
  const baseClasses = "px-2 py-1 rounded-full text-xs font-medium";
  const variantClasses = {
    default: "bg-gray-100 text-gray-800",
    success: "bg-green-100 text-green-800",
    warning: "bg-yellow-100 text-yellow-800",
    danger: "bg-red-100 text-red-800"
  };
  
  return (
    <span className={`${baseClasses} ${variantClasses[variant]}`}>
      {children}
    </span>
  );
};

const Progress = ({ 
  value, 
  max = 100, 
  className = "" 
}: { 
  value: number; 
  max?: number; 
  className?: string;
}) => (
  <div className={`w-full bg-gray-200 rounded-full h-2 ${className}`}>
    <div 
      className="bg-blue-600 h-2 rounded-full transition-all duration-300"
      style={{ width: `${(value / max) * 100}%` }}
    />
  </div>
);

// Icons
const UploadIcon = () => (
  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
  </svg>
);

const FileTextIcon = () => (
  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
  </svg>
);

const CheckCircleIcon = () => (
  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
  </svg>
);

const AlertTriangleIcon = () => (
  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.732 16.5c-.77.833.192 2.5 1.732 2.5z" />
  </svg>
);

const XIcon = () => (
  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
  </svg>
);

// Interfaces
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

interface MatchingPanelProps {
  userRole?: 'viewer' | 'finance' | 'admin';
  onMatchingComplete?: (result: MatchingResult) => void;
}

const MatchingPanel: React.FC<MatchingPanelProps> = ({
  userRole = 'viewer',
  onMatchingComplete
}) => {
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [invoiceFile, setInvoiceFile] = useState<File | null>(null);
  const [deliveryFile, setDeliveryFile] = useState<File | null>(null);
  const [matchingResult, setMatchingResult] = useState<MatchingResult | null>(null);
  const [threshold, setThreshold] = useState(0.8);
  const [normalizeDescriptions, setNormalizeDescriptions] = useState(true);
  const [saveDebug, setSaveDebug] = useState(false);

  const invoiceInputRef = useRef<HTMLInputElement>(null);
  const deliveryInputRef = useRef<HTMLInputElement>(null);

  const handleInvoiceSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) {
      setInvoiceFile(file);
    }
  };

  const handleDeliverySelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) {
      setDeliveryFile(file);
    }
  };

  const handleFileRemove = (type: 'invoice' | 'delivery') => {
    if (type === 'invoice') {
      setInvoiceFile(null);
      if (invoiceInputRef.current) {
        invoiceInputRef.current.value = '';
      }
    } else {
      setDeliveryFile(null);
      if (deliveryInputRef.current) {
        deliveryInputRef.current.value = '';
      }
    }
  };

  const handleUpload = async () => {
    if (!invoiceFile || !deliveryFile) {
      alert('Please select both invoice and delivery note files');
      return;
    }

    setIsUploading(true);
    setUploadProgress(0);

    try {
      // Simulate upload progress
      const progressInterval = setInterval(() => {
        setUploadProgress(prev => {
          if (prev >= 90) {
            clearInterval(progressInterval);
            return 90;
          }
          return prev + 10;
        });
      }, 200);

      // Mock API call - replace with actual API call
      await new Promise(resolve => setTimeout(resolve, 2000));

      // Mock result
      const mockResult: MatchingResult = {
        matching_id: `match_${Date.now()}`,
        invoice_processing: {
          document_type: 'invoice',
          overall_confidence: 0.85,
          manual_review_required: false,
          processing_time: 1.2
        },
        delivery_processing: {
          document_type: 'delivery_note',
          overall_confidence: 0.78,
          manual_review_required: false,
          processing_time: 1.1
        },
        matching_results: {
          document_matching: {
            supplier_match: true,
            date_match: true,
            overall_confidence: 0.82
          },
          item_matching: {
            matched_items: [
              {
                invoice_description: 'Product A',
                delivery_description: 'Product A',
                similarity_score: 0.95,
                quantity_mismatch: false,
                price_mismatch: false
              },
              {
                invoice_description: 'Product B',
                delivery_description: 'Product B',
                similarity_score: 0.88,
                quantity_mismatch: true,
                price_mismatch: false,
                quantity_difference: 2
              }
            ],
            invoice_only_items: [
              {
                description: 'Product C',
                quantity: 5,
                unit_price: 10.50,
                total_price: 52.50
              }
            ],
            delivery_only_items: [
              {
                description: 'Product D',
                quantity: 3,
                unit: 'pcs'
              }
            ],
            total_matches: 2,
            total_discrepancies: 1,
            overall_confidence: 0.82
          },
          summary: {
            total_invoice_items: 3,
            total_delivery_items: 3,
            matched_percentage: 66.7,
            discrepancy_percentage: 50.0
          }
        },
        created_at: new Date().toISOString()
      };

      setMatchingResult(mockResult);
      onMatchingComplete?.(mockResult);
      setUploadProgress(100);

      setTimeout(() => {
        setUploadProgress(0);
      }, 1000);

    } catch (error) {
      console.error('Upload failed:', error);
      alert('Upload failed. Please try again.');
    } finally {
      setIsUploading(false);
    }
  };

  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 0.8) return 'success';
    if (confidence >= 0.6) return 'warning';
    return 'danger';
  };

  const getConfidenceIcon = (confidence: number) => {
    if (confidence >= 0.8) return <CheckCircleIcon />;
    return <AlertTriangleIcon />;
  };

  const canUpload = userRole !== 'viewer';

  return (
    <div className="space-y-6">
      {/* Upload Configuration */}
      <Card>
        <h3 className="text-lg font-semibold mb-4">Matching Configuration</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Matching Threshold
            </label>
            <input
              type="range"
              min="0.5"
              max="1.0"
              step="0.05"
              value={threshold}
              onChange={(e) => setThreshold(parseFloat(e.target.value))}
              className="w-full"
            />
            <div className="text-sm text-gray-500 mt-1">
              {Math.round(threshold * 100)}% similarity required
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Normalize Descriptions
            </label>
            <select
              value={normalizeDescriptions.toString()}
              onChange={(e) => setNormalizeDescriptions(e.target.value === 'true')}
              className="w-full px-3 py-2 border border-gray-300 rounded-md"
            >
              <option value="true">Yes</option>
              <option value="false">No</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Save Debug Artifacts
            </label>
            <select
              value={saveDebug.toString()}
              onChange={(e) => setSaveDebug(e.target.value === 'true')}
              className="w-full px-3 py-2 border border-gray-300 rounded-md"
            >
              <option value="false">No</option>
              <option value="true">Yes</option>
            </select>
          </div>
        </div>
      </Card>

      {/* File Upload */}
      <Card>
        <h3 className="text-lg font-semibold mb-4">Upload Documents</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Invoice Upload */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Invoice Document
            </label>
            <div className="border-2 border-dashed border-gray-300 rounded-lg p-4 text-center">
              {invoiceFile ? (
                <div className="space-y-2">
                  <FileTextIcon />
                  <p className="text-sm font-medium">{invoiceFile.name}</p>
                  <p className="text-xs text-gray-500">
                    {(invoiceFile.size / 1024 / 1024).toFixed(2)} MB
                  </p>
                  <Button
                    onClick={() => handleFileRemove('invoice')}
                    variant="danger"
                    className="text-xs"
                  >
                    <XIcon />
                    Remove
                  </Button>
                </div>
              ) : (
                <div className="space-y-2">
                  <UploadIcon />
                  <p className="text-sm text-gray-600">Click to select invoice file</p>
                  <Button
                    onClick={() => invoiceInputRef.current?.click()}
                    disabled={!canUpload}
                    className="text-xs"
                  >
                    Select File
                  </Button>
                  <input
                    ref={invoiceInputRef}
                    type="file"
                    accept=".pdf,.jpg,.jpeg,.png"
                    onChange={handleInvoiceSelect}
                    className="hidden"
                  />
                </div>
              )}
            </div>
          </div>

          {/* Delivery Note Upload */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Delivery Note
            </label>
            <div className="border-2 border-dashed border-gray-300 rounded-lg p-4 text-center">
              {deliveryFile ? (
                <div className="space-y-2">
                  <FileTextIcon />
                  <p className="text-sm font-medium">{deliveryFile.name}</p>
                  <p className="text-xs text-gray-500">
                    {(deliveryFile.size / 1024 / 1024).toFixed(2)} MB
                  </p>
                  <Button
                    onClick={() => handleFileRemove('delivery')}
                    variant="danger"
                    className="text-xs"
                  >
                    <XIcon />
                    Remove
                  </Button>
                </div>
              ) : (
                <div className="space-y-2">
                  <UploadIcon />
                  <p className="text-sm text-gray-600">Click to select delivery note file</p>
                  <Button
                    onClick={() => deliveryInputRef.current?.click()}
                    disabled={!canUpload}
                    className="text-xs"
                  >
                    Select File
                  </Button>
                  <input
                    ref={deliveryInputRef}
                    type="file"
                    accept=".pdf,.jpg,.jpeg,.png"
                    onChange={handleDeliverySelect}
                    className="hidden"
                  />
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Upload Button */}
        <div className="mt-6">
          <Button
            onClick={handleUpload}
            disabled={!canUpload || !invoiceFile || !deliveryFile || isUploading}
            className="w-full"
          >
            {isUploading ? 'Processing...' : 'Match Documents'}
          </Button>
        </div>

        {/* Progress Bar */}
        {isUploading && (
          <div className="mt-4">
            <div className="flex justify-between text-sm text-gray-600 mb-1">
              <span>Processing...</span>
              <span>{uploadProgress}%</span>
            </div>
            <Progress value={uploadProgress} />
          </div>
        )}
      </Card>

      {/* Results */}
      {matchingResult && (
        <Card>
          <h3 className="text-lg font-semibold mb-4">Matching Results</h3>
          
          {/* Document Processing Summary */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
            <div className="border rounded-lg p-4">
              <h4 className="font-medium mb-2">Invoice Processing</h4>
              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span>Confidence:</span>
                  <Badge variant={getConfidenceColor(matchingResult.invoice_processing.overall_confidence)}>
                    {Math.round(matchingResult.invoice_processing.overall_confidence * 100)}%
                  </Badge>
                </div>
                <div className="flex justify-between">
                  <span>Type:</span>
                  <span className="capitalize">{matchingResult.invoice_processing.document_type}</span>
                </div>
                <div className="flex justify-between">
                  <span>Processing Time:</span>
                  <span>{matchingResult.invoice_processing.processing_time}s</span>
                </div>
              </div>
            </div>

            <div className="border rounded-lg p-4">
              <h4 className="font-medium mb-2">Delivery Note Processing</h4>
              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span>Confidence:</span>
                  <Badge variant={getConfidenceColor(matchingResult.delivery_processing.overall_confidence)}>
                    {Math.round(matchingResult.delivery_processing.overall_confidence * 100)}%
                  </Badge>
                </div>
                <div className="flex justify-between">
                  <span>Type:</span>
                  <span className="capitalize">{matchingResult.delivery_processing.document_type}</span>
                </div>
                <div className="flex justify-between">
                  <span>Processing Time:</span>
                  <span>{matchingResult.delivery_processing.processing_time}s</span>
                </div>
              </div>
            </div>
          </div>

          {/* Document Matching */}
          <div className="border rounded-lg p-4 mb-6">
            <h4 className="font-medium mb-3">Document-Level Matching</h4>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
              <div className="flex items-center space-x-2">
                <span>Supplier Match:</span>
                <Badge variant={matchingResult.matching_results.document_matching.supplier_match ? 'success' : 'danger'}>
                  {matchingResult.matching_results.document_matching.supplier_match ? 'Yes' : 'No'}
                </Badge>
              </div>
              <div className="flex items-center space-x-2">
                <span>Date Match:</span>
                <Badge variant={matchingResult.matching_results.document_matching.date_match ? 'success' : 'danger'}>
                  {matchingResult.matching_results.document_matching.date_match ? 'Yes' : 'No'}
                </Badge>
              </div>
              <div className="flex items-center space-x-2">
                <span>Overall Confidence:</span>
                <Badge variant={getConfidenceColor(matchingResult.matching_results.document_matching.overall_confidence)}>
                  {Math.round(matchingResult.matching_results.document_matching.overall_confidence * 100)}%
                </Badge>
              </div>
            </div>
          </div>

          {/* Item Matching Summary */}
          <div className="border rounded-lg p-4 mb-6">
            <h4 className="font-medium mb-3">Item-Level Matching</h4>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
              <div className="text-center">
                <div className="text-2xl font-bold text-blue-600">
                  {matchingResult.matching_results.item_matching.total_matches}
                </div>
                <div className="text-gray-600">Matched Items</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-red-600">
                  {matchingResult.matching_results.item_matching.total_discrepancies}
                </div>
                <div className="text-gray-600">Discrepancies</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-gray-600">
                  {matchingResult.matching_results.item_matching.invoice_only_items.length}
                </div>
                <div className="text-gray-600">Invoice Only</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-gray-600">
                  {matchingResult.matching_results.item_matching.delivery_only_items.length}
                </div>
                <div className="text-gray-600">Delivery Only</div>
              </div>
            </div>
          </div>

          {/* Matched Items */}
          {matchingResult.matching_results.item_matching.matched_items.length > 0 && (
            <div className="border rounded-lg p-4 mb-6">
              <h4 className="font-medium mb-3">Matched Items</h4>
              <div className="space-y-3">
                {matchingResult.matching_results.item_matching.matched_items.map((item, index) => (
                  <div key={index} className="border rounded p-3">
                    <div className="flex justify-between items-start mb-2">
                      <div className="flex-1">
                        <div className="font-medium">{item.invoice_description}</div>
                        <div className="text-sm text-gray-600">{item.delivery_description}</div>
                      </div>
                      <div className="flex items-center space-x-2">
                        <Badge variant={getConfidenceColor(item.similarity_score)}>
                          {Math.round(item.similarity_score * 100)}%
                        </Badge>
                        {item.quantity_mismatch && (
                          <Badge variant="warning">Quantity Mismatch</Badge>
                        )}
                        {item.price_mismatch && (
                          <Badge variant="warning">Price Mismatch</Badge>
                        )}
                      </div>
                    </div>
                    {item.quantity_difference && (
                      <div className="text-sm text-red-600">
                        Quantity difference: {item.quantity_difference}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Unmatched Items */}
          {(matchingResult.matching_results.item_matching.invoice_only_items.length > 0 || 
            matchingResult.matching_results.item_matching.delivery_only_items.length > 0) && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {matchingResult.matching_results.item_matching.invoice_only_items.length > 0 && (
                <div className="border rounded-lg p-4">
                  <h4 className="font-medium mb-3 text-red-600">Invoice Only Items</h4>
                  <div className="space-y-2">
                    {matchingResult.matching_results.item_matching.invoice_only_items.map((item, index) => (
                      <div key={index} className="text-sm">
                        <div className="font-medium">{item.description}</div>
                        <div className="text-gray-600">
                          Qty: {item.quantity} | Price: £{item.unit_price}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {matchingResult.matching_results.item_matching.delivery_only_items.length > 0 && (
                <div className="border rounded-lg p-4">
                  <h4 className="font-medium mb-3 text-red-600">Delivery Only Items</h4>
                  <div className="space-y-2">
                    {matchingResult.matching_results.item_matching.delivery_only_items.map((item, index) => (
                      <div key={index} className="text-sm">
                        <div className="font-medium">{item.description}</div>
                        <div className="text-gray-600">
                          Qty: {item.quantity} {item.unit}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </Card>
      )}
    </div>
  );
};

export default MatchingPanel; 