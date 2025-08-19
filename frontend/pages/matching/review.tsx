import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
import DocumentPairingSuggestionCard from '../../components/matching/DocumentPairingSuggestionCard';
import { MatchCandidate, MatchCandidatesResponse, MatchingStats } from '../../types/matching';
import matchingOfflineQueue from '../../lib/matchingOfflineQueue';

const MatchingReviewPage: React.FC = () => {
  const router = useRouter();
  const [currentInvoiceIndex, setCurrentInvoiceIndex] = useState(0);
  const [invoices, setInvoices] = useState<any[]>([]);
  const [candidates, setCandidates] = useState<MatchCandidate[]>([]);
  const [currentCandidateIndex, setCurrentCandidateIndex] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [stats, setStats] = useState<MatchingStats | null>(null);
  const [banner, setBanner] = useState<{ type: 'success' | 'error'; message: string } | null>(null);
  const [isOnline, setIsOnline] = useState(true);

  // Load unmatched invoices and stats
  useEffect(() => {
    loadUnmatchedInvoices();
    loadStats();
    
    // Set up online/offline listeners
    const handleOnline = () => setIsOnline(true);
    const handleOffline = () => setIsOnline(false);
    
    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);
    
    // Set initial online status
    setIsOnline(navigator.onLine);
    
    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, []);

  // Load candidates when invoice changes
  useEffect(() => {
    if (invoices.length > 0 && currentInvoiceIndex < invoices.length) {
      loadCandidates(invoices[currentInvoiceIndex].id);
    }
  }, [currentInvoiceIndex, invoices]);

  const loadUnmatchedInvoices = async () => {
    try {
      const response = await fetch('/api/invoices?status=scanned');
      if (response.ok) {
        const data = await response.json();
        setInvoices(data.invoices || []);
      }
    } catch (error) {
      console.error('Error loading invoices:', error);
      setBanner({ type: 'error', message: 'Failed to load invoices' });
    }
  };

  const loadStats = async () => {
    try {
      const response = await fetch('/api/matching/stats');
      if (response.ok) {
        const data = await response.json();
        setStats(data);
      }
    } catch (error) {
      console.error('Error loading stats:', error);
    }
  };

  const loadCandidates = async (invoiceId: string) => {
    setIsLoading(true);
    try {
      const response = await fetch(`/api/matching/candidates/${invoiceId}?limit=5&min_confidence=30`);
      if (response.ok) {
        const data: MatchCandidatesResponse = await response.json();
        setCandidates(data.candidate_delivery_notes);
        setCurrentCandidateIndex(0);
      } else {
        setCandidates([]);
      }
    } catch (error) {
      console.error('Error loading candidates:', error);
      setCandidates([]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleConfirm = async (invoiceId: string, deliveryNoteId: string) => {
    try {
      const response = await fetch('/api/matching/confirm', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ invoice_id: invoiceId, delivery_note_id: deliveryNoteId })
      });

      if (response.ok) {
        setBanner({ type: 'success', message: 'Match confirmed successfully!' });
        // Move to next candidate or invoice
        moveToNext();
        // Reload stats
        loadStats();
      } else {
        throw new Error('Failed to confirm match');
      }
    } catch (error) {
      console.error('Error confirming match:', error);
      setBanner({ type: 'error', message: 'Failed to confirm match' });
    }
  };

  const handleReject = async (invoiceId: string, deliveryNoteId: string) => {
    try {
      const response = await fetch('/api/matching/reject', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ invoice_id: invoiceId, delivery_note_id: deliveryNoteId })
      });

      if (response.ok) {
        setBanner({ type: 'success', message: 'Match rejected' });
        // Move to next candidate
        moveToNextCandidate();
      } else {
        throw new Error('Failed to reject match');
      }
    } catch (error) {
      console.error('Error rejecting match:', error);
      setBanner({ type: 'error', message: 'Failed to reject match' });
    }
  };

  const handleSkip = () => {
    moveToNextCandidate();
  };

  const moveToNextCandidate = () => {
    if (currentCandidateIndex < candidates.length - 1) {
      setCurrentCandidateIndex(currentCandidateIndex + 1);
    } else {
      // No more candidates for this invoice, move to next invoice
      moveToNextInvoice();
    }
  };

  const moveToNextInvoice = () => {
    if (currentInvoiceIndex < invoices.length - 1) {
      setCurrentInvoiceIndex(currentInvoiceIndex + 1);
    } else {
      // No more invoices to review
      setBanner({ type: 'success', message: 'All invoices reviewed!' });
    }
  };

  const moveToNext = () => {
    if (currentCandidateIndex < candidates.length - 1) {
      setCurrentCandidateIndex(currentCandidateIndex + 1);
    } else {
      moveToNextInvoice();
    }
  };

  const handleRetryLate = async () => {
    try {
      const response = await fetch('/api/matching/retry-late', { method: 'POST' });
      if (response.ok) {
        const data = await response.json();
        setBanner({ 
          type: 'success', 
          message: `${data.new_matches_found} new matches found!` 
        });
        // Reload data
        loadUnmatchedInvoices();
        loadStats();
      }
    } catch (error) {
      console.error('Error retrying late matches:', error);
      setBanner({ type: 'error', message: 'Failed to retry late matches' });
    }
  };

  // Clear banner after 5 seconds
  useEffect(() => {
    if (banner) {
      const timer = setTimeout(() => setBanner(null), 5000);
      return () => clearTimeout(timer);
    }
  }, [banner]);

  // Listen for offline queue events
  useEffect(() => {
    const handleOfflineQueueSuccess = (event: CustomEvent) => {
      setBanner({ type: 'success', message: event.detail.message });
    };
    
    const handleOfflineQueueFailure = (event: CustomEvent) => {
      setBanner({ type: 'error', message: event.detail.message });
    };
    
    window.addEventListener('matchingOfflineQueueSuccess', handleOfflineQueueSuccess as EventListener);
    window.addEventListener('matchingOfflineQueueFailure', handleOfflineQueueFailure as EventListener);
    
    return () => {
      window.removeEventListener('matchingOfflineQueueSuccess', handleOfflineQueueSuccess as EventListener);
      window.removeEventListener('matchingOfflineQueueFailure', handleOfflineQueueFailure as EventListener);
    };
  }, []);

  if (invoices.length === 0 && !isLoading) {
    return (
      <div className="min-h-screen bg-gray-50 p-6">
        <div className="max-w-6xl mx-auto">
          <div className="bg-white rounded-[12px] p-8 text-center">
            <h1 className="text-2xl font-semibold text-gray-900 mb-4">
              No Invoices to Review
            </h1>
            <p className="text-gray-600 mb-6">
              All invoices have been matched or there are no unmatched invoices available.
            </p>
            <button
              onClick={handleRetryLate}
              className="px-4 py-2 bg-blue-600 text-white rounded-[8px] hover:bg-blue-700"
            >
              Retry Late Matches
            </button>
          </div>
        </div>
      </div>
    );
  }

  const currentInvoice = invoices[currentInvoiceIndex];
  const currentCandidate = candidates[currentCandidateIndex];

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-6xl mx-auto space-y-6">
        {/* Header */}
        <div className="bg-white rounded-[12px] p-6 shadow-sm">
          <div className="flex justify-between items-center">
            <div>
              <h1 className="text-2xl font-semibold text-gray-900">
                Delivery Note Matching Review
              </h1>
              <p className="text-gray-600 mt-1">
                Review and confirm matches between invoices and delivery notes
              </p>
              {!isOnline && (
                <div className="mt-2 text-sm text-amber-600 bg-amber-50 px-3 py-1 rounded-md">
                  ⚠️ Offline mode - actions will be queued
                </div>
              )}
            </div>
            
            <div className="flex space-x-4">
              <button
                onClick={handleRetryLate}
                className="px-4 py-2 bg-blue-600 text-white rounded-[8px] hover:bg-blue-700"
              >
                Retry Late Matches
              </button>
              
              {stats && (
                <div className="text-right">
                  <div className="text-sm text-gray-600">
                    {stats.unmatched_invoices} invoices • {stats.unmatched_delivery_notes} delivery notes
                  </div>
                  <div className="text-sm text-gray-600">
                    {stats.confirmed_matches} confirmed • {stats.rejected_matches} rejected
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Progress */}
        <div className="bg-white rounded-[12px] p-4 shadow-sm">
          <div className="flex justify-between items-center">
            <div className="text-sm text-gray-600">
              Invoice {currentInvoiceIndex + 1} of {invoices.length}
            </div>
            <div className="text-sm text-gray-600">
              Candidate {currentCandidateIndex + 1} of {candidates.length}
            </div>
          </div>
          <div className="mt-2 bg-gray-200 rounded-full h-2">
            <div 
              className="bg-blue-600 h-2 rounded-full transition-all duration-300"
              style={{ 
                width: `${((currentInvoiceIndex * candidates.length + currentCandidateIndex + 1) / (invoices.length * Math.max(candidates.length, 1))) * 100}%` 
              }}
            />
          </div>
        </div>

        {/* Banner */}
        {banner && (
          <div className={`rounded-[12px] p-4 ${
            banner.type === 'success' 
              ? 'bg-green-50 border border-green-200 text-green-800' 
              : 'bg-red-50 border border-red-200 text-red-800'
          }`}>
            {banner.message}
          </div>
        )}

        {/* Main Content */}
        {isLoading ? (
          <div className="bg-white rounded-[12px] p-8 text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
            <p className="text-gray-600 mt-4">Loading candidates...</p>
          </div>
        ) : currentInvoice && currentCandidate ? (
          <DocumentPairingSuggestionCard
            invoice={currentInvoice}
            candidate={currentCandidate}
            onConfirm={handleConfirm}
            onReject={handleReject}
            onSkip={handleSkip}
          />
        ) : (
          <div className="bg-white rounded-[12px] p-8 text-center">
            <p className="text-gray-600">No candidates found for this invoice.</p>
            <button
              onClick={moveToNextInvoice}
              className="mt-4 px-4 py-2 bg-gray-600 text-white rounded-[8px] hover:bg-gray-700"
            >
              Next Invoice
            </button>
          </div>
        )}
      </div>
    </div>
  );
};

export default MatchingReviewPage; 