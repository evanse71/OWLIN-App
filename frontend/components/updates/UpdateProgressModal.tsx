import React, { useState, useEffect } from 'react';

interface UpdateProgressTick {
  job_id: string;
  kind: 'apply' | 'rollback';
  step: 'preflight' | 'snapshot' | 'apply' | 'finalise' | 'done' | 'error';
  percent: number;
  message?: string;
  occurred_at: string;
}

interface UpdateProgressModalProps {
  jobId: string;
  kind: 'apply' | 'rollback';
  onClose: () => void;
}

export default function UpdateProgressModal({ jobId, kind, onClose }: UpdateProgressModalProps) {
  const [progress, setProgress] = useState<UpdateProgressTick[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const pollProgress = async () => {
      try {
        const response = await fetch(`/api/updates/progress/${jobId}`);
        if (response.ok) {
          const data = await response.json();
          setProgress(data);
          
          // Check if we're done
          const lastTick = data[data.length - 1];
          if (lastTick && (lastTick.step === 'done' || lastTick.step === 'error')) {
            setLoading(false);
            if (lastTick.step === 'error') {
              setError(lastTick.message || 'Update failed');
            } else {
              // Auto-close on success after 2 seconds
              setTimeout(() => {
                onClose();
              }, 2000);
            }
          }
        } else {
          setError('Failed to fetch progress');
          setLoading(false);
        }
      } catch (err) {
        setError('Network error');
        setLoading(false);
      }
    };

    // Poll every second
    const interval = setInterval(pollProgress, 1000);
    pollProgress(); // Initial call

    return () => clearInterval(interval);
  }, [jobId, onClose]);

  const getStepLabel = (step: string) => {
    switch (step) {
      case 'preflight': return 'Preflight Checks';
      case 'snapshot': return 'Creating Snapshot';
      case 'apply': return 'Applying Update';
      case 'finalise': return 'Finalizing';
      case 'done': return 'Complete';
      case 'error': return 'Error';
      default: return step;
    }
  };

  const getCurrentProgress = () => {
    if (progress.length === 0) return 0;
    return progress[progress.length - 1].percent;
  };

  const getCurrentStep = () => {
    if (progress.length === 0) return 'Starting...';
    return getStepLabel(progress[progress.length - 1].step);
  };

  const getCurrentMessage = () => {
    if (progress.length === 0) return '';
    return progress[progress.length - 1].message || '';
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg p-6 w-96 max-w-full mx-4">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-gray-900">
            {kind === 'apply' ? 'Applying Update' : 'Rolling Back'}
          </h2>
          {!loading && (
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-gray-600"
            >
              ✕
            </button>
          )}
        </div>

        <div className="space-y-4">
          {/* Progress Bar */}
          <div className="w-full bg-gray-200 rounded-full h-2">
            <div
              className="bg-blue-600 h-2 rounded-full transition-all duration-300"
              style={{ width: `${getCurrentProgress()}%` }}
            />
          </div>

          {/* Progress Info */}
          <div className="text-center">
            <div className="text-2xl font-bold text-gray-900">{getCurrentProgress()}%</div>
            <div className="text-sm text-gray-600">{getCurrentStep()}</div>
            {getCurrentMessage() && (
              <div className="text-xs text-gray-500 mt-1">{getCurrentMessage()}</div>
            )}
          </div>

          {/* Progress History */}
          <div className="max-h-32 overflow-y-auto">
            <div className="space-y-1">
              {progress.map((tick, index) => (
                <div key={index} className="flex items-center gap-2 text-xs">
                  <div className={`w-2 h-2 rounded-full ${
                    tick.step === 'done' ? 'bg-green-500' :
                    tick.step === 'error' ? 'bg-red-500' : 'bg-blue-500'
                  }`} />
                  <span className="text-gray-600">{getStepLabel(tick.step)}</span>
                  <span className="text-gray-400">({tick.percent}%)</span>
                  {tick.message && (
                    <span className="text-gray-500">- {tick.message}</span>
                  )}
                </div>
              ))}
            </div>
          </div>

          {/* Error State */}
          {error && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-3">
              <div className="text-sm text-red-800">
                <strong>Error:</strong> {error}
              </div>
              <button
                onClick={() => window.location.reload()}
                className="mt-2 text-sm text-red-600 hover:text-red-800 underline"
              >
                Retry
              </button>
            </div>
          )}

          {/* Success State */}
          {!loading && !error && getCurrentProgress() === 100 && (
            <div className="bg-green-50 border border-green-200 rounded-lg p-3">
              <div className="text-sm text-green-800">
                <strong>Success!</strong> Update completed successfully.
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
