import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import AppShell from '@/components/layout/AppShell';
import { apiService } from '@/services/api';
import { on } from '@/lib/events';

interface DashboardData {
  system_metrics: {
    total_invoices: number;
    total_value: number;
    matched_invoices: number;
    discrepancy_invoices: number;
    not_paired_invoices: number;
    processing_invoices: number;
    total_suppliers: number;
    total_venues: number;
    success_rate: number;
  };
  flagged_summary: {
    total_flagged: number;
    total_error_value: number;
    affected_invoices: number;
  };
  recent_activity: Array<{
    date: string;
    invoice_count: number;
    daily_value: number;
  }>;
  top_suppliers: Array<{
    name: string;
    invoice_count: number;
    total_value: number;
  }>;
  venue_breakdown: Array<{
    name: string;
    invoice_count: number;
    total_value: number;
  }>;
}

// Fallback data when API is unavailable
const FALLBACK_DATA: DashboardData = {
  system_metrics: {
    total_invoices: 156,
    total_value: 45230.50,
    matched_invoices: 142,
    discrepancy_invoices: 8,
    not_paired_invoices: 6,
    processing_invoices: 2,
    total_suppliers: 12,
    total_venues: 3,
    success_rate: 91,
  },
  flagged_summary: {
    total_flagged: 8,
    total_error_value: 1250.75,
    affected_invoices: 6,
  },
  recent_activity: [
    { date: '2024-01-15', invoice_count: 12, daily_value: 3450.00 },
    { date: '2024-01-14', invoice_count: 8, daily_value: 2100.50 },
    { date: '2024-01-13', invoice_count: 15, daily_value: 5200.75 },
    { date: '2024-01-12', invoice_count: 10, daily_value: 2800.25 },
    { date: '2024-01-11', invoice_count: 6, daily_value: 1800.00 },
  ],
  top_suppliers: [
    { name: 'ABC Corporation', invoice_count: 45, total_value: 12500.00 },
    { name: 'XYZ Company', invoice_count: 32, total_value: 8900.50 },
    { name: 'Fresh Foods Ltd', invoice_count: 28, total_value: 7200.75 },
    { name: 'Quality Supplies', invoice_count: 22, total_value: 5800.25 },
    { name: 'Premium Vendors', invoice_count: 18, total_value: 4200.00 },
  ],
  venue_breakdown: [
    { name: 'Main Venue', invoice_count: 89, total_value: 28000.00 },
    { name: 'Secondary Venue', invoice_count: 45, total_value: 12500.00 },
    { name: 'Event Space', invoice_count: 22, total_value: 4730.50 },
  ],
};

