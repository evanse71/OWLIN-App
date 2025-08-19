import React, { useState } from 'react';

interface VenueRow {
	venue_id: string;
	venue_name: string;
	total_invoices: number;
	total_spend: number;
	match_rate: number;
	avg_confidence: number;
	flagged_issues: number;
	delivery_reliability: number;
}

interface CompareTableProps {
	venues: VenueRow[];
}

export default function CompareTable({ venues }: CompareTableProps) {
	const [sortField, setSortField] = useState<keyof VenueRow>('venue_name');
	const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('asc');
	
	const handleSort = (field: keyof VenueRow) => {
		if (sortField === field) {
			setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
		} else {
			setSortField(field);
			setSortDirection('asc');
		}
	};
	
	const sortedVenues = [...venues].sort((a, b) => {
		const aVal = a[sortField];
		const bVal = b[sortField];
		
		if (typeof aVal === 'string' && typeof bVal === 'string') {
			return sortDirection === 'asc' 
				? aVal.localeCompare(bVal)
				: bVal.localeCompare(aVal);
		}
		
		if (typeof aVal === 'number' && typeof bVal === 'number') {
			return sortDirection === 'asc' ? aVal - bVal : bVal - aVal;
		}
		
		return 0;
	});
	
	const getSortIcon = (field: keyof VenueRow) => {
		if (sortField !== field) return '↕';
		return sortDirection === 'asc' ? '↑' : '↓';
	};
	
	return (
		<div className="bg-white rounded-lg border border-[var(--owlin-color-border)] overflow-hidden">
			<div className="px-4 py-3 border-b border-[var(--owlin-color-border)]">
				<h3 className="font-semibold">Venue Comparison</h3>
			</div>
			<div className="overflow-x-auto">
				<table className="w-full text-sm">
					<thead className="bg-[var(--owlin-color-bg)]">
						<tr>
							<th 
								className="px-4 py-2 text-left cursor-pointer hover:bg-gray-100"
								onClick={() => handleSort('venue_name')}
							>
								Venue {getSortIcon('venue_name')}
							</th>
							<th 
								className="px-4 py-2 text-right cursor-pointer hover:bg-gray-100"
								onClick={() => handleSort('total_invoices')}
							>
								Invoices {getSortIcon('total_invoices')}
							</th>
							<th 
								className="px-4 py-2 text-right cursor-pointer hover:bg-gray-100"
								onClick={() => handleSort('total_spend')}
							>
								Spend {getSortIcon('total_spend')}
							</th>
							<th 
								className="px-4 py-2 text-right cursor-pointer hover:bg-gray-100"
								onClick={() => handleSort('match_rate')}
							>
								Match Rate {getSortIcon('match_rate')}
							</th>
							<th 
								className="px-4 py-2 text-right cursor-pointer hover:bg-gray-100"
								onClick={() => handleSort('avg_confidence')}
							>
								Confidence {getSortIcon('avg_confidence')}
							</th>
							<th 
								className="px-4 py-2 text-right cursor-pointer hover:bg-gray-100"
								onClick={() => handleSort('flagged_issues')}
							>
								Issues {getSortIcon('flagged_issues')}
							</th>
							<th 
								className="px-4 py-2 text-right cursor-pointer hover:bg-gray-100"
								onClick={() => handleSort('delivery_reliability')}
							>
								Reliability {getSortIcon('delivery_reliability')}
							</th>
						</tr>
					</thead>
					<tbody>
						{sortedVenues.map((venue, index) => (
							<tr 
								key={venue.venue_id} 
								className={`border-t border-[var(--owlin-color-border)] ${
									index % 2 === 0 ? 'bg-white' : 'bg-[var(--owlin-color-bg)]'
								}`}
							>
								<td className="px-4 py-2 font-medium">{venue.venue_name}</td>
								<td className="px-4 py-2 text-right">{venue.total_invoices.toLocaleString()}</td>
								<td className="px-4 py-2 text-right">${venue.total_spend.toLocaleString()}</td>
								<td className="px-4 py-2 text-right">{venue.match_rate.toFixed(1)}%</td>
								<td className="px-4 py-2 text-right">{venue.avg_confidence.toFixed(1)}%</td>
								<td className="px-4 py-2 text-right">{venue.flagged_issues}</td>
								<td className="px-4 py-2 text-right">{venue.delivery_reliability.toFixed(1)}%</td>
							</tr>
						))}
					</tbody>
				</table>
			</div>
			{venues.length === 0 && (
				<div className="px-4 py-8 text-center text-[var(--owlin-color-muted)]">
					No venue data available
				</div>
			)}
		</div>
	);
} 