import { memo, useMemo, useRef, useState, useEffect, useCallback } from 'react'
import { InvoiceCard } from './InvoiceCard'
import { InvoiceGroup } from './InvoiceGroup'
import './VirtualizedInvoiceList.css'

export interface Invoice {
  id: string
  supplier: string
  date: string
  value: number
  status: 'matched' | 'flagged' | 'error' | 'pending' | 'scanned'
  confidence?: number
  isReceipt?: boolean
  metadata?: any
}

interface GroupedInvoice {
  groupKey: string
  groupLabel: string
  invoices: Invoice[]
}

interface VirtualizedInvoiceListProps {
  invoices: Invoice[]
  selectedId?: string | null
  onInvoiceClick: (invoice: Invoice) => void
  itemHeight?: number
  containerHeight?: number
}

function groupInvoicesByDate(invoices: Invoice[]): GroupedInvoice[] {
  const now = new Date()
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate())
  const yesterday = new Date(today)
  yesterday.setDate(yesterday.getDate() - 1)
  const weekAgo = new Date(today)
  weekAgo.setDate(weekAgo.getDate() - 7)
  const monthAgo = new Date(today)
  monthAgo.setMonth(monthAgo.getMonth() - 1)

  const groups: Record<string, Invoice[]> = {
    today: [],
    yesterday: [],
    thisWeek: [],
    thisMonth: [],
    older: [],
  }

  invoices.forEach((invoice) => {
    const invoiceDate = new Date(invoice.date)
    
    if (invoiceDate >= today) {
      groups.today.push(invoice)
    } else if (invoiceDate >= yesterday) {
      groups.yesterday.push(invoice)
    } else if (invoiceDate >= weekAgo) {
      groups.thisWeek.push(invoice)
    } else if (invoiceDate >= monthAgo) {
      groups.thisMonth.push(invoice)
    } else {
      groups.older.push(invoice)
    }
  })

  const groupLabels: Record<string, string> = {
    today: 'Today',
    yesterday: 'Yesterday',
    thisWeek: 'This Week',
    thisMonth: 'This Month',
    older: 'Older',
  }

  return Object.entries(groups)
    .filter(([_, invoices]) => invoices.length > 0)
    .map(([key, invoices]) => ({
      groupKey: key,
      groupLabel: groupLabels[key],
      invoices: invoices.sort((a, b) => new Date(b.date).getTime() - new Date(a.date).getTime()),
    }))
}

export const VirtualizedInvoiceList = memo(function VirtualizedInvoiceList({
  invoices,
  selectedId,
  onInvoiceClick,
  itemHeight = 120,
  containerHeight = 600,
}: VirtualizedInvoiceListProps) {
  const [expandedGroups, setExpandedGroups] = useState<Set<string>>(new Set(['today', 'yesterday', 'thisWeek']))
  const [scrollTop, setScrollTop] = useState(0)
  const containerRef = useRef<HTMLDivElement>(null)

  const groupedInvoices = useMemo(() => groupInvoicesByDate(invoices), [invoices])

  const toggleGroup = useCallback((groupKey: string) => {
    setExpandedGroups((prev) => {
      const next = new Set(prev)
      if (next.has(groupKey)) {
        next.delete(groupKey)
      } else {
        next.add(groupKey)
      }
      return next
    })
  }, [])

  const handleScroll = useCallback((e: React.UIEvent<HTMLDivElement>) => {
    setScrollTop(e.currentTarget.scrollTop)
  }, [])

  // Calculate visible items
  const visibleItems = useMemo(() => {
    let offset = 0
    const visible: Array<{ type: 'group' | 'invoice'; data: any; index: number; offset: number }> = []

    groupedInvoices.forEach((group) => {
      const isExpanded = expandedGroups.has(group.groupKey)
      const groupHeight = 48 // Group header height
      const invoicesHeight = isExpanded ? group.invoices.length * itemHeight : 0
      const totalGroupHeight = groupHeight + invoicesHeight

      // Check if group is visible
      if (offset + totalGroupHeight >= scrollTop - itemHeight && offset <= scrollTop + containerHeight + itemHeight) {
        visible.push({
          type: 'group',
          data: group,
          index: visible.length,
          offset,
        })

        if (isExpanded) {
          group.invoices.forEach((invoice, idx) => {
            const invoiceOffset = offset + groupHeight + idx * itemHeight
            if (invoiceOffset >= scrollTop - itemHeight && invoiceOffset <= scrollTop + containerHeight + itemHeight) {
              visible.push({
                type: 'invoice',
                data: invoice,
                index: visible.length,
                offset: invoiceOffset,
              })
            }
          })
        }
      }

      offset += totalGroupHeight
    })

    return visible
  }, [groupedInvoices, expandedGroups, scrollTop, containerHeight, itemHeight])

  const totalHeight = useMemo(() => {
    return groupedInvoices.reduce((acc, group) => {
      const isExpanded = expandedGroups.has(group.groupKey)
      return acc + 48 + (isExpanded ? group.invoices.length * itemHeight : 0)
    }, 0)
  }, [groupedInvoices, expandedGroups, itemHeight])

  if (invoices.length === 0) {
    return (
      <div className="virtualized-list-empty">
        <p>No invoices found</p>
      </div>
    )
  }

  return (
    <div
      ref={containerRef}
      className="virtualized-invoice-list"
      style={{ height: containerHeight }}
      onScroll={handleScroll}
    >
      <div className="virtualized-invoice-list-content" style={{ height: totalHeight }}>
        {groupedInvoices.map((group) => {
          const isExpanded = expandedGroups.has(group.groupKey)
          return (
            <InvoiceGroup
              key={group.groupKey}
              groupKey={group.groupKey}
              label={group.groupLabel}
              invoices={group.invoices}
              isExpanded={isExpanded}
              onToggle={() => toggleGroup(group.groupKey)}
              onInvoiceClick={onInvoiceClick}
              selectedId={selectedId}
              itemHeight={itemHeight}
            />
          )
        })}
      </div>
    </div>
  )
})

