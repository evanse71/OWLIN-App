/**
 * SidebarItem Component - Dynamic Glassmorphism Design
 * 
 * Navigation item that adapts to collapsed/expanded state with smooth animations.
 * Features circular icon buttons and elegant active state indication.
 */

import { NavLink } from "react-router-dom"
import { ComponentType } from "react"
import './SidebarItem.css'

interface SidebarItemProps {
  to: string
  icon: ComponentType<{ className?: string; style?: React.CSSProperties }>
  label: string
  badge?: number
  badgeVariant?: "default" | "secondary" | "destructive" | "outline"
  testId: string
  isCollapsed: boolean
  isVisible?: boolean
}

export function SidebarItem({ 
  to, 
  icon: Icon, 
  label, 
  badge, 
  badgeVariant = "secondary",
  testId, 
  isCollapsed,
  isVisible = true 
}: SidebarItemProps) {
  if (!isVisible) return null

  return (
    <NavLink
      to={to}
      data-testid={testId}
      end={to === "/"} // Exact match for root path
      className={({ isActive }) => {
        return `sidebar-item ${isActive ? 'sidebar-item-active' : ''} ${isCollapsed ? 'sidebar-item-collapsed' : ''}`
      }}
    >
      {({ isActive }) => (
        <>
          {/* Circular Icon Button */}
          <div className={`sidebar-item-icon ${isActive ? 'sidebar-item-icon-active' : ''}`}>
            <Icon style={{ width: '20px', height: '20px' }} />
          </div>
          
          {/* Label - fades in/out based on collapsed state */}
          <span 
            className={`sidebar-item-label ${isCollapsed ? 'sidebar-item-label-hidden' : ''}`}
            style={{
              opacity: isCollapsed ? 0 : 1,
              width: isCollapsed ? 0 : 'auto',
              transition: 'opacity 450ms cubic-bezier(0.25, 0.46, 0.45, 0.94), width 450ms cubic-bezier(0.25, 0.46, 0.45, 0.94)'
            }}
          >
            {label}
          </span>
          
          {/* Badge */}
          {badge !== undefined && badge > 0 && !isCollapsed && (
            <span 
              className={`sidebar-item-badge ${badgeVariant === "destructive" ? 'sidebar-item-badge-destructive' : 'sidebar-item-badge-secondary'}`}
              data-testid={testId ? `${testId}-badge` : undefined}
              style={{
                opacity: isCollapsed ? 0 : 1,
                transition: 'opacity 450ms cubic-bezier(0.25, 0.46, 0.45, 0.94)'
              }}
            >
              {badge}
            </span>
          )}
          
          {isActive && (
            <span className="sr-only" aria-current="page">
              Current page
            </span>
          )}
        </>
      )}
    </NavLink>
  )
}
