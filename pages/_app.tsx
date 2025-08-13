import '@/styles/globals.css';
import '@/styles/invoices-ux.css';
import type { AppProps } from 'next/app';
import { ToastProvider } from '@/utils/toast';
import { useEffect } from 'react';

function useDevAutoReset() {
  useEffect(() => {
    if (process.env.NODE_ENV !== 'development') return;
    if (typeof window === 'undefined') return;
    const reset = async () => {
      try {
        await fetch('/api/dev/clear-documents', { method: 'DELETE', cache: 'no-store' });
      } catch {
        // ... existing code ...
      }
    };
    reset();
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