import React, { useState } from 'react';
import InvoiceCard from '../components/invoices/InvoiceCard';
import DeliveryNoteCard from '../components/invoices/DeliveryNoteCard';

const TestCardsPage: React.FC = () => {
  const [testInvoices, setTestInvoices] = useState([
    {
      id: '1',
      invoiceId: 'INV-001',
      supplierName: 'Test Supplier',
      invoiceDate: '2024-01-15',
      totalAmount: '1,250.00',
      progress: 100,
      status: 'complete' as const,
      confidence: 95,
      parsedData: {
        supplier_name: 'Test Supplier',
        invoice_number: 'INV-001',
        total_amount: '1,250.00',
        invoice_date: '2024-01-15'
      }
    },
    {
      id: '2',
      invoiceId: 'INV-002',
      supplierName: 'Processing...',
      invoiceDate: 'Extracting...',
      totalAmount: 'Calculating...',
      progress: 45,
      status: 'processing' as const,
      confidence: undefined,
      parsedData: undefined
    },
    {
      id: '3',
      invoiceId: 'INV-003',
      supplierName: '⚠ Failed to scan',
      invoiceDate: 'N/A',
      totalAmount: 'N/A',
      progress: 100,
      status: 'error' as const,
      errorMessage: 'Empty file',
      confidence: undefined,
      parsedData: undefined
    }
  ]);

  const [testDeliveryNotes, setTestDeliveryNotes] = useState([
    {
      id: '1',
      noteId: 'DN-001',
      deliveryDate: '2024-01-14',
      itemCount: 5,
      status: 'delivered' as const,
      progress: 100,
      confidence: 88,
      parsedData: {
        supplier_name: 'Test Supplier',
        delivery_note_number: 'DN-001',
        delivery_date: '2024-01-14',
        items: [{}, {}, {}, {}, {}]
      }
    },
    {
      id: '2',
      noteId: 'DN-002',
      deliveryDate: 'Extracting...',
      itemCount: 0,
      status: 'processing' as const,
      progress: 30,
      confidence: undefined,
      parsedData: undefined
    }
  ]);

  const handleCancelInvoice = (id: string) => {
    setTestInvoices(prev => prev.filter(invoice => invoice.id !== id));
  };

  const handleCancelDelivery = (id: string) => {
    setTestDeliveryNotes(prev => prev.filter(note => note.id !== id));
  };

  const handleInvoiceClick = (id: string) => {
    console.log('Invoice clicked:', id);
  };

  const handleDeliveryClick = (id: string) => {
    console.log('Delivery note clicked:', id);
  };

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="max-w-6xl mx-auto px-6">
        <h1 className="text-3xl font-bold text-gray-900 mb-8">Card System Test</h1>
        
        {/* Invoice Cards */}
        <div className="mb-12">
          <h2 className="text-2xl font-semibold text-gray-800 mb-6">Invoice Cards</h2>
          <div className="space-y-6">
            {testInvoices.map((invoice) => (
              <InvoiceCard
                key={invoice.id}
                invoiceId={invoice.invoiceId}
                invoiceNumber={invoice.invoiceId}
                supplierName={invoice.supplierName}
                invoiceDate={invoice.invoiceDate}
                totalAmount={invoice.totalAmount}
                progress={invoice.progress}
                status={invoice.status}
                errorMessage={invoice.errorMessage}
                isProcessing={invoice.status === 'processing'}
                confidence={invoice.confidence}
                parsedData={invoice.parsedData}
                onClick={() => handleInvoiceClick(invoice.id)}
                onCancel={() => handleCancelInvoice(invoice.id)}
              />
            ))}
          </div>
        </div>

        {/* Delivery Note Cards */}
        <div className="mb-12">
          <h2 className="text-2xl font-semibold text-gray-800 mb-6">Delivery Note Cards</h2>
          <div className="space-y-6">
            {testDeliveryNotes.map((note) => (
              <DeliveryNoteCard
                key={note.id}
                noteId={note.noteId}
                deliveryDate={note.deliveryDate}
                itemCount={note.itemCount}
                status={note.status}
                progress={note.progress}
                isProcessing={note.status === 'processing'}
                confidence={note.confidence}
                parsedData={note.parsedData}
                onClick={() => handleDeliveryClick(note.id)}
                onCancel={() => handleCancelDelivery(note.id)}
              />
            ))}
          </div>
        </div>

        {/* Add Test Buttons */}
        <div className="bg-white rounded-lg p-6 shadow-sm">
          <h3 className="text-lg font-medium text-gray-800 mb-4">Test Controls</h3>
          <div className="flex gap-4">
            <button
              onClick={() => {
                const newId = Date.now().toString();
                setTestInvoices(prev => [...prev, {
                  id: newId,
                  invoiceId: `INV-${newId}`,
                  supplierName: 'Processing...',
                  invoiceDate: 'Extracting...',
                  totalAmount: 'Calculating...',
                  progress: 0,
                  status: 'processing',
                  confidence: undefined,
                  parsedData: undefined
                }]);
              }}
              className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors"
            >
              Add Processing Invoice
            </button>
            <button
              onClick={() => {
                const newId = Date.now().toString();
                setTestDeliveryNotes(prev => [...prev, {
                  id: newId,
                  noteId: `DN-${newId}`,
                  deliveryDate: 'Extracting...',
                  itemCount: 0,
                  status: 'processing',
                  progress: 0,
                  confidence: undefined,
                  parsedData: undefined
                }]);
              }}
              className="px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 transition-colors"
            >
              Add Processing Delivery Note
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default TestCardsPage; 