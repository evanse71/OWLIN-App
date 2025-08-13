import React, { useState } from 'react';

interface CreditSuggestion {
  suggested_credit: number;
  confidence: number;
  confidence_label: string;
  reason: string;
  base_price: number;
  quantity_delta: number;
  vat_amount: number;
  price_source: string;
  item_name: string;
}

interface AgentCreditSummaryBoxProps {
  suggestions: CreditSuggestion[];
  onAcceptAll: (suggestions: CreditSuggestion[]) => void;
  onCopyAll: (suggestions: CreditSuggestion[]) => void;
  userRole: 'gm' | 'finance' | 'shift';
}

const AgentCreditSummaryBox: React.FC<AgentCreditSummaryBoxProps> = ({
  suggestions,
  onAcceptAll,
  onCopyAll,
  userRole
}) => {
  const [isCopied, setIsCopied] = useState(false);

  // Only show for finance users
  if (userRole !== 'finance' || suggestions.length === 0) {
    return null;
  }

  const totalCredit = suggestions.reduce((sum, suggestion) => sum + suggestion.suggested_credit, 0);
  const averageConfidence = Math.round(
    suggestions.reduce((sum, suggestion) => sum + suggestion.confidence, 0) / suggestions.length
  );

  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 80) return 'bg-green-100 text-green-800';
    if (confidence >= 60) return 'bg-yellow-100 text-yellow-800';
    return 'bg-gray-100 text-gray-800';
  };

  const handleCopyAll = async () => {
    try {
      const creditText = suggestions.map(suggestion => 
        `${suggestion.item_name}: £${suggestion.suggested_credit.toFixed(2)} - ${suggestion.reason}`
      ).join('\n');
      
      const summaryText = `Total suggested credits: £${totalCredit.toFixed(2)}\n\n${creditText}`;
      await navigator.clipboard.writeText(summaryText);
      setIsCopied(true);
      onCopyAll(suggestions);
      
      // Reset copied state after 2 seconds
      setTimeout(() => setIsCopied(false), 2000);
    } catch (error) {
      console.error('Failed to copy to clipboard:', error);
    }
  };

  const handleAcceptAll = () => {
    onAcceptAll(suggestions);
  };

  return (
    <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-4">
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center space-x-2">
          <div className="w-6 h-6 bg-blue-100 rounded-full flex items-center justify-center">
            <svg className="w-4 h-4 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1" />
            </svg>
          </div>
          <h3 className="text-sm font-semibold text-blue-900">
            💰 Credit Suggestions Summary
          </h3>
          <span
            className={`px-2 py-1 rounded-full text-xs font-medium ${getConfidenceColor(
              averageConfidence
            )}`}
          >
            {averageConfidence}% avg confidence
          </span>
        </div>
      </div>
      
      <div className="mb-3">
        <div className="text-sm text-blue-900 mb-2">
          <strong>Total Suggested Credit:</strong> £{totalCredit.toFixed(2)}
        </div>
        <div className="text-xs text-blue-700">
          {suggestions.length} item{suggestions.length !== 1 ? 's' : ''} with issues detected
        </div>
      </div>
      
      <div className="space-y-2 mb-3">
        {suggestions.map((suggestion, index) => (
          <div key={index} className="bg-white rounded border border-blue-200 p-2">
            <div className="flex items-center justify-between">
              <div className="flex-1">
                <div className="text-xs font-medium text-blue-900">
                  {suggestion.item_name}
                </div>
                <div className="text-xs text-blue-700">
                  £{suggestion.suggested_credit.toFixed(2)} - {suggestion.reason}
                </div>
              </div>
              <span
                className={`px-2 py-1 rounded-full text-xs font-medium ${getConfidenceColor(
                  suggestion.confidence
                )}`}
              >
                {suggestion.confidence}%
              </span>
            </div>
          </div>
        ))}
      </div>
      
      <div className="flex space-x-2">
        <button
          onClick={handleAcceptAll}
          className="px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 transition-colors"
        >
          ✅ Accept All Credits
        </button>
        <button
          onClick={handleCopyAll}
          className="px-4 py-2 bg-white border border-blue-300 text-blue-700 text-sm font-medium rounded-md hover:bg-blue-50 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 transition-colors"
        >
          {isCopied ? '📋 Copied!' : '📤 Copy All'}
        </button>
      </div>
    </div>
  );
};

export default AgentCreditSummaryBox; 