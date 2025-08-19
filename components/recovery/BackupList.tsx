import React, { useEffect, useState } from 'react';

export default function BackupList(){
	const [backups, setBackups] = useState<any[]>([]);
	const [loading, setLoading] = useState(true);
	
	useEffect(()=>{
		async function loadBackups(){
			try{
				const res = await fetch('/api/recovery/backups', { cache: 'no-store' });
				const data = await res.json();
				setBackups(data);
			}catch(e){
				console.error('Failed to load backups:', e);
			}finally{
				setLoading(false);
			}
		}
		loadBackups();
	}, []);
	
	function formatBytes(bytes: number): string {
		if(bytes === 0) return '0 Bytes';
		const k = 1024;
		const sizes = ['Bytes', 'KB', 'MB', 'GB'];
		const i = Math.floor(Math.log(bytes) / Math.log(k));
		return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
	}
	
	return (
		<div className="bg-white rounded-lg border border-[var(--owlin-color-border)] p-4">
			<div className="flex items-center gap-2 mb-3">
				<svg className="w-5 h-5 text-[var(--owlin-color-muted)]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<ellipse cx="12" cy="5" rx="8" ry="3"/>
					<path d="M4 5v6c0 1.66 3.58 3 8 3s8-1.34 8-3V5M4 11v6c0 1.66 3.58 3 8 3s8-1.34 8-3v-6"/>
				</svg>
				<div className="font-medium">Backups</div>
			</div>
			
			{loading ? (
				<div className="text-sm text-[var(--owlin-color-muted)]">Loading...</div>
			) : backups.length === 0 ? (
				<div className="text-sm text-[var(--owlin-color-muted)]">No backups found</div>
			) : (
				<div className="space-y-2">
					{backups.slice(0, 5).map((backup, i) => (
						<div key={i} className="flex items-center justify-between text-sm p-2 bg-gray-50 rounded">
							<div>
								<div className="font-medium">{backup.name}</div>
								<div className="text-[var(--owlin-color-muted)]">
									{new Date(backup.created_at).toLocaleDateString()}
								</div>
							</div>
							<div className="text-[var(--owlin-color-muted)]">
								{formatBytes(backup.size_bytes)}
							</div>
						</div>
					))}
				</div>
			)}
		</div>
	);
} 