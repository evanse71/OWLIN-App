// src/lib/featureFlags.ts
export const FRONTEND_FEATURE_OCR_V2 =
  (import.meta as any)?.env?.VITE_FEATURE_OCR_V2 === 'true' ||
  (typeof process !== 'undefined' && process.env?.NEXT_PUBLIC_FEATURE_OCR_V2 === 'true');

export const API_BASE_URL: string =
  (import.meta as any)?.env?.VITE_API_BASE_URL ||
  (typeof process !== 'undefined' && (process.env?.NEXT_PUBLIC_API_BASE_URL ?? 'http://127.0.0.1:8000')) ||
  'http://127.0.0.1:8000';
