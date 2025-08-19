import { useState, useEffect } from 'react';

export type UserRole = {
  name: 'Finance' | 'GM' | 'ShiftLead' | 'viewer';
  permissions: string[];
};

export const useRole = () => {
  const [role, setRole] = useState<UserRole | null>(null);

  useEffect(() => {
    // Simulate fetching role from an auth context or API
    // For now, default to 'Finance' or read from URL for testing
    const urlParams = new URLSearchParams(window.location.search);
    const roleParam = urlParams.get('role');

    let defaultRole: UserRole['name'] = 'Finance';
    if (roleParam === 'GM' || roleParam === 'ShiftLead') {
      defaultRole = roleParam;
    }

    setRole({
      name: defaultRole,
      permissions: ['read', 'write', 'upload'], // Example permissions
    });
  }, []);

  return role;
}; 