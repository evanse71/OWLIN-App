// API service for the new backend endpoints

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api';

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

export interface Invoice {
  id: string;
  invoice_number?: string;
  invoice_date?: string;
  supplier_name?: string;
  total_amount?: number;
  status: 'pending' | 'scanned' | 'matched' | 'unmatched' | 'error' | 'waiting' | 'utility';
  confidence?: number;
  upload_timestamp: string;
  delivery_note?: {
    id: string;
    delivery_note_number: string;
    delivery_date: string;
  } | null;
  delivery_note_required?: boolean;
  is_utility_invoice?: boolean;
  utility_keywords?: string[];
  parent_pdf_filename?: string;
  page_number?: number;
  ocr_text?: string;
  // ✅ VAT calculations
  subtotal?: number;
  vat?: number;
  vat_rate?: number;
  total_incl_vat?: number;
  // ✅ Enhanced line items with VAT calculations
  line_items?: Array<{
    description: string;
    quantity: number;
    unit_price?: number; // Legacy field
    total_price?: number; // Legacy field
    unit_price_excl_vat?: number;
    unit_price_incl_vat?: number;
    line_total_excl_vat?: number;
    line_total_incl_vat?: number;
    flagged?: boolean;
  }>;
  price_mismatches?: Array<{
    description: string;
    invoice_amount: number;
    delivery_amount: number;
    difference: number;
  }>;
}

export interface DeliveryNote {
  id: string;
  delivery_note_number?: string;
  delivery_date?: string;
  supplier_name?: string;
  total_amount?: number; // ✅ Add total_amount for price comparison
  status: 'pending' | 'scanned' | 'matched' | 'unmatched' | 'error';
  confidence?: number;
  upload_timestamp: string;
  invoice?: {
    id: string;
    invoice_number: string;
    invoice_date: string;
  } | null;
}

export interface DocumentGroup {
  recentlyUploaded: FileStatus[];
  scannedAwaitingMatch: (Invoice | DeliveryNote)[];
  matchedDocuments: (Invoice | DeliveryNote)[];
  failedDocuments: FileStatus[];
}

export interface DocumentQueueItem {
  id: string;
  filename: string;
  file_type: string;
  file_path: string;
  file_size: number;
  upload_date: string;
  status: string;
  status_badge: string;
  confidence: number;
  extracted_text?: string;
  error_message?: string;
  supplier_guess: string;
  document_type_guess: string;
}

export interface ReviewData {
  document_type: 'invoice' | 'delivery_note' | 'receipt' | 'utility';
  supplier_name: string;
  invoice_number?: string;
  delivery_note_number?: string;
  invoice_date?: string;
  delivery_date?: string;
  total_amount?: number;
  confidence: number;
  extracted_text?: string;
  reviewed_by?: string;
  line_items?: Array<{
    description: string;
    quantity: number;
    unit_price: number;
    total_price: number;
  }>;
  vat_included?: boolean;
  comments?: string;
}

export interface EscalationData {
  reason: string;
  comments?: string;
}

// Fallback data when backend is not available
const FALLBACK_DATA = {
  files: [
    {
      id: '1',
      original_filename: 'sample_invoice_1.pdf',
      file_type: 'invoice' as const,
      processing_status: 'completed' as const,
      confidence: 0.95,
      upload_timestamp: '2024-01-15T10:00:00Z',
      document_status: 'unmatched'
    },
    {
      id: '2',
      original_filename: 'sample_delivery_1.pdf',
      file_type: 'delivery_note' as const,
      processing_status: 'completed' as const,
      confidence: 0.92,
      upload_timestamp: '2024-01-15T09:00:00Z',
      document_status: 'unmatched'
    }
  ],
  invoices: [
    {
      id: '1',
      invoice_number: 'INV-2024-001',
      invoice_date: '2024-01-15',
      supplier_name: 'ABC Corporation',
      total_amount: 1500.00,
      status: 'unmatched' as const,
      confidence: 0.95,
      upload_timestamp: '2024-01-15T10:00:00Z'
    }
  ],
  delivery_notes: [
    {
      id: '2',
      delivery_note_number: 'DN-2024-001',
      delivery_date: '2024-01-15',
      supplier_name: 'ABC Corporation',
      status: 'unmatched' as const,
      confidence: 0.92,
      upload_timestamp: '2024-01-15T09:00:00Z'
    }
  ]
};

class ApiService {
  private async fetchWithErrorHandling<T>(url: string, options?: RequestInit): Promise<T> {
    try {
      const response = await fetch(`${API_BASE_URL}${url}`, {
        headers: {
          'Content-Type': 'application/json',
          ...options?.headers,
        },
        ...options,
      });

      if (!response.ok) {
        throw new Error(`API Error: ${response.status} ${response.statusText}`);
      }

      return await response.json();
    } catch (error) {
      console.error('API request failed:', error);
      throw error;
    }
  }

