import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import FlaggedIssuesTable from '@/components/issues/FlaggedIssuesTable';
import BulkActionBar from '@/components/issues/BulkActionBar';
import EscalateDialog from '@/components/issues/EscalateDialog';
import AssignDialog from '@/components/issues/AssignDialog';
import CommentDialog from '@/components/issues/CommentDialog';

// Mock the offline queue
jest.mock('@/lib/offlineQueue', () => ({
  offlineQueue: {
    addToQueue: jest.fn().mockResolvedValue('test-id'),
    getQueueLength: jest.fn().mockReturnValue(0),
    isOnlineStatus: jest.fn().mockReturnValue(true),
  },
}));

const mockIssues = [
  {
    id: '1',
    item: 'Test Item 1',
    qty: 10,
    price: 5.0,
    flagged: true,
    source: 'invoice',
    upload_timestamp: '2024-01-01T00:00:00Z',
    invoice_number: 'INV-001',
    supplier: 'Test Supplier',
    invoice_date: '2024-01-01',
    venue: 'Test Venue',
    total_value: 50.0,
    severity: 'high',
  },
  {
    id: '2',
    item: 'Test Item 2',
    qty: 5,
    price: 10.0,
    flagged: true,
    source: 'invoice',
    upload_timestamp: '2024-01-01T00:00:00Z',
    invoice_number: 'INV-002',
    supplier: 'Test Supplier',
    invoice_date: '2024-01-01',
    venue: 'Test Venue',
    total_value: 50.0,
    severity: 'medium',
  },
];

describe('FlaggedIssuesTable', () => {
  const defaultProps = {
    issues: mockIssues,
    selectedIds: [],
    onSelectionChange: jest.fn(),
    onResolveIssue: jest.fn(),
    onEscalateIssue: jest.fn(),
    userRole: 'gm' as const,
    isLoading: false,
  };

  it('renders table with issues', () => {
    render(<FlaggedIssuesTable {...defaultProps} />);
    
    expect(screen.getByText('Test Item 1')).toBeInTheDocument();
    expect(screen.getByText('Test Item 2')).toBeInTheDocument();
    expect(screen.getByText('INV-001')).toBeInTheDocument();
    expect(screen.getByText('INV-002')).toBeInTheDocument();
  });

  it('handles select all checkbox', () => {
    render(<FlaggedIssuesTable {...defaultProps} />);
    
    const selectAllCheckbox = screen.getByRole('checkbox', { name: '' });
    fireEvent.click(selectAllCheckbox);
    
    expect(defaultProps.onSelectionChange).toHaveBeenCalledWith(['1', '2']);
  });

  it('handles individual issue selection', () => {
    render(<FlaggedIssuesTable {...defaultProps} />);
    
    const checkboxes = screen.getAllByRole('checkbox');
    const firstIssueCheckbox = checkboxes[1]; // Skip header checkbox
    
    fireEvent.click(firstIssueCheckbox);
    
    expect(defaultProps.onSelectionChange).toHaveBeenCalledWith(['1']);
  });

  it('shows resolve button for GM role', () => {
    render(<FlaggedIssuesTable {...defaultProps} />);
    
    const resolveButtons = screen.getAllByText('Resolve');
    expect(resolveButtons).toHaveLength(2);
  });

  it('hides resolve button for shift_lead role', () => {
    render(<FlaggedIssuesTable {...defaultProps} userRole="shift_lead" />);
    
    const resolveButtons = screen.queryAllByText('Resolve');
    expect(resolveButtons).toHaveLength(0);
  });
});

