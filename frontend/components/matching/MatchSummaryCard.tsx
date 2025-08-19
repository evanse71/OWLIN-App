import React from 'react';
import { MatchingSummary, MatchingPair } from '../../types/matching';

interface MatchSummaryCardProps {
  summary: MatchingSummary | null;
  selectedPair: MatchingPair | null;
  onPairSelect: (pair: MatchingPair) => void;
  stateFilter: string;
  supplierFilter: string;
  searchQuery: string;
}

const MatchSummaryCard: React.FC<MatchSummaryCardProps> = ({
  summary,
  selectedPair,
  onPairSelect,
  stateFilter,
  supplierFilter,
  searchQuery
}) => {
  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 75) return '#10B981'; // Green
    if (confidence >= 50) return '#F59E0B'; // Amber
    return '#EF4444'; // Red
  };

  const getStatusBadgeClass = (status: string) => {
    switch (status) {
      case 'matched':
        return 'bg-[#ECFDF5] text-[#065F46] border border-[#D1FAE5]';
      case 'partial':
        return 'bg-[#FEF3C7] text-[#92400E] border border-[#FDE68A]';
      case 'conflict':
        return 'bg-[#F3F4F6] text-[#374151] border border-[#E5E7EB]';
      case 'unmatched':
        return 'bg-[#FEE2E2] text-[#7F1D1D] border border-[#FECACA]';
      default:
        return 'bg-[#F3F4F6] text-[#374151] border border-[#E5E7EB]';
    }
  };

  const filteredPairs = summary?.pairs.filter(pair => {
    if (stateFilter !== 'all' && pair.status !== stateFilter) return false;
    if (supplierFilter && !pair.reasons.some(r => r.detail.includes(supplierFilter))) return false;
    if (searchQuery && !pair.id.includes(searchQuery)) return false;
    return true;
  }) || [];

  return (
    <div className="bg-white rounded-[12px] border border-[#E5E7EB] shadow-sm p-3">
      {/* Totals */}
      <div className="mb-4">
        <h3 className="text-lg font-semibold text-gray-900 mb-3">Matching Summary</h3>
        <div className="grid grid-cols-2 gap-2">
          {summary?.totals && Object.entries(summary.totals).map(([status, count]) => (
            <div key={status} className="flex items-center justify-between p-2 rounded-[8px] bg-gray-50">
              <span className="text-sm font-medium text-gray-700 capitalize">{status}</span>
              <span className="text-sm text-gray-900 font-semibold">{count}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Pairs List */}
      <div className="space-y-2 max-h-96 overflow-y-auto">
        {filteredPairs.length === 0 ? (
          <div className="text-center py-8 text-gray-500">
            <p>No matching pairs found</p>
          </div>
        ) : (
          filteredPairs.map((pair) => (
            <div
              key={pair.id}
              onClick={() => onPairSelect(pair)}
              className={`flex items-center justify-between gap-2 p-2 rounded-[8px] hover:bg-[#F9FAFB] cursor-pointer transition-colors ${
                selectedPair?.id === pair.id ? 'bg-blue-50 border border-blue-200' : ''
              }`}
            >
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1">
                  {/* Link Icon */}
                  <svg 
                    xmlns="http://www.w3.org/2000/svg" 
                    width="14" 
                    height="14" 
                    fill="none" 
                    stroke="#6B7280" 
                    strokeWidth="2" 
                    strokeLinecap="round" 
                    strokeLinejoin="round" 
                    aria-label="Linked"
                  >
                    <path d="M4.5 9a2.5 2.5 0 0 1 0-5h2"/>
                    <path d="M9.5 10a2.5 2.5 0 0 0 0-5h-2"/>
                  </svg>
                  
                  <span className="text-sm font-medium text-gray-900">
                    INV-{pair.invoice_id}
                  </span>
                  <span className="text-gray-400">→</span>
                  <span className="text-sm font-medium text-gray-900">
                    DN-{pair.delivery_note_id}
                  </span>
                </div>
                
                <div className="flex items-center gap-2">
                  <span className={`text-[12px] px-2 py-0.5 rounded-[6px] ${getStatusBadgeClass(pair.status)}`}>
                    {pair.status}
                  </span>
                  
                  <div 
                    className="text-[12px] px-2 py-0.5 rounded-[6px] text-white font-medium"
                    style={{ backgroundColor: getConfidenceColor(pair.confidence) }}
                  >
                    {Math.round(pair.confidence)}%
                  </div>
                </div>
              </div>
              
              <div className="text-xs text-gray-500">
                {new Date().toLocaleDateString()}
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
};

export default MatchSummaryCard; 