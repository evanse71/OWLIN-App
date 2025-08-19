import React, { useEffect, useState } from 'react';

interface RecoveryStatus {
	active: boolean;
	reason?: string;
	activated_at?: string;
	activated_by?: string;
}

export default function RecoveryBanner() {
	const [status, setStatus] = useState<RecoveryStatus | null>(null);
	const [loading, setLoading] = useState(true);
	const [isAdmin, setIsAdmin] = useState(false);

	useEffect(() => {
		checkRecoveryStatus();
		// Check if user is admin (simplified - in real app this would come from auth context)
		setIsAdmin(true); // Assume admin for demo
	}, []);

	const checkRecoveryStatus = async () => {
		try {
			const response = await fetch('/api/recovery/status', {
				headers: {
					'X-Owlin-Session': 'demo-session',
					'X-Owlin-Venue': 'demo-venue'
				}
			});
			
			if (response.ok) {
				const data = await response.json();
				setStatus(data);
			}
		} catch (error) {
			console.error('Failed to check recovery status:', error);
		} finally {
			setLoading(false);
		}
	};

	const deactivateRecovery = async () => {
		try {
			const response = await fetch('/api/recovery/deactivate', {
				method: 'POST',
				headers: {
					'X-Owlin-Session': 'demo-session',
					'X-Owlin-Venue': 'demo-venue'
				}
			});
			
			if (response.ok) {
				await checkRecoveryStatus();
			}
		} catch (error) {
			console.error('Failed to deactivate recovery mode:', error);
		}
	};

	if (loading) {
		return null;
	}

	if (!status?.active) {
		return null;
	}

	return (
		<div className="fixed top-0 left-0 right-0 z-50 bg-red-600 text-white px-4 py-3 shadow-lg">
			<div className="max-w-7xl mx-auto flex items-center justify-between">
				<div className="flex items-center space-x-3">
					{/* Warning icon */}
					<svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
						<path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
					</svg>
					
					<div>
						<div className="font-semibold">Recovery Mode Active</div>
						{status.reason && (
							<div className="text-sm opacity-90">{status.reason}</div>
						)}
						{status.activated_at && (
							<div className="text-xs opacity-75">
								Activated: {new Date(status.activated_at).toLocaleString()}
							</div>
						)}
					</div>
				</div>
				
				{isAdmin && (
					<button
						onClick={deactivateRecovery}
						className="px-4 py-2 bg-white text-red-600 rounded-md font-medium hover:bg-gray-100 transition-colors"
					>
						Deactivate
					</button>
				)}
			</div>
		</div>
	);
} 