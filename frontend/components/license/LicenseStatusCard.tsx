import React from 'react';
import { LicenseStatus, LicenseSummary } from '../../lib/licenseClient';
import dayjs from 'dayjs';

interface LicenseStatusCardProps {
  status: LicenseStatus;
}

export default function LicenseStatusCard({ status }: LicenseStatusCardProps) {
  const getStatusColor = (state: LicenseStatus['state']) => {
    switch (state) {
      case 'valid':
        return 'bg-[#A7C4A0] text-white';
      case 'grace':
        return 'bg-[#F5A623] text-white';
      case 'expired':
      case 'invalid':
      case 'mismatch':
      case 'not_found':
        return 'bg-[#E57373] text-white';
      default:
        return 'bg-gray-500 text-white';
    }
  };

  const getStatusText = (state: LicenseStatus['state']) => {
    switch (state) {
      case 'valid':
        return 'Valid';
      case 'grace':
        return 'Grace Period';
      case 'expired':
        return 'Expired';
      case 'invalid':
        return 'Invalid';
      case 'mismatch':
        return 'Device Mismatch';
      case 'not_found':
        return 'Not Found';
      default:
        return 'Unknown';
    }
  };

  const formatDate = (dateString: string) => {
    return dayjs(dateString).format('MMM D, YYYY');
  };

  const getRoleUsage = (role: string, limit: number) => {
    // Mock usage - in real implementation, get from database
    const usage = Math.floor(Math.random() * (limit + 2));
    const percentage = Math.min((usage / limit) * 100, 100);
    const isExceeded = usage > limit;
    
    return { usage, percentage, isExceeded };
  };

  if (!status.summary) {
    return (
      <div className="bg-white border border-[#E5E7EB] rounded-[12px] p-4">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-[16px] font-semibold text-[#1F2937]">License Status</h3>
          <span className={`px-2 py-1 rounded-[6px] text-xs font-medium ${getStatusColor(status.state)}`}>
            {getStatusText(status.state)}
          </span>
        </div>
        <p className="text-[#6B7280] text-sm">No license information available</p>
      </div>
    );
  }

  const summary = status.summary;

  return (
    <div className="bg-white border border-[#E5E7EB] rounded-[12px] p-4">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-[16px] font-semibold text-[#1F2937]">License Status</h3>
        <span className={`px-2 py-1 rounded-[6px] text-xs font-medium ${getStatusColor(status.state)}`}>
          {getStatusText(status.state)}
        </span>
      </div>

      <div className="space-y-4">
        {/* Customer and License ID */}
        <div>
          <div className="text-sm font-medium text-[#374151] mb-1">Customer</div>
          <div className="text-sm text-[#6B7280]">{summary.customer}</div>
        </div>

        <div>
          <div className="text-sm font-medium text-[#374151] mb-1">License ID</div>
          <div className="text-sm text-[#6B7280] font-mono">{summary.license_id}</div>
        </div>

        {/* Device ID */}
        <div>
          <div className="text-sm font-medium text-[#374151] mb-1">Device ID</div>
          <div className="text-sm text-[#6B7280] font-mono">{summary.device_id}</div>
        </div>

        {/* Venues */}
        <div>
          <div className="text-sm font-medium text-[#374151] mb-2">Venues</div>
          <div className="flex flex-wrap gap-2">
            {summary.venues.map((venue) => (
              <span 
                key={venue} 
                className="px-2 py-1 bg-[#F3F4F6] text-[#374151] rounded-[6px] text-xs"
              >
                {venue}
              </span>
            ))}
          </div>
        </div>

        {/* Expiry */}
        <div>
          <div className="text-sm font-medium text-[#374151] mb-1">Expires</div>
          <div className="text-sm text-[#6B7280]">{formatDate(summary.expires_utc)}</div>
        </div>

        {/* Role Limits */}
        <div>
          <div className="text-sm font-medium text-[#374151] mb-2">Role Limits</div>
          <div className="space-y-2">
            {Object.entries(summary.roles).map(([role, limit]) => {
              const { usage, percentage, isExceeded } = getRoleUsage(role, limit);
              
              return (
                <div key={role} className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="text-sm text-[#6B7280] capitalize">{role}</span>
                    {isExceeded && (
                      <div className="w-2 h-2 bg-red-500 rounded-full" title="ROLE_LIMIT_EXCEEDED" />
                    )}
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="w-16 bg-[#F3F4F6] rounded-full h-2">
                      <div 
                        className={`h-2 rounded-full ${isExceeded ? 'bg-red-500' : 'bg-[#10B981]'}`}
                        style={{ width: `${percentage}%` }}
                      />
                    </div>
                    <span className="text-xs text-[#6B7280]">
                      {usage}/{limit}
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Features */}
        <div>
          <div className="text-sm font-medium text-[#374151] mb-2">Features</div>
          <div className="flex flex-wrap gap-2">
            {Object.entries(summary.features).map(([feature, enabled]) => (
              <span 
                key={feature} 
                className={`px-2 py-1 rounded-[6px] text-xs ${
                  enabled 
                    ? 'bg-[#D1FAE5] text-[#065F46]' 
                    : 'bg-[#FEE2E2] text-[#991B1B]'
                }`}
              >
                {feature} {enabled ? '✓' : '✗'}
              </span>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
} 