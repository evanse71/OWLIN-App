import React, { useState } from 'react';

export default function SupportPack(){
	const [creating, setCreating] = useState(false);
	const [result, setResult] = useState<string|null>(null);
	
	async function createSupportPack(){
		setCreating(true);
		setResult(null);
		try{
			const res = await fetch('/api/recovery/support-pack', { 
				method: 'POST',
				cache: 'no-store' 
			});
			const data = await res.json();
			setResult(data.message || 'Support pack created');
		}catch(e){
			setResult('Failed to create support pack');
		}finally{
			setCreating(false);
		}
	}
	
	return (
		<div className="bg-white rounded-lg border border-[var(--owlin-color-border)] p-4">
			<div className="flex items-center gap-2 mb-3">
				<svg className="w-5 h-5 text-[var(--owlin-color-muted)]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>
				</svg>
				<div className="font-medium">Support Pack</div>
			</div>
			
			<div className="text-sm text-[var(--owlin-color-muted)] mb-3">
				Export database, audit logs, and license for support
			</div>
			
			<button 
				onClick={createSupportPack}
				disabled={creating}
				className="w-full px-3 py-2 bg-[var(--owlin-color-accent)] text-white rounded-lg hover:brightness-110 disabled:opacity-50"
			>
				{creating ? 'Creating...' : 'Create Support Pack'}
			</button>
			
			{result && (
				<div className="mt-3 p-2 bg-green-50 border border-green-200 rounded text-sm">
					{result}
				</div>
			)}
		</div>
	);
} 