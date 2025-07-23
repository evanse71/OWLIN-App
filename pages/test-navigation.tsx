import React from 'react';
import Layout from '@/components/Layout';

const TestNavigationPage: React.FC = () => {
  return (
    <Layout>
      <div className="container mx-auto py-8 px-4">
        <h1 className="text-3xl font-bold text-gray-900 mb-8 text-center">
          Navigation Test Page
        </h1>
        
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-xl font-semibold mb-4">Navigation Test</h2>
          <p className="text-gray-600 mb-4">
            This page is used to test navigation functionality. Try clicking on different navigation items in the header.
          </p>
          
          <div className="space-y-4">
            <div className="p-4 bg-green-50 rounded border">
              <h3 className="font-medium text-green-800">✅ Navigation Working</h3>
              <p className="text-sm text-green-600">If you can see this page, navigation is working correctly</p>
            </div>
            
            <div className="p-4 bg-blue-50 rounded border">
              <h3 className="font-medium text-blue-800">🧪 Test Instructions</h3>
              <p className="text-sm text-blue-600">
                1. Click on "Dashboard" in the navigation<br/>
                2. Click on "Invoices" in the navigation<br/>
                3. Click on "Product Trends" in the navigation<br/>
                4. Verify that each page loads correctly
              </p>
            </div>
            
            <div className="p-4 bg-yellow-50 rounded border">
              <h3 className="font-medium text-yellow-800">⚠️ Expected Behavior</h3>
              <p className="text-sm text-yellow-600">
                - Each navigation item should load the correct page<br/>
                - No console errors should appear<br/>
                - Navigation state should be maintained
              </p>
            </div>
          </div>
        </div>
      </div>
    </Layout>
  );
};

export default TestNavigationPage; 