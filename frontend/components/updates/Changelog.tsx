import React, { useState, useEffect } from 'react';

interface ChangelogEntry {
  id: string;
  version: string;
  build: string;
  applied_at: string;
  status: 'success' | 'rollback' | 'failed';
  notes?: string;
}

export default function Changelog() {
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
        setEntries(data);
      }
    } catch (error) {
      console.error('Failed to fetch changelog:', error);
    } finally {
      setLoading(false);
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'success':
        return 'text-green-600 bg-green-100';
      case 'rollback':
        return 'text-yellow-600 bg-yellow-100';
      case 'failed':
        return 'text-red-600 bg-red-100';
      default:
        return 'text-gray-600 bg-gray-100';
    }
  };

  if (loading) {
    return (
      <div className="bg-white rounded-lg p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Changelog</h2>
        <div className="text-gray-500">Loading changelog...</div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg p-6">
      <h2 className="text-lg font-semibold text-gray-900 mb-4">Changelog</h2>
      
      {entries.length === 0 ? (
        <div className="text-gray-500">No changelog entries</div>
      ) : (
        <div className="space-y-3">
          {entries.map((entry) => (
            <div key={entry.id} className="border border-gray-200 rounded-lg p-3">
              <div className="flex items-center justify-between mb-2">
                <h3 className="font-medium text-gray-900">
                  Version {entry.version}
                </h3>
                <span className={`px-2 py-1 rounded-full text-xs font-medium ${getStatusColor(entry.status)}`}>
                  {entry.status}
                </span>
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
