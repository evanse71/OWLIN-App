import React from 'react';

export default function UniversalTrendGraph({ width=560, height=160, points }:{ width?:number; height?:number; points: { t: string; v: number }[] }){
	if (!points || points.length === 0) return <div className="text-sm text-[var(--owlin-color-muted)]">No data</div>;
	const padding = { l: 28, r: 6, t: 10, b: 18 };
	const xs = points.map((p)=>new Date(p.t).getTime());
	const ys = points.map((p)=>p.v);
	const xMin = Math.min(...xs), xMax = Math.max(...xs);
	const yMin = Math.min(...ys), yMax = Math.max(...ys);
	const x = (t:number)=> padding.l + ( (t - xMin) / Math.max(1, xMax - xMin) ) * (width - padding.l - padding.r);
	const y = (v:number)=> height - padding.b - ( (v - yMin) / Math.max(1, yMax - yMin) ) * (height - padding.t - padding.b);
	const path = points.map((p,i)=> `${i===0?'M':'L'} ${x(new Date(p.t).getTime()).toFixed(1)} ${y(p.v).toFixed(1)}`).join(' ');
	const area = `${path} L ${x(xMax).toFixed(1)} ${y(yMin).toFixed(1)} L ${x(xMin).toFixed(1)} ${y(yMin).toFixed(1)} Z`;
	return (
		<svg width={width} height={height} role="img" aria-label="trend graph">
			<path d={area} fill="rgba(31,58,95,0.06)"></path>
			<path d={path} fill="none" stroke="currentColor" strokeWidth="1.5"></path>
			{points.map((p,i)=> (
				<circle key={i} cx={x(new Date(p.t).getTime())} cy={y(p.v)} r="2" />
			))}
		</svg>
	);
} 