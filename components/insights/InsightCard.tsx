import React from 'react';
import UniversalTrendGraph from './UniversalTrendGraph';
import ScoreBadge from './ScoreBadge';

export default function InsightCard({ title, badge, points }:{ title:string; badge:{label:string; value:string; tone?:'neutral'|'ok'|'warn'|'error'}; points:{t:string,v:number}[] }){
	return (
		<div className="bg-white rounded-[12px] border border-[var(--owlin-color-border)] p-3">
			<div className="flex items-center justify-between mb-2">
				<div className="font-medium">{title}</div>
				<ScoreBadge {...badge} />
			</div>
			<UniversalTrendGraph points={points} />
		</div>
	);
} 