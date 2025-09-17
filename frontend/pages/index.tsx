import { useRouter } from 'next/router';
import { useEffect } from 'react';

export default function Home() {
  const router = useRouter();

  useEffect(() => {
    // Redirect to invoices page
    router.push('/invoices');
  }, [router]);

  return (
    <div className="flex items-center justify-center min-h-screen">
      <div className="text-center">
        <h1 className="text-2xl font-bold mb-4">Owlin App</h1>
        <p className="text-gray-600">Redirecting to invoices...</p>
      </div>
    </div>
  );
}
