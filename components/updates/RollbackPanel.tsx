import React, { useState, useEffect } from 'react';

interface ChangelogEntry {
  id: string;
  version: string;
  build: string;
  applied_at: string;
  status: 'success' | 'rollback' | 'failed';
  notes?: string;
}

interface RollbackPanelProps {
  onRollback: (changelogId: string, backupDate: string) => void;
}

export default function RollbackPanel({ onRollback }: RollbackPanelProps) {
  const [entries, setEntries] = useState<ChangelogEntry[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchChangelog();
  }, []);

  const fetchChangelog = async () => {
    try {
      const response = await fetch('/api/api/updates/changelog');
      if (response.ok) {
        const data = await response.json();
        // Only show successful updates that can be rolled back
        setEntries(data.filter((entry: ChangelogEntry) => entry.status === 'success'));
      }
    } catch (error) {
      console.error('Failed to fetch changelog:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="bg-white rounded-lg p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Rollback Options</h2>
        <div className="text-gray-500">Loading rollback options...</div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg p-6">
      <h2 className="text-lg font-semibold text-gray-900 mb-4">Rollback Options</h2>
      
      {entries.length === 0 ? (
        <div className="text-gray-500">No rollback points available</div>
      ) : (
        <div className="space-y-3">
          {entries.map((entry) => (
            <div key={entry.id} className="border border-gray-200 rounded-lg p-3">
              <div className="flex items-center justify-between mb-2">
                <h3 className="font-medium text-gray-900">
                  Version {entry.version}
                </h3>
                <button
                  onClick={() => onRollback(entry.id, entry.applied_at)}
                  className="px-3 py-1 text-sm text-red-600 border border-red-300 rounded hover:bg-red-50 transition-colors"
                >
                  Rollback
                </button>
              </div>
              
              <div className="text-sm text-gray-600 space-y-1">
                <div>Build: {entry.build}</div>
                <div>Applied: {new Date(entry.applied_at).toLocaleDateString()}</div>
                {entry.notes && (
                  <div className="mt-2 text-gray-700">{entry.notes}</div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
