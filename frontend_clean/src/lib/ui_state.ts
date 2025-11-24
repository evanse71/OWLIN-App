/**
 * UI State Management Utilities
 * Handles selected invoice ID, dev mode, and deep-link synchronization
 */

/**
 * Parse invoice ID from hash (e.g., "#inv-123" -> "123")
 */
export function parseHash(hash: string): string | null {
  const match = hash.match(/^#inv-(.+)$/)
  return match ? match[1] : null
}

/**
 * Build hash from invoice ID (e.g., "123" -> "#inv-123")
 */
export function buildHash(id: string): string {
  return `#inv-${id}`
}

/**
 * Check if dev mode is enabled
 * Checks: query param ?dev=1, localStorage key owlin_dev=1
 */
export function isDevModeEnabled(): boolean {
  // Check query param
  const params = new URLSearchParams(window.location.search)
  if (params.get('dev') === '1') {
    return true
  }

  // Check localStorage
  try {
    return localStorage.getItem('owlin_dev') === '1'
  } catch {
    return false
  }
}

/**
 * Toggle dev mode
 * Sets localStorage and updates query param
 */
export function toggleDevMode(enabled: boolean): void {
  try {
    if (enabled) {
      localStorage.setItem('owlin_dev', '1')
    } else {
      localStorage.removeItem('owlin_dev')
    }
  } catch {
    // Ignore localStorage errors
  }

  // Update query param
  const url = new URL(window.location.href)
  if (enabled) {
    url.searchParams.set('dev', '1')
  } else {
    url.searchParams.delete('dev')
  }
  window.history.replaceState({}, '', url)
}

/**
 * Get selected invoice ID from hash
 */
export function getSelectedIdFromHash(): string | null {
  return parseHash(window.location.hash)
}

/**
 * Update hash with selected invoice ID
 */
export function setHashForId(id: string | null): void {
  if (id) {
    const newHash = buildHash(id)
    if (window.location.hash !== newHash) {
      window.history.replaceState({}, '', `${window.location.pathname}${window.location.search}${newHash}`)
    }
  } else {
    // Clear hash
    if (window.location.hash) {
      window.history.replaceState({}, '', `${window.location.pathname}${window.location.search}`)
    }
  }
}

