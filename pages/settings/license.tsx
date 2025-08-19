import React, { useState, useEffect } from 'react';
import { NextPage } from 'next';
import { licenseClient, LicenseStatus, LicenseUploadResponse } from '../../frontend/lib/licenseClient';
import LimitedModeBanner from '../../frontend/components/license/LimitedModeBanner';
import LicenseStatusCard from '../../frontend/components/license/LicenseStatusCard';
import LicenseUpload from '../../frontend/components/license/LicenseUpload';

const LicenseManagerPage: NextPage = () => {
  const [licenseStatus, setLicenseStatus] = useState<LicenseStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadLicenseStatus();
  }, []);

  const loadLicenseStatus = async () => {
    try {
      setLoading(true);
      setError(null);
      const status = await licenseClient.getStatus();
      setLicenseStatus(status);
    } catch (err) {
      setError('Failed to load license status');
      console.error('Error loading license status:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleUploadSuccess = (response: LicenseUploadResponse) => {
    setLicenseStatus(response.status);
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-[#F9FAFB] p-6">
        <div className="max-w-4xl mx-auto">
          <div className="animate-pulse">
            <div className="h-8 bg-gray-200 rounded w-1/4 mb-6"></div>
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <div className="h-64 bg-gray-200 rounded"></div>
              <div className="h-64 bg-gray-200 rounded"></div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#F9FAFB] p-6">
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <div className="mb-6">
          <h1 className="text-[24px] font-semibold text-[#1F2937] mb-2">License Manager</h1>
          <p className="text-[#6B7280] text-sm">
            Manage your OWLIN license and view system status
          </p>
        </div>

        {/* Limited Mode Banner */}
        {licenseStatus && (
          <LimitedModeBanner 
            state={licenseStatus.state} 
            graceUntil={licenseStatus.grace_until_utc}
          />
        )}

        {/* Error State */}
        {error && (
          <div className="mb-6 p-4 bg-[#FEE2E2] border border-[#FCA5A5] rounded-[12px]">
            <div className="flex items-center gap-2">
              <svg 
                className="w-5 h-5 text-[#DC2626]" 
                fill="none" 
                stroke="currentColor" 
                viewBox="0 0 24 24"
              >
                <path 
                  strokeLinecap="round" 
                  strokeLinejoin="round" 
                  strokeWidth={2} 
                  d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" 
                />
              </svg>
              <span className="text-[#DC2626] text-sm font-medium">{error}</span>
            </div>
          </div>
        )}

        {/* Main Content */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* License Status */}
          <div>
            <LicenseStatusCard status={licenseStatus || {
              valid: false,
              state: 'not_found',
              reason: 'LICENSE_NOT_FOUND'
            }} />
          </div>

          {/* License Upload */}
          <div>
            <LicenseUpload onUploadSuccess={handleUploadSuccess} />
          </div>
        </div>

        {/* Additional Information */}
        <div className="mt-8 bg-white border border-[#E5E7EB] rounded-[12px] p-4">
          <h3 className="text-[16px] font-semibold text-[#1F2937] mb-3">About License Management</h3>
          <div className="text-sm text-[#6B7280] space-y-2">
            <p>
              Your OWLIN license is bound to this device and controls access to features like OCR processing, 
              forecasting, and system updates.
            </p>
            <p>
              In Limited Mode, you can view all data but editing, uploading, and exporting are disabled. 
              Contact support to renew or transfer your license.
            </p>
            <p>
              License files are stored locally and never transmitted to external servers.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default LicenseManagerPage; 