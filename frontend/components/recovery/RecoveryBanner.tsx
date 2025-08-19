import React from 'react';
import { RecoveryStatus } from '../../lib/recoveryClient';

interface RecoveryBannerProps {
  status: RecoveryStatus;
}

export default function RecoveryBanner({ status }: RecoveryBannerProps) {
  const getBannerText = () => {
    switch (status.reason) {
      case 'INTEGRITY_FAILED':
        return 'Database integrity issues detected. Recovery mode is active.';
      case 'SCHEMA_MISMATCH':
        return 'Schema version mismatch detected. Recovery mode is active.';
      case 'UPDATE_INCOMPLETE':
        return 'Incomplete update detected. Recovery mode is active.';
      default:
        return 'System issues detected. Recovery mode is active.';
    }
  };

  if (status.state === 'normal') {
    return null;
  }

  return (
    <div className="bg-[#FFF7ED] border border-[#FDE68A] px-4 py-3 rounded-[12px] mb-6">
      <div className="flex items-center gap-3">
        <svg 
          xmlns="http://www.w3.org/2000/svg" 
          width="18" 
          height="18" 
          fill="none" 
          stroke="#D97706" 
          strokeWidth="2" 
          strokeLinecap="round" 
          strokeLinejoin="round" 
          aria-label="Recovery mode"
        >
          <circle cx="9" cy="9" r="7"/>
          <path d="M9 2v4M9 12v4M2 9h4M12 9h4"/>
        </svg>
        <span className="text-[#4B5563] text-[14px] font-medium">
          {getBannerText()}
        </span>
      </div>
    </div>
  );
} 