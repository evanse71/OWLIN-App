import React, { useState, useEffect, useCallback } from 'react';
import { Search, Filter, X, Calendar, Building2, User, AlertTriangle, Link, CreditCard, Zap } from 'lucide-react';
import { useFilters } from '../../state/filters/FiltersContext';

interface InvoiceFilterPanelProps {
  className?: string;
}

const InvoiceFilterPanel: React.FC<InvoiceFilterPanelProps> = ({ 
  className = '' 
}) => {
  const { filters, setFilters, reset } = useFilters();
  const [searchValue, setSearchValue] = useState(filters.searchText || '');
  const [suppliers, setSuppliers] = useState<string[]>([]);
  const [venues, setVenues] = useState<Array<{id: string, name: string}>>([]);

  // Debounced search
  useEffect(() => {
    const timer = setTimeout(() => {
      setFilters({ searchText: searchValue || undefined });
    }, 300);

    return () => clearTimeout(timer);
  }, [searchValue, setFilters]);

  // Load suppliers and venues
  useEffect(() => {
    const loadSuppliers = async () => {
      try {
        const response = await fetch('/api/invoices/suppliers');
        if (response.ok) {
          const data = await response.json();
          setSuppliers(data.suppliers || []);
        }
      } catch (error) {
        console.error('Failed to load suppliers:', error);
      }
    };

    const loadVenues = async () => {
      try {
        const response = await fetch('/api/invoices/venues');
        if (response.ok) {
          const data = await response.json();
          setVenues(data.venues || []);
        }
      } catch (error) {
        console.error('Failed to load venues:', error);
      }
    };

    loadSuppliers();
    loadVenues();
  }, []);

  // Keyboard navigation handler
  const handleKeyDown = useCallback((e: React.KeyboardEvent, action: () => void) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      action();
    }
  }, []);

  const hasActiveFilters = filters.onlyFlagged || filters.onlyUnmatched || filters.onlyWithCredit || 
                          filters.supplierQuery || filters.searchText || filters.dateFrom || filters.dateTo;

  return (
    <div 
      className={`bg-white rounded-xl shadow-sm border border-gray-100 p-6 ${className}`}
      role="complementary"
      aria-label="Invoice filters and controls"
      data-ui="filter-panel"
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-2">
          <Filter className="w-5 h-5 text-gray-600" aria-hidden="true" />
          <h3 className="text-lg font-semibold text-gray-900">Filters</h3>
        </div>
        {hasActiveFilters && (
          <button
            onClick={reset}
            onKeyDown={(e) => handleKeyDown(e, reset)}
            className="text-sm text-gray-500 hover:text-gray-700 flex items-center gap-1 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 rounded"
            aria-label="Reset all filters to defaults"
            data-ui="reset-filters"
          >
            <X className="w-4 h-4" aria-hidden="true" />
            Reset
          </button>
        )}
      </div>

      {/* Search Bar */}
      <div className="mb-6">
        <label htmlFor="search-input" className="sr-only">Search invoices</label>
        <div className="relative">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" aria-hidden="true" />
          <input
            id="search-input"
            type="text"
            value={searchValue}
            onChange={(e) => setSearchValue(e.target.value)}
            placeholder="Search invoices..."
            className="w-full pl-10 pr-4 py-3 rounded-lg border border-gray-200 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            aria-describedby="search-description"
            data-ui="search-input"
          />
        </div>
        <div id="search-description" className="sr-only">
          Search through supplier names, invoice numbers, and dates
        </div>
      </div>

      {/* Venue Dropdown */}
      <div className="mb-6">
        <label htmlFor="venue-select" className="block text-sm font-medium text-gray-700 mb-2 flex items-center gap-2">
          <Building2 className="w-4 h-4" aria-hidden="true" />
          Venue
        </label>
        <select
          id="venue-select"
          value={filters.venueIds[0] || 'all'}
          onChange={(e) => setFilters({ venueIds: e.target.value === 'all' ? [] : [parseInt(e.target.value)] })}
          className="w-full px-3 py-2 rounded-lg border border-gray-200 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          aria-describedby="venue-description"
          data-ui="venue-select"
        >
          <option value="all">All Venues</option>
          {venues.map((venue) => (
            <option key={venue.id} value={venue.id}>
              {venue.name}
            </option>
          ))}
        </select>
        <div id="venue-description" className="sr-only">
          Filter invoices by venue location
        </div>
      </div>

      {/* Supplier Dropdown */}
      <div className="mb-6">
        <label htmlFor="supplier-select" className="block text-sm font-medium text-gray-700 mb-2 flex items-center gap-2">
          <User className="w-4 h-4" aria-hidden="true" />
          Supplier
        </label>
        <select
          id="supplier-select"
          value={filters.supplierQuery || ''}
          onChange={(e) => setFilters({ supplierQuery: e.target.value || undefined })}
          className="w-full px-3 py-2 rounded-lg border border-gray-200 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          aria-describedby="supplier-description"
        >
          <option value="">All Suppliers</option>
          {suppliers.map((supplier) => (
            <option key={supplier} value={supplier}>
              {supplier}
            </option>
          ))}
        </select>
        <div id="supplier-description" className="sr-only">
          Filter invoices by supplier name
        </div>
      </div>

      {/* Date Range */}
      <div className="mb-6">
        <label className="block text-sm font-medium text-gray-700 mb-2 flex items-center gap-2">
          <Calendar className="w-4 h-4" aria-hidden="true" />
          Date Range
        </label>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label htmlFor="date-from" className="sr-only">From date</label>
            <input
              id="date-from"
              type="date"
              value={filters.dateFrom || ''}
              onChange={(e) => setFilters({ dateFrom: e.target.value || undefined })}
              className="w-full px-3 py-2 rounded-lg border border-gray-200 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              aria-describedby="date-range-description"
            />
          </div>
          <div>
            <label htmlFor="date-to" className="sr-only">To date</label>
            <input
              id="date-to"
              type="date"
              value={filters.dateTo || ''}
              onChange={(e) => setFilters({ dateTo: e.target.value || undefined })}
              className="w-full px-3 py-2 rounded-lg border border-gray-200 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              aria-describedby="date-range-description"
            />
          </div>
        </div>
        <div id="date-range-description" className="sr-only">
          Filter invoices by date range
        </div>
      </div>

      {/* Filter Toggles */}
      <div className="mb-6">
        <label className="block text-sm font-medium text-gray-700 mb-3">Quick Filters</label>
        <div className="space-y-3" role="group" aria-label="Quick filter options">
          <button
            onClick={() => setFilters({ onlyFlagged: !filters.onlyFlagged })}
            onKeyDown={(e) => handleKeyDown(e, () => setFilters({ onlyFlagged: !filters.onlyFlagged }))}
            role="switch"
            aria-checked={filters.onlyFlagged}
            aria-label="Show only flagged invoices"
            className={`w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 ${
              filters.onlyFlagged
                ? 'bg-red-50 border border-red-200 text-red-700'
                : 'bg-gray-50 border border-gray-200 text-gray-700 hover:bg-gray-100'
            }`}
          >
            <AlertTriangle className={`w-4 h-4 ${filters.onlyFlagged ? 'text-red-500' : 'text-gray-400'}`} aria-hidden="true" />
            Only flagged
          </button>

          <button
            onClick={() => setFilters({ onlyUnmatched: !filters.onlyUnmatched })}
            onKeyDown={(e) => handleKeyDown(e, () => setFilters({ onlyUnmatched: !filters.onlyUnmatched }))}
            role="switch"
            aria-checked={filters.onlyUnmatched}
            aria-label="Show only unmatched invoices"
            className={`w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 ${
              filters.onlyUnmatched
                ? 'bg-orange-50 border border-orange-200 text-orange-700'
                : 'bg-gray-50 border border-gray-200 text-gray-700 hover:bg-gray-100'
            }`}
          >
            <Link className={`w-4 h-4 ${filters.onlyUnmatched ? 'text-orange-500' : 'text-gray-400'}`} aria-hidden="true" />
            Only unmatched
          </button>

          <button
            onClick={() => setFilters({ onlyWithCredit: !filters.onlyWithCredit })}
            onKeyDown={(e) => handleKeyDown(e, () => setFilters({ onlyWithCredit: !filters.onlyWithCredit }))}
            role="switch"
            aria-checked={filters.onlyWithCredit}
            aria-label="Show only invoices with credit"
            className={`w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 ${
              filters.onlyWithCredit
                ? 'bg-green-50 border border-green-200 text-green-700'
                : 'bg-gray-50 border border-gray-200 text-gray-700 hover:bg-gray-100'
            }`}
          >
            <CreditCard className={`w-4 h-4 ${filters.onlyWithCredit ? 'text-green-500' : 'text-gray-400'}`} aria-hidden="true" />
            Only with credit
          </button>
        </div>
      </div>

      {/* Sort Options */}
      <div className="mb-6">
        <label htmlFor="sort-select" className="block text-sm font-medium text-gray-700 mb-2">Sort By</label>
        <select
          id="sort-select"
          value={filters.sort}
          onChange={(e) => setFilters({ sort: e.target.value as any })}
          className="w-full px-3 py-2 rounded-lg border border-gray-200 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          data-ui="sort-select"
        >
          <option value="newest">Date (Newest first)</option>
          <option value="oldest">Date (Oldest first)</option>
          <option value="supplier_az">Supplier (A-Z)</option>
          <option value="value_desc">Amount (High to low)</option>
          <option value="value_asc">Amount (Low to high)</option>
        </select>
      </div>
    </div>
  );
};

export default InvoiceFilterPanel;