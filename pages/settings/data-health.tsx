import React, { useState } from 'react';
import BackupList from '@/components/data/BackupList';
import SupportPackPanel from '@/components/data/SupportPackPanel';

type TabType = 'backups' | 'support-packs';

export default function DataHealthPage() {
  const [activeTab, setActiveTab] = useState<TabType>('backups');
  const [banner, setBanner] = useState<{ type: 'success' | 'error'; message: string } | null>(null);

  const showBanner = (type: 'success' | 'error', message: string) => {
    setBanner({ type, message });
    if (type === 'success') {
      setTimeout(() => setBanner(null), 5000);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="mb-8">
          <h1 className="text-2xl font-semibold text-gray-900">Data Health</h1>
          <p className="mt-2 text-sm text-gray-600">
            Manage backups and generate support packs for system maintenance.
          </p>
        </div>

        {/* Banner */}
        {banner && (
          <div className={`mb-6 p-4 rounded-lg ${
            banner.type === 'success' 
              ? 'bg-green-50 border border-green-200 text-green-800' 
              : 'bg-red-50 border border-red-200 text-red-800'
          }`}>
            <div className="flex items-center justify-between">
              <span>{banner.message}</span>
              {banner.type === 'error' && (
                <button
                  onClick={() => setBanner(null)}
                  className="text-gray-400 hover:text-gray-600"
                >
                  ✕
                </button>
              )}
            </div>
          </div>
        )}

        {/* Tabs */}
        <div className="border-b border-gray-200 mb-6">
          <nav className="-mb-px flex space-x-8">
            <button
              onClick={() => setActiveTab('backups')}
              className={`py-2 px-1 border-b-2 font-medium text-sm ${
                activeTab === 'backups'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              Backups
            </button>
            <button
              onClick={() => setActiveTab('support-packs')}
              className={`py-2 px-1 border-b-2 font-medium text-sm ${
                activeTab === 'support-packs'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              Support Packs
            </button>
          </nav>
        </div>

        {/* Content */}
        <div className="space-y-6">
          {activeTab === 'backups' && (
            <BackupList onBanner={showBanner} />
          )}
          {activeTab === 'support-packs' && (
            <SupportPackPanel onBanner={showBanner} />
          )}
        </div>
      </div>
    </div>
  );
}
