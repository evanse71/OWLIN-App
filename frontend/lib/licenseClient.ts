export interface LicenseStatus {
  valid: boolean;
  state: 'valid' | 'grace' | 'expired' | 'invalid' | 'mismatch' | 'not_found';
  grace_until_utc?: string;
  reason?: string;
  summary?: LicenseSummary;
}

export interface LicenseSummary {
  customer: string;
  license_id: string;
  expires_utc: string;
  device_id: string;
  venues: string[];
  roles: Record<string, number>;
  features: Record<string, boolean>;
}

export interface LicenseUploadResponse {
  ok: boolean;
  message: string;
  status: LicenseStatus;
}

export interface LicenseVerifyResponse {
  signature_valid: boolean;
  device_match: boolean;
  expiry_check: string;
  grace_period?: string;
  overall_valid: boolean;
}

class LicenseClient {
  private baseUrl = '/api/license';

  async getStatus(): Promise<LicenseStatus> {
    try {
      const response = await fetch(`${this.baseUrl}/status`);
      if (!response.ok) {
        throw new Error('Failed to get license status');
      }
      return await response.json();
    } catch (error) {
      console.error('Error getting license status:', error);
      // Return not_found state on error
      return {
        valid: false,
        state: 'not_found',
        reason: 'LICENSE_NOT_FOUND'
      };
    }
  }

  async uploadLicense(file: File): Promise<LicenseUploadResponse> {
    try {
      const formData = new FormData();
      formData.append('file', file);

      const response = await fetch(`${this.baseUrl}/upload`, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        throw new Error('Failed to upload license');
      }

      return await response.json();
    } catch (error) {
      console.error('Error uploading license:', error);
      throw error;
    }
  }

  async uploadLicenseContent(content: string): Promise<LicenseUploadResponse> {
    try {
      const formData = new FormData();
      formData.append('license_content', content);

      const response = await fetch(`${this.baseUrl}/upload`, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        throw new Error('Failed to upload license');
      }

      return await response.json();
    } catch (error) {
      console.error('Error uploading license content:', error);
      throw error;
    }
  }

  async verifyLicense(): Promise<LicenseVerifyResponse> {
    try {
      const response = await fetch(`${this.baseUrl}/verify`);
      if (!response.ok) {
        throw new Error('Failed to verify license');
      }
      return await response.json();
    } catch (error) {
      console.error('Error verifying license:', error);
      throw error;
    }
  }

  async getDeviceFingerprint(): Promise<{ device_fingerprint: string }> {
    try {
      const response = await fetch(`${this.baseUrl}/device-fingerprint`);
      if (!response.ok) {
        throw new Error('Failed to get device fingerprint');
      }
      return await response.json();
    } catch (error) {
      console.error('Error getting device fingerprint:', error);
      throw error;
    }
  }
}

export const licenseClient = new LicenseClient(); 