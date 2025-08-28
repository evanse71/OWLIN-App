import { render, screen } from '@testing-library/react'
import InvoiceCard from '@/components/invoices/InvoiceCard'
import type { Invoice, LineItem } from '@/types'

// Mock the formatCurrency function
jest.mock('@/lib/money', () => ({
  formatCurrency: (amount: number) => `£${(amount / 100).toFixed(2)}`,
  formatDateShort: (date: string) => date,
  pounds: (pence: number) => `£${(pence / 100).toFixed(2)}`
}))

const mockInvoice: Invoice = {
  id: 'inv_123',
  supplier_name: 'Test Supplier',
  invoice_number: 'INV-001',
  invoice_date: '2024-01-01',
  status: 'scanned',
  total_amount: 1000,
  confidence: 85,
  paired: 0
}

const mockLineItem: LineItem = {
  description: 'Test Item',
  qty: 2,
  unit_price: 500,
  total: 1000,
  vat_rate: 20
}

describe('InvoiceCard Field Mapping', () => {
  it('renders line items when invoice has line_items field', () => {
    const invoiceWithLineItems = {
      ...mockInvoice,
      line_items: [mockLineItem]
    }
    
    render(<InvoiceCard invoice={invoiceWithLineItems} />)
    
    expect(screen.getByText('Test Item')).toBeInTheDocument()
    expect(screen.getByText('Qty: 2 × £5.00')).toBeInTheDocument()
    expect(screen.getByText('£10.00')).toBeInTheDocument()
  })

  it('renders line items when invoice has items field (backward compatibility)', () => {
    const invoiceWithItems = {
      ...mockInvoice,
      items: [mockLineItem]
    }
    
    render(<InvoiceCard invoice={invoiceWithItems} />)
    
    expect(screen.getByText('Test Item')).toBeInTheDocument()
    expect(screen.getByText('Qty: 2 × £5.00')).toBeInTheDocument()
    expect(screen.getByText('£10.00')).toBeInTheDocument()
  })

  it('renders line items when items are passed as prop', () => {
    render(<InvoiceCard invoice={mockInvoice} items={[mockLineItem]} />)
    
    expect(screen.getByText('Test Item')).toBeInTheDocument()
    expect(screen.getByText('Qty: 2 × £5.00')).toBeInTheDocument()
    expect(screen.getByText('£10.00')).toBeInTheDocument()
  })

  it('shows "No line items available" when no items are present', () => {
    render(<InvoiceCard invoice={mockInvoice} />)
    
    expect(screen.getByText('No line items available')).toBeInTheDocument()
  })

  it('prioritizes line_items over items field', () => {
    const invoiceWithBoth = {
      ...mockInvoice,
      line_items: [mockLineItem],
      items: [{ description: 'Wrong Item', qty: 1, unit_price: 100, total: 100 }]
    }
    
    render(<InvoiceCard invoice={invoiceWithBoth} />)
    
    expect(screen.getByText('Test Item')).toBeInTheDocument()
    expect(screen.queryByText('Wrong Item')).not.toBeInTheDocument()
  })
}) 