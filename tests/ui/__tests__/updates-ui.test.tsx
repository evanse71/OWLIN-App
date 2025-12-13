import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import UpdateBadge from '@/components/updates/UpdateBadge';
import UpdateDetailsPanel from '@/components/updates/UpdateDetailsPanel';
import UpdateProgressModal from '@/components/updates/UpdateProgressModal';
import RollbackConfirmDialog from '@/components/updates/RollbackConfirmDialog';

// Mock fetch
global.fetch = jest.fn();

describe('UpdateBadge', () => {
  it('renders validation badge with ok status', () => {
    render(
      <UpdateBadge
        type="validation"
        status="ok"
        text="Signature Valid"
      />
    );
    
    expect(screen.getByText('✓')).toBeInTheDocument();
    expect(screen.getByText('Signature Valid')).toBeInTheDocument();
  });

  it('renders dependency badge with warn status', () => {
    render(
      <UpdateBadge
        type="dependency"
        status="warn"
        text="Missing dependency"
      />
    );
    
    expect(screen.getByText('⚠')).toBeInTheDocument();
    expect(screen.getByText('Missing dependency')).toBeInTheDocument();
  });

  it('renders error status with correct styling', () => {
    render(
      <UpdateBadge
        type="validation"
        status="error"
        text="Invalid signature"
      />
    );
    
    expect(screen.getByText('✗')).toBeInTheDocument();
    expect(screen.getByText('Invalid signature')).toBeInTheDocument();
  });
});

describe('UpdateDetailsPanel', () => {
  const mockBundle = {
    id: 'test-bundle-123',
    filename: 'update_1.3.0.zip',
    version: '1.3.0',
    build: '2025-08-10.1',
    created_at: '2025-08-10T12:34:56Z',
    description: 'Test update',
    verified: 'pending' as const,
    reason: null
  };

  const mockOnClose = jest.fn();
  const mockOnApply = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders bundle information', () => {
    render(
      <UpdateDetailsPanel
        bundle={mockBundle}
        onClose={mockOnClose}
        onApply={mockOnApply}
      />
    );
    
    expect(screen.getByText('Update Details')).toBeInTheDocument();
    expect(screen.getByText('1.3.0')).toBeInTheDocument();
    expect(screen.getByText('2025-08-10.1')).toBeInTheDocument();
    expect(screen.getByText('Test update')).toBeInTheDocument();
  });

  it('calls onClose when close button is clicked', () => {
    render(
      <UpdateDetailsPanel
        bundle={mockBundle}
        onClose={mockOnClose}
        onApply={mockOnApply}
      />
    );
    
    const closeButton = screen.getByText('✕');
    fireEvent.click(closeButton);
    
    expect(mockOnClose).toHaveBeenCalledTimes(1);
  });

  it('calls onApply when apply button is clicked', () => {
    render(
      <UpdateDetailsPanel
        bundle={mockBundle}
        onClose={mockOnClose}
        onApply={mockOnApply}
      />
    );
    
    const applyButton = screen.getByText('Apply Update');
    fireEvent.click(applyButton);
    
    expect(mockOnApply).toHaveBeenCalledWith('test-bundle-123');
  });

  it('shows validation results when validate is clicked', async () => {
    const mockValidationResponse = {
      bundle_id: 'test-bundle-123',
      filename: 'update_1.3.0.zip',
      version: '1.3.0',
      build: '2025-08-10.1',
      signature_ok: true,
      manifest_ok: true,
      reason: null,
      checksum_sha256: 'test-checksum',
      created_at: '2025-08-10T12:34:56Z'
    };

    (fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => mockValidationResponse
    });

    render(
      <UpdateDetailsPanel
        bundle={mockBundle}
        onClose={mockOnClose}
        onApply={mockOnApply}
      />
    );
    
    const validateButton = screen.getByText('Validate');
    fireEvent.click(validateButton);
    
    await waitFor(() => {
      expect(screen.getByText('Signature Valid')).toBeInTheDocument();
      expect(screen.getByText('Manifest Valid')).toBeInTheDocument();
    });
  });
});

