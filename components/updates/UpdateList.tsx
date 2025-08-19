import React, { useState, useEffect } from 'react';
import UpdateBadge from './UpdateBadge';

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

interface UpdateListProps {
  onBundleSelect: (bundle: UpdateBundle) => void;
}

export default function UpdateList({ onBundleSelect }: UpdateListProps) {
  const [updates, setUpdates] = useState<UpdateBundle[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchUpdates();
  }, []);

  const fetchUpdates = async () => {
    try {
      const response = await fetch('/api/api/updates/available');
      if (response.ok) {
        const data = await response.json();
        setUpdates(data);
      }
    } catch (error) {
      console.error('Failed to fetch updates:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="bg-white rounded-lg p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Available Updates</h2>
        <div className="text-gray-500">Loading updates...</div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg p-6">
      <h2 className="text-lg font-semibold text-gray-900 mb-4">Available Updates</h2>
      
      {updates.length === 0 ? (
        <div className="text-gray-500">No updates available</div>
      ) : (
        <div className="space-y-3">
          {updates.map((update) => (
            <div
              key={update.id}
              className="border border-gray-200 rounded-lg p-4 hover:bg-gray-50 cursor-pointer transition-colors"
              onClick={() => onBundleSelect(update)}
            >
              <div className="flex items-center justify-between mb-2">
                <h3 className="font-medium text-gray-900">
                  Version {update.version}
                </h3>
                <UpdateBadge
                  type="validation"
                  status={update.verified === 'ok' ? 'ok' : update.verified === 'failed' ? 'error' : 'warn'}
                  text={update.verified === 'ok' ? 'Verified' : update.verified === 'failed' ? 'Failed' : 'Pending'}
                />
              </div>
              
              <div className="text-sm text-gray-600 space-y-1">
                <div>Build: {update.build}</div>
                <div>Created: {new Date(update.created_at).toLocaleDateString()}</div>
                {update.description && (
                  <div>{update.description}</div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
