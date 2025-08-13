import React from 'react';
import Layout from '@/components/Layout';
import NavigationDebugger from '@/components/NavigationDebugger';

const TestNavigationPage: React.FC = () => {
  return (
    <Layout>
      <div className="container mx-auto py-8 px-4">
        <div className="max-w-4xl mx-auto">
          <h1 className="text-3xl font-bold text-gray-900 mb-6">
            Navigation Test Page
          </h1>
          
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 mb-6">
            <h2 className="text-xl font-semibold text-gray-900 mb-4">
              Navigation Status
            </h2>
            <p className="text-gray-600 mb-4">
              This page is used to test if navigation is working properly. 
              Try clicking on the navigation links in the header above.
            </p>
            
            <div className="space-y-2">
              <div className="flex items-center space-x-2">
                <span className="w-4 h-4 bg-green-500 rounded-full"></span>
                <span>Navigation should be visible and clickable</span>
              </div>
              <div className="flex items-center space-x-2">
                <span className="w-4 h-4 bg-green-500 rounded-full"></span>
                <span>Links should have hover effects</span>
              </div>
              <div className="flex items-center space-x-2">
                <span className="w-4 h-4 bg-green-500 rounded-full"></span>
                <span>Active page should be highlighted</span>
              </div>
            </div>
          </div>

          <div className="bg-blue-50 rounded-lg border border-blue-200 p-6">
            <h3 className="text-lg font-semibold text-blue-900 mb-3">
              Troubleshooting
            </h3>
            <ul className="text-blue-800 space-y-2">
              <li>• Check browser console for navigation click logs</li>
              <li>• Ensure no modals or overlays are blocking navigation</li>
              <li>• Verify z-index values are correct</li>
              <li>• Check if any JavaScript errors are preventing navigation</li>
              <li>• Use the debug button below to inspect navigation elements</li>
            </ul>
          </div>

          <div className="bg-yellow-50 rounded-lg border border-yellow-200 p-6 mt-6">
            <h3 className="text-lg font-semibold text-yellow-900 mb-3">
              Debug Information
            </h3>
            <p className="text-yellow-800 mb-3">
              Click the red &quot;Debug Nav&quot; button in the bottom-left corner to see detailed information about navigation elements and potential blocking issues.
            </p>
            <p className="text-yellow-800 text-sm">
              This will help identify if there are any elements with high z-index values or other CSS properties that might be preventing navigation from working.
            </p>
          </div>
        </div>
      </div>
      
      <NavigationDebugger />
    </Layout>
  );
};

export default TestNavigationPage; 