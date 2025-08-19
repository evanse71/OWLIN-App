import React from 'react';

export default function ForecastChart({ history, forecast, width=560, height=180 }:{ history:{t:string,p:number}[]; forecast:{t:string,p:number}[]; width?:number; height?:number }){
	const points = [...history, ...forecast];
	if (!points.length) return <div className="text-sm text-[var(--owlin-color-muted)]">No data</div>;
	const pad={l:30,r:8,t:10,b:18};
	const xs=points.map(p=>new Date(p.t).getTime()); const ys=points.map(p=>p.p);
	const xMin=Math.min(...xs), xMax=Math.max(...xs); const yMin=Math.min(...ys), yMax=Math.max(...ys);
	const x=(t:number)=> pad.l + ((t-xMin)/Math.max(1,xMax-xMin))*(width-pad.l-pad.r);
	const y=(v:number)=> height - pad.b - ((v-yMin)/Math.max(1,yMax-yMin))*(height-pad.t-pad.b);
	const dHist = history.map((p,i)=> `${i?'L':'M'} ${x(new Date(p.t).getTime()).toFixed(1)} ${y(p.p).toFixed(1)}`).join(' ');
	const dFc = forecast.map((p,i)=> `${i?'L':'M'} ${x(new Date(p.t).getTime()).toFixed(1)} ${y(p.p).toFixed(1)}`).join(' ');
	return (
		<svg width={width} height={height} role="img" aria-label="price forecast">
			<path d={dHist} fill="none" stroke="#1F3A5F" strokeWidth="1.5"/>
			<path d={dFc} fill="none" stroke="#2563EB" strokeDasharray="4 3" strokeWidth="1.5"/>
		</svg>
	);
} 