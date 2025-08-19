import React, { useEffect, useState } from 'react';
import ForecastChart from './ForecastChart';
import BudgetBadge from './BudgetBadge';

export default function ForecastPanel({ itemId }:{ itemId: string }){
	const [data, setData] = useState<any|null>(null);
	const [error, setError] = useState<string|null>(null);
	useEffect(()=>{
		async function load(){
			try{
				const res = await (await fetch(`/api/forecast/items/${itemId}?horizon=3`, { cache: 'no-store' })).json();
				setData(res);
			}catch(e:any){ setError(e?.message||'Failed to load forecast'); }
		}
		if(itemId) load();
	},[itemId]);
	if(error) return <div className="text-red-700">{error}</div>;
	if(!data) return <div className="text-[var(--owlin-color-muted)]">Loading...</div>;
	return (
		<div className="space-y-3">
			<div className="flex items-center justify-between">
				<div className="font-medium">Price Forecast</div>
				<BudgetBadge projected={0} threshold={0} />
			</div>
			<ForecastChart history={data.points} forecast={data.forecast} />
		</div>
	);
} 