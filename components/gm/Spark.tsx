import React from 'react';

interface SparkProps {
	data: number[];
	width?: number;
	height?: number;
	color?: string;
}

export default function Spark({ 
	data, 
	width = 100, 
	height = 40, 
	color = "var(--owlin-color-accent)" 
}: SparkProps) {
	if (data.length < 2) return null;
	
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
				stroke={color}
				strokeWidth="1.5"
				points={points}
			/>
		</svg>
	);
} 