const DashboardPage: React.FC = () => {
  const [dashboardData, setDashboardData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [usingFallback, setUsingFallback] = useState(false);

  // New widget states
  const [spend, setSpend] = useState<{ total_spend: number; prior_spend: number; delta_percent: number } | null>(null);
  const [matchRate, setMatchRate] = useState<{ total: number; passed: number; issues: number; failed: number; rate_percent: number } | null>(null);
  const [issuesByType, setIssuesByType] = useState<{ issues: Array<{ issue_type: string; count: number }>; total_flagged_items: number } | null>(null);
  const [duplicates, setDuplicates] = useState<{ duplicates_prevented: number; prevented_value: number } | null>(null);
  const [pairing, setPairing] = useState<{ paired: number; needs_review: number; unmatched: number } | null>(null);
  const [volatileProducts, setVolatileProducts] = useState<{ products: Array<{ product: string; supplier: string; current_price: number; volatility_90d: number; transactions: number }> } | null>(null);
  const [lowOCR, setLowOCR] = useState<{ total: number; low_confidence: number; threshold: number } | null>(null);

  // Filters (simple defaults; could be lifted to a global provider later)
  const [startDate, setStartDate] = useState<string | undefined>(undefined);
  const [endDate, setEndDate] = useState<string | undefined>(undefined);
  const [venue, setVenue] = useState<string | undefined>(undefined);

  useEffect(() => {
    fetchDashboardData();
  }, []);

  useEffect(() => {
    const off = on(e => {
      if (e.type === 'INVOICES_SUBMITTED') {
        fetchDashboardData();
        fetchWidgets();
      }
    });
    return off;
  }, []);

  useEffect(() => {
    // Refetch dependent widgets on filter change
    fetchWidgets();
  }, [startDate, endDate, venue]);

  const fetchDashboardData = async () => {
    try {
      setLoading(true);
      setError(null);

      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8002/api';
      const response = await fetch(`${apiUrl}/analytics/dashboard`);

      if (!response.ok) {
        throw new Error(`API Error: ${response.status} ${response.statusText}`);
      }

      const data = await response.json();
      setDashboardData(data);
      setUsingFallback(false);
    } catch (err) {
      console.warn('API unavailable, using fallback data:', err);
      setDashboardData(FALLBACK_DATA);
      setUsingFallback(true);
      setError('Backend connection unavailable - showing sample data');
    } finally {
      setLoading(false);
    }
  };

  const fetchWidgets = async () => {
    try {
      const [spendResp, matchResp, issuesResp, dupResp, pairResp, volResp, lowResp] = await Promise.all([
        apiService.getSpendSummary({ start_date: startDate, end_date: endDate, venue }),
        apiService.getMatchRate({ start_date: startDate, end_date: endDate, venue }),
        apiService.getIssuesByType({ start_date: startDate, end_date: endDate, venue }),
        apiService.getDuplicatesSummary({ start_date: startDate, end_date: endDate }),
        apiService.getUnmatchedCounts({ start_date: startDate, end_date: endDate, venue }),
        apiService.getVolatileProducts({ days: 90, limit: 5 }),
        apiService.getLowOCR({ threshold: 0.7, start_date: startDate, end_date: endDate }),
      ]);
      setSpend(spendResp);
      setMatchRate(matchResp);
      setIssuesByType(issuesResp);
      setDuplicates(dupResp);
      setPairing(pairResp);
      setVolatileProducts(volResp);
      setLowOCR(lowResp);
    } catch (e) {
      console.warn('Some analytics widgets failed to load', e);
    }
  };

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-GB', {
      style: 'currency',
      currency: 'GBP'
    }).format(amount);
  };

  const pct = (n?: number) => `${(n ?? 0).toFixed(1)}%`;

  if (loading) {
    return (
      <AppShell>
        <div className="py-8">
          <div className="flex items-center justify-center h-64">
            <div className="text-center">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
              <p className="text-gray-600">Loading dashboard...</p>
            </div>
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
          <div className="text-center mb-6">
            <h1 className="text-4xl font-bold text-gray-900 mb-2">Owlin Dashboard</h1>
            {usingFallback && (
              <div className="mt-2 p-2 bg-yellow-50 border border-yellow-200 rounded-lg max-w-md mx-auto">
                <div className="flex items-center justify-center text-sm text-yellow-800">Demo mode - showing sample data</div>
              </div>
            )}
          </div>

          {/* Filters (minimal) */}
          <div className="bg-white rounded-lg shadow-sm p-4 mb-6">
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <div>
                <label className="block text-xs text-gray-600 mb-1">Start date</label>
                <input className="w-full border rounded px-3 py-2 text-sm" type="date" value={startDate || ''} onChange={(e) => setStartDate(e.target.value || undefined)} />
              </div>
              <div>
                <label className="block text-xs text-gray-600 mb-1">End date</label>
                <input className="w-full border rounded px-3 py-2 text-sm" type="date" value={endDate || ''} onChange={(e) => setEndDate(e.target.value || undefined)} />
              </div>
              <div>
                <label className="block text-xs text-gray-600 mb-1">Venue</label>
                <input className="w-full border rounded px-3 py-2 text-sm" placeholder="All venues" value={venue || ''} onChange={(e) => setVenue(e.target.value || undefined)} />
              </div>
              <div className="flex items-end">
                <button onClick={fetchWidgets} className="w-full px-3 py-2 bg-gray-800 text-white rounded hover:bg-gray-900">Apply</button>
              </div>
            </div>
          </div>

          {/* Top row: Spend, Credits, ROI, Match Rate */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-6">
            <div className="bg-white rounded-lg shadow p-5">
              <div className="text-xs text-gray-500" title="Sum of invoices total in range">Total Spend</div>
              <div className="text-3xl font-semibold text-gray-900 mt-1">{formatCurrency(spend?.total_spend || dashboardData?.system_metrics.total_value || 0)}</div>
              <div className={`text-sm mt-1 ${((spend?.delta_percent || 0) >= 0) ? 'text-green-700' : 'text-red-700'}`}>vs prior {pct(spend?.delta_percent)}</div>
              <Link href="/invoices" className="text-sm text-blue-600 mt-2 inline-block">Open invoices →</Link>
            </div>

            <div className="bg-white rounded-lg shadow p-5">
              <div className="text-xs text-gray-500" title="Sum of confirmed credit recoveries">Credits Recovered (30/90d)</div>
              <div className="text-3xl font-semibold text-gray-900 mt-1">{formatCurrency(0)}</div>
              <div className="text-xs text-gray-500 mt-1">Coming soon</div>
              <Link href="/flagged" className="text-sm text-blue-600 mt-2 inline-block">Open cases →</Link>
            </div>

            <div className="bg-white rounded-lg shadow p-5">
              <div className="text-xs text-gray-500" title="CreditsRecovered / LicenseCost">ROI Meter</div>
              <div className="mt-2">
                <div className="h-2 rounded bg-gray-100">
                  <div className="h-2 rounded bg-green-600" style={{ width: '30%' }}></div>
                </div>
                <div className="text-sm text-gray-700 mt-2">£0 per £1 license</div>
              </div>
            </div>

            <div className="bg-white rounded-lg shadow p-5">
              <div className="text-xs text-gray-500" title="Passed / (Passed + Issues + Failed)">3‑Way Match Rate</div>
              <div className="text-3xl font-semibold text-gray-900 mt-1">{pct(matchRate?.rate_percent)}</div>
              <div className="text-sm text-gray-600 mt-1">Passed {matchRate?.passed ?? 0} • Issues {matchRate?.issues ?? 0} • Failed {matchRate?.failed ?? 0}</div>
              <Link href="/matching-demo" className="text-sm text-blue-600 mt-2 inline-block">Open triage →</Link>
            </div>
          </div>

          {/* Issues by Type, Pairing Status, Duplicates Prevented */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
            <div className="bg-white rounded-lg shadow p-5">
              <div className="flex items-center justify-between mb-2">
                <div className="text-sm font-semibold text-gray-900">Issues by Type</div>
                <div className="text-xs text-gray-500" title="Counts of flagged items by issue type">?</div>
              </div>
              <div className="space-y-2">
                {(issuesByType?.issues || []).slice(0, 6).map((it, idx) => (
                  <div key={idx} className="flex items-center justify-between">
                    <div className="text-sm text-gray-700 capitalize">{it.issue_type}</div>
                    <Link href="/flagged" className="text-sm text-blue-600">{it.count}</Link>
                  </div>
                ))}
                {(!issuesByType || issuesByType.issues.length === 0) && (
                  <div className="text-sm text-gray-500">No issues in period</div>
                )}
              </div>
            </div>

            <div className="bg-white rounded-lg shadow p-5">
              <div className="text-sm font-semibold text-gray-900 mb-2">Pairing Status</div>
              <div className="flex gap-2 flex-wrap">
                <Link href="/document-queue" className="px-3 py-1 rounded-full bg-green-100 text-green-800 text-sm">Paired {pairing?.paired ?? 0}</Link>
                <Link href="/document-queue" className="px-3 py-1 rounded-full bg-yellow-100 text-yellow-800 text-sm">Needs Review {pairing?.needs_review ?? 0}</Link>
                <Link href="/document-queue" className="px-3 py-1 rounded-full bg-red-100 text-red-800 text-sm">Unmatched {pairing?.unmatched ?? 0}</Link>
              </div>
            </div>

            <div className="bg-white rounded-lg shadow p-5">
              <div className="text-sm font-semibold text-gray-900 mb-2">Duplicates Prevented</div>
              <div className="text-3xl font-semibold text-gray-900">{duplicates?.duplicates_prevented ?? 0}</div>
              <div className="text-sm text-gray-600 mt-1">Value {formatCurrency(duplicates?.prevented_value || 0)}</div>
            </div>
          </div>

          {/* Delivery Accuracy (placeholder), Volatile Products */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
            <div className="bg-white rounded-lg shadow p-5">
              <div className="text-sm font-semibold text-gray-900 mb-2">Delivery Accuracy</div>
              <div className="text-sm text-gray-500">Heatmap coming soon</div>
            </div>
            <div className="bg-white rounded-lg shadow p-5">
              <div className="text-sm font-semibold text-gray-900 mb-2">Top Volatile Products (90d)</div>
              <div className="overflow-x-auto">
                <table className="min-w-full text-sm">
                  <thead>
                    <tr className="text-gray-500">
                      <th className="text-left py-1">Product</th>
                      <th className="text-left py-1">Supplier</th>
                      <th className="text-right py-1">Current</th>
                      <th className="text-right py-1">Volatility</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(volatileProducts?.products || []).map((p, idx) => (
                      <tr key={idx} className="border-t">
                        <td className="py-1 pr-2 text-gray-800">{p.product}</td>
                        <td className="py-1 pr-2 text-gray-600">{p.supplier}</td>
                        <td className="py-1 pl-2 text-right text-gray-800">{formatCurrency(p.current_price)}</td>
                        <td className="py-1 pl-2 text-right text-gray-800">{(p.volatility_90d * 100).toFixed(1)}%</td>
                      </tr>
                    ))}
                    {(!volatileProducts || volatileProducts.products.length === 0) && (
                      <tr><td colSpan={4} className="text-sm text-gray-500 py-2">No volatile products found</td></tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          </div>

          {/* Unmatched & Low OCR */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
            <div className="bg-white rounded-lg shadow p-5">
              <div className="text-sm font-semibold text-gray-900 mb-2">Unmatched</div>
              <div className="flex gap-2 flex-wrap">
                <Link href="/document-queue" className="px-3 py-1 rounded bg-red-100 text-red-800 text-sm">Notes — {pairing?.unmatched ?? 0}</Link>
                <Link href="/invoices" className="px-3 py-1 rounded bg-red-100 text-red-800 text-sm">Invoices — {pairing?.unmatched ?? 0}</Link>
              </div>
            </div>
            <div className="bg-white rounded-lg shadow p-5">
              <div className="text-sm font-semibold text-gray-900 mb-2">Low OCR Confidence</div>
              <Link href="/document-queue" className="inline-block px-3 py-1 rounded bg-yellow-100 text-yellow-800 text-sm">
                Needs Review (OCR): {lowOCR?.low_confidence ?? 0}
              </Link>
            </div>
            <div className="bg-white rounded-lg shadow p-5">
              <div className="text-sm font-semibold text-gray-900 mb-2">Quick Actions</div>
              <div className="flex gap-3 flex-wrap text-sm">
                <Link href="/invoice-agent-demo" className="px-3 py-2 rounded bg-gray-800 text-white">Create Credit Pack</Link>
                <Link href="/file-preview" className="px-3 py-2 rounded bg-gray-100 text-gray-800">Export to Xero/Sage/QBO</Link>
                <Link href="/matching-demo" className="px-3 py-2 rounded bg-gray-100 text-gray-800">Pair All Suggestions</Link>
              </div>
            </div>
          </div>
        </div>
      </div>
    </AppShell>
  );
};

export default DashboardPage; 