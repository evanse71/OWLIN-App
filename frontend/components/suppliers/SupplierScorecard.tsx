import React, { useEffect, useMemo, useState } from 'react';
import ScoreBadge from './ScoreBadge';
import MetricBadge from './MetricBadge';
import InsightFeed, { InsightItem } from './InsightFeed';

interface SupplierMetric { name:string; score:number; trend:'up'|'down'|'stable'; detail:string }
interface SupplierScorecard { supplier_id:string; overall_score:number; categories: Record<string,SupplierMetric>; insights: InsightItem[] }

export default function SupplierScorecard({ supplierId }:{ supplierId:string }){
	const [data, setData] = useState<SupplierScorecard|null>(null);
	const [error, setError] = useState<string|null>(null);
	const [cachedInfo, setCachedInfo] = useState<string|null>(null);

	async function load() {
		try {
			setError(null);
			const res = await fetch(`/api/suppliers/${supplierId}/scorecard`, { cache: 'no-store' });
			if (!res.ok) throw new Error('Failed to load');
			const json = await res.json();
			setData(json);
			setCachedInfo(null);
		} catch (e:any) {
			setError("Couldn't refresh supplier data. Showing last saved info.");
		}
	}
	useEffect(()=>{ load(); }, [supplierId]);

	const metrics = useMemo(()=> data ? [
		{ key:'spend_share', label:'Spend Share', icon:(<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" aria-label="Spend share"><circle cx="8" cy="8" r="7" fill="#E5E7EB"/><path d="M8 1 A7 7 0 1 1 2 8 L8 8 Z" fill="#2563EB"/></svg>)},
		{ key:'reliability', label:'Delivery Reliability', icon:(<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="none" stroke="#374151" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-label="Delivery reliability"><rect x="1" y="3" width="12" height="7"/><circle cx="5" cy="14" r="2"/><circle cx="12" cy="14" r="2"/></svg>)},
		{ key:'pricing_stability', label:'Pricing Stability', icon:(<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="none" stroke="#374151" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-label="Pricing stability"><path d="M2 7l7 7 7-7-7-7-7 7z"/></svg>)},
		{ key:'error_rate', label:'Error Rate', icon:(<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="none" stroke="#D97706" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-label="Error rate"><path d="M8 2l6.9 12H1.1L8 2z"/><path d="M8 6v4M8 12h.01"/></svg>)},
		{ key:'credit_responsiveness', label:'Credit Responsiveness', icon:(<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="none" stroke="#6B7280" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-label="Credit responsiveness"><path d="M4 2h8M4 14h8M5 2c0 3 2 4 3 6-1 2-3 3-3 6M11 2c0 3-2 4-3 6 1 2 3 3 3 6"/></svg>)},
		{ key:'doc_confidence', label:'Document Confidence', icon:(<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="none" stroke="#374151" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-label="Document confidence"><path d="M1 8s3-5 7-5 7 5 7 5-3 5-7 5-7-5-7-5z"/><circle cx="8" cy="8" r="2"/></svg>)},
	] : [], [data]);

	return (
		<div className="bg-white rounded-[12px] border border-[#E5E7EB] shadow-sm p-4 sm:p-5">
			<div className="flex items-start justify-between gap-3 mb-4">
				<div className="text-[16px] font-semibold leading-[1.4]">Supplier Scorecard</div>
				{cachedInfo && (
					<div className="inline-flex items-center gap-1 text-[12px] text-[#92400E] bg-[#FFFBEB] border border-[#FDE68A] rounded-[6px] px-2 py-1">Viewing cached data — {cachedInfo}</div>
				)}
			</div>
			{error && (
				<div className="flex items-center gap-2 bg-[#FFFBEB] border border-[#FDE68A] text-[#7C2D12] rounded-[8px] p-2 text-[12px] mb-3">
					<span>Couldn't refresh supplier data. Showing last saved info.</span>
					<button onClick={load} className="ml-auto inline-flex items-center gap-1 px-2 py-1 rounded-[6px] border border-[#E5E7EB] text-[#374151] hover:bg-white focus:outline-none focus:ring-2 focus:ring-[#A7C4A0]">Retry</button>
				</div>
			)}
			<div className="flex items-center justify-between">
				<div className="text-[14px] text-[#6B7280]">Overall</div>
				<ScoreBadge score={data?.overall_score ?? 0} />
			</div>
			<div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6 mt-4">
				{metrics.map((m)=>{
					const v = data?.categories?.[m.key as keyof typeof data.categories];
					if (!v) return null;
					return (
						<MetricBadge key={m.key} icon={m.icon} name={m.label} detail={v.detail} score={v.score} trend={v.trend} />
					);
				})}
			</div>
			<div className="mt-6 mb-2 text-[14px] font-semibold text-[#1F2937]">Insights</div>
			<InsightFeed items={data?.insights ?? []} />
		</div>
	);
} 