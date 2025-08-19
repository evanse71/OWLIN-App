import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import RecoveryBanner from '../../components/recovery/RecoveryBanner';
import TableDiff from '../../components/recovery/TableDiff';
import RestoreWizard from '../../components/recovery/RestoreWizard';

// Mock the recovery client
jest.mock('../../lib/recoveryClient', () => ({
  recoveryClient: {
    getStatus: jest.fn(),
    scanSystem: jest.fn(),
    previewRestore: jest.fn(),
    getTableDiff: jest.fn(),
    commitRestore: jest.fn(),
  },
}));

const mockRecoveryStatus = {
  state: 'recovery' as const,
  reason: 'INTEGRITY_FAILED',
  details: ['Database integrity check failed'],
  snapshots: [
    {
      id: '2025-08-14T10-00-00Z',
      size_bytes: 1024000,
      created_at: '2025-08-14T10:00:00Z',
      manifest_ok: true,
    },
  ],
  live_db_hash: 'abc123',
  schema_version: 1,
  app_version: '1.0.0',
};

const mockTableDiff = {
  table: 'invoices',
  pk: ['id'],
  stats: {
    add: 2,
    remove: 1,
    change: 3,
    identical: 10,
  },
  rows: [
    {
      key: 'id=INV-001',
      op: 'change' as const,
      cells: [
        {
          col: 'amount',
          old: 100.50,
          new: 150.75,
          changed: true,
        },
        {
          col: 'supplier_id',
          old: 'SUP-001',
          new: 'SUP-001',
          changed: false,
        },
      ],
    },
  ],
};

describe('RecoveryBanner', () => {
  it('renders banner when state is not normal', () => {
    render(<RecoveryBanner status={mockRecoveryStatus} />);
    
    expect(screen.getByText(/Database integrity issues detected/)).toBeInTheDocument();
    expect(screen.getByLabelText('Recovery mode')).toBeInTheDocument();
  });

  it('does not render when state is normal', () => {
    const normalStatus = { ...mockRecoveryStatus, state: 'normal' as const };
    const { container } = render(<RecoveryBanner status={normalStatus} />);
    
    expect(container.firstChild).toBeNull();
  });

  it('shows different text for different reasons', () => {
    const schemaMismatchStatus = { ...mockRecoveryStatus, reason: 'SCHEMA_MISMATCH' };
    render(<RecoveryBanner status={schemaMismatchStatus} />);
    
    expect(screen.getByText(/Schema version mismatch detected/)).toBeInTheDocument();
  });

  it('shows update incomplete message', () => {
    const updateIncompleteStatus = { ...mockRecoveryStatus, reason: 'UPDATE_INCOMPLETE' };
    render(<RecoveryBanner status={updateIncompleteStatus} />);
    
    expect(screen.getByText(/Incomplete update detected/)).toBeInTheDocument();
  });

  it('shows default message for unknown reason', () => {
    const unknownStatus = { ...mockRecoveryStatus, reason: 'UNKNOWN_REASON' };
    render(<RecoveryBanner status={unknownStatus} />);
    
    expect(screen.getByText(/System issues detected/)).toBeInTheDocument();
  });

  it('has correct styling classes', () => {
    render(<RecoveryBanner status={mockRecoveryStatus} />);
    
    const banner = screen.getByText(/Database integrity issues detected/).closest('div');
    expect(banner).toHaveClass('bg-[#FFF7ED]', 'border-[#FDE68A]', 'text-[#4B5563]');
  });
});

