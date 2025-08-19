import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
import MatchSummaryCard from '../../components/matching/MatchSummaryCard';
import DocumentPair from '../../components/matching/DocumentPair';
import { MatchingSummary, MatchingPair } from '../../types/matching';

const MatchingWorkbench: React.FC = () => {
  const router = useRouter();
  const [summary, setSummary] = useState<MatchingSummary | null>(null);
  const [selectedPair, setSelectedPair] = useState<MatchingPair | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  // Filters
  const [stateFilter, setStateFilter] = useState('all');
  const [supplierFilter, setSupplierFilter] = useState('');
  const [dateWindow, setDateWindow] = useState(21);
  const [searchQuery, setSearchQuery] = useState('');

  useEffect(() => {
    loadMatchingSummary();
  }, [stateFilter, dateWindow]);

  const loadMatchingSummary = async () => {
    try {
      setIsLoading(true);
      setError(null);
      
      const response = await fetch(`/api/matching/summary?state=${stateFilter}&limit=50`);
      if (!response.ok) {
        throw new Error('Failed to load matching summary');
      }
      
      const data = await response.json();
      setSummary(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setIsLoading(false);
    }
  };

  const handleRebuild = async () => {
    try {
      const response = await fetch('/api/matching/rebuild', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ days: dateWindow })
      });
      
      if (!response.ok) {
        throw new Error('Failed to rebuild matching');
      }
      
      await loadMatchingSummary();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    }
  };

  const handlePairSelect = (pair: MatchingPair) => {
    setSelectedPair(pair);
  };

  const handleAcceptPair = async (pairId: string) => {
    try {
      const response = await fetch(`/api/matching/pair/${pairId}/accept`, {
        method: 'POST'
      });
      
      if (!response.ok) {
        throw new Error('Failed to accept pair');
      }
      
      await loadMatchingSummary();
      setSelectedPair(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    }
  };

  const handleOverridePair = async (pairId: string, deliveryNoteId: string) => {
    try {
      const response = await fetch(`/api/matching/pair/${pairId}/override`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ delivery_note_id: deliveryNoteId })
      });
      
      if (!response.ok) {
        throw new Error('Failed to override pair');
      }
      
      await loadMatchingSummary();
      setSelectedPair(null);
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
            <div className="grid grid-cols-5 gap-6">
              <div className="col-span-2 h-96 bg-gray-200 rounded"></div>
              <div className="col-span-3 h-96 bg-gray-200 rounded"></div>
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
                Invoice ↔ Delivery Note Matching
              </h1>
              <p className="text-gray-600 mt-1">
                Review and resolve matching pairs with confidence scoring
              </p>
            </div>
            
            <div className="flex space-x-4">
              <button
                onClick={handleRebuild}
                className="px-4 py-2 bg-blue-600 text-white rounded-[8px] hover:bg-blue-700"
              >
                Rebuild Matching
              </button>
            </div>
          </div>
        </div>

        {/* Error Banner */}
        {error && (
          <div className="bg-amber-50 border border-amber-200 rounded-[12px] p-4">
            <div className="flex">
              <div className="flex-shrink-0">
                <svg className="h-5 w-5 text-amber-400" viewBox="0 0 20 20" fill="currentColor">
                  <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                </svg>
              </div>
              <div className="ml-3">
                <p className="text-sm text-amber-800">{error}</p>
              </div>
              <div className="ml-auto pl-3">
                <button
                  onClick={() => setError(null)}
                  className="text-amber-400 hover:text-amber-600"
                >
                  <span className="sr-only">Dismiss</span>
                  <svg className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                    <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
                  </svg>
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Filters */}
        <div className="bg-white rounded-[12px] p-4 shadow-sm">
          <div className="grid grid-cols-4 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                State
              </label>
              <select
                value={stateFilter}
                onChange={(e) => setStateFilter(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-[8px] focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="all">All States</option>
                <option value="matched">Matched</option>
                <option value="partial">Partial</option>
                <option value="conflict">Conflict</option>
                <option value="unmatched">Unmatched</option>
              </select>
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Date Window
              </label>
              <select
                value={dateWindow}
                onChange={(e) => setDateWindow(Number(e.target.value))}
                className="w-full px-3 py-2 border border-gray-300 rounded-[8px] focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value={7}>Last 7 days</option>
                <option value={14}>Last 14 days</option>
                <option value={21}>Last 21 days</option>
                <option value={30}>Last 30 days</option>
              </select>
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
                className="w-full px-3 py-2 border border-gray-300 rounded-[8px] focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Search
              </label>
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Invoice or DN number..."
                className="w-full px-3 py-2 border border-gray-300 rounded-[8px] focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
          </div>
        </div>

        {/* Main Content */}
        <div className="grid grid-cols-5 gap-6">
          {/* Left Panel - Summary */}
          <div className="col-span-2">
            <MatchSummaryCard
              summary={summary}
              selectedPair={selectedPair}
              onPairSelect={handlePairSelect}
              stateFilter={stateFilter}
              supplierFilter={supplierFilter}
              searchQuery={searchQuery}
            />
          </div>
          
          {/* Right Panel - Document Pair */}
          <div className="col-span-3">
            {selectedPair ? (
              <DocumentPair
                pair={selectedPair}
                onAccept={handleAcceptPair}
                onOverride={handleOverridePair}
              />
            ) : (
              <div className="bg-white rounded-[12px] p-8 text-center shadow-sm">
                <div className="text-gray-400 mb-4">
                  <svg className="mx-auto h-12 w-12" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                </div>
                <h3 className="text-lg font-medium text-gray-900 mb-2">
                  Select a Pair
                </h3>
                <p className="text-gray-600">
                  Choose a matching pair from the list to view details and resolve issues.
                </p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default MatchingWorkbench; 