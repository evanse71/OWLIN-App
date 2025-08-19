import React from 'react';
import { useRouter } from 'next/router';
import InsightsPanel from '@/components/insights/InsightsPanel';
import '@/styles/globals.css';

export default function SupplierInsightsPage() {
	const router = useRouter(); const { id } = router.query as { id?: string };
	if (!id) return null;
	return (
		<main className="max-w-[1200px] mx-auto p-4">
			<h1 className="text-xl font-semibold mb-3">Supplier Insights</h1>
			<InsightsPanel supplierId={id} />
		</main>
	);
} 