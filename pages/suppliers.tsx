import React, { useState, useEffect } from 'react';
import AppShell from '@/components/layout/AppShell';

interface Supplier {
  name: string;
  total_invoices: number;
  total_value: number;
  avg_invoice_value: number;
  first_invoice: string;
  last_invoice: string;
}

interface SupplierAnalytics {
  supplier: string;
  total_invoices: number;
  total_value: number;
  total_line_items: number;
  flagged_items: number;
  mismatch_rate: number;
  avg_item_price: number;
  price_volatility: number;
  unique_items: number;
}

interface SuppliersOverview {
  total_suppliers: number;
  total_value: number;
  avg_supplier_value: number;
  total_invoices: number;
  matched_invoices: number;
  discrepancy_invoices: number;
  success_rate: number;
}

const SuppliersPage: React.FC = () => {
  const [suppliers, setSuppliers] = useState<Supplier[]>([]);
  const [analytics, setAnalytics] = useState<SupplierAnalytics[]>([]);
  const [overview, setOverview] = useState<SuppliersOverview | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedSupplier, setSelectedSupplier] = useState<string | null>(null);

  useEffect(() => {
    fetchSuppliers();
    fetchAnalytics();
    fetchOverview();
  }, []);

  const fetchSuppliers = async () => {
    try {
      const response = await fetch('/api/suppliers/', { cache: 'no-store' });
      if (!response.ok) {
        throw new Error('Failed to fetch suppliers');
      }
      const data = await response.json();
      setSuppliers(data.suppliers);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
    } finally {
      setLoading(false);
    }
  };

  const fetchAnalytics = async () => {
    try {
      const response = await fetch('/api/suppliers/analytics', { cache: 'no-store' });
      if (!response.ok) {
        throw new Error('Failed to fetch analytics');
      }
      const data = await response.json();
      setAnalytics(data.analytics);
    } catch (err) {
      console.error('Error fetching analytics:', err);
    }
  };

  const fetchOverview = async () => {
    try {
      const response = await fetch('/api/suppliers/summary/overview', { cache: 'no-store' });
      if (!response.ok) {
        throw new Error('Failed to fetch overview');
      }
      const data = await response.json();
      setOverview(data);
    } catch (err) {
      console.error('Error fetching overview:', err);
    }
  };

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-GB', {
      style: 'currency',
      currency: 'GBP'
    }).format(amount);
  };

  const formatDate = (dateString: string) => {
    if (!dateString) return 'N/A';
    return new Date(dateString).toLocaleDateString('en-GB');
  };

  const getMismatchRateColor = (rate: number) => {
    if (rate <= 5) return 'text-green-700';
    if (rate <= 15) return 'text-yellow-700';
    return 'text-red-700';
  };

  if (loading) {
    return (
      <AppShell>
        <div className="py-8">
          <div className="flex items-center justify-center h-64">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-owlin-cerulean"></div>
          </div>
        </div>
      </AppShell>
    );
  }

  if (error) {
    return (
      <AppShell>
        <div className="py-8">
          <div className="bg-owlin-card border border-owlin-stroke rounded-owlin p-4">
            <p className="text-red-700">Error loading suppliers: {error}</p>
            <button 
              onClick={() => {
                setError(null);
                fetchSuppliers();
                fetchAnalytics();
                fetchOverview();
              }}
              className="mt-2 px-4 py-2 bg-[var(--owlin-sapphire)] text-white rounded-owlin hover:brightness-110"
            >
              Retry
            </button>
          </div>
        </div>
      </AppShell>
    );
  }

  return (
    <AppShell>
      <div className="py-8">
        <div className="max-w-7xl mx-auto">
          {/* Header */}
          <div className="mb-8">
            <h1 className="text-3xl font-semibold text-owlin-text mb-2">Supplier Analytics</h1>
            <p className="text-owlin-muted">Monitor supplier performance and identify areas for improvement</p>
          </div>

          {/* Overview Stats */}
          {overview && (
            <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
              <div className="bg-owlin-card rounded-owlin shadow-owlin p-6 border border-owlin-stroke">
                <div className="flex items-center">
                  <div className="p-3 rounded-owlin bg-[color-mix(in_oklab,var(--owlin-sapphire)_12%,transparent)]">
                    <svg className="w-8 h-8 text-owlin-cerulean" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
                    </svg>
                  </div>
                  <div className="ml-4">
                    <p className="text-sm font-medium text-owlin-muted">Total Suppliers</p>
                    <p className="text-2xl font-semibold text-owlin-text">{overview.total_suppliers}</p>
                  </div>
                </div>
              </div>

              <div className="bg-owlin-card rounded-owlin shadow-owlin p-6 border border-owlin-stroke">
                <div className="flex items-center">
                  <div className="p-3 rounded-owlin bg-[color-mix(in_oklab,var(--owlin-sapphire)_12%,transparent)]">
                    <svg className="w-8 h-8 text-owlin-cerulean" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1" />
                    </svg>
                  </div>
                  <div className="ml-4">
                    <p className="text-sm font-medium text-owlin-muted">Total Value</p>
                    <p className="text-2xl font-semibold text-owlin-text">{formatCurrency(overview.total_value)}</p>
                  </div>
                </div>
              </div>

              <div className="bg-owlin-card rounded-owlin shadow-owlin p-6 border border-owlin-stroke">
                <div className="flex items-center">
                  <div className="p-3 rounded-owlin bg-[color-mix(in_oklab,var(--owlin-sapphire)_12%,transparent)]">
                    <svg className="w-8 h-8 text-owlin-cerulean" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2z" />
                    </svg>
                  </div>
                  <div className="ml-4">
                    <p className="text-sm font-medium text-owlin-muted">Success Rate</p>
                    <p className="text-2xl font-semibold text-owlin-text">{overview.success_rate}%</p>
                  </div>
                </div>
              </div>

              <div className="bg-owlin-card rounded-owlin shadow-owlin p-6 border border-owlin-stroke">
                <div className="flex items-center">
                  <div className="p-3 rounded-owlin bg-[color-mix(in_oklab,var(--owlin-sapphire)_12%,transparent)]">
                    <svg className="w-8 h-8 text-owlin-cerulean" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.732 16.5c-.77.833.192 2.5 1.732 2.5z" />
                    </svg>
                  </div>
                  <div className="ml-4">
                    <p className="text-sm font-medium text-owlin-muted">Discrepancies</p>
                    <p className="text-2xl font-semibold text-owlin-text">{overview.discrepancy_invoices}</p>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Supplier Analytics Table */}
          <div className="bg-owlin-card rounded-owlin shadow-owlin mb-8 border border-owlin-stroke">
            <div className="px-6 py-4 border-b border-owlin-stroke">
              <h3 className="text-lg font-semibold text-owlin-text">Supplier Performance Analytics</h3>
            </div>
            
            {analytics.length === 0 ? (
              <div className="p-8 text-center">
                <div className="text-owlin-muted mb-4">
                  <svg className="mx-auto h-12 w-12" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2z" />
                  </svg>
                </div>
                <h3 className="text-lg font-medium text-owlin-text mb-2">No supplier data</h3>
                <p className="text-owlin-muted">Start processing invoices to see supplier analytics.</p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="min-w-full">
                  <thead className="sticky top-0 z-[1] bg-owlin-card border-b border-owlin-stroke">
                    <tr>
                      <th className="px-6 py-3 text-left text-xs font-medium text-owlin-muted uppercase tracking-wider">Supplier</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-owlin-muted uppercase tracking-wider">Invoices</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-owlin-muted uppercase tracking-wider">Total Value</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-owlin-muted uppercase tracking-wider">Mismatch Rate</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-owlin-muted uppercase tracking-wider">Avg Item Price</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-owlin-muted uppercase tracking-wider">Unique Items</th>
                    </tr>
                  </thead>
                  <tbody className="bg-owlin-card divide-y divide-owlin-stroke">
                    {analytics.map((supplier, index) => (
                      <tr key={index} className="hover:bg-[color-mix(in_oklab,var(--owlin-bg)_92%,transparent)] cursor-pointer" onClick={() => setSelectedSupplier(supplier.supplier)}>
                        <td className="px-6 py-3 whitespace-nowrap"><div className="text-sm font-medium text-owlin-text">{supplier.supplier}</div></td>
                        <td className="px-6 py-3 whitespace-nowrap text-sm text-owlin-muted">{supplier.total_invoices}</td>
                        <td className="px-6 py-3 whitespace-nowrap text-sm text-owlin-muted">{formatCurrency(supplier.total_value)}</td>
                        <td className="px-6 py-3 whitespace-nowrap"><span className={`text-sm font-medium ${getMismatchRateColor(supplier.mismatch_rate)}`}>{supplier.mismatch_rate}%</span></td>
                        <td className="px-6 py-3 whitespace-nowrap text-sm text-owlin-muted">{formatCurrency(supplier.avg_item_price)}</td>
                        <td className="px-6 py-3 whitespace-nowrap text-sm text-owlin-muted">{supplier.unique_items}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          {/* Top Suppliers by Value */}
          <div className="bg-owlin-card rounded-owlin shadow-owlin border border-owlin-stroke">
            <div className="px-6 py-4 border-b border-owlin-stroke">
              <h3 className="text-lg font-semibold text-owlin-text">Top Suppliers by Value</h3>
            </div>
            
            {suppliers.length === 0 ? (
              <div className="p-8 text-center">
                <div className="text-owlin-muted mb-4">
                  <svg className="mx-auto h-12 w-12" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
                  </svg>
                </div>
                <h3 className="text-lg font-medium text-owlin-text mb-2">No suppliers found</h3>
                <p className="text-owlin-muted">Start processing invoices to see supplier data.</p>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 p-6">
                {suppliers.slice(0, 6).map((supplier, index) => (
                  <div key={index} className="bg-[color-mix(in_oklab,var(--owlin-bg)_92%,transparent)] rounded-owlin p-4 border border-owlin-stroke">
                    <div className="flex items-center justify-between mb-3">
                      <h4 className="text-lg font-semibold text-owlin-text truncate">{supplier.name}</h4>
                      <span className="text-sm text-owlin-muted">#{index + 1}</span>
                    </div>
                    
                    <div className="space-y-2 text-sm">
                      <div className="flex justify-between"><span className="text-owlin-muted">Total Value:</span><span className="font-medium text-owlin-text">{formatCurrency(supplier.total_value)}</span></div>
                      <div className="flex justify-between"><span className="text-owlin-muted">Invoices:</span><span className="font-medium text-owlin-text">{supplier.total_invoices}</span></div>
                      <div className="flex justify-between"><span className="text-owlin-muted">Avg Invoice:</span><span className="font-medium text-owlin-text">{formatCurrency(supplier.avg_invoice_value)}</span></div>
                      <div className="flex justify-between"><span className="text-owlin-muted">Last Invoice:</span><span className="font-medium text-owlin-text">{formatDate(supplier.last_invoice)}</span></div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </AppShell>
  );
};

export default SuppliersPage; 