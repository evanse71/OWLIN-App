import { describe, it, expect } from 'vitest'
import { normalizeUploadResponse } from '../src/lib/upload'

describe('normalizeUploadResponse', () => {
  it('should map STORI-like response with vendor_name, invoice_number, grand_total, ocr_confidence, pages, items', () => {
    const storiLike = {
      doc_id: 'test-doc-123',
      vendor_name: 'Stori Beer & Wine CYF',
      invoice_number: 'INV-2024-001',
      invoice_date: '2024-01-15',
      grand_total: 125.50,
      ocr_confidence: 92.5,
      pages: [
        { page_num: 1, confidence: 95.0, words: 150 },
        { page_num: 2, confidence: 90.0, words: 120 },
      ],
      items: [
        {
          name: 'Beer Case',
          qty: 2,
          unit_price_pence: 5000,
          line_total_pence: 10000,
        },
        {
          name: 'Wine Bottle',
          qty: 1,
          unit_price_pence: 2550,
          line_total_pence: 2550,
        },
      ],
    }

    const normalized = normalizeUploadResponse(storiLike, 'test.pdf', 1234567890)

    expect(normalized.id).toBe('test-doc-123')
    expect(normalized.supplier).toBe('Stori Beer & Wine CYF')
    expect(normalized.invoiceNo).toBe('INV-2024-001')
    expect(normalized.date).toBe('2024-01-15')
    expect(normalized.value).toBe(125.50)
    expect(normalized.confidence).toBe(92.5)
    expect(normalized.pages).toHaveLength(2)
    expect(normalized.pages?.[0]).toEqual({
      index: 1,
      confidence: 95.0,
      words: 150,
      psm: undefined,
    })
    expect(normalized.pages?.[1]).toEqual({
      index: 2,
      confidence: 90.0,
      words: 120,
      psm: undefined,
    })
    expect(normalized.lineItems).toHaveLength(2)
    expect(normalized.lineItems?.[0]).toMatchObject({
      description: 'Beer Case',
      qty: 2,
      price: 50.0, // pence converted to pounds
      total: 100.0,
    })
    expect(normalized.lineItems?.[1]).toMatchObject({
      description: 'Wine Bottle',
      qty: 1,
      price: 25.5,
      total: 25.5,
    })
    expect(normalized.raw).toBe(storiLike)
  })

  it('should map Tesseract-like response with flat text + confidence, sparse keys', () => {
    const tesseractLike = {
      id: 'tess-456',
      supplier: 'Generic Supplier Ltd',
      invoice_no: 'TESS-789',
      date: '2024-02-20',
      total: 89.99,
      confidence: 75.3,
      pages: [
        { index: 0, confidence: 70.0 },
        { index: 1, confidence: 80.0 },
      ],
      line_items: [
        {
          description: 'Item A',
          quantity: 3,
          unit_price: 15.0,
          line_total: 45.0,
        },
        {
          desc: 'Item B',
          qty: 2,
          price: 22.5,
          total: 45.0,
        },
      ],
    }

    const normalized = normalizeUploadResponse(tesseractLike, 'tesseract.pdf', 1234567890)

    expect(normalized.id).toBe('tess-456')
    expect(normalized.supplier).toBe('Generic Supplier Ltd')
    expect(normalized.invoiceNo).toBe('TESS-789')
    expect(normalized.date).toBe('2024-02-20')
    expect(normalized.value).toBe(89.99)
    expect(normalized.confidence).toBe(75.3)
    expect(normalized.pages).toHaveLength(2)
    expect(normalized.pages?.[0]).toEqual({
      index: 0,
      confidence: 70.0,
      words: undefined,
      psm: undefined,
    })
    expect(normalized.lineItems).toHaveLength(2)
    expect(normalized.lineItems?.[0]).toMatchObject({
      description: 'Item A',
      qty: 3,
      price: 15.0,
      total: 45.0,
    })
    expect(normalized.lineItems?.[1]).toMatchObject({
      description: 'Item B',
      qty: 2,
      price: 22.5,
      total: 45.0,
    })
    expect(normalized.raw).toBe(tesseractLike)
  })

  it('should map minimal response with only id', () => {
    const minimal = {
      doc_id: 'minimal-789',
      status: 'processing',
    }

    const normalized = normalizeUploadResponse(minimal, 'minimal.pdf', 1234567890)

    expect(normalized.id).toBe('minimal-789')
    expect(normalized.supplier).toBeUndefined()
    expect(normalized.invoiceNo).toBeUndefined()
    expect(normalized.date).toBeUndefined()
    expect(normalized.value).toBeUndefined()
    expect(normalized.confidence).toBeUndefined()
    expect(normalized.pages).toBeUndefined()
    expect(normalized.lineItems).toBeUndefined()
    expect(normalized.raw).toBe(minimal)
  })

  it('should handle parsed nested structure (from /api/upload/status)', () => {
    const statusResponse = {
      doc_id: 'status-123',
      status: 'ready',
      parsed: {
        supplier: 'Nested Supplier',
        invoice_no: 'NEST-001',
        date: '2024-03-10',
        value_pence: 50000, // 500.00 in pounds
        confidence: 88.5,
      },
      items: [
        {
          desc: 'Product X',
          qty: 5,
          unit_price: 100.0,
          total: 500.0,
        },
      ],
    }

    const normalized = normalizeUploadResponse(statusResponse, 'status.pdf', 1234567890)

    expect(normalized.id).toBe('status-123')
    expect(normalized.supplier).toBe('Nested Supplier')
    expect(normalized.invoiceNo).toBe('NEST-001')
    expect(normalized.date).toBe('2024-03-10')
    expect(normalized.value).toBe(500.0) // pence converted
    expect(normalized.confidence).toBe(88.5)
    expect(normalized.lineItems).toHaveLength(1)
    expect(normalized.lineItems?.[0]).toMatchObject({
      description: 'Product X',
      qty: 5,
      price: 100.0,
      total: 500.0,
    })
  })

  it('should handle invoice nested structure', () => {
    const invoiceResponse = {
      doc_id: 'inv-456',
      invoice: {
        id: 'invoice-789',
        supplier: 'Invoice Supplier',
        invoice_number: 'INV-999',
        invoice_date: '2024-04-01',
        value_pence: 75000,
        confidence: 95.0,
        items: [
          {
            name: 'Service A',
            qty: 1,
            unit_price: 750.0,
            line_total: 750.0,
          },
        ],
      },
    }

    const normalized = normalizeUploadResponse(invoiceResponse, 'invoice.pdf', 1234567890)

    expect(normalized.id).toBe('inv-456')
    expect(normalized.supplier).toBe('Invoice Supplier')
    expect(normalized.invoiceNo).toBe('INV-999')
    expect(normalized.date).toBe('2024-04-01')
    expect(normalized.value).toBe(750.0) // pence converted
    expect(normalized.confidence).toBe(95.0)
    expect(normalized.lineItems).toHaveLength(1)
    expect(normalized.lineItems?.[0]).toMatchObject({
      description: 'Service A',
      qty: 1,
      price: 750.0,
      total: 750.0,
    })
  })

  it('should handle value_pence conversion correctly', () => {
    const withPence = {
      doc_id: 'pence-test',
      value_pence: 12345, // Should become 123.45
    }

    const normalized = normalizeUploadResponse(withPence, 'pence.pdf', 1234567890)

    expect(normalized.value).toBe(123.45)
  })

  it('should fallback to filename+timestamp when no id provided', () => {
    const noId = {
      status: 'processing',
    }

    const normalized = normalizeUploadResponse(noId, 'fallback.pdf', 1234567890)

    expect(normalized.id).toBe('fallback.pdf-1234567890')
  })

  it('should handle missing optional fields gracefully', () => {
    const sparse = {
      doc_id: 'sparse-123',
      // No other fields
    }

    const normalized = normalizeUploadResponse(sparse, 'sparse.pdf', 1234567890)

    expect(normalized.id).toBe('sparse-123')
    expect(normalized.supplier).toBeUndefined()
    expect(normalized.invoiceNo).toBeUndefined()
    expect(normalized.date).toBeUndefined()
    expect(normalized.value).toBeUndefined()
    expect(normalized.confidence).toBeUndefined()
    expect(normalized.pages).toBeUndefined()
    expect(normalized.lineItems).toBeUndefined()
  })

  // Additional test fixtures from requirements
  it('FIXTURE A (STORI-like): should map vendor_name, invoice_number, grand_total, ocr_confidence, pages, items', () => {
    const fixtureA = {
      vendor_name: 'STORI LTD',
      invoice_number: 'INV-123',
      invoice_date: '2025-10-12',
      grand_total: 126.40,
      ocr_confidence: 83,
      pages: [{ index: 0, confidence: 82, words: 713, psm: '6' }],
      items: [{ name: 'Keg', quantity: 2, unit_price: 62.5, line_total: 125 }],
    }

    const normalized = normalizeUploadResponse(fixtureA, 'stori.pdf', Date.now())

    expect(normalized.supplier).toBe('STORI LTD')
    expect(normalized.invoiceNo).toBe('INV-123')
    expect(normalized.date).toBe('2025-10-12')
    expect(normalized.value).toBe(126.40)
    expect(normalized.confidence).toBe(83)
    expect(normalized.pages).toHaveLength(1)
    expect(normalized.pages?.[0]).toMatchObject({
      index: 0,
      confidence: 82,
      words: 713,
      psm: '6',
    })
    expect(normalized.lineItems).toHaveLength(1)
    expect(normalized.lineItems?.[0]).toMatchObject({
      description: 'Keg',
      qty: 2,
      price: 62.5,
      total: 125,
    })
  })

  it('FIXTURE B (Tesseract-like sparse): should handle sparse response with ocr_text', () => {
    const fixtureB = {
      id: 'abc',
      confidence: 71,
      ocr_text: '...STORI LTD... Total £126.40...',
    }

    const normalized = normalizeUploadResponse(fixtureB, 'tesseract.pdf', Date.now())

    expect(normalized.id).toBe('abc')
    expect(normalized.confidence).toBe(71)
    expect(normalized.supplier).toBeUndefined()
    expect(normalized.value).toBeUndefined()
    // OCR Preview should be available via raw.ocr_text
    expect(normalized.raw.ocr_text).toBe('...STORI LTD... Total £126.40...')
  })

  it('FIXTURE C (pence fields): should convert value_pence and use vendor', () => {
    const fixtureC = {
      invoice_id: 'X1',
      value_pence: 12640,
      vendor: 'Stori',
    }

    const normalized = normalizeUploadResponse(fixtureC, 'pence.pdf', Date.now())

    expect(normalized.id).toBe('X1')
    expect(normalized.value).toBe(126.40)
    expect(normalized.supplier).toBe('Stori')
  })

  it('should extract text from pages when available', () => {
    const withPageText = {
      doc_id: 'page-text-test',
      pages: [
        { index: 0, confidence: 85, text: 'Page 1 content here' },
        { index: 1, confidence: 80, text: 'Page 2 content here' },
      ],
    }

    const normalized = normalizeUploadResponse(withPageText, 'pages.pdf', Date.now())

    expect(normalized.pages).toHaveLength(2)
    expect(normalized.pages?.[0]).toMatchObject({
      index: 0,
      confidence: 85,
      text: 'Page 1 content here',
    })
    expect(normalized.pages?.[1]).toMatchObject({
      index: 1,
      confidence: 80,
      text: 'Page 2 content here',
    })
  })
})

