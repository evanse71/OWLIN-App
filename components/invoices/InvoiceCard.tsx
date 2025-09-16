import { useState } from 'react'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { ChevronRight, FileText, CheckCircle, AlertTriangle, Clock, ChevronDown, Edit, Save, X, Loader2 } from 'lucide-react'
import { formatCurrency, formatDateShort, pounds } from '@/lib/money'
import type { Invoice, LineItem } from '@/types'

interface InvoiceCardProps {
  invoice: Invoice
  items?: LineItem[]
  isSelected?: boolean
  onClick?: () => void
  onChange?: (patch: Partial<Invoice> & { line_items?: LineItem[] }) => void
  onRetry?: (invoiceId: string) => void
}

// VAT computation helpers
const toPounds = (p?: number | null) =>
  typeof p === 'number'
    ? `£${(p/100).toLocaleString('en-GB', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
    : '—';

// Progress donut component
function ProgressDonut({ progress }: { progress: number }) {
  const radius = 12
  const circumference = 2 * Math.PI * radius
  const strokeDasharray = circumference
  const strokeDashoffset = circumference - (progress / 100) * circumference
  
  return (
    <div className="relative w-6 h-6">
      <svg className="w-6 h-6 transform -rotate-90" viewBox="0 0 32 32">
        {/* Background circle */}
        <circle
          cx="16"
          cy="16"
          r={radius}
          stroke="currentColor"
          strokeWidth="2"
          fill="none"
          className="text-gray-200"
        />
        {/* Progress circle */}
        <circle
          cx="16"
          cy="16"
          r={radius}
          stroke="currentColor"
          strokeWidth="2"
          fill="none"
          strokeDasharray={strokeDasharray}
          strokeDashoffset={strokeDashoffset}
          className="text-blue-500 transition-all duration-300"
        />
      </svg>
      <div className="absolute inset-0 flex items-center justify-center text-xs font-medium">
        {progress}%
      </div>
    </div>
  )
}

export default function InvoiceCard({ 
  invoice, 
  items = [], 
  isSelected = false, 
  onClick,
  onChange,
  onRetry
}: InvoiceCardProps) {
  const [isExpanded, setIsExpanded] = useState(false)
  const [isEditing, setIsEditing] = useState(false)
  
  // Handle both line_items and items fields for backward compatibility
  const lineItems = invoice.line_items ?? invoice.items ?? items ?? []
  
  const [editData, setEditData] = useState({
    supplier_name: invoice.supplier_name || '',
    invoice_number: invoice.invoice_number || '',
    invoice_date: invoice.invoice_date || '',
    line_items: lineItems.map(item => ({ ...item }))
  })

  // Unified status logic - prefer data presence over status
  const isProcessing = invoice.status === 'processing' || typeof invoice.processing_progress === 'number';
  const progress = invoice.processing_progress || 0;
  const canRenderData = lineItems.length > 0 || invoice?.subtotal_p != null || invoice?.total_p != null;
  
  // Error handling logic
  const hasError = invoice.status === 'failed' || invoice.status === 'timeout';
  const showRetry = hasError && onRetry;
  const errorMessage = invoice.status === 'timeout' 
    ? 'Processing took too long (timeout). Try again or open in Edit.'
    : invoice.error_message || 'Processing failed. Try again or open in Edit.';
  
  // "Needs review" chip logic
  const needsReview = (invoice.confidence ?? 0) < 70
    || invoice.validation_flags?.includes('HEADER_WEAK')
    || invoice.validation_flags?.includes('LINES_WEAK')
    || invoice.validation_flags?.includes('TOTALS_WEAK');

  // VAT computation with fallbacks - never show dashes
  const toPounds = (p?: number | null) =>
    typeof p === 'number'
      ? `£${(p/100).toLocaleString('en-GB',{minimumFractionDigits:2,maximumFractionDigits:2})}`
      : '—';

  // items for this invoice are already passed in; if not, keep as []
  const itemsSubtotalP = Array.isArray(lineItems) ? lineItems.reduce((a,b)=>a+(b?.total||0),0) : null;

  const subtotalP = invoice.subtotal_p ?? itemsSubtotalP ?? null;
  const totalP    = invoice.total_p ?? ((invoice.subtotal_p!=null && invoice.vat_total_p!=null) ? invoice.subtotal_p + invoice.vat_total_p : null);
  const vatP      = invoice.vat_total_p ?? ((totalP!=null && subtotalP!=null) ? Math.max(0, totalP - subtotalP) : null);

  // Ensure we always have values for display
  const displaySubtotal = subtotalP ?? 0;
  const displayVat = vatP ?? 0;
  const displayTotal = totalP ?? invoice.total_amount ?? 0;
  
  let primary: {label: string; tone: 'neutral'|'success'|'warning'|'destructive'; icon: 'spinner'|'link'|'file'|'alert'}; 

  if (hasError) {
    primary = { label: 'failed', tone: 'destructive', icon: 'alert' };
  } else if (isProcessing && !canRenderData) {
    primary = { label: 'processing', tone: 'warning', icon: 'spinner' };
  } else if (invoice.paired) {
    primary = { label: 'matched', tone: 'success', icon: 'link' };
  } else if (invoice.status === 'parsed' || canRenderData) {
    primary = { label: 'parsed', tone: 'neutral', icon: 'file' };
  } else {
    primary = { label: 'scanned', tone: 'neutral', icon: 'file' };
  }

  const getPrimaryIcon = () => {
    switch (primary.icon) {
      case 'spinner':
        return <ProgressDonut progress={progress} />
      case 'link':
        return <CheckCircle className="h-4 w-4" />
      case 'file':
        return <FileText className="h-4 w-4" />
      case 'alert':
        return <AlertTriangle className="h-4 w-4" />
      default:
        return <FileText className="h-4 w-4" />
    }
  }

  const getPrimaryTone = () => {
    switch (primary.tone) {
      case 'success':
        return 'bg-green-100 text-green-800'
      case 'warning':
        return 'bg-yellow-100 text-yellow-800'
      case 'neutral':
        return 'bg-blue-100 text-blue-800'
      case 'destructive':
        return 'bg-red-100 text-red-800'
      default:
        return 'bg-gray-100 text-gray-800'
    }
  }

  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 80) return 'bg-green-100 text-green-800'
    if (confidence >= 50) return 'bg-yellow-100 text-yellow-800'
    return 'bg-red-100 text-red-800'
  }

  const handleCardClick = (e: React.MouseEvent) => {
    e.stopPropagation()
    setIsExpanded(!isExpanded)
    onClick?.()
  }

  const handleEdit = () => {
    setIsEditing(true)
    setEditData({
      supplier_name: invoice.supplier_name || '',
      invoice_number: invoice.invoice_number || '',
      invoice_date: invoice.invoice_date || '',
      line_items: lineItems.map(item => ({ ...item }))
    })
  }

  const handleSave = async () => {
    try {
      // Calculate total from line items
      const total_amount = editData.line_items.reduce((sum, item) => sum + (item.total || 0), 0)
      
      const patch = {
        supplier_name: editData.supplier_name,
        invoice_number: editData.invoice_number || null,
        invoice_date: editData.invoice_date || null,
        total_amount,
        line_items: editData.line_items
      }
      
      // Call PATCH /invoices/:id
      const response = await fetch(`/api/invoices/${invoice.id}`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(patch)
      })
      
      if (!response.ok) {
        throw new Error('Failed to save invoice')
      }
      
      // Update parent component
      onChange?.(patch)
      setIsEditing(false)
    } catch (error) {
      console.error('Save failed:', error)
      // You could add a toast notification here
    }
  }

  const handleCancel = () => {
    setIsEditing(false)
    setEditData({
      supplier_name: invoice.supplier_name || '',
      invoice_number: invoice.invoice_number || '',
      invoice_date: invoice.invoice_date || '',
      line_items: items.map(item => ({ ...item }))
    })
  }

  const updateLineItem = (index: number, field: keyof LineItem, value: any) => {
    const newItems = [...editData.line_items]
    newItems[index] = { ...newItems[index], [field]: value }
    
    // Auto-calculate total if qty or unit_price changed
    if (field === 'qty' || field === 'unit_price') {
      const item = newItems[index]
      newItems[index] = {
        ...item,
        total: (item.qty || 0) * (item.unit_price || 0)
      }
    }
    
    setEditData(prev => ({ ...prev, line_items: newItems }))
  }

  const addLineItem = () => {
    const newItem: LineItem = {
      description: '',
      qty: 1,
      unit_price: 0,
      total: 0
    }
    setEditData(prev => ({
      ...prev,
      line_items: [...prev.line_items, newItem]
    }))
  }

  const removeLineItem = (index: number) => {
    setEditData(prev => ({
      ...prev,
      line_items: prev.line_items.filter((_, i) => i !== index)
    }))
  }

  return (
    <Card 
      className={`ow-card cursor-pointer transition-colors hover:bg-[var(--ow-muted)]/50 ${
        isSelected ? 'ring-2 ring-[var(--ow-primary)]' : ''
      }`}
      onClick={handleCardClick}
    >
      <CardContent className="p-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            {getPrimaryIcon()}
            <div>
              <h3 className="font-medium text-[var(--ow-ink)]">
                {isEditing ? (
                  <Input
                    value={editData.invoice_number}
                    onChange={(e) => setEditData(prev => ({ ...prev, invoice_number: e.target.value }))}
                    className="w-32"
                    onClick={(e) => e.stopPropagation()}
                  />
                ) : (
                  // Show supplier name instead of "Processing..."
                  invoice.supplier_name || 'Unknown Supplier'
                )}
              </h3>
              <p className="text-sm text-[var(--ow-ink-dim)]">
                {isEditing ? (
                  <Input
                    value={editData.supplier_name}
                    onChange={(e) => setEditData(prev => ({ ...prev, supplier_name: e.target.value }))}
                    className="w-48"
                    onClick={(e) => e.stopPropagation()}
                  />
                ) : (
                  <div className="flex items-center gap-2">
                    <span>
                      {invoice.filename || invoice.invoice_number || 'billN13472213_1.pdf'}
                    </span>
                    {/* Page range badge */}
                    {invoice.page_range && (
                      <span className="text-[11px] rounded px-1.5 py-0.5 bg-neutral-100 text-neutral-600">
                        {invoice.page_range.includes('-') ? `pp. ${invoice.page_range}` : `p. ${invoice.page_range}`}
                      </span>
                    )}
                  </div>
                )}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <div className="text-right">
              <p className="font-medium text-[var(--ow-ink)]">
                {toPounds(totalP ?? null)}
              </p>
              <p className="text-sm text-[var(--ow-ink-dim)]">
                {invoice.invoice_date ? formatDateShort(invoice.invoice_date) : ''}
              </p>
            </div>
            {isExpanded ? (
              <ChevronDown className="h-4 w-4 text-[var(--ow-ink-dim)]" />
            ) : (
              <ChevronRight className="h-4 w-4 text-[var(--ow-ink-dim)]" />
            )}
          </div>
        </div>
        
        {/* Unified status badges */}
        <div className="flex items-center gap-2 mt-3">
          <Badge className={getPrimaryTone()}>
            {primary.label}
          </Badge>
          
          {/* Only show confidence when not processing */}
          {!isProcessing && (
            <Badge className={getConfidenceColor(invoice.confidence)}>
              {invoice.confidence}% confidence
            </Badge>
          )}
          
          {/* "Needs review" chip */}
          {needsReview && (
            <Badge variant="outline" className="text-orange-600 border-orange-300">
              Needs review
            </Badge>
          )}
          
          {/* Only show issues when not processing */}
          {!isProcessing && invoice.issues_count && invoice.issues_count > 0 && (
            <Badge variant="destructive">
              {invoice.issues_count} issues
            </Badge>
          )}
        </div>

        {/* Error banner for failed/timeout invoices */}
        {hasError && (
          <div className="mt-3 p-3 bg-red-50 border border-red-200 rounded-md">
            <div className="flex items-center justify-between">
              <p className="text-sm text-red-700">{errorMessage}</p>
              {showRetry && (
                <Button 
                  size="sm" 
                  variant="outline" 
                  onClick={(e) => { 
                    e.stopPropagation(); 
                    onRetry(invoice.id); 
                  }}
                  className="text-red-700 border-red-300 hover:bg-red-100"
                >
                  Retry
                </Button>
              )}
            </div>
          </div>
        )}

        {/* Expanded content */}
        {isExpanded && (
          <div className="mt-4 pt-4 border-t border-[var(--ow-border)]">
            <div className="flex items-center justify-between mb-3">
              <h4 className="font-medium text-[var(--ow-ink)]">Line Items</h4>
              {!isEditing ? (
                <Button size="sm" onClick={(e) => { e.stopPropagation(); handleEdit(); }}>
                  <Edit className="h-4 w-4 mr-2" />
                  Edit Invoice
                </Button>
              ) : (
                <div className="flex gap-2">
                  <Button size="sm" onClick={(e) => { e.stopPropagation(); handleSave(); }}>
                    <Save className="h-4 w-4 mr-2" />
                    Save
                  </Button>
                  <Button size="sm" variant="outline" onClick={(e) => { e.stopPropagation(); handleCancel(); }}>
                    <X className="h-4 w-4 mr-2" />
                    Cancel
                  </Button>
                </div>
              )}
            </div>
            
            {isEditing ? (
              <div className="space-y-3">
                {editData.line_items.map((item, index) => (
                  <div key={index} className="p-3 bg-[var(--ow-muted)]/30 rounded border">
                    <div className="grid grid-cols-12 gap-2 items-center">
                      <div className="col-span-4">
                        <Input
                          value={item.description ?? ''}
                          onChange={(e) => updateLineItem(index, 'description', e.target.value)}
                          placeholder="Description"
                          onClick={(e) => e.stopPropagation()}
                        />
                      </div>
                      <div className="col-span-2">
                        <Input
                          type="number"
                          value={Number.isFinite(item.qty) ? item.qty : 0}
                          onChange={(e) => updateLineItem(index, 'qty', parseFloat(e.target.value) || 0)}
                          placeholder="Qty"
                          onClick={(e) => e.stopPropagation()}
                        />
                      </div>
                      <div className="col-span-2">
                        <Input
                          type="number"
                          value={Number.isFinite(item.unit_price) ? item.unit_price : 0}
                          onChange={(e) => updateLineItem(index, 'unit_price', parseFloat(e.target.value) || 0)}
                          placeholder="Unit £"
                          onClick={(e) => e.stopPropagation()}
                        />
                      </div>
                      <div className="col-span-2">
                        <Select 
                          value={item.vat_rate?.toString() ?? '0'} 
                          onValueChange={(value) => updateLineItem(index, 'vat_rate', value === '' ? null : parseFloat(value))}
                        >
                          <SelectTrigger onClick={(e) => e.stopPropagation()}>
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="">—</SelectItem>
                            <SelectItem value="0">0%</SelectItem>
                            <SelectItem value="20">20%</SelectItem>
                            <SelectItem value="5">5%</SelectItem>
                          </SelectContent>
                        </Select>
                      </div>
                      <div className="col-span-1 text-right">
                        <span className="font-medium text-[var(--ow-ink)]">
                          {formatCurrency(item.total || 0)}
                        </span>
                      </div>
                      <div className="col-span-1">
                        <Button 
                          size="sm" 
                          variant="outline" 
                          onClick={(e) => { e.stopPropagation(); removeLineItem(index); }}
                        >
                          <X className="h-3 w-3" />
                        </Button>
                      </div>
                    </div>
                  </div>
                ))}
                <Button size="sm" variant="outline" onClick={(e) => { e.stopPropagation(); addLineItem(); }}>
                  + Add Item
                </Button>
              </div>
            ) : (
              <div className="space-y-2">
                {lineItems.length > 0 ? (
                  lineItems.map((item, index) => (
                    <div key={index} className="flex items-center justify-between p-2 bg-[var(--ow-muted)]/30 rounded">
                      <div className="flex-1">
                        <p className="font-medium text-sm text-[var(--ow-ink)]">{item.description}</p>
                        <p className="text-xs text-[var(--ow-ink-dim)]">
                          Qty: {item.qty} × {formatCurrency(item.unit_price || 0)}
                        </p>
                      </div>
                      <div className="text-right">
                        <p className="font-medium text-sm text-[var(--ow-ink)]">
                          {formatCurrency(item.total || 0)}
                        </p>
                      </div>
                    </div>
                  ))
                ) : (
                  <p className="text-sm text-[var(--ow-ink-dim)]">No line items available</p>
                )}
                
                {/* VAT Summary - Show when not processing and VAT data is available */}
                {!isProcessing && (
                  <div className="mt-4 pt-3 border-t border-[var(--ow-border)]">
                    <div className="space-y-1 text-sm">
                      <div className="flex justify-between">
                        <span className="text-[var(--ow-ink-dim)]">Subtotal</span>
                        <span className="text-[var(--ow-ink)]">{toPounds(subtotalP)}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-[var(--ow-ink-dim)]">
                          VAT{items?.[0]?.vat_rate != null ? ` (${items[0].vat_rate}%)` : ''}
                        </span>
                        <span className="text-[var(--ow-ink)]">{toPounds(vatP)}</span>
                      </div>
                      <div className="flex justify-between font-medium pt-1 border-t border-[var(--ow-border)]">
                        <span className="text-[var(--ow-ink)]">Total</span>
                        <span className="text-[var(--ow-ink)]">
                          {toPounds(totalP)}
                        </span>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  )
} 