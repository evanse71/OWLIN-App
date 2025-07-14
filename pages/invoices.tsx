import React, { useState, useEffect } from 'react';
import InvoicesUploadPanel from '@/components/invoices/InvoicesUploadPanel';
import UnmatchedDeliveryNotesSidebar from '@/components/invoices/UnmatchedDeliveryNotesSidebar';
import UnpairedInvoicesPanel from '@/components/invoices/UnpairedInvoicesPanel';
import Layout from '@/components/Layout';

interface DeliveryNote {
  id: string;
  filename: string;
  supplier: string;
  deliveryNumber: string;
  deliveryDate: string;
  status: 'Unmatched' | 'Processing' | 'Error' | 'Unknown';
  confidence?: number;
  parsedData?: any;
}

interface Invoice {
  id: string;
  filename: string;
  supplier: string;
  invoiceNumber: string;
  invoiceDate: string;
  totalAmount: string;
  type: 'Invoice' | 'Delivery Note' | 'Unknown';
  status: 'Processing' | 'Complete' | 'Error' | 'Matched' | 'Unmatched' | 'Unknown' | 'Scanned';
  confidence?: number;
  numIssues?: number;
  parsedData?: any;
  matchedDocument?: any;
}

const InvoicesPage: React.FC = () => {
  const [deliveryNotes, setDeliveryNotes] = useState<DeliveryNote[]>([]);
  const [invoices, setInvoices] = useState<Invoice[]>([]);

  // This function will be called by the InvoicesUploadPanel to update delivery notes
  const updateDeliveryNotes = (notes: DeliveryNote[]) => {
    setDeliveryNotes(notes);
  };

  // This function will be called by the InvoicesUploadPanel to update invoices
  const updateInvoices = (newInvoices: Invoice[]) => {
    setInvoices(newInvoices);
  };

  // Handle manual pairing of invoices with delivery notes
  const handleManualPair = (invoice: Invoice) => {
    // TODO: Implement manual pairing modal/side-panel
    console.log('Manual pair requested for invoice:', invoice);
    // This would typically open a modal or side-panel where the user can select a delivery note to pair
  };

  // Filter for unmatched invoices
  const unmatchedInvoices = invoices.filter(invoice => 
    invoice.status === 'Unmatched' && 
    invoice.type === 'Invoice'
  );

  return (
    <Layout>
      <div className="container mx-auto py-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-8 text-center">
          Owlin - Invoices
        </h1>
        
        {/* Responsive grid layout */}
        <div className="grid grid-cols-1 md:grid-cols-[1fr,320px] lg:grid-cols-[1fr,320px,320px] gap-8">
          {/* Main content - invoices and upload panel */}
          <div className="min-w-0">
            <InvoicesUploadPanel 
              onDeliveryNotesUpdate={updateDeliveryNotes}
              onInvoicesUpdate={updateInvoices}
            />
          </div>
          
          {/* Sidebar - unpaired invoices (shown on medium and large screens) */}
          <div className="hidden md:block">
            <UnpairedInvoicesPanel 
              invoices={invoices} 
              onManualPair={handleManualPair}
            />
          </div>
          
          {/* Sidebar - unmatched delivery notes (shown on large screens only) */}
          <div className="hidden lg:block">
            <UnmatchedDeliveryNotesSidebar deliveryNotes={deliveryNotes} />
          </div>
        </div>

        {/* Mobile message for sidebar */}
        <div className="md:hidden mt-8 p-4 bg-blue-50 rounded-lg border border-blue-200">
          <div className="text-center">
            <p className="text-sm text-blue-800 mb-2">
              📱 <span className="font-medium">Desktop view recommended</span>
            </p>
            <p className="text-xs text-blue-600">
              Switch to a larger screen to view unpaired invoices and unmatched delivery notes in the sidebar
            </p>
          </div>
        </div>

        {/* Medium screen message for delivery notes sidebar */}
        <div className="hidden md:block lg:hidden mt-8 p-4 bg-amber-50 rounded-lg border border-amber-200">
          <div className="text-center">
            <p className="text-sm text-amber-800 mb-2">
              💻 <span className="font-medium">Large screen recommended</span>
            </p>
            <p className="text-xs text-amber-600">
              Switch to a larger screen to also view unmatched delivery notes in the third column
            </p>
          </div>
        </div>
      </div>
    </Layout>
  );
};

export default InvoicesPage; 