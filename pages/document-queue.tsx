import React, { useState, useEffect, useRef } from 'react';
import AppShell from '@/components/layout/AppShell';
import DocumentQueueCard from '@/components/document-queue/DocumentQueueCard';
import DocumentReviewModal from '@/components/document-queue/DocumentReviewModal';
import { apiService } from '@/services/api';
import { DocumentQueueItem } from '@/components/document-queue/DocumentQueueCard';
import { ReviewData, EscalationData } from '@/components/document-queue/DocumentReviewModal';
import { useToast } from '@/utils/toast';

interface DocumentQueuePageProps {}

const DocumentQueuePage: React.FC<DocumentQueuePageProps> = () => {
  const [documents, setDocuments] = useState<DocumentQueueItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedDocument, setSelectedDocument] = useState<DocumentQueueItem | null>(null);
  const [reviewModalOpen, setReviewModalOpen] = useState(false);
  const [filterStatus, setFilterStatus] = useState<string>('all');
  const [sortBy, setSortBy] = useState<string>('upload_date');
  const [searchTerm, setSearchTerm] = useState<string>('');
  const [documentTypeFilter, setDocumentTypeFilter] = useState<string>('all');
  const [lowConfidenceOnly, setLowConfidenceOnly] = useState(false);
  const [unmatchedOnly, setUnmatchedOnly] = useState(false);
  
  // Auto-refresh state
  const [autoRefresh, setAutoRefresh] = useState(false);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const intervalRef = useRef<NodeJS.Timeout | null>(null);

  // Selection state
  const [selectedDocuments, setSelectedDocuments] = useState<Set<string>>(new Set());
  const [showCheckboxes, setShowCheckboxes] = useState(false);

  const { showToast } = useToast();

  // Fetch documents for review
  const fetchDocuments = async (showLoadingSpinner = true) => {
    try {
      if (showLoadingSpinner) {
        setLoading(true);
      }
      setIsRefreshing(true);
      setError(null);
      const response = await apiService.getDocumentsForReview();
      setDocuments(response.documents);
    } catch (err) {
      const errorMessage = 'Failed to fetch documents';
      setError(errorMessage);
      showToast('error', '🚨 Something went wrong');
      console.error('Error fetching documents:', err);
    } finally {
      if (showLoadingSpinner) {
        setLoading(false);
      }
      setIsRefreshing(false);
    }
  };

  // Initial fetch
  useEffect(() => {
    fetchDocuments();
  }, []);

  // Auto-refresh effect
  useEffect(() => {
    if (autoRefresh) {
      // Set up interval for auto-refresh (30 seconds)
      intervalRef.current = setInterval(() => {
        fetchDocuments(false); // Don't show loading spinner for auto-refresh
      }, 30000);

      // Cleanup function
      return () => {
        if (intervalRef.current) {
          clearInterval(intervalRef.current);
          intervalRef.current = null;
        }
      };
    } else {
      // Clear interval when auto-refresh is disabled
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    }
  }, [autoRefresh]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    };
  }, []);

  // Get filtered and sorted documents
  const getFilteredDocuments = () => {
    let filtered = documents;

    // Filter by status
    if (filterStatus !== 'all') {
      filtered = filtered.filter(doc => doc.status === filterStatus);
    }

    // Filter by document type
    if (documentTypeFilter !== 'all') {
      filtered = filtered.filter(doc => doc.document_type_guess === documentTypeFilter);
    }

    // Filter by low confidence only
    if (lowConfidenceOnly) {
      filtered = filtered.filter(doc => doc.confidence < 70);
    }

    // Filter by unmatched only
    if (unmatchedOnly) {
      filtered = filtered.filter(doc => doc.status === 'pending' || doc.status === 'failed');
    }

    // Filter by search term
    if (searchTerm) {
      filtered = filtered.filter(doc => {
        const searchableText = [
          doc.filename,
          doc.supplier_guess,
          doc.document_type_guess
        ].join(' ').toLowerCase();
        
        return searchableText.includes(searchTerm.toLowerCase());
      });
    }

    // Sort documents
    filtered.sort((a, b) => {
      if (sortBy === 'upload_date') {
        return new Date(b.upload_timestamp).getTime() - new Date(a.upload_timestamp).getTime();
      }
      
      if (sortBy === 'supplier') {
        return a.supplier_guess.localeCompare(b.supplier_guess);
      }

      if (sortBy === 'confidence') {
        return a.confidence - b.confidence;
      }
      
      return 0;
    });

    return filtered;
  };

  const handleDocumentClick = (document: DocumentQueueItem) => {
    setSelectedDocument(document);
    setReviewModalOpen(true);
  };

  const handleApprove = async (document: DocumentQueueItem, reviewData: ReviewData) => {
    try {
      await apiService.approveDocument(document.id, reviewData);
      
      // Remove the document from the local state
      setDocuments(prev => prev.filter(doc => doc.id !== document.id));
      setReviewModalOpen(false);
      setSelectedDocument(null);
      
      // Show success toast
      showToast('success', '✅ Document approved');
    } catch (err) {
      console.error('Error approving document:', err);
      // Show error toast
      showToast('error', '🚨 Something went wrong');
    }
  };

  const handleEscalate = async (document: DocumentQueueItem, escalationData: EscalationData) => {
    try {
      await apiService.escalateDocument(document.id, escalationData);
      
      // Remove the document from the local state
      setDocuments(prev => prev.filter(doc => doc.id !== document.id));
      setReviewModalOpen(false);
      setSelectedDocument(null);
      
      // Show warning toast
      showToast('warning', '⚠️ Document escalated');
    } catch (err) {
      console.error('Error escalating document:', err);
      // Show error toast
      showToast('error', '🚨 Something went wrong');
    }
  };

  const handleDelete = async (document: DocumentQueueItem) => {
    if (!confirm('Are you sure you want to delete this document? This action cannot be undone.')) {
      return;
    }

    try {
      await apiService.deleteDocument(document.id);
      
      // Remove the document from the local state
      setDocuments(prev => prev.filter(doc => doc.id !== document.id));
      setReviewModalOpen(false);
      setSelectedDocument(null);
      
      // Show destructive toast
      showToast('error', '❌ Document deleted');
    } catch (err) {
      console.error('Error deleting document:', err);
      // Show error toast
      showToast('error', '🚨 Something went wrong');
    }
  };

  const handleManualRefresh = () => {
    fetchDocuments();
  };

  // Selection handlers
  const handleDocumentSelect = (documentId: string, selected: boolean) => {
    const newSelected = new Set(selectedDocuments);
    if (selected) {
      newSelected.add(documentId);
    } else {
      newSelected.delete(documentId);
    }
    setSelectedDocuments(newSelected);
    
    // Show checkboxes if any document is selected
    setShowCheckboxes(newSelected.size > 0);
  };

  const handleSelectAll = () => {
    const filteredDocs = getFilteredDocuments();
    if (selectedDocuments.size === filteredDocs.length) {
      // Deselect all
      setSelectedDocuments(new Set());
      setShowCheckboxes(false);
    } else {
      // Select all
      const allIds = new Set(filteredDocs.map(doc => doc.id));
      setSelectedDocuments(allIds);
      setShowCheckboxes(true);
    }
  };

  const handleDeleteSelected = async () => {
    if (!confirm(`Are you sure you want to delete ${selectedDocuments.size} selected document(s)? This action cannot be undone.`)) {
      return;
    }

    try {
      // Delete all selected documents
      const deletePromises = Array.from(selectedDocuments).map(id => 
        apiService.deleteDocument(id)
      );
      await Promise.all(deletePromises);
      
      // Remove from local state
      setDocuments(prev => prev.filter(doc => !selectedDocuments.has(doc.id)));
      setSelectedDocuments(new Set());
      setShowCheckboxes(false);
      
      // Show success toast
      showToast('error', `❌ ${selectedDocuments.size} document(s) deleted`);
    } catch (err) {
      console.error('Error deleting selected documents:', err);
      showToast('error', '🚨 Something went wrong');
    }
  };

  const filteredDocuments = getFilteredDocuments();
  const selectedCount = selectedDocuments.size;
  const totalCount = filteredDocuments.length;
  const isAllSelected = selectedCount === totalCount && totalCount > 0;

  if (loading) {
    return (
      <AppShell>
        <div className="py-8">
          <div className="flex items-center justify-center h-64">
            <div className="text-center">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-owlin-cerulean mx-auto mb-4"></div>
              <p className="text-owlin-muted">Loading document queue...</p>
            </div>
          </div>
        </div>
      </AppShell>
    );
  }

  return (
    <AppShell>
      <div className="py-6">
        <div className="max-w-7xl mx-auto">
          {/* Header */}
          <div className="mb-6">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h1 className="text-3xl font-semibold text-owlin-text">📋 Document Queue</h1>
                <p className="text-owlin-muted mt-2">Review and classify uploaded documents</p>
              </div>
              <div className="flex items-center space-x-4">
                {/* Auto-refresh toggle */}
                <div className="flex items-center space-x-3">
                  <label className="flex items-center cursor-pointer">
                    <div className="relative">
                      <input type="checkbox" checked={autoRefresh} onChange={(e) => setAutoRefresh(e.target.checked)} className="sr-only" />
                      <div className={`block w-14 h-8 rounded-full transition-colors duration-200 ease-in-out ${autoRefresh ? 'bg-[var(--owlin-sapphire)]' : 'bg-owlin-bg'}`}>
                        <div className={`absolute left-1 top-1 bg-white w-6 h-6 rounded-full transition-transform duration-200 ease-in-out transform ${autoRefresh ? 'translate-x-6' : 'translate-x-0'}`}></div>
                      </div>
                    </div>
                    <span className="ml-3 text-sm font-medium text-owlin-text">Auto-refresh</span>
                  </label>
                  {autoRefresh && isRefreshing && (
                    <div className="flex items-center space-x-2 text-sm text-owlin-muted">
                      <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-owlin-cerulean"></div>
                      <span>Refreshing...</span>
                    </div>
                  )}
                </div>

                <button onClick={handleManualRefresh} disabled={isRefreshing} className="px-4 py-2 bg-[var(--owlin-sapphire)] text-white rounded-owlin hover:brightness-110 transition-colors disabled:opacity-50 disabled:cursor-not-allowed">
                  🔄 Refresh
                </button>
              </div>
            </div>

            {/* Selection Toolbar */}
            {showCheckboxes && (
              <div className="bg-owlin-card border border-owlin-stroke rounded-owlin p-4 mb-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-4">
                    <label className="flex items-center cursor-pointer">
                      <input type="checkbox" checked={isAllSelected} onChange={handleSelectAll} className="w-4 h-4 text-[var(--owlin-sapphire)] bg-owlin-card border-owlin-stroke rounded focus:ring-owlin-sapphire" />
                      <span className="ml-2 text-sm font-medium text-owlin-text">{isAllSelected ? 'Deselect All' : 'Select All'}</span>
                    </label>
                    <span className="text-sm text-owlin-muted">{selectedCount} of {totalCount} selected</span>
                  </div>
                  <div className="flex items-center space-x-2">
                    <button onClick={handleDeleteSelected} disabled={selectedCount === 0} className="px-4 py-2 bg-red-600 text-white rounded-owlin hover:bg-red-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed text-sm">
                      🗑️ Delete Selected ({selectedCount})
                    </button>
                    <button onClick={() => { setSelectedDocuments(new Set()); setShowCheckboxes(false); }} className="px-3 py-2 text-owlin-muted hover:text-owlin-text transition-colors text-sm">
                      ✕ Cancel
                    </button>
                  </div>
                </div>
              </div>
            )}

            {/* Stats */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-4">
              <div className="bg-owlin-card rounded-owlin p-4 border border-owlin-stroke shadow-owlin">
                <div className="flex items-center">
                  <div className="p-2 rounded-owlin bg-[color-mix(in_oklab,var(--owlin-sapphire)_12%,transparent)]">
                    <span className="text-owlin-cerulean text-xl">📄</span>
                  </div>
                  <div className="ml-3">
                    <p className="text-sm font-medium text-owlin-muted">Total Documents</p>
                    <p className="text-2xl font-bold text-owlin-text">{filteredDocuments.length}</p>
                  </div>
                </div>
              </div>

              <div className="bg-owlin-card rounded-owlin p-4 border border-owlin-stroke shadow-owlin">
                <div className="flex items-center">
                  <div className="p-2 rounded-owlin bg-[color-mix(in_oklab,var(--owlin-yellow)_12%,transparent)]">
                    <span className="text-owlin-yellow text-xl">⏳</span>
                  </div>
                  <div className="ml-3">
                    <p className="text-sm font-medium text-owlin-muted">Pending Review</p>
                    <p className="text-2xl font-bold text-owlin-text">
                      {filteredDocuments.filter(doc => doc.status === 'pending').length}
                    </p>
                  </div>
                </div>
              </div>

              <div className="bg-owlin-card rounded-owlin p-4 border border-owlin-stroke shadow-owlin">
                <div className="flex items-center">
                  <div className="p-2 rounded-owlin bg-[color-mix(in_oklab,var(--owlin-red)_12%,transparent)]">
                    <span className="text-owlin-red text-xl">❌</span>
                  </div>
                  <div className="ml-3">
                    <p className="text-sm font-medium text-owlin-muted">Errors</p>
                    <p className="text-2xl font-bold text-owlin-text">
                      {filteredDocuments.filter(doc => doc.status === 'failed').length}
                    </p>
                  </div>
                </div>
              </div>

              <div className="bg-owlin-card rounded-owlin p-4 border border-owlin-stroke shadow-owlin">
                <div className="flex items-center">
                  <div className="p-2 rounded-owlin bg-[color-mix(in_oklab,var(--owlin-orange)_12%,transparent)]">
                    <span className="text-owlin-orange text-xl">⚠️</span>
                  </div>
                  <div className="ml-3">
                    <p className="text-sm font-medium text-owlin-muted">Low Confidence</p>
                    <p className="text-2xl font-bold text-owlin-text">
                      {filteredDocuments.filter(doc => doc.confidence < 0.7).length}
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Filters and Search */}
          <div className="bg-owlin-card border border-owlin-stroke rounded-owlin p-4 mb-4">
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-4">
              {/* Search */}
              <div>
                <label className="block text-sm font-medium text-owlin-text">
                  Search Documents
                </label>
                <input
                  type="text"
                  placeholder="Search by filename or supplier..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="w-full px-3 py-2 border border-owlin-stroke rounded-md bg-owlin-bg text-owlin-text focus:outline-none focus:ring-2 focus:ring-owlin-sapphire"
                />
              </div>

              {/* Document Type Filter */}
              <div>
                <label className="block text-sm font-medium text-owlin-text">
                  Document Type
                </label>
                <select
                  value={documentTypeFilter}
                  onChange={(e) => setDocumentTypeFilter(e.target.value)}
                  className="w-full px-3 py-2 border border-owlin-stroke rounded-md bg-owlin-bg text-owlin-text focus:outline-none focus:ring-2 focus:ring-owlin-sapphire"
                >
                  <option value="all">All Types</option>
                  <option value="invoice">Invoice</option>
                  <option value="delivery_note">Delivery Note</option>
                  <option value="receipt">Receipt</option>
                  <option value="utility">Utility</option>
                </select>
              </div>

              {/* Status Filter */}
              <div>
                <label className="block text-sm font-medium text-owlin-text">
                  Status Filter
                </label>
                <select
                  value={filterStatus}
                  onChange={(e) => setFilterStatus(e.target.value)}
                  className="w-full px-3 py-2 border border-owlin-stroke rounded-md bg-owlin-bg text-owlin-text focus:outline-none focus:ring-2 focus:ring-owlin-sapphire"
                >
                  <option value="all">All Statuses</option>
                  <option value="pending">Pending</option>
                  <option value="failed">Failed</option>
                  <option value="processing">Processing</option>
                </select>
              </div>

              {/* Sort By */}
              <div>
                <label className="block text-sm font-medium text-owlin-text">
                  Sort By
                </label>
                <select
                  value={sortBy}
                  onChange={(e) => setSortBy(e.target.value)}
                  className="w-full px-3 py-2 border border-owlin-stroke rounded-md bg-owlin-bg text-owlin-text focus:outline-none focus:ring-2 focus:ring-owlin-sapphire"
                >
                  <option value="upload_date">Upload Date (Newest)</option>
                  <option value="supplier">Supplier Name</option>
                  <option value="confidence">Confidence (Low to High)</option>
                </select>
              </div>
            </div>

            {/* Checkbox Filters */}
            <div className="flex flex-wrap gap-4">
              <label className="flex items-center">
                <input
                  type="checkbox"
                  checked={lowConfidenceOnly}
                  onChange={(e) => setLowConfidenceOnly(e.target.checked)}
                  className="rounded border-owlin-stroke text-[var(--owlin-sapphire)] focus:ring-owlin-sapphire"
                />
                <span className="ml-2 text-sm text-owlin-text">Low Confidence Only</span>
              </label>
              
              <label className="flex items-center">
                <input
                  type="checkbox"
                  checked={unmatchedOnly}
                  onChange={(e) => setUnmatchedOnly(e.target.checked)}
                  className="rounded border-owlin-stroke text-[var(--owlin-sapphire)] focus:ring-owlin-sapphire"
                />
                <span className="ml-2 text-sm text-owlin-text">Unmatched Only</span>
              </label>
            </div>
          </div>

          {/* Error Display */}
          {error && (
            <div className="bg-red-50 border border-red-200 rounded-owlin p-4 mb-4">
              <div className="flex items-center">
                <span className="text-red-600 text-xl mr-2">❌</span>
                <span className="text-red-700">{error}</span>
              </div>
            </div>
          )}

          {/* Documents Grid */}
          {filteredDocuments.length === 0 ? (
            <div className="text-center py-12">
              <div className="text-owlin-muted dark:text-owlin-gray-500 text-6xl mb-4">📋</div>
              <h3 className="text-lg font-medium text-owlin-text dark:text-owlin-gray-100 mb-2">
                No documents in queue
              </h3>
              <p className="text-owlin-muted dark:text-owlin-gray-400">
                All documents have been reviewed or there are no documents matching your filters.
              </p>
            </div>
          ) : (
            <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-4 gap-4">
              {filteredDocuments.map((document) => (
                <DocumentQueueCard
                  key={document.id}
                  document={document}
                  onClick={() => handleDocumentClick(document)}
                  isSelected={selectedDocuments.has(document.id)}
                  onSelectChange={(selected) => handleDocumentSelect(document.id, selected)}
                  showCheckbox={showCheckboxes}
                />
              ))}
            </div>
          )}
        </div>

        {/* Review Modal */}
        {selectedDocument && (
          <DocumentReviewModal
            isOpen={reviewModalOpen}
            onClose={() => {
              setReviewModalOpen(false);
              setSelectedDocument(null);
            }}
            document={selectedDocument}
            onApprove={handleApprove}
            onEscalate={handleEscalate}
            onDelete={handleDelete}
          />
        )}
      </div>
    </AppShell>
  );
};

export default DocumentQueuePage; 