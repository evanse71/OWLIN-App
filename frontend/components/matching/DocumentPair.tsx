import React from 'react';
import { MatchingPair } from '../../types/matching';
import LineReconcileTable from './LineReconcileTable';
import AutoApplyBar from './AutoApplyBar';

interface DocumentPairProps {
  pair: MatchingPair;
  onAccept: (pairId: string) => void;
  onOverride: (pairId: string, deliveryNoteId: string) => void;
}

const DocumentPair: React.FC<DocumentPairProps> = ({
  pair,
  onAccept,
  onOverride
}) => {
  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 75) return '#10B981'; // Green
    if (confidence >= 50) return '#F59E0B'; // Amber
    return '#EF4444'; // Red
  };

  return (
    <div className="bg-white rounded-[12px] border border-[#E5E7EB] shadow-sm">
      {/* Header */}
      <div className="p-6 border-b border-gray-200">
        <div className="grid grid-cols-2 gap-3">
          {/* Invoice Card */}
          <div className="bg-gray-50 rounded-[8px] p-4">
            <h4 className="font-semibold text-gray-900 mb-2">Invoice #{pair.invoice_id}</h4>
            <div className="space-y-1 text-sm text-gray-600">
              <div>Date: {new Date().toLocaleDateString()}</div>
              <div>Total: £0.00</div>
              <div>Venue: Main Venue</div>
            </div>
          </div>
          
          {/* Delivery Note Card */}
          <div className="bg-gray-50 rounded-[8px] p-4">
            <h4 className="font-semibold text-gray-900 mb-2">Delivery Note #{pair.delivery_note_id}</h4>
            <div className="space-y-1 text-sm text-gray-600">
              <div>Date: {new Date().toLocaleDateString()}</div>
              <div>Total: £0.00</div>
              <div>Venue: Main Venue</div>
            </div>
          </div>
        </div>
        
        {/* Confidence and Status */}
        <div className="mt-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div 
              className="text-sm px-3 py-1 rounded-[6px] text-white font-medium"
              style={{ backgroundColor: getConfidenceColor(pair.confidence) }}
            >
              {Math.round(pair.confidence)}% Confidence
            </div>
            <span className={`text-[12px] px-2 py-1 rounded-[6px] ${
              pair.status === 'matched' ? 'bg-[#ECFDF5] text-[#065F46] border border-[#D1FAE5]' :
              pair.status === 'partial' ? 'bg-[#FEF3C7] text-[#92400E] border border-[#FDE68A]' :
              pair.status === 'conflict' ? 'bg-[#F3F4F6] text-[#374151] border border-[#E5E7EB]' :
              'bg-[#FEE2E2] text-[#7F1D1D] border border-[#FECACA]'
            }`}>
              {pair.status}
            </span>
          </div>
          
          <div className="flex gap-2">
            <button
              onClick={() => onAccept(pair.id)}
              className="px-3 py-1.5 bg-[#2563EB] text-white hover:bg-[#1D4ED8] rounded-[8px] text-sm"
            >
              Accept Pair
            </button>
            <button
              onClick={() => onOverride(pair.id, pair.delivery_note_id.toString())}
              className="px-3 py-1.5 bg-white text-[#374151] border border-[#E5E7EB] hover:bg-[#F9FAFB] rounded-[8px] text-sm"
            >
              Override DN...
            </button>
          </div>
        </div>
      </div>
      
      {/* Reasons */}
      {pair.reasons.length > 0 && (
        <div className="p-6 border-b border-gray-200">
          <h5 className="font-medium text-gray-900 mb-3">Matching Reasons</h5>
          <div className="flex flex-wrap gap-2">
            {pair.reasons.map((reason, index) => (
              <span
                key={index}
                className="text-[12px] bg-[#F3F4F6] text-[#374151] border border-[#E5E7EB] rounded-[6px] px-2 py-1"
                title={reason.detail}
              >
                {reason.code}
              </span>
            ))}
          </div>
        </div>
      )}
      
      {/* Line Reconciliation Table */}
      <div className="p-6">
        <LineReconcileTable lineDiffs={pair.line_diffs} />
      </div>
      
      {/* Auto Apply Bar */}
      <AutoApplyBar pair={pair} />
    </div>
  );
};

export default DocumentPair; 