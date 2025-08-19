import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import InvoiceFilterPanel from '../components/invoices/InvoiceFilterPanel';

// Mock the useInvoices hook
jest.mock('../hooks/useInvoices', () => ({
  useInvoices: () => ({
    filters: {
      venue_id: undefined,
      supplier_name: undefined,
      date_start: undefined,
      date_end: undefined,
      status: undefined,
      search_text: undefined,
      only_flagged: false,
      only_unmatched: false,
      only_with_credit: false,
      include_utilities: true,
    },
    updateFilter: jest.fn(),
    toggleFilter: jest.fn(),
    resetFilters: jest.fn(),
    loading: false,
    totalCount: 0,
  }),
}));

describe('InvoiceFilterPanel', () => {
  it('renders filter panel with all components', () => {
    render(<InvoiceFilterPanel role="viewer" />);
    
    // Check for main elements
    expect(screen.getByText('Filters')).toBeInTheDocument();
    expect(screen.getByPlaceholderText('Search invoices...')).toBeInTheDocument();
    expect(screen.getByText('Venue')).toBeInTheDocument();
    expect(screen.getByText('Supplier')).toBeInTheDocument();
    expect(screen.getByText('Date Range')).toBeInTheDocument();
    expect(screen.getByText('Quick Filters')).toBeInTheDocument();
    expect(screen.getByText('Sort by')).toBeInTheDocument();
  });

  it('shows reset button when filters are active', () => {
    const mockUseInvoices = require('../hooks/useInvoices').useInvoices;
    mockUseInvoices.mockReturnValue({
      filters: {
        only_flagged: true,
        search_text: 'test',
      },
      updateFilter: jest.fn(),
      toggleFilter: jest.fn(),
      resetFilters: jest.fn(),
      loading: false,
      totalCount: 0,
    });

    render(<InvoiceFilterPanel role="viewer" />);
    expect(screen.getByText('Reset')).toBeInTheDocument();
  });

  it('handles search input changes', async () => {
    const mockUpdateFilter = jest.fn();
    const mockUseInvoices = require('../hooks/useInvoices').useInvoices;
    mockUseInvoices.mockReturnValue({
      filters: {
        search_text: '',
      },
      updateFilter: mockUpdateFilter,
      toggleFilter: jest.fn(),
      resetFilters: jest.fn(),
      loading: false,
      totalCount: 0,
    });

    render(<InvoiceFilterPanel role="viewer" />);
    
    const searchInput = screen.getByPlaceholderText('Search invoices...');
    fireEvent.change(searchInput, { target: { value: 'test search' } });

    await waitFor(() => {
      expect(mockUpdateFilter).toHaveBeenCalledWith('search_text', 'test search');
    }, { timeout: 400 });
  });

  it('handles filter toggles', () => {
    const mockToggleFilter = jest.fn();
    const mockUseInvoices = require('../hooks/useInvoices').useInvoices;
    mockUseInvoices.mockReturnValue({
      filters: {
        only_flagged: false,
        only_unmatched: false,
        only_with_credit: false,
        include_utilities: true,
      },
      updateFilter: jest.fn(),
      toggleFilter: mockToggleFilter,
      resetFilters: jest.fn(),
      loading: false,
      totalCount: 0,
    });

    render(<InvoiceFilterPanel role="viewer" />);
    
    const flaggedButton = screen.getByText('Only flagged');
    fireEvent.click(flaggedButton);
    
    expect(mockToggleFilter).toHaveBeenCalledWith('only_flagged');
  });
}); 