"use client";
import { useEffect } from "react";

export default function DashboardError({ error, reset }: { error: Error; reset: () => void }) {
  useEffect(() => {
    // Optional: send to logs
    console.error('Dashboard Error:', error);
  }, [error]);

  return (
    <div className="min-h-screen bg-[hsl(var(--ow-bg))] p-6">
      <div className="max-w-[1400px] mx-auto">
        <div className="text-center py-8">
          <h2 className="text-lg font-semibold text-[hsl(var(--ow-ink))] mb-2">
            Something went wrong on the Dashboard.
          </h2>
          <p className="mb-4 opacity-80 text-[hsl(var(--ow-ink-dim))]">
            {error?.message ?? "Unexpected error."}
          </p>
          <button
            onClick={() => reset()}
            className="rounded-lg px-3 py-2 border bg-[hsl(var(--ow-accent))] text-white hover:bg-[hsl(var(--ow-accent))]/90"
          >
            Try again
          </button>
        </div>
      </div>
    </div>
  );
}
