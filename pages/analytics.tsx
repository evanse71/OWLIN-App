import React from 'react';
import Layout from '@/components/Layout';
import AdvancedAnalyticsDashboard from '@/components/analytics/AdvancedAnalyticsDashboard';

const AnalyticsPage: React.FC = () => {
  return (
    <Layout>
      <div className="container mx-auto py-8 px-4">
        <div className="max-w-7xl mx-auto">
          {/* Header */}
          <div className="text-center mb-8">
            <h1 className="text-4xl font-bold text-gray-900 mb-2">Advanced Analytics</h1>
            <p className="text-lg text-gray-600">
              Comprehensive insights and performance metrics for your invoice processing system
            </p>
          </div>

          {/* Advanced Analytics Dashboard */}
          <AdvancedAnalyticsDashboard className="mb-8" />

          {/* Additional Analytics Sections */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
            {/* Quick Stats */}
            <div className="bg-white rounded-lg shadow-lg p-6">
              <h2 className="text-xl font-semibold mb-4">Quick Statistics</h2>
              <div className="space-y-4">
                <div className="flex justify-between items-center p-3 bg-gray-50 rounded">
                  <span className="text-gray-600">Processing Efficiency</span>
                  <span className="font-semibold text-green-600">95.2%</span>
                </div>
                <div className="flex justify-between items-center p-3 bg-gray-50 rounded">
                  <span className="text-gray-600">Average Processing Time</span>
                  <span className="font-semibold text-blue-600">2.3s</span>
                </div>
                <div className="flex justify-between items-center p-3 bg-gray-50 rounded">
                  <span className="text-gray-600">OCR Accuracy</span>
                  <span className="font-semibold text-purple-600">94.8%</span>
                </div>
                <div className="flex justify-between items-center p-3 bg-gray-50 rounded">
                  <span className="text-gray-600">Match Rate</span>
                  <span className="font-semibold text-orange-600">87.3%</span>
                </div>
              </div>
            </div>

            {/* System Health */}
            <div className="bg-white rounded-lg shadow-lg p-6">
              <h2 className="text-xl font-semibold mb-4">System Health</h2>
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <span className="text-gray-600">Database Status</span>
                  <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                    Healthy
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-gray-600">OCR Engine</span>
                  <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                    Operational
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-gray-600">API Response Time</span>
                  <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                    45ms
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-gray-600">Storage Usage</span>
                  <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-yellow-100 text-yellow-800">
                    67%
                  </span>
                </div>
              </div>
            </div>
          </div>

          {/* Insights Section */}
          <div className="mt-8 bg-white rounded-lg shadow-lg p-6">
            <h2 className="text-xl font-semibold mb-4">Key Insights</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              <div className="p-4 bg-blue-50 rounded-lg border border-blue-200">
                <div className="flex items-center mb-2">
                  <div className="text-2xl mr-3">📈</div>
                  <h3 className="font-semibold text-blue-900">Trend Analysis</h3>
                </div>
                <p className="text-sm text-blue-700">
                  Invoice processing volume has increased by 23% over the last 30 days, 
                  indicating growing system adoption.
                </p>
              </div>

              <div className="p-4 bg-green-50 rounded-lg border border-green-200">
                <div className="flex items-center mb-2">
                  <div className="text-2xl mr-3">✅</div>
                  <h3 className="font-semibold text-green-900">Performance</h3>
                </div>
                <p className="text-sm text-green-700">
                  Average processing time has improved by 15% this month, 
                  thanks to optimized OCR algorithms.
                </p>
              </div>

              <div className="p-4 bg-orange-50 rounded-lg border border-orange-200">
                <div className="flex items-center mb-2">
                  <div className="text-2xl mr-3">⚠️</div>
                  <h3 className="font-semibold text-orange-900">Alerts</h3>
                </div>
                <p className="text-sm text-orange-700">
                  12 flagged issues detected this week, primarily related to 
                  price discrepancies in food service invoices.
                </p>
              </div>
            </div>
          </div>

          {/* Action Items */}
          <div className="mt-8 bg-white rounded-lg shadow-lg p-6">
            <h2 className="text-xl font-semibold mb-4">Recommended Actions</h2>
            <div className="space-y-3">
              <div className="flex items-center p-3 bg-yellow-50 rounded border border-yellow-200">
                <div className="text-yellow-600 mr-3">🔍</div>
                <div className="flex-1">
                  <p className="font-medium text-yellow-900">Review Flagged Issues</p>
                  <p className="text-sm text-yellow-700">5 invoices require manual review due to low confidence scores</p>
                </div>
                <button className="px-3 py-1 bg-yellow-600 text-white rounded text-sm hover:bg-yellow-700">
                  Review
                </button>
              </div>

              <div className="flex items-center p-3 bg-blue-50 rounded border border-blue-200">
                <div className="text-blue-600 mr-3">📊</div>
                <div className="flex-1">
                  <p className="font-medium text-blue-900">Export Analytics Report</p>
                  <p className="text-sm text-blue-700">Generate monthly performance report for stakeholders</p>
                </div>
                <button className="px-3 py-1 bg-blue-600 text-white rounded text-sm hover:bg-blue-700">
                  Export
                </button>
              </div>

              <div className="flex items-center p-3 bg-green-50 rounded border border-green-200">
                <div className="text-green-600 mr-3">⚙️</div>
                <div className="flex-1">
                  <p className="font-medium text-green-900">System Optimization</p>
                  <p className="text-sm text-green-700">Consider upgrading OCR settings for better accuracy</p>
                </div>
                <button className="px-3 py-1 bg-green-600 text-white rounded text-sm hover:bg-green-700">
                  Optimize
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </Layout>
  );
};

export default AnalyticsPage; 