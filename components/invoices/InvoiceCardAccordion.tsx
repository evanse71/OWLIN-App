import React, { useState } from 'react';
import { ChevronDown, ChevronUp, AlertTriangle, CheckCircle, Clock, FileText, Loader2, XCircle, Circle, Star, Bug, Eye, EyeOff } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import ConfidenceBadge from '@/components/common/ConfidenceBadge';
import LoadingSpinner from '@/components/common/LoadingSpinner';
import InvoiceLineItemTable from './InvoiceLineItemTable';
import { Invoice, DeliveryNote, LineItem } from '@/services/api';
import { apiService } from '@/services/api';

interface InvoiceCardAccordionProps {
  invoice: Invoice;
  isSelected?: boolean;
  onClick?: () => void;
  onExpand?: (id: string) => void;
}

interface DetailedInvoice extends Invoice {
  line_items?: LineItem[];
  delivery_note_match?: DeliveryNote | null;
  price_mismatches?: Array<{
    description: string;
    invoice_amount: number;
    delivery_amount: number;
    difference: number;
  }>;
  // VAT calculations
  subtotal?: number;
  vat?: number;
  vat_rate?: number;
  total_incl_vat?: number;
  // State-of-the-art additions
  quality_score?: number;
  processing_time?: number;
  extraction_method?: string;
  validation_passed?: boolean;
  quality_indicators?: Record<string, any>;
  engine_contributions?: Record<string, any>;
  factor_scores?: Record<string, number>;
  business_rule_compliance?: Record<string, boolean>;
  error_messages?: string[];
  // ✅ OCR Debug Information
  ocr_debug?: {
    preprocessing_steps?: Array<{
      step: string;
      status: 'success' | 'failed' | 'skipped';
      details?: string;
      processing_time?: number;
    }>;
    engine_results?: Array<{
      engine: string;
      status: 'success' | 'failed' | 'timeout';
      confidence: number;
      processing_time: number;
      text_extracted?: string;
      error_message?: string;
    }>;
    field_extraction?: Array<{
      field: string;
      status: 'success' | 'failed' | 'partial';
      value: string;
      confidence: number;
      extraction_method: string;
      error_message?: string;
    }>;
    validation_results?: Array<{
      rule: string;
      status: 'passed' | 'failed';
      details?: string;
    }>;
    segmentation_info?: {
      total_sections: number;
      sections_processed: number;
      multi_invoice_detected: boolean;
      section_details?: Array<{
        section_id: number;
        supplier_name: string;
        invoice_number: string;
        total_amount: number;
        confidence: number;
        status: 'success' | 'failed';
      }>;
    };
  };
}

