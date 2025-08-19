import React from 'react';
import RoleMatrix from '@/components/rbac/RoleMatrix';

export default function RolesPage(){ 
	return (
		<main className="max-w-[1200px] mx-auto p-4">
			<h1 className="text-xl font-semibold mb-4">Role Management</h1>
			<RoleMatrix/>
		</main>
	);
} 