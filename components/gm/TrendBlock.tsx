import React from 'react';
import Spark from './Spark';

interface TrendBlockProps {
	title: string;
	value: string;
	delta?: string;
	trend?: 'up' | 'down' | 'neutral';
	data?: number[];
}

export default function TrendBlock({ 
	title, 
	value, 
	delta, 
	trend = 'neutral', 
	data = [] 
}: TrendBlockProps) {
	const getTrendColor = () => {
		switch (trend) {
			case 'up': return 'text-green-600 bg-green-50';
			case 'down': return 'text-red-600 bg-red-50';
			default: return 'text-gray-600 bg-gray-50';
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
		<div className="bg-white rounded-lg border border-[var(--owlin-color-border)] p-4">
			<div className="flex items-center justify-between mb-3">
				<h3 className="text-sm font-medium text-[var(--owlin-color-muted)]">{title}</h3>
				{delta && (
					<span className={`text-xs px-2 py-1 rounded-full font-medium ${getTrendColor()}`}>
						{getTrendIcon()} {delta}
					</span>
				)}
			</div>
			<div className="text-xl font-semibold mb-3">{value}</div>
			{data.length > 0 && (
				<div className="h-16">
					<Spark data={data} width={120} height={60} />
				</div>
			)}
		</div>
	);
} 