const InvoiceCardAccordion: React.FC<InvoiceCardAccordionProps> = ({
  invoice,
  isSelected = false,
  onClick,
  onExpand,
}) => {
  const [detailedInvoice, setDetailedInvoice] = useState<DetailedInvoice | null>(null);
  const [isExpanded, setIsExpanded] = useState(false);
  const [isLoadingDetails, setIsLoadingDetails] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [flaggedIssuesCount, setFlaggedIssuesCount] = useState(0);
  // ✅ OCR Debug Panel State
  const [showOcrDebug, setShowOcrDebug] = useState(false);
  const [debugPanelExpanded, setDebugPanelExpanded] = useState<string | null>(null);

  const handleToggle = async () => {
    if (!isExpanded) {
      setIsLoadingDetails(true);
      setLoadError(null);
      
      try {
        const details = await fetchInvoiceDetails();
        setDetailedInvoice(details);
        setIsExpanded(true);
        onExpand?.(invoice.id);
      } catch (error) {
        console.error('Failed to load invoice details:', error);
        setLoadError('Failed to load invoice details');
      } finally {
        setIsLoadingDetails(false);
      }
    } else {
      setIsExpanded(false);
    }
  };

  const handleFieldEdit = (field: string, value: string) => {
    if (detailedInvoice) {
      setDetailedInvoice({
        ...detailedInvoice,
        [field]: value,
      });
    }
  };

  const handleSaveEdits = async () => {
    if (!detailedInvoice) return;
    
    try {
      // Update the invoice in the backend
      await fetch(`/api/invoices/${invoice.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(detailedInvoice),
      });
    } catch (error) {
      console.error('Failed to update invoice:', error);
    }
  };

  const fetchInvoiceDetails = async (): Promise<DetailedInvoice> => {
    const response = await fetch(`/api/invoices/${invoice.id}`);
    if (!response.ok) {
      throw new Error('Failed to fetch invoice details');
    }
    return response.json();
  };

  const formatDate = (dateString: string | undefined) => {
    if (!dateString || dateString === 'Unknown' || dateString === 'Unknown Date') {
      return 'Unknown Date';
    }
    try {
      const date = new Date(dateString);
      if (isNaN(date.getTime())) {
        return 'Invalid Date';
      }
      return date.toLocaleDateString('en-GB', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric',
      });
    } catch {
      return dateString;
    }
  };

  const formatCurrency = (amount: number | undefined) => {
    if (amount === undefined || amount === null) {
      return '£0.00';
    }
    return new Intl.NumberFormat('en-GB', {
      style: 'currency',
      currency: 'GBP',
    }).format(amount);
  };

  const formatVATRate = (rate: number | undefined) => {
    if (rate === undefined || rate === null) {
      return '0%';
    }
    return `${rate}%`;
  };

  const getStatusIcon = (status: string) => {
    switch (status?.toLowerCase()) {
      case 'completed':
        return <CheckCircle className="w-3 h-3" />;
      case 'processing':
        return <Loader2 className="w-3 h-3 animate-spin" />;
      case 'error':
        return <XCircle className="w-3 h-3" />;
      case 'flagged':
        return <AlertTriangle className="w-3 h-3" />;
      default:
        return <Circle className="w-3 h-3" />;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status?.toLowerCase()) {
      case 'completed':
        return 'bg-green-100 text-green-800 border-green-200';
      case 'processing':
        return 'bg-blue-100 text-blue-800 border-blue-200';
      case 'error':
        return 'bg-red-100 text-red-800 border-red-200';
      case 'flagged':
        return 'bg-orange-100 text-orange-800 border-orange-200';
      default:
        return 'bg-gray-100 text-gray-800 border-gray-200';
    }
  };

  const getStatusLabel = (status: string) => {
    switch (status?.toLowerCase()) {
      case 'completed':
        return 'Completed';
      case 'processing':
        return 'Processing';
      case 'error':
        return 'Error';
      case 'flagged':
        return 'Flagged';
      default:
        return 'Unknown';
    }
  };

  // Enhanced confidence display with quality indicators
  const renderConfidenceDisplay = () => {
    const confidence = Math.round((invoice.confidence || 0) * 100);
    const qualityScore = Math.round(((invoice as any).quality_score || 0) * 100);
    
    return (
      <div className="flex flex-col space-y-2">
        <div className="flex items-center justify-between">
          <span className="text-sm font-medium text-slate-700">OCR Confidence</span>
          <span className="text-sm font-bold text-slate-900">{confidence}%</span>
        </div>
        {(invoice as any).quality_score !== undefined && (
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium text-slate-700">Quality Score</span>
            <span className="text-sm font-bold text-slate-900">{qualityScore}%</span>
          </div>
        )}
        <div className="w-full bg-slate-200 rounded-full h-2">
          <div 
            className="bg-blue-600 h-2 rounded-full transition-all duration-300"
            style={{ width: `${confidence}%` }}
          />
        </div>
      </div>
    );
  };

  // Enhanced quality indicators display
  const renderQualityIndicators = () => {
    if (!detailedInvoice?.quality_indicators) return null;
    
    const indicators = detailedInvoice.quality_indicators;
    
    return (
      <div className="space-y-3">
        <h4 className="font-semibold text-slate-900">Quality Indicators</h4>
        <div className="grid grid-cols-2 gap-3">
          {Object.entries(indicators).map(([key, value]) => (
            <div key={key} className="flex items-center justify-between">
              <span className="text-sm text-slate-600 capitalize">
                {key.replace(/_/g, ' ')}
              </span>
              <span className="text-sm font-medium text-slate-900">
                {typeof value === 'number' ? `${Math.round(value * 100)}%` : String(value)}
              </span>
            </div>
          ))}
        </div>
      </div>
    );
  };

  // Enhanced engine contributions display
  const renderEngineContributions = () => {
    if (!detailedInvoice?.engine_contributions) return null;
    
    const contributions = detailedInvoice.engine_contributions;
    
    return (
      <div className="space-y-3">
        <h4 className="font-semibold text-slate-900">OCR Engine Contributions</h4>
        <div className="space-y-2">
          {Object.entries(contributions).map(([engine, data]) => (
            <div key={engine} className="flex items-center justify-between p-2 bg-slate-50 rounded">
              <span className="text-sm font-medium text-slate-700 capitalize">
                {engine}
              </span>
              <div className="flex items-center space-x-3">
                <span className="text-sm text-slate-600">
                  {Math.round((data.confidence || 0) * 100)}%
                </span>
                <span className="text-xs text-slate-500">
                  {data.processing_time?.toFixed(2)}s
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  };

  // Enhanced factor scores display
  const renderFactorScores = () => {
    if (!detailedInvoice?.factor_scores) return null;
    
    const scores = detailedInvoice.factor_scores;
    
    return (
      <div className="space-y-3">
        <h4 className="font-semibold text-slate-900">Confidence Factors</h4>
        <div className="space-y-2">
          {Object.entries(scores).map(([factor, score]) => (
            <div key={factor} className="flex items-center justify-between">
              <span className="text-sm text-slate-600 capitalize">
                {factor.replace(/_/g, ' ')}
              </span>
              <span className="text-sm font-medium text-slate-900">
                {Math.round(score * 100)}%
              </span>
            </div>
          ))}
        </div>
      </div>
    );
  };

  // Enhanced business rule compliance display
  const renderBusinessRuleCompliance = () => {
    if (!detailedInvoice?.business_rule_compliance) return null;
    
    const compliance = detailedInvoice.business_rule_compliance;
    
    return (
      <div className="space-y-3">
        <h4 className="font-semibold text-slate-900">Business Rule Compliance</h4>
        <div className="space-y-2">
          {Object.entries(compliance).map(([field, passed]) => (
            <div key={field} className="flex items-center justify-between">
              <span className="text-sm text-slate-600 capitalize">
                {field.replace(/_/g, ' ')}
              </span>
              <div className="flex items-center space-x-2">
                {passed ? (
                  <CheckCircle className="w-4 h-4 text-green-600" />
                ) : (
                  <XCircle className="w-4 h-4 text-red-600" />
                )}
                <span className="text-sm font-medium text-slate-900">
                  {passed ? 'Passed' : 'Failed'}
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  };

  // Enhanced error messages display
  const renderErrorMessages = () => {
    if (!detailedInvoice?.error_messages || detailedInvoice.error_messages.length === 0) return null;
    
    return (
      <div className="space-y-3">
        <h4 className="font-semibold text-red-900">Processing Errors</h4>
        <div className="space-y-2">
          {detailedInvoice.error_messages.map((error, index) => (
            <div key={index} className="p-3 bg-red-50 border border-red-200 rounded">
              <span className="text-sm text-red-800">{error}</span>
            </div>
          ))}
        </div>
      </div>
    );
  };

  // ✅ OCR Debug Panel Functions
  const renderOcrDebugPanel = () => {
    if (!detailedInvoice?.ocr_debug) return null;

    const debug = detailedInvoice.ocr_debug;

    return (
      <div className="border-t border-slate-200 pt-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-slate-900">🔍 OCR Processing Debug</h3>
          <button
            onClick={() => setShowOcrDebug(!showOcrDebug)}
            className="flex items-center space-x-2 px-3 py-1 text-sm font-medium text-slate-600 bg-slate-100 hover:bg-slate-200 rounded-lg transition-colors"
          >
            {showOcrDebug ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
            <span>{showOcrDebug ? 'Hide' : 'Show'} Debug Info</span>
          </button>
        </div>

        {showOcrDebug && (
          <div className="space-y-4">
            {/* Preprocessing Steps */}
            {debug.preprocessing_steps && debug.preprocessing_steps.length > 0 && (
              <div className="bg-slate-50 rounded-lg p-4">
                <h4 className="font-semibold text-slate-900 mb-3">🔄 Preprocessing Steps</h4>
                <div className="space-y-2">
                  {debug.preprocessing_steps.map((step, index) => (
                    <div key={index} className="flex items-center justify-between p-2 bg-white rounded border">
                      <div className="flex items-center space-x-2">
                        {step.status === 'success' && <CheckCircle className="w-4 h-4 text-green-600" />}
                        {step.status === 'failed' && <XCircle className="w-4 h-4 text-red-600" />}
                        {step.status === 'skipped' && <Circle className="w-4 h-4 text-gray-400" />}
                        <span className="text-sm font-medium text-slate-700">{step.step}</span>
                      </div>
                      <div className="flex items-center space-x-2 text-xs text-slate-500">
                        {step.processing_time && <span>{step.processing_time.toFixed(2)}s</span>}
                        <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                          step.status === 'success' ? 'bg-green-100 text-green-800' :
                          step.status === 'failed' ? 'bg-red-100 text-red-800' :
                          'bg-gray-100 text-gray-800'
                        }`}>
                          {step.status}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* OCR Engine Results */}
            {debug.engine_results && debug.engine_results.length > 0 && (
              <div className="bg-slate-50 rounded-lg p-4">
                <h4 className="font-semibold text-slate-900 mb-3">🤖 OCR Engine Results</h4>
                <div className="space-y-2">
                  {debug.engine_results.map((engine, index) => (
                    <div key={index} className="p-3 bg-white rounded border">
                      <div className="flex items-center justify-between mb-2">
                        <div className="flex items-center space-x-2">
                          {engine.status === 'success' && <CheckCircle className="w-4 h-4 text-green-600" />}
                          {engine.status === 'failed' && <XCircle className="w-4 h-4 text-red-600" />}
                          {engine.status === 'timeout' && <Clock className="w-4 h-4 text-orange-600" />}
                          <span className="font-medium text-slate-700">{engine.engine}</span>
                        </div>
                        <div className="flex items-center space-x-2 text-xs">
                          <span>{Math.round(engine.confidence * 100)}%</span>
                          <span>{engine.processing_time.toFixed(2)}s</span>
                          <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                            engine.status === 'success' ? 'bg-green-100 text-green-800' :
                            engine.status === 'failed' ? 'bg-red-100 text-red-800' :
                            'bg-orange-100 text-orange-800'
                          }`}>
                            {engine.status}
                          </span>
                        </div>
                      </div>
                      {engine.error_message && (
                        <div className="text-xs text-red-600 bg-red-50 p-2 rounded">
                          {engine.error_message}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Field Extraction Results */}
            {debug.field_extraction && debug.field_extraction.length > 0 && (
              <div className="bg-slate-50 rounded-lg p-4">
                <h4 className="font-semibold text-slate-900 mb-3">📝 Field Extraction</h4>
                <div className="space-y-2">
                  {debug.field_extraction.map((field, index) => (
                    <div key={index} className="p-3 bg-white rounded border">
                      <div className="flex items-center justify-between mb-2">
                        <div className="flex items-center space-x-2">
                          {field.status === 'success' && <CheckCircle className="w-4 h-4 text-green-600" />}
                          {field.status === 'failed' && <XCircle className="w-4 h-4 text-red-600" />}
                          {field.status === 'partial' && <AlertTriangle className="w-4 h-4 text-orange-600" />}
                          <span className="font-medium text-slate-700">{field.field}</span>
                        </div>
                        <div className="flex items-center space-x-2 text-xs">
                          <span>{Math.round(field.confidence * 100)}%</span>
                          <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                            field.status === 'success' ? 'bg-green-100 text-green-800' :
                            field.status === 'failed' ? 'bg-red-100 text-red-800' :
                            'bg-orange-100 text-orange-800'
                          }`}>
                            {field.status}
                          </span>
                        </div>
                      </div>
                      <div className="text-xs text-slate-600">
                        <div><strong>Value:</strong> {field.value || 'None'}</div>
                        <div><strong>Method:</strong> {field.extraction_method}</div>
                        {field.error_message && (
                          <div className="text-red-600 mt-1">{field.error_message}</div>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Validation Results */}
            {debug.validation_results && debug.validation_results.length > 0 && (
              <div className="bg-slate-50 rounded-lg p-4">
                <h4 className="font-semibold text-slate-900 mb-3">✅ Validation Results</h4>
                <div className="space-y-2">
                  {debug.validation_results.map((rule, index) => (
                    <div key={index} className="flex items-center justify-between p-2 bg-white rounded border">
                      <div className="flex items-center space-x-2">
                        {rule.status === 'passed' && <CheckCircle className="w-4 h-4 text-green-600" />}
                        {rule.status === 'failed' && <XCircle className="w-4 h-4 text-red-600" />}
                        <span className="text-sm font-medium text-slate-700">{rule.rule}</span>
                      </div>
                      <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                        rule.status === 'passed' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
                      }`}>
                        {rule.status}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Segmentation Info */}
            {debug.segmentation_info && (
              <div className="bg-slate-50 rounded-lg p-4">
                <h4 className="font-semibold text-slate-900 mb-3">📄 Document Segmentation</h4>
                <div className="space-y-3">
                  <div className="grid grid-cols-2 gap-4 text-sm">
                    <div>
                      <span className="font-medium text-slate-600">Total Sections:</span>
                      <span className="ml-2 text-slate-900">{debug.segmentation_info.total_sections}</span>
                    </div>
                    <div>
                      <span className="font-medium text-slate-600">Processed:</span>
                      <span className="ml-2 text-slate-900">{debug.segmentation_info.sections_processed}</span>
                    </div>
                    <div>
                      <span className="font-medium text-slate-600">Multi-Invoice:</span>
                      <span className="ml-2 text-slate-900">{debug.segmentation_info.multi_invoice_detected ? 'Yes' : 'No'}</span>
                    </div>
                  </div>
                  
                  {debug.segmentation_info.section_details && debug.segmentation_info.section_details.length > 0 && (
                    <div>
                      <h5 className="font-medium text-slate-700 mb-2">Section Details:</h5>
                      <div className="space-y-2">
                        {debug.segmentation_info.section_details.map((section, index) => (
                          <div key={index} className="p-2 bg-white rounded border text-xs">
                            <div className="flex items-center justify-between mb-1">
                              <span className="font-medium">Section {section.section_id}</span>
                              <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                                section.status === 'success' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
                              }`}>
                                {section.status}
                              </span>
                            </div>
                            <div className="grid grid-cols-2 gap-2 text-xs text-slate-600">
                              <div>Supplier: {section.supplier_name}</div>
                              <div>Invoice: {section.invoice_number}</div>
                              <div>Total: {formatCurrency(section.total_amount)}</div>
                              <div>Confidence: {Math.round(section.confidence * 100)}%</div>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="space-y-4">
      {/* Main Card */}
      <motion.div
        layout
        className={`
          relative bg-white rounded-2xl border-2 shadow-sm hover:shadow-md transition-all duration-200 cursor-pointer
          ${isSelected ? 'border-blue-500 bg-blue-50' : 'border-slate-200 hover:border-slate-300'}
        `}
        onClick={onClick}
      >
        <div className="p-6">
          {/* Top Row - Supplier and Amount */}
          <div className="flex items-start justify-between mb-4">
            <div className="flex-1 min-w-0">
              <div className="flex items-center space-x-2 mb-2">
                <h3 className="font-semibold text-slate-900 truncate">
                  {invoice?.supplier_name || 'Unknown Supplier'}
                </h3>
                {(invoice as any)?.validation_passed && (
                  <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-green-100 text-green-800">
                    <CheckCircle className="w-3 h-3 mr-1" />
                    Validated
                  </span>
                )}
              </div>
              <div className="text-sm text-slate-600 mb-2">
                {formatDate(invoice?.invoice_date)}
              </div>
              <div className="flex items-center space-x-2">
                <span className="text-sm text-slate-500">Invoice:</span>
                <span className="text-sm font-medium text-slate-700">
                  {invoice?.invoice_number || 'No Invoice #'}
                </span>
              </div>
            </div>
            
            {/* ✅ Enhanced Confidence Badge (always visible, top-right) */}
            {invoice?.confidence !== undefined && (
              <div className="absolute top-2 right-2 z-10">
                <ConfidenceBadge confidence={Math.round((invoice.confidence || 0) * 100)} />
              </div>
            )}
          </div>
          
          <span className="text-sm text-gray-500 truncate mt-1">
            {invoice?.parent_pdf_filename || invoice?.invoice_number || invoice?.id?.slice(0, 8) + '...' || 'Unknown'}
          </span>
        </div>
        
        <div className="text-right">
          <div className="font-bold text-slate-900 text-lg">
            {formatCurrency(invoice?.total_amount)}
          </div>
          <div className="text-xs text-slate-500">
            {invoice?.invoice_number || 'No Invoice #'}
          </div>
        </div>
      </motion.div>

      {/* Bottom Row - Status and Badges */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-2">
          {/* Status Badge */}
          <div className={`
            inline-flex items-center space-x-1 px-2 py-1 rounded-full text-xs font-medium border
            ${getStatusColor(invoice?.status)}
          `}>
            {getStatusIcon(invoice?.status)}
            <span>{getStatusLabel(invoice?.status)}</span>
          </div>

          {/* Quality Score Badge */}
          {(invoice as any)?.quality_score !== undefined && (
            <div className="inline-flex items-center space-x-1 px-2 py-1 rounded-full text-xs font-medium bg-purple-100 text-purple-800 border border-purple-200">
              <Star className="w-3 h-3" />
              <span>Quality: {Math.round(((invoice as any).quality_score || 0) * 100)}%</span>
            </div>
          )}

          {/* Manual Review Badge for low confidence */}
          {invoice?.confidence !== undefined && (invoice.confidence || 0) * 100 < 40 && (
            <div className="inline-flex items-center space-x-1 px-2 py-1 rounded-full text-xs font-medium bg-orange-100 text-orange-800 border border-orange-200">
              <AlertTriangle className="w-3 h-3" />
              <span>Manual review</span>
            </div>
          )}

          {/* Flagged Issues Badge */}
          {flaggedIssuesCount > 0 && (
            <div className="inline-flex items-center space-x-1 px-2 py-1 rounded-full text-xs font-medium bg-red-100 text-red-800 border border-red-200">
              <AlertTriangle className="w-3 h-3" />
              <span>{flaggedIssuesCount} flagged</span>
            </div>
          )}
        </div>
        
        {/* Loading indicator for OCR processing */}
        {invoice?.status === 'processing' && (
          <div className="flex items-center space-x-2 text-xs text-slate-500">
            <div className="animate-spin rounded-full h-3 w-3 border-b-2 border-blue-600"></div>
            <span>Processing...</span>
          </div>
        )}
      </div>

      {/* Enhanced Expand/Collapse Button */}
      <div className="flex justify-center">
        <button
          onClick={handleToggle}
          className="inline-flex items-center space-x-2 px-4 py-2 text-sm font-medium text-slate-700 bg-slate-100 hover:bg-slate-200 rounded-lg transition-colors duration-200"
        >
          {isExpanded ? (
            <>
              <ChevronUp className="w-4 h-4" />
              <span>Hide Details</span>
            </>
          ) : (
            <>
              <ChevronDown className="w-4 h-4" />
              <span>Show Details</span>
            </>
          )}
        </button>
      </div>

      {/* Enhanced Expanded Content */}
      <AnimatePresence>
        {isExpanded && (
          <motion.div
            id={`invoice-details-${invoice.id}`}
            initial={{ opacity: 0, height: 0, scale: 0.95 }}
            animate={{ opacity: 1, height: 'auto', scale: 1 }}
            exit={{ opacity: 0, height: 0, scale: 0.95 }}
            transition={{ duration: 0.3, ease: 'easeInOut' }}
            className="overflow-hidden"
          >
            <div className="rounded-2xl bg-slate-50 border border-slate-200 p-6 mb-4">
              {/* ✅ Enhanced Loading State */}
              {isLoadingDetails && (
                <div className="flex flex-col items-center justify-center py-12">
                  <LoadingSpinner size="lg" color="blue" className="mb-4" />
                  <p className="text-slate-600 text-center">
                    Loading invoice details...
                  </p>
                  <p className="text-sm text-slate-500 text-center mt-1">
                    Fetching line items and quality indicators
                  </p>
                </div>
              )}

              {/* ✅ Error State */}
              {loadError && (
                <div className="flex flex-col items-center justify-center py-12">
                  <AlertTriangle className="w-12 h-12 text-red-500 mb-4" />
                  <p className="text-red-600 text-center font-medium">
                    Failed to load invoice details
                  </p>
                  <p className="text-sm text-red-500 text-center mt-1">
                    {loadError}
                  </p>
                  <button
                    onClick={handleToggle}
                    className="mt-4 px-4 py-2 text-sm font-medium text-white bg-red-600 hover:bg-red-700 rounded-lg transition-colors duration-200"
                  >
                    Retry
                  </button>
                </div>
              )}

              {/* ✅ Enhanced Content Display */}
              {detailedInvoice && !isLoadingDetails && !loadError && (
                <div className="space-y-6">
                  {/* Basic Information */}
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div className="space-y-4">
                      <h3 className="text-lg font-semibold text-slate-900">Invoice Information</h3>
                      
                      <div className="space-y-3">
                        <div className="flex justify-between">
                          <span className="text-sm font-medium text-slate-600">Supplier</span>
                          <span className="text-sm text-slate-900">{detailedInvoice.supplier_name}</span>
                        </div>
                        
                        <div className="flex justify-between">
                          <span className="text-sm font-medium text-slate-600">Invoice Number</span>
                          <span className="text-sm text-slate-900">{detailedInvoice.invoice_number}</span>
                        </div>
                        
                        <div className="flex justify-between">
                          <span className="text-sm font-medium text-slate-600">Date</span>
                          <span className="text-sm text-slate-900">{formatDate(detailedInvoice.invoice_date)}</span>
                        </div>
                        
                        <div className="flex justify-between">
                          <span className="text-sm font-medium text-slate-600">Total Amount</span>
                          <span className="text-sm font-bold text-slate-900">{formatCurrency(detailedInvoice.total_amount)}</span>
                        </div>
                      </div>
                    </div>

                    <div className="space-y-4">
                      <h3 className="text-lg font-semibold text-slate-900">Processing Information</h3>
                      
                      <div className="space-y-3">
                        <div className="flex justify-between">
                          <span className="text-sm font-medium text-slate-600">Processing Time</span>
                          <span className="text-sm text-slate-900">
                            {detailedInvoice.processing_time?.toFixed(2)}s
                          </span>
                        </div>
                        
                        <div className="flex justify-between">
                          <span className="text-sm font-medium text-slate-600">Extraction Method</span>
                          <span className="text-sm text-slate-900 capitalize">
                            {detailedInvoice.extraction_method?.replace(/_/g, ' ') || 'Unknown'}
                          </span>
                        </div>
                        
                        <div className="flex justify-between">
                          <span className="text-sm font-medium text-slate-600">Validation Status</span>
                          <span className={`text-sm font-medium ${
                            detailedInvoice.validation_passed ? 'text-green-600' : 'text-red-600'
                          }`}>
                            {detailedInvoice.validation_passed ? 'Passed' : 'Failed'}
                          </span>
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Enhanced Confidence Display */}
                  <div className="border-t border-slate-200 pt-6">
                    <h3 className="text-lg font-semibold text-slate-900 mb-4">Confidence Analysis</h3>
                    {renderConfidenceDisplay()}
                  </div>

                  {/* Quality Indicators */}
                  {detailedInvoice.quality_indicators && (
                    <div className="border-t border-slate-200 pt-6">
                      {renderQualityIndicators()}
                    </div>
                  )}

                  {/* Engine Contributions */}
                  {detailedInvoice.engine_contributions && (
                    <div className="border-t border-slate-200 pt-6">
                      {renderEngineContributions()}
                    </div>
                  )}

                  {/* Factor Scores */}
                  {detailedInvoice.factor_scores && (
                    <div className="border-t border-slate-200 pt-6">
                      {renderFactorScores()}
                    </div>
                  )}

                  {/* Business Rule Compliance */}
                  {detailedInvoice.business_rule_compliance && (
                    <div className="border-t border-slate-200 pt-6">
                      {renderBusinessRuleCompliance()}
                    </div>
                  )}

                  {/* Error Messages */}
                  {detailedInvoice.error_messages && detailedInvoice.error_messages.length > 0 && (
                    <div className="border-t border-slate-200 pt-6">
                      {renderErrorMessages()}
                    </div>
                  )}

                  {/* ✅ OCR Debug Panel */}
                  {renderOcrDebugPanel()}

                  {/* Line Items */}
                  {detailedInvoice.line_items && detailedInvoice.line_items.length > 0 && (
                    <div className="border-t border-slate-200 pt-6">
                      <h3 className="text-lg font-semibold text-slate-900 mb-4">Line Items</h3>
                      <InvoiceLineItemTable items={detailedInvoice.line_items} />
                    </div>
                  )}

                  {/* VAT Calculations */}
                  {(detailedInvoice.subtotal || detailedInvoice.vat || detailedInvoice.total_incl_vat) && (
                    <div className="border-t border-slate-200 pt-6">
                      <h3 className="text-lg font-semibold text-slate-900 mb-4">VAT Breakdown</h3>
                      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                        {detailedInvoice.subtotal && (
                          <div className="text-center p-4 bg-slate-100 rounded-lg">
                            <div className="text-sm text-slate-600">Subtotal</div>
                            <div className="text-lg font-bold text-slate-900">{formatCurrency(detailedInvoice.subtotal)}</div>
                          </div>
                        )}
                        {detailedInvoice.vat && (
                          <div className="text-center p-4 bg-slate-100 rounded-lg">
                            <div className="text-sm text-slate-600">VAT ({formatVATRate(detailedInvoice.vat_rate)})</div>
                            <div className="text-lg font-bold text-slate-900">{formatCurrency(detailedInvoice.vat)}</div>
                          </div>
                        )}
                        {detailedInvoice.total_incl_vat && (
                          <div className="text-center p-4 bg-blue-100 rounded-lg">
                            <div className="text-sm text-blue-600">Total (inc. VAT)</div>
                            <div className="text-lg font-bold text-blue-900">{formatCurrency(detailedInvoice.total_incl_vat)}</div>
                          </div>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

export default InvoiceCardAccordion; 