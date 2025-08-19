import React, { useState } from 'react';
import { MatchCandidate } from '../../types/matching';
import matchingOfflineQueue from '../../lib/matchingOfflineQueue';

interface DocumentPairingSuggestionCardProps {
  invoice: {
    id: string;
    supplier_name: string;
    invoice_date: string;
    total_amount: number;
    line_items: Array<{
      description: string;
      qty: number;
      unit_price: number;
      total: number;
    }>;
  };
  candidate: MatchCandidate;
  onConfirm: (invoiceId: string, deliveryNoteId: string) => void;
  onReject: (invoiceId: string, deliveryNoteId: string) => void;
  onSkip: () => void;
}

const DocumentPairingSuggestionCard: React.FC<DocumentPairingSuggestionCardProps> = ({
  invoice,
  candidate,
  onConfirm,
  onReject,
  onSkip
}) => {
  const [isLoading, setIsLoading] = useState(false);
  const [showBreakdown, setShowBreakdown] = useState(false);

  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 80) return '#6BA368'; // High - desaturated green
    if (confidence >= 60) return '#D9A441'; // Medium - muted amber
    return '#C16C5B'; // Low - muted red
  };

  const getConfidenceLabel = (confidence: number) => {
    if (confidence >= 80) return 'High';
    if (confidence >= 60) return 'Medium';
    return 'Low';
  };

  const handleConfirm = async () => {
    setIsLoading(true);
    try {
      if (matchingOfflineQueue.isOnlineStatus()) {
        await onConfirm(invoice.id, candidate.delivery_note_id);
      } else {
        // Queue for offline processing
        await matchingOfflineQueue.addToQueue('confirm', invoice.id, candidate.delivery_note_id);
        // Optimistic update
        onConfirm(invoice.id, candidate.delivery_note_id);
      }
    } finally {
      setIsLoading(false);
    }
  };

  const handleReject = async () => {
    setIsLoading(true);
    try {
      if (matchingOfflineQueue.isOnlineStatus()) {
        await onReject(invoice.id, candidate.delivery_note_id);
      } else {
        // Queue for offline processing
        await matchingOfflineQueue.addToQueue('reject', invoice.id, candidate.delivery_note_id);
        // Optimistic update
        onReject(invoice.id, candidate.delivery_note_id);
      }
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyPress = (event: React.KeyboardEvent) => {
    if (event.key === 'Enter') {
      handleConfirm();
    } else if (event.key === 'Backspace') {
      handleReject();
    } else if (event.key === 'ArrowRight') {
      onSkip();
    }
  };

  return (
    <div 
      className="bg-white border border-gray-200 rounded-[12px] p-6 shadow-sm"
      onKeyDown={handleKeyPress}
      tabIndex={0}
    >
      <div className="grid grid-cols-3 gap-6">
        {/* Left Column - Invoice Details */}
        <div className="space-y-4">
          <h3 className="text-lg font-semibold text-gray-900">Invoice</h3>
          
          <div className="space-y-2">
            <div>
              <span className="text-sm font-medium text-gray-700">Supplier:</span>
              <p className="text-sm text-gray-900">{invoice.supplier_name}</p>
            </div>
            
            <div>
              <span className="text-sm font-medium text-gray-700">Date:</span>
              <p className="text-sm text-gray-900">
                {new Date(invoice.invoice_date).toLocaleDateString()}
              </p>
            </div>
            
            <div>
              <span className="text-sm font-medium text-gray-700">Total:</span>
              <p className="text-sm text-gray-900">
                £{(invoice.total_amount / 100).toFixed(2)}
              </p>
            </div>
          </div>

          {/* Invoice Line Items */}
          <div>
            <h4 className="text-sm font-medium text-gray-700 mb-2">Line Items</h4>
            <div className="space-y-1 max-h-32 overflow-y-auto">
              {invoice.line_items.map((item, index) => (
                <div key={index} className="text-xs text-gray-600 p-1 bg-gray-50 rounded">
                  {item.description} - {item.qty} × £{(item.unit_price / 100).toFixed(2)}
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Middle Column - Confidence Score */}
        <div className="flex flex-col items-center justify-center space-y-4">
          <div className="text-center">
            <div 
              className="w-24 h-24 rounded-full flex items-center justify-center text-white font-bold text-lg shadow-lg"
              style={{ backgroundColor: getConfidenceColor(candidate.confidence) }}
            >
              {Math.round(candidate.confidence)}%
            </div>
            <p className="text-sm font-medium mt-2" style={{ color: getConfidenceColor(candidate.confidence) }}>
              {getConfidenceLabel(candidate.confidence)} Confidence
            </p>
          </div>

          {/* Confidence Breakdown Button */}
          <button
            onClick={() => setShowBreakdown(true)}
            className="text-xs text-blue-600 hover:text-blue-800 underline"
          >
            View Breakdown
          </button>
        </div>

        {/* Right Column - Delivery Note Details */}
        <div className="space-y-4">
          <h3 className="text-lg font-semibold text-gray-900">Delivery Note</h3>
          
          {candidate.delivery_note && (
            <>
              <div className="space-y-2">
                <div>
                  <span className="text-sm font-medium text-gray-700">Supplier:</span>
                  <p className="text-sm text-gray-900">{candidate.delivery_note.supplier_name}</p>
                </div>
                
                <div>
                  <span className="text-sm font-medium text-gray-700">Date:</span>
                  <p className="text-sm text-gray-900">
                    {new Date(candidate.delivery_note.delivery_date).toLocaleDateString()}
                  </p>
                </div>
                
                <div>
                  <span className="text-sm font-medium text-gray-700">Total:</span>
                  <p className="text-sm text-gray-900">
                    £{(candidate.delivery_note.total_amount / 100).toFixed(2)}
                  </p>
                </div>
              </div>

              {/* Delivery Note Line Items */}
              <div>
                <h4 className="text-sm font-medium text-gray-700 mb-2">Line Items</h4>
                <div className="space-y-1 max-h-32 overflow-y-auto">
                  {candidate.delivery_note.items?.map((item: any, index: number) => (
                    <div key={index} className="text-xs text-gray-600 p-1 bg-gray-50 rounded">
                      {item.description} - {item.qty} × £{(item.unit_price / 100).toFixed(2)}
                    </div>
                  ))}
                </div>
              </div>
            </>
          )}
        </div>
      </div>

      {/* Footer Controls */}
      <div className="flex justify-between items-center mt-6 pt-4 border-t border-gray-200">
        <div className="text-xs text-gray-500">
          Press Enter to confirm, Backspace to reject, or → to skip
        </div>
        
        <div className="flex space-x-2">
          <button
            onClick={onSkip}
            disabled={isLoading}
            className="px-3 py-2 text-sm text-gray-600 border border-gray-300 rounded-[8px] hover:bg-gray-50 disabled:opacity-50"
          >
            Skip ⏭
          </button>
          
          <button
            onClick={handleReject}
            disabled={isLoading}
            className="px-3 py-2 text-sm text-red-600 border border-red-300 rounded-[8px] hover:bg-red-50 disabled:opacity-50"
          >
            Reject ❌
          </button>
          
          <button
            onClick={handleConfirm}
            disabled={isLoading}
            className="px-3 py-2 text-sm text-white bg-green-600 border border-green-600 rounded-[8px] hover:bg-green-700 disabled:opacity-50"
          >
            {isLoading ? 'Confirming...' : 'Confirm ✅'}
          </button>
        </div>
      </div>

      {/* Confidence Breakdown Modal */}
      {showBreakdown && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-[12px] p-6 max-w-md w-full mx-4">
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-lg font-semibold text-gray-900">Confidence Breakdown</h3>
              <button
                onClick={() => setShowBreakdown(false)}
                className="text-gray-400 hover:text-gray-600"
              >
                ✕
              </button>
            </div>
            
            <div className="space-y-4">
              <div className="flex justify-between items-center p-3 bg-gray-50 rounded-lg">
                <div>
                  <div className="font-medium text-gray-900">Supplier Match</div>
                  <div className="text-sm text-gray-600">Exact name match, partial match, or alias</div>
                </div>
                <div className="text-right">
                  <div className="font-bold text-gray-900">{candidate.breakdown.supplier.toFixed(1)}/40</div>
                  <div className="text-xs text-gray-500">points</div>
                </div>
              </div>
              
              <div className="flex justify-between items-center p-3 bg-gray-50 rounded-lg">
                <div>
                  <div className="font-medium text-gray-900">Date Proximity</div>
                  <div className="text-sm text-gray-600">Same date (25), ±1 day (20), ±3 days (10)</div>
                </div>
                <div className="text-right">
                  <div className="font-bold text-gray-900">{candidate.breakdown.date.toFixed(1)}/25</div>
                  <div className="text-xs text-gray-500">points</div>
                </div>
              </div>
              
              <div className="flex justify-between items-center p-3 bg-gray-50 rounded-lg">
                <div>
                  <div className="font-medium text-gray-900">Line Item Overlap</div>
                  <div className="text-sm text-gray-600">% of matched SKUs × 30</div>
                </div>
                <div className="text-right">
                  <div className="font-bold text-gray-900">{candidate.breakdown.line_items.toFixed(1)}/30</div>
                  <div className="text-xs text-gray-500">points</div>
                </div>
              </div>
              
              <div className="flex justify-between items-center p-3 bg-gray-50 rounded-lg">
                <div>
                  <div className="font-medium text-gray-900">Value Match</div>
                  <div className="text-sm text-gray-600">±2% total value difference = full 5 points</div>
                </div>
                <div className="text-right">
                  <div className="font-bold text-gray-900">{candidate.breakdown.value.toFixed(1)}/5</div>
                  <div className="text-xs text-gray-500">points</div>
                </div>
              </div>
              
              <div className="border-t pt-4">
                <div className="flex justify-between items-center">
                  <div className="font-bold text-gray-900">Total Score</div>
                  <div className="font-bold text-lg" style={{ color: getConfidenceColor(candidate.confidence) }}>
                    {Math.round(candidate.confidence)}/100
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default DocumentPairingSuggestionCard; 