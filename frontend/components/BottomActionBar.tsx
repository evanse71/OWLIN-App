import React, { useState } from 'react';
import { apiExportInvoices } from '@/lib/api';

interface BottomActionBarProps {
  selectedIds: string[];
  onSave: () => void;
  onCancel: () => void;
  onSend?: () => Promise<void>;
}

export default function BottomActionBar({ selectedIds, onSave, onCancel, onSend }: BottomActionBarProps) {
  const [isExporting, setIsExporting] = useState(false);

  const handleSend = async () => {
    if (selectedIds.length === 0) {
      alert('Please select at least one invoice');
      return;
    }

    if (onSend) {
      await onSend();
      return;
    }

    // Default export behavior
    setIsExporting(true);
    try {
      const result = await apiExportInvoices(selectedIds);
      if (result.ok) {
        alert(`Exported to ${result.zip_path}`);
      } else {
        alert('Export failed');
      }
    } catch (error: any) {
      console.error('Export failed:', error);
      alert(`Export failed: ${error.message}`);
    } finally {
      setIsExporting(false);
    }
  };

  if (selectedIds.length === 0) {
    return null;
  }

  return (
    <div className="fixed bottom-0 left-0 right-0 bg-white border-t shadow-lg p-4">
      <div className="max-w-6xl mx-auto flex items-center justify-between">
        <div className="text-sm text-gray-600">
          {selectedIds.length} invoice{selectedIds.length !== 1 ? 's' : ''} selected
        </div>
        
        <div className="flex items-center gap-3">
          <button
            onClick={onCancel}
            className="px-4 py-2 text-sm border border-gray-300 rounded-lg hover:bg-gray-50"
          >
            Clear All
          </button>
          
          <button
            onClick={onSave}
            className="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700"
          >
            Save Draft
          </button>
          
          <button
            onClick={handleSend}
            disabled={isExporting}
            className="px-4 py-2 text-sm bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50"
          >
            {isExporting ? 'Submitting...' : 'Submit to Owlin'}
          </button>
        </div>
      </div>
    </div>
  );
}
