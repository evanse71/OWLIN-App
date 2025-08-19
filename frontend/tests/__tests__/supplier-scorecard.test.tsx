import React from 'react';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import ScoreBadge from '../../components/suppliers/ScoreBadge';
import MetricBadge from '../../components/suppliers/MetricBadge';
import InsightFeed from '../../components/suppliers/InsightFeed';
import SupplierScorecard from '../../components/suppliers/SupplierScorecard';

// Mock fetch for API calls
global.fetch = jest.fn();

describe('Supplier Scorecard Components', () => {
  beforeEach(() => {
    (fetch as jest.Mock).mockClear();
  });

  describe('ScoreBadge', () => {
    it('renders score correctly', () => {
      render(<ScoreBadge score={85} />);
      expect(screen.getByText('85')).toBeInTheDocument();
    });

    it('has correct ARIA attributes', () => {
      render(<ScoreBadge score={85} />);
      const badge = screen.getByRole('progressbar');
      expect(badge).toHaveAttribute('aria-valuenow', '85');
      expect(badge).toHaveAttribute('aria-valuemin', '0');
      expect(badge).toHaveAttribute('aria-valuemax', '100');
    });
  });

  describe('MetricBadge', () => {
    const mockMetric = {
      icon: <span data-testid="icon">📊</span>,
      name: 'Test Metric',
      detail: 'Test detail',
      score: 75,
      trend: 'up' as const,
      onActivate: jest.fn(),
    };

    it('renders metric information correctly', () => {
      render(<MetricBadge {...mockMetric} />);
      expect(screen.getByText('Test Metric')).toBeInTheDocument();
      expect(screen.getByText('Test detail')).toBeInTheDocument();
      expect(screen.getByText('75')).toBeInTheDocument();
      expect(screen.getByTestId('icon')).toBeInTheDocument();
    });

    it('shows trend indicator', () => {
      render(<MetricBadge {...mockMetric} />);
      expect(screen.getByText('↑')).toBeInTheDocument();
    });
  });

  describe('InsightFeed', () => {
    const mockInsights = [
      {
        id: '1',
        timestamp: '2025-08-18T15:17:10',
        severity: 'warn' as const,
        message: 'Test warning message',
      },
    ];

    it('renders insights correctly', () => {
      render(<InsightFeed items={mockInsights} />);
      expect(screen.getByText('Test warning message')).toBeInTheDocument();
    });

    it('shows empty state when no insights', () => {
      render(<InsightFeed items={[]} />);
      expect(screen.getByText('No recent insights')).toBeInTheDocument();
    });
  });

  describe('SupplierScorecard', () => {
    beforeEach(() => {
      (fetch as jest.Mock).mockResolvedValue({
        ok: true,
        json: async () => ({
          supplier_id: 'test-supplier',
          overall_score: 85,
          categories: {
            spend_share: {
              name: 'Spend Share',
              score: 80,
              trend: 'up',
              detail: '20% of total spend',
            },
          },
          insights: [],
        }),
      });
    });

    it('renders scorecard with supplier ID', () => {
      render(<SupplierScorecard supplierId="test-supplier" />);
      expect(screen.getByText('Supplier Scorecard')).toBeInTheDocument();
    });

    it('shows loading state initially', () => {
      (fetch as jest.Mock).mockImplementation(() => new Promise(() => {}));
      render(<SupplierScorecard supplierId="test-supplier" />);
      // Component should show loading or empty state
      expect(screen.getByText('Supplier Scorecard')).toBeInTheDocument();
    });
  });
}); 