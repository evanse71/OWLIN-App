/**
 * API configuration
 * In dev mode (Vite dev server), use relative URLs to leverage proxy
 * In production, use VITE_API_BASE_URL or default to same origin (backend serves frontend)
 * 
 * Note: For single-port setup (backend serves frontend on port 5177), relative URLs work correctly
 * as the frontend and API are served from the same origin.
 */
export const API_BASE_URL = import.meta.env.DEV
  ? '' // Use relative URLs in dev mode (works with single-port setup where backend serves frontend)
  : (import.meta.env.VITE_API_BASE_URL || '') // Empty = same origin (backend on 5177 serves both)

