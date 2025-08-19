import { useState, useEffect, useCallback, useMemo } from 'react';

export interface InvoiceListItem {
  id: number;
  supplier_name: string;
  invoice_number: string;
  invoice_date: string;
  total_amount: number;
  status: string;
  confidence: number;
  page_range?: string;
  parent_pdf_filename?: string;
  issues_count: number;
  upload_id: string;
  matched_delivery_note_id?: number;
}

export interface InvoiceFilter {
  venue_id?: string;
  supplier_name?: string;
  date_start?: string;
  date_end?: string;
  status?: string[];
  search_text?: string;
  only_flagged: boolean;
  only_unmatched: boolean;
  only_with_credit: boolean;
  include_utilities: boolean;
}

export interface InvoiceSort {
  sort_by: string;
  limit?: number;
  offset: number;
}

export interface InvoiceQueryResult {
  invoices: InvoiceListItem[];
  count: number;
  filters_applied: any;
  query_time_ms: number;
}

export type UserRole = 'finance' | 'GM' | 'shift_lead' | 'viewer';

const STORAGE_KEY = 'owlin_invoice_filters';

// Role-aware default filters
const getRoleDefaults = (role: UserRole): InvoiceFilter => {
  const endDate = new Date();
  const startDate = new Date();
  startDate.setDate(startDate.getDate() - 90); // Last 90 days

  const baseDefaults: InvoiceFilter = {
    only_flagged: false,
    only_unmatched: false,
    only_with_credit: false,
    include_utilities: true,
    date_start: startDate.toISOString().split('T')[0],
    date_end: endDate.toISOString().split('T')[0],
  };

  switch (role) {
    case 'finance':
      return {
        ...baseDefaults,
        only_flagged: true,
      };
    case 'GM':
      return {
        ...baseDefaults,
      };
    case 'shift_lead':
      return {
        ...baseDefaults,
        only_unmatched: true,
      };
    default:
      return baseDefaults;
  }
};

const getRoleDefaultSort = (role: UserRole): string => {
  switch (role) {
    case 'finance':
      return 'date_desc';
    case 'GM':
      return 'supplier_asc';
    case 'shift_lead':
      return 'date_desc';
    default:
      return 'date_desc';
  }
};

export const useInvoices = (role: UserRole = 'viewer') => {
  const [filters, setFilters] = useState<InvoiceFilter>(() => {
    // Load from localStorage or use role defaults
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored) {
      try {
        const parsed = JSON.parse(stored);
        return { ...getRoleDefaults(role), ...parsed };
      } catch {
        return getRoleDefaults(role);
      }
    }
    return getRoleDefaults(role);
  });

  const [sort, setSort] = useState<InvoiceSort>(() => ({
    sort_by: getRoleDefaultSort(role),
    offset: 0,
  }));

  const [invoices, setInvoices] = useState<InvoiceListItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [totalCount, setTotalCount] = useState(0);
  const [queryTime, setQueryTime] = useState(0);

  // Save filters to localStorage whenever they change
  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(filters));
  }, [filters]);

  // Build query parameters from filters and sort
  const queryParams = useMemo(() => {
    const params = new URLSearchParams();
    
    if (filters.venue_id) params.append('venue_id', filters.venue_id);
    if (filters.supplier_name) params.append('supplier_name', filters.supplier_name);
    if (filters.date_start) params.append('date_start', filters.date_start);
    if (filters.date_end) params.append('date_end', filters.date_end);
    if (filters.status?.length) {
      filters.status.forEach(s => params.append('status', s));
    }
    if (filters.search_text) params.append('search_text', filters.search_text);
    if (filters.only_flagged) params.append('only_flagged', 'true');
    if (filters.only_unmatched) params.append('only_unmatched', 'true');
    if (filters.only_with_credit) params.append('only_with_credit', 'true');
    if (!filters.include_utilities) params.append('include_utilities', 'false');
    
    params.append('sort_by', sort.sort_by);
    if (sort.limit) params.append('limit', sort.limit.toString());
    params.append('offset', sort.offset.toString());
    params.append('role', role);
    
    return params;
  }, [filters, sort, role]);

  // Fetch invoices
  const fetchInvoices = useCallback(async () => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await fetch(`/api/invoices?${queryParams.toString()}`);
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const data: InvoiceQueryResult = await response.json();
      setInvoices(data.invoices);
      setTotalCount(data.count);
      setQueryTime(data.query_time_ms);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch invoices');
      console.error('Error fetching invoices:', err);
    } finally {
      setLoading(false);
    }
  }, [queryParams]);

  // Fetch invoices when filters or sort change
  useEffect(() => {
    fetchInvoices();
  }, [fetchInvoices]);

  // Update individual filter
  const updateFilter = useCallback((key: keyof InvoiceFilter, value: any) => {
    setFilters(prev => ({
      ...prev,
      [key]: value,
    }));
  }, []);

  // Update sort
  const updateSort = useCallback((sort_by: string) => {
    setSort(prev => ({
      ...prev,
      sort_by,
      offset: 0, // Reset offset when sorting changes
    }));
  }, []);

  // Reset filters to role defaults
  const resetFilters = useCallback(() => {
    setFilters(getRoleDefaults(role));
    setSort({
      sort_by: getRoleDefaultSort(role),
      offset: 0,
    });
  }, [role]);

  // Toggle boolean filters
  const toggleFilter = useCallback((key: keyof InvoiceFilter) => {
    setFilters(prev => ({
      ...prev,
      [key]: !prev[key],
    }));
  }, []);

  // Load more (pagination)
  const loadMore = useCallback(() => {
    setSort(prev => ({
      ...prev,
      offset: prev.offset + (prev.limit || 50),
    }));
  }, []);

  return {
    // Data
    invoices,
    totalCount,
    queryTime,
    loading,
    error,
    
    // Filters and sort
    filters,
    sort,
    
    // Actions
    updateFilter,
    updateSort,
    resetFilters,
    toggleFilter,
    loadMore,
    refetch: fetchInvoices,
  };
}; 