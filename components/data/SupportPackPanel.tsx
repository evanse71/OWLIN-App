import React, { useState, useEffect } from 'react';

interface SupportPackInfo {
  id: string;
  created_at: string;
  path: string;
  size_bytes: number;
  notes?: string;
  app_version: string;
}

interface SupportPackPanelProps {
  onBanner: (type: 'success' | 'error', message: string) => void;
}

export default function SupportPackPanel({ onBanner }: SupportPackPanelProps) {
  const [packs, setPacks] = useState<SupportPackInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [notes, setNotes] = useState('');

  useEffect(() => {
    fetchPacks();
  }, []);

  const fetchPacks = async () => {
    try {
      const response = await fetch('/api/support-packs');
      if (response.ok) {
        const data = await response.json();
        setPacks(data);
      } else {
        onBanner('error', 'Failed to fetch support packs');
      }
    } catch (error) {
      onBanner('error', 'Failed to fetch support packs');
    } finally {
      setLoading(false);
    }
  };

  const handleCreatePack = async () => {
    try {
      setCreating(true);
      const response = await fetch('/api/support-packs', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ notes: notes || undefined }),
      });
      
      if (response.ok) {
        const result = await response.json();
        onBanner('success', `Support pack created successfully (${(result.size_bytes / 1024 / 1024).toFixed(1)}MB)`);
        setNotes('');
        fetchPacks(); // Refresh list
      } else {
        const error = await response.json();
        onBanner('error', `Support pack creation failed: ${error.detail || 'Unknown error'}`);
      }
    } catch (error) {
      onBanner('error', 'Failed to create support pack');
    } finally {
      setCreating(false);
    }
  };

  const handleDownload = async (packId: string, filename: string) => {
    try {
      const response = await fetch(`/api/support-packs/${packId}/download`);
      
      if (response.ok) {
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
        
        onBanner('success', 'Support pack downloaded successfully');
      } else {
        onBanner('error', 'Failed to download support pack');
      }
    } catch (error) {
      onBanner('error', 'Failed to download support pack');
    }
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
          <div className="text-gray-500">Loading support packs...</div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-white rounded-lg border border-gray-200 p-6">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="text-lg font-semibold text-gray-900">Support Packs</h2>
            <p className="text-sm text-gray-600 mt-1">
              Generate support packs for troubleshooting and system analysis.
            </p>
          </div>
        </div>

        {/* Create Form */}
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Notes (optional)
            </label>
            <textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="e.g., post-incident analysis, system upgrade..."
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              rows={3}
            />
          </div>
          
          <div className="flex items-center justify-between">
            <div className="text-sm text-gray-600">
              A Support Pack bundles logs, a DB snapshot, and a system report. No personal data.
            </div>
            <button
              onClick={handleCreatePack}
              disabled={creating}
              className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors"
            >
              {creating ? 'Creating...' : 'Generate Support Pack'}
            </button>
          </div>
        </div>
      </div>

      {/* Pack List */}
      {packs.length === 0 ? (
        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <div className="text-center text-gray-500">
            <p>No support packs yet. Generate one to get started.</p>
          </div>
        </div>
      ) : (
        <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
          <div className="px-6 py-4 border-b border-gray-200">
            <h3 className="text-lg font-medium text-gray-900">Available Support Packs</h3>
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
                    Version
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Notes
                  </th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {packs.map((pack) => (
                  <tr key={pack.id} className="hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {formatDate(pack.created_at)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {formatFileSize(pack.size_bytes)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {pack.app_version}
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-900">
                      {pack.notes || '-'}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                      <button
                        onClick={() => handleDownload(pack.id, `support_pack_${pack.id}.zip`)}
                        className="text-blue-600 hover:text-blue-900"
                      >
                        Download
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