describe('BulkActionBar', () => {
  const defaultProps = {
    selectedCount: 2,
    userRole: 'gm' as const,
    onResolve: jest.fn(),
    onDismiss: jest.fn(),
    onEscalate: jest.fn(),
    onAssign: jest.fn(),
    onComment: jest.fn(),
    onClearSelection: jest.fn(),
    isLoading: false,
  };

  it('renders when items are selected', () => {
    render(<BulkActionBar {...defaultProps} />);
    
    expect(screen.getByText('2 selected')).toBeInTheDocument();
    expect(screen.getByText('Resolve')).toBeInTheDocument();
    expect(screen.getByText('Dismiss')).toBeInTheDocument();
    expect(screen.getByText('Escalate')).toBeInTheDocument();
    expect(screen.getByText('Assign')).toBeInTheDocument();
    expect(screen.getByText('Comment')).toBeInTheDocument();
  });

  it('does not render when no items selected', () => {
    render(<BulkActionBar {...defaultProps} selectedCount={0} />);
    
    expect(screen.queryByText('selected')).not.toBeInTheDocument();
  });

  it('handles resolve action', () => {
    render(<BulkActionBar {...defaultProps} />);
    
    fireEvent.click(screen.getByText('Resolve'));
    expect(defaultProps.onResolve).toHaveBeenCalled();
  });

  it('handles clear selection', () => {
    render(<BulkActionBar {...defaultProps} />);
    
    const clearButton = screen.getByTitle('Clear selection');
    fireEvent.click(clearButton);
    
    expect(defaultProps.onClearSelection).toHaveBeenCalled();
  });

  it('disables actions for insufficient permissions', () => {
    render(<BulkActionBar {...defaultProps} userRole="shift_lead" />);
    
    const resolveButton = screen.getByText('Resolve');
    const escalateButton = screen.getByText('Escalate');
    const assignButton = screen.getByText('Assign');
    
    expect(resolveButton).toBeDisabled();
    expect(escalateButton).toBeDisabled();
    expect(assignButton).toBeDisabled();
  });
});

describe('EscalateDialog', () => {
  const defaultProps = {
    isOpen: true,
    onClose: jest.fn(),
    onConfirm: jest.fn(),
    selectedCount: 2,
    isLoading: false,
  };

  it('renders dialog when open', () => {
    render(<EscalateDialog {...defaultProps} />);
    
    expect(screen.getByText('Escalate 2 Issues')).toBeInTheDocument();
    expect(screen.getByText('General Manager')).toBeInTheDocument();
    expect(screen.getByText('Finance')).toBeInTheDocument();
  });

  it('handles role selection', () => {
    render(<EscalateDialog {...defaultProps} />);
    
    const gmRadio = screen.getByLabelText('General Manager');
    fireEvent.click(gmRadio);
    
    expect(gmRadio).toBeChecked();
  });

  it('handles reason input', () => {
    render(<EscalateDialog {...defaultProps} />);
    
    const reasonInput = screen.getByPlaceholderText('Brief explanation for escalation...');
    fireEvent.change(reasonInput, { target: { value: 'Test reason' } });
    
    expect(reasonInput).toHaveValue('Test reason');
  });

  it('disables confirm button when no role selected', () => {
    render(<EscalateDialog {...defaultProps} />);
    
    const confirmButton = screen.getByText('Escalate');
    expect(confirmButton).toBeDisabled();
  });

  it('enables confirm button when role selected', () => {
    render(<EscalateDialog {...defaultProps} />);
    
    const gmRadio = screen.getByLabelText('General Manager');
    fireEvent.click(gmRadio);
    
    const confirmButton = screen.getByText('Escalate');
    expect(confirmButton).not.toBeDisabled();
  });

  it('calls onConfirm with correct parameters', () => {
    render(<EscalateDialog {...defaultProps} />);
    
    const gmRadio = screen.getByLabelText('General Manager');
    const reasonInput = screen.getByPlaceholderText('Brief explanation for escalation...');
    const confirmButton = screen.getByText('Escalate');
    
    fireEvent.click(gmRadio);
    fireEvent.change(reasonInput, { target: { value: 'Test reason' } });
    fireEvent.click(confirmButton);
    
    expect(defaultProps.onConfirm).toHaveBeenCalledWith('gm', 'Test reason');
  });
});

