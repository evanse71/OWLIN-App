/**
 * API configuration
 * In dev mode, use relative URLs (let Vite proxy handle it) or detect current host
 * In production, use VITE_API_BASE_URL from environment, defaulting to http://127.0.0.1:8000
 */
function getApiBaseUrl(): string {
  // If explicitly set in env, use it
  if (import.meta.env.VITE_API_BASE_URL) {
    return import.meta.env.VITE_API_BASE_URL
  }
  
  // In dev mode (Vite), use relative URLs to leverage the proxy
  // This works when accessing from remote machines (192.168.x.x)
  if (import.meta.env.DEV) {
    // Use empty string for relative URLs - Vite proxy will handle /api/* requests
    return ''
  }
  
  // Production fallback
  return "http://127.0.0.1:8000"
}

export const API_BASE_URL = getApiBaseUrl()

