// ICONS: added local icon imports
import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
import ItemForecastCard from '../../components/forecast/ItemForecastCard';
import ForecastChart from '../../components/forecast/ForecastChart';
import ScenarioControls from '../../components/forecast/ScenarioControls';
import QualityPanel from '../../components/forecast/QualityPanel';
import { ForecastSummary, ForecastSeries, ForecastQuality, ForecastItem, ForecastScenario } from '../../types/forecast';
import { RefreshIcon, WarningTriangleIcon } from '../../components/icons';

const ForecastWorkspace: React.FC = () => {
  const router = useRouter();
  const [summary, setSummary] = useState<ForecastSummary | null>(null);
  const [selectedItem, setSelectedItem] = useState<ForecastItem | null>(null);
  const [selectedForecast, setSelectedForecast] = useState<ForecastSeries | null>(null);
  const [quality, setQuality] = useState<ForecastQuality | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  // Filters
  const [searchQuery, setSearchQuery] = useState('');
  const [supplierFilter, setSupplierFilter] = useState('');
  const [venueFilter, setVenueFilter] = useState('');
  const [onlyLongHistory, setOnlyLongHistory] = useState(false);

  useEffect(() => {
    loadForecastSummary();
  }, [searchQuery, supplierFilter, venueFilter, onlyLongHistory]);

  const loadForecastSummary = async () => {
    try {
      setIsLoading(true);
      setError(null);
      
      const params = new URLSearchParams({
        limit: '50',
        offset: '0'
      });
      
      if (searchQuery) params.append('search', searchQuery);
      if (supplierFilter) params.append('supplier_id', supplierFilter);
      if (venueFilter) params.append('venue_id', venueFilter);
      
      const response = await fetch(`/api/forecast/items?${params}`);
      if (!response.ok) {
        throw new Error('Failed to load forecast summary');
      }
      
      const data = await response.json();
      setSummary(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setIsLoading(false);
    }
  };

  const handleItemSelect = async (item: ForecastItem) => {
    setSelectedItem(item);
    
    try {
      // Load detailed forecast
      const response = await fetch(`/api/forecast/item/${item.item_id}?horizon=12`);
      if (response.ok) {
        const forecast = await response.json();
        setSelectedForecast(forecast);
      }
      
      // Load quality metrics
      const qualityResponse = await fetch(`/api/forecast/quality/${item.item_id}`);
      if (qualityResponse.ok) {
        const qualityData = await qualityResponse.json();
        setQuality(qualityData);
      }
    } catch (err) {
      console.error('Failed to load item details:', err);
    }
  };

  const handleScenarioChange = async (scenario: ForecastScenario) => {
    if (!selectedItem) return;
    
    try {
      const scenarioJson = encodeURIComponent(JSON.stringify(scenario));
      const response = await fetch(`/api/forecast/item/${selectedItem.item_id}?horizon=12&scenario=${scenarioJson}`);
      if (response.ok) {
        const forecast = await response.json();
        setSelectedForecast(forecast);
      }
    } catch (err) {
      console.error('Failed to apply scenario:', err);
    }
  };

  const handleRecompute = async () => {
    try {
      const response = await fetch('/api/forecast/recompute', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ all: true })
      });
      
      if (!response.ok) {
        throw new Error('Failed to queue recompute');
      }
      
      // Show success message
      console.log('Recompute queued successfully');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    }
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-50 p-6">
        <div className="max-w-7xl mx-auto">
          <div className="animate-pulse">
            <div className="h-8 bg-gray-200 rounded w-1/4 mb-6"></div>
            <div className="grid grid-cols-7 gap-6">
              <div className="col-span-3 h-96 bg-gray-200 rounded"></div>
              <div className="col-span-4 h-96 bg-gray-200 rounded"></div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-7xl mx-auto space-y-6">
        {/* Header */}
        <div className="bg-white rounded-[12px] p-6 shadow-sm">
          <div className="flex justify-between items-center">
            <div>
              <h1 className="text-2xl font-semibold text-gray-900">
                Item-Level Price Forecasts
              </h1>
              <p className="text-gray-600 mt-1">
                Predict price trends with confidence intervals and scenario controls
              </p>
            </div>
            
            <div className="flex space-x-4">
              <button
                onClick={handleRecompute}
                className="px-4 py-2 bg-[#2563EB] text-white hover:bg-[#1D4ED8] rounded-[8px] text-sm flex items-center gap-2"
              >
                <RefreshIcon size={16} stroke="white" />
                Recompute All
              </button>
            </div>
          </div>
        </div>

        {/* Error Banner */}
        {error && (
          <div className="flex items-center gap-2 bg-[#FFFBEB] border border-[#FDE68A] text-[#7C2D12] rounded-[8px] p-2 text-[12px]">
            <WarningTriangleIcon size={16} stroke="#7C2D12" />
            <span>{error}</span>
            <button
              onClick={() => setError(null)}
              className="ml-auto text-[#7C2D12] hover:text-[#5B1A0A]"
            >
              ×
            </button>
          </div>
        )}

        {/* Filters */}
        <div className="bg-white rounded-[12px] p-4 shadow-sm">
          <div className="grid grid-cols-4 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Search Items
              </label>
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search by item name..."
                className="w-full px-3 py-2 border border-gray-300 rounded-[8px] focus:outline-none focus:ring-2 focus:ring-[#A7C4A0]"
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Supplier
              </label>
              <input
                type="text"
                value={supplierFilter}
                onChange={(e) => setSupplierFilter(e.target.value)}
                placeholder="Filter by supplier..."
                className="w-full px-3 py-2 border border-gray-300 rounded-[8px] focus:outline-none focus:ring-2 focus:ring-[#A7C4A0]"
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Venue
              </label>
              <input
                type="text"
                value={venueFilter}
                onChange={(e) => setVenueFilter(e.target.value)}
                placeholder="Filter by venue..."
                className="w-full px-3 py-2 border border-gray-300 rounded-[8px] focus:outline-none focus:ring-2 focus:ring-[#A7C4A0]"
              />
            </div>
            
            <div className="flex items-end">
              <label className="flex items-center">
                <input
                  type="checkbox"
                  checked={onlyLongHistory}
                  onChange={(e) => setOnlyLongHistory(e.target.checked)}
                  className="rounded border-gray-300 text-blue-600 focus:ring-[#A7C4A0]"
                />
                <span className="ml-2 text-sm text-gray-700">Only 12+ months history</span>
              </label>
            </div>
          </div>
        </div>

        {/* Main Content */}
        <div className="grid grid-cols-7 gap-6">
          {/* Left Panel - Items List */}
          <div className="col-span-3">
            <div className="bg-white rounded-[12px] border border-[#E5E7EB] shadow-sm p-3">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">Items</h3>
              
              <div className="space-y-2 max-h-96 overflow-y-auto">
                {summary?.items && summary.items.length > 0 ? (
                  summary.items.map((item) => (
                    <ItemForecastCard
                      key={item.item_id}
                      item={item}
                      isSelected={selectedItem?.item_id === item.item_id}
                      onClick={() => handleItemSelect(item)}
                    />
                  ))
                ) : (
                  <div className="text-center py-8 text-gray-500">
                    <p>No forecast items found</p>
                  </div>
                )}
              </div>
            </div>
          </div>
          
          {/* Right Panel - Forecast Details */}
          <div className="col-span-4 space-y-6">
            {selectedForecast ? (
              <>
                <ForecastChart forecast={selectedForecast} />
                <div className="grid grid-cols-2 gap-6">
                  <ScenarioControls onScenarioChange={handleScenarioChange} />
                  <QualityPanel quality={quality} />
                </div>
              </>
            ) : (
              <div className="bg-white rounded-[12px] p-8 text-center shadow-sm">
                <div className="text-gray-400 mb-4">
                  <svg className="mx-auto h-12 w-12" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                  </svg>
                </div>
                <h3 className="text-lg font-medium text-gray-900 mb-2">
                  Select an Item
                </h3>
                <p className="text-gray-600">
                  Choose an item from the list to view detailed forecasts and scenarios.
                </p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default ForecastWorkspace; 