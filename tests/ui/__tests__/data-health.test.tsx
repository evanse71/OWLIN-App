import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import DataHealthPage from '@/pages/settings/data-health';

// Mock fetch
global.fetch = jest.fn();

describe('DataHealthPage', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders tabs correctly', () => {
    render(<DataHealthPage />);
    
    expect(screen.getByText('Backups')).toBeInTheDocument();
    expect(screen.getByText('Support Packs')).toBeInTheDocument();
  });

  it('switches between tabs', () => {
    render(<DataHealthPage />);
    
    // Initially on backups tab
    expect(screen.getByText('Create Backup')).toBeInTheDocument();
    
    // Switch to support packs tab
    fireEvent.click(screen.getByText('Support Packs'));
    expect(screen.getByText('Generate Support Pack')).toBeInTheDocument();
  });

  it('shows success banner', async () => {
    render(<DataHealthPage />);
    
    // Mock successful backup creation
    (fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        id: 'test-backup-123',
        size_bytes: 1024000
      })
    });
    
    // Mock successful backup list
    (fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => []
    });
    
    // Click create backup
    fireEvent.click(screen.getByText('Create Backup'));
    
    await waitFor(() => {
      expect(screen.getByText(/Backup created successfully/)).toBeInTheDocument();
    });
  });

  it('shows error banner', async () => {
    render(<DataHealthPage />);
    
    // Mock failed backup creation
    (fetch as jest.Mock).mockResolvedValueOnce({
      ok: false,
      json: async () => ({
        detail: 'Disk space error'
      })
    });
    
    // Click create backup
    fireEvent.click(screen.getByText('Create Backup'));
    
    await waitFor(() => {
      expect(screen.getByText(/Backup creation failed/)).toBeInTheDocument();
    });
  });

  it('renders empty state for backups', async () => {
    // Mock empty backup list
    (fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => []
    });
    
    render(<DataHealthPage />);
    
    await waitFor(() => {
      expect(screen.getByText('No backups yet. Create one to get started.')).toBeInTheDocument();
    });
  });

  it('renders empty state for support packs', async () => {
    // Mock empty support pack list
    (fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => []
    });
    
    render(<DataHealthPage />);
    
    // Switch to support packs tab
    fireEvent.click(screen.getByText('Support Packs'));
    
    await waitFor(() => {
      expect(screen.getByText('No support packs yet. Generate one to get started.')).toBeInTheDocument();
    });
  });

  it('creates support pack with notes', async () => {
    // Mock successful support pack creation
    (fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        id: 'test-pack-123',
        size_bytes: 2048000
      })
    });
    
    // Mock empty support pack list
    (fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => []
    });
    
    render(<DataHealthPage />);
    
    // Switch to support packs tab
    fireEvent.click(screen.getByText('Support Packs'));
    
    // Enter notes
    const notesTextarea = screen.getByPlaceholderText(/post-incident analysis/);
    fireEvent.change(notesTextarea, { target: { value: 'Test notes' } });
    
    // Click generate
    fireEvent.click(screen.getByText('Generate Support Pack'));
    
    await waitFor(() => {
      expect(fetch).toHaveBeenCalledWith('/api/support-packs', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ notes: 'Test notes' }),
      });
    });
  });

  it('handles network errors gracefully', async () => {
    // Mock network error
    (fetch as jest.Mock).mockRejectedValueOnce(new Error('Network error'));
    
    render(<DataHealthPage />);
    
    // Click create backup
    fireEvent.click(screen.getByText('Create Backup'));
    
    await waitFor(() => {
      expect(screen.getByText('Failed to create backup')).toBeInTheDocument();
    });
  });
});
