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
  status: string;
  confidence?: number;
  upload_timestamp?: string;
  line_items?: any[];
  subtotal?: number;
  vat?: number;
  vat_rate?: number;
  total_incl_vat?: number;
  price_mismatches?: Array<{
    description: string;
    invoice_amount: number;
    delivery_amount: number;
    difference: number;
  }>;
  // Add missing properties for matching
  delivery_note?: DeliveryNote;
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
  // Add missing properties for matching
  invoice?: Invoice;
}

// Document Queue Types
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

// Document Group Types
export interface DocumentGroup {
  recentlyUploaded: FileStatus[];
  scannedAwaitingMatch: (Invoice | DeliveryNote)[];
  matchedDocuments: (Invoice | DeliveryNote)[];
  failedDocuments: FileStatus[];
}

// Fallback data for development
const FALLBACK_DATA = {
  invoices: [
    {
      id: 'inv-001',
      invoice_number: 'INV-2023-001',
      invoice_date: '2023-12-15',
      supplier_name: 'Tech Supplies Ltd',
      total_amount: 1250.00,
      status: 'matched',
      confidence: 0.95,
      upload_timestamp: '2023-12-15T10:30:00Z'
    },
    {
      id: 'inv-002',
      invoice_number: 'INV-2023-002',
      invoice_date: '2023-12-14',
      supplier_name: 'Office Solutions',
      total_amount: 850.50,
      status: 'unmatched',
      confidence: 0.87,
      upload_timestamp: '2023-12-14T14:20:00Z'
    }
  ],
  delivery_notes: [
    {
      id: 'dn-001',
      delivery_number: 'DN-2023-001',
      delivery_note_number: 'DN-2023-001',
      delivery_date: '2023-12-15',
      supplier_name: 'Tech Supplies Ltd',
      total_amount: 1250.00,
      status: 'matched',
      confidence: 0.92,
      upload_timestamp: '2023-12-15T09:15:00Z'
    }
  ]
};

class ApiService {
  private async fetchWithErrorHandling<T>(url: string, options?: RequestInit): Promise<T> {
    const fullUrl = `${API_BASE_URL}${url}`;
    
    console.log(`🌐 API Request: ${options?.method || 'GET'} ${fullUrl}`);
    
    try {
      // Don't override Content-Type for file uploads (FormData)
      const isFileUpload = options?.body instanceof FormData;
      
      const requestOptions: RequestInit = {
        ...options,
        headers: {
          // Only set Content-Type if not a file upload
          ...(isFileUpload ? {} : { 'Content-Type': 'application/json' }),
          ...options?.headers,
        },
      };

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
    } catch (error) {
      console.error(`💥 API Request failed:`, error);
      throw error;
    }
  }

  // Get all invoices - try new endpoint first, fallback to existing
  async getInvoices(): Promise<{ invoices: Invoice[] }> {
    try {
      // Use the correct endpoint that matches the backend route
      const response = await this.fetchWithErrorHandling<any>('/invoices');
      
      // The backend returns { invoices: [...], delivery_notes: [...], grouped: {...} }
      // We need to extract just the invoices array
      if (response.invoices) {
        return { invoices: response.invoices };
      } else {
        console.warn('No invoices found in response:', response);
        return { invoices: [] };
      }
    } catch (error) {
      console.error('Failed to fetch invoices:', error);
      // Return empty array instead of fallback data to avoid confusion
      return { invoices: [] };
    }
  }

  // Get all delivery notes
  async getDeliveryNotes(): Promise<{ delivery_notes: DeliveryNote[] }> {
    try {
      // Use the correct endpoint that matches the backend route
      const response = await this.fetchWithErrorHandling<any>('/invoices');
      
      // The backend returns { invoices: [...], delivery_notes: [...], grouped: {...} }
      // We need to extract just the delivery_notes array
      if (response.delivery_notes) {
        return { delivery_notes: response.delivery_notes };
      } else {
        console.warn('No delivery notes found in response:', response);
        return { delivery_notes: [] };
      }
    } catch (error) {
      console.error('Failed to fetch delivery notes:', error);
      // Return empty array instead of fallback data to avoid confusion
      return { delivery_notes: [] };
    }
  }

