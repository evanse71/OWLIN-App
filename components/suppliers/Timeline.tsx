import React from 'react';

export type Event = {
	id: string;
	ts: string;
	type: string;
	title: string;
	summary?: string;
	severity?: 'info' | 'warn' | 'error';
};

export default function Timeline({ events }: { events: Event[] }) {
	if (!events?.length) {
		return (
			<div className="text-[var(--owlin-color-muted)] text-sm p-4 text-center">
				No events in this period.
			</div>
		);
	}
	
	const getSeverityColor = (severity?: string) => {
		switch (severity) {
			case 'error': return 'border-red-200 bg-red-50';
			case 'warn': return 'border-yellow-200 bg-yellow-50';
			default: return 'border-[var(--owlin-color-border)] bg-white';
		}
	};
	
	const getEventIcon = (type: string) => {
		switch (type) {
			case 'INVOICE': return '📄';
			case 'DELIVERY': return '🚚';
			case 'ISSUE_OPENED': return '⚠️';
			case 'ISSUE_RESOLVED': return '✅';
			case 'ESCALATION_OPENED': return '🚨';
			case 'ESCALATION_UPDATED': return '💬';
			case 'ESCALATION_RESOLVED': return '✅';
			default: return '📋';
		}
	};
	
	return (
		<div className="relative pl-6">
			{/* Timeline line */}
			<div className="absolute left-2 top-0 bottom-0 w-px bg-[var(--owlin-color-border)]" />
			
			<ul className="space-y-3">
				{events.map(ev => (
					<li key={ev.id} className="relative">
						{/* Timeline dot */}
						<div className="absolute -left-2 top-1 w-3 h-3 rounded-full border-2 bg-white border-[var(--owlin-color-border)]" />
						
						{/* Event card */}
						<div className={`border rounded-lg p-3 ${getSeverityColor(ev.severity)}`}>
							<div className="flex items-start gap-3">
								<div className="text-lg">{getEventIcon(ev.type)}</div>
								<div className="flex-1 min-w-0">
									<div className="text-xs text-[var(--owlin-color-muted)] mb-1">
										{new Date(ev.ts).toLocaleString()}
									</div>
									<div className="font-medium text-sm">{ev.title}</div>
									{ev.summary && (
										<div className="text-sm text-[var(--owlin-color-muted)] mt-1">
											{ev.summary}
										</div>
									)}
									{ev.severity !== 'info' && (
										<div className="text-xs mt-2">
											<span className={`px-2 py-1 rounded-full ${
												ev.severity === 'warn' 
													? 'bg-yellow-100 text-yellow-800' 
													: 'bg-red-100 text-red-800'
											}`}>
												{ev.severity === 'warn' ? 'Needs attention' : 'Critical'}
											</span>
										</div>
									)}
								</div>
							</div>
						</div>
					</li>
				))}
			</ul>
		</div>
	);
} 