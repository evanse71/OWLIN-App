// API Service configuration
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api';

// Type definitions
export interface FileStatus {
  id: string;
  original_filename: string;
  file_type: 'invoice' | 'delivery_note';
  processing_status: 'pending' | 'processing' | 'completed' | 'failed';
  confidence?: number;
  upload_timestamp: string;
  error_message?: string;
  document_status?: string;
}

export interface LineItem {
  id?: string;
  description: string;
  quantity: number;
  unit: string;
  unit_price: number;
  vat_rate: number;
  line_total: number;
  page: number;
  row_idx: number;
  confidence: number;
  flags: string[];
}

export interface Address {
  supplier_address?: string;
  delivery_address?: string;
}

export interface SignatureRegion {
  page: number;
  bbox: { x: number; y: number; width: number; height: number };
  image_b64: string;
}

export interface Invoice {
  id: string;
  invoice_number: string;
  invoice_date: string;
  supplier_name: string;
  total_amount: number;
  subtotal?: number;
  vat?: number;
  vat_rate?: number;
  total_incl_vat?: number;
  status: 'scanned' | 'processed' | 'error' | 'manual_review' | 'unmatched' | 'waiting' | 'utility' | 'matched' | 'processing';
  confidence?: number;
  upload_timestamp?: string;
  parent_pdf_filename?: string;
  line_items?: LineItem[];
  page_range?: string;
  word_count?: number;
  psm_used?: string;
  was_retried?: boolean;
  raw_ocr_text?: string;
  ocr_pages?: Array<{
    page: number;
    text: string;
    avg_confidence: number;
    word_count: number;
    psm_used?: string;
  }>;
  price_mismatches?: Array<{
    description: string;
    invoice_amount: number;
    delivery_amount: number;
    difference: number;
  }>;
  // New fields for vertical cards
  field_confidence?: Record<string, number>;
  addresses?: Address;
  signature_regions?: SignatureRegion[];
  verification_status?: 'unreviewed' | 'needs_review' | 'reviewed';
}

export interface DeliveryNote {
  id: string;
  delivery_number?: string;
  delivery_note_number?: string;
  delivery_date?: string;
  supplier_name?: string;
  total_amount?: number;
  status: string;
  confidence?: number;
  upload_timestamp?: string;
  invoice?: Invoice;
}

export interface DocumentGroup {
  recentlyUploaded: FileStatus[];
  scannedAwaitingMatch: (Invoice | DeliveryNote)[];
  matchedDocuments: (Invoice | DeliveryNote)[];
  failedDocuments: FileStatus[];
}

