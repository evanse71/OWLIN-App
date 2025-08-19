import React, { useState, useEffect } from 'react';
import RestoreDialog from './RestoreDialog';

interface BackupInfo {
  id: string;
  created_at: string;
  path: string;
  size_bytes: number;
  mode: 'manual' | 'scheduled';
  app_version: string;
  db_schema_version: number;
}

interface BackupListProps {
  onBanner: (type: 'success' | 'error', message: string) => void;
}

export default function BackupList({ onBanner }: BackupListProps) {
  const [backups, setBackups] = useState<BackupInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [showRestoreDialog, setShowRestoreDialog] = useState(false);
  const [selectedBackup, setSelectedBackup] = useState<BackupInfo | null>(null);

  useEffect(() => {
    fetchBackups();
  }, []);

  const fetchBackups = async () => {
    try {
      const response = await fetch('/api/backups');
      if (response.ok) {
        const data = await response.json();
        setBackups(data);
      } else {
        onBanner('error', 'Failed to fetch backups');
      }
    } catch (error) {
      onBanner('error', 'Failed to fetch backups');
    } finally {
      setLoading(false);
    }
  };

  const handleCreateBackup = async () => {
    try {
      const response = await fetch('/api/backups', {
        method: 'POST',
      });
      
      if (response.ok) {
        const result = await response.json();
        onBanner('success', `Backup created successfully (${(result.size_bytes / 1024 / 1024).toFixed(1)}MB)`);
        fetchBackups(); // Refresh list
      } else {
        const error = await response.json();
        onBanner('error', `Backup creation failed: ${error.detail || 'Unknown error'}`);
      }
    } catch (error) {
      onBanner('error', 'Failed to create backup');
    }
  };

  const handleRestore = (backup: BackupInfo) => {
    setSelectedBackup(backup);
    setShowRestoreDialog(true);
  };

  const handleRestoreComplete = () => {
    setShowRestoreDialog(false);
    setSelectedBackup(null);
    onBanner('success', 'Restore completed successfully');
  };

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString();
  };

  if (loading) {
    return (
      <div className="bg-white rounded-lg border border-gray-200 p-6">
        <div className="flex items-center justify-center">
          <div className="text-gray-500">Loading backups...</div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-white rounded-lg border border-gray-200 p-6">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-lg font-semibold text-gray-900">Backups</h2>
            <p className="text-sm text-gray-600 mt-1">
              Create and manage system backups for data protection.
            </p>
          </div>
          <button
            onClick={handleCreateBackup}
            className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition-colors"
          >
            Create Backup
          </button>
        </div>
      </div>

      {/* Backup List */}
      {backups.length === 0 ? (
        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <div className="text-center text-gray-500">
            <p>No backups yet. Create one to get started.</p>
          </div>
        </div>
      ) : (
        <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
          <div className="px-6 py-4 border-b border-gray-200">
            <h3 className="text-lg font-medium text-gray-900">Available Backups</h3>
          </div>
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Created
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Size
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Mode
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Version
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Schema
                  </th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {backups.map((backup) => (
                  <tr key={backup.id} className="hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {formatDate(backup.created_at)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {formatFileSize(backup.size_bytes)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${
                        backup.mode === 'manual' 
                          ? 'bg-blue-100 text-blue-800' 
                          : 'bg-green-100 text-green-800'
                      }`}>
                        {backup.mode}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {backup.app_version}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {backup.db_schema_version}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                      <button
                        onClick={() => handleRestore(backup)}
                        className="text-blue-600 hover:text-blue-900"
                      >
                        Restore...
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Restore Dialog */}
      {showRestoreDialog && selectedBackup && (
        <RestoreDialog
          backup={selectedBackup}
          onClose={() => setShowRestoreDialog(false)}
          onComplete={handleRestoreComplete}
        />
      )}
    </div>
  );
}
