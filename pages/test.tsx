import React from 'react';
import Layout from '@/components/Layout';

const TestPage: React.FC = () => {
  return (
    <Layout>
      <div className="container mx-auto py-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-8 text-center">
          Test Page - React Rendering Test
        </h1>
        
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-xl font-semibold mb-4">Basic React Test</h2>
          <p className="text-gray-600 mb-4">
            If you can see this page, React is working correctly.
          </p>
          
          <div className="space-y-4">
            <div className="p-4 bg-blue-50 rounded border">
              <h3 className="font-medium text-blue-800">✅ Layout Component</h3>
              <p className="text-sm text-blue-600">Layout component is rendering correctly</p>
            </div>
            
            <div className="p-4 bg-green-50 rounded border">
              <h3 className="font-medium text-green-800">✅ NavBar Component</h3>
              <p className="text-sm text-green-600">Navigation bar should be visible at the top</p>
            </div>
            
            <div className="p-4 bg-yellow-50 rounded border">
              <h3 className="font-medium text-yellow-800">✅ Tailwind CSS</h3>
              <p className="text-sm text-yellow-600">Styling is working if colors are visible</p>
            </div>
          </div>
          
          <div className="mt-6 p-4 bg-gray-50 rounded border">
            <h3 className="font-medium text-gray-800 mb-2">Next.js Router Test</h3>
            <a href="/invoices" className="text-blue-600 hover:text-blue-800 underline">
              Try navigating to /invoices
            </a>
          </div>
        </div>
      </div>
    </Layout>
  );
};

export default TestPage; 