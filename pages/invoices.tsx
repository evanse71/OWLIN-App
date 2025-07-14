import React, { useState, useEffect } from 'react';
import InvoicesUploadPanel from '@/components/invoices/InvoicesUploadPanel';
import UnmatchedDeliveryNotesSidebar from '@/components/invoices/UnmatchedDeliveryNotesSidebar';
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

const InvoicesPage: React.FC = () => {
  const [deliveryNotes, setDeliveryNotes] = useState<DeliveryNote[]>([]);

  // This function will be called by the InvoicesUploadPanel to update delivery notes
  const updateDeliveryNotes = (notes: DeliveryNote[]) => {
    setDeliveryNotes(notes);
  };

  return (
    <Layout>
      <div className="container mx-auto py-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-8 text-center">
          Owlin - Invoices
        </h1>
        
        {/* 2-column layout */}
        <div className="grid grid-cols-1 md:grid-cols-[1fr,320px] gap-8">
          {/* Main content - invoices and upload panel */}
          <div className="min-w-0">
            <InvoicesUploadPanel onDeliveryNotesUpdate={updateDeliveryNotes} />
          </div>
          
          {/* Sidebar - unmatched delivery notes */}
          <UnmatchedDeliveryNotesSidebar deliveryNotes={deliveryNotes} />
        </div>

        {/* Mobile message for sidebar */}
        <div className="md:hidden mt-8 p-4 bg-blue-50 rounded-lg border border-blue-200">
          <div className="text-center">
            <p className="text-sm text-blue-800 mb-2">
              📱 <span className="font-medium">Desktop view recommended</span>
            </p>
            <p className="text-xs text-blue-600">
              Switch to a larger screen to view unmatched delivery notes in the sidebar
            </p>
          </div>
        </div>
      </div>
    </Layout>
  );
};

export default InvoicesPage; 