import React, { useEffect, useState } from 'react';
import UpdateList from '@/components/updates/UpdateList';
import Changelog from '@/components/updates/Changelog';
import RollbackPanel from '@/components/updates/RollbackPanel';
import UpdateDetailsPanel from '@/components/updates/UpdateDetailsPanel';
import UpdateProgressModal from '@/components/updates/UpdateProgressModal';
import RollbackConfirmDialog from '@/components/updates/RollbackConfirmDialog';

interface UpdateBundle {
  id: string;
  filename: string;
  version: string;
  build: string;
  created_at: string;
  description?: string;
  verified: 'pending' | 'ok' | 'failed';
  reason?: string;
}

interface Banner {
  type: 'success' | 'error';
  message: string;
}

export default function UpdatesPage() {
  const [selectedBundle, setSelectedBundle] = useState<UpdateBundle | null>(null);
  const [showProgress, setShowProgress] = useState(false);
  const [jobId, setJobId] = useState<string | null>(null);
  const [progressKind, setProgressKind] = useState<'apply' | 'rollback'>('apply');
  const [showRollbackConfirm, setShowRollbackConfirm] = useState(false);
  const [rollbackDate, setRollbackDate] = useState('');
  const [banner, setBanner] = useState<Banner | null>(null);

  const showBanner = (type: 'success' | 'error', message: string) => {
    setBanner({ type, message });
    setTimeout(() => setBanner(null), 5000);
  };

  const handleBundleSelect = (bundle: UpdateBundle) => {
    setSelectedBundle(bundle);
  };

  const handleApplyUpdate = async (bundleId: string) => {
    try {
      const response = await fetch(`/api/updates/apply/${bundleId}`, {
        method: 'POST',
      });
      
      if (response.ok) {
        const data = await response.json();
        setJobId(data.job_id);
        setProgressKind('apply');
        setShowProgress(true);
        setSelectedBundle(null); // Close details panel
      } else {
        const error = await response.json();
        showBanner('error', `Update failed: ${error.detail || 'Unknown error'}`);
      }
    } catch (error) {
      showBanner('error', 'Failed to apply update');
    }
  };

  const handleRollback = async (changelogId: string, backupDate: string) => {
    setRollbackDate(backupDate);
    setShowRollbackConfirm(true);
  };

  const confirmRollback = async () => {
    // This would be implemented to actually perform the rollback
    setShowRollbackConfirm(false);
    showBanner('success', 'Rollback completed successfully');
  };

  const handleProgressClose = () => {
    setShowProgress(false);
    setJobId(null);
    showBanner('success', 'Update completed successfully');
  };

  return (
    <div className="flex h-screen">
      <main className="flex-1 p-6 overflow-y-auto">
        <div className="max-w-4xl mx-auto">
          <h1 className="text-2xl font-semibold text-gray-900 mb-6">System Updates</h1>
          
          {/* Banner */}
          {banner && (
            <div className={`mb-4 p-4 rounded-lg ${
              banner.type === 'success' 
                ? 'bg-green-50 border border-green-200 text-green-800' 
                : 'bg-red-50 border border-red-200 text-red-800'
            }`}>
              {banner.message}
            </div>
          )}

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Left Column - Update List */}
            <div>
              <UpdateList onBundleSelect={handleBundleSelect} />
            </div>

            {/* Right Column - Changelog & Rollback */}
            <div className="space-y-6">
              <Changelog />
              <RollbackPanel onRollback={handleRollback} />
            </div>
          </div>
        </div>
      </main>

      {/* Details Panel */}
      {selectedBundle && (
        <UpdateDetailsPanel
          bundle={selectedBundle}
          onClose={() => setSelectedBundle(null)}
          onApply={handleApplyUpdate}
        />
      )}

      {/* Progress Modal */}
      {showProgress && jobId && (
        <UpdateProgressModal
          jobId={jobId}
          kind={progressKind}
          onClose={handleProgressClose}
        />
      )}

      {/* Rollback Confirm Dialog */}
      {showRollbackConfirm && (
        <RollbackConfirmDialog
          backupDate={rollbackDate}
          onConfirm={confirmRollback}
          onCancel={() => setShowRollbackConfirm(false)}
        />
      )}
    </div>
  );
}
