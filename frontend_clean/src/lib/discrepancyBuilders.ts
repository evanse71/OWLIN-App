/**
 * Discrepancy Builders
 * Build discrepancy items from invoice data
 */

import type { DiscrepancyItem } from './discrepanciesApi'
import type { InvoiceDetail } from '../components/invoices/DocumentDetailPanel'
import type { InvoiceListItem } from '../components/invoices/DocumentList'

function formatInvoiceNumber(invoiceNumber?: string, id?: string): string {
  if (invoiceNumber) {
    // If already in INV-XXX format, use it; otherwise format it
    if (/^INV-?/i.test(invoiceNumber)) {
      return invoiceNumber.toUpperCase().replace(/^INV-?/, 'INV-')
    }
    return `INV-${invoiceNumber}`
  }
  // Fallback to ID if no invoice number
  if (id) {
    return `INV-${String(id).slice(-4).padStart(4, '0')}`
  }
  return 'INV-XXXX'
}

export function buildInvoiceDetailDiscrepancies(invoice: InvoiceDetail | null): DiscrepancyItem[] {
  if (!invoice) return []
  
  const discrepancies: DiscrepancyItem[] = []
  const invoiceNum = formatInvoiceNumber(invoice.invoiceNumber, invoice.id)
  const contextLabel = `Invoice • ${invoiceNum}`
  
  // Check for missing delivery note
  if (!invoice.deliveryNote && !invoice.matched) {
    discrepancies.push({
      id: `missing-dn-${invoice.id}`,
      type: 'missing_delivery_note',
      severity: 'warning',
      level: 'major',
      title: `Invoice ${invoiceNum} is not linked to a delivery note`,
      description: 'Link a delivery note or check if this invoice was delivered.',
      contextLabel,
      focusTarget: 'delivery_link',
      actions: [
        {
          actionType: 'scroll',
          target: 'delivery_link',
          label: 'Link Delivery Note'
        }
      ],
      contextRef: {
        type: 'invoice',
        id: invoice.id
      },
      createdAt: new Date().toISOString()
    })
  }
  
  // Check for total/line items mismatch
  if (invoice.value !== undefined && invoice.lineItems && invoice.lineItems.length > 0) {
    const lineItemsTotal = invoice.lineItems.reduce((sum, item) => {
      const qty = item.qty || 0
      const price = item.unitPrice || 0
      return sum + (qty * price)
    }, 0)
    const difference = Math.abs(invoice.value - lineItemsTotal)
    // Consider it a big mismatch if difference is more than 1% of total or more than £10
    const threshold = Math.max(invoice.value * 0.01, 10)
    if (difference > threshold) {
      discrepancies.push({
        id: `mismatch-${invoice.id}`,
        type: 'total_mismatch',
        severity: 'critical',
        level: 'critical',
        title: `Big mismatch in invoice ${invoiceNum}`,
        description: `Total and line items differ by £${difference.toFixed(2)}.`,
        contextLabel,
        focusTarget: 'line_items',
        contextRef: {
          type: 'invoice',
          id: invoice.id
        },
        createdAt: new Date().toISOString()
      })
    }
  }
  
  // Check for low OCR confidence
  if (invoice.confidence !== null && invoice.confidence !== undefined && invoice.confidence < 0.7) {
    discrepancies.push({
      id: `low-confidence-${invoice.id}`,
      type: 'low_confidence',
      severity: 'info',
      level: 'minor',
      title: `Check invoice ${invoiceNum} before submitting`,
      description: 'Some values were hard to read. Double-check totals and VAT.',
      contextLabel,
      focusTarget: 'invoice_header',
      contextRef: {
        type: 'invoice',
        id: invoice.id
      },
      createdAt: new Date().toISOString()
    })
  }
  
  // Check for flagged invoices
  if (invoice.flagged) {
    discrepancies.push({
      id: `flagged-${invoice.id}`,
      type: 'flagged',
      severity: 'warning',
      level: 'major',
      title: `Invoice ${invoiceNum} needs review`,
      description: 'This invoice has been flagged for review.',
      contextLabel,
      focusTarget: 'invoice_header',
      contextRef: {
        type: 'invoice',
        id: invoice.id
      },
      createdAt: new Date().toISOString()
    })
  }
  
  return discrepancies
}

export function buildInvoiceListDiscrepancies(invoices: InvoiceListItem[]): DiscrepancyItem[] {
  const discrepancies: DiscrepancyItem[] = []
  
  // Count unpaired invoices
  const unpairedCount = invoices.filter(inv => !inv.matched && !inv.hasDeliveryNote).length
  if (unpairedCount > 0) {
    discrepancies.push({
      id: 'unpaired-invoices',
      type: 'unpaired_invoices',
      severity: 'warning',
      level: 'major',
      title: `${unpairedCount} invoice${unpairedCount !== 1 ? 's' : ''} not linked to delivery notes`,
      description: unpairedCount === 1 
        ? 'One invoice needs to be linked to a delivery note.'
        : `${unpairedCount} invoices need to be linked to delivery notes.`,
      actions: [
        {
          actionType: 'filter',
          target: 'unpaired',
          label: 'Show Unpaired'
        }
      ],
      contextRef: {
        type: 'system'
      },
      createdAt: new Date().toISOString()
    })
  }
  
  // Count flagged invoices
  const flaggedCount = invoices.filter(inv => inv.flagged || (inv.issuesCount && inv.issuesCount > 0)).length
  if (flaggedCount > 0) {
    discrepancies.push({
      id: 'flagged-invoices',
      type: 'flagged_invoices',
      severity: 'warning',
      level: 'major',
      title: `${flaggedCount} invoice${flaggedCount !== 1 ? 's' : ''} need${flaggedCount === 1 ? 's' : ''} review`,
      description: flaggedCount === 1
        ? 'One invoice has been flagged and needs your attention.'
        : `${flaggedCount} invoices have been flagged and need your attention.`,
      actions: [
        {
          actionType: 'filter',
          target: 'flagged',
          label: 'Show Flagged'
        }
      ],
      contextRef: {
        type: 'system'
      },
      createdAt: new Date().toISOString()
    })
  }
  
  return discrepancies
}
