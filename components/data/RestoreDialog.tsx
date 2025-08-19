import React, { useState } from 'react';

interface BackupInfo {
  id: string;
  created_at: string;
  path: string;
  size_bytes: number;
  mode: 'manual' | 'scheduled';
  app_version: string;
  db_schema_version: number;
}

interface RestorePreviewChange {
  table: string;
  adds: number;
  updates: number;
  deletes: number;
}

interface RestoreDialogProps {
  backup: BackupInfo;
  onClose: () => void;
  onComplete: () => void;
}

export default function RestoreDialog({ backup, onClose, onComplete }: RestoreDialogProps) {
  const [preview, setPreview] = useState<RestorePreviewChange[]>([]);
  const [loading, setLoading] = useState(true);
  const [previewError, setPreviewError] = useState<string | null>(null);
  const [confirmText, setConfirmText] = useState('');
  const [restoring, setRestoring] = useState(false);

  React.useEffect(() => {
    loadPreview();
  }, [backup.id]);

  const loadPreview = async () => {
    try {
      setLoading(true);
      const response = await fetch(`/api/backups/restore?backup_id=${backup.id}&dry_run=true`);
      
      if (response.ok) {
        const data = await response.json();
        if (data.ok) {
          setPreview(data.changes || []);
        } else {
          setPreviewError(data.reason || 'Preview failed');
        }
      } else {
        setPreviewError('Failed to load preview');
      }
    } catch (error) {
      setPreviewError('Failed to load preview');
    } finally {
      setLoading(false);
    }
  };

  const handleRestore = async () => {
    if (confirmText !== 'RESTORE') {
      return;
    }

    try {
      setRestoring(true);
      const response = await fetch(`/api/backups/restore?backup_id=${backup.id}&dry_run=false`, {
        method: 'POST',
      });
      
      if (response.ok) {
        const result = await response.json();
        if (result.ok) {
          onComplete();
        } else {
          setPreviewError(result.reason || 'Restore failed');
        }
      } else {
        const error = await response.json();
        setPreviewError(error.detail || 'Restore failed');
      }
    } catch (error) {
      setPreviewError('Restore failed');
    } finally {
      setRestoring(false);
    }
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString();
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg p-6 w-full max-w-2xl mx-4 max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-gray-900">Restore Backup</h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600"
          >
            ✕
          </button>
        </div>

        <div className="space-y-4">
          {/* Backup Info */}
          <div className="bg-gray-50 rounded-lg p-4">
            <h3 className="font-medium text-gray-900 mb-2">Backup Details</h3>
            <div className="text-sm text-gray-600 space-y-1">
              <div>Created: {formatDate(backup.created_at)}</div>
              <div>Mode: {backup.mode}</div>
              <div>App Version: {backup.app_version}</div>
              <div>DB Schema: {backup.db_schema_version}</div>
            </div>
          </div>

          {/* Preview */}
          <div>
            <h3 className="font-medium text-gray-900 mb-2">Restore Preview</h3>
            
            {loading && (
              <div className="text-gray-500">Loading preview...</div>
            )}
            
            {previewError && (
              <div className="bg-red-50 border border-red-200 rounded-lg p-3">
                <div className="text-sm text-red-800">
                  <strong>Error:</strong> {previewError}
                </div>
              </div>
            )}
            
            {!loading && !previewError && (
              <div className="bg-gray-50 rounded-lg p-4">
                {preview.length === 0 ? (
                  <div className="text-gray-600">No changes detected</div>
                ) : (
                  <div className="space-y-2">
                    {preview.map((change, index) => (
                      <div key={index} className="flex justify-between text-sm">
                        <span className="font-medium">{change.table}</span>
                        <div className="space-x-4">
                          {change.adds > 0 && (
                            <span className="text-green-600">+{change.adds}</span>
                          )}
                          {change.updates > 0 && (
                            <span className="text-yellow-600">~{change.updates}</span>
                          )}
                          {change.deletes > 0 && (
                            <span className="text-red-600">-{change.deletes}</span>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Warning */}
          <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
            <div className="text-sm text-yellow-800">
              <strong>Warning:</strong> This action will replace the current database with the backup. 
              This cannot be undone. A pre-restore backup will be created automatically.
            </div>
          </div>

          {/* Confirmation */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Type &apos;RESTORE&apos; to confirm:
            </label>
            <input
              type="text"
              value={confirmText}
              onChange={(e) => setConfirmText(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              placeholder="RESTORE"
            />
          </div>

          {/* Actions */}
          <div className="flex gap-3 pt-4">
            <button
              onClick={onClose}
              className="flex-1 px-4 py-2 text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200 transition-colors"
            >
              Cancel
            </button>
            <button
              onClick={handleRestore}
              disabled={confirmText !== 'RESTORE' || restoring || !!previewError}
              className="flex-1 px-4 py-2 text-white bg-red-600 rounded-lg hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {restoring ? 'Restoring...' : 'Confirm Restore'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