class ApiService {
  private async fetchWithErrorHandling<T>(url: string, options?: RequestInit): Promise<T> {
    const fullUrl = `${API_BASE_URL}${url}`;
    
    console.log(`🌐 API Request: ${options?.method || 'GET'} ${fullUrl}`);
    
    try {
      const isFileUpload = options?.body instanceof FormData;
      
      const requestOptions: RequestInit = {
        ...options,
        headers: {
          ...(isFileUpload ? {} : { 'Content-Type': 'application/json' }),
          ...options?.headers,
        },
      };

      if (isFileUpload) {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 120000);
        
        try {
          const response = await fetch(fullUrl, {
            ...requestOptions,
            signal: controller.signal,
          });
          
          clearTimeout(timeoutId);
          
          console.log(`📡 API Response: ${response.status} ${response.statusText}`);

          if (!response.ok) {
            let errorMessage = `HTTP ${response.status}: ${response.statusText}`;
            
            try {
              const errorData = await response.json();
              errorMessage = errorData.detail || errorData.message || errorMessage;
            } catch (parseError) {
              console.warn('Could not parse error response:', parseError);
            }
            
            console.error(`❌ API Error: ${errorMessage}`);
            throw new Error(errorMessage);
          }

          const data = await response.json() as T;
          console.log(`✅ API Success:`, data);
          return data;
        } catch (error) {
          clearTimeout(timeoutId);
          if (error instanceof Error && error.name === 'AbortError') {
            throw new Error('Request timed out after 2 minutes');
          }
          throw error;
        }
      } else {
        const response = await fetch(fullUrl, requestOptions);

        console.log(`📡 API Response: ${response.status} ${response.statusText}`);

        if (!response.ok) {
          let errorMessage = `HTTP ${response.status}: ${response.statusText}`;
          
          try {
            const errorData = await response.json();
            errorMessage = errorData.detail || errorData.message || errorMessage;
          } catch (parseError) {
            console.warn('Could not parse error response:', parseError);
          }
          
          console.error(`❌ API Error: ${errorMessage}`);
          throw new Error(errorMessage);
        }

        const data = await response.json() as T;
        console.log(`✅ API Success:`, data);
        return data;
      }
    } catch (error) {
      console.error(`💥 API Request failed:`, error);
      throw error;
    }
  }

  // Health check endpoint
  async health() {
    const response = await fetch(`${API_BASE_URL.replace('/api', '')}/health`);
    return response.json();
  }

  // Get all invoices
  async getInvoices(): Promise<{ invoices: Invoice[] }> {
    try {
      const response = await this.fetchWithErrorHandling<any>('/invoices');
      
      let invoices: Invoice[] = [];
      
      if (Array.isArray(response)) {
        invoices = response;
      } else if (response && Array.isArray(response.invoices)) {
        invoices = response.invoices;
      } else if (response && typeof response === 'object') {
        invoices = response.invoices || [];
      } else {
        console.warn('Unexpected response format:', response);
        invoices = [];
      }
      
      const safeInvoices = invoices.map(invoice => ({
        id: invoice?.id || 'unknown',
        invoice_number: invoice?.invoice_number || 'Unknown',
        invoice_date: invoice?.invoice_date || 'Unknown',
        supplier_name: invoice?.supplier_name || 'Unknown Supplier',
        total_amount: invoice?.total_amount || 0,
        status: invoice?.status || 'unknown',
        confidence: invoice?.confidence || 0,
        parent_pdf_filename: invoice?.parent_pdf_filename || '',
        line_items: invoice?.line_items || [],
        subtotal: invoice?.subtotal,
        vat: invoice?.vat,
        vat_rate: invoice?.vat_rate,
        total_incl_vat: invoice?.total_incl_vat,
        upload_timestamp: invoice?.upload_timestamp,
        page_range: invoice?.page_range,
        word_count: invoice?.word_count,
        psm_used: invoice?.psm_used,
        was_retried: invoice?.was_retried,
        raw_ocr_text: invoice?.raw_ocr_text,
        ocr_pages: invoice?.ocr_pages || [],
        price_mismatches: invoice?.price_mismatches || [],
      }));
      
      return { invoices: safeInvoices };
    } catch (error) {
      console.error('Failed to fetch invoices:', error);
      return { invoices: [] };
    }
  }

  // Get all delivery notes
  async getDeliveryNotes(): Promise<{ delivery_notes: DeliveryNote[] }> {
    try {
      const response = await this.fetchWithErrorHandling<any>('/delivery-notes');
      
      let deliveryNotes: DeliveryNote[] = [];
      
      if (Array.isArray(response)) {
        deliveryNotes = response;
      } else if (response && Array.isArray(response.delivery_notes)) {
        deliveryNotes = response.delivery_notes;
      } else if (response && typeof response === 'object') {
        deliveryNotes = response.delivery_notes || [];
      } else {
        console.warn('Unexpected response format:', response);
        deliveryNotes = [];
      }
      
      const safeDeliveryNotes = deliveryNotes.map(dn => ({
        id: dn?.id || 'unknown',
        delivery_number: dn?.delivery_number || 'Unknown',
        delivery_note_number: dn?.delivery_note_number || 'Unknown',
        delivery_date: dn?.delivery_date || 'Unknown',
        supplier_name: dn?.supplier_name || 'Unknown Supplier',
        total_amount: dn?.total_amount || 0,
        status: dn?.status || 'unknown',
        confidence: dn?.confidence || 0,
        upload_timestamp: dn?.upload_timestamp,
        invoice: dn?.invoice,
      }));
      
      return { delivery_notes: safeDeliveryNotes };
    } catch (error) {
      console.error('Failed to fetch delivery notes:', error);
      return { delivery_notes: [] };
    }
  }

  // Get file status
  async getFilesStatus(): Promise<{ files: FileStatus[] }> {
    try {
      const response = await this.fetchWithErrorHandling<any>('/files');
      
      let files: FileStatus[] = [];
      
      if (Array.isArray(response)) {
        files = response;
      } else if (response && Array.isArray(response.files)) {
        files = response.files;
      } else if (response && typeof response === 'object') {
        files = response.files || [];
      } else {
        console.warn('Unexpected response format:', response);
        files = [];
      }
      
      const safeFiles = files.map(file => ({
        id: file?.id || 'unknown',
        original_filename: file?.original_filename || 'Unknown',
        file_type: file?.file_type || 'invoice',
        processing_status: file?.processing_status || 'pending',
        confidence: file?.confidence || 0,
        upload_timestamp: file?.upload_timestamp || new Date().toISOString(),
        error_message: file?.error_message,
        document_status: file?.document_status,
      }));
      
      return { files: safeFiles };
    } catch (error) {
      console.error('Failed to fetch files status:', error);
      return { files: [] };
    }
  }

  async uploadFile(file: File, onProgress?: (progress: number) => void) {
    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await fetch(`${API_BASE_URL}/upload`, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      return response.json();
    } catch (error) {
      console.error('Upload failed:', error);
      throw error;
    }
  }

  // Upload document with OCR processing
  async uploadInvoice(file: File): Promise<any> {
    console.log(`📤 Starting invoice upload for: ${file.name} (${file.size} bytes)`);
    
    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await this.fetchWithErrorHandling('/upload', {
        method: 'POST',
        body: formData,
        headers: {},
      });
      
      console.log(`✅ Invoice upload successful:`, response);
      return response;
    } catch (error) {
      console.error(`❌ Invoice upload failed:`, error);
      throw error;
    }
  }

  async uploadDocumentForReview(file: File): Promise<any> {
    const formData = new FormData();
    formData.append('file', file);
    // Reuse main upload as a fallback; in future this could call a specialized review endpoint
    return this.fetchWithErrorHandling('/upload', {
      method: 'POST',
      body: formData,
      headers: {}
    });
  }

  // Group documents by status
  groupDocumentsByStatus(
    files: FileStatus[],
    invoices: Invoice[],
    deliveryNotes: DeliveryNote[]
  ): DocumentGroup {
    const safeFiles = files || [];
    const safeInvoices = invoices || [];
    const safeDeliveryNotes = deliveryNotes || [];

    const recentlyUploaded = safeFiles.filter(file => 
      file?.processing_status === 'pending' || file?.processing_status === 'processing'
    );

    const scannedAwaitingMatch = [
      ...safeInvoices.filter(invoice => 
        invoice?.status === 'unmatched' || 
        invoice?.status === 'waiting' || 
        invoice?.status === 'utility' ||
        invoice?.status === 'scanned' ||
        invoice?.status === 'processed'
      ),
      ...safeDeliveryNotes.filter(dn => 
        dn?.status === 'unmatched' ||
        dn?.status === 'scanned'
      )
    ];

    const matchedDocuments = [
      ...safeInvoices.filter(invoice => invoice?.status === 'matched'),
      ...safeDeliveryNotes.filter(dn => dn?.status === 'matched')
    ];

    const failedDocuments = safeFiles.filter(file => 
      file?.processing_status === 'failed' || file?.error_message
    );

    return {
      recentlyUploaded,
      scannedAwaitingMatch,
      matchedDocuments,
      failedDocuments,
    };
  }

  // File endpoints
  async getFiles() {
    const response = await fetch(`${API_BASE_URL}/files`);
    return response.json();
  }

  // Supplier endpoints
  async getSuppliers() {
    const response = await fetch(`${API_BASE_URL}/suppliers`);
    return response.json();
  }

  async getDashboard(): Promise<any> {
    return this.fetchWithErrorHandling<any>('/analytics/dashboard');
  }

  async getSpendSummary(params?: { start_date?: string; end_date?: string; venue?: string; supplier?: string; }): Promise<{ total_spend: number; prior_spend: number; delta_percent: number; }>{
    const query = new URLSearchParams();
    if (params?.start_date) query.set('start_date', params.start_date);
    if (params?.end_date) query.set('end_date', params.end_date);
    if (params?.venue) query.set('venue', params.venue);
    if (params?.supplier) query.set('supplier', params.supplier);
    return this.fetchWithErrorHandling(`/analytics/spend-summary?${query.toString()}`);
  }

  async getSpendBySupplier(params?: { start_date?: string; end_date?: string; venue?: string; limit?: number; }): Promise<{ total: number; suppliers: Array<{ supplier: string; total_value: number; }>; }>{
    const query = new URLSearchParams();
    if (params?.start_date) query.set('start_date', params.start_date);
    if (params?.end_date) query.set('end_date', params.end_date);
    if (params?.venue) query.set('venue', params.venue);
    if (params?.limit !== undefined) query.set('limit', String(params.limit));
    return this.fetchWithErrorHandling(`/analytics/spend-by-supplier?${query.toString()}`);
  }

  async getMatchRate(params?: { start_date?: string; end_date?: string; venue?: string; supplier?: string; }): Promise<{ total: number; passed: number; issues: number; failed: number; rate_percent: number; }>{
    const query = new URLSearchParams();
    if (params?.start_date) query.set('start_date', params.start_date);
    if (params?.end_date) query.set('end_date', params.end_date);
    if (params?.venue) query.set('venue', params.venue);
    if (params?.supplier) query.set('supplier', params.supplier);
    return this.fetchWithErrorHandling(`/analytics/match-rate?${query.toString()}`);
  }

  async getIssuesByType(params?: { start_date?: string; end_date?: string; venue?: string; }): Promise<{ issues: Array<{ issue_type: string; count: number; }>; total_flagged_items: number; }>{
    const query = new URLSearchParams();
    if (params?.start_date) query.set('start_date', params.start_date);
    if (params?.end_date) query.set('end_date', params.end_date);
    if (params?.venue) query.set('venue', params.venue);
    return this.fetchWithErrorHandling(`/analytics/issues-by-type?${query.toString()}`);
  }

  async getDuplicatesSummary(params?: { start_date?: string; end_date?: string; }): Promise<{ duplicates_prevented: number; prevented_value: number; groups: Array<{ supplier_name: string; invoice_number: string; count: number; total_sum: number; }>; }>{
    const query = new URLSearchParams();
    if (params?.start_date) query.set('start_date', params.start_date);
    if (params?.end_date) query.set('end_date', params.end_date);
    return this.fetchWithErrorHandling(`/analytics/duplicates-summary?${query.toString()}`);
  }

  async getUnmatchedCounts(params?: { start_date?: string; end_date?: string; venue?: string; }): Promise<{ paired: number; needs_review: number; unmatched: number; }>{
    const query = new URLSearchParams();
    if (params?.start_date) query.set('start_date', params.start_date);
    if (params?.end_date) query.set('end_date', params.end_date);
    if (params?.venue) query.set('venue', params.venue);
    return this.fetchWithErrorHandling(`/analytics/unmatched-counts?${query.toString()}`);
  }

  async getLowOCR(params?: { threshold?: number; start_date?: string; end_date?: string; }): Promise<{ total: number; low_confidence: number; threshold: number; }>{
    const query = new URLSearchParams();
    if (params?.threshold !== undefined) query.set('threshold', String(params.threshold));
    if (params?.start_date) query.set('start_date', params.start_date);
    if (params?.end_date) query.set('end_date', params.end_date);
    return this.fetchWithErrorHandling(`/analytics/low-ocr?${query.toString()}`);
  }

  async getVolatileProducts(params?: { days?: number; limit?: number; }): Promise<{ products: Array<{ product: string; supplier: string; current_price: number; volatility_90d: number; transactions: number; }>; }>{
    const query = new URLSearchParams();
    if (params?.days !== undefined) query.set('days', String(params.days));
    if (params?.limit !== undefined) query.set('limit', String(params.limit));
    return this.fetchWithErrorHandling(`/analytics/volatile-products?${query.toString()}`);
  }

  async getDocumentsForReview(): Promise<{ documents: any[] }> {
    return this.fetchWithErrorHandling('/documents/queue');
  }

  async approveDocument(docId: string, reviewData: any): Promise<any> {
    return this.fetchWithErrorHandling('/documents/approve', {
      method: 'POST',
      body: JSON.stringify({ doc_id: docId, ...reviewData }),
    });
  }

  async escalateDocument(docId: string, escalationData: any): Promise<any> {
    return this.fetchWithErrorHandling('/documents/escalate', {
      method: 'POST',
      body: JSON.stringify({ doc_id: docId, ...escalationData }),
    });
  }

  async deleteDocument(docId: string): Promise<any> {
    return this.fetchWithErrorHandling(`/documents/${docId}`, {
      method: 'DELETE',
    });
  }

  async clearAllDocuments(): Promise<void> {
    // Dev-only convenience endpoint; no-op if backend not available
    try {
      await this.fetchWithErrorHandling('/dev/clear-all', { method: 'POST' });
    } catch {
      // Swallow errors in non-dev envs
    }
  }

  // ✅ Vertical Cards API Methods
  async patchLineItem(invoiceId: string, rowIdx: number, patch: Partial<LineItem>): Promise<any> {
    return this.fetchWithErrorHandling(`/invoices/${invoiceId}/line-item/${rowIdx}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(patch),
    });
  }

  async patchInvoiceFlags(invoiceId: string, payload: any): Promise<any> {
    return this.fetchWithErrorHandling(`/invoices/${invoiceId}/flags`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
  }

  async patchVerificationStatus(invoiceId: string, status: 'unreviewed' | 'needs_review' | 'reviewed'): Promise<any> {
    return this.fetchWithErrorHandling(`/invoices/${invoiceId}/verification-status`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ status }),
    });
  }

  async extractSignatures(invoiceId: string): Promise<any> {
    return this.fetchWithErrorHandling(`/invoices/${invoiceId}/signatures/extract`, {
      method: 'POST',
    });
  }
}

export const apiService = new ApiService();