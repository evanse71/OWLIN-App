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

interface AgentCreditSuggestionBoxProps {
  suggestion: CreditSuggestion;
  onAccept: (suggestion: CreditSuggestion) => void;
  onEdit: (suggestion: CreditSuggestion) => void;
  onCopy: (suggestion: CreditSuggestion) => void;
  userRole: 'gm' | 'finance' | 'shift';
}

const AgentCreditSuggestionBox: React.FC<AgentCreditSuggestionBoxProps> = ({
  suggestion,
  onAccept,
  onEdit,
  onCopy,
  userRole
}) => {
  const [isCopied, setIsCopied] = useState(false);

  // Only show for finance users
  if (userRole !== 'finance') {
    return null;
  }

  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 80) return 'bg-green-100 text-green-800';
    if (confidence >= 60) return 'bg-yellow-100 text-yellow-800';
    return 'bg-gray-100 text-gray-800';
  };

  const handleCopy = async () => {
    try {
      const creditText = `Suggested credit: £${suggestion.suggested_credit.toFixed(2)}. ${suggestion.reason}`;
      await navigator.clipboard.writeText(creditText);
      setIsCopied(true);
      onCopy(suggestion);
      
      // Reset copied state after 2 seconds
      setTimeout(() => setIsCopied(false), 2000);
    } catch (error) {
      console.error('Failed to copy to clipboard:', error);
    }
  };

  const handleAccept = () => {
    onAccept(suggestion);
  };

  const handleEdit = () => {
    onEdit(suggestion);
  };

  return (
    <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 mt-2">
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <div className="flex items-center space-x-2 mb-2">
            <div className="w-5 h-5 bg-blue-100 rounded-full flex items-center justify-center">
              <svg className="w-3 h-3 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1" />
              </svg>
            </div>
            <h4 className="text-sm font-semibold text-blue-900">
              💸 Suggested Credit: £{suggestion.suggested_credit.toFixed(2)}
            </h4>
            <span
              className={`px-2 py-1 rounded-full text-xs font-medium ${getConfidenceColor(
                suggestion.confidence
              )}`}
            >
              {suggestion.confidence}% {suggestion.confidence_label}
            </span>
          </div>
          
          <p className="text-xs text-blue-800 mb-2">
            📎 {suggestion.reason}
          </p>
          
          <div className="text-xs text-blue-700 space-y-1">
            <div className="flex items-center space-x-2">
              <span className="font-medium">Price source:</span>
              <span>{suggestion.price_source}</span>
            </div>
            {suggestion.vat_amount > 0 && (
              <div className="flex items-center space-x-2">
                <span className="font-medium">VAT included:</span>
                <span>£{suggestion.vat_amount.toFixed(2)}</span>
              </div>
            )}
          </div>
        </div>
      </div>
      
      <div className="flex space-x-2 mt-3">
        <button
          onClick={handleAccept}
          className="px-3 py-1 bg-blue-600 text-white text-xs font-medium rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 transition-colors"
        >
          ✅ Accept
        </button>
        <button
          onClick={handleEdit}
          className="px-3 py-1 bg-white border border-blue-300 text-blue-700 text-xs font-medium rounded-md hover:bg-blue-50 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 transition-colors"
        >
          ✏️ Edit
        </button>
        <button
          onClick={handleCopy}
          className="px-3 py-1 bg-white border border-blue-300 text-blue-700 text-xs font-medium rounded-md hover:bg-blue-50 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 transition-colors"
        >
          {isCopied ? '📋 Copied!' : '📤 Copy'}
        </button>
      </div>
    </div>
  );
};

export default AgentCreditSuggestionBox; 