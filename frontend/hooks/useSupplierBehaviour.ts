import { useState, useEffect } from 'react';

export interface SupplierEvent {
  id: string;
  event_type: 'missed_delivery' | 'invoice_mismatch' | 'late_delivery' | 'quality_issue' | 'price_spike';
  severity: 'low' | 'medium' | 'high';
  description?: string;
  source: 'invoice_audit' | 'manual' | 'system';
  created_at: string;
  is_acknowledged: boolean;
}

export interface SupplierInsight {
  metric_name: string;
  metric_value: number;
  trend_direction: 'up' | 'down' | 'flat';
  trend_percentage: number;
  period_days: number;
  last_updated: string;
}

export interface SupplierAlert {
  supplier_id: string;
  supplier_name: string;
  alert_type: string;
  severity: 'low' | 'medium' | 'high';
  summary: string;
}

export interface SupplierEventRequest {
  supplier_id: string;
  event_type: 'missed_delivery' | 'invoice_mismatch' | 'late_delivery' | 'quality_issue' | 'price_spike';
  severity: 'low' | 'medium' | 'high';
  description?: string;
  source: 'invoice_audit' | 'manual' | 'system';
}

export function useSupplierEvents(supplierId: string) {
  const [events, setEvents] = useState<SupplierEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isCachedData, setIsCachedData] = useState(false);

  useEffect(() => {
    const fetchEvents = async () => {
      try {
        setLoading(true);
        setError(null);
        
        // Check if we're offline
        if (!navigator.onLine) {
          // Try to get cached data
          const cached = localStorage.getItem(`supplier_events_${supplierId}`);
          if (cached) {
            setEvents(JSON.parse(cached));
            setIsCachedData(true);
          }
          setLoading(false);
          return;
        }

        const response = await fetch(`/api/supplier-behaviour/events/${supplierId}?limit=20`);
        if (!response.ok) {
          throw new Error('Failed to fetch events');
        }
        
        const data = await response.json();
        setEvents(data.events || []);
        setIsCachedData(false);
        
        // Cache the data
        localStorage.setItem(`supplier_events_${supplierId}`, JSON.stringify(data.events || []));
        
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to fetch events');
      } finally {
        setLoading(false);
      }
    };

    if (supplierId) {
      fetchEvents();
    }
  }, [supplierId]);

  return { events, loading, error, isCachedData };
}

export function useSupplierInsights(supplierId: string) {
  const [insights, setInsights] = useState<SupplierInsight[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isCachedData, setIsCachedData] = useState(false);

  useEffect(() => {
    const fetchInsights = async () => {
      try {
        setLoading(true);
        setError(null);
        
        // Check if we're offline
        if (!navigator.onLine) {
          // Try to get cached data
          const cached = localStorage.getItem(`supplier_insights_${supplierId}`);
          if (cached) {
            setInsights(JSON.parse(cached));
            setIsCachedData(true);
          }
          setLoading(false);
          return;
        }

        const response = await fetch(`/api/supplier-behaviour/insights/${supplierId}`);
        if (!response.ok) {
          throw new Error('Failed to fetch insights');
        }
        
        const data = await response.json();
        setInsights(data.insights || []);
        setIsCachedData(false);
        
        // Cache the data
        localStorage.setItem(`supplier_insights_${supplierId}`, JSON.stringify(data.insights || []));
        
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to fetch insights');
      } finally {
        setLoading(false);
      }
    };

    if (supplierId) {
      fetchInsights();
    }
  }, [supplierId]);

  return { insights, loading, error, isCachedData };
}

export function useAlerts() {
  const [alerts, setAlerts] = useState<SupplierAlert[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isCachedData, setIsCachedData] = useState(false);

  useEffect(() => {
    const fetchAlerts = async () => {
      try {
        setLoading(true);
        setError(null);
        
        // Check if we're offline
        if (!navigator.onLine) {
          // Try to get cached data
          const cached = localStorage.getItem('supplier_alerts');
          if (cached) {
            setAlerts(JSON.parse(cached));
            setIsCachedData(true);
          }
          setLoading(false);
          return;
        }

        const response = await fetch('/api/supplier-behaviour/alerts');
        if (!response.ok) {
          throw new Error('Failed to fetch alerts');
        }
        
        const data = await response.json();
        setAlerts(data.alerts || []);
        setIsCachedData(false);
        
        // Cache the data
        localStorage.setItem('supplier_alerts', JSON.stringify(data.alerts || []));
        
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to fetch alerts');
      } finally {
        setLoading(false);
      }
    };

    fetchAlerts();
  }, []);

  return { alerts, loading, error, isCachedData };
}

export async function logSupplierEvent(request: SupplierEventRequest): Promise<boolean> {
  try {
    // Check if we're offline
    if (!navigator.onLine) {
      // Queue for offline processing
      const offlineQueue = JSON.parse(localStorage.getItem('supplier_events_offline_queue') || '[]');
      offlineQueue.push({
        ...request,
        timestamp: new Date().toISOString(),
        retryCount: 0
      });
      localStorage.setItem('supplier_events_offline_queue', JSON.stringify(offlineQueue));
      return true;
    }

    const response = await fetch('/api/supplier-behaviour/event', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(request),
    });

    if (!response.ok) {
      throw new Error('Failed to log event');
    }

    return true;
  } catch (error) {
    console.error('Error logging supplier event:', error);
    return false;
  }
} 