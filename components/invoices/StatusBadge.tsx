import { Loader2, CheckCircle2, ScanLine, FilePlus2 } from 'lucide-react'
import { Badge } from '@/components/ui/badge'

interface StatusBadgeProps {
  status: string | null
  matched?: boolean
  className?: string
}

export default function StatusBadge({ status, matched = false, className = "" }: StatusBadgeProps) {
  const getStatusInfo = () => {
    if (matched) {
      return {
        icon: <CheckCircle2 className="w-3 h-3" />,
        label: "Matched",
        className: "bg-green-100 text-green-800 border-green-200"
      }
    }

    switch (status?.toLowerCase()) {
      case 'queued':
        return {
          icon: <Loader2 className="w-3 h-3 animate-spin" />,
          label: "Queued",
          className: "bg-amber-100 text-amber-800 border-amber-200"
        }
      case 'scanned':
        return {
          icon: <ScanLine className="w-3 h-3" />,
          label: "Scanned",
          className: "bg-blue-100 text-blue-800 border-blue-200"
        }
      case 'manual':
        return {
          icon: <FilePlus2 className="w-3 h-3" />,
          label: "Manual",
          className: "bg-violet-100 text-violet-800 border-violet-200"
        }
      default:
        return {
          icon: null,
          label: status || "Unknown",
          className: "bg-gray-100 text-gray-800 border-gray-200"
        }
    }
  }

  const { icon, label, className: statusClass } = getStatusInfo()

  return (
    <Badge className={`${statusClass} ${className} flex items-center gap-1 border`}>
      {icon}
      {label}
    </Badge>
  )
}
