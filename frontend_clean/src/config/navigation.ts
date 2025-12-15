/**
 * Navigation Configuration - Single Source of Truth
 * 
 * This file defines all navigation items for the Owlin sidebar.
 * Each item includes:
 * - id: Unique identifier
 * - label: Display text
 * - icon: Lucide icon name (as string for dynamic import)
 * - path: Router path
 * - roles: Array of roles allowed to see this item
 * - section: Optional grouping for visual organization
 */

import { 
  LayoutDashboard, 
  FileText, 
  ClipboardList, 
  Building2, 
  AlertTriangle, 
  Settings, 
  BarChart3,
  StickyNote,
  Package,
  Trash2,
  FlaskConical
} from "lucide-react"
import { ComponentType } from "react"

export type UserRole = 'GM' | 'Finance' | 'ShiftLead'

export interface NavigationItem {
  id: string
  label: string
  icon: ComponentType<{ className?: string }>
  path: string
  roles: UserRole[]
  section?: 'Core' | 'Analysis' | 'Admin'
  badge?: {
    count?: number
    variant?: 'default' | 'secondary' | 'destructive' | 'outline'
    testId?: string
  }
  testId?: string
}

/**
 * Complete navigation configuration for Owlin
 * All sidebar items are defined here - no hardcoded arrays elsewhere
 */
export const navigationConfig: NavigationItem[] = [
  // Core Section
  {
    id: 'dashboard',
    label: 'Dashboard',
    icon: LayoutDashboard,
    path: '/',
    roles: ['GM', 'Finance', 'ShiftLead'],
    section: 'Core',
    testId: 'nav-dashboard'
  },
  {
    id: 'invoices',
    label: 'Invoices',
    icon: FileText,
    path: '/invoices',
    roles: ['GM', 'Finance', 'ShiftLead'],
    section: 'Core',
    testId: 'nav-invoices'
  },
  {
    id: 'invoices-gen',
    label: 'Invoices Gen (Test)',
    icon: FlaskConical,
    path: '/invoices-gen',
    roles: ['GM', 'Finance', 'ShiftLead'],
    section: 'Core',
    testId: 'nav-invoices-gen'
  },
  {
    id: 'delivery-notes',
    label: 'Delivery Notes',
    icon: ClipboardList,
    path: '/delivery-notes',
    roles: ['GM', 'Finance', 'ShiftLead'],
    section: 'Core',
    badge: {
      testId: 'badge-unmatched-dn'
      // count will be loaded dynamically
    },
    testId: 'nav-delivery-notes'
  },
  {
    id: 'suppliers',
    label: 'Suppliers',
    icon: Building2,
    path: '/suppliers',
    roles: ['GM', 'Finance'], // ShiftLead excluded
    section: 'Core',
    testId: 'nav-suppliers'
  },
  {
    id: 'issues',
    label: 'Flagged Issues',
    icon: AlertTriangle,
    path: '/issues',
    roles: ['GM', 'Finance', 'ShiftLead'],
    section: 'Core',
    badge: {
      variant: 'destructive',
      testId: 'badge-flagged'
      // count will be loaded dynamically
    },
    testId: 'nav-issues'
  },
  {
    id: 'waste',
    label: 'Waste',
    icon: Trash2,
    path: '/waste',
    roles: ['GM', 'Finance', 'ShiftLead'],
    section: 'Core',
    testId: 'nav-waste'
  },
  
  // Analysis Section
  {
    id: 'products',
    label: 'Products',
    icon: Package,
    path: '/products',
    roles: ['GM', 'Finance'],
    section: 'Analysis',
    testId: 'nav-products'
  },
  {
    id: 'reports',
    label: 'Reports',
    icon: BarChart3,
    path: '/reports',
    roles: ['GM', 'Finance'],
    section: 'Analysis',
    testId: 'nav-reports'
  },
  {
    id: 'forecasting',
    label: 'Forecasting',
    icon: BarChart3,
    path: '/forecasting',
    roles: ['GM', 'Finance'],
    section: 'Analysis',
    testId: 'nav-forecasting'
  },
  
  // Admin Section
  {
    id: 'notes',
    label: 'Notes & Logs',
    icon: StickyNote,
    path: '/notes',
    roles: ['GM', 'Finance'],
    section: 'Admin',
    testId: 'nav-notes'
  },
  {
    id: 'settings',
    label: 'Settings',
    icon: Settings,
    path: '/settings',
    roles: ['GM', 'Finance'], // ShiftLead excluded
    testId: 'nav-settings'
  }
]

/**
 * Filter navigation items by user role
 */
export function filterNavigationByRole(
  items: NavigationItem[],
  currentRole: UserRole
): NavigationItem[] {
  return items.filter(item => item.roles.includes(currentRole))
}

/**
 * Group navigation items by section
 */
export function groupNavigationBySection(
  items: NavigationItem[]
): Record<string, NavigationItem[]> {
  const grouped: Record<string, NavigationItem[]> = {}
  
  items.forEach(item => {
    const section = item.section || 'Other'
    if (!grouped[section]) {
      grouped[section] = []
    }
    grouped[section].push(item)
  })
  
  return grouped
}

