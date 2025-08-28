import Link from 'next/link'
import { useRouter } from 'next/router'
import { LucideIcon } from 'lucide-react'
import { cn } from '@/lib/utils'
import { Badge } from '@/components/ui/badge'

interface SidebarItemProps {
  href: string
  icon: LucideIcon
  label: string
  badge?: number
  badgeVariant?: "default" | "secondary" | "destructive" | "outline"
  testId: string
  isExpanded: boolean
  isVisible?: boolean
}

export function SidebarItem({ 
  href, 
  icon: Icon, 
  label, 
  badge, 
  badgeVariant = "secondary",
  testId, 
  isExpanded,
  isVisible = true 
}: SidebarItemProps) {
  const router = useRouter()
  const isActive = router.pathname === href

  if (!isVisible) return null

  return (
    <Link
      href={href}
      data-testid={testId}
      className={cn(
        "flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors hover:bg-accent hover:text-accent-foreground",
        isActive && "bg-accent text-accent-foreground",
        !isExpanded && "justify-center px-2"
      )}
    >
      <Icon className="h-4 w-4" />
      {isExpanded && (
        <>
          <span className="flex-1">{label}</span>
          {badge !== undefined && (
            <Badge variant={badgeVariant} className="ml-auto">
              {badge}
            </Badge>
          )}
        </>
      )}
    </Link>
  )
} 