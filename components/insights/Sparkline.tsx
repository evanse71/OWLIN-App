import React from 'react';

export default function Sparkline({ points, width=120, height=28 }:{ points:{t:string,v:number}[]; width?:number; height?:number }){
	if (!points?.length) return null;
	const xs = points.map(p=>new Date(p.t).getTime()); const ys = points.map(p=>p.v);
	const xMin=Math.min(...xs), xMax=Math.max(...xs); const yMin=Math.min(...ys), yMax=Math.max(...ys);
	const x=(t:number)=> ( (t-xMin)/Math.max(1,xMax-xMin) ) * width;
	const y=(v:number)=> height - ( (v-yMin)/Math.max(1,yMax-yMin) ) * height;
	const d = points.map((p,i)=> `${i?'L':'M'} ${x(new Date(p.t).getTime()).toFixed(1)} ${y(p.v).toFixed(1)}`).join(' ');
	return <svg width={width} height={height}><path d={d} fill="none" stroke="currentColor" strokeWidth="1"/></svg>;
} 