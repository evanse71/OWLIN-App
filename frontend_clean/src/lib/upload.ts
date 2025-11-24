import { API_BASE_URL } from './config'
import { normalizeInvoiceRecord, normalizeInvoicesPayload } from './api'

export interface PageInfo {
  index: number
  confidence?: number
  words?: number
  psm?: string | number
  text?: string
}

export interface LineItem {
  description?: string
  item?: string
  qty?: number
  quantity?: number
  unit?: string
  uom?: string
  price?: number
  unit_price?: number
  total?: number
  line_total?: number
  [key: string]: unknown
}

export interface InvoiceMetadata {
  id?: string
  supplier?: string
  invoiceNo?: string
  date?: string
  value?: number
  confidence?: number
  pages?: PageInfo[]
  lineItems?: LineItem[]
  raw?: any // Keep original for DEV drawer
  [key: string]: unknown
}

export interface UploadProgress {
  loaded: number
  total: number
  percentage: number
}

export interface UploadResult {
  success: boolean
  metadata?: InvoiceMetadata
  error?: string
}

export interface UploadOptions {
  onProgress?: (progress: UploadProgress) => void
  onComplete?: (metadata: InvoiceMetadata) => void
}

/**
 * Normalize backend upload response to consistent frontend format.
 * Handles various field name variations from different extractors (STORI, Tesseract, etc.)
 */
