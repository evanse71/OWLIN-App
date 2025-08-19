import React from 'react';
import Link from 'next/link';
import { useRouter } from 'next/router';

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

export default function Sidebar() {
  const router = useRouter();
  const isActive = (href: string) => router.pathname.startsWith(href === '/' ? '/' : href);

  return (
    <aside className="hidden md:flex md:flex-col w-[240px] shrink-0 border-r border-owlin-stroke bg-[color-mix(in_oklab,var(--owlin-card)_92%,transparent)]">
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
  );
} 