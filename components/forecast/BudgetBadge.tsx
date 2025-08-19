import React from 'react';

export default function BudgetBadge({ projected, threshold }:{ projected:number; threshold:number }){
	const pct = threshold ? Math.round((projected/threshold)*100) : 0;
	const tone = pct>=120? '#991B1B' : pct>=105? '#92400E' : '#047857';
	return (
		<div className="inline-flex items-center gap-2 px-2 py-1 rounded-full text-xs" style={{ background: 'var(--owlin-color-bg)', color: tone }}>
			<span className="uppercase tracking-wide">Budget</span>
			<strong>{pct}%</strong>
		</div>
	);
} 