describe('TableDiff', () => {
  const mockOnDecisionChange = jest.fn();
  const mockDecisions = { 'id=INV-001': 'keep_live' };

  beforeEach(() => {
    mockOnDecisionChange.mockClear();
  });

  it('renders table with correct headers', () => {
    render(
      <TableDiff
        diff={mockTableDiff}
        onDecisionChange={mockOnDecisionChange}
        decisions={mockDecisions}
      />
    );

    expect(screen.getByText('Table: invoices')).toBeInTheDocument();
    expect(screen.getByText('Decision')).toBeInTheDocument();
    expect(screen.getByText('Op')).toBeInTheDocument();
    expect(screen.getByText('Row Key')).toBeInTheDocument();
  });

  it('shows correct statistics', () => {
    render(
      <TableDiff
        diff={mockTableDiff}
        onDecisionChange={mockOnDecisionChange}
        decisions={mockDecisions}
      />
    );

    expect(screen.getByText('Add: 2')).toBeInTheDocument();
    expect(screen.getByText('Remove: 1')).toBeInTheDocument();
    expect(screen.getByText('Change: 3')).toBeInTheDocument();
    expect(screen.getByText('Identical: 10')).toBeInTheDocument();
  });

  it('calls onDecisionChange when decision is changed', () => {
    render(
      <TableDiff
        diff={mockTableDiff}
        onDecisionChange={mockOnDecisionChange}
        decisions={mockDecisions}
      />
    );

    const select = screen.getByDisplayValue('Keep Live');
    fireEvent.change(select, { target: { value: 'take_snapshot' } });

    expect(mockOnDecisionChange).toHaveBeenCalledWith('id=INV-001', 'take_snapshot');
  });

  it('shows operation badges', () => {
    render(
      <TableDiff
        diff={mockTableDiff}
        onDecisionChange={mockOnDecisionChange}
        decisions={mockDecisions}
      />
    );

    expect(screen.getByText('CHANGE')).toBeInTheDocument();
  });

  it('expands row details when clicked', () => {
    render(
      <TableDiff
        diff={mockTableDiff}
        onDecisionChange={mockOnDecisionChange}
        decisions={mockDecisions}
      />
    );

    const rowKeyButton = screen.getByText(/id=INV-001/);
    fireEvent.click(rowKeyButton);

    expect(screen.getByText('Live Data')).toBeInTheDocument();
    expect(screen.getByText('Snapshot Data')).toBeInTheDocument();
  });

  it('shows different operation badges for different ops', () => {
    const diffWithMultipleOps = {
      ...mockTableDiff,
      rows: [
        { ...mockTableDiff.rows[0], op: 'add' as const },
        { ...mockTableDiff.rows[0], key: 'id=INV-002', op: 'remove' as const },
        { ...mockTableDiff.rows[0], key: 'id=INV-003', op: 'identical' as const },
      ],
    };

    render(
      <TableDiff
        diff={diffWithMultipleOps}
        onDecisionChange={mockOnDecisionChange}
        decisions={mockDecisions}
      />
    );

    expect(screen.getByText('ADD')).toBeInTheDocument();
    expect(screen.getByText('REMOVE')).toBeInTheDocument();
    expect(screen.getByText('IDENTICAL')).toBeInTheDocument();
  });

  it('formats values correctly', () => {
    const diffWithNullValues = {
      ...mockTableDiff,
      rows: [
        {
          key: 'id=INV-001',
          op: 'change' as const,
          cells: [
            {
              col: 'amount',
              old: null,
              new: 150.75,
              changed: true,
            },
          ],
        },
      ],
    };

    render(
      <TableDiff
        diff={diffWithNullValues}
        onDecisionChange={mockOnDecisionChange}
        decisions={mockDecisions}
      />
    );

    expect(screen.getByText('NULL')).toBeInTheDocument();
  });
});

