import React, { useEffect, useState } from 'react';

export default function UserAssignments(){
	const [users, setUsers] = useState<any[]>([]);
	const [venues, setVenues] = useState<any[]>([]);
	const [roles, setRoles] = useState<any[]>([]);
	
	async function load(){
		try {
			const usersRes = await fetch('/api/users', { cache: 'no-store' });
			setUsers(await usersRes.json());
			
			const venuesRes = await fetch('/api/users/venues', { cache: 'no-store' });
			setVenues(await venuesRes.json());
			
			const rolesRes = await fetch('/api/roles', { cache: 'no-store' });
			setRoles(await rolesRes.json());
		} catch(e) {
			console.error('Failed to load data:', e);
		}
	}
	
	useEffect(()=>{ load(); }, []);
	
	async function assign(userId: string, roleId: string, venueId: string){
		try {
			await fetch('/api/assignments', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ user_id: userId, role_id: roleId, venue_id: venueId })
			});
			await load();
		} catch(e) {
			console.error('Failed to assign role:', e);
		}
	}
	
	return (
		<div className="bg-white rounded-lg border border-[var(--owlin-color-border)] p-4 space-y-3">
			<div className="font-semibold">User Assignments</div>
			{users.map(u => (
				<div key={u.id} className="p-3 border rounded-lg border-[var(--owlin-color-border)]">
					<div className="font-medium mb-2">
						{u.display_name} 
						<span className="text-[var(--owlin-color-muted)]">({u.email})</span>
					</div>
					<div className="grid grid-cols-1 md:grid-cols-3 gap-2">
						{venues.map(v => (
							<div key={v.id} className="p-2 rounded bg-[var(--owlin-color-bg)]">
								<div className="text-sm font-medium">{v.name}</div>
								<div className="mt-1 flex flex-wrap gap-1">
									{roles.map(r => (
										<button 
											key={r.id} 
											onClick={() => assign(u.id, r.id, v.id)}
											className="text-xs border rounded px-2 py-1 hover:bg-[var(--owlin-color-accent)] hover:text-white transition-colors"
										>
											{r.name}
										</button>
									))}
								</div>
							</div>
						))}
					</div>
				</div>
			))}
		</div>
	);
} 