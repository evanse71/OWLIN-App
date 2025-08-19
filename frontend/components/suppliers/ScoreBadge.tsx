import React from 'react';

export default function ScoreBadge({ score }:{ score:number }){
	const clamped = Math.max(0, Math.min(100, Math.round(score)));
	const dash = `${clamped} 100`;
	let color = '#10B981';
	if (clamped < 60) color = '#EF4444';
	else if (clamped < 80) color = '#F59E0B';
	return (
		<div className="relative w-[64px] h-[64px]" aria-label={`Overall supplier score ${clamped} out of 100`} role="progressbar" aria-valuemin={0} aria-valuemax={100} aria-valuenow={clamped}>
			<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 36 36" width="64" height="64">
				<path d="M18 2a16 16 0 1 1 0 32a16 16 0 0 1 0-32" fill="none" stroke="#E5E7EB" strokeWidth="3"/>
				<path d="M18 2a16 16 0 1 1 0 32a16 16 0 0 1 0-32" fill="none" stroke={color} strokeWidth="3" strokeLinecap="round" strokeDasharray={dash}/>
			</svg>
			<div className="absolute inset-0 flex items-center justify-center text-[14px] font-semibold text-[#1F2937]">{clamped}</div>
		</div>
	);
} 