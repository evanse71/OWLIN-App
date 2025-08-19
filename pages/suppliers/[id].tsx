import React, { useEffect, useState } from 'react';
import { useRouter } from 'next/router';
import SupplierScorecard from '../../frontend/components/suppliers/SupplierScorecard';

export default function SupplierPage(){
	const router = useRouter();
	const { id } = router.query as { id?: string };
	if (!id) return <div className="min-h-screen bg-[#F8F9FB] font-[Inter] text-[#1F2937]"><div className="max-w-[1100px] mx-auto px-4 sm:px-6 lg:px-8 py-6">Loading...</div></div>;
	return (
		<div className="min-h-screen bg-[#F8F9FB] font-[Inter] text-[#1F2937]">
			<div className="max-w-[1100px] mx-auto px-4 sm:px-6 lg:px-8 py-6">
				<div className="grid grid-cols-1 lg:grid-cols-[1.3fr_1fr] gap-6 lg:gap-8">
					<div className="flex flex-col gap-6">
						<SupplierScorecard supplierId={id} />
					</div>
					<div className="flex flex-col gap-6">
						{/* Right column reserved for activity lists */}
					</div>
				</div>
			</div>
		</div>
	);
} 