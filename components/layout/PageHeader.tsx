import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { Search, Filter } from 'lucide-react'

interface PageHeaderProps {
  onFilterChange?: (filters: {
    q?: string
    venue?: string
    supplier?: string
    from?: string
    to?: string
    onlyUnmatched?: boolean
    onlyFlagged?: boolean
  }) => void
  issuesCount?: number
  unmatchedCount?: number
}

export default function PageHeader({ 
  onFilterChange, 
  issuesCount = 0, 
  unmatchedCount = 0 
}: PageHeaderProps) {
  const [filters, setFilters] = useState({
    q: '',
    venue: '',
    supplier: '',
    from: '',
    to: '',
    onlyUnmatched: false,
    onlyFlagged: false
  })

  const updateFilters = (newFilters: Partial<typeof filters>) => {
    const updated = { ...filters, ...newFilters }
    setFilters(updated)
    onFilterChange?.(updated)
  }

  return (
    <div className="sticky top-0 z-20 bg-[var(--ow-card)] border-b border-[var(--ow-border)] shadow-sm">
      <div className="max-w-[1280px] mx-auto px-6 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4 flex-1">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-muted-foreground h-4 w-4" />
              <Input
                placeholder="Search invoices..."
                value={filters.q}
                onChange={(e) => updateFilters({ q: e.target.value })}
                className="pl-10 w-80"
              />
            </div>
            <Button variant="outline" size="sm">
              <Filter className="h-4 w-4 mr-2" />
              Filters
            </Button>
          </div>
          <div className="flex items-center gap-2">
            <Badge variant="outline">
              {issuesCount} issues
            </Badge>
            <Badge variant="outline">
              {unmatchedCount} unmatched
            </Badge>
          </div>
        </div>
      </div>
    </div>
  )
} 