import React from 'react';
import clsx from 'clsx';

export default function ScoreBadge({ label, value, tone='neutral' }:{ label:string; value:string; tone?:'neutral'|'ok'|'warn'|'error' }){
	const tones: Record<string,string> = {
		neutral: 'bg-[var(--owlin-color-bg)] text-[var(--owlin-color-muted)]',
		ok: 'bg-[#ECFDF5] text-[#047857]',
		warn: 'bg-[#FFFBEB] text-[#92400E]',
		error: 'bg-[#FEF2F2] text-[#991B1B]',
	};
	return (
		<div className={clsx('inline-flex items-center gap-2 px-2 py-1 rounded-full text-xs', tones[tone])}>
			<span className="uppercase tracking-wide">{label}</span>
			<strong>{value}</strong>
		</div>
	);
} 