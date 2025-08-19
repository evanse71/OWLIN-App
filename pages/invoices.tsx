import React, { useState, useEffect, useCallback, useRef } from 'react';
import AppShell from '../components/layout/AppShell';
import InvoiceFilterPanel from '../frontend/components/invoices/InvoiceFilterPanel';
import InvoiceCardsPanel from '../frontend/components/invoices/InvoiceCardsPanel';
import UploadSection from '../frontend/components/invoices/UploadSection';
import InvoiceDetailBox from '../frontend/components/invoices/InvoiceDetailBox';
import { FiltersProvider, useFilters, Role } from '../frontend/state/filters/FiltersContext';
import { useRole } from '../frontend/hooks/useRole';
import { useLicense } from '../frontend/hooks/useLicense';
import { normalizeInvoice, ApiInvoice, UiInvoice } from '../frontend/lib/normalizeInvoice';
import { InvoiceListItem } from '../frontend/hooks/useInvoices';

// Adapter function to convert UiInvoice to InvoiceListItem
function convertToInvoiceListItem(uiInvoice: UiInvoice): InvoiceListItem {
  return {
    id: parseInt(uiInvoice.id),
    supplier_name: uiInvoice.supplierName,
    invoice_number: uiInvoice.invoiceNumber,
    invoice_date: uiInvoice.invoiceDate,
    total_amount: uiInvoice.totalAmount,
    status: uiInvoice.status,
    confidence: uiInvoice.confidence || 0,
    page_range: undefined,
    parent_pdf_filename: undefined,
    issues_count: 0,
    upload_id: '',
    matched_delivery_note_id: uiInvoice.matchedDeliveryNoteId ? parseInt(uiInvoice.matchedDeliveryNoteId) : undefined,
  };
}

// Error boundary component
const Safe: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [hasError, setHasError] = useState(false);
  
  if (hasError) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <h2 className="text-xl font-semibold text-gray-900 mb-2">Something went wrong</h2>
          <p className="text-gray-600 mb-4">Please refresh the page to try again.</p>
          <button 
            onClick={() => window.location.reload()}
            className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
          >
            Refresh Page
          </button>
        </div>
      </div>
    );
  }

  return (
    <React.Suspense fallback={
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Loading...</p>
        </div>
      </div>
    }>
      {children}
    </React.Suspense>
  );
};

// Main invoices page component
const InvoicesPageContent: React.FC = () => {
  const role = useRole();
  const license = useLicense();
  const { filters } = useFilters();
  
  const [invoices, setInvoices] = useState<InvoiceListItem[]>([]);
  const [selectedInvoice, setSelectedInvoice] = useState<InvoiceListItem | null>(null);
  const [expandedId, setExpandedId] = useState<number | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // Mock data for development
  const mockApiInvoices: ApiInvoice[] = [
    {
      id: 1,
      supplier_name: "FreshCo Supplies",
      invoice_number: "INV-2025-001",
      invoice_date: "2025-08-15",
      total_amount: 1247.50,
      status: "parsed",
      confidence: 92.5,
    },
    {
      id: 2,
      supplier_name: "Metro Beverages",
      invoice_number: "MB-2025-089",
      invoice_date: "2025-08-14",
      total_amount: 892.30,
      status: "flagged",
      confidence: 78.2,
    }
  ];

  useEffect(() => {
    // Simulate API call
    const loadInvoices = async () => {
      setIsLoading(true);
      try {
        // In real implementation, this would be an API call
        const normalizedInvoices = mockApiInvoices.map(normalizeInvoice);
        const invoiceListItems = normalizedInvoices.map(convertToInvoiceListItem);
        setInvoices(invoiceListItems);
      } catch (error) {
        console.error('Failed to load invoices:', error);
      } finally {
        setIsLoading(false);
      }
    };

    loadInvoices();
  }, []);

  const handleCardClick = useCallback((id: number) => {
    const invoice = invoices.find(inv => inv.id === id);
    setSelectedInvoice(invoice || null);
    setExpandedId(expandedId === id ? null : id);
  }, [invoices, expandedId]);

  const handleCardKeyDown = useCallback((e: React.KeyboardEvent, id: number) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      handleCardClick(id);
    }
  }, [handleCardClick]);

  const handleFilesUpload = useCallback(async (files: File[]) => {
    // Simulate file upload
    console.log('Uploading files:', files);
    // In real implementation, this would upload to the backend
  }, []);

  const handleRetryOCR = useCallback(() => {
    // Simulate OCR retry
    console.log('Retrying OCR for invoice:', selectedInvoice?.id);
  }, [selectedInvoice]);

  const handleResolveIssue = useCallback((lineId: number, action: string, payload?: any) => {
    // Simulate issue resolution
    console.log('Resolving issue:', { lineId, action, payload });
  }, []);

  // Check for role and license
  if (!role || !license) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Loading user permissions...</p>
        </div>
      </div>
    );
  }

  // License gating
  if (!license.valid) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <h2 className="text-xl font-semibold text-gray-900 mb-2">License Required</h2>
          <p className="text-gray-600">{license.reason || 'Please contact your administrator.'}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="h-screen flex" data-ui="invoices-page">
      <AppShell>
        <div className="flex-1 flex flex-col">
          {/* Filter Panel */}
          <div className="border-b border-gray-200 bg-white">
            <InvoiceFilterPanel />
          </div>
          
          {/* Main Content Area */}
          <div className="flex-1 flex overflow-hidden">
            {/* Left Panel - Upload and Cards */}
            <div className="flex-1 flex flex-col">
              {/* Upload Section */}
              <div className="border-b border-gray-200 bg-gray-50">
                <UploadSection 
                  onFilesUpload={handleFilesUpload}
                />
              </div>
              
              {/* Invoice Cards Panel */}
              <div className="flex-1 overflow-hidden">
                <InvoiceCardsPanel
                  invoices={invoices}
                  expandedId={expandedId}
                  onCardClick={handleCardClick}
                  onCardKeyDown={handleCardKeyDown}
                />
              </div>
            </div>
            
            {/* Right Panel - Detail Box */}
            <div className="w-96 border-l border-gray-200 bg-white">
              <InvoiceDetailBox
                invoice={selectedInvoice}
                onRetryOCR={handleRetryOCR}
                onResolveIssue={handleResolveIssue}
              />
            </div>
          </div>
        </div>
      </AppShell>
    </div>
  );
};

// Wrapper with providers
const InvoicesPage: React.FC = () => {
  const role = useRole();
  
  if (!role) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Loading...</p>
        </div>
      </div>
    );
  }

  return (
    <Safe>
      <FiltersProvider role={role.name as Role}>
        <InvoicesPageContent />
      </FiltersProvider>
    </Safe>
  );
};

export default InvoicesPage; 