export function normalizeUploadResponse(raw: any, fileName?: string, timestamp?: number): InvoiceMetadata {
  // Generate ID: prefer doc_id, then id, then fallback to filename+timestamp
  const id =
    raw.doc_id ||
    raw.id ||
    raw.invoice_id ||
    raw.invoice_no ||
    raw.invoice_number ||
    raw.doc_id ||
    (fileName && timestamp ? `${fileName}-${timestamp}` : undefined) ||
    String(Date.now())

  // Extract supplier/vendor name (check multiple possible keys)
  const supplier =
    raw.supplier ||
    raw.supplier_name ||
    raw.vendor ||
    raw.vendor_name ||
    (raw.parsed && (raw.parsed.supplier || raw.parsed.supplier_name || raw.parsed.vendor || raw.parsed.vendor_name)) ||
    (raw.invoice && (raw.invoice.supplier || raw.invoice.supplier_name || raw.invoice.vendor || raw.invoice.vendor_name))

  // Extract invoice number
  const invoiceNo =
    raw.invoice_no ||
    raw.invoice_number ||
    raw.invoiceId ||
    raw.invoice_id ||
    (raw.parsed && (raw.parsed.invoice_no || raw.parsed.invoice_number || raw.parsed.invoice_id)) ||
    (raw.invoice && (raw.invoice.invoice_no || raw.invoice.invoice_number || raw.invoice.invoice_id))

  // Extract date
  const date =
    raw.date ||
    raw.invoice_date ||
    raw.doc_date ||
    (raw.parsed && (raw.parsed.date || raw.parsed.invoice_date || raw.parsed.doc_date)) ||
    (raw.invoice && (raw.invoice.date || raw.invoice.invoice_date || raw.invoice.doc_date))

  // Extract value/total (handle pence conversion)
  let value: number | undefined
  if (raw.value !== undefined && raw.value !== null) {
    value = typeof raw.value === 'number' ? raw.value : parseFloat(String(raw.value))
  } else if (raw.total !== undefined && raw.total !== null) {
    value = typeof raw.total === 'number' ? raw.total : parseFloat(String(raw.total))
  } else if (raw.grand_total !== undefined && raw.grand_total !== null) {
    value = typeof raw.grand_total === 'number' ? raw.grand_total : parseFloat(String(raw.grand_total))
  } else if (raw.amount !== undefined && raw.amount !== null) {
    value = typeof raw.amount === 'number' ? raw.amount : parseFloat(String(raw.amount))
  } else if (raw.value_pence !== undefined && raw.value_pence !== null) {
    // Convert pence to pounds
    const pence = typeof raw.value_pence === 'number' ? raw.value_pence : parseFloat(String(raw.value_pence))
    value = pence / 100.0
  } else if (raw.parsed) {
    if (raw.parsed.value !== undefined && raw.parsed.value !== null) {
      value = typeof raw.parsed.value === 'number' ? raw.parsed.value : parseFloat(String(raw.parsed.value))
    } else if (raw.parsed.value_pence !== undefined && raw.parsed.value_pence !== null) {
      const pence = typeof raw.parsed.value_pence === 'number' ? raw.parsed.value_pence : parseFloat(String(raw.parsed.value_pence))
      value = pence / 100.0
    } else if (raw.parsed.total !== undefined && raw.parsed.total !== null) {
      value = typeof raw.parsed.total === 'number' ? raw.parsed.total : parseFloat(String(raw.parsed.total))
    }
  } else if (raw.invoice) {
    if (raw.invoice.value !== undefined && raw.invoice.value !== null) {
      value = typeof raw.invoice.value === 'number' ? raw.invoice.value : parseFloat(String(raw.invoice.value))
    } else if (raw.invoice.value_pence !== undefined && raw.invoice.value_pence !== null) {
      const pence = typeof raw.invoice.value_pence === 'number' ? raw.invoice.value_pence : parseFloat(String(raw.invoice.value_pence))
      value = pence / 100.0
    } else if (raw.invoice.total !== undefined && raw.invoice.total !== null) {
      value = typeof raw.invoice.total === 'number' ? raw.invoice.total : parseFloat(String(raw.invoice.total))
    }
  }

  // Extract confidence
  const confidence =
    raw.confidence !== undefined && raw.confidence !== null
      ? (typeof raw.confidence === 'number' ? raw.confidence : parseFloat(String(raw.confidence)))
      : raw.ocr_confidence !== undefined && raw.ocr_confidence !== null
        ? (typeof raw.ocr_confidence === 'number' ? raw.ocr_confidence : parseFloat(String(raw.ocr_confidence)))
        : raw.overall_confidence !== undefined && raw.overall_confidence !== null
          ? (typeof raw.overall_confidence === 'number' ? raw.overall_confidence : parseFloat(String(raw.overall_confidence)))
          : (raw.parsed && raw.parsed.confidence !== undefined && raw.parsed.confidence !== null
              ? (typeof raw.parsed.confidence === 'number' ? raw.parsed.confidence : parseFloat(String(raw.parsed.confidence)))
              : (raw.invoice && raw.invoice.confidence !== undefined && raw.invoice.confidence !== null
                  ? (typeof raw.invoice.confidence === 'number' ? raw.invoice.confidence : parseFloat(String(raw.invoice.confidence)))
                  : undefined))

  // Extract pages
  let pages: PageInfo[] | undefined
  const pagesRaw = raw.pages || raw.ocr_pages || raw.page_metrics || (raw.parsed && raw.parsed.pages)
  if (Array.isArray(pagesRaw)) {
    pages = pagesRaw.map((page: any, idx: number) => ({
      index: page.index !== undefined ? page.index : page.page_num !== undefined ? page.page_num : idx + 1,
      confidence: page.confidence !== undefined ? (typeof page.confidence === 'number' ? page.confidence : parseFloat(String(page.confidence))) : undefined,
      words: page.words !== undefined ? (typeof page.words === 'number' ? page.words : parseInt(String(page.words), 10)) : undefined,
      psm: page.psm !== undefined ? page.psm : undefined,
      text: page.text || page.ocr_text || page.extracted_text || undefined,
    }))
  }

  // Extract line items
  let lineItems: LineItem[] | undefined
  const itemsRaw = raw.line_items || raw.items || raw.lines || (raw.parsed && (raw.parsed.line_items || raw.parsed.items)) || (raw.invoice && (raw.invoice.items || raw.invoice.line_items))
  if (Array.isArray(itemsRaw)) {
    lineItems = itemsRaw.map((item: any) => {
      // Handle price (check for pence conversion)
      let price: number | undefined
      if (item.price !== undefined && item.price !== null) {
        price = typeof item.price === 'number' ? item.price : parseFloat(String(item.price))
      } else if (item.unit_price !== undefined && item.unit_price !== null) {
        price = typeof item.unit_price === 'number' ? item.unit_price : parseFloat(String(item.unit_price))
      } else if (item.unit_price_pence !== undefined && item.unit_price_pence !== null) {
        const pence = typeof item.unit_price_pence === 'number' ? item.unit_price_pence : parseFloat(String(item.unit_price_pence))
        price = pence / 100.0
      }

      // Handle total (check for pence conversion)
      let total: number | undefined
      if (item.total !== undefined && item.total !== null) {
        total = typeof item.total === 'number' ? item.total : parseFloat(String(item.total))
      } else if (item.line_total !== undefined && item.line_total !== null) {
        total = typeof item.line_total === 'number' ? item.line_total : parseFloat(String(item.line_total))
      } else if (item.line_total_pence !== undefined && item.line_total_pence !== null) {
        const pence = typeof item.line_total_pence === 'number' ? item.line_total_pence : parseFloat(String(item.line_total_pence))
        total = pence / 100.0
      }

      return {
        description: item.description || item.desc || item.name || item.item || '',
        qty: item.qty !== undefined ? (typeof item.qty === 'number' ? item.qty : parseFloat(String(item.qty))) : item.quantity !== undefined ? (typeof item.quantity === 'number' ? item.quantity : parseFloat(String(item.quantity))) : undefined,
        unit: item.unit || item.uom || '',
        price,
        total,
        // Keep original item for reference
        ...item,
      }
    })
  }

  const result = {
    id,
    supplier,
    invoiceNo,
    date,
    value,
    confidence,
    pages,
    lineItems,
    raw, // Keep original for DEV drawer
  }

  // Apply centralized normalization for field aliases and line item normalization
  return normalizeInvoiceRecord(result) as InvoiceMetadata
}

