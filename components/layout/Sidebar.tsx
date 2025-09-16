import { useState, useEffect } from 'react'
import { SidebarItem } from './SidebarItem'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { 
  FileText, 
  BarChart3, 
  Settings, 
  ChevronLeft, 
  ChevronRight,
  Download
} from 'lucide-react'

interface SidebarProps {
  currentRole?: 'GM' | 'Finance' | 'ShiftLead'
  onWidthChange?: (width: number) => void
  onToggle?: (isExpanded: boolean) => void
}

export function Sidebar({ 
  currentRole = 'GM', 
  onWidthChange, 
  onToggle 
}: SidebarProps) {
  const [mounted, setMounted] = useState(false)
  const [isExpanded, setIsExpanded] = useState(true)

  useEffect(() => {
    setMounted(true)
    const saved = typeof window !== 'undefined' ? localStorage.getItem('owlin:sidebar') : null
    if (saved === 'collapsed') setIsExpanded(false)
    console.log("[Sidebar] mounted", typeof window !== 'undefined' ? window.innerWidth : 'SSR')
  }, [])

  useEffect(() => {
    if (!mounted) return
    localStorage.setItem('owlin:sidebar', isExpanded ? 'expanded' : 'collapsed')
    onWidthChange?.(isExpanded ? 280 : 72)
    onToggle?.(isExpanded)
  }, [isExpanded, mounted, onWidthChange, onToggle])

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'b' && (e.metaKey || e.ctrlKey)) {
        e.preventDefault()
        setIsExpanded((prev: boolean) => !prev)
      }
    }

    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [])

  const loadData = async () => {
    try {
      // Load any sidebar-specific data here
    } catch (error) {
      console.error('Failed to load sidebar data:', error)
    }
  }

  useEffect(() => {
    loadData()
  }, [])

  if (!mounted) {
    // render minimal shell to avoid SSR/CSR mismatch
    return <aside className="w-[280px]" aria-hidden />
  }

  return (
    <div 
      className={`bg-background border-r transition-all duration-300 flex flex-col ${
        isExpanded ? 'w-[280px]' : 'w-[72px]'
      }`}
    >
      {/* Header */}
      <div className="p-4 border-b">
        <div className="flex items-center justify-between">
          {isExpanded && (
            <h1 className="text-lg font-semibold">Owlin</h1>
          )}
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setIsExpanded(!isExpanded)}
            className="ml-auto"
          >
            {isExpanded ? (
              <ChevronLeft className="h-4 w-4" />
            ) : (
              <ChevronRight className="h-4 w-4" />
            )}
          </Button>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 p-4 space-y-2">
        <SidebarItem
          href="/"
          icon={BarChart3}
          label="Dashboard"
          isExpanded={isExpanded}
          testId="sidebar-dashboard"
        />
        <SidebarItem
          href="/invoices"
          icon={FileText}
          label="Invoices"
          isExpanded={isExpanded}
          testId="sidebar-invoices"
        />
        <SidebarItem
          href="/suppliers"
          icon={Download}
          label="Suppliers"
          isExpanded={isExpanded}
          testId="sidebar-suppliers"
        />
        <SidebarItem
          href="/settings"
          icon={Settings}
          label="Settings"
          isExpanded={isExpanded}
          testId="sidebar-settings"
        />
      </nav>

      {/* Footer */}
      {isExpanded && (
        <div className="p-4 border-t">
          <Card>
            <CardContent className="p-3">
              <div className="text-xs text-muted-foreground">
                <div>Role: {currentRole}</div>
                <div>Version: 1.0.0</div>
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  )
} 