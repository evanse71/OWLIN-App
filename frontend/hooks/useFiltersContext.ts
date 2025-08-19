import { useState, useEffect, useCallback, useMemo } from 'react';
import { useSearchParams } from 'next/navigation';
import { useRouter } from 'next/router';
import { InvoiceFilter, UserRole } from './useInvoices';

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

// Convert filter state to URL search parameters
const stateToSearchParams = (filters: InvoiceFilter): Record<string, string> => {
  const params: Record<string, string> = {};
  
  if (filters.venue_id) params.venue_id = filters.venue_id;
  if (filters.supplier_name) params.supplier_name = filters.supplier_name;
  if (filters.date_start) params.date_start = filters.date_start;
  if (filters.date_end) params.date_end = filters.date_end;
  if (filters.status?.length) params.status = filters.status.join(',');
  if (filters.search_text) params.search_text = filters.search_text;
  if (filters.only_flagged) params.only_flagged = 'true';
  if (filters.only_unmatched) params.only_unmatched = 'true';
  if (filters.only_with_credit) params.only_with_credit = 'true';
  if (!filters.include_utilities) params.include_utilities = 'false';
  
  return params;
};

// Convert URL search parameters to filter state
const searchParamsToPartialState = (searchParams: URLSearchParams): Partial<InvoiceFilter> => {
  const state: Partial<InvoiceFilter> = {};
  
  const venue_id = searchParams.get('venue_id');
  if (venue_id) state.venue_id = venue_id;
  
  const supplier_name = searchParams.get('supplier_name');
  if (supplier_name) state.supplier_name = supplier_name;
  
  const date_start = searchParams.get('date_start');
  if (date_start) state.date_start = date_start;
  
  const date_end = searchParams.get('date_end');
  if (date_end) state.date_end = date_end;
  
  const status = searchParams.get('status');
  if (status) state.status = status.split(',');
  
  const search_text = searchParams.get('search_text');
  if (search_text) state.search_text = search_text;
  
  const only_flagged = searchParams.get('only_flagged');
  if (only_flagged) state.only_flagged = only_flagged === 'true';
  
  const only_unmatched = searchParams.get('only_unmatched');
  if (only_unmatched) state.only_unmatched = only_unmatched === 'true';
  
  const only_with_credit = searchParams.get('only_with_credit');
  if (only_with_credit) state.only_with_credit = only_with_credit === 'true';
  
  const include_utilities = searchParams.get('include_utilities');
  if (include_utilities) state.include_utilities = include_utilities === 'true';
  
  return state;
};

export const useFiltersContext = (role: UserRole = 'viewer') => {
  const router = useRouter();
  const searchParams = useSearchParams();
  
  // Initialize filters from URL params, localStorage, or role defaults
  const [filters, setFilters] = useState<InvoiceFilter>(() => {
    // First, try to get from URL params
    const urlState = searchParamsToPartialState(new URLSearchParams(router.asPath.split('?')[1] || ''));
    
    // Then, try to get from localStorage
    let localStorageState: Partial<InvoiceFilter> = {};
    if (typeof window !== 'undefined') {
      try {
        const stored = localStorage.getItem(STORAGE_KEY);
        if (stored) {
          localStorageState = JSON.parse(stored);
        }
      } catch (error) {
        console.warn('Failed to parse localStorage filters:', error);
      }
    }
    
    // Merge with role defaults
    const defaults = getRoleDefaults(role);
    return {
      ...defaults,
      ...localStorageState,
      ...urlState,
    };
  });

  // Update URL when filters change
  const updateURL = useCallback((newFilters: InvoiceFilter) => {
    const params = stateToSearchParams(newFilters);
    const query = new URLSearchParams();
    
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== null && value !== '') {
        query.set(key, value);
      }
    });
    
    const newQuery = query.toString();
    const newPath = newQuery ? `${router.pathname}?${newQuery}` : router.pathname;
    
    router.replace(newPath, undefined, { shallow: true });
  }, [router]);

  // Update localStorage when filters change
  const updateLocalStorage = useCallback((newFilters: InvoiceFilter) => {
    if (typeof window !== 'undefined') {
      try {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(newFilters));
      } catch (error) {
        console.warn('Failed to save filters to localStorage:', error);
      }
    }
  }, []);

  // Update individual filter
  const updateFilter = useCallback((key: keyof InvoiceFilter, value: any) => {
    setFilters(prev => {
      const newFilters = {
        ...prev,
        [key]: value,
      };
      
      // Update URL and localStorage
      updateURL(newFilters);
      updateLocalStorage(newFilters);
      
      return newFilters;
    });
  }, [updateURL, updateLocalStorage]);

  // Toggle boolean filters
  const toggleFilter = useCallback((key: keyof InvoiceFilter) => {
    setFilters(prev => {
      const newFilters = {
        ...prev,
        [key]: !prev[key],
      };
      
      // Update URL and localStorage
      updateURL(newFilters);
      updateLocalStorage(newFilters);
      
      return newFilters;
    });
  }, [updateURL, updateLocalStorage]);

  // Reset filters to role defaults
  const resetFilters = useCallback(() => {
    const defaults = getRoleDefaults(role);
    setFilters(defaults);
    
    // Clear URL params and localStorage
    router.replace(router.pathname, undefined, { shallow: true });
    if (typeof window !== 'undefined') {
      localStorage.removeItem(STORAGE_KEY);
    }
  }, [role, router]);

  // Check if any filters are active
  const hasActiveFilters = useMemo(() => {
    return !!(
      filters.venue_id ||
      filters.supplier_name ||
      filters.date_start ||
      filters.date_end ||
      filters.search_text ||
      filters.only_flagged ||
      filters.only_unmatched ||
      filters.only_with_credit ||
      !filters.include_utilities
    );
  }, [filters]);

  // Sync with URL changes
  useEffect(() => {
    const urlState = searchParamsToPartialState(new URLSearchParams(router.asPath.split('?')[1] || ''));
    setFilters(prev => ({
      ...prev,
      ...urlState,
    }));
  }, [router.asPath]);

  return {
    filters,
    updateFilter,
    toggleFilter,
    resetFilters,
    hasActiveFilters,
  };
}; 