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

interface UpdateValidateResult {
  bundle_id: string;
  filename: string;
  version: string;
  build: string;
  signature_ok: boolean;
  manifest_ok: boolean;
  reason?: string;
  checksum_sha256?: string;
  created_at?: string;
}

interface DependencyItem {
  id: string;
  version: string;
  satisfied: boolean;
  reason?: string;
}

interface UpdateDependencies {
  bundle_id: string;
  items: DependencyItem[];
  all_satisfied: boolean;
}

interface UpdateDetailsPanelProps {
  bundle: UpdateBundle | null;
  onClose: () => void;
  onApply: (bundleId: string) => void;
}

export default function UpdateDetailsPanel({ bundle, onClose, onApply }: UpdateDetailsPanelProps) {
  const [validation, setValidation] = useState<UpdateValidateResult | null>(null);
  const [dependencies, setDependencies] = useState<UpdateDependencies | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (bundle) {
      loadValidation();
      loadDependencies();
    }
  }, [bundle]);

  const loadValidation = async () => {
    if (!bundle) return;
    
    try {
      const response = await fetch(`/api/updates/validate/${bundle.id}`);
      if (response.ok) {
        const data = await response.json();
        setValidation(data);
      }
    } catch (error) {
      console.error('Failed to load validation:', error);
    }
  };

  const loadDependencies = async () => {
    if (!bundle) return;
    
    try {
      const response = await fetch(`/api/updates/dependencies/${bundle.id}`);
      if (response.ok) {
        const data = await response.json();
        setDependencies(data);
      }
    } catch (error) {
      console.error('Failed to load dependencies:', error);
    }
  };

  const handleValidate = async () => {
    if (!bundle) return;
    setLoading(true);
    try {
      await loadValidation();
    } finally {
      setLoading(false);
    }
  };

  const handleCheckDeps = async () => {
    if (!bundle) return;
    setLoading(true);
    try {
      await loadDependencies();
    } finally {
      setLoading(false);
    }
  };

  const handleApply = () => {
    if (bundle) {
      onApply(bundle.id);
    }
  };

  if (!bundle) {
    return null;
  }

  return (
    <div className="fixed inset-y-0 right-0 w-96 bg-white border-l border-gray-200 shadow-lg overflow-y-auto">
      <div className="p-6">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-lg font-semibold text-gray-900">Update Details</h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600"
          >
            ✕
          </button>
        </div>

        <div className="space-y-6">
          {/* Bundle Info */}
          <div className="bg-gray-50 rounded-lg p-4">
            <h3 className="font-medium text-gray-900 mb-2">Bundle Information</h3>
            <div className="space-y-2 text-sm">
              <div><span className="font-medium">Version:</span> {bundle.version}</div>
              <div><span className="font-medium">Build:</span> {bundle.build}</div>
              <div><span className="font-medium">Created:</span> {new Date(bundle.created_at).toLocaleDateString()}</div>
              {bundle.description && (
                <div><span className="font-medium">Description:</span> {bundle.description}</div>
              )}
            </div>
          </div>

          {/* Validation */}
          <div className="bg-gray-50 rounded-lg p-4">
            <div className="flex items-center justify-between mb-2">
              <h3 className="font-medium text-gray-900">Validation</h3>
              <button
                onClick={handleValidate}
                disabled={loading}
                className="text-sm text-blue-600 hover:text-blue-800 disabled:opacity-50"
              >
                {loading ? 'Validating...' : 'Validate'}
              </button>
            </div>
            
            {validation && (
              <div className="space-y-2">
                <UpdateBadge
                  type="validation"
                  status={validation.signature_ok ? 'ok' : 'error'}
                  text={validation.signature_ok ? 'Signature Valid' : 'Signature Invalid'}
                />
                <UpdateBadge
                  type="validation"
                  status={validation.manifest_ok ? 'ok' : 'error'}
                  text={validation.manifest_ok ? 'Manifest Valid' : 'Manifest Invalid'}
                />
                {validation.checksum_sha256 && (
                  <div className="text-xs text-gray-600">
                    <span className="font-medium">Checksum:</span> {validation.checksum_sha256.substring(0, 16)}...
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Dependencies */}
          <div className="bg-gray-50 rounded-lg p-4">
            <div className="flex items-center justify-between mb-2">
              <h3 className="font-medium text-gray-900">Dependencies</h3>
              <button
                onClick={handleCheckDeps}
                disabled={loading}
                className="text-sm text-blue-600 hover:text-blue-800 disabled:opacity-50"
              >
                {loading ? 'Checking...' : 'Check Dependencies'}
              </button>
            </div>
            
            {dependencies && (
              <div className="space-y-2">
                {dependencies.items.map((item) => (
                  <UpdateBadge
                    key={item.id}
                    type="dependency"
                    status={item.satisfied ? 'ok' : 'warn'}
                    text={`${item.id} ${item.version} ${item.satisfied ? '✓' : '✗'}`}
                  />
                ))}
                {dependencies.items.length === 0 && (
                  <div className="text-sm text-gray-600">No dependencies found</div>
                )}
              </div>
            )}
          </div>

          {/* Actions */}
          <div className="space-y-3">
            <button
              onClick={handleApply}
              disabled={!validation?.signature_ok || !validation?.manifest_ok || !dependencies?.all_satisfied}
              className="w-full bg-blue-600 text-white py-2 px-4 rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Apply Update
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
