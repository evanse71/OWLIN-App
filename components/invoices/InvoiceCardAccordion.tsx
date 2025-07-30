import React, { useState } from 'react';
import { ChevronDown, ChevronUp, AlertTriangle, CheckCircle, Clock, FileText } from 'lucide-react';
import ConfidenceBadge from '@/components/common/ConfidenceBadge';
import LoadingSpinner from '@/components/common/LoadingSpinner';
import InvoiceLineItemTable from '@/components/invoices/InvoiceLineItemTable';
import { motion, AnimatePresence } from 'framer-motion';
import { Invoice, DeliveryNote } from '@/services/api';
import { apiService } from '@/services/api';

interface InvoiceCardAccordionProps {
  invoice: Invoice;
  deliveryNote?: DeliveryNote | null; // optional external selection control
  isSelected?: boolean;
  onExpand?: (id: string) => void; // optional callback when expanded
  onClick?: () => void; // Added for opening detail drawer
}

interface DetailedInvoice extends Invoice {
  line_items?: Array<{
    description: string;
    quantity: number;
    unit_price?: number;
    total_price?: number;
    unit_price_excl_vat?: number;
    unit_price_incl_vat?: number;
    line_total_excl_vat?: number;
    line_total_incl_vat?: number;
    flagged?: boolean;
  }>;
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
}

