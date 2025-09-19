// frontend/pages/index.tsx
import React from "react";
import Link from "next/link";

export default function HomePage() {
  return (
    <main className="p-6">
      <h1 className="text-2xl font-semibold">Owlin</h1>
      <p className="mt-2 text-gray-600">Local-first invoice + delivery notes.</p>
      <div className="mt-4 space-x-3">
        <Link className="underline" href="/invoices">Go to Invoices</Link>
      </div>
    </main>
  );
}