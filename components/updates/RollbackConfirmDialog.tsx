import React, { useState } from 'react';

interface RollbackConfirmDialogProps {
  backupDate: string;
  onConfirm: () => void;
  onCancel: () => void;
}

export default function RollbackConfirmDialog({ backupDate, onConfirm, onCancel }: RollbackConfirmDialogProps) {
  const [confirmText, setConfirmText] = useState('');

  const handleConfirm = () => {
    if (confirmText === 'ROLLBACK') {
      onConfirm();
    }
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg p-6 w-96 max-w-full mx-4">
        <div className="mb-4">
          <h2 className="text-lg font-semibold text-gray-900 mb-2">Confirm Rollback</h2>
          <p className="text-sm text-gray-600">
            This will revert to the backup from <strong>{backupDate}</strong>. 
            This action cannot be undone.
          </p>
        </div>

        <div className="mb-4">
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Type &apos;ROLLBACK&apos; to confirm:
          </label>
          <input
            type="text"
            value={confirmText}
            onChange={(e) => setConfirmText(e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            placeholder="ROLLBACK"
          />
        </div>

        <div className="flex gap-3">
          <button
            onClick={onCancel}
            className="flex-1 px-4 py-2 text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200 transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handleConfirm}
            disabled={confirmText !== 'ROLLBACK'}
            className="flex-1 px-4 py-2 text-white bg-red-600 rounded-lg hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            Confirm Rollback
          </button>
        </div>
      </div>
    </div>
  );
}