const InvoiceCardAccordion: React.FC<InvoiceCardAccordionProps> = ({
  invoice,
  deliveryNote,
  isSelected = false,
  onExpand,
  onClick,
}) => {
  const [isExpanded, setIsExpanded] = useState(false);
  const [detailedInvoice, setDetailedInvoice] = useState<DetailedInvoice | null>(null);
  const [isLoadingDetails, setIsLoadingDetails] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [editingFields, setEditingFields] = useState<{[key: string]: string}>({});

  const handleToggle = async () => {
    const newExpandedState = !isExpanded;
    setIsExpanded(newExpandedState);
    
    if (newExpandedState && onExpand) {
      onExpand(invoice.id);
    }

    // ✅ Fetch detailed invoice data when expanding
    if (newExpandedState && !detailedInvoice && !isLoadingDetails) {
      await fetchInvoiceDetails();
    }

    // If an onClick handler is provided, call it when the card is clicked
    if (onClick) {
      onClick();
    }
  };

  // ✅ Handle field editing for low confidence invoices
  const handleFieldEdit = (field: string, value: string) => {
    setEditingFields(prev => ({
      ...prev,
      [field]: value
    }));
  };

  // ✅ Save edited fields
  const handleSaveEdits = async () => {
    try {
      // TODO: Implement API call to save edited fields
      console.log('Saving edited fields:', editingFields);
      setEditingFields({});
    } catch (error) {
      console.error('Failed to save edits:', error);
    }
  };

  // ✅ Fetch detailed invoice data from backend
  const fetchInvoiceDetails = async () => {
    setIsLoadingDetails(true);
    setLoadError(null);
    
    try {
      console.log('Fetching invoice details for:', invoice.id);
      const detailedData = await apiService.getInvoiceDetails(invoice.id);
      console.log('Received invoice details:', detailedData);
      
      // ✅ Transform the response to include line items and other details
      const enhancedInvoice: DetailedInvoice = {
        ...detailedData,
        line_items: detailedData.line_items || [],
        delivery_note_match: deliveryNote || null,
        price_mismatches: detailedData.price_mismatches || [],
        // VAT calculations
        subtotal: detailedData.subtotal || 0,
        vat: detailedData.vat || 0,
        vat_rate: detailedData.vat_rate || 0.2,
        total_incl_vat: detailedData.total_incl_vat || detailedData.total_amount || 0
      };
      
      setDetailedInvoice(enhancedInvoice);
    } catch (error) {
      console.error('Failed to fetch invoice details:', error);
      setLoadError('Failed to load invoice details. Please try again.');
    } finally {
      setIsLoadingDetails(false);
    }
  };

  const formatDate = (dateString: string | undefined) => {
    if (!dateString) return 'N/A';
    try {
      return new Date(dateString).toLocaleDateString('en-GB', {
        day: '2-digit',
        month: 'short',
        year: 'numeric',
      });
    } catch {
      return 'Invalid Date';
    }
  };

  const formatCurrency = (amount: number | undefined) => {
    if (amount === undefined || amount === null) return '£0.00';
    return new Intl.NumberFormat('en-GB', {
      style: 'currency',
      currency: 'GBP',
    }).format(amount);
  };

  const formatVATRate = (rate: number | undefined) => {
    if (rate === undefined || rate === null) return '20%';
    return `${(rate * 100).toFixed(0)}%`;
  };

  const getStatusIcon = (status: string) => {
    switch (status.toLowerCase()) {
      case 'matched':
        return <CheckCircle className="w-4 h-4 text-green-600" />;
      case 'scanned':
        return <FileText className="w-4 h-4 text-blue-600" />;
      case 'waiting':
      case 'unmatched':
        return <Clock className="w-4 h-4 text-amber-600" />;
      default:
        return <AlertTriangle className="w-4 h-4 text-gray-600" />;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status.toLowerCase()) {
      case 'matched':
        return 'bg-green-100 text-green-800 border-green-200';
      case 'scanned':
        return 'bg-blue-100 text-blue-800 border-blue-200';
      case 'waiting':
      case 'unmatched':
        return 'bg-amber-100 text-amber-800 border-amber-200';
      default:
        return 'bg-gray-100 text-gray-800 border-gray-200';
    }
  };

  const getStatusLabel = (status: string) => {
    switch (status.toLowerCase()) {
      case 'matched':
        return 'Matched';
      case 'scanned':
        return 'Scanned';
      case 'waiting':
        return 'Waiting';
      case 'unmatched':
        return 'Unmatched';
      default:
        return status.charAt(0).toUpperCase() + status.slice(1);
    }
  };

  // ✅ Use real line items from detailed invoice or show fallback
  const lineItems = detailedInvoice?.line_items || [];
  const flaggedIssuesCount = lineItems.filter(item => item.flagged).length;

  return (
    <div className="w-full">
      {/* Main Card */}
      <motion.div
        className={`
          rounded-2xl bg-white shadow-sm border border-slate-200 p-4 mb-2
          hover:shadow-md hover:border-slate-300 transition-all duration-200
          cursor-pointer select-none
          ${isSelected ? 'ring-2 ring-blue-500 ring-opacity-50' : ''}
        `}
        onClick={handleToggle}
        whileHover={{ scale: 1.01 }}
        whileTap={{ scale: 0.99 }}
        role="button"
        tabIndex={0}
        aria-expanded={isExpanded}
        aria-controls={`invoice-details-${invoice.id}`}
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            handleToggle();
          }
        }}
      >
        {/* Header Row */}
        <div className="flex items-start justify-between mb-3">
          <div className="flex-1 min-w-0">
            {/* Invoice ID and Date */}
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs text-slate-500 font-mono">
                {invoice.id.slice(0, 8)}...
              </span>
              <div className="flex items-center space-x-2">
                <span className="text-sm text-slate-600">
                  {formatDate(invoice.invoice_date)}
                </span>
                <motion.div
                  animate={{ rotate: isExpanded ? 180 : 0 }}
                  transition={{ duration: 0.2 }}
                  className={`${isLoadingDetails ? 'animate-pulse' : ''}`}
                >
                  <ChevronDown className="w-4 h-4 text-slate-400" />
                </motion.div>
              </div>
            </div>
    
            {/* Supplier and Amount */}
            <div className="flex items-center justify-between">
              {/* Header block: Supplier, Filename, Confidence, Page Range */}
              <div className="flex flex-col flex-1 min-w-0">
                <div className="flex items-center justify-between">
                  <div className="flex-1 min-w-0">
                    <span className="font-semibold text-base text-gray-900 truncate">
                      {invoice.supplier_name || 'Unknown Supplier'}
                    </span>
                    <div className="flex items-center space-x-2 mt-1">
                      {/* Page Range Badge (if available) */}
                      {invoice.page_range && (
                        <span className="inline-block bg-blue-100 text-blue-800 text-xs font-medium px-2 py-0.5 rounded-full border border-blue-200">
                          Pages {invoice.page_range}
                        </span>
                      )}
                    </div>
                  </div>
                  {/* ✅ Confidence Badge (always visible, top-right) */}
                  {invoice.confidence !== undefined && (
                    <div className="flex-shrink-0 ml-2">
                      <ConfidenceBadge confidence={Math.round(invoice.confidence)} />
                    </div>
                  )}
                </div>
                <span className="text-sm text-gray-500 truncate mt-1">
                  {invoice.parent_pdf_filename || invoice.invoice_number || invoice.id.slice(0, 8) + '...'}
                </span>
              </div>
              <div className="text-right">
                <div className="font-bold text-slate-900 text-lg">
                  {formatCurrency(invoice.total_amount)}
                </div>
                <div className="text-xs text-slate-500">
                  {invoice.invoice_number || 'No Invoice #'}
                </div>
              </div>
            </div>
          </div>
        </div>
    
        {/* Bottom Row - Status and Badges */}
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            {/* Status Badge */}
            <div className={`
              inline-flex items-center space-x-1 px-2 py-1 rounded-full text-xs font-medium border
              ${getStatusColor(invoice.status)}
            `}>
              {getStatusIcon(invoice.status)}
              <span>{getStatusLabel(invoice.status)}</span>
            </div>
    
            {/* Confidence Badge */}
            {invoice.confidence !== undefined && (
              <ConfidenceBadge confidence={Math.round(invoice.confidence)} />
            )}
    
            {/* Manual Review Badge for low confidence */}
            {invoice.confidence !== undefined && invoice.confidence < 40 && (
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
          {invoice.status === 'processing' && (
            <div className="flex items-center space-x-2 text-xs text-slate-500">
              <div className="animate-spin rounded-full h-3 w-3 border-b-2 border-blue-600"></div>
              <span>Processing...</span>
            </div>
          )}
        </div>
      </motion.div>
    
      {/* Expanded Content */}
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
                    Fetching line items and VAT calculations
                  </p>
                </div>
              )}

              {/* ✅ Error State */}
              {loadError && (
                <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
                  <div className="flex items-center">
                    <AlertTriangle className="w-5 h-5 text-red-600 mr-2" />
                    <span className="text-red-800">{loadError}</span>
                  </div>
                  <button
                    onClick={fetchInvoiceDetails}
                    className="mt-2 text-sm text-red-600 hover:text-red-800 underline"
                  >
                    Try again
                  </button>
                </div>
              )}

              {/* ✅ Enhanced Detailed Content */}
              {!isLoadingDetails && !loadError && detailedInvoice && (
                <>
                  {/* VAT Summary Section */}
                  {detailedInvoice.subtotal && detailedInvoice.vat && (
                    <div className="mb-6">
                      <h4 className="font-semibold text-slate-800 mb-4 flex items-center">
                        <FileText className="w-4 h-4 mr-2" />
                        VAT Summary
                      </h4>
                      <div className="bg-white rounded-lg border border-slate-200 p-4">
                        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                          <div>
                            <span className="text-slate-600">Subtotal (ex. VAT):</span>
                            <div className="font-medium text-slate-900">
                              {formatCurrency(detailedInvoice.subtotal)}
                            </div>
                          </div>
                          <div>
                            <span className="text-slate-600">VAT ({formatVATRate(detailedInvoice.vat_rate)}):</span>
                            <div className="font-medium text-slate-900">
                              {formatCurrency(detailedInvoice.vat)}
                            </div>
                          </div>
                          <div>
                            <span className="text-slate-600">Total (incl. VAT):</span>
                            <div className="font-medium text-slate-900">
                              {formatCurrency(detailedInvoice.total_incl_vat)}
                            </div>
                          </div>
                          <div>
                            <span className="text-slate-600">VAT Rate:</span>
                            <div className="font-medium text-slate-900">
                              {formatVATRate(detailedInvoice.vat_rate)}
                            </div>
                          </div>
                        </div>
                      </div>
                    </div>
                  )}

                  {/* ✅ Editable Fields for Low Confidence Invoices */}
                  {invoice.confidence !== undefined && invoice.confidence < 40 && (
                    <div className="mb-6">
                      <h4 className="font-semibold text-slate-800 mb-4 flex items-center">
                        <AlertTriangle className="w-4 h-4 mr-2 text-orange-600" />
                        Manual Review Required
                        <span className="ml-2 text-sm text-orange-600">
                          (OCR Confidence: {Math.round(invoice.confidence)}%)
                        </span>
                      </h4>
                      <div className="bg-orange-50 border border-orange-200 rounded-lg p-4">
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                          <div>
                            <label className="block text-sm font-medium text-slate-700 mb-1">
                              Supplier Name
                            </label>
                            <input
                              type="text"
                              value={editingFields.supplier_name || detailedInvoice.supplier_name || ''}
                              onChange={(e) => handleFieldEdit('supplier_name', e.target.value)}
                              className="w-full px-3 py-2 border border-slate-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                              placeholder="Enter supplier name"
                            />
                          </div>
                          <div>
                            <label className="block text-sm font-medium text-slate-700 mb-1">
                              Invoice Number
                            </label>
                            <input
                              type="text"
                              value={editingFields.invoice_number || detailedInvoice.invoice_number || ''}
                              onChange={(e) => handleFieldEdit('invoice_number', e.target.value)}
                              className="w-full px-3 py-2 border border-slate-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                              placeholder="Enter invoice number"
                            />
                          </div>
                          <div>
                            <label className="block text-sm font-medium text-slate-700 mb-1">
                              Invoice Date
                            </label>
                            <input
                              type="date"
                              value={editingFields.invoice_date || detailedInvoice.invoice_date || ''}
                              onChange={(e) => handleFieldEdit('invoice_date', e.target.value)}
                              className="w-full px-3 py-2 border border-slate-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                            />
                          </div>
                          <div>
                            <label className="block text-sm font-medium text-slate-700 mb-1">
                              Total Amount
                            </label>
                            <input
                              type="number"
                              step="0.01"
                              value={editingFields.total_amount || detailedInvoice.total_amount || ''}
                              onChange={(e) => handleFieldEdit('total_amount', e.target.value)}
                              className="w-full px-3 py-2 border border-slate-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                              placeholder="0.00"
                            />
                          </div>
                        </div>
                        <div className="mt-4 flex justify-end">
                          <button
                            onClick={handleSaveEdits}
                            className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
                          >
                            Save Changes
                          </button>
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Line Items Section */}
                  <div className="mb-6">
                    <h4 className="font-semibold text-slate-800 mb-4 flex items-center">
                      <FileText className="w-4 h-4 mr-2" />
                      Line Items
                      {lineItems.length > 0 && (
                        <span className="ml-2 text-sm text-slate-500">
                          ({lineItems.length} items)
                        </span>
                      )}
                    </h4>
                    
                    {/* ✅ Show fallback message if no line items */}
                    {lineItems.length === 0 ? (
                      <div className="bg-slate-50 border border-slate-200 rounded-lg p-6 text-center">
                        <div className="text-slate-500 mb-2">
                          <FileText className="w-8 h-8 mx-auto mb-2 text-slate-400" />
                          <p className="text-sm">No line items detected</p>
                          <p className="text-xs text-slate-400 mt-1">
                            OCR couldn't identify individual line items from this invoice
                          </p>
                        </div>
                      </div>
                    ) : (
                      <InvoiceLineItemTable items={lineItems} />
                    )}
                  </div>

                  {/* ✅ OCR Debug Panel - Show for low confidence or dev mode */}
                  {(invoice.confidence !== undefined && invoice.confidence < 70) && (
                    <div className="mb-6">
                      <h4 className="font-semibold text-slate-800 mb-4 flex items-center">
                        <AlertTriangle className="w-4 h-4 mr-2 text-orange-600" />
                        OCR Debug Information
                        <span className="ml-2 text-sm text-orange-600">
                          (Low Confidence: {Math.round(invoice.confidence)}%)
                        </span>
                      </h4>
                      
                      <div className="bg-slate-50 border border-slate-200 rounded-lg p-4">
                        {/* Real OCR data from backend */}
                        <div className="space-y-4">
                          {/* OCR Quality Metrics */}
                          <div className="grid grid-cols-2 gap-4 text-sm">
                            <div>
                              <span className="text-slate-500">OCR Confidence:</span>
                              <span className="ml-2 font-mono">{invoice.confidence?.toFixed(1)}%</span>
                            </div>
                            <div>
                              <span className="text-slate-500">Word Count:</span>
                              <span className="ml-2 font-mono">{invoice.word_count || 'Unknown'}</span>
                            </div>
                            <div>
                              <span className="text-slate-500">PSM Used:</span>
                              <span className="ml-2 font-mono">{invoice.psm_used === 'paddle' ? 'PaddleOCR' : invoice.psm_used || 'Unknown'}</span>
                            </div>
                            <div>
                              <span className="text-slate-500">Was Retried:</span>
                              <span className="ml-2 font-mono text-orange-600">
                                {invoice.was_retried ? 'Yes' : 'No'}
                              </span>
                            </div>
                          </div>
                          
                          {/* Raw OCR Text Preview */}
                          {invoice.raw_ocr_text && (
                            <div className="mt-4 pt-4 border-t border-slate-200">
                              <h6 className="font-medium text-slate-700 mb-2">Raw OCR Text Preview</h6>
                              <div className="bg-slate-100 rounded p-3 max-h-32 overflow-y-auto">
                                <p className="text-xs font-mono text-slate-600 leading-relaxed">
                                  {invoice.raw_ocr_text.slice(0, 500)}
                                  {invoice.raw_ocr_text.length > 500 && '...'}
                                </p>
                              </div>
                            </div>
                          )}
                          
                          {/* Per-Page Details (if available) */}
                          {invoice.ocr_pages && invoice.ocr_pages.length > 0 && (
                            <div className="mt-4 pt-4 border-t border-slate-200">
                              <h6 className="font-medium text-slate-700 mb-2">Per-Page Details</h6>
                              <div className="space-y-2">
                                {invoice.ocr_pages.map((page: any, index: number) => (
                                  <div key={index} className="border-l-4 border-blue-500 pl-4">
                                    <div className="flex items-center justify-between mb-1">
                                      <h5 className="font-medium text-slate-700 text-sm">Page {page.page}</h5>
                                      <div className="flex items-center space-x-2">
                                        <span className="text-xs text-slate-500">
                                          {page.avg_confidence?.toFixed(1)}% confidence
                                        </span>
                                        <span className="text-xs bg-blue-100 text-blue-800 px-2 py-1 rounded">
                                          {page.psm_used === 'paddle' ? 'PaddleOCR' : page.psm_used || 'Unknown'}
                                        </span>
                                      </div>
                                    </div>
                                    <div className="bg-slate-100 rounded p-2">
                                      <p className="text-xs font-mono text-slate-600 leading-relaxed">
                                        {page.text?.slice(0, 200) || 'No text extracted'}
                                        {page.text && page.text.length > 200 && '...'}
                                      </p>
                                    </div>
                                  </div>
                                ))}
                              </div>
                            </div>
                          )}
                        </div>
                      </div>
                    </div>
                  )}
    
                  {/* Delivery Note Section */}
                  {detailedInvoice.delivery_note_match && (
                    <div className="mb-6">
                      <h4 className="font-semibold text-slate-800 mb-4 flex items-center">
                        <CheckCircle className="w-4 h-4 mr-2" />
                        Delivery Note
                      </h4>
                      <div className="bg-white rounded-lg border border-slate-200 p-4">
                        <div className="grid grid-cols-2 gap-4 text-sm">
                          <div>
                            <span className="text-slate-600">Number:</span>
                            <span className="ml-2 font-medium text-slate-900">
                              {detailedInvoice.delivery_note_match.delivery_note_number || 'N/A'}
                            </span>
                          </div>
                          <div>
                            <span className="text-slate-600">Date:</span>
                            <span className="ml-2 font-medium text-slate-900">
                              {formatDate(detailedInvoice.delivery_note_match.delivery_date)}
                            </span>
                          </div>
                          <div>
                            <span className="text-slate-600">Amount:</span>
                            <span className="ml-2 font-medium text-slate-900">
                              {formatCurrency(detailedInvoice.delivery_note_match.total_amount)}
                            </span>
                          </div>
                          <div>
                            <span className="text-slate-600">Status:</span>
                            <span className="ml-2 font-medium text-slate-900">
                              {getStatusLabel(detailedInvoice.delivery_note_match.status)}
                            </span>
                          </div>
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Price Mismatches Section */}
                  {detailedInvoice.price_mismatches && detailedInvoice.price_mismatches.length > 0 && (
                    <div className="mb-6">
                      <h4 className="font-semibold text-slate-800 mb-4 flex items-center">
                        <AlertTriangle className="w-4 h-4 mr-2 text-red-600" />
                        Price Mismatches
                      </h4>
                      <div className="bg-white rounded-lg border border-slate-200 overflow-hidden">
                        <table className="w-full">
                          <thead className="bg-red-50">
                            <tr>
                              <th className="px-4 py-3 text-left text-xs font-medium text-red-600 uppercase tracking-wider">
                                Item
                              </th>
                              <th className="px-4 py-3 text-right text-xs font-medium text-red-600 uppercase tracking-wider">
                                Invoice Amount
                              </th>
                              <th className="px-4 py-3 text-right text-xs font-medium text-red-600 uppercase tracking-wider">
                                Delivery Amount
                              </th>
                              <th className="px-4 py-3 text-right text-xs font-medium text-red-600 uppercase tracking-wider">
                                Difference
                              </th>
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-slate-200">
                            {detailedInvoice.price_mismatches.map((mismatch, index) => (
                              <tr key={index} className="bg-red-50">
                                <td className="px-4 py-3 text-sm text-slate-900">
                                  {mismatch.description}
                                </td>
                                <td className="px-4 py-3 text-sm text-slate-900 text-right">
                                  {formatCurrency(mismatch.invoice_amount)}
                                </td>
                                <td className="px-4 py-3 text-sm text-slate-900 text-right">
                                  {formatCurrency(mismatch.delivery_amount)}
                                </td>
                                <td className="px-4 py-3 text-sm font-medium text-red-600 text-right">
                                  {formatCurrency(mismatch.difference)}
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  )}
    
                  {/* Confidence Breakdown */}
                  <div className="mb-6">
                    <h4 className="font-semibold text-slate-800 mb-4">Confidence Breakdown</h4>
                    <div className="bg-white rounded-lg border border-slate-200 p-4">
                      <div className="space-y-3">
                        <div className="flex items-center justify-between">
                          <span className="text-sm text-slate-600">OCR Quality</span>
                          <div className="flex items-center space-x-2">
                            <div className="w-24 bg-slate-200 rounded-full h-2">
                              <div
                                className="bg-blue-600 h-2 rounded-full"
                                style={{ width: `${(invoice.confidence || 0) * 100}%` }}
                              />
                            </div>
                            <span className="text-sm font-medium text-slate-900">
                              {Math.round((invoice.confidence || 0) * 100)}%
                            </span>
                          </div>
                        </div>
                        <div className="flex items-center justify-between">
                          <span className="text-sm text-slate-600">Data Completeness</span>
                          <span className="text-sm font-medium text-slate-900">
                            {[
                              invoice.invoice_number,
                              invoice.supplier_name,
                              invoice.invoice_date,
                              invoice.total_amount
                            ].filter(Boolean).length}/4 fields
                          </span>
                        </div>
                        <div className="flex items-center justify-between">
                          <span className="text-sm text-slate-600">Line Items Found</span>
                          <span className="text-sm font-medium text-slate-900">
                            {lineItems.length} items
                          </span>
                        </div>
                        <div className="flex items-center justify-between">
                          <span className="text-sm text-slate-600">VAT Calculations</span>
                          <span className="text-sm font-medium text-slate-900">
                            {detailedInvoice.subtotal && detailedInvoice.vat ? 'Complete' : 'Incomplete'}
                          </span>
                        </div>
                      </div>
                    </div>
                  </div>
    
                  {/* Comments Section */}
                  <div>
                    <h4 className="font-semibold text-slate-800 mb-4">Comments & Notes</h4>
                    <div className="bg-white rounded-lg border border-slate-200 p-4">
                      <textarea
                        className="w-full h-20 p-3 text-sm border border-slate-300 rounded-lg resize-none focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                        placeholder="Add a comment or note about this invoice..."
                        disabled
                      />
                      <div className="mt-2 flex justify-end">
                        <button
                          className="px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                          disabled
                        >
                          Add Comment
                        </button>
                      </div>
                    </div>
                  </div>
                </>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

export default InvoiceCardAccordion; 