describe('UpdateProgressModal', () => {
  const mockOnClose = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders progress modal with job ID', () => {
    render(
      <UpdateProgressModal
        jobId="test-job-123"
        kind="apply"
        onClose={mockOnClose}
      />
    );
    
    expect(screen.getByText('Applying Update')).toBeInTheDocument();
    expect(screen.getByText('0%')).toBeInTheDocument();
  });

  it('shows progress updates', async () => {
    const mockProgressResponse = [
      {
        job_id: 'test-job-123',
        kind: 'apply',
        step: 'preflight',
        percent: 10,
        message: 'Preflight checks',
        occurred_at: '2025-08-14T10:00:00Z'
      },
      {
        job_id: 'test-job-123',
        kind: 'apply',
        step: 'done',
        percent: 100,
        message: 'Complete',
        occurred_at: '2025-08-14T10:00:05Z'
      }
    ];

    (fetch as jest.Mock).mockResolvedValue({
      ok: true,
      json: async () => mockProgressResponse
    });

    render(
      <UpdateProgressModal
        jobId="test-job-123"
        kind="apply"
        onClose={mockOnClose}
      />
    );
    
    await waitFor(() => {
      expect(screen.getByText('100%')).toBeInTheDocument();
      expect(screen.getByText('Complete')).toBeInTheDocument();
    });
  });

  it('shows error state', async () => {
    const mockErrorResponse = [
      {
        job_id: 'test-job-123',
        kind: 'apply',
        step: 'error',
        percent: 100,
        message: 'Update failed',
        occurred_at: '2025-08-14T10:00:05Z'
      }
    ];

    (fetch as jest.Mock).mockResolvedValue({
      ok: true,
      json: async () => mockErrorResponse
    });

    render(
      <UpdateProgressModal
        jobId="test-job-123"
        kind="apply"
        onClose={mockOnClose}
      />
    );
    
    await waitFor(() => {
      expect(screen.getByText('Error: Update failed')).toBeInTheDocument();
      expect(screen.getByText('Retry')).toBeInTheDocument();
    });
  });
});

describe('RollbackConfirmDialog', () => {
  const mockOnConfirm = jest.fn();
  const mockOnCancel = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders confirmation dialog', () => {
    render(
      <RollbackConfirmDialog
        backupDate="2025-08-10"
        onConfirm={mockOnConfirm}
        onCancel={mockOnCancel}
      />
    );
    
    expect(screen.getByText('Confirm Rollback')).toBeInTheDocument();
    expect(screen.getByText(/This will revert to the backup from/)).toBeInTheDocument();
    expect(screen.getByText('2025-08-10')).toBeInTheDocument();
  });

  it('enables confirm button when ROLLBACK is typed', () => {
    render(
      <RollbackConfirmDialog
        backupDate="2025-08-10"
        onConfirm={mockOnConfirm}
        onCancel={mockOnCancel}
      />
    );
    
    const input = screen.getByPlaceholderText('ROLLBACK');
    const confirmButton = screen.getByText('Confirm Rollback');
    
    // Initially disabled
    expect(confirmButton).toBeDisabled();
    
    // Type ROLLBACK
    fireEvent.change(input, { target: { value: 'ROLLBACK' } });
    
    // Now enabled
    expect(confirmButton).not.toBeDisabled();
  });

  it('calls onConfirm when ROLLBACK is typed and confirm is clicked', () => {
    render(
      <RollbackConfirmDialog
        backupDate="2025-08-10"
        onConfirm={mockOnConfirm}
        onCancel={mockOnCancel}
      />
    );
    
    const input = screen.getByPlaceholderText('ROLLBACK');
    const confirmButton = screen.getByText('Confirm Rollback');
    
    fireEvent.change(input, { target: { value: 'ROLLBACK' } });
    fireEvent.click(confirmButton);
    
    expect(mockOnConfirm).toHaveBeenCalledTimes(1);
  });

  it('calls onCancel when cancel is clicked', () => {
    render(
      <RollbackConfirmDialog
        backupDate="2025-08-10"
        onConfirm={mockOnConfirm}
        onCancel={mockOnCancel}
      />
    );
    
    const cancelButton = screen.getByText('Cancel');
    fireEvent.click(cancelButton);
    
    expect(mockOnCancel).toHaveBeenCalledTimes(1);
  });
});
