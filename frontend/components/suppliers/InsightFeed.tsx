import React from 'react';

export interface InsightItem { id:string; timestamp:string; severity:'info'|'warn'|'critical'; message:string }

export default function InsightFeed({ items }:{ items: InsightItem[] }){
	if (!items || items.length===0) {
		return <div className="bg-white rounded-[12px] border border-[#E5E7EB] shadow-sm p-3 sm:p-4 text-center text-[13px] text-[#6B7280] py-6">No recent insights</div>;
	}
	const dot = (sev:string)=> sev==='warn'? 'bg-[#F59E0B]' : sev==='critical'? 'bg-[#EF4444]' : 'bg-[#3B82F6]';
	return (
		<div className="bg-white rounded-[12px] border border-[#E5E7EB] shadow-sm p-3 sm:p-4">
			<div role="list">
				{items.map((it)=> (
					<div key={it.id} role="listitem" className="flex items-start gap-3 py-2 first:pt-0 last:pb-0 border-b border-[#E5E7EB] last:border-b-0">
						<div className={`mt-1 w-[8px] h-[8px] rounded-full ${dot(it.severity)}`} aria-hidden />
						<div className="min-w-0">
							<div className="text-[12px] text-[#6B7280]">{new Date(it.timestamp).toLocaleString()}</div>
							<div className="text-[14px] text-[#1F2937]">{it.message}</div>
						</div>
					</div>
				))}
			</div>
		</div>
	);
} 