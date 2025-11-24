/**
 * Centralized API configuration - single source of truth
 * Works in both Next.js (process.env.NEXT_PUBLIC_*) and Vite (import.meta.env.VITE_*)
 */

// Safe import.meta access for Vite environments
let viteEnv: any = undefined;
try {
  // Guard: import.meta is undefined on Next/SSR
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  viteEnv = (import.meta as any)?.env;
} catch {
  // import.meta not available (Next.js SSR)
}

const getApiBaseUrl = (): string => {
  // Priority order:
  // 1. NEXT_PUBLIC_API_BASE_URL (Next.js)
  // 2. VITE_API_BASE_URL (Vite)
  // 3. Runtime injector (optional)
  // 4. Browser location with port replacement
  // 5. Default fallback

  // Next.js environment variable
  const nextPublic = typeof process !== "undefined" ? process.env.NEXT_PUBLIC_API_BASE_URL : undefined;
  if (nextPublic) {
    return nextPublic.replace(/\/$/, '');
  }

  // Vite environment variable
  if (viteEnv?.VITE_API_BASE_URL) {
    return viteEnv.VITE_API_BASE_URL.replace(/\/$/, '');
  }

  // Runtime injector (optional)
  if (typeof globalThis !== 'undefined' && (globalThis as any).__OWLIN_API_BASE_URL__) {
    return (globalThis as any).__OWLIN_API_BASE_URL__.replace(/\/$/, '');
  }

  // Client-side: use browser location
  if (typeof window !== 'undefined') {
    const origin = window.location.origin;
    if (origin.includes(':3000')) return origin.replace(':3000', ':8000');
    if (origin.includes(':3001')) return origin.replace(':3001', ':8000');
    if (origin.includes(':3002')) return origin.replace(':3002', ':8000');
    if (origin.includes(':3003')) return origin.replace(':3003', ':8000');
    if (origin.includes(':5173')) return origin.replace(':5173', ':8000');
    return origin; // Fallback to current origin
  }

  // Server-side or fallback
  return 'http://127.0.0.1:8000';
};

export const API_BASE_URL = getApiBaseUrl();
export const API_BASE_URL_WITH_PREFIX = `${API_BASE_URL}/api`;

// Health check function
export async function pingAPI(): Promise<boolean> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/health`, {
      cache: 'no-store',
      signal: AbortSignal.timeout(5000) // 5 second timeout
    });
    return response.ok;
  } catch (error) {
    console.error('Health check failed:', error);
    return false;
  }
}

// Centralized upload function with enhanced error handling
export async function uploadDocument(file: File): Promise<any> {
  const formData = new FormData();
  formData.append('file', file); // Ensure field name matches FastAPI parameter

  const isHealthy = await pingAPI();
  if (!isHealthy) {
    throw new Error('Backend unreachable. Check that the server is running on ' + API_BASE_URL);
  }

  try {
    const response = await fetch(`${API_BASE_URL_WITH_PREFIX}/upload`, {
      method: 'POST',
      body: formData,
      signal: AbortSignal.timeout(120000) // 2 minute timeout for uploads
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`Upload failed (${response.status}): ${errorText}`);
    }
    return response.json();
  } catch (error: any) {
    if (error instanceof Error && error.name === 'AbortError') {
      throw new Error('Upload timed out after 2 minutes');
    }
    if (error instanceof TypeError && error.message.includes('fetch')) {
      throw new Error(`Backend unreachable at ${API_BASE_URL}. Check server and .env configuration.`);
    }
    throw error;
  }
}

// Development logging
if (process.env.NODE_ENV !== 'production') {
  console.info('[API Config] Base URL:', API_BASE_URL);
  console.info('[API Config] Full API URL:', API_BASE_URL_WITH_PREFIX);
  console.info('[API Config] Environment:', process.env.VITE_API_BASE_URL ? 'VITE_API_BASE_URL set' : 'Using fallback');
}
