import React, { useEffect, useState, useMemo } from 'react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';

function formatGBP(n: number): string {
	const pounds = (n ?? 0);
	return pounds.toLocaleString('en-GB', { style: 'currency', currency: 'GBP' });
}

function MatchBadge({ value }: { value: number }) {
	const tone = value >= 90 ? '#047857' : value >= 70 ? '#92400E' : '#991B1B';
	return <span style={{ color: tone }} className="text-sm font-medium">{value}%</span>;
}

const Icons = {
	CheckCircle: (
		<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="inline">
			<path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/>
		</svg>
	),
	AlertTriangle: (
		<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="inline">
			<path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/>
			<line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/>
		</svg>
	),
	TrendingUp: (
		<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="inline">
			<polyline points="23 6 13.5 15.5 8.5 10.5 1 18"/><polyline points="17 6 23 6 23 12"/>
		</svg>
	)
};

export default function SupplierScorecardPanel({ role = 'Finance' as 'Finance'|'GM'|'ShiftLead' }) {
	const [items, setItems] = useState<any[]>([]);
	const [loading, setLoading] = useState(true);
	const [error, setError] = useState<string|null>(null);

	async function load() {
		try {
			setLoading(true); setError(null);
			const res = await (await fetch('/api/suppliers/scorecard', { cache: 'no-store' })).json();
			setItems(res?.items ?? []);
		} catch (e: any) {
			setError(e?.message || 'Failed to load scorecard');
		} finally { setLoading(false); }
	}
	useEffect(()=>{ load(); }, []);

	function exportCsv() {
		const headers = [
			'supplier_id','supplier_name','total_invoices','match_rate','avg_invoice_confidence','total_flagged_issues','credit_value_pending','delivery_reliability_score','last_updated'
		];
		const rows = items.map((i)=> headers.map(h=> i[h] ?? ''));
		const csv = [headers.join(','), ...rows.map(r=> r.join(','))].join('\n');
		const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
		const url = URL.createObjectURL(blob);
		const a = document.createElement('a');
		a.href = url; a.download = 'supplier_scorecard.csv'; a.click(); URL.revokeObjectURL(url);
	}

	return (
		<div className="space-y-3">
			<div className="flex items-center justify-between">
				<h2 className="text-xl font-semibold text-[var(--owlin-color-text)]">Supplier Scorecard</h2>
				<Button onClick={exportCsv}>Export CSV</Button>
			</div>
			{loading && <div className="text-[var(--owlin-color-muted)]">Loading...</div>}
			{error && <div className="text-red-700">Error: {error}</div>}
			{!loading && !error && (
				<div className="grid gap-3" style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))' }}>
					{items.map((it:any) => (
						<Card key={it.supplier_id}>
							<div role="button" tabIndex={0} onKeyDown={(e)=>{ if(e.key==='Enter'||e.key===' ') (window.location.href = `/suppliers/${it.supplier_id}`); }} onClick={()=>{ window.location.href = `/suppliers/${it.supplier_id}`; }} className="block outline-none focus:ring-2 focus:ring-[var(--owlin-color-accent)]">
								<div className="flex items-start justify-between">
									<div className="min-w-0">
										<div className="text-lg font-semibold truncate">{it.supplier_name}</div>
										<div className="text-sm text-[var(--owlin-color-muted)]">{new Date(it.last_updated).toLocaleString()}</div>
									</div>
								</div>
								<div className="mt-3 flex items-center justify-between">
									<div className="flex items-center gap-2">
										{Icons.CheckCircle}
										<span className="text-sm">Match</span>
									</div>
									<MatchBadge value={it.match_rate ?? 0} />
								</div>
								<div className="mt-2 flex items-center justify-between text-sm">
									<div className="flex items-center gap-2">
										{Icons.AlertTriangle}
										<span>Issues</span>
									</div>
									<div className={it.total_flagged_issues>0? 'text-[#92400E]':'text-[var(--owlin-color-muted)]'}>{it.total_flagged_issues}</div>
								</div>
								{role !== 'ShiftLead' && (
									<div className="mt-2 flex items-center justify-between text-sm">
										<span>Credit pending</span>
										<div className="text-[var(--owlin-color-muted)]">{formatGBP(it.credit_value_pending ?? 0)}</div>
									</div>
								)}
								{role !== 'ShiftLead' && (
									<div className="mt-3">
										<div className="flex items-center gap-2 text-sm mb-1">
											{Icons.TrendingUp}
											<span>Delivery reliability</span>
										</div>
										<div className="w-full h-2 rounded-full bg-[var(--owlin-color-bg)] overflow-hidden">
											<div className="h-full bg-[var(--owlin-color-accent)]" style={{ width: `${Math.max(0, Math.min(100, it.delivery_reliability_score ?? 0))}%` }} />
										</div>
									</div>
								)}
							</div>
						</Card>
					))}
				</div>
			)}
			{!loading && !error && items.length === 0 && (
				<div className="text-[var(--owlin-color-muted)] p-6 text-center">No suppliers found.</div>
			)}
		</div>
	);
} 