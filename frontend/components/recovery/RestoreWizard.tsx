import React, { useState, useEffect } from 'react';
import { 
  recoveryClient, 
  RecoveryStatus, 
  SnapshotInfo, 
  RestorePreview, 
  TableDiff,
  ResolvePlan 
} from '../../lib/recoveryClient';
import TableDiffComponent from './TableDiff';

interface RestoreWizardProps {
  onClose: () => void;
}

type WizardStep = 'select' | 'preview' | 'resolve' | 'commit';

export default function RestoreWizard({ onClose }: RestoreWizardProps) {
  const [currentStep, setCurrentStep] = useState<WizardStep>('select');
  const [status, setStatus] = useState<RecoveryStatus | null>(null);
  const [selectedSnapshot, setSelectedSnapshot] = useState<SnapshotInfo | null>(null);
  const [preview, setPreview] = useState<RestorePreview | null>(null);
  const [currentTable, setCurrentTable] = useState<string>('');
  const [tableDiff, setTableDiff] = useState<TableDiff | null>(null);
  const [decisions, setDecisions] = useState<Record<string, Record<string, string>>>({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadStatus();
  }, []);

  const loadStatus = async () => {
    try {
      setLoading(true);
      setError(null);
      const recoveryStatus = await recoveryClient.getStatus();
      setStatus(recoveryStatus);
    } catch (err) {
      setError('Failed to load recovery status');
    } finally {
      setLoading(false);
    }
  };

  const handleSnapshotSelect = async (snapshot: SnapshotInfo) => {
    try {
      setLoading(true);
      setError(null);
      setSelectedSnapshot(snapshot);
      
      const previewData = await recoveryClient.previewRestore(snapshot.id);
      setPreview(previewData);
      setCurrentStep('preview');
    } catch (err) {
      setError('Failed to create preview');
    } finally {
      setLoading(false);
    }
  };

  const handleTableSelect = async (table: string) => {
    if (!selectedSnapshot) return;
    
    try {
      setLoading(true);
      setError(null);
      setCurrentTable(table);
      
      const diff = await recoveryClient.getTableDiff(table, selectedSnapshot.id);
      setTableDiff(diff);
      setCurrentStep('resolve');
    } catch (err) {
      setError('Failed to load table diff');
    } finally {
      setLoading(false);
    }
  };

  const handleDecisionChange = (rowKey: string, decision: string) => {
    setDecisions(prev => ({
      ...prev,
      [currentTable]: {
        ...prev[currentTable],
        [rowKey]: decision
      }
    }));
  };

  const handleCommit = async () => {
    if (!selectedSnapshot) return;
    
    try {
      setLoading(true);
      setError(null);
      
      const resolvePlan: ResolvePlan = {
        snapshot_id: selectedSnapshot.id,
        decisions: decisions
      };
      
      const result = await recoveryClient.commitRestore(resolvePlan);
      
      if (result.ok) {
        setCurrentStep('commit');
      } else {
        setError('Restore failed');
      }
    } catch (err) {
      setError('Failed to commit restore');
    } finally {
      setLoading(false);
    }
  };

  const getStepTitle = (step: WizardStep) => {
    switch (step) {
      case 'select': return 'Select Snapshot';
      case 'preview': return 'Preview Changes';
      case 'resolve': return 'Resolve Conflicts';
      case 'commit': return 'Commit Restore';
    }
  };

  const renderSelectStep = () => (
    <div className="space-y-4">
      <h3 className="text-[16px] font-semibold text-[#1F2937]">Available Snapshots</h3>
      {status?.snapshots.map((snapshot) => (
        <div 
          key={snapshot.id}
          className={`p-4 border rounded-[12px] cursor-pointer transition-colors ${
            snapshot.manifest_ok 
              ? 'border-[#E5E7EB] hover:border-[#3B82F6]' 
              : 'border-[#FCA5A5] opacity-50 cursor-not-allowed'
          }`}
          onClick={() => snapshot.manifest_ok && handleSnapshotSelect(snapshot)}
        >
          <div className="flex items-center justify-between">
            <div>
              <div className="font-medium text-[#1F2937]">{snapshot.id}</div>
              <div className="text-sm text-[#6B7280]">
                Created: {new Date(snapshot.created_at).toLocaleString()}
              </div>
              <div className="text-sm text-[#6B7280]">
                Size: {(snapshot.size_bytes / 1024 / 1024).toFixed(2)} MB
              </div>
            </div>
            <div className="flex items-center gap-2">
              {snapshot.manifest_ok ? (
                <span className="px-2 py-1 bg-green-100 text-green-800 rounded text-xs font-medium">
                  Valid
                </span>
              ) : (
                <span className="px-2 py-1 bg-red-100 text-red-800 rounded text-xs font-medium">
                  Invalid
                </span>
              )}
            </div>
          </div>
        </div>
      ))}
    </div>
  );

  const renderPreviewStep = () => (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-[16px] font-semibold text-[#1F2937]">Preview Changes</h3>
        <div className="text-sm text-[#6B7280]">
          Snapshot: {selectedSnapshot?.id}
        </div>
      </div>
      
      <div className="grid grid-cols-3 gap-4 mb-6">
        <div className="p-4 bg-green-50 border border-green-200 rounded-[12px]">
          <div className="text-2xl font-bold text-green-600">{preview?.summary.rows_add}</div>
          <div className="text-sm text-green-700">Rows to Add</div>
        </div>
        <div className="p-4 bg-red-50 border border-red-200 rounded-[12px]">
          <div className="text-2xl font-bold text-red-600">{preview?.summary.rows_remove}</div>
          <div className="text-sm text-red-700">Rows to Remove</div>
        </div>
        <div className="p-4 bg-amber-50 border border-amber-200 rounded-[12px]">
          <div className="text-2xl font-bold text-amber-600">{preview?.summary.rows_change}</div>
          <div className="text-sm text-amber-700">Rows to Change</div>
        </div>
      </div>
      
      <div className="space-y-2">
        <h4 className="text-[14px] font-medium text-[#374151]">Affected Tables</h4>
        {preview?.tables.map((table) => (
          <div 
            key={table.table}
            className="p-3 border border-[#E5E7EB] rounded-[8px] cursor-pointer hover:bg-[#F9FAFB]"
            onClick={() => handleTableSelect(table.table)}
          >
            <div className="flex items-center justify-between">
              <div className="font-medium text-[#1F2937]">{table.table}</div>
              <div className="flex items-center gap-4 text-sm text-[#6B7280]">
                <span>+{table.stats.add}</span>
                <span>-{table.stats.remove}</span>
                <span>~{table.stats.change}</span>
                <span>={table.stats.identical}</span>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );

  const renderResolveStep = () => (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-[16px] font-semibold text-[#1F2937]">Resolve Conflicts</h3>
        <div className="text-sm text-[#6B7280]">
          Table: {currentTable}
        </div>
      </div>
      
      {tableDiff && (
        <TableDiffComponent
          diff={tableDiff}
          onDecisionChange={handleDecisionChange}
          decisions={decisions[currentTable] || {}}
        />
      )}
    </div>
  );

  const renderCommitStep = () => (
    <div className="text-center space-y-4">
      <svg 
        xmlns="http://www.w3.org/2000/svg" 
        width="48" 
        height="48" 
        fill="none" 
        stroke="#15803D" 
        strokeWidth="2" 
        strokeLinecap="round" 
        strokeLinejoin="round" 
        className="mx-auto"
        aria-label="Success"
      >
        <path d="M3 8l3 3 7-7"/>
      </svg>
      
      <h3 className="text-[18px] font-semibold text-[#1F2937]">Restore Completed Successfully</h3>
      <p className="text-[#6B7280]">
        The database has been restored from snapshot {selectedSnapshot?.id}. 
        All changes have been applied and the system is now stable.
      </p>
    </div>
  );

  const renderStepContent = () => {
    switch (currentStep) {
      case 'select': return renderSelectStep();
      case 'preview': return renderPreviewStep();
      case 'resolve': return renderResolveStep();
      case 'commit': return renderCommitStep();
    }
  };

  const canGoNext = () => {
    switch (currentStep) {
      case 'select': return selectedSnapshot !== null;
      case 'preview': return true;
      case 'resolve': return Object.keys(decisions).length > 0;
      case 'commit': return false;
    }
  };

  const handleNext = () => {
    if (currentStep === 'resolve') {
      handleCommit();
    } else {
      // Other steps are handled by user actions
    }
  };

  const handleBack = () => {
    switch (currentStep) {
      case 'preview':
        setCurrentStep('select');
        break;
      case 'resolve':
        setCurrentStep('preview');
        break;
    }
  };

  if (loading) {
    return (
      <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
        <div className="bg-white rounded-[12px] p-6">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-[#3B82F6] mx-auto"></div>
          <div className="text-center mt-4 text-[#6B7280]">Loading...</div>
        </div>
      </div>
    );
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-[12px] max-w-4xl w-full mx-4 max-h-[90vh] overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-[#E5E7EB]">
          <h2 className="text-[18px] font-semibold text-[#1F2937]">
            {getStepTitle(currentStep)}
          </h2>
          <button onClick={onClose} className="text-[#6B7280] hover:text-[#374151] transition-colors">
            <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M18 6L6 18M6 6l12 12"/>
            </svg>
          </button>
        </div>

        {/* Content */}
        <div className="p-6 overflow-y-auto max-h-[calc(90vh-120px)]">
          {error && (
            <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-[8px] text-red-700">
              {error}
            </div>
          )}
          
          {renderStepContent()}
        </div>

        {/* Footer */}
        {currentStep !== 'commit' && (
          <div className="flex items-center justify-between p-6 border-t border-[#E5E7EB]">
            <button
              onClick={handleBack}
              disabled={currentStep === 'select'}
              className="px-4 py-2 text-[#6B7280] hover:text-[#374151] disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Back
            </button>
            
            <div className="flex items-center gap-2">
              {currentStep === 'resolve' && (
                <button
                  onClick={handleNext}
                  disabled={!canGoNext()}
                  className="px-4 py-2 bg-[#3B82F6] text-white rounded-[6px] font-medium hover:bg-[#2563EB] disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  Commit Restore
                </button>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
} 