describe('CommentDialog', () => {
  const defaultProps = {
    isOpen: true,
    onClose: jest.fn(),
    onConfirm: jest.fn(),
    selectedCount: 2,
    isLoading: false,
  };

  it('renders dialog when open', () => {
    render(<CommentDialog {...defaultProps} />);
    
    expect(screen.getByText('Comment on 2 Issues')).toBeInTheDocument();
    expect(screen.getByPlaceholderText('Add a comment to these issues...')).toBeInTheDocument();
  });

  it('handles comment input', () => {
    render(<CommentDialog {...defaultProps} />);
    
    const commentInput = screen.getByPlaceholderText('Add a comment to these issues...');
    fireEvent.change(commentInput, { target: { value: 'Test comment' } });
    
    expect(commentInput).toHaveValue('Test comment');
  });

  it('shows character count', () => {
    render(<CommentDialog {...defaultProps} />);
    
    const commentInput = screen.getByPlaceholderText('Add a comment to these issues...');
    fireEvent.change(commentInput, { target: { value: 'Test' } });
    
    expect(screen.getByText('4/4000 characters')).toBeInTheDocument();
  });

  it('disables confirm button when comment is empty', () => {
    render(<CommentDialog {...defaultProps} />);
    
    const confirmButton = screen.getByText('Add Comment');
    expect(confirmButton).toBeDisabled();
  });

  it('enables confirm button when comment is provided', () => {
    render(<CommentDialog {...defaultProps} />);
    
    const commentInput = screen.getByPlaceholderText('Add a comment to these issues...');
    const confirmButton = screen.getByText('Add Comment');
    
    fireEvent.change(commentInput, { target: { value: 'Test comment' } });
    
    expect(confirmButton).not.toBeDisabled();
  });

  it('calls onConfirm with comment text', () => {
    render(<CommentDialog {...defaultProps} />);
    
    const commentInput = screen.getByPlaceholderText('Add a comment to these issues...');
    const confirmButton = screen.getByText('Add Comment');
    
    fireEvent.change(commentInput, { target: { value: 'Test comment' } });
    fireEvent.click(confirmButton);
    
    expect(defaultProps.onConfirm).toHaveBeenCalledWith('Test comment');
  });
});

describe('AssignDialog', () => {
  const defaultProps = {
    isOpen: true,
    onClose: jest.fn(),
    onConfirm: jest.fn(),
    selectedCount: 2,
    isLoading: false,
  };

  beforeEach(() => {
    // Mock fetch for users API
    global.fetch = jest.fn(() =>
      Promise.resolve({
        ok: true,
        json: () => Promise.resolve({
          users: [
            { id: '1', name: 'User 1', email: 'user1@example.com', role: 'gm' },
            { id: '2', name: 'User 2', email: 'user2@example.com', role: 'finance' },
          ]
        })
      })
    ) as jest.Mock;
  });

  it('renders dialog when open', () => {
    render(<AssignDialog {...defaultProps} />);
    
    expect(screen.getByText('Assign 2 Issues')).toBeInTheDocument();
    expect(screen.getByPlaceholderText('Search by name or email...')).toBeInTheDocument();
  });

  it('loads users on open', async () => {
    render(<AssignDialog {...defaultProps} />);
    
    await waitFor(() => {
      expect(screen.getByText('User 1')).toBeInTheDocument();
      expect(screen.getByText('User 2')).toBeInTheDocument();
    });
  });

  it('handles user search', async () => {
    render(<AssignDialog {...defaultProps} />);
    
    await waitFor(() => {
      expect(screen.getByText('User 1')).toBeInTheDocument();
    });
    
    const searchInput = screen.getByPlaceholderText('Search by name or email...');
    fireEvent.change(searchInput, { target: { value: 'User 1' } });
    
    expect(screen.getByText('User 1')).toBeInTheDocument();
    expect(screen.queryByText('User 2')).not.toBeInTheDocument();
  });

  it('handles user selection', async () => {
    render(<AssignDialog {...defaultProps} />);
    
    await waitFor(() => {
      expect(screen.getByText('User 1')).toBeInTheDocument();
    });
    
    const user1 = screen.getByText('User 1');
    fireEvent.click(user1);
    
    const confirmButton = screen.getByText('Assign');
    expect(confirmButton).not.toBeDisabled();
  });

  it('calls onConfirm with selected user ID', async () => {
    render(<AssignDialog {...defaultProps} />);
    
    await waitFor(() => {
      expect(screen.getByText('User 1')).toBeInTheDocument();
    });
    
    const user1 = screen.getByText('User 1');
    const confirmButton = screen.getByText('Assign');
    
    fireEvent.click(user1);
    fireEvent.click(confirmButton);
    
    expect(defaultProps.onConfirm).toHaveBeenCalledWith('1');
  });
}); 