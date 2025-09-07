import { useState, useCallback, useEffect } from 'react';
import useFeatureFlags from './useFeatureFlags';

interface HealthMetrics {
  timeouts_24h: number;
  failed_24h: number;
  avg_duration_ms_24h: number;
  hi_conf_zero_lines_24h: number;
  multi_invoice_uploads_24h: number;
}

interface HealthResponse {
  status: 'healthy' | 'degraded' | 'critical';
  timestamp: string;
  metrics: HealthMetrics;
  violations?: string[];
}

export const useHealthMonitoring = () => {
  const { healthDashboard } = useFeatureFlags();
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchHealth = useCallback(async () => {
    if (!healthDashboard) {
      return; // Feature flag OFF - do nothing
    }

    setLoading(true);
    setError(null);

    try {
      const response = await fetch('/api/health/post_ocr');
      if (!response.ok) {
        throw new Error('Failed to fetch health metrics');
      }

      const data: HealthResponse = await response.json();
      setHealth(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  }, [healthDashboard]);

  // Auto-refresh health metrics every 30 seconds when feature is enabled
  useEffect(() => {
    if (!healthDashboard) {
      return;
    }

    fetchHealth();
    const interval = setInterval(fetchHealth, 30000);

    return () => clearInterval(interval);
  }, [healthDashboard, fetchHealth]);

  return {
    health,
    loading,
    error,
    fetchHealth,
    enabled: healthDashboard,
  };
}; 