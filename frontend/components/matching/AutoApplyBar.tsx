import React, { useState } from 'react';
import { MatchingPair } from '../../types/matching';

interface AutoApplyBarProps {
  pair: MatchingPair;
}

const AutoApplyBar: React.FC<AutoApplyBarProps> = ({ pair }) => {
  const [autoAcceptQty, setAutoAcceptQty] = useState(true);
  const [autoAcceptPrice, setAutoAcceptPrice] = useState(false);
  const [autoSplit, setAutoSplit] = useState(false);

  const hasMismatches = pair.line_diffs.some(diff => 
    diff.status === 'qty_mismatch' || diff.status === 'price_mismatch' || diff.status.includes('missing')
  );

  if (!hasMismatches) {
    return null;
  }

  const handleApply = async () => {
    // TODO: Implement batch apply logic
    console.log('Applying auto-actions:', {
      autoAcceptQty,
      autoAcceptPrice,
      autoSplit
    });
  };

  return (
    <div className="fixed bottom-0 right-0 left-0 max-w-[1100px] mx-auto bg-white border-t border-[#E5E7EB] p-2 rounded-t-[12px] shadow-sm">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-6">
          <div className="flex items-center gap-2">
            <input
              type="checkbox"
              id="auto-qty"
              checked={autoAcceptQty}
              onChange={(e) => setAutoAcceptQty(e.target.checked)}
              className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
            />
            <label htmlFor="auto-qty" className="text-sm text-gray-700">
              Auto-accept qty within tolerance
            </label>
          </div>
          
          <div className="flex items-center gap-2">
            <input
              type="checkbox"
              id="auto-price"
              checked={autoAcceptPrice}
              onChange={(e) => setAutoAcceptPrice(e.target.checked)}
              className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
            />
            <label htmlFor="auto-price" className="text-sm text-gray-700">
              Auto-accept price within tolerance
            </label>
          </div>
          
          <div className="flex items-center gap-2">
            <input
              type="checkbox"
              id="auto-split"
              checked={autoSplit}
              onChange={(e) => setAutoSplit(e.target.checked)}
              className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
            />
            <label htmlFor="auto-split" className="text-sm text-gray-700">
              Auto-split partial deliveries
            </label>
          </div>
        </div>
        
        <button
          onClick={handleApply}
          className="px-4 py-2 bg-[#2563EB] text-white hover:bg-[#1D4ED8] rounded-[8px] text-sm font-medium"
        >
          Apply
        </button>
      </div>
    </div>
  );
};

export default AutoApplyBar; 