import React from 'react';
import AppShell from '@/components/layout/AppShell';
import AdvancedAnalyticsDashboard from '@/components/analytics/AdvancedAnalyticsDashboard';

export default function AnalyticsPage() {
  return (
    <AppShell>
      <div className="py-8">
        <AdvancedAnalyticsDashboard />
      </div>
    </AppShell>
  );
} 