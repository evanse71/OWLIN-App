import React, { useState } from 'react';

export default function LicenseVerifier(){
	const [uploading, setUploading] = useState(false);
	const [result, setResult] = useState<string|null>(null);
	
	async function handleFileUpload(event: React.ChangeEvent<HTMLInputElement>){
		const file = event.target.files?.[0];
		if(!file) return;
		
		setUploading(true);
		setResult(null);
		
		try{
			const formData = new FormData();
			formData.append('file', file);
			
			const res = await fetch('/api/recovery/license/upload', {
				method: 'POST',
				body: formData
			});
			
			const data = await res.json();
			setResult(data.message || 'License uploaded');
		}catch(e){
			setResult('Failed to upload license');
		}finally{
			setUploading(false);
		}
	}
	
	return (
		<div className="bg-white rounded-lg border border-[var(--owlin-color-border)] p-4">
			<div className="flex items-center gap-2 mb-3">
				<svg className="w-5 h-5 text-[var(--owlin-color-muted)]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"/>
				</svg>
				<div className="font-medium">License Verifier</div>
			</div>
			
			<div className="text-sm text-[var(--owlin-color-muted)] mb-3">
				Upload and verify license file
			</div>
			
			<input
				type="file"
				accept=".lic,.json"
				onChange={handleFileUpload}
				disabled={uploading}
				className="w-full px-3 py-2 border border-[var(--owlin-color-border)] rounded-lg disabled:opacity-50"
			/>
			
			{result && (
				<div className="mt-3 p-2 bg-blue-50 border border-blue-200 rounded text-sm">
					{result}
				</div>
			)}
		</div>
	);
} 