/**
 * Poll upload status endpoint until processing is complete
 * @param docId - Document ID from upload response
 * @param maxAttempts - Maximum number of polling attempts (default: 40 = ~60 seconds)
 * @param intervalMs - Polling interval in milliseconds (default: 1500ms)
 * @returns Promise resolving to normalized metadata or null if timeout
 */
async function pollUploadStatus(
  docId: string,
  maxAttempts: number = 40,
  intervalMs: number = 1500
): Promise<InvoiceMetadata | null> {
  for (let attempt = 0; attempt < maxAttempts; attempt++) {
    try {
      const response = await fetch(`${API_BASE_URL}/api/upload/status?doc_id=${encodeURIComponent(docId)}`)
      if (!response.ok) {
        await new Promise((resolve) => setTimeout(resolve, intervalMs))
        continue
      }

      const statusData = await response.json()

      // Check if processing is complete (has parsed data AND status is ready, OR has items)
      // Use optional chaining and check for truthy values (not just existence)
      const hasData = (statusData?.parsed && Object.keys(statusData.parsed).length > 0) || 
                      (statusData?.invoice && Object.keys(statusData.invoice).length > 0)
      const hasItems = Array.isArray(statusData?.items) && statusData.items.length > 0
      const isReady = statusData?.status === 'ready' || 
                      statusData?.status === 'scanned' || 
                      statusData?.status === 'completed' ||
                      statusData?.status === 'submitted' ||
                      statusData?.status === 'duplicate'

      // Only stop polling if we have items OR status is ready/completed/scanned
      // This ensures we wait for line items to be inserted before stopping
      // Priority: if we have items, stop immediately (even if status isn't ready yet)
      // Also accept ready/scanned/completed status even if some optional fields are null
      if (hasItems || isReady) {
        // Merge status response into a format normalizeUploadResponse can handle
        // The status endpoint returns: { doc_id, status, parsed: {...}, items: [...], invoice: {...} }
        // We need to flatten it for normalization
        // Use optional chaining to safely spread potentially undefined objects
        const mergedResponse = {
          ...statusData,
          ...(statusData?.parsed || {}),
          ...(statusData?.invoice || {}),
          // Ensure line_items is available (from items or invoice.items)
          line_items: statusData?.items || statusData?.line_items || statusData?.invoice?.items || statusData?.invoice?.line_items || [],
          items: statusData?.items || statusData?.line_items || statusData?.invoice?.items || statusData?.invoice?.line_items || [],
          // Ensure supplier is available (from parsed or invoice)
          supplier: statusData?.supplier || statusData?.parsed?.supplier || statusData?.invoice?.supplier || statusData?.supplier_name || statusData?.parsed?.supplier_name || statusData?.invoice?.supplier_name,
          supplier_name: statusData?.supplier_name || statusData?.parsed?.supplier_name || statusData?.invoice?.supplier_name || statusData?.supplier || statusData?.parsed?.supplier || statusData?.invoice?.supplier,
          // Ensure total/total_value is available
          total: statusData?.total || statusData?.parsed?.total || statusData?.invoice?.total,
          total_value: statusData?.total_value || statusData?.parsed?.total_value || statusData?.invoice?.total_value || statusData?.total || statusData?.parsed?.total || statusData?.invoice?.total,
          value: statusData?.value || statusData?.parsed?.value || statusData?.invoice?.value || statusData?.total || statusData?.parsed?.total || statusData?.invoice?.total,
          // Preserve raw for debug
          raw: statusData,
        }

        // Apply normalization to status payload before returning
        // This will convert snake_case to camelCase and apply field aliases
        const normalized = normalizeUploadResponse(mergedResponse, undefined, Date.now())
        return normalized
      }

      // Still processing, wait and retry
      await new Promise((resolve) => setTimeout(resolve, intervalMs))
    } catch (error) {
      console.warn(`Poll attempt ${attempt + 1} failed:`, error)
      await new Promise((resolve) => setTimeout(resolve, intervalMs))
    }
  }

  // Timeout - return null to indicate processing not complete
  return null
}

