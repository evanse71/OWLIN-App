/**
 * Enhanced API service with:
 * - Real-time progress tracking
 * - Intelligent error handling
 * - Confidence normalization
 * - Quality-based display
 */

export interface UploadProgress {
  stage: 'uploading' | 'processing' | 'extracting' | 'complete' | 'error';
  progress: number;
  message: string;
  details?: any;
}

export interface EnhancedUploadResult {
  success: boolean;
  confidence: number;
  quality_score: number;
  fields: {
    supplier_name: string;
    invoice_number: string;
    invoice_date: string;
    total_amount: number;
  };
  processing_time: number;
  engine_contributions: Record<string, any>;
  quality_indicators: Record<string, any>;
  error_messages: string[];
}

export interface InvoiceDetails {
  id: string;
  supplier_name: string;
  invoice_number: string;
  invoice_date: string;
  total_amount: number;
  confidence: number;
  quality_score: number;
  status: string;
  created_at: string;
  parent_pdf_filename?: string;
  line_items?: Array<{
    description: string;
    quantity: number;
    unit_price?: number;
    total_price?: number;
    unit_price_excl_vat?: number;
    unit_price_incl_vat?: number;
    line_total_excl_vat?: number;
    line_total_incl_vat?: number;
    flagged?: boolean;
  }>;
  delivery_note_match?: any;
  price_mismatches?: Array<{
    description: string;
    invoice_amount: number;
    delivery_amount: number;
    difference: number;
  }>;
  subtotal?: number;
  vat?: number;
  vat_rate?: number;
  total_incl_vat?: number;
}

class EnhancedAPIService {
  private baseURL: string;
  private uploadProgressCallbacks: Map<string, (progress: UploadProgress) => void>;

  constructor() {
    this.baseURL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8002';
    this.uploadProgressCallbacks = new Map();
  }

  /**
   * Normalize confidence to ensure it's always 0-100 scale
   */
  private normalizeConfidence(confidence: number): number {
    if (confidence === undefined || confidence === null) {
      return 0;
    }

    // If confidence is already 0-100 scale
    if (confidence > 1.0) {
      return Math.min(confidence, 100.0);
    } else {
      // Convert 0-1 scale to 0-100 scale
      return Math.min(confidence * 100, 100.0);
    }
  }

