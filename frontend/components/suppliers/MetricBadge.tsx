import React from 'react';

export type Trend = 'up'|'down'|'stable';

export default function MetricBadge({
	icon,
	name,
	detail,
	score,
	trend,
	onActivate
}:{
	icon: React.ReactNode;
	name: string;
	detail: string;
	score: number;
	trend: Trend;
	onActivate?: ()=>void;
}){
	const trendClass = trend==='up' ? 'text-[#16A34A]' : trend==='down' ? 'text-[#DC2626]' : 'text-[#6B7280]';
	return (
		<button type="button" onClick={onActivate} className="w-full text-left focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-[#A7C4A0] rounded-[12px]">
			<div className="flex items-center justify-between gap-3 bg-[#F9FAFB] border border-[#E5E7EB] rounded-[12px] p-3 hover:shadow-sm transition-shadow">
				<div className="shrink-0 w-8 h-8 rounded-full bg-white border border-[#E5E7EB] flex items-center justify-center" aria-hidden>{icon}</div>
				<div className="min-w-0 flex-1">
					<div className="text-[13px] font-medium text-[#1F2937] truncate">{name}</div>
					<div className="text-[12px] text-[#6B7280] truncate">{detail}</div>
				</div>
				<div className="text-right">
					<div className="text-[14px] font-semibold text-[#1F2937]">{Math.round(score)}</div>
					<div className={`flex items-center justify-end gap-1 text-[12px] ${trendClass}`}>
						{trend==='up' && '↑'}
						{trend==='down' && '↓'}
						{trend==='stable' && '→'}
					</div>
				</div>
			</div>
		</button>
	);
} 