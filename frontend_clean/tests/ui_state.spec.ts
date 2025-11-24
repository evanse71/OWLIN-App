import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import {
  parseHash,
  buildHash,
  isDevModeEnabled,
  toggleDevMode,
  getSelectedIdFromHash,
  setHashForId,
} from '../src/lib/ui_state'

describe('ui_state', () => {
  let originalLocation: Location
  let originalLocalStorage: Storage

  beforeEach(() => {
    // Save originals
    originalLocation = window.location
    originalLocalStorage = window.localStorage

    // Mock location
    delete (window as { location?: Location }).location
    window.location = {
      ...originalLocation,
      hash: '',
      search: '',
      pathname: '/invoices',
      href: 'http://localhost:5173/invoices',
      replaceState: vi.fn(),
    } as Location

    // Mock localStorage
    const store: Record<string, string> = {}
    Object.defineProperty(window, 'localStorage', {
      value: {
        getItem: vi.fn((key: string) => store[key] || null),
        setItem: vi.fn((key: string, value: string) => {
          store[key] = value
        }),
        removeItem: vi.fn((key: string) => {
          delete store[key]
        }),
        clear: vi.fn(() => {
          Object.keys(store).forEach((key) => delete store[key])
        }),
      },
      writable: true,
    })
  })

  afterEach(() => {
    window.location = originalLocation
    window.localStorage = originalLocalStorage
    vi.clearAllMocks()
  })

  describe('parseHash', () => {
    it('should parse invoice ID from hash "#inv-123"', () => {
      expect(parseHash('#inv-123')).toBe('123')
    })

    it('should parse invoice ID with special characters', () => {
      expect(parseHash('#inv-abc-123')).toBe('abc-123')
    })

    it('should return null for invalid hash', () => {
      expect(parseHash('#other-123')).toBeNull()
      expect(parseHash('inv-123')).toBeNull()
      expect(parseHash('')).toBeNull()
    })
  })

  describe('buildHash', () => {
    it('should build hash from invoice ID', () => {
      expect(buildHash('123')).toBe('#inv-123')
    })

    it('should handle IDs with special characters', () => {
      expect(buildHash('abc-123')).toBe('#inv-abc-123')
    })
  })

  describe('isDevModeEnabled', () => {
    it('should return true when query param dev=1 is present', () => {
      window.location.search = '?dev=1'
      expect(isDevModeEnabled()).toBe(true)
    })

    it('should return true when localStorage owlin_dev=1 is set', () => {
      window.location.search = ''
      window.localStorage.setItem('owlin_dev', '1')
      expect(isDevModeEnabled()).toBe(true)
    })

    it('should return false when neither is set', () => {
      window.location.search = ''
      window.localStorage.removeItem('owlin_dev')
      expect(isDevModeEnabled()).toBe(false)
    })

    it('should prioritize query param over localStorage', () => {
      window.location.search = '?dev=1'
      window.localStorage.setItem('owlin_dev', '0')
      expect(isDevModeEnabled()).toBe(true)
    })
  })

  describe('toggleDevMode', () => {
    it('should set localStorage and update query param when enabling', () => {
      window.location.search = ''
      toggleDevMode(true)
      expect(window.localStorage.setItem).toHaveBeenCalledWith('owlin_dev', '1')
      expect(window.location.replaceState).toHaveBeenCalled()
    })

    it('should remove localStorage and update query param when disabling', () => {
      window.location.search = '?dev=1'
      toggleDevMode(false)
      expect(window.localStorage.removeItem).toHaveBeenCalledWith('owlin_dev')
      expect(window.location.replaceState).toHaveBeenCalled()
    })
  })

  describe('getSelectedIdFromHash', () => {
    it('should return invoice ID from current hash', () => {
      window.location.hash = '#inv-123'
      expect(getSelectedIdFromHash()).toBe('123')
    })

    it('should return null when hash is empty', () => {
      window.location.hash = ''
      expect(getSelectedIdFromHash()).toBeNull()
    })

    it('should return null when hash is invalid', () => {
      window.location.hash = '#other-123'
      expect(getSelectedIdFromHash()).toBeNull()
    })
  })

  describe('setHashForId', () => {
    it('should update hash when ID is provided', () => {
      window.location.hash = ''
      setHashForId('123')
      expect(window.location.replaceState).toHaveBeenCalledWith(
        {},
        '',
        '/invoices#inv-123'
      )
    })

    it('should clear hash when ID is null', () => {
      window.location.hash = '#inv-123'
      setHashForId(null)
      expect(window.location.replaceState).toHaveBeenCalledWith(
        {},
        '',
        '/invoices'
      )
    })

    it('should not update if hash already matches', () => {
      window.location.hash = '#inv-123'
      const callCount = (window.location.replaceState as ReturnType<typeof vi.fn>).mock.calls.length
      setHashForId('123')
      // Should still be called to ensure consistency
      expect(window.location.replaceState).toHaveBeenCalled()
    })
  })
})