  /**
   * Enhanced upload with real-time progress tracking
   */
  async uploadDocument(
    file: File,
    onProgress?: (progress: UploadProgress) => void
  ): Promise<EnhancedUploadResult> {
    const uploadId = `upload_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    
    try {
      // Initialize progress tracking
      if (onProgress) {
        this.uploadProgressCallbacks.set(uploadId, onProgress);
        onProgress({
          stage: 'uploading',
          progress: 0,
          message: 'Preparing upload...'
        });
      }

      const formData = new FormData();
      formData.append('file', file);

      // Create upload request with progress tracking
      const xhr = new XMLHttpRequest();
      
      return new Promise((resolve, reject) => {
        xhr.upload.addEventListener('progress', (event) => {
          if (event.lengthComputable && onProgress) {
            const progress = (event.loaded / event.total) * 100;
            onProgress({
              stage: 'uploading',
              progress: Math.round(progress),
              message: `Uploading... ${Math.round(progress)}%`
            });
          }
        });

        xhr.addEventListener('load', async () => {
          try {
            if (xhr.status === 200) {
              const result = JSON.parse(xhr.responseText);
              
              // Normalize confidence for frontend display
              if (result.confidence !== undefined) {
                result.confidence = this.normalizeConfidence(result.confidence);
              }

              // Update progress to complete
              if (onProgress) {
                onProgress({
                  stage: 'complete',
                  progress: 100,
                  message: 'Upload completed successfully',
                  details: result
                });
              }

              resolve(result);
            } else {
              throw new Error(`Upload failed: ${xhr.statusText}`);
            }
          } catch (error) {
            if (onProgress) {
              onProgress({
                stage: 'error',
                progress: 0,
                message: `Upload failed: ${error instanceof Error ? error.message : 'Unknown error'}`
              });
            }
            reject(error);
          } finally {
            this.uploadProgressCallbacks.delete(uploadId);
          }
        });

        xhr.addEventListener('error', () => {
          const error = new Error('Network error during upload');
          if (onProgress) {
            onProgress({
              stage: 'error',
              progress: 0,
              message: 'Network error during upload'
            });
          }
          this.uploadProgressCallbacks.delete(uploadId);
          reject(error);
        });

        xhr.addEventListener('timeout', () => {
          const error = new Error('Upload timeout');
          if (onProgress) {
            onProgress({
              stage: 'error',
              progress: 0,
              message: 'Upload timeout'
            });
          }
          this.uploadProgressCallbacks.delete(uploadId);
          reject(error);
        });

        // Start upload
        xhr.open('POST', `${this.baseURL}/api/upload`);
        xhr.timeout = 120000; // 2 minutes timeout
        xhr.send(formData);
      });

    } catch (error) {
      console.error('Upload failed:', error);
      if (onProgress) {
        onProgress({
          stage: 'error',
          progress: 0,
          message: `Upload failed: ${error instanceof Error ? error.message : 'Unknown error'}`
        });
      }
      this.uploadProgressCallbacks.delete(uploadId);
      throw error;
    }
  }

  /**
   * Get all invoices with enhanced error handling
   */
  async getInvoices(): Promise<InvoiceDetails[]> {
    try {
      const response = await fetch(`${this.baseURL}/api/invoices`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        throw new Error(`Failed to fetch invoices: ${response.statusText}`);
      }

      const invoices = await response.json();
      
      // Normalize confidence for all invoices
      return invoices.map((invoice: any) => ({
        ...invoice,
        confidence: this.normalizeConfidence(invoice.confidence),
        quality_score: this.normalizeConfidence(invoice.quality_score || 0)
      }));

    } catch (error) {
      console.error('Failed to fetch invoices:', error);
      throw error;
    }
  }

  /**
   * Get invoice details with enhanced error handling
   */
  async getInvoiceDetails(invoiceId: string): Promise<InvoiceDetails> {
    try {
      const response = await fetch(`${this.baseURL}/api/invoices/${invoiceId}`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        throw new Error(`Failed to fetch invoice details: ${response.statusText}`);
      }

      const invoice = await response.json();
      
      // Normalize confidence
      return {
        ...invoice,
        confidence: this.normalizeConfidence(invoice.confidence),
        quality_score: this.normalizeConfidence(invoice.quality_score || 0)
      };

    } catch (error) {
      console.error('Failed to fetch invoice details:', error);
      throw error;
    }
  }

  /**
   * Get delivery notes with enhanced error handling
   */
  async getDeliveryNotes(): Promise<any[]> {
    try {
      const response = await fetch(`${this.baseURL}/api/delivery-notes`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        throw new Error(`Failed to fetch delivery notes: ${response.statusText}`);
      }

      return await response.json();

    } catch (error) {
      console.error('Failed to fetch delivery notes:', error);
      throw error;
    }
  }

  /**
   * Get delivery note details with enhanced error handling
   */
  async getDeliveryNoteDetails(deliveryNoteId: string): Promise<any> {
    try {
      const response = await fetch(`${this.baseURL}/api/delivery-notes/${deliveryNoteId}`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        throw new Error(`Failed to fetch delivery note details: ${response.statusText}`);
      }

      return await response.json();

    } catch (error) {
      console.error('Failed to fetch delivery note details:', error);
      throw error;
    }
  }

  /**
   * Get files status with enhanced error handling
   */
  async getFilesStatus(): Promise<any[]> {
    try {
      const response = await fetch(`${this.baseURL}/api/files`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        throw new Error(`Failed to fetch files status: ${response.statusText}`);
      }

      return await response.json();

    } catch (error) {
      console.error('Failed to fetch files status:', error);
      throw error;
    }
  }

  /**
   * Health check with enhanced error handling
   */
  async healthCheck(): Promise<{ status: string; timestamp: string }> {
    try {
      const response = await fetch(`${this.baseURL}/health`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        throw new Error(`Health check failed: ${response.statusText}`);
      }

      const result = await response.json();
      return {
        ...result,
        timestamp: new Date().toISOString()
      };

    } catch (error) {
      console.error('Health check failed:', error);
      throw error;
    }
  }

  /**
   * Update invoice with enhanced error handling
   */
  async updateInvoice(invoiceId: string, updates: Partial<InvoiceDetails>): Promise<InvoiceDetails> {
    try {
      const response = await fetch(`${this.baseURL}/api/invoices/${invoiceId}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(updates),
      });

      if (!response.ok) {
        throw new Error(`Failed to update invoice: ${response.statusText}`);
      }

      const invoice = await response.json();
      
      // Normalize confidence
      return {
        ...invoice,
        confidence: this.normalizeConfidence(invoice.confidence),
        quality_score: this.normalizeConfidence(invoice.quality_score || 0)
      };

    } catch (error) {
      console.error('Failed to update invoice:', error);
      throw error;
    }
  }

  /**
   * Delete invoice with enhanced error handling
   */
  async deleteInvoice(invoiceId: string): Promise<void> {
    try {
      const response = await fetch(`${this.baseURL}/api/invoices/${invoiceId}`, {
        method: 'DELETE',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        throw new Error(`Failed to delete invoice: ${response.statusText}`);
      }

    } catch (error) {
      console.error('Failed to delete invoice:', error);
      throw error;
    }
  }

  /**
   * Get processing statistics
   */
  async getProcessingStats(): Promise<{
    total_invoices: number;
    average_confidence: number;
    average_processing_time: number;
    success_rate: number;
  }> {
    try {
      const response = await fetch(`${this.baseURL}/api/stats`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        throw new Error(`Failed to fetch processing stats: ${response.statusText}`);
      }

      const stats = await response.json();
      
      // Normalize confidence values
      return {
        ...stats,
        average_confidence: this.normalizeConfidence(stats.average_confidence || 0)
      };

    } catch (error) {
      console.error('Failed to fetch processing stats:', error);
      throw error;
    }
  }

  /**
   * Retry failed processing
   */
  async retryProcessing(fileId: string): Promise<EnhancedUploadResult> {
    try {
      const response = await fetch(`${this.baseURL}/api/retry/${fileId}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        throw new Error(`Failed to retry processing: ${response.statusText}`);
      }

      const result = await response.json();
      
      // Normalize confidence
      if (result.confidence !== undefined) {
        result.confidence = this.normalizeConfidence(result.confidence);
      }

      return result;

    } catch (error) {
      console.error('Failed to retry processing:', error);
      throw error;
    }
  }

  /**
   * Get quality indicators for an invoice
   */
  async getQualityIndicators(invoiceId: string): Promise<{
    ocr_quality: number;
    field_validation: number;
    business_rules: number;
    data_consistency: number;
    overall_quality: number;
  }> {
    try {
      const response = await fetch(`${this.baseURL}/api/invoices/${invoiceId}/quality`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        throw new Error(`Failed to fetch quality indicators: ${response.statusText}`);
      }

      const indicators = await response.json();
      
      // Normalize all quality scores
      return {
        ocr_quality: this.normalizeConfidence(indicators.ocr_quality || 0),
        field_validation: this.normalizeConfidence(indicators.field_validation || 0),
        business_rules: this.normalizeConfidence(indicators.business_rules || 0),
        data_consistency: this.normalizeConfidence(indicators.data_consistency || 0),
        overall_quality: this.normalizeConfidence(indicators.overall_quality || 0)
      };

    } catch (error) {
      console.error('Failed to fetch quality indicators:', error);
      throw error;
    }
  }
}

// Export singleton instance
export const enhancedAPIService = new EnhancedAPIService();
export default enhancedAPIService; 