/**
 * Upload a file using XMLHttpRequest for accurate progress tracking
 * @param file - File to upload
 * @param options - Upload options including progress callback
 * @returns Promise resolving to upload result with metadata or error
 */
export function uploadFile(
  file: File,
  options: UploadOptions = {}
): Promise<UploadResult> {
  return new Promise((resolve) => {
    const xhr = new XMLHttpRequest()
    const formData = new FormData()
    formData.append('file', file)

    // Track upload progress
    xhr.upload.addEventListener('progress', (e) => {
      if (e.lengthComputable && options.onProgress) {
        const progress: UploadProgress = {
          loaded: e.loaded,
          total: e.total,
          percentage: Math.round((e.loaded / e.total) * 100),
        }
        options.onProgress(progress)
      }
    })

    // Handle completion
    xhr.addEventListener('load', async () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        try {
          const rawResponse = JSON.parse(xhr.responseText)
          const docId = rawResponse.doc_id || rawResponse.id || rawResponse.existing_doc_id

          // If status is "processing" or "duplicate", poll for results
          // Duplicates need polling too because they might have existing invoice/line items
          if ((rawResponse.status === 'processing' || rawResponse.status === 'duplicate') && docId) {
            // Return initial response immediately, then poll in background
            const initialMetadata = normalizeUploadResponse(rawResponse, file.name, Date.now())
            resolve({
              success: true,
              metadata: initialMetadata,
            })

            // Poll for complete data in background (works for both new uploads and duplicates)
            const completeMetadata = await pollUploadStatus(docId)
            if (completeMetadata) {
              // Update via callback if provided
              if (options.onComplete) {
                options.onComplete(completeMetadata)
              }
            }
            return
          }

          // Normalize the response to handle various backend field name variations
          const metadata = normalizeUploadResponse(rawResponse, file.name, Date.now())
          resolve({
            success: true,
            metadata,
          })
        } catch (error) {
          resolve({
            success: false,
            error: `Failed to parse response: ${error instanceof Error ? error.message : 'Unknown error'}`,
          })
        }
      } else {
        resolve({
          success: false,
          error: `Upload failed: ${xhr.status} ${xhr.statusText}`,
        })
      }
    })

    // Handle errors
    xhr.addEventListener('error', () => {
      resolve({
        success: false,
        error: 'Network error: Failed to connect to server',
      })
    })

    xhr.addEventListener('abort', () => {
      resolve({
        success: false,
        error: 'Upload cancelled',
      })
    })

    // Start upload
    xhr.open('POST', `${API_BASE_URL}/api/upload`)
    xhr.send(formData)
  })
}

