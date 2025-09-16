import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Accordion, AccordionItem, AccordionTrigger, AccordionContent } from '@/components/ui/accordion'
import LineItemsTable from './LineItemsTable'

interface DeliveryNote {
  id: string
  supplier: string
  delivery_date: string
  total_value?: number | null
  filename?: string
}

interface DeliveryNoteCardProps {
  dn: DeliveryNote
}

export default function DeliveryNoteCard({ dn }: DeliveryNoteCardProps) {
  const formatCurrency = (value: number | null | undefined) => {
    if (value === null || value === undefined) return '—'
    return `£${(value / 100).toFixed(2)}`
  }

  const formatDate = (date: string) => {
    return new Date(date).toLocaleDateString('en-GB')
  }

  const shortId = dn.id.split('-')[0]

  return (
    <Card className="rounded-2xl shadow-sm">
      <CardHeader className="p-4 sm:p-6">
        <div className="flex items-center justify-between">
          <div className="flex-1 min-w-0">
            <CardTitle className="text-base font-semibold text-gray-900 truncate">
              {dn.supplier}
            </CardTitle>
            <div className="flex items-center gap-4 mt-1 text-sm text-gray-600">
              <span>{formatDate(dn.delivery_date)}</span>
              <span>•</span>
              <span className="font-mono">#{shortId}</span>
              {dn.filename && (
                <>
                  <span>•</span>
                  <span className="truncate max-w-32" title={dn.filename}>
                    {dn.filename}
                  </span>
                </>
              )}
              {dn.total_value && (
                <>
                  <span>•</span>
                  <span className="font-medium text-green-600">
                    {formatCurrency(dn.total_value)}
                  </span>
                </>
              )}
            </div>
          </div>
          <Badge variant="outline" className="bg-green-50 text-green-700 border-green-200">
            Available
          </Badge>
        </div>
      </CardHeader>
      
      <CardContent className="p-4 sm:p-6 pt-0">
        <Accordion type="single" collapsible className="w-full">
          <AccordionItem value="line-items">
            <AccordionTrigger className="text-sm font-medium">
              Line Items
            </AccordionTrigger>
            <AccordionContent className="pt-3">
              <LineItemsTable invoiceId={dn.id} type="delivery_note" />
            </AccordionContent>
          </AccordionItem>
        </Accordion>
      </CardContent>
    </Card>
  )
}
