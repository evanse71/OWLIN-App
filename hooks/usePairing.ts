import { useState, useCallback } from 'react';
import useFeatureFlags from './useFeatureFlags';

interface PairingSuggestion {
  dn_id: string;
  score: number;
  rationale: string[];
  supplier_name: string;
  date: string;
  amount: number;
}

interface PairingResponse {
  invoice_id: string;
  suggestions: PairingSuggestion[];
  count: number;
}

export const usePairingSuggestions = () => {
  const { dnPairing } = useFeatureFlags();
  const [suggestions, setSuggestions] = useState<PairingSuggestion[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const getSuggestions = useCallback(async (invoiceId: string) => {
    if (!dnPairing) {
      return; // Feature flag OFF - do nothing
    }

    setLoading(true);
    setError(null);

    try {
      const response = await fetch(`/api/pairing/suggestions?invoice_id=${invoiceId}`);
      if (!response.ok) {
        throw new Error('Failed to fetch pairing suggestions');
      }

      const data: PairingResponse = await response.json();
      setSuggestions(data.suggestions);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  }, [dnPairing]);

  return {
    suggestions,
    loading,
    error,
    getSuggestions,
    enabled: dnPairing,
  };
};

export const usePairingConfirmation = () => {
  const { dnPairing } = useFeatureFlags();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const confirmPairing = useCallback(async (invoiceId: string, deliveryNoteId: string) => {
    if (!dnPairing) {
      return false; // Feature flag OFF - do nothing
    }

    setLoading(true);
    setError(null);

    try {
      const response = await fetch('/api/pairing/confirm', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ invoice_id: invoiceId, delivery_note_id: deliveryNoteId }),
      });

      if (!response.ok) {
        throw new Error('Failed to confirm pairing');
      }

      return true;
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
      return false;
    } finally {
      setLoading(false);
    }
  }, [dnPairing]);

  const rejectPairing = useCallback(async (invoiceId: string, deliveryNoteId: string) => {
    if (!dnPairing) {
      return false; // Feature flag OFF - do nothing
    }

    setLoading(true);
    setError(null);

    try {
      const response = await fetch('/api/pairing/reject', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ invoice_id: invoiceId, delivery_note_id: deliveryNoteId }),
      });

      if (!response.ok) {
        throw new Error('Failed to reject pairing');
      }

      return true;
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
      return false;
    } finally {
      setLoading(false);
    }
  }, [dnPairing]);

  return {
    loading,
    error,
    confirmPairing,
    rejectPairing,
    enabled: dnPairing,
  };
}; 