  // Get all file statuses - try new endpoint first, fallback to existing
  async getFilesStatus(): Promise<{ files: FileStatus[] }> {
    try {
      // Try the new endpoint first
      return await this.fetchWithErrorHandling<{ files: FileStatus[] }>('/files/status');
    } catch (error) {
      console.warn('New files/status endpoint not available, using fallback data');
      return { files: FALLBACK_DATA.files as FileStatus[] };
    }
  }

  // Get all invoices - try new endpoint first, fallback to existing
  async getInvoices(): Promise<{ invoices: Invoice[] }> {
    try {
      // Try the new endpoint first
      return await this.fetchWithErrorHandling<{ invoices: Invoice[] }>('/documents/invoices');
    } catch (error) {
      try {
        // Try the existing endpoint
        const response = await this.fetchWithErrorHandling<any>('/files/invoices');
        // Transform the response to match our interface
        const invoices: Invoice[] = response.files?.map((file: any) => ({
          id: file.filename,
          invoice_number: file.parsed_data?.invoice_number,
          invoice_date: file.parsed_data?.invoice_date,
          supplier_name: file.parsed_data?.supplier_name,
          total_amount: parseFloat(file.parsed_data?.total_amount || '0'),
          status: file.status as any,
          confidence: 0.9,
          upload_timestamp: file.uploaded_at || new Date().toISOString()
        })) || [];
        return { invoices };
      } catch (fallbackError) {
        console.warn('All invoice endpoints failed, using fallback data');
        return { invoices: FALLBACK_DATA.invoices as Invoice[] };
      }
    }
  }

  // Get all delivery notes - try new endpoint first, fallback to existing
  async getDeliveryNotes(): Promise<{ delivery_notes: DeliveryNote[] }> {
    try {
      // Try the new endpoint first
      return await this.fetchWithErrorHandling<{ delivery_notes: DeliveryNote[] }>('/documents/delivery-notes');
    } catch (error) {
      try {
        // Try the existing endpoint
        const response = await this.fetchWithErrorHandling<any>('/files/delivery');
        // Transform the response to match our interface
        const delivery_notes: DeliveryNote[] = response.files?.map((file: any) => ({
          id: file.filename,
          delivery_note_number: file.parsed_data?.delivery_note_number,
          delivery_date: file.parsed_data?.delivery_date,
          supplier_name: file.parsed_data?.supplier_name,
          status: file.status as any,
          confidence: 0.9,
          upload_timestamp: file.uploaded_at || new Date().toISOString()
        })) || [];
        return { delivery_notes };
      } catch (fallbackError) {
        console.warn('All delivery note endpoints failed, using fallback data');
        return { delivery_notes: FALLBACK_DATA.delivery_notes as DeliveryNote[] };
      }
    }
  }

  // Get invoice details
  async getInvoiceDetails(invoiceId: string): Promise<Invoice> {
    try {
      return await this.fetchWithErrorHandling<Invoice>(`/documents/invoices/${invoiceId}`);
    } catch (error) {
      // Return fallback data
      return FALLBACK_DATA.invoices.find(inv => inv.id === invoiceId) as Invoice || FALLBACK_DATA.invoices[0] as Invoice;
    }
  }

  // Get delivery note details
  async getDeliveryNoteDetails(deliveryNoteId: string): Promise<DeliveryNote> {
    try {
      return await this.fetchWithErrorHandling<DeliveryNote>(`/documents/delivery-notes/${deliveryNoteId}`);
    } catch (error) {
      // Return fallback data
      return FALLBACK_DATA.delivery_notes.find(dn => dn.id === deliveryNoteId) as DeliveryNote || FALLBACK_DATA.delivery_notes[0] as DeliveryNote;
    }
  }

  // Upload invoice with OCR processing
  async uploadInvoice(file: File): Promise<any> {
    const formData = new FormData();
    formData.append('file', file);
    
    try {
      return await this.fetchWithErrorHandling('/upload', {
        method: 'POST',
        body: formData,
        headers: {}, // Let browser set Content-Type for FormData
      });
    } catch (error) {
      console.error('Upload failed:', error);
      throw error;
    }
  }

  // Upload delivery note
  async uploadDeliveryNote(file: File): Promise<any> {
    const formData = new FormData();
    formData.append('file', file);
    
    try {
      return await this.fetchWithErrorHandling('/upload/delivery', {
        method: 'POST',
        body: formData,
        headers: {}, // Let browser set Content-Type for FormData
      });
    } catch (error) {
      console.error('Upload failed:', error);
      throw error;
    }
  }

