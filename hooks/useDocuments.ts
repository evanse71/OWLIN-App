import { useState, useEffect, useCallback } from 'react';
import { apiService, DocumentGroup } from '@/services/api';

export const useDocuments = (refreshInterval = 10000) => {
  const [documents, setDocuments] = useState<DocumentGroup>({
    recentlyUploaded: [],
    scannedAwaitingMatch: [],
    matchedDocuments: [],
    failedDocuments: [],
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchDocuments = useCallback(async () => {
    try {
      setError(null);
      const [filesResponse, invoicesResponse, deliveryNotesResponse] = await Promise.all([
        apiService.getFilesStatus(),
        apiService.getInvoices(),
        apiService.getDeliveryNotes(),
      ]);

      const groupedDocuments = apiService.groupDocumentsByStatus(
        filesResponse.files,
        invoicesResponse.invoices,
        deliveryNotesResponse.delivery_notes
      );

      setDocuments(groupedDocuments);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Unknown error';
      setError(`Failed to fetch documents: ${errorMessage}`);
      console.error('Error fetching documents:', err);
      
      // Set fallback data even on error to prevent infinite loading
      setDocuments({
        recentlyUploaded: [],
        scannedAwaitingMatch: [],
        matchedDocuments: [],
        failedDocuments: [],
      });
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchDocuments();

    const interval = setInterval(fetchDocuments, refreshInterval);

    return () => clearInterval(interval);
  }, [fetchDocuments, refreshInterval]);

  return {
    documents,
    loading,
    error,
    refetch: fetchDocuments,
  };
}; 