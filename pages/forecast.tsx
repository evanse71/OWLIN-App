import React from 'react';
import ForecastPanel from '@/components/forecast/ForecastPanel';

export default function ForecastPage(){
	const sample = '00000000-0000-0000-0000-000000000001';
	return (
		<main className="max-w-[1000px] mx-auto p-4">
			<h1 className="text-xl font-semibold mb-3">Forecasts</h1>
			<ForecastPanel itemId={sample} />
		</main>
	);
} 