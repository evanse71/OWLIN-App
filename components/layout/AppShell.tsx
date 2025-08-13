import React from 'react';
import Link from 'next/link';
import { Card } from '@/components/ui/card';

interface AppShellProps {
  children: React.ReactNode;
}

export default function AppShell({ children }: AppShellProps) {
  return (
    <div className="min-h-screen bg-owlin-bg text-owlin-text">
      {/* Header */}
      <header className="sticky top-0 z-[var(--z-sticky)]">
        <div className="max-w-[1280px] mx-auto px-6 lg:px-8 py-3">
          <Card className="shadow-owlin flex items-center justify-between px-4 py-3">
            <div className="flex items-center gap-3">
              <span className="w-6 h-6 rounded-full bg-owlin-sapphire inline-block" />
              <span className="font-semibold">Owlin</span>
            </div>
            <nav className="flex items-center gap-3 text-sm">
              <Link href="/" className="px-3 py-1 rounded-owlin hover:bg-owlin-bg">Dashboard</Link>
              <Link href="/invoices" className="px-3 py-1 rounded-owlin hover:bg-owlin-bg">Invoices</Link>
              <Link href="/document-queue" className="px-3 py-1 rounded-owlin hover:bg-owlin-bg">Queue</Link>
              <Link href="/flagged" className="px-3 py-1 rounded-owlin hover:bg-owlin-bg">Flagged</Link>
            </nav>
          </Card>
        </div>
      </header>

      {/* Content Section */}
      <section className="max-w-[1280px] mx-auto px-6 lg:px-8 py-6">
        {children}
      </section>
    </div>
  );
} 