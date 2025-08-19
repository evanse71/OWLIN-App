import React, { useEffect, useState } from 'react';

interface ConflictListItem {
	id: string;
	table_name: string;
	conflict_type: 'schema' | 'row' | 'cell';
	detected_at: string;
	resolved: boolean;
	summary: string;
}

interface TableDiff {
	table_name: string;
	diff_type: 'schema' | 'row' | 'cell';
	html_diff: string;
	json_diff: any;
	summary: string;
}

export default function ConflictViewer() {
	const [conflicts, setConflicts] = useState<ConflictListItem[]>([]);
	const [selectedConflict, setSelectedConflict] = useState<TableDiff | null>(null);
	const [loading, setLoading] = useState(true);
	const [resolving, setResolving] = useState(false);

	useEffect(() => {
		loadConflicts();
	}, []);

	const loadConflicts = async () => {
		try {
			const response = await fetch('/api/conflicts?limit=50', {
				headers: {
					'X-Owlin-Session': 'demo-session',
					'X-Owlin-Venue': 'demo-venue'
				}
			});
			
			if (response.ok) {
				const data = await response.json();
				setConflicts(data);
			}
		} catch (error) {
			console.error('Failed to load conflicts:', error);
		} finally {
			setLoading(false);
		}
	};

	const loadConflictDiff = async (conflictId: string) => {
		try {
			const response = await fetch(`/api/conflicts/${conflictId}/diff`, {
				headers: {
					'X-Owlin-Session': 'demo-session',
					'X-Owlin-Venue': 'demo-venue'
				}
			});
			
			if (response.ok) {
				const data = await response.json();
				setSelectedConflict(data);
			}
		} catch (error) {
			console.error('Failed to load conflict diff:', error);
		}
	};

	const resolveConflict = async (conflictId: string, action: 'apply' | 'rollback' | 'ignore', notes?: string) => {
		setResolving(true);
		try {
			const response = await fetch(`/api/conflicts/${conflictId}/resolve`, {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
					'X-Owlin-Session': 'demo-session',
					'X-Owlin-Venue': 'demo-venue'
				},
				body: JSON.stringify({ action, notes })
			});
			
			if (response.ok) {
				await loadConflicts();
				setSelectedConflict(null);
			}
		} catch (error) {
			console.error('Failed to resolve conflict:', error);
		} finally {
			setResolving(false);
		}
	};

	const getConflictIcon = (type: string) => {
		switch (type) {
			case 'schema': return '🔧';
			case 'row': return '📋';
			case 'cell': return '📝';
			default: return '❓';
		}
	};

	const getConflictColor = (type: string) => {
		switch (type) {
			case 'schema': return 'bg-red-100 text-red-800 border-red-200';
			case 'row': return 'bg-yellow-100 text-yellow-800 border-yellow-200';
			case 'cell': return 'bg-blue-100 text-blue-800 border-blue-200';
			default: return 'bg-gray-100 text-gray-800 border-gray-200';
		}
	};

	if (loading) {
		return (
			<div className="flex items-center justify-center p-8">
				<div className="text-[var(--owlin-color-muted)]">Loading conflicts...</div>
			</div>
		);
	}

	return (
		<div className="space-y-6">
			{/* Header */}
			<div className="flex items-center justify-between">
				<h2 className="text-xl font-semibold">Database Conflicts</h2>
				<div className="text-sm text-[var(--owlin-color-muted)]">
					{conflicts.length} conflicts found
				</div>
			</div>

			{/* Conflict List */}
			<div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
				{/* Left panel - Conflict list */}
				<div className="space-y-3">
					<h3 className="font-medium text-[var(--owlin-color-muted)]">Detected Conflicts</h3>
					
					{conflicts.length === 0 ? (
						<div className="text-center py-8 text-[var(--owlin-color-muted)]">
							<div className="text-2xl mb-2">✅</div>
							<div>No conflicts detected</div>
						</div>
					) : (
						<div className="space-y-2">
							{conflicts.map(conflict => (
								<div
									key={conflict.id}
									className={`border rounded-lg p-3 cursor-pointer transition-colors ${
										selectedConflict?.table_name === conflict.table_name
											? 'border-[var(--owlin-color-accent)] bg-[var(--owlin-color-accent)]/5'
											: 'border-[var(--owlin-color-border)] hover:border-[var(--owlin-color-accent)]/50'
									}`}
									onClick={() => loadConflictDiff(conflict.id)}
								>
									<div className="flex items-start justify-between">
										<div className="flex items-center space-x-2">
											<span className="text-lg">{getConflictIcon(conflict.conflict_type)}</span>
											<div>
												<div className="font-medium">{conflict.table_name}</div>
												<div className="text-sm text-[var(--owlin-color-muted)]">
													{conflict.summary}
												</div>
											</div>
										</div>
										
										<div className="flex items-center space-x-2">
											<span className={`text-xs px-2 py-1 rounded-full border ${getConflictColor(conflict.conflict_type)}`}>
												{conflict.conflict_type}
											</span>
											{conflict.resolved && (
												<span className="text-xs px-2 py-1 rounded-full bg-green-100 text-green-800 border border-green-200">
													Resolved
												</span>
											)}
										</div>
									</div>
									
									<div className="text-xs text-[var(--owlin-color-muted)] mt-2">
										{new Date(conflict.detected_at).toLocaleString()}
									</div>
								</div>
							))}
						</div>
					)}
				</div>

				{/* Right panel - Conflict details */}
				<div className="space-y-3">
					<h3 className="font-medium text-[var(--owlin-color-muted)]">Conflict Details</h3>
					
					{selectedConflict ? (
						<div className="space-y-4">
							{/* Conflict summary */}
							<div className="bg-white border border-[var(--owlin-color-border)] rounded-lg p-4">
								<div className="flex items-center justify-between mb-3">
									<h4 className="font-medium">{selectedConflict.table_name}</h4>
									<span className={`text-xs px-2 py-1 rounded-full border ${getConflictColor(selectedConflict.diff_type)}`}>
										{selectedConflict.diff_type}
									</span>
								</div>
								<div className="text-sm text-[var(--owlin-color-muted)]">
									{selectedConflict.summary}
								</div>
							</div>

							{/* HTML Diff */}
							<div className="bg-white border border-[var(--owlin-color-border)] rounded-lg p-4">
								<h4 className="font-medium mb-3">Diff View</h4>
								<div 
									className="prose prose-sm max-w-none"
									dangerouslySetInnerHTML={{ __html: selectedConflict.html_diff }}
								/>
							</div>

							{/* Action buttons */}
							<div className="bg-white border border-[var(--owlin-color-border)] rounded-lg p-4">
								<h4 className="font-medium mb-3">Actions</h4>
								<div className="flex space-x-2">
									<button
										onClick={() => resolveConflict(selectedConflict.table_name, 'apply')}
										disabled={resolving}
										className="px-3 py-2 bg-green-600 text-white rounded-md text-sm font-medium hover:bg-green-700 disabled:opacity-50"
									>
										Apply Fix
									</button>
									<button
										onClick={() => resolveConflict(selectedConflict.table_name, 'rollback')}
										disabled={resolving}
										className="px-3 py-2 bg-blue-600 text-white rounded-md text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
									>
										Rollback
									</button>
									<button
										onClick={() => resolveConflict(selectedConflict.table_name, 'ignore')}
										disabled={resolving}
										className="px-3 py-2 bg-gray-600 text-white rounded-md text-sm font-medium hover:bg-gray-700 disabled:opacity-50"
									>
										Ignore
									</button>
								</div>
							</div>
						</div>
					) : (
						<div className="text-center py-8 text-[var(--owlin-color-muted)]">
							<div className="text-2xl mb-2">📋</div>
							<div>Select a conflict to view details</div>
						</div>
					)}
				</div>
			</div>
		</div>
	);
} 