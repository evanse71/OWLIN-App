import { useMemo } from 'react';

interface FeatureFlags {
  dnPairing: boolean;
  healthDashboard: boolean;
  supplierIntel: boolean;
}

export const useFeatureFlags = (): FeatureFlags => {
  return useMemo(() => ({
    dnPairing: process.env.NEXT_PUBLIC_FEATURE_DN_PAIRING === 'true',
    healthDashboard: process.env.NEXT_PUBLIC_FEATURE_HEALTH_DASHBOARD === 'true',
    supplierIntel: process.env.NEXT_PUBLIC_FEATURE_SUPPLIER_INTEL === 'true',
  }), []);
};

export default useFeatureFlags; 