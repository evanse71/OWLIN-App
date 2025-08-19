import React from 'react';
import RecoveryBanner from '@/components/recovery/RecoveryBanner';
import ConflictViewer from '@/components/recovery/ConflictViewer';

export default function RecoveryPage() {
	return (
		<>
			<RecoveryBanner />
			<main className="max-w-7xl mx-auto p-4 pt-20">
				<div className="space-y-6">
					{/* Page header */}
					<div className="border-b border-[var(--owlin-color-border)] pb-4">
						<h1 className="text-2xl font-semibold">Recovery & Conflict Resolution</h1>
						<p className="text-[var(--owlin-color-muted)] mt-1">
							Monitor database integrity and resolve conflicts
						</p>
					</div>

					{/* Conflict viewer */}
					<ConflictViewer />
				</div>
			</main>
		</>
	);
} 