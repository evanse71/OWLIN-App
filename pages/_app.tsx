import '@/styles/globals.css';
import '@/styles/invoices-ux.css';
import type { AppProps } from 'next/app';
import { ToastProvider } from '@/utils/toast';
import { useEffect } from 'react';

function useDevAutoReset() {
  useEffect(() => {
    if (process.env.NODE_ENV !== 'development' && process.env.NEXT_PUBLIC_ENABLE_DEV_RESET !== 'true') return;
    if (typeof window === 'undefined') return;
    const key = 'owlin-dev-reset-run';
    if (sessionStorage.getItem(key)) return; // once per tab session
    sessionStorage.setItem(key, '1');
    fetch('/api/dev/clear-documents', { method: 'DELETE' }).catch(() => {});
  }, []);
}

export default function App({ Component, pageProps }: AppProps) {
  useDevAutoReset();
  return (
    <ToastProvider>
      <Component {...pageProps} />
    </ToastProvider>
  );
} 