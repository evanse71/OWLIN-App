import React, { useState } from 'react';

type FieldDiff = { column: string; old: any; new: any; decision: 'keep_old' | 'use_new' | 'manual' };
type RowDiff = { table: string; pk: string; diffs: FieldDiff[] };

export default function ConflictResolver(){
	const [diff, setDiff] = useState<{rows: RowDiff[], summary: any}|null>(null);
	const [busy, setBusy] = useState(false);
	
	async function dryRun(){
		setBusy(true);
		try {
			const res = await fetch('/api/recovery/restore/dry-run', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ backup_id: '00000000-0000-0000-0000-000000000001' })
			});
			const data = await res.json();
			setDiff(data);
		} catch(e) {
			console.error('Dry run failed:', e);
		} finally {
			setBusy(false);
		}
	}
	
	async function apply(){
		if(!diff) return;
		
		setBusy(true);
		try {
			const res = await fetch('/api/recovery/restore/apply', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify(diff)
			});
			const data = await res.json();
			if(data.ok) {
				setDiff(null);
			}
		} catch(e) {
			console.error('Apply failed:', e);
		} finally {
			setBusy(false);
		}
	}
	
	return (
		<div className="bg-white rounded-lg border border-[var(--owlin-color-border)] p-4">
			<div className="flex items-center justify-between mb-3">
				<div className="flex items-center gap-2">
					<svg className="w-5 h-5 text-[var(--owlin-color-muted)]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path d="M7 3v6a5 5 0 0 0 5 5h5"/>
						<path d="M3 7h6"/>
						<path d="M14 16l3 3 3-3"/>
					</svg>
					<div className="font-medium">Conflict Resolver</div>
				</div>
				<button 
					onClick={dryRun}
					disabled={busy}
					className="px-3 py-1 bg-[var(--owlin-color-accent)] text-white rounded text-sm hover:brightness-110 disabled:opacity-50"
				>
					{!diff ? 'Dry Run' : 'Refresh'}
				</button>
			</div>
			
			{!diff && (
				<div className="text-[var(--owlin-color-muted)] text-sm">Run a dry-run to view conflicts.</div>
			)}
			
			{diff && (
				<div className="space-y-3">
					<div className="text-sm text-[var(--owlin-color-muted)]">
						Rows: {diff.summary.rows} • Fields: {diff.summary.fields}
					</div>
					
					{diff.rows.map((r, idx) => (
						<div key={idx} className="border border-[var(--owlin-color-border)] rounded p-3">
							<div className="font-medium mb-2">{r.table} • PK={r.pk}</div>
							<div className="grid grid-cols-3 gap-2 text-sm">
								<div className="text-[var(--owlin-color-muted)]">Column</div>
								<div className="text-[var(--owlin-color-muted)]">Current</div>
								<div className="text-[var(--owlin-color-muted)]">Backup</div>
								{r.diffs.map((f, i) => (
									<React.Fragment key={i}>
										<div className="py-1">{f.column}</div>
										<div className="py-1">{String(f.old ?? '—')}</div>
										<div className="py-1">{String(f.new ?? '—')}</div>
									</React.Fragment>
								))}
							</div>
							<div className="mt-2 flex gap-2 justify-end">
								<button 
									onClick={() => {
										r.diffs.forEach(d => d.decision = 'keep_old');
										setDiff({...diff});
									}}
									className="px-2 py-1 border border-[var(--owlin-color-border)] rounded text-sm hover:bg-gray-50"
								>
									Keep Current
								</button>
								<button 
									onClick={() => {
										r.diffs.forEach(d => d.decision = 'use_new');
										setDiff({...diff});
									}}
									className="px-2 py-1 bg-[var(--owlin-color-accent)] text-white rounded text-sm hover:brightness-110"
								>
									Use Backup
								</button>
							</div>
						</div>
					))}
					
					<div className="flex justify-end">
						<button 
							onClick={apply}
							disabled={busy}
							className="px-4 py-2 bg-[var(--owlin-color-accent)] text-white rounded hover:brightness-110 disabled:opacity-50"
						>
							{busy ? 'Applying...' : 'Apply'}
						</button>
					</div>
				</div>
			)}
		</div>
	);
} 