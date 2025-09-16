import React from 'react';
import { getJSON } from '@/lib/api';

type Metrics = {
  total_spend: number;
  match_rate: number;
  issues: number;
  avg_ocr: number;
};

type TimeSeriesPoint = {
  date: string;
  spend: number;
};

type TimeSeries = {
  series: TimeSeriesPoint[];
};

export default function DashboardPage() {
  const [metrics, setMetrics] = React.useState<Metrics | null>(null);
  const [timeSeries, setTimeSeries] = React.useState<TimeSeries | null>(null);
  const [selectedRange, setSelectedRange] = React.useState<'7' | '30' | '90'>('30');
  const [loading, setLoading] = React.useState(true);

  const loadData = React.useCallback(async () => {
    try {
      setLoading(true);
      const [metricsData, timeSeriesData] = await Promise.all([
        getJSON<Metrics>('/api/dashboard/metrics'),
        getJSON<TimeSeries>('/api/dashboard/spend_timeseries')
      ]);
      setMetrics(metricsData);
      setTimeSeries(timeSeriesData);
    } catch (error) {
      console.error('Failed to load dashboard data:', error);
    } finally {
      setLoading(false);
    }
  }, []);

  React.useEffect(() => {
    loadData();
  }, [loadData]);

  const filteredSeries = React.useMemo(() => {
    if (!timeSeries) return [];
    const days = parseInt(selectedRange);
    const cutoff = new Date();
    cutoff.setDate(cutoff.getDate() - days);
    return timeSeries.series.filter(point => new Date(point.date) >= cutoff);
  }, [timeSeries, selectedRange]);

  if (loading) {
    return (
      <div className="p-6">
        <div className="text-center">Loading dashboard...</div>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6">
      <h1 className="text-2xl font-bold">Dashboard</h1>
      
      {/* Metrics Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-white p-6 rounded-lg border shadow-sm">
          <h3 className="text-sm font-medium text-gray-500">Total Spend</h3>
          <p className="text-2xl font-bold text-green-600">
            ${metrics?.total_spend?.toLocaleString() || '0'}
          </p>
        </div>
        
        <div className="bg-white p-6 rounded-lg border shadow-sm">
          <h3 className="text-sm font-medium text-gray-500">Match Rate</h3>
          <p className="text-2xl font-bold text-blue-600">
            {metrics?.match_rate?.toFixed(1) || '0.0'}%
          </p>
        </div>
        
        <div className="bg-white p-6 rounded-lg border shadow-sm">
          <h3 className="text-sm font-medium text-gray-500">Issues</h3>
          <p className="text-2xl font-bold text-red-600">
            {metrics?.issues || 0}
          </p>
        </div>
        
        <div className="bg-white p-6 rounded-lg border shadow-sm">
          <h3 className="text-sm font-medium text-gray-500">Avg OCR</h3>
          <p className="text-2xl font-bold text-purple-600">
            {metrics?.avg_ocr?.toFixed(1) || '0.0'}%
          </p>
        </div>
      </div>

      {/* Timeseries Chart */}
      <div className="bg-white p-6 rounded-lg border shadow-sm">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold">Spend Over Time</h2>
          <div className="flex gap-2">
            {(['7', '30', '90'] as const).map(range => (
              <button
                key={range}
                onClick={() => setSelectedRange(range)}
                className={`px-3 py-1 rounded text-sm ${
                  selectedRange === range
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                }`}
              >
                {range}d
              </button>
            ))}
          </div>
        </div>
        
        {filteredSeries.length > 0 ? (
          <div className="space-y-2">
            {filteredSeries.map((point, index) => (
              <div key={point.date} className="flex items-center justify-between p-2 bg-gray-50 rounded">
                <span className="text-sm font-medium">{point.date}</span>
                <span className="text-sm text-green-600 font-medium">
                  ${point.spend.toLocaleString()}
                </span>
              </div>
            ))}
          </div>
        ) : (
          <div className="text-center py-8 text-gray-500">
            No spend data available for the selected period.
          </div>
        )}
      </div>
    </div>
  );
}
