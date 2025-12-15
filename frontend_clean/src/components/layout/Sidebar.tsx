/**
 * Owlin Sidebar Component - Dynamic Glassmorphism Design
 * 
 * Auto-collapsing sidebar that expands on hover, with smooth animations
 * and seamless edge blending for a modern, dynamic feel.
 */

import { useEffect, useState, useRef } from "react"
import { useLocation } from "react-router-dom"
import { ChevronLeft, Menu, ChevronRight } from "lucide-react"
import { SidebarItem } from "./SidebarItem"
import { 
  navigationConfig, 
  filterNavigationByRole, 
  groupNavigationBySection,
  type UserRole 
} from "../../config/navigation"
import './Sidebar.css'

interface SidebarProps {
  currentRole?: UserRole
  onWidthChange?: (width: number) => void
  onToggle?: (isExpanded: boolean) => void
}

export function Sidebar({ currentRole = 'GM', onWidthChange, onToggle }: SidebarProps) {
  const location = useLocation()
  const sidebarRef = useRef<HTMLAsideElement>(null)
  const hoverTimeoutRef = useRef<NodeJS.Timeout | null>(null)
  
  // Always start expanded - ignore localStorage
  const [isExpanded, setIsExpanded] = useState(true)
  const [isHovered, setIsHovered] = useState(false)
  const [isManuallyCollapsed, setIsManuallyCollapsed] = useState(false)
  const [isMobileOpen, setIsMobileOpen] = useState(false)
  const [isDesktop, setIsDesktop] = useState(() => {
    if (typeof window === "undefined") return true
    return window.innerWidth >= 1024
  })

  // Track window size for responsive behavior
  useEffect(() => {
    const handleResize = () => {
      setIsDesktop(window.innerWidth >= 1024)
    }
    window.addEventListener('resize', handleResize)
    handleResize() // Initial check
    return () => window.removeEventListener('resize', handleResize)
  }, [])

  // Auto-collapse/exp logic
  const shouldShowExpanded = isManuallyCollapsed ? false : (isHovered || isExpanded)

  // Force expanded on mount - clear localStorage collapsed state
  useEffect(() => {
    if (typeof window === "undefined") return
    localStorage.removeItem('owlin:sidebar')
    setIsExpanded(true)
  }, []) // Run once on mount

  // Handle hover-based auto-collapse/expand with smooth, responsive transitions
  useEffect(() => {
    if (!isDesktop || isManuallyCollapsed) return

    const handleMouseEnter = () => {
      if (hoverTimeoutRef.current) {
        clearTimeout(hoverTimeoutRef.current)
        hoverTimeoutRef.current = null
      }
      // Smooth, gradual expand - set hovered first, then expand after tiny delay for progressive feel
      setIsHovered(true)
      // Small delay creates a more natural, progressive expansion
      setTimeout(() => {
        setIsExpanded(true)
      }, 50)
    }

    const handleMouseLeave = () => {
      // Reduced delay for more responsive collapse
      hoverTimeoutRef.current = setTimeout(() => {
        setIsHovered(false)
        // Gradual collapse with slight delay
        setTimeout(() => {
          setIsExpanded(false)
        }, 100)
      }, 200) // 200ms delay - more responsive
    }

    const sidebar = sidebarRef.current
    if (sidebar) {
      sidebar.addEventListener('mouseenter', handleMouseEnter)
      sidebar.addEventListener('mouseleave', handleMouseLeave)
      
      return () => {
        sidebar.removeEventListener('mouseenter', handleMouseEnter)
        sidebar.removeEventListener('mouseleave', handleMouseLeave)
        if (hoverTimeoutRef.current) {
          clearTimeout(hoverTimeoutRef.current)
        }
      }
    }
  }, [isDesktop, isManuallyCollapsed])

  // Click-outside detection for immediate collapse
  useEffect(() => {
    if (!isDesktop || isManuallyCollapsed || !shouldShowExpanded) return

    const handleClickOutside = (event: MouseEvent) => {
      const sidebar = sidebarRef.current
      if (sidebar && !sidebar.contains(event.target as Node)) {
        // Clear any pending hover timeouts
        if (hoverTimeoutRef.current) {
          clearTimeout(hoverTimeoutRef.current)
          hoverTimeoutRef.current = null
        }
        // Immediate collapse on click outside (0ms delay)
        setIsHovered(false)
        setIsExpanded(false)
      }
    }

    // Use capture phase to catch clicks early
    document.addEventListener('mousedown', handleClickOutside, true)
    
    return () => {
      document.removeEventListener('mousedown', handleClickOutside, true)
    }
  }, [isDesktop, isManuallyCollapsed, shouldShowExpanded])

  // Persist expanded state
  useEffect(() => {
    if (typeof window === "undefined") return
    const width = shouldShowExpanded ? 280 : 80
    onWidthChange?.(width)
    onToggle?.(shouldShowExpanded)
  }, [shouldShowExpanded, onWidthChange, onToggle])

  // Keyboard shortcut: Cmd/Ctrl + `
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === '`') {
        e.preventDefault()
        setIsManuallyCollapsed(prev => !prev)
        if (hoverTimeoutRef.current) {
          clearTimeout(hoverTimeoutRef.current)
        }
      }
      if (e.key === 'Escape' && isMobileOpen) {
        setIsMobileOpen(false)
      }
    }
    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [isMobileOpen])

  // Filter and group navigation items by role
  const filteredItems = filterNavigationByRole(navigationConfig, currentRole)
  const groupedItems = groupNavigationBySection(filteredItems)
  const sectionOrder: Array<keyof typeof groupedItems> = ['Core', 'Analysis', 'Admin', 'Other']

  // Render navigation items
  const renderNavItems = (items: typeof filteredItems) => {
    return items.map((item) => {
      return (
        <SidebarItem
          key={item.id}
          to={item.path}
          icon={item.icon}
          label={item.label}
          badge={undefined}
          badgeVariant={item.badge?.variant}
          testId={item.testId || item.id}
          isCollapsed={!shouldShowExpanded}
          isVisible={true}
        />
      )
    })
  }

  // Desktop Sidebar Content - Dynamic glassmorphism with hover expansion
  const sidebarContent = isDesktop ? (
    <aside
      ref={sidebarRef}
      data-testid="sidebar"
      className="sidebar-desktop"
      style={{
        display: 'flex',
        height: '100vh',
        width: shouldShowExpanded ? '280px' : '80px',
        backgroundColor: '#1a1a1a',
        backdropFilter: 'blur(24px)',
        WebkitBackdropFilter: 'blur(24px)',
        borderRight: '1px solid rgba(255, 255, 255, 0.12)',
        boxShadow: shouldShowExpanded
          ? '0 8px 32px rgba(0, 0, 0, 0.5), -4px 0 16px rgba(0, 0, 0, 0.3)'
          : '0 8px 32px rgba(0, 0, 0, 0.4), -2px 0 8px rgba(0, 0, 0, 0.2)',
        flexDirection: 'column',
        position: 'fixed',
        left: 0,
        top: 0,
        zIndex: 20,
        transition: 'width 300ms cubic-bezier(0.4, 0, 0.2, 1), box-shadow 300ms cubic-bezier(0.4, 0, 0.2, 1)',
        // Solid background to prevent white showing through
        backgroundImage: 'none',
        overflow: 'hidden'
      }}
    >
      {/* Top Section - Logo */}
      <div style={{
        borderBottom: '1px solid rgba(255, 255, 255, 0.1)',
        padding: shouldShowExpanded ? '24px 20px' : '20px 12px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: shouldShowExpanded ? 'flex-start' : 'center',
        gap: '12px',
        transition: 'padding 300ms cubic-bezier(0.4, 0, 0.2, 1)',
        minHeight: '72px'
      }}>
        <div style={{
          width: shouldShowExpanded ? '44px' : '40px',
          height: shouldShowExpanded ? '44px' : '40px',
          borderRadius: '14px',
          background: 'linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          color: 'white',
          fontWeight: 'bold',
          fontSize: shouldShowExpanded ? '20px' : '18px',
          boxShadow: '0 4px 16px rgba(37, 99, 235, 0.35)',
          flexShrink: 0,
          transition: 'all 300ms cubic-bezier(0.4, 0, 0.2, 1)',
          cursor: 'pointer'
        }}
        onMouseEnter={(e) => {
          e.currentTarget.style.transform = 'scale(1.05)'
          e.currentTarget.style.boxShadow = '0 6px 20px rgba(37, 99, 235, 0.45)'
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.transform = 'scale(1)'
          e.currentTarget.style.boxShadow = '0 4px 16px rgba(37, 99, 235, 0.35)'
        }}
        >
          O
        </div>
        {shouldShowExpanded && (
          <span style={{
            fontSize: '22px',
            fontWeight: 700,
            color: 'rgba(255, 255, 255, 0.87)',
            letterSpacing: '-0.02em',
            whiteSpace: 'nowrap',
            opacity: shouldShowExpanded ? 1 : 0,
            transition: 'opacity 400ms cubic-bezier(0.4, 0, 0.2, 1)',
            animation: shouldShowExpanded ? 'fadeIn 400ms cubic-bezier(0.4, 0, 0.2, 1)' : 'none'
          }}>
            Owlin
          </span>
        )}
      </div>

      {/* Navigation - Grouped by Section */}
      <nav style={{
        flex: 1,
        overflowY: 'auto',
        overflowX: 'hidden',
        padding: shouldShowExpanded ? '20px 12px' : '16px 8px',
        display: 'flex',
        flexDirection: 'column',
        gap: shouldShowExpanded ? '28px' : '20px',
        transition: 'padding 300ms cubic-bezier(0.4, 0, 0.2, 1)'
      }}>
        {sectionOrder.map((section) => {
          const items = groupedItems[section]
          if (!items || items.length === 0) return null

          return (
            <div key={section} style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
              {shouldShowExpanded && section !== 'Core' && (
                <div style={{
                  padding: '0 12px 6px 12px',
                  opacity: shouldShowExpanded ? 1 : 0,
                  transition: 'opacity 400ms cubic-bezier(0.4, 0, 0.2, 1)'
                }}>
                  <span style={{
                    fontSize: '11px',
                    fontWeight: 700,
                    color: 'rgba(255, 255, 255, 0.7)',
                    textTransform: 'uppercase',
                    letterSpacing: '0.1em'
                  }}>
                    {section}
                  </span>
                </div>
              )}
              <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                {renderNavItems(items)}
              </div>
            </div>
          )
        })}
      </nav>

      {/* Bottom Section - Collapse Toggle (only when expanded) */}
      {shouldShowExpanded && (
        <div style={{
          borderTop: '1px solid rgba(255, 255, 255, 0.1)',
          padding: '12px',
          opacity: shouldShowExpanded ? 1 : 0,
          transition: 'opacity 400ms cubic-bezier(0.4, 0, 0.2, 1)'
        }}>
          <button
            onClick={() => {
              setIsManuallyCollapsed(true)
              setIsHovered(false)
              if (hoverTimeoutRef.current) {
                clearTimeout(hoverTimeoutRef.current)
              }
            }}
            data-testid="sidebar-toggle"
            style={{
              width: '100%',
              display: 'flex',
              alignItems: 'center',
              gap: '12px',
              color: 'rgba(255, 255, 255, 0.75)',
              padding: '10px 12px',
              borderRadius: '12px',
              fontSize: '14px',
              fontWeight: 500,
              transition: 'all 300ms cubic-bezier(0.4, 0, 0.2, 1)',
              border: 'none',
              background: 'rgba(255, 255, 255, 0.03)',
              cursor: 'pointer',
              backdropFilter: 'blur(10px)'
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.backgroundColor = 'rgba(255, 255, 255, 0.08)'
              e.currentTarget.style.color = 'rgba(255, 255, 255, 1)'
              e.currentTarget.style.transform = 'translateX(-2px)'
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.backgroundColor = 'rgba(255, 255, 255, 0.03)'
              e.currentTarget.style.color = 'rgba(255, 255, 255, 0.75)'
              e.currentTarget.style.transform = 'translateX(0)'
            }}
          >
            <ChevronLeft style={{ width: '18px', height: '18px', flexShrink: 0 }} />
            <span>Collapse</span>
          </button>
        </div>
      )}

      {/* Expand hint when collapsed */}
      {!shouldShowExpanded && !isManuallyCollapsed && (
        <div style={{
          position: 'absolute',
          right: '8px',
          top: '50%',
          transform: 'translateY(-50%)',
          opacity: 0.6,
          pointerEvents: 'none',
          transition: 'opacity 300ms cubic-bezier(0.4, 0, 0.2, 1)'
        }}>
          <ChevronRight style={{ width: '16px', height: '16px', color: 'rgba(255, 255, 255, 0.4)' }} />
        </div>
      )}
    </aside>
  ) : null

  return (
    <>
      {/* Manual Expand Button - Top Left (when manually collapsed) */}
      {isManuallyCollapsed && isDesktop && (
        <div style={{
          position: 'fixed',
          top: '20px',
          left: '20px',
          zIndex: 50
        }}>
          <button
            onClick={() => {
              setIsManuallyCollapsed(false)
              setIsExpanded(true)
            }}
            data-testid="sidebar-mini"
            style={{
              width: '52px',
              height: '52px',
              padding: 0,
              backgroundColor: '#1a1a1a',
              backdropFilter: 'blur(24px)',
              WebkitBackdropFilter: 'blur(24px)',
              border: '1px solid rgba(255, 255, 255, 0.1)',
              boxShadow: '0 8px 24px rgba(0, 0, 0, 0.5)',
              borderRadius: '14px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              cursor: 'pointer',
              transition: 'all 300ms cubic-bezier(0.4, 0, 0.2, 1)'
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.backgroundColor = '#1f1f1f'
              e.currentTarget.style.transform = 'scale(1.08)'
              e.currentTarget.style.boxShadow = '0 12px 32px rgba(0, 0, 0, 0.7)'
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.backgroundColor = '#1a1a1a'
              e.currentTarget.style.transform = 'scale(1)'
              e.currentTarget.style.boxShadow = '0 8px 24px rgba(0, 0, 0, 0.5)'
            }}
            aria-label="Open sidebar"
          >
            <div style={{
              width: '36px',
              height: '36px',
              borderRadius: '10px',
              background: 'linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: 'white',
              fontWeight: 'bold',
              fontSize: '18px',
              boxShadow: '0 4px 12px rgba(37, 99, 235, 0.4)'
            }}>
              O
            </div>
          </button>
        </div>
      )}

      {/* Mobile Hamburger Button */}
      {!isDesktop && (
        <div style={{
          position: 'fixed',
          top: '20px',
          left: '20px',
          zIndex: 50
        }}>
          <button
            onClick={() => setIsMobileOpen(!isMobileOpen)}
            data-testid="sidebar-open"
            style={{
              width: '52px',
              height: '52px',
              backgroundColor: '#1a1a1a',
              backdropFilter: 'blur(24px)',
              WebkitBackdropFilter: 'blur(24px)',
              border: '1px solid rgba(255, 255, 255, 0.1)',
              boxShadow: '0 8px 24px rgba(0, 0, 0, 0.5)',
              padding: '14px',
              borderRadius: '14px',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              transition: 'all 300ms cubic-bezier(0.4, 0, 0.2, 1)'
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.backgroundColor = '#1f1f1f'
              e.currentTarget.style.transform = 'scale(1.08)'
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.backgroundColor = '#1a1a1a'
              e.currentTarget.style.transform = 'scale(1)'
            }}
          >
            <Menu style={{ width: '22px', height: '22px', color: 'rgba(255, 255, 255, 0.87)' }} />
          </button>
        </div>
      )}

      {/* Mobile Sidebar Overlay */}
      {isMobileOpen && !isDesktop && (
        <div style={{
          position: 'fixed',
          inset: 0,
          zIndex: 40
        }}>
          <div
            style={{
              position: 'absolute',
              inset: 0,
              backgroundColor: 'rgba(0, 0, 0, 0.5)',
              backdropFilter: 'blur(4px)'
            }}
            onClick={() => setIsMobileOpen(false)}
          />
          <aside style={{
            position: 'absolute',
            left: 0,
            top: 0,
            height: '100%',
            width: '280px',
            backgroundColor: '#1a1a1a',
            backdropFilter: 'blur(24px)',
            WebkitBackdropFilter: 'blur(24px)',
            boxShadow: '0 8px 32px rgba(0, 0, 0, 0.7)',
            display: 'flex',
            flexDirection: 'column'
          }}>
            <div style={{
              borderBottom: '1px solid rgba(255, 255, 255, 0.1)',
              padding: '24px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between'
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                <div style={{
                  width: '44px',
                  height: '44px',
                  borderRadius: '14px',
                  background: 'linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  color: 'white',
                  fontWeight: 'bold',
                  fontSize: '20px',
                  boxShadow: '0 4px 16px rgba(37, 99, 235, 0.35)'
                }}>
                  O
                </div>
                <span style={{ fontSize: '22px', fontWeight: 700, color: 'rgba(255, 255, 255, 0.87)' }}>Owlin</span>
              </div>
              <button
                onClick={() => setIsMobileOpen(false)}
                style={{
                  width: '36px',
                  height: '36px',
                  borderRadius: '10px',
                  border: 'none',
                  background: 'rgba(255, 255, 255, 0.05)',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  color: 'rgba(255, 255, 255, 0.6)',
                  transition: 'all 150ms ease-out'
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.backgroundColor = 'rgba(255, 255, 255, 0.1)'
                  e.currentTarget.style.color = 'rgba(255, 255, 255, 0.95)'
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.backgroundColor = 'rgba(255, 255, 255, 0.05)'
                  e.currentTarget.style.color = 'rgba(255, 255, 255, 0.6)'
                }}
              >
                <ChevronLeft style={{ width: '20px', height: '20px' }} />
              </button>
            </div>
            <nav style={{ flex: 1, overflowY: 'auto', padding: '20px 12px' }}>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '28px' }}>
                {sectionOrder.map((section) => {
                  const items = groupedItems[section]
                  if (!items || items.length === 0) return null
                  return (
                    <div key={section} style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                      {section !== 'Core' && (
                        <div style={{ padding: '0 12px 6px 12px' }}>
                          <span style={{
                            fontSize: '11px',
                            fontWeight: 700,
                            color: 'rgba(255, 255, 255, 0.7)',
                            textTransform: 'uppercase',
                            letterSpacing: '0.1em'
                          }}>
                            {section}
                          </span>
                        </div>
                      )}
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                        {renderNavItems(items)}
                      </div>
                    </div>
                  )
                })}
              </div>
            </nav>
          </aside>
        </div>
      )}

      {/* Desktop Sidebar */}
      {sidebarContent}
    </>
  )
}
