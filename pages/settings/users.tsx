import React from 'react';
import UserAssignments from '@/components/rbac/UserAssignments';

export default function UsersPage(){ 
	return (
		<main className="max-w-[1200px] mx-auto p-4 space-y-3">
			<h1 className="text-xl font-semibold mb-4">User Management</h1>
			<UserAssignments/>
		</main>
	);
} 