  // Get scanned invoices specifically
  async getScannedInvoices(): Promise<Invoice[]> {
    try {
      const response = await this.fetchWithErrorHandling<any>('/invoices');
      
      if (response.invoices) {
        // Filter for invoices with 'scanned' status
        const scannedInvoices = response.invoices.filter((invoice: Invoice) => 
          invoice.status === 'scanned'
        );
        return scannedInvoices;
      } else {
        console.warn('No invoices found in response:', response);
        return [];
      }
    } catch (error) {
      console.error('Failed to fetch scanned invoices:', error);
      return [];
    }
  }

  // Get file status - this was missing and causing the useDocuments hook to fail
  async getFilesStatus(): Promise<{ files: FileStatus[] }> {
    try {
      // For now, return empty array since we don't have a specific endpoint for this
      // The useDocuments hook expects this to work
      console.log('getFilesStatus called - returning empty array');
      return { files: [] };
    } catch (error) {
      console.error('Failed to fetch files status:', error);
      return { files: [] };
    }
  }

  // Get file status for a specific file
  async getFileStatus(fileId: string): Promise<FileStatus> {
    try {
      return await this.fetchWithErrorHandling<FileStatus>(`/files/${fileId}/status`);
    } catch (error) {
      console.error('Failed to get file status:', error);
      throw error;
    }
  }

  // Get invoice details
  async getInvoiceDetails(invoiceId: string): Promise<Invoice> {
    try {
      return await this.fetchWithErrorHandling<Invoice>(`/documents/invoices/${invoiceId}`);
    } catch (error) {
      console.error('Failed to get invoice details:', error);
      // Return fallback data
      return FALLBACK_DATA.invoices.find(inv => inv.id === invoiceId) as Invoice || FALLBACK_DATA.invoices[0] as Invoice;
    }
  }

  // Get delivery note details
  async getDeliveryNoteDetails(deliveryNoteId: string): Promise<DeliveryNote> {
    try {
      return await this.fetchWithErrorHandling<DeliveryNote>(`/documents/delivery-notes/${deliveryNoteId}`);
    } catch (error) {
      console.error('Failed to get delivery note details:', error);
      // Return fallback data
      return FALLBACK_DATA.delivery_notes.find(dn => dn.id === deliveryNoteId) as DeliveryNote || FALLBACK_DATA.delivery_notes[0] as DeliveryNote;
    }
  }

  // Upload invoice with OCR processing
  async uploadInvoice(file: File): Promise<any> {
    console.log(`📤 Starting invoice upload for: ${file.name} (${file.size} bytes)`);
    
    const formData = new FormData();
    formData.append('file', file);
    
    try {
      const response = await this.fetchWithErrorHandling('/upload', {
        method: 'POST',
        body: formData,
        headers: {}, // Let browser set Content-Type for FormData
      });
      
      console.log(`✅ Invoice upload successful:`, response);
      return response;
    } catch (error) {
      console.error(`❌ Invoice upload failed:`, error);
      throw error;
    }
  }

  // Upload delivery note
  async uploadDeliveryNote(file: File): Promise<any> {
    console.log(`📤 Starting delivery note upload for: ${file.name} (${file.size} bytes)`);
    
    const formData = new FormData();
    formData.append('file', file);
    
    try {
      const response = await this.fetchWithErrorHandling('/upload/delivery', {
        method: 'POST',
        body: formData,
        headers: {}, // Let browser set Content-Type for FormData
      });
      
      console.log(`✅ Delivery note upload successful:`, response);
      return response;
    } catch (error) {
      console.error(`❌ Delivery note upload failed:`, error);
      throw error;
    }
  }

