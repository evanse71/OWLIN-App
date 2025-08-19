import React from 'react';

export default function RoleBadge({ role, onClick }: { role: string; onClick?: () => void }){
	return (
		<div 
			className={`inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs ${
				onClick ? 
					'bg-[var(--owlin-color-accent)] text-white cursor-pointer hover:brightness-110' :
					'bg-[var(--owlin-color-bg)] text-[var(--owlin-color-muted)]'
			}`}
			onClick={onClick}
		>
			<svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
				<rect x="3" y="11" width="18" height="10" rx="2"/>
				<path d="M7 11V7a5 5 0 0 1 10 0v4"/>
			</svg>
			<span>{role}</span>
		</div>
	);
} 