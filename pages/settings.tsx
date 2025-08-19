import React from 'react';
import AppShell from '@/components/layout/AppShell';

const SettingsPage: React.FC = () => {
  return (
    <AppShell>
      <div className="py-8">
        <div className="max-w-4xl mx-auto">
          <h1 className="text-3xl font-semibold text-owlin-text mb-8">Settings</h1>
          
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
            {/* License Management */}
            <div className="bg-owlin-card rounded-owlin shadow-owlin p-6 border border-owlin-stroke">
              <h2 className="text-xl font-semibold text-owlin-text mb-4">License Management</h2>
              <div className="space-y-4">
                <div className="flex items-center justify-between p-4 bg-[color-mix(in_oklab,var(--owlin-sapphire)_10%,transparent)] rounded-owlin">
                  <div>
                    <p className="font-medium text-owlin-text">License Status</p>
                    <p className="text-sm text-owlin-muted">Active - Valid until Dec 31, 2024</p>
                  </div>
                  <div className="p-2 rounded-full bg-[color-mix(in_oklab,var(--owlin-sapphire)_12%,transparent)]">
                    <svg className="w-5 h-5 text-owlin-cerulean" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                  </div>
                </div>
                <button className="w-full bg-[var(--owlin-sapphire)] text-white py-2 px-4 rounded-owlin hover:brightness-110 transition-colors">
                  Renew License
                </button>
              </div>
            </div>

            {/* System Information */}
            <div className="bg-owlin-card rounded-owlin shadow-owlin p-6 border border-owlin-stroke">
              <h2 className="text-xl font-semibold text-owlin-text mb-4">System Information</h2>
              <div className="space-y-3">
                <div className="flex justify-between"><span className="text-owlin-muted">Version</span><span className="font-medium text-owlin-text">1.0.0</span></div>
                <div className="flex justify-between"><span className="text-owlin-muted">Build Date</span><span className="font-medium text-owlin-text">July 11, 2024</span></div>
                <div className="flex justify-between"><span className="text-owlin-muted">Database</span><span className="font-medium text-owlin-text">SQLite 3.x</span></div>
                <div className="flex justify-between"><span className="text-owlin-muted">OCR Engine</span><span className="font-medium text-owlin-text">Tesseract 5.x</span></div>
              </div>
            </div>

            {/* Backup & Restore */}
            <div className="bg-owlin-card rounded-owlin shadow-owlin p-6 border border-owlin-stroke">
              <h2 className="text-xl font-semibold text-owlin-text mb-4">Backup & Restore</h2>
              <div className="space-y-4">
                <div className="flex items-center justify-between p-4 bg-[color-mix(in_oklab,var(--owlin-sapphire)_10%,transparent)] rounded-owlin">
                  <div>
                    <p className="font-medium text-owlin-text">Last Backup</p>
                    <p className="text-sm text-owlin-muted">July 10, 2024 at 2:30 PM</p>
                  </div>
                  <svg className="w-5 h-5 text-owlin-cerulean" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7H5a2 2 0 00-2 2v9a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-3m-1 4l-3 3m0 0l-3-3m3 3V4" />
                  </svg>
                </div>
                <div className="flex space-x-3">
                  <button className="flex-1 bg-[var(--owlin-sapphire)] text-white py-2 px-4 rounded-owlin hover:brightness-110 transition-colors">Create Backup</button>
                  <button className="flex-1 border border-owlin-stroke text-owlin-text py-2 px-4 rounded-owlin hover:bg-[color-mix(in_oklab,var(--owlin-card)_92%,transparent)] transition-colors">Restore</button>
                </div>
              </div>
            </div>

            {/* User Preferences */}
            <div className="bg-owlin-card rounded-owlin shadow-owlin p-6 border border-owlin-stroke">
              <h2 className="text-xl font-semibold text-owlin-text mb-4">User Preferences</h2>
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <span className="text-owlin-text">Dark Mode</span>
                  <button className="relative inline-flex h-6 w-11 items-center rounded-full bg-owlin-bg">
                    <span className="inline-block h-4 w-4 transform rounded-full bg-white transition"></span>
                  </button>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-owlin-text">Email Notifications</span>
                  <button className="relative inline-flex h-6 w-11 items-center rounded-full bg-[var(--owlin-sapphire)]">
                    <span className="inline-block h-4 w-4 transform rounded-full bg-white transition translate-x-5"></span>
                  </button>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-owlin-text">Auto-save</span>
                  <button className="relative inline-flex h-6 w-11 items-center rounded-full bg-[var(--owlin-sapphire)]">
                    <span className="inline-block h-4 w-4 transform rounded-full bg-white transition translate-x-5"></span>
                  </button>
                </div>
              </div>
            </div>
          </div>

          {/* Advanced Settings */}
          <div className="mt-8 bg-owlin-card rounded-owlin shadow-owlin p-6 border border-owlin-stroke">
            <h2 className="text-xl font-semibold text-owlin-text mb-4">Advanced Settings</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <label className="block text-sm font-medium text-owlin-text mb-2">OCR Confidence Threshold</label>
                <input type="range" min="0" max="100" defaultValue="80" className="w-full h-2 bg-owlin-bg rounded-owlin appearance-none cursor-pointer" />
                <div className="flex justify-between text-xs text-owlin-muted mt-1"><span>0%</span><span>80%</span><span>100%</span></div>
              </div>
              <div>
                <label className="block text-sm font-medium text-owlin-text mb-2">Max File Size (MB)</label>
                <input type="number" defaultValue="10" className="w-full px-3 py-2 border border-owlin-stroke rounded-owlin bg-owlin-card focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-owlin-sapphire" />
              </div>
            </div>
          </div>
        </div>
      </div>
    </AppShell>
  );
};

export default SettingsPage; 