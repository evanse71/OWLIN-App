import React, { useState } from 'react';

interface SupplierMetrics {
  supplierId: string;
  supplierName: string;
  mismatchRate: number;
  avgConfidence: number;
  lateDeliveryRate: number;
  flaggedIssueCount: number;
  totalInvoices: number;
  recentIssues: string[];
}

interface AgentEscalationBannerProps {
  supplierMetrics: SupplierMetrics;
  onEscalate: (supplierId: string, reason: string) => void;
  onViewHistory: (supplierId: string) => void;
  onDismiss: () => void;
  userRole: 'gm' | 'finance' | 'shift';
}

const AgentEscalationBanner: React.FC<AgentEscalationBannerProps> = ({
  supplierMetrics,
  onEscalate,
  onViewHistory,
  onDismiss,
  userRole
}) => {
  const [isDismissed, setIsDismissed] = useState(false);

  // Only show for GMs
  if (userRole !== 'gm' || isDismissed) {
    return null;
  }

  const getEscalationReason = (metrics: SupplierMetrics): string => {
    const reasons: string[] = [];
    
    if (metrics.mismatchRate > 25 && metrics.totalInvoices >= 3) {
      reasons.push(`${Math.round(metrics.mismatchRate)}% delivery mismatch rate`);
    }
    
    if (metrics.avgConfidence < 60) {
      reasons.push(`low confidence (${Math.round(metrics.avgConfidence)}%)`);
    }
    
    if (metrics.lateDeliveryRate > 40) {
      reasons.push(`${Math.round(metrics.lateDeliveryRate)}% late delivery rate`);
    }
    
    if (metrics.flaggedIssueCount >= 5) {
      reasons.push(`${metrics.flaggedIssueCount} flagged issues in 30 days`);
    }
    
    return reasons.join(', ');
  };

  const getPrimaryIssue = (metrics: SupplierMetrics): string => {
    if (metrics.mismatchRate > 25 && metrics.totalInvoices >= 3) {
      return `${Math.round(metrics.mismatchRate)}% of their deliveries have mismatches`;
    }
    if (metrics.flaggedIssueCount >= 5) {
      return `${metrics.flaggedIssueCount} issues flagged in the last 30 days`;
    }
    if (metrics.lateDeliveryRate > 40) {
      return `${Math.round(metrics.lateDeliveryRate)}% of their deliveries are late`;
    }
    if (metrics.avgConfidence < 60) {
      return `consistently low confidence (${Math.round(metrics.avgConfidence)}%)`;
    }
    return 'multiple quality issues detected';
  };

  const handleEscalate = () => {
    const reason = getEscalationReason(supplierMetrics);
    onEscalate(supplierMetrics.supplierId, reason);
    setIsDismissed(true);
  };

  const handleViewHistory = () => {
    onViewHistory(supplierMetrics.supplierId);
  };

  const handleDismiss = () => {
    setIsDismissed(true);
    onDismiss();
  };

  return (
    <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-4">
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <div className="flex items-center space-x-2 mb-2">
            <div className="w-6 h-6 bg-red-100 rounded-full flex items-center justify-center">
              <svg className="w-4 h-4 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.732 16.5c-.77.833.192 2.5 1.732 2.5z" />
              </svg>
            </div>
            <h3 className="text-sm font-semibold text-red-900">
              Supplier Escalation Suggested
            </h3>
          </div>
          
          <p className="text-sm text-red-800 mb-3">
            You may want to escalate <strong>{supplierMetrics.supplierName}</strong>. 
            {getPrimaryIssue(supplierMetrics)}.
          </p>
          
          <div className="space-y-2">
            <div className="flex items-center space-x-2">
              <span className="text-xs text-red-600 font-medium">Issues:</span>
              <span className="text-xs text-red-700">{getEscalationReason(supplierMetrics)}</span>
            </div>
            
            {supplierMetrics.recentIssues.length > 0 && (
              <div className="text-xs text-red-600">
                <span className="font-medium">Recent issues:</span>
                <ul className="mt-1 space-y-1">
                  {supplierMetrics.recentIssues.slice(0, 3).map((issue, index) => (
                    <li key={index} className="text-red-700">• {issue}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </div>
        
        <button
          onClick={handleDismiss}
          className="text-red-400 hover:text-red-600 transition-colors ml-2"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>
      
      <div className="flex space-x-2 mt-4">
        <button
          onClick={handleEscalate}
          className="px-3 py-2 bg-red-600 text-white text-xs font-medium rounded-md hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-offset-2 transition-colors"
        >
          Escalate Supplier
        </button>
        <button
          onClick={handleViewHistory}
          className="px-3 py-2 bg-white border border-red-300 text-red-700 text-xs font-medium rounded-md hover:bg-red-50 focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-offset-2 transition-colors"
        >
          View History
        </button>
        <button
          onClick={handleDismiss}
          className="px-3 py-2 bg-transparent text-red-600 text-xs font-medium hover:text-red-700 focus:outline-none transition-colors"
        >
          Not now
        </button>
      </div>
    </div>
  );
};

export default AgentEscalationBanner; 