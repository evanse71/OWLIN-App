import React from 'react';
import { LicenseStatus } from '../../lib/licenseClient';

interface LimitedModeBannerProps {
  state: LicenseStatus['state'];
  graceUntil?: string;
}

export default function LimitedModeBanner({ state, graceUntil }: LimitedModeBannerProps) {
  const getBannerText = () => {
    switch (state) {
      case 'not_found':
      case 'invalid':
        return 'Limited Mode — editing is locked: invalid license.';
      case 'expired':
        return 'Limited Mode — license expired.';
      case 'grace':
        return `Limited Mode — license expired; grace until ${graceUntil}.`;
      case 'mismatch':
        return 'Limited Mode — license bound to a different device.';
      default:
        return 'Limited Mode — editing is locked.';
    }
  };

  if (state === 'valid') {
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
          stroke="#6B7280" 
          strokeWidth="2" 
          strokeLinecap="round" 
          strokeLinejoin="round" 
          aria-label="Limited mode"
        >
          <rect x="3" y="8" width="12" height="8" rx="2" ry="2"/>
          <path d="M6 8V6a3 3 0 0 1 6 0v2"/>
        </svg>
        <span className="text-[#4B5563] text-[14px] font-medium">
          {getBannerText()}
        </span>
      </div>
    </div>
  );
} 