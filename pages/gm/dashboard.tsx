import React, { useEffect, useState } from 'react';
import KpiCard from '@/components/gm/KpiCard';
import CompareTable from '@/components/gm/CompareTable';
import TrendBlock from '@/components/gm/TrendBlock';

interface DashboardData {
	period: string;
	total_venues: number;
	total_invoices: number;
	total_spend: number;
	avg_match_rate: number;
	avg_confidence: number;
	total_issues: number;
	kpi_cards: Array<{
		title: string;
		value: string;
		delta?: string;
		trend: 'up' | 'down' | 'neutral';
		series: number[];
	}>;
	venue_comparison: Array<{
		venue_id: string;
		venue_name: string;
		total_invoices: number;
		total_spend: number;
		match_rate: number;
		avg_confidence: number;
		flagged_issues: number;
		delivery_reliability: number;
	}>;
	trends: Array<{
		venue_id: string;
		venue_name: string;
		series: Array<{
			date: string;
			value: number;
		}>;
	}>;
}

export default function GMDashboard() {
	const [data, setData] = useState<DashboardData | null>(null);
	const [loading, setLoading] = useState(true);
	const [error, setError] = useState<string | null>(null);
	const [dateRange, setDateRange] = useState({
		start: '2025-07-01',
		end: '2025-07-31'
	});
	
	const fetchDashboardData = async () => {
		setLoading(true);
		setError(null);
		
		try {
			const response = await fetch(
				`/api/gm/dashboard/summary?start=${dateRange.start}&end=${dateRange.end}`,
				{ cache: 'no-store' }
			);
			
			if (!response.ok) {
				throw new Error(`HTTP ${response.status}: ${response.statusText}`);
			}
			
			const dashboardData = await response.json();
			setData(dashboardData);
		} catch (err) {
			setError(err instanceof Error ? err.message : 'Failed to load dashboard data');
		} finally {
			setLoading(false);
		}
	};
	
	useEffect(() => {
		fetchDashboardData();
	}, [dateRange]);
	
	const handleRefresh = async () => {
		try {
			await fetch('/api/gm/dashboard/refresh', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ force: true })
			});
			await fetchDashboardData();
		} catch (err) {
			console.error('Failed to refresh:', err);
		}
	};
	
	if (loading) {
		return (
			<main className="max-w-[1200px] mx-auto p-4">
				<div className="flex items-center justify-center h-64">
					<div className="text-[var(--owlin-color-muted)]">Loading dashboard...</div>
				</div>
			</main>
		);
	}
	
	if (error) {
		return (
			<main className="max-w-[1200px] mx-auto p-4">
				<div className="bg-red-50 border border-red-200 rounded-lg p-4">
					<div className="text-red-800 font-medium">Error loading dashboard</div>
					<div className="text-red-600 text-sm mt-1">{error}</div>
					<button 
						onClick={fetchDashboardData}
						className="mt-3 px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700"
					>
						Retry
					</button>
				</div>
			</main>
		);
	}
	
	if (!data) {
		return (
			<main className="max-w-[1200px] mx-auto p-4">
				<div className="text-center text-[var(--owlin-color-muted)]">
					No dashboard data available
				</div>
			</main>
		);
	}
	
	return (
		<main className="max-w-[1200px] mx-auto p-4 space-y-6">
			{/* Header */}
			<div className="flex items-center justify-between">
				<div>
					<h1 className="text-2xl font-semibold">GM Dashboard</h1>
					<p className="text-[var(--owlin-color-muted)] mt-1">
						{data.period} • {data.total_venues} venues
					</p>
				</div>
				<div className="flex gap-3">
					<select 
						value={`${dateRange.start} to ${dateRange.end}`}
						onChange={(e) => {
							const [start, end] = e.target.value.split(' to ');
							setDateRange({ start, end });
						}}
						className="px-3 py-2 border border-[var(--owlin-color-border)] rounded text-sm"
					>
						<option value="2025-07-01 to 2025-07-31">July 2025</option>
						<option value="2025-06-01 to 2025-06-30">June 2025</option>
						<option value="2025-05-01 to 2025-05-31">May 2025</option>
					</select>
					<button 
						onClick={handleRefresh}
						className="px-4 py-2 bg-[var(--owlin-color-accent)] text-white rounded hover:brightness-110 text-sm"
					>
						Refresh
					</button>
				</div>
			</div>
			
			{/* KPI Cards */}
			<div className="grid grid-cols-1 md:grid-cols-3 gap-4">
				{data.kpi_cards.map((card, index) => (
					<KpiCard
						key={index}
						title={card.title}
						value={card.value}
						delta={card.delta}
						trend={card.trend}
						series={card.series}
					/>
				))}
			</div>
			
			{/* Summary Stats */}
			<div className="grid grid-cols-1 md:grid-cols-4 gap-4">
				<TrendBlock
					title="Total Invoices"
					value={data.total_invoices.toLocaleString()}
					delta="+15.2%"
					trend="up"
					data={[120, 135, 142, 138, 156, 148, 162]}
				/>
				<TrendBlock
					title="Total Spend"
					value={`$${data.total_spend.toLocaleString()}`}
					delta="+8.7%"
					trend="up"
					data={[45000, 48000, 52000, 49000, 54000, 51000, 58000]}
				/>
				<TrendBlock
					title="Avg Match Rate"
					value={`${data.avg_match_rate.toFixed(1)}%`}
					delta="+2.1%"
					trend="up"
					data={[85.2, 87.1, 86.8, 88.3, 89.4, 87.9, 88.7]}
				/>
				<TrendBlock
					title="Flagged Issues"
					value={data.total_issues.toString()}
					delta="-12.5%"
					trend="down"
					data={[24, 22, 19, 18, 16, 15, 14]}
				/>
			</div>
			
			{/* Venue Comparison Table */}
			<CompareTable venues={data.venue_comparison} />
		</main>
	);
} 