import { useState, useEffect } from 'react';
import { licenseClient, LicenseStatus } from '../lib/licenseClient';

export interface LimitedModeState {
  limited: boolean;
  reason?: string;
  graceUntil?: string;
  state: LicenseStatus['state'];
}

export function useLimitedMode(): LimitedModeState {
  const [state, setState] = useState<LimitedModeState>({
    limited: false,
    state: 'not_found'
  });

  useEffect(() => {
    async function checkLicense() {
      try {
        const licenseStatus = await licenseClient.getStatus();
        
        setState({
          limited: !licenseStatus.valid,
          reason: licenseStatus.reason,
          graceUntil: licenseStatus.grace_until_utc,
          state: licenseStatus.state
        });
      } catch (error) {
        console.error('Error checking license status:', error);
        setState({
          limited: true,
          reason: 'LICENSE_NOT_FOUND',
          state: 'not_found'
        });
      }
    }

    checkLicense();
    
    // Check license status every 5 minutes
    const interval = setInterval(checkLicense, 5 * 60 * 1000);
    
    return () => clearInterval(interval);
  }, []);

  return state;
}

export function getLimitedModeTooltip(state: LimitedModeState): string {
  if (!state.limited) return '';
  
  switch (state.state) {
    case 'not_found':
      return 'Requires valid license';
    case 'expired':
      return 'License expired';
    case 'grace':
      return `Expired — grace until ${state.graceUntil}`;
    case 'mismatch':
      return 'Device mismatch — contact support';
    case 'invalid':
      return 'Invalid license';
    default:
      return 'Requires valid license';
  }
} 