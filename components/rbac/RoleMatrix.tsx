import React, { useEffect, useState } from 'react';

export default function RoleMatrix(){
	const [roles, setRoles] = useState<any[]>([]);
	const [perms, setPerms] = useState<string[]>([]);
	const [saving, setSaving] = useState(false);
	
	async function load(){
		try {
			const r = await fetch('/api/roles', { cache: 'no-store' });
			const rolesData = await r.json();
			setRoles(rolesData);
			
			const p = await fetch('/api/roles/permissions', { cache: 'no-store' });
			const permsData = await p.json();
			setPerms(permsData.map((x: any) => x.code) ?? []);
		} catch(e) {
			console.error('Failed to load roles/permissions:', e);
		}
	}
	
	useEffect(()=>{ load(); }, []);
	
	async function toggle(roleId: string, perm: string){
		setSaving(true);
		try {
			const role = roles.find((r: any) => r.id === roleId);
			const has = role.permissions.some((p: any) => p.code === perm);
			const next = has ? 
				role.permissions.filter((p: any) => p.code !== perm) : 
				[...role.permissions, {code: perm, description: ''}];
			
			const payload = { 
				id: role.id, 
				name: role.name, 
				description: role.description, 
				permissions: next.map((p: any) => p.code) 
			};
			
			const res = await fetch(`/api/roles/${role.id}`, {
				method: 'PATCH',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify(payload)
			});
			const updatedRole = await res.json();
			setRoles(roles.map((r: any) => r.id === role.id ? updatedRole : r));
		} catch(e) {
			console.error('Failed to toggle permission:', e);
		} finally { 
			setSaving(false); 
		}
	}
	
	return (
		<div className="bg-white rounded-lg border border-[var(--owlin-color-border)] p-4">
			<div className="font-semibold mb-3">Roles & Permissions</div>
			<div className="overflow-auto">
				<table className="text-sm">
					<thead>
						<tr>
							<th className="text-left pr-4 py-2">Role</th>
							{perms.map(p => (
								<th key={p} className="px-3 py-2 text-left text-[var(--owlin-color-muted)]">
									{p.replace('.', ' ')}
								</th>
							))}
						</tr>
					</thead>
					<tbody>
						{roles.map((r: any) => (
							<tr key={r.id} className="border-t border-[var(--owlin-color-border)]">
								<td className="pr-4 py-2">{r.name}</td>
								{perms.map(p => {
									const has = r.permissions.some((x: any) => x.code === p);
									return (
										<td key={p} className="px-3 py-2">
											<button 
												onClick={() => toggle(r.id, p)}
												disabled={saving}
												className={`w-4 h-4 rounded border ${
													has ? 'bg-[var(--owlin-color-accent)] border-[var(--owlin-color-accent)]' : 
													'bg-white border-[var(--owlin-color-border)]'
												} disabled:opacity-50`}
											/>
										</td>
									);
								})}
							</tr>
						))}
					</tbody>
				</table>
			</div>
		</div>
	);
} 