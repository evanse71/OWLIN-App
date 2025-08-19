import React from 'react';
import Link from 'next/link';
import { useRouter } from 'next/router';
import { Search } from 'lucide-react';

interface AppShellProps {
  children: React.ReactNode;
}

const nav = [
  { href: '/', label: 'Dashboard', emoji: '🏠' },
  { href: '/invoices', label: 'Invoices', emoji: '📄' },
  { href: '/document-queue', label: 'Document Queue', emoji: '📋' },
  { href: '/flagged', label: 'Flagged Issues', emoji: '⚠️' },
  { href: '/suppliers', label: 'Suppliers', emoji: '🏢' },
  { href: '/product-trends', label: 'Product Trends', emoji: '📈' },
  { href: '/settings', label: 'Settings', emoji: '⚙️' },
  { href: '/diagnostics/ocr', label: 'OCR Diagnostics', emoji: '🩺' },
];

export default function AppShell({ children }: AppShellProps) {
  const router = useRouter();
  const isActive = (href: string) => router.pathname.startsWith(href === '/' ? '/' : href);

  return (
    <div className="min-h-screen bg-owlin-bg text-owlin-text">
      <div className="flex w-full min-h-screen">
        {/* Sidebar */}
        <aside 
          className="hidden md:flex md:flex-col w-[240px] shrink-0 border-r border-owlin-stroke bg-[color-mix(in_oklab,var(--owlin-card)_92%,transparent)]"
          data-ui="sidebar"
        >
          <div className="h-14 px-4 flex items-center gap-2 border-b border-owlin-stroke">
            <span className="w-6 h-6 rounded-full bg-owlin-sapphire inline-block" />
            <span className="font-semibold">Owlin</span>
          </div>
          <nav className="p-2 space-y-1">
            {nav.map(item => (
              <Link
                key={item.href}
                href={item.href}
                className={`flex items-center gap-2 px-3 py-2 rounded-owlin text-sm transition-colors ${
                  isActive(item.href)
                    ? 'bg-owlin-bg text-owlin-text'
                    : 'text-owlin-muted hover:bg-owlin-bg'
                }`}
              >
                <span className="text-base" aria-hidden>{item.emoji}</span>
                <span>{item.label}</span>
              </Link>
            ))}
          </nav>
        </aside>

        {/* Main area */}
        <div className="flex-1 flex flex-col min-w-0">
          {/* Top header */}
          <header className="sticky top-0 z-[var(--z-sticky)] border-b border-owlin-stroke bg-[color-mix(in_oklab,var(--owlin-card)_96%,transparent)]/90 backdrop-blur">
            <div className="h-14 px-4 md:px-6 flex items-center justify-between">
              <div className="font-semibold truncate">
                {/* Page title derived from route */}
                {nav.find(n => n.href !== '/' && router.pathname.startsWith(n.href))?.label || 'Dashboard'}
              </div>
              <div className="flex items-center gap-2">
                <div className="hidden md:flex items-center gap-2 px-3 py-1.5 rounded-owlin border border-owlin-stroke bg-owlin-card">
                  <Search className="w-4 h-4 text-owlin-muted" />
                  <input
                    className="bg-transparent outline-none text-sm placeholder:text-owlin-muted"
                    placeholder="Search…"
                    aria-label="Search"
                  />
                </div>
              </div>
            </div>
          </header>

          {/* Content */}
          <main className="px-4 md:px-6 py-4 md:py-6">
            {children}
          </main>
        </div>
      </div>
    </div>
  );
} 