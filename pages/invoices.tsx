import React from 'react';
import InvoicesUploadPanel from '@/components/invoices/InvoicesUploadPanel';
import Layout from '@/components/Layout';

const InvoicesPage: React.FC = () => {
  return (
    <Layout>
      <div className="container mx-auto py-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-8 text-center">
          Owlin - Invoices
        </h1>
        
        {/* Render the upload panel */}
        <InvoicesUploadPanel />
        
        {/* Additional content can be added here */}
        <div className="mt-12 text-center text-gray-600">
          <p>Upload your invoices and delivery notes to get started.</p>
        </div>
      </div>
    </Layout>
  );
};

export default InvoicesPage; 