  // Upload document with type (new simplified method)
  async uploadDocument(file: File, documentType: 'invoice' | 'delivery_note' | 'receipt' | 'utility'): Promise<any> {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('document_type', documentType);
    
    try {
      return await this.fetchWithErrorHandling('/upload/document', {
        method: 'POST',
        body: formData,
        headers: {}, // Let browser set Content-Type for FormData
      });
    } catch (error) {
      console.error('Upload failed:', error);
      throw error;
    }
  }

  // Upload document for smart processing and review
  async uploadDocumentForReview(file: File): Promise<{ suggested_documents: any[] }> {
    const formData = new FormData();
    formData.append('file', file);
    
    try {
      return await this.fetchWithErrorHandling('/upload/review', {
        method: 'POST',
        body: formData,
        headers: {}, // Let browser set Content-Type for FormData
      });
    } catch (error) {
      console.error('Upload for review failed:', error);
      throw error;
    }
  }

  // Confirm document splits after review
  async confirmDocumentSplits(fileName: string, documents: any[]): Promise<{ success: boolean; message: string }> {
    try {
      return await this.fetchWithErrorHandling('/upload/confirm-splits', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          file_name: fileName,
          documents: documents,
        }),
      });
    } catch (error) {
      console.error('Confirm splits failed:', error);
      throw error;
    }
  }

  // Group documents by status
  groupDocumentsByStatus(
    files: FileStatus[],
    invoices: Invoice[],
    deliveryNotes: DeliveryNote[]
  ): DocumentGroup {
    const recentlyUploaded = files.filter(file => 
      file.processing_status === 'pending' || file.processing_status === 'processing'
    );

    const scannedAwaitingMatch = [
      ...invoices.filter(invoice => 
        invoice.status === 'unmatched' || 
        invoice.status === 'waiting' || 
        invoice.status === 'utility' ||
        invoice.status === 'scanned'  // ✅ Add scanned invoices to the list
      ),
      ...deliveryNotes.filter(dn => 
        dn.status === 'unmatched' ||
        dn.status === 'scanned'  // ✅ Add scanned delivery notes to the list
      )
    ];

    const matchedDocuments = [
      ...invoices.filter(invoice => invoice.status === 'matched'),
      ...deliveryNotes.filter(dn => dn.status === 'matched')
    ];

    const failedDocuments = files.filter(file => 
      file.processing_status === 'failed' || file.error_message
    );

    return {
      recentlyUploaded,
      scannedAwaitingMatch,
      matchedDocuments,
      failedDocuments,
    };
  }

  // Document Queue API methods
  async getDocumentsForReview(): Promise<{ documents: DocumentQueueItem[] }> {
    try {
      const response = await this.fetchWithErrorHandling<{ documents: DocumentQueueItem[] }>(
        `${API_BASE_URL}/documents/queue`
      );
      return response;
    } catch (error) {
      console.error('Error fetching documents for review:', error);
      return { documents: [] };
    }
  }

  async approveDocument(documentId: string, reviewData: ReviewData): Promise<{ success: boolean; message: string }> {
    try {
      const response = await this.fetchWithErrorHandling<{ success: boolean; message: string }>(
        `${API_BASE_URL}/documents/${documentId}/approve`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(reviewData),
        }
      );
      return response;
    } catch (error) {
      console.error('Error approving document:', error);
      throw error;
    }
  }

  async escalateDocument(documentId: string, escalationData: EscalationData): Promise<{ success: boolean; message: string }> {
    try {
      const response = await this.fetchWithErrorHandling<{ success: boolean; message: string }>(
        `${API_BASE_URL}/documents/${documentId}/escalate`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(escalationData),
        }
      );
      return response;
    } catch (error) {
      console.error('Error escalating document:', error);
      throw error;
    }
  }

  async deleteDocument(documentId: string): Promise<{ success: boolean; message: string }> {
    try {
      const response = await this.fetchWithErrorHandling<{ success: boolean; message: string }>(
        `${API_BASE_URL}/documents/${documentId}`,
        {
          method: 'DELETE',
        }
      );
      return response;
    } catch (error) {
      console.error('Error deleting document:', error);
      throw error;
    }
  }

  // ✅ Dev-only method to clear all documents
  async clearAllDocuments(): Promise<void> {
    const response = await fetch('/api/dev/clear-documents', {
      method: 'DELETE',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      throw new Error(`Failed to clear documents: ${response.statusText}`);
    }

    return response.json();
  }
}

export const apiService = new ApiService(); 