describe('RestoreWizard', () => {
  const mockOnClose = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders select step initially', () => {
    render(<RestoreWizard onClose={mockOnClose} />);
    
    expect(screen.getByText('Select Snapshot')).toBeInTheDocument();
    expect(screen.getByText('Available Snapshots')).toBeInTheDocument();
  });

  it('shows loading state', () => {
    render(<RestoreWizard onClose={mockOnClose} />);
    
    expect(screen.getByText('Loading...')).toBeInTheDocument();
  });

  it('calls onClose when close button is clicked', () => {
    render(<RestoreWizard onClose={mockOnClose} />);
    
    const closeButton = screen.getByRole('button', { name: /close/i });
    fireEvent.click(closeButton);
    
    expect(mockOnClose).toHaveBeenCalled();
  });

  it('shows error message when error occurs', async () => {
    const { recoveryClient } = require('../../lib/recoveryClient');
    recoveryClient.getStatus.mockRejectedValue(new Error('Network error'));

    render(<RestoreWizard onClose={mockOnClose} />);
    
    await waitFor(() => {
      expect(screen.getByText('Failed to load recovery status')).toBeInTheDocument();
    });
  });

  it('shows snapshots in select step', async () => {
    const { recoveryClient } = require('../../lib/recoveryClient');
    recoveryClient.getStatus.mockResolvedValue(mockRecoveryStatus);

    render(<RestoreWizard onClose={mockOnClose} />);
    
    await waitFor(() => {
      expect(screen.getByText('2025-08-14T10-00-00Z')).toBeInTheDocument();
      expect(screen.getByText('Valid')).toBeInTheDocument();
    });
  });

  it('disables invalid snapshots', async () => {
    const statusWithInvalidSnapshot = {
      ...mockRecoveryStatus,
      snapshots: [
        { ...mockRecoveryStatus.snapshots[0], manifest_ok: false },
      ],
    };

    const { recoveryClient } = require('../../lib/recoveryClient');
    recoveryClient.getStatus.mockResolvedValue(statusWithInvalidSnapshot);

    render(<RestoreWizard onClose={mockOnClose} />);
    
    await waitFor(() => {
      expect(screen.getByText('Invalid')).toBeInTheDocument();
    });
  });

  it('shows preview step after snapshot selection', async () => {
    const { recoveryClient } = require('../../lib/recoveryClient');
    recoveryClient.getStatus.mockResolvedValue(mockRecoveryStatus);
    recoveryClient.previewRestore.mockResolvedValue({
      snapshot: mockRecoveryStatus.snapshots[0],
      tables: [mockTableDiff],
      summary: { rows_add: 2, rows_remove: 1, rows_change: 3 },
    });

    render(<RestoreWizard onClose={mockOnClose} />);
    
    await waitFor(() => {
      const snapshotCard = screen.getByText('2025-08-14T10-00-00Z');
      fireEvent.click(snapshotCard);
    });

    await waitFor(() => {
      expect(screen.getByText('Preview Changes')).toBeInTheDocument();
      expect(screen.getByText('Rows to Add')).toBeInTheDocument();
      expect(screen.getByText('Rows to Remove')).toBeInTheDocument();
      expect(screen.getByText('Rows to Change')).toBeInTheDocument();
    });
  });

  it('shows resolve step after table selection', async () => {
    const { recoveryClient } = require('../../lib/recoveryClient');
    recoveryClient.getStatus.mockResolvedValue(mockRecoveryStatus);
    recoveryClient.previewRestore.mockResolvedValue({
      snapshot: mockRecoveryStatus.snapshots[0],
      tables: [mockTableDiff],
      summary: { rows_add: 2, rows_remove: 1, rows_change: 3 },
    });
    recoveryClient.getTableDiff.mockResolvedValue(mockTableDiff);

    render(<RestoreWizard onClose={mockOnClose} />);
    
    // Select snapshot
    await waitFor(() => {
      const snapshotCard = screen.getByText('2025-08-14T10-00-00Z');
      fireEvent.click(snapshotCard);
    });

    // Select table
    await waitFor(() => {
      const tableCard = screen.getByText('invoices');
      fireEvent.click(tableCard);
    });

    await waitFor(() => {
      expect(screen.getByText('Resolve Conflicts')).toBeInTheDocument();
      expect(screen.getByText('Table: invoices')).toBeInTheDocument();
    });
  });

  it('shows commit step after successful restore', async () => {
    const { recoveryClient } = require('../../lib/recoveryClient');
    recoveryClient.getStatus.mockResolvedValue(mockRecoveryStatus);
    recoveryClient.previewRestore.mockResolvedValue({
      snapshot: mockRecoveryStatus.snapshots[0],
      tables: [mockTableDiff],
      summary: { rows_add: 2, rows_remove: 1, rows_change: 3 },
    });
    recoveryClient.getTableDiff.mockResolvedValue(mockTableDiff);
    recoveryClient.commitRestore.mockResolvedValue({ ok: true, restore_id: 'test-123' });

    render(<RestoreWizard onClose={mockOnClose} />);
    
    // Navigate through steps
    await waitFor(() => {
      const snapshotCard = screen.getByText('2025-08-14T10-00-00Z');
      fireEvent.click(snapshotCard);
    });

    await waitFor(() => {
      const tableCard = screen.getByText('invoices');
      fireEvent.click(tableCard);
    });

    await waitFor(() => {
      const commitButton = screen.getByText('Commit Restore');
      fireEvent.click(commitButton);
    });

    await waitFor(() => {
      expect(screen.getByText('Restore Completed Successfully')).toBeInTheDocument();
    });
  });
});

describe('Recovery UI Integration', () => {
  it('handles keyboard navigation in table diff', () => {
    const mockOnDecisionChange = jest.fn();
    const mockDecisions = { 'id=INV-001': 'keep_live' };

    render(
      <TableDiff
        diff={mockTableDiff}
        onDecisionChange={mockOnDecisionChange}
        decisions={mockDecisions}
      />
    );

    const select = screen.getByDisplayValue('Keep Live');
    select.focus();
    
    expect(select).toHaveFocus();
  });

  it('shows correct step titles in wizard', () => {
    render(<RestoreWizard onClose={jest.fn()} />);
    
    // Initially shows select step
    expect(screen.getByText('Select Snapshot')).toBeInTheDocument();
  });

  it('disables restore button when no snapshots available', async () => {
    const { recoveryClient } = require('../../lib/recoveryClient');
    recoveryClient.getStatus.mockResolvedValue({
      ...mockRecoveryStatus,
      snapshots: [],
    });

    render(<RestoreWizard onClose={jest.fn()} />);
    
    await waitFor(() => {
      expect(screen.getByText('No snapshots available')).toBeInTheDocument();
    });
  });

  it('handles network errors gracefully', async () => {
    const { recoveryClient } = require('../../lib/recoveryClient');
    recoveryClient.getStatus.mockRejectedValue(new Error('Network error'));

    render(<RestoreWizard onClose={jest.fn()} />);
    
    await waitFor(() => {
      expect(screen.getByText('Failed to load recovery status')).toBeInTheDocument();
    });
  });

  it('shows loading states during API calls', async () => {
    const { recoveryClient } = require('../../lib/recoveryClient');
    recoveryClient.getStatus.mockImplementation(() => new Promise(resolve => setTimeout(() => resolve(mockRecoveryStatus), 100)));

    render(<RestoreWizard onClose={jest.fn()} />);
    
    expect(screen.getByText('Loading...')).toBeInTheDocument();
  });
}); 