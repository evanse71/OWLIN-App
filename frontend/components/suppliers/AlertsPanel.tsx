import React from 'react';
import { useAlerts, SupplierAlert } from '../../hooks/useSupplierBehaviour';

interface AlertsPanelProps {
  onSupplierClick?: (supplierId: string) => void;
}

const getSeverityIcon = (severity: string) => {
  switch (severity) {
    case 'high':
      return (
        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="none" stroke="#DC2626" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-label="High severity">
          <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/>
          <line x1="12" y1="9" x2="12" y2="13"/>
          <line x1="12" y1="17" x2="12.01" y2="17"/>
        </svg>
      );
    case 'medium':
      return (
        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="none" stroke="#D97706" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-label="Medium severity">
          <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/>
          <line x1="12" y1="9" x2="12" y2="13"/>
          <line x1="12" y1="17" x2="12.01" y2="17"/>
        </svg>
      );
    case 'low':
      return (
        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="none" stroke="#6B7280" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-label="Low severity">
          <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/>
          <line x1="12" y1="9" x2="12" y2="13"/>
          <line x1="12" y1="17" x2="12.01" y2="17"/>
        </svg>
      );
    default:
      return null;
  }
};

const getSeverityColor = (severity: string) => {
  switch (severity) {
    case 'high':
      return 'bg-[#F87171] text-[#7F1D1D]';
    case 'medium':
      return 'bg-[#FCD34D] text-[#92400E]';
    case 'low':
      return 'bg-[#E5E7EB] text-[#374151]';
    default:
      return 'bg-[#E5E7EB] text-[#374151]';
  }
};

const AlertRow: React.FC<{ alert: SupplierAlert; onSupplierClick?: (supplierId: string) => void }> = ({ alert, onSupplierClick }) => {
  const handleSupplierClick = () => {
    if (onSupplierClick) {
      onSupplierClick(alert.supplier_id);
    }
  };

  return (
    <div className="flex items-center justify-between p-3 hover:bg-[#F8F9FB] transition-colors">
      <div className="flex items-center gap-3 flex-1 min-w-0">
        <div className="flex-shrink-0">
          {getSeverityIcon(alert.severity)}
        </div>
        <div className="flex-1 min-w-0">
          <button
            onClick={handleSupplierClick}
            className="text-[14px] font-medium text-[#1F2937] hover:text-[#3B82F6] transition-colors text-left truncate"
          >
            {alert.supplier_name}
          </button>
          <p className="text-[12px] text-[#6B7280] truncate">{alert.summary}</p>
        </div>
      </div>
      <span className={`px-2 py-1 rounded-[6px] text-xs font-medium ${getSeverityColor(alert.severity)}`}>
        {alert.severity}
      </span>
    </div>
  );
};

const LoadingSkeleton: React.FC = () => (
  <div className="space-y-2">
    {[1, 2, 3].map((i) => (
      <div key={i} className="flex items-center gap-3 p-3 animate-pulse">
        <div className="w-4 h-4 bg-gray-200 rounded"></div>
        <div className="flex-1">
          <div className="h-4 bg-gray-200 rounded mb-1"></div>
          <div className="h-3 bg-gray-200 rounded w-2/3"></div>
        </div>
        <div className="w-12 h-6 bg-gray-200 rounded"></div>
      </div>
    ))}
  </div>
);

const EmptyState: React.FC = () => (
  <div className="text-center py-8">
    <div className="w-12 h-12 bg-gray-200 rounded-full flex items-center justify-center mx-auto mb-3">
      <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" fill="none" stroke="#9CA3AF" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/>
        <line x1="12" y1="9" x2="12" y2="13"/>
        <line x1="12" y1="17" x2="12.01" y2="17"/>
      </svg>
    </div>
    <p className="text-[14px] text-[#6B7280]">No active supplier alerts</p>
  </div>
);

const ErrorState: React.FC<{ error: string; onRetry: () => void }> = ({ error, onRetry }) => (
  <div className="bg-[#FFEBEE] border border-[#E57373] rounded-[12px] p-4">
    <div className="flex items-center justify-between">
      <p className="text-[14px] text-[#C62828]">{error}</p>
      <button 
        onClick={onRetry}
        className="px-3 py-1 bg-[#C62828] text-white rounded-[8px] text-xs font-medium hover:bg-[#B71C1C] transition-colors"
      >
        Retry
      </button>
    </div>
  </div>
);

export default function AlertsPanel({ onSupplierClick }: AlertsPanelProps) {
  const { alerts, loading, error, isCachedData } = useAlerts();

  const handleRetry = () => {
    window.location.reload();
  };

  const handleSupplierClick = (supplierId: string) => {
    if (onSupplierClick) {
      onSupplierClick(supplierId);
    } else {
      // Default navigation to supplier profile
      window.location.href = `/suppliers/${supplierId}`;
    }
  };

  return (
    <div className="bg-white rounded-[12px] border border-[#E5E7EB] overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-[#E5E7EB]">
        <h3 className="text-[16px] font-semibold text-[#1F2937]">Supplier Alerts</h3>
        {isCachedData && (
          <span className="px-2 py-1 bg-[#E5E7EB] text-[#374151] rounded-[6px] text-xs font-medium">
            Cached
          </span>
        )}
      </div>

      {/* Content */}
      <div className="max-h-[300px] overflow-y-auto">
        {loading && <LoadingSkeleton />}
        
        {error && (
          <ErrorState error={error} onRetry={handleRetry} />
        )}
        
        {!loading && !error && alerts.length === 0 && (
          <EmptyState />
        )}
        
        {!loading && !error && alerts.length > 0 && (
          <div className="divide-y divide-[#E5E7EB]">
            {alerts.map((alert) => (
              <AlertRow 
                key={`${alert.supplier_id}-${alert.alert_type}`} 
                alert={alert} 
                onSupplierClick={handleSupplierClick}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
} 