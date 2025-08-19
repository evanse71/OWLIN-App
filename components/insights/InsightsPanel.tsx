import React, { useEffect, useState } from 'react';
import InsightCard from './InsightCard';
import ScoreBadge from './ScoreBadge';

export default function InsightsPanel({ supplierId }:{ supplierId: string }) {
	const [summary, setSummary] = useState<any|null>(null);
	const [error, setError] = useState<string|null>(null);
	async function load() {
		try {
			const end = new Date();
			const start = new Date(end.getFullYear()-1, end.getMonth(), 1);
			const qs = new URLSearchParams({ start: start.toISOString().slice(0,10), end: end.toISOString().slice(0,10), bucket: 'month' });
			const res = await (await fetch(`/api/insights/suppliers/${supplierId}/summary?${qs.toString()}`, { cache: 'no-store' })).json();
			setSummary(res);
		} catch (e:any) { setError(e?.message || 'Failed to fetch insights'); }
	}
	useEffect(()=>{ load(); }, [supplierId]);
	if (error) return <div className="text-red-700">{error}</div>;
	if (!summary) return <div className="text-[var(--owlin-color-muted)]">Loading...</div>;
	return (
		<div className="space-y-3">
			<div className="flex flex-wrap gap-2">
				{summary.top_badges.map((b:any, i:number)=> <ScoreBadge key={i} {...b} />)}
			</div>
			<div className="grid grid-cols-1 md:grid-cols-2 gap-3">
				{summary.series.map((s:any, i:number)=> (
					<InsightCard key={i} title={s.metric.replace('_',' ').toUpperCase()} badge={{ label: 'Latest', value: `${(s.points?.slice(-1)[0]?.v ?? 0)}` }} points={s.points} />
				))}
			</div>
		</div>
	);
} 