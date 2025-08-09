import React, { useState, useEffect } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, BarChart, Bar, PieChart, Pie, Cell } from 'recharts';

interface AdvancedAnalyticsData {
  real_time_metrics: {
    total_invoices: number;
    last_24h: number;
    last_7d: number;
    matched: number;
    discrepancy: number;
    not_paired: number;
    total_value: number;
    avg_invoice_value: number;
    match_rate: number;
    discrepancy_rate: number;
    unpaired_rate: number;
  };
  daily_trends: Array<{
    date: string;
    invoice_count: number;
    daily_value: number;
    matched_count: number;
    discrepancy_count: number;
    match_rate: number;
  }>;
  top_suppliers: Array<{
    name: string;
    invoice_count: number;
    total_value: number;
    avg_value: number;
    match_rate: number;
  }>;
  flagged_analysis: {
    total_flagged: number;
    affected_invoices: number;
    total_error_value: number;
  };
  performance_metrics: {
    avg_processing_time: number;
    max_processing_time: number;
    min_processing_time: number;
  };
  venue_breakdown: Array<{
    name: string;
    invoice_count: number;
    total_value: number;
    match_rate: number;
  }>;
  ocr_analysis: {
    total_processed: number;
    high_confidence: number;
    medium_confidence: number;
    low_confidence: number;
    avg_confidence: number;
  };
  last_updated: string;
}

interface AdvancedAnalyticsDashboardProps {
  className?: string;
}

