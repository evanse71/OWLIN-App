import { useState, useEffect } from 'react';

export type LicenseStatus = {
  valid: boolean;
  reason?: string;
};

export const useLicense = () => {
  const [license, setLicense] = useState<LicenseStatus | null>(null);

  useEffect(() => {
    // Simulate fetching license status
    // For now, default to valid
    setLicense({ valid: true });
  }, []);

  return license;
}; 