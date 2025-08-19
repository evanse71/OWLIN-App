import React from 'react';

interface KpiCardProps {
	title: string;
	value: string;
	delta?: string;
	trend?: 'up' | 'down' | 'neutral';
	series?: number[];
}

export default function KpiCard({ title, value, delta, trend = 'neutral', series = [] }: KpiCardProps) {
	const getTrendColor = () => {
		switch (trend) {
			case 'up': return 'text-green-600';
			case 'down': return 'text-red-600';
			default: return 'text-gray-500';
		}
	};
	
	const getTrendIcon = () => {
		switch (trend) {
			case 'up': return '↗';
			case 'down': return '↘';
			default: return '→';
		}
	};
	
	return (
		<div className="bg-white rounded-lg border border-[var(--owlin-color-border)] p-4 hover:shadow-sm transition-shadow">
			<div className="flex items-center justify-between mb-2">
				<h3 className="text-sm font-medium text-[var(--owlin-color-muted)]">{title}</h3>
				{delta && (
					<span className={`text-xs font-medium ${getTrendColor()}`}>
						{getTrendIcon()} {delta}
					</span>
				)}
			</div>
			<div className="text-2xl font-semibold mb-3">{value}</div>
			{series.length > 0 && (
				<div className="h-12">
					<Spark data={series} />
				</div>
			)}
		</div>
	);
}

// Pure SVG sparkline component
function Spark({ data }: { data: number[] }) {
	if (data.length < 2) return null;
	
	const width = 100;
	const height = 40;
	const padding = 4;
	
	const chartWidth = width - (padding * 2);
	const chartHeight = height - (padding * 2);
	
	const min = Math.min(...data);
	const max = Math.max(...data);
	const range = max - min || 1;
	
	const points = data.map((value, index) => {
		const x = padding + (index / (data.length - 1)) * chartWidth;
		const y = padding + chartHeight - ((value - min) / range) * chartHeight;
		return `${x},${y}`;
	}).join(' ');
	
	return (
		<svg width={width} height={height} className="w-full h-full">
			<polyline
				fill="none"
				stroke="currentColor"
				strokeWidth="1.5"
				points={points}
				className="text-[var(--owlin-color-accent)]"
			/>
		</svg>
	);
} 