const AdvancedAnalyticsDashboard: React.FC<AdvancedAnalyticsDashboardProps> = ({ className = '' }) => {
  const [data, setData] = useState<AdvancedAnalyticsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'overview' | 'trends' | 'performance' | 'suppliers'>('overview');

  useEffect(() => {
    fetchAdvancedAnalytics();
  }, []);

  const fetchAdvancedAnalytics = async () => {
    try {
      setLoading(true);
      setError(null);

      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8002/api';
      const response = await fetch(`${apiUrl}/analytics/advanced-dashboard`);

      if (!response.ok) {
        throw new Error(`API Error: ${response.status} ${response.statusText}`);
      }

      const analyticsData = await response.json();
      setData(analyticsData);
    } catch (err) {
      console.error('Failed to fetch advanced analytics:', err);
      setError(err instanceof Error ? err.message : 'Failed to load analytics');
    } finally {
      setLoading(false);
    }
  };

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-GB', {
      style: 'currency',
      currency: 'GBP'
    }).format(amount);
  };

  const formatNumber = (num: number) => {
    return new Intl.NumberFormat('en-GB').format(num);
  };

  const formatPercentage = (value: number) => {
    return `${value.toFixed(1)}%`;
  };

  const formatTime = (seconds: number) => {
    if (seconds < 60) return `${seconds.toFixed(1)}s`;
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = seconds % 60;
    return `${minutes}m ${remainingSeconds.toFixed(0)}s`;
  };

  if (loading) {
    return (
      <div className={`bg-white rounded-lg shadow-lg p-6 ${className}`}>
        <div className="flex items-center justify-center h-64">
          <div className="text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
            <p className="text-gray-600">Loading advanced analytics...</p>
          </div>
        </div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className={`bg-white rounded-lg shadow-lg p-6 ${className}`}>
        <div className="text-center">
          <div className="text-red-500 mb-2">⚠️ Analytics Unavailable</div>
          <p className="text-gray-600">{error || 'Failed to load analytics data'}</p>
          <button 
            onClick={fetchAdvancedAnalytics}
            className="mt-4 px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  const { real_time_metrics, daily_trends, top_suppliers, flagged_analysis, performance_metrics, venue_breakdown, ocr_analysis } = data;

  // Prepare chart data
  const trendData = daily_trends.map(trend => ({
    date: new Date(trend.date).toLocaleDateString('en-GB', { month: 'short', day: 'numeric' }),
    invoices: trend.invoice_count,
    value: trend.daily_value,
    matchRate: trend.match_rate
  }));

  const supplierData = top_suppliers.slice(0, 8).map(supplier => ({
    name: supplier.name.length > 15 ? supplier.name.substring(0, 15) + '...' : supplier.name,
    value: supplier.total_value,
    matchRate: supplier.match_rate
  }));

  const ocrData = [
    { name: 'High Confidence', value: ocr_analysis.high_confidence, color: '#10B981' },
    { name: 'Medium Confidence', value: ocr_analysis.medium_confidence, color: '#F59E0B' },
    { name: 'Low Confidence', value: ocr_analysis.low_confidence, color: '#EF4444' }
  ];

  return (
    <div className={`bg-white rounded-lg shadow-lg overflow-hidden ${className}`}>
      {/* Header */}
      <div className="bg-gradient-to-r from-blue-600 to-blue-800 text-white p-6">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-2xl font-bold">Advanced Analytics Dashboard</h2>
            <p className="text-blue-100">Real-time insights and performance metrics</p>
          </div>
          <div className="text-right">
            <div className="text-sm text-blue-200">Last Updated</div>
            <div className="text-lg font-semibold">
              {new Date(data.last_updated).toLocaleTimeString('en-GB')}
            </div>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="border-b border-gray-200">
        <nav className="flex space-x-8 px-6">
          {[
            { id: 'overview', label: 'Overview', icon: '📊' },
            { id: 'trends', label: 'Trends', icon: '📈' },
            { id: 'performance', label: 'Performance', icon: '⚡' },
            { id: 'suppliers', label: 'Suppliers', icon: '🏢' }
          ].map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              className={`py-4 px-1 border-b-2 font-medium text-sm ${
                activeTab === tab.id
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              <span className="mr-2">{tab.icon}</span>
              {tab.label}
            </button>
          ))}
        </nav>
      </div>

      {/* Content */}
      <div className="p-6">
        {activeTab === 'overview' && (
          <div className="space-y-6">
            {/* Key Metrics Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
              <div className="bg-gradient-to-br from-green-50 to-green-100 p-4 rounded-lg border border-green-200">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-green-600">Total Value</p>
                    <p className="text-2xl font-bold text-green-900">{formatCurrency(real_time_metrics.total_value)}</p>
                    <p className="text-xs text-green-600">{formatNumber(real_time_metrics.total_invoices)} invoices</p>
                  </div>
                  <div className="text-3xl">💰</div>
                </div>
              </div>

              <div className="bg-gradient-to-br from-blue-50 to-blue-100 p-4 rounded-lg border border-blue-200">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-blue-600">Match Rate</p>
                    <p className="text-2xl font-bold text-blue-900">{formatPercentage(real_time_metrics.match_rate)}</p>
                    <p className="text-xs text-blue-600">{real_time_metrics.matched} matched</p>
                  </div>
                  <div className="text-3xl">✅</div>
                </div>
              </div>

              <div className="bg-gradient-to-br from-orange-50 to-orange-100 p-4 rounded-lg border border-orange-200">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-orange-600">Flagged Issues</p>
                    <p className="text-2xl font-bold text-orange-900">{formatNumber(flagged_analysis.total_flagged)}</p>
                    <p className="text-xs text-orange-600">{formatCurrency(flagged_analysis.total_error_value)} value</p>
                  </div>
                  <div className="text-3xl">⚠️</div>
                </div>
              </div>

              <div className="bg-gradient-to-br from-purple-50 to-purple-100 p-4 rounded-lg border border-purple-200">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-purple-600">Avg Processing</p>
                    <p className="text-2xl font-bold text-purple-900">{formatTime(performance_metrics.avg_processing_time)}</p>
                    <p className="text-xs text-purple-600">per invoice</p>
                  </div>
                  <div className="text-3xl">⚡</div>
                </div>
              </div>
            </div>

            {/* Charts Row */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Daily Trends */}
              <div className="bg-gray-50 p-4 rounded-lg">
                <h3 className="text-lg font-semibold mb-4">Daily Invoice Trends (30 days)</h3>
                <ResponsiveContainer width="100%" height={300}>
                  <LineChart data={trendData}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="date" />
                    <YAxis />
                    <Tooltip 
                      formatter={(value, name) => [
                        name === 'invoices' ? formatNumber(Number(value)) : formatCurrency(Number(value)),
                        name === 'invoices' ? 'Invoices' : 'Value'
                      ]}
                    />
                    <Line type="monotone" dataKey="invoices" stroke="#3B82F6" strokeWidth={2} />
                    <Line type="monotone" dataKey="value" stroke="#10B981" strokeWidth={2} />
                  </LineChart>
                </ResponsiveContainer>
              </div>

              {/* OCR Confidence */}
              <div className="bg-gray-50 p-4 rounded-lg">
                <h3 className="text-lg font-semibold mb-4">OCR Confidence Distribution</h3>
                <ResponsiveContainer width="100%" height={300}>
                  <PieChart>
                    <Pie
                      data={ocrData}
                      cx="50%"
                      cy="50%"
                      outerRadius={80}
                      dataKey="value"
                      label={({ name, percent }) => `${name} ${((percent || 0) * 100).toFixed(0)}%`}
                    >
                      {ocrData.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={entry.color} />
                      ))}
                    </Pie>
                    <Tooltip formatter={(value) => [formatNumber(Number(value)), 'Documents']} />
                  </PieChart>
                </ResponsiveContainer>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'trends' && (
          <div className="space-y-6">
            <div className="bg-gray-50 p-6 rounded-lg">
              <h3 className="text-xl font-semibold mb-4">Trend Analysis</h3>
              <ResponsiveContainer width="100%" height={400}>
                <LineChart data={trendData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="date" />
                  <YAxis />
                  <Tooltip 
                    formatter={(value, name) => [
                      name === 'matchRate' ? `${Number(value)}%` : formatCurrency(Number(value)),
                      name === 'matchRate' ? 'Match Rate' : 'Daily Value'
                    ]}
                  />
                  <Line type="monotone" dataKey="value" stroke="#10B981" strokeWidth={3} name="Daily Value" />
                  <Line type="monotone" dataKey="matchRate" stroke="#3B82F6" strokeWidth={2} name="Match Rate" />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>
        )}

        {activeTab === 'performance' && (
          <div className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="bg-gray-50 p-4 rounded-lg">
                <h3 className="text-lg font-semibold mb-4">Processing Performance</h3>
                <div className="space-y-3">
                  <div className="flex justify-between">
                    <span className="text-gray-600">Average Time:</span>
                    <span className="font-semibold">{formatTime(performance_metrics.avg_processing_time)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600">Fastest Time:</span>
                    <span className="font-semibold">{formatTime(performance_metrics.min_processing_time)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600">Slowest Time:</span>
                    <span className="font-semibold">{formatTime(performance_metrics.max_processing_time)}</span>
                  </div>
                </div>
              </div>

              <div className="bg-gray-50 p-4 rounded-lg">
                <h3 className="text-lg font-semibold mb-4">OCR Performance</h3>
                <div className="space-y-3">
                  <div className="flex justify-between">
                    <span className="text-gray-600">Total Processed:</span>
                    <span className="font-semibold">{formatNumber(ocr_analysis.total_processed)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600">High Confidence:</span>
                    <span className="font-semibold">{formatNumber(ocr_analysis.high_confidence)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600">Average Confidence:</span>
                    <span className="font-semibold">{formatPercentage(ocr_analysis.avg_confidence * 100)}</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'suppliers' && (
          <div className="space-y-6">
            <div className="bg-gray-50 p-4 rounded-lg">
              <h3 className="text-lg font-semibold mb-4">Top Suppliers by Value</h3>
              <ResponsiveContainer width="100%" height={400}>
                <BarChart data={supplierData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="name" angle={-45} textAnchor="end" height={80} />
                  <YAxis />
                  <Tooltip formatter={(value) => [formatCurrency(Number(value)), 'Total Value']} />
                  <Bar dataKey="value" fill="#3B82F6" />
                </BarChart>
              </ResponsiveContainer>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="bg-gray-50 p-4 rounded-lg">
                <h3 className="text-lg font-semibold mb-4">Supplier Performance</h3>
                <div className="space-y-3">
                  {top_suppliers.slice(0, 5).map((supplier, index) => (
                    <div key={index} className="flex justify-between items-center p-2 bg-white rounded">
                      <div>
                        <div className="font-medium">{supplier.name}</div>
                        <div className="text-sm text-gray-500">{supplier.invoice_count} invoices</div>
                      </div>
                      <div className="text-right">
                        <div className="font-semibold">{formatCurrency(supplier.total_value)}</div>
                        <div className="text-sm text-gray-500">{formatPercentage(supplier.match_rate)} match rate</div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              <div className="bg-gray-50 p-4 rounded-lg">
                <h3 className="text-lg font-semibold mb-4">Venue Breakdown</h3>
                <div className="space-y-3">
                  {venue_breakdown.slice(0, 5).map((venue, index) => (
                    <div key={index} className="flex justify-between items-center p-2 bg-white rounded">
                      <div>
                        <div className="font-medium">{venue.name}</div>
                        <div className="text-sm text-gray-500">{venue.invoice_count} invoices</div>
                      </div>
                      <div className="text-right">
                        <div className="font-semibold">{formatCurrency(venue.total_value)}</div>
                        <div className="text-sm text-gray-500">{formatPercentage(venue.match_rate)} match rate</div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default AdvancedAnalyticsDashboard; 