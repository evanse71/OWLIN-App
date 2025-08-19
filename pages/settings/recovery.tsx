import React, { useState, useEffect } from 'react';
import { NextPage } from 'next';
import { recoveryClient, RecoveryStatus } from '../../frontend/lib/recoveryClient';
import RecoveryBanner from '../../frontend/components/recovery/RecoveryBanner';
import RestoreWizard from '../../frontend/components/recovery/RestoreWizard';

const RecoveryPage: NextPage = () => {
  const [status, setStatus] = useState<RecoveryStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showWizard, setShowWizard] = useState(false);

  useEffect(() => {
    loadStatus();
  }, []);

  const loadStatus = async () => {
    try {
      setLoading(true);
      setError(null);
      const recoveryStatus = await recoveryClient.getStatus();
      setStatus(recoveryStatus);
    } catch (err) {
      setError('Failed to load recovery status');
      console.error('Error loading recovery status:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleScan = async () => {
    try {
      setLoading(true);
      setError(null);
      const recoveryStatus = await recoveryClient.scanSystem();
      setStatus(recoveryStatus);
    } catch (err) {
      setError('Failed to scan system');
      console.error('Error scanning system:', err);
    } finally {
      setLoading(false);
    }
  };

  const getStatusColor = (state: RecoveryStatus['state']) => {
    switch (state) {
      case 'normal':
        return 'bg-green-100 text-green-800';
      case 'degraded':
        return 'bg-yellow-100 text-yellow-800';
      case 'recovery':
        return 'bg-red-100 text-red-800';
      case 'restore_pending':
        return 'bg-blue-100 text-blue-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const getStatusText = (state: RecoveryStatus['state']) => {
    switch (state) {
      case 'normal':
        return 'Normal';
      case 'degraded':
        return 'Degraded';
      case 'recovery':
        return 'Recovery Mode';
      case 'restore_pending':
        return 'Restore Pending';
      default:
        return 'Unknown';
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-[#F9FAFB] p-6">
        <div className="max-w-4xl mx-auto">
          <div className="animate-pulse">
            <div className="h-8 bg-gray-200 rounded w-1/4 mb-6"></div>
            <div className="space-y-4">
              <div className="h-32 bg-gray-200 rounded"></div>
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
          <h1 className="text-[24px] font-semibold text-[#1F2937] mb-2">Recovery Mode</h1>
          <p className="text-[#6B7280] text-sm">
            Monitor system health and restore from snapshots when needed
          </p>
        </div>

        {/* Recovery Banner */}
        {status && <RecoveryBanner status={status} />}

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

        {/* Status Card */}
        {status && (
          <div className="bg-white border border-[#E5E7EB] rounded-[12px] p-6 mb-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-[18px] font-semibold text-[#1F2937]">System Status</h2>
              <div className="flex items-center gap-3">
                <span className={`px-3 py-1 rounded-[6px] text-sm font-medium ${getStatusColor(status.state)}`}>
                  {getStatusText(status.state)}
                </span>
                <button
                  onClick={handleScan}
                  className="px-4 py-2 bg-[#3B82F6] text-white rounded-[6px] font-medium text-sm hover:bg-[#2563EB] transition-colors"
                >
                  Scan System
                </button>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* System Info */}
              <div>
                <h3 className="text-[14px] font-medium text-[#374151] mb-3">System Information</h3>
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-[#6B7280]">App Version:</span>
                    <span className="font-mono">{status.app_version}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-[#6B7280]">Schema Version:</span>
                    <span className="font-mono">{status.schema_version}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-[#6B7280]">Database Hash:</span>
                    <span className="font-mono text-xs">{status.live_db_hash.substring(0, 16)}...</span>
                  </div>
                </div>
              </div>

              {/* Snapshots */}
              <div>
                <h3 className="text-[14px] font-medium text-[#374151] mb-3">Available Snapshots</h3>
                <div className="space-y-2">
                  {status.snapshots.length > 0 ? (
                    status.snapshots.slice(0, 3).map((snapshot) => (
                      <div key={snapshot.id} className="flex items-center justify-between p-2 bg-[#F9FAFB] rounded-[6px]">
                        <div>
                          <div className="text-sm font-medium text-[#1F2937]">{snapshot.id}</div>
                          <div className="text-xs text-[#6B7280]">
                            {new Date(snapshot.created_at).toLocaleDateString()}
                          </div>
                        </div>
                        <div className="flex items-center gap-2">
                          <span className="text-xs text-[#6B7280]">
                            {(snapshot.size_bytes / 1024 / 1024).toFixed(1)} MB
                          </span>
                          {snapshot.manifest_ok ? (
                            <span className="w-2 h-2 bg-green-500 rounded-full"></span>
                          ) : (
                            <span className="w-2 h-2 bg-red-500 rounded-full"></span>
                          )}
                        </div>
                      </div>
                    ))
                  ) : (
                    <div className="text-sm text-[#6B7280]">No snapshots available</div>
                  )}
                </div>
              </div>
            </div>

            {/* Issues */}
            {status.details.length > 0 && (
              <div className="mt-6">
                <h3 className="text-[14px] font-medium text-[#374151] mb-3">Issues Detected</h3>
                <div className="space-y-2">
                  {status.details.map((detail, index) => (
                    <div key={index} className="flex items-start gap-2 p-3 bg-[#FEF3C7] border border-[#FDE68A] rounded-[6px]">
                      <svg 
                        className="w-4 h-4 text-[#D97706] mt-0.5 flex-shrink-0" 
                        fill="none" 
                        stroke="currentColor" 
                        viewBox="0 0 24 24"
                      >
                        <path 
                          strokeLinecap="round" 
                          strokeLinejoin="round" 
                          strokeWidth={2} 
                          d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.732 16.5c-.77.833.192 2.5 1.732 2.5z" 
                        />
                      </svg>
                      <span className="text-sm text-[#92400E]">{detail}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Actions */}
        <div className="bg-white border border-[#E5E7EB] rounded-[12px] p-6">
          <h2 className="text-[18px] font-semibold text-[#1F2937] mb-4">Recovery Actions</h2>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <button
              onClick={() => setShowWizard(true)}
              disabled={!status || status.snapshots.length === 0}
              className="p-4 border border-[#E5E7EB] rounded-[12px] text-left hover:border-[#3B82F6] hover:bg-[#F0F9FF] transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <div className="flex items-center gap-3">
                <svg 
                  xmlns="http://www.w3.org/2000/svg" 
                  width="24" 
                  height="24" 
                  fill="none" 
                  stroke="#3B82F6" 
                  strokeWidth="2" 
                  strokeLinecap="round" 
                  strokeLinejoin="round"
                >
                  <path d="M4 5h10M4 9h10M4 13h10"/>
                </svg>
                <div>
                  <div className="font-medium text-[#1F2937]">Restore from Snapshot</div>
                  <div className="text-sm text-[#6B7280]">
                    Preview and restore data from a backup snapshot
                  </div>
                </div>
              </div>
            </button>

            <button
              onClick={handleScan}
              className="p-4 border border-[#E5E7EB] rounded-[12px] text-left hover:border-[#3B82F6] hover:bg-[#F0F9FF] transition-colors"
            >
              <div className="flex items-center gap-3">
                <svg 
                  xmlns="http://www.w3.org/2000/svg" 
                  width="24" 
                  height="24" 
                  fill="none" 
                  stroke="#3B82F6" 
                  strokeWidth="2" 
                  strokeLinecap="round" 
                  strokeLinejoin="round"
                >
                  <path d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/>
                </svg>
                <div>
                  <div className="font-medium text-[#1F2937]">Scan System</div>
                  <div className="text-sm text-[#6B7280]">
                    Run integrity checks and update status
                  </div>
                </div>
              </div>
            </button>
          </div>
        </div>

        {/* Restore Wizard */}
        {showWizard && (
          <RestoreWizard onClose={() => setShowWizard(false)} />
        )}
      </div>
    </div>
  );
};

export default RecoveryPage; 