import React from 'react';
import { fetchJSON } from '@/lib/api';
import { useRouter } from 'next/router';

type SupplierScorecard = {
  supplier: string;
  invoices: number;
  spend: number;
  avg_ocr: number;
  mismatch_rate: number;
  volatility: number;
};

type SuppliersData = {
  items: SupplierScorecard[];
};

export default function SuppliersPage() {
  const [suppliers, setSuppliers] = React.useState<SupplierScorecard[]>([]);
  const [loading, setLoading] = React.useState(true);
  const router = useRouter();

  const loadData = React.useCallback(async () => {
    try {
      setLoading(true);
      const data = await fetchJSON<SuppliersData>('/api/suppliers/scorecards');
      setSuppliers(data.items);
    } catch (error) {
      console.error('Failed to load suppliers data:', error);
    } finally {
      setLoading(false);
    }
  }, []);

  React.useEffect(() => {
    loadData();
  }, [loadData]);

  const handleSupplierClick = (supplier: string) => {
    // Deep-link to invoices filtered by supplier
    router.push(`/invoices?supplier=${encodeURIComponent(supplier)}`);
  };

  if (loading) {
    return (
      <div className="p-6">
        <div className="text-center">Loading suppliers...</div>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6">
      <h1 className="text-2xl font-bold">Suppliers</h1>
      
      {suppliers.length === 0 ? (
        <div className="text-center py-8">
          <p className="text-gray-500">No suppliers found.</p>
        </div>
      ) : (
        <div className="grid gap-4">
          {suppliers.map((supplier, index) => (
            <div
              key={supplier.supplier}
              className="bg-white p-6 rounded-lg border shadow-sm hover:shadow-md transition-shadow cursor-pointer"
              onClick={() => handleSupplierClick(supplier.supplier)}
            >
              <div className="flex items-center justify-between">
                <div className="flex-1">
                  <h3 className="text-lg font-semibold text-gray-900">
                    {supplier.supplier}
                  </h3>
                  <div className="mt-2 grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                    <div>
                      <span className="text-gray-500">Invoices:</span>
                      <span className="ml-2 font-medium">{supplier.invoices}</span>
                    </div>
                    <div>
                      <span className="text-gray-500">Spend:</span>
                      <span className="ml-2 font-medium text-green-600">
                        ${supplier.spend.toLocaleString()}
                      </span>
                    </div>
                    <div>
                      <span className="text-gray-500">Avg OCR:</span>
                      <span className="ml-2 font-medium">{supplier.avg_ocr.toFixed(1)}%</span>
                    </div>
                    <div>
                      <span className="text-gray-500">Mismatch Rate:</span>
                      <span className="ml-2 font-medium">{supplier.mismatch_rate.toFixed(1)}%</span>
                    </div>
                  </div>
                </div>
                <div className="text-right">
                  <div className="text-sm text-gray-500">Volatility</div>
                  <div className="text-lg font-semibold">{supplier.volatility.toFixed(1)}%</div>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