  // Upload document with type (new simplified method)
  async uploadDocument(file: File, documentType: 'invoice' | 'delivery_note' | 'receipt' | 'utility'): Promise<any> {
    console.log(`📤 Starting document upload for: ${file.name} (${file.size} bytes) as ${documentType}`);
    
    const formData = new FormData();
    formData.append('file', file);
    formData.append('document_type', documentType);
    
    try {
      const response = await this.fetchWithErrorHandling('/upload/document', {
        method: 'POST',
        body: formData,
        headers: {}, // Let browser set Content-Type for FormData
      });
      
      console.log(`✅ Document upload successful:`, response);
      return response;
    } catch (error) {
      console.error(`❌ Document upload failed:`, error);
      throw error;
    }
  }

  // Upload document for smart processing and review
  async uploadDocumentForReview(file: File): Promise<any> {
    console.log(`📤 Starting document review upload for: ${file.name} (${file.size} bytes)`);
    
    const formData = new FormData();
    formData.append('file', file);
    
    try {
      const response = await this.fetchWithErrorHandling('/upload/review', {
        method: 'POST',
        body: formData,
        headers: {}, // Let browser set Content-Type for FormData
      });
      
      console.log(`✅ Document review upload successful:`, response);
      return response;
    } catch (error) {
      console.error(`❌ Document review upload failed:`, error);
      throw error;
    }
  }

  // Submit documents to archive
  async submitDocuments(documents: any[]): Promise<any> {
    console.log(`📤 Submitting ${documents.length} documents to archive`);
    
    try {
      const response = await this.fetchWithErrorHandling('/documents/submit', {
        method: 'POST',
        body: JSON.stringify({ documents }),
        headers: {
          'Content-Type': 'application/json',
        },
      });
      
      console.log(`✅ Documents submitted successfully:`, response);
      return response;
    } catch (error) {
      console.error(`❌ Document submission failed:`, error);
      throw error;
    }
  }

  // Get document queue
  async getDocumentQueue(): Promise<any[]> {
    try {
      const response = await this.fetchWithErrorHandling<any[]>('/documents/queue');
      return response;
    } catch (error) {
      console.error('Failed to get document queue:', error);
      return [];
    }
  }

  // Get documents for review
  async getDocumentsForReview(): Promise<{ documents: DocumentQueueItem[] }> {
    try {
      const response = await this.fetchWithErrorHandling<{ documents: DocumentQueueItem[] }>('/documents/queue');
      return response;
    } catch (error) {
      console.error('Error fetching documents for review:', error);
      return { documents: [] };
    }
  }

  // Approve document
  async approveDocument(documentId: string, reviewData: ReviewData): Promise<{ success: boolean; message: string }> {
    try {
      const response = await this.fetchWithErrorHandling<{ success: boolean; message: string }>(`/documents/${documentId}/approve`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(reviewData),
      });
      return response;
    } catch (error) {
      console.error('Error approving document:', error);
      throw error;
    }
  }

  // Escalate document
  async escalateDocument(documentId: string, escalationData: EscalationData): Promise<{ success: boolean; message: string }> {
    try {
      const response = await this.fetchWithErrorHandling<{ success: boolean; message: string }>(`/documents/${documentId}/escalate`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(escalationData),
      });
      return response;
    } catch (error) {
      console.error('Error escalating document:', error);
      throw error;
    }
  }

  // Delete document
  async deleteDocument(documentId: string): Promise<{ success: boolean; message: string }> {
    try {
      const response = await this.fetchWithErrorHandling<{ success: boolean; message: string }>(`/documents/${documentId}`, {
        method: 'DELETE',
      });
      return response;
    } catch (error) {
      console.error('Error deleting document:', error);
      throw error;
    }
  }

  // Update document status
  async updateDocumentStatus(documentId: string, status: string): Promise<any> {
    try {
      const response = await this.fetchWithErrorHandling(`/documents/${documentId}/status`, {
        method: 'PUT',
        body: JSON.stringify({ status }),
        headers: {
          'Content-Type': 'application/json',
        },
      });
      return response;
    } catch (error) {
      console.error('Failed to update document status:', error);
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
        invoice.status === 'scanned'
      ),
      ...deliveryNotes.filter(dn => 
        dn.status === 'unmatched' ||
        dn.status === 'scanned'
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

  // Dev-only method to clear all documents
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