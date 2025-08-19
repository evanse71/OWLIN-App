import React, { useState, useEffect } from 'react';
import AppShell from '@/components/layout/AppShell';
import ProductTrendPanel from '@/components/forecast/ProductTrendPanel';

interface ForecastData {
  item_name: string;
  historic: { x: string; y: number }[];
  forecast: { x: string; y: number; upper?: number; lower?: number }[];
  confidence: 'low' | 'medium' | 'high';
  volatility: 'low' | 'moderate' | 'high';
  data_points: number;
}

const ProductTrendsPage: React.FC = () => {
  const [forecastData, setForecastData] = useState<ForecastData[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [availableProducts, setAvailableProducts] = useState<string[]>([]);
  const [timeframe, setTimeframe] = useState('12'); // Default to 12 months

  useEffect(() => {
    fetchAvailableProducts();
  }, []);

  useEffect(() => {
    if (availableProducts.length > 0) {
      fetchForecastData(availableProducts.slice(0, 3));
    }
  }, [timeframe, availableProducts]);

  const fetchAvailableProducts = async () => {
    try {
      const response = await fetch('/api/products/available', { cache: 'no-store' });
      if (!response.ok) {
        throw new Error('Failed to fetch available products');
      }
      const data = await response.json();
      setAvailableProducts(data.products);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch products');
      setLoading(false);
    }
  };

  const fetchForecastData = async (products: string[]) => {
    try {
      setLoading(true);
      const forecastPromises = products.map(async (product) => {
        const response = await fetch(`/api/products/forecast/${encodeURIComponent(product)}?months_ahead=${timeframe}`);
        if (!response.ok) {
          throw new Error(`Failed to fetch forecast for ${product}`);
        }
        return response.json();
      });

      const results = await Promise.all(forecastPromises);
      setForecastData(results);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch forecast data');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <AppShell>
        <div className="py-8">
          <div className="max-w-4xl mx-auto">
            <div className="flex items-center justify-between mb-8">
              <h1 className="text-3xl font-semibold text-owlin-text" style={{ fontFamily: 'Work Sans, system-ui, sans-serif' }}>
                Product Price Trends
              </h1>
              <div className="flex items-center space-x-4">
                <label className="text-sm font-medium text-owlin-text">Timeframe:</label>
                <select value={timeframe} onChange={(e) => setTimeframe(e.target.value)} className="px-3 py-2 border border-owlin-stroke rounded-owlin bg-owlin-card text-owlin-text text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-owlin-sapphire">
                  <option value="3">3 months</option>
                  <option value="6">6 months</option>
                  <option value="12">12 months</option>
                </select>
              </div>
            </div>
            <div className="flex items-center justify-center h-64">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-owlin-cerulean"></div>
            </div>
          </div>
        </div>
      </AppShell>
    );
  }

  if (error) {
    return (
      <AppShell>
        <div className="py-8">
          <div className="max-w-4xl mx-auto">
            <div className="flex items-center justify-between mb-8">
              <h1 className="text-3xl font-semibold text-owlin-text" style={{ fontFamily: 'Work Sans, system-ui, sans-serif' }}>
                Product Price Trends
              </h1>
              <div className="flex items-center space-x-4">
                <label className="text-sm font-medium text-owlin-text">Timeframe:</label>
                <select value={timeframe} onChange={(e) => setTimeframe(e.target.value)} className="px-3 py-2 border border-owlin-stroke rounded-owlin bg-owlin-card text-owlin-text text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-owlin-sapphire">
                  <option value="3">3 months</option>
                  <option value="6">6 months</option>
                  <option value="12">12 months</option>
                </select>
              </div>
            </div>
            <div className="bg-owlin-card border border-owlin-stroke rounded-owlin p-4">
              <p className="text-red-700">Error loading forecast data: {error}</p>
              <button onClick={() => fetchAvailableProducts()} className="mt-2 px-4 py-2 bg-[var(--owlin-sapphire)] text-white rounded-owlin hover:brightness-110">Retry</button>
            </div>
          </div>
        </div>
      </AppShell>
    );
  }

  return (
    <AppShell>
      <div className="py-8">
        <div className="max-w-4xl mx-auto">
          <div className="flex items-center justify-between mb-8">
            <h1 className="text-3xl font-semibold text-owlin-text" style={{ fontFamily: 'Work Sans, system-ui, sans-serif' }}>
              Product Price Trends
            </h1>
            <div className="flex items-center space-x-4">
              <label className="text-sm font-medium text-owlin-text">Timeframe:</label>
              <select value={timeframe} onChange={(e) => setTimeframe(e.target.value)} className="px-3 py-2 border border-owlin-stroke rounded-owlin bg-owlin-card text-owlin-text text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-owlin-sapphire">
                <option value="3">3 months</option>
                <option value="6">6 months</option>
                <option value="12">12 months</option>
              </select>
            </div>
          </div>
          
          {forecastData.length === 0 ? (
            <div className="text-center py-12">
              <p className="text-owlin-muted">No forecast data available</p>
            </div>
          ) : (
            <div className="space-y-4">
              {forecastData.map((data) => (
                <ProductTrendPanel
                  key={data.item_name}
                  productName={data.item_name}
                  historic={data.historic}
                  forecast={data.forecast}
                  confidence={data.confidence}
                  volatility={data.volatility}
                  dataPoints={data.data_points}
                />
              ))}
            </div>
          )}
        </div>
      </div>
    </AppShell>
  );
};

export default ProductTrendsPage; 