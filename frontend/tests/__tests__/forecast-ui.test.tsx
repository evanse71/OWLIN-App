import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import ItemForecastCard from '../../components/forecast/ItemForecastCard';
import ForecastChart from '../../components/forecast/ForecastChart';
import ScenarioControls from '../../components/forecast/ScenarioControls';
import QualityPanel from '../../components/forecast/QualityPanel';
import { ForecastItem, ForecastSeries, ForecastQuality, ForecastScenario } from '../../types/forecast';

// Mock data
const mockItem: ForecastItem = {
  item_id: 1,
  name: 'Test Item',
  latest_price: 100.0,
  trend: 'up',
  forecast_1m: 105.0,
  forecast_3m: 110.0,
  forecast_12m: 120.0
};

const mockForecast: ForecastSeries = {
  item_id: 1,
  horizon_months: 12,
  granularity: 'month',
  model: 'ewma',
  version: 1,
  points: [
    {
      t: '2024-01-01',
      yhat: 100.0,
      yhat_lower: 95.0,
      yhat_upper: 105.0
    },
    {
      t: '2024-02-01',
      yhat: 105.0,
      yhat_lower: 100.0,
      yhat_upper: 110.0
    }
  ],
  explain: {
    residual_sd: 5.0,
    params: { alpha: 0.3 }
  }
};

const mockQuality: ForecastQuality = {
  item_id: 1,
  model: 'ewma',
  window_days: 90,
  smape: 15.0,
  mape: 14.0,
  wape: 16.0,
  bias_pct: 2.0
};

describe('ItemForecastCard', () => {
  const mockOnClick = jest.fn();

  beforeEach(() => {
    mockOnClick.mockClear();
  });

  test('renders item information correctly', () => {
    render(
      <ItemForecastCard
        item={mockItem}
        isSelected={false}
        onClick={mockOnClick}
      />
    );

    expect(screen.getByText('Test Item')).toBeInTheDocument();
    expect(screen.getByText('£100.00')).toBeInTheDocument();
    expect(screen.getByText('£105.00')).toBeInTheDocument();
    expect(screen.getByText('£110.00')).toBeInTheDocument();
    expect(screen.getByText('£120.00')).toBeInTheDocument();
  });

  test('shows correct trend indicator', () => {
    render(
      <ItemForecastCard
        item={mockItem}
        isSelected={false}
        onClick={mockOnClick}
      />
    );

    expect(screen.getByText('up')).toBeInTheDocument();
  });

  test('applies selected styling when isSelected is true', () => {
    render(
      <ItemForecastCard
        item={mockItem}
        isSelected={true}
        onClick={mockOnClick}
      />
    );

    const card = screen.getByText('Test Item').closest('div');
    expect(card).toHaveClass('border-[#2563EB]', 'bg-[#EFF6FF]');
  });

  test('calls onClick when clicked', () => {
    render(
      <ItemForecastCard
        item={mockItem}
        isSelected={false}
        onClick={mockOnClick}
      />
    );

    fireEvent.click(screen.getByText('Test Item').closest('div')!);
    expect(mockOnClick).toHaveBeenCalledTimes(1);
  });

  test('shows price change percentages', () => {
    render(
      <ItemForecastCard
        item={mockItem}
        isSelected={false}
        onClick={mockOnClick}
      />
    );

    expect(screen.getByText('+5.0%')).toBeInTheDocument();
    expect(screen.getByText('+10.0%')).toBeInTheDocument();
    expect(screen.getByText('+20.0%')).toBeInTheDocument();
  });
});

describe('ForecastChart', () => {
  test('renders chart with forecast data', () => {
    render(<ForecastChart forecast={mockForecast} />);

    expect(screen.getByText('Price Forecast')).toBeInTheDocument();
    expect(screen.getByText('12-month horizon • ewma model')).toBeInTheDocument();
    expect(screen.getByText('v1')).toBeInTheDocument();
  });

  test('renders SVG chart element', () => {
    render(<ForecastChart forecast={mockForecast} />);

    const svg = screen.getByRole('img', { hidden: true });
    expect(svg).toBeInTheDocument();
  });

  test('shows model explanation when available', () => {
    render(<ForecastChart forecast={mockForecast} />);

    expect(screen.getByText('Model Details')).toBeInTheDocument();
    expect(screen.getByText('Residual SD: 5.00')).toBeInTheDocument();
  });

  test('renders legend', () => {
    render(<ForecastChart forecast={mockForecast} />);

    expect(screen.getByText('Forecast')).toBeInTheDocument();
    expect(screen.getByText('80% Confidence')).toBeInTheDocument();
  });
});

describe('ScenarioControls', () => {
  const mockOnScenarioChange = jest.fn();

  beforeEach(() => {
    mockOnScenarioChange.mockClear();
  });

  test('renders scenario controls', () => {
    render(<ScenarioControls onScenarioChange={mockOnScenarioChange} />);

    expect(screen.getByText('Scenario Controls')).toBeInTheDocument();
    expect(screen.getByText('Annual Inflation Rate')).toBeInTheDocument();
    expect(screen.getByText('Last-Minute Shock')).toBeInTheDocument();
    expect(screen.getByText('Weight by venue volume')).toBeInTheDocument();
    expect(screen.getByText('Alternative Supplier')).toBeInTheDocument();
  });

  test('updates inflation rate when slider changes', () => {
    render(<ScenarioControls onScenarioChange={mockOnScenarioChange} />);

    const inflationSlider = screen.getByRole('slider', { name: /annual inflation rate/i });
    fireEvent.change(inflationSlider, { target: { value: '5.0' } });

    expect(mockOnScenarioChange).toHaveBeenCalledWith(
      expect.objectContaining({
        inflation_annual_pct: 5.0
      })
    );
  });

  test('updates shock percentage when slider changes', () => {
    render(<ScenarioControls onScenarioChange={mockOnScenarioChange} />);

    const shockSlider = screen.getByRole('slider', { name: /last-minute shock/i });
    fireEvent.change(shockSlider, { target: { value: '10' } });

    expect(mockOnScenarioChange).toHaveBeenCalledWith(
      expect.objectContaining({
        shock_pct: 10
      })
    );
  });

  test('toggles venue weighting checkbox', () => {
    render(<ScenarioControls onScenarioChange={mockOnScenarioChange} />);

    const venueCheckbox = screen.getByRole('checkbox', { name: /weight by venue volume/i });
    fireEvent.click(venueCheckbox);

    expect(mockOnScenarioChange).toHaveBeenCalledWith(
      expect.objectContaining({
        weight_by_venue: true
      })
    );
  });

  test('changes alternative supplier', () => {
    render(<ScenarioControls onScenarioChange={mockOnScenarioChange} />);

    const supplierSelect = screen.getByRole('combobox', { name: /alternative supplier/i });
    fireEvent.change(supplierSelect, { target: { value: '2' } });

    expect(mockOnScenarioChange).toHaveBeenCalledWith(
      expect.objectContaining({
        alt_supplier_id: 2
      })
    );
  });

  test('resets scenario when reset button clicked', () => {
    render(<ScenarioControls onScenarioChange={mockOnScenarioChange} />);

    const resetButton = screen.getByText('Reset');
    fireEvent.click(resetButton);

    expect(mockOnScenarioChange).toHaveBeenCalledWith(
      expect.objectContaining({
        inflation_annual_pct: 2.5,
        shock_pct: 0,
        weight_by_venue: false,
        alt_supplier_id: undefined
      })
    );
  });

  test('applies preset scenarios', () => {
    render(<ScenarioControls onScenarioChange={mockOnScenarioChange} />);

    const conservativeButton = screen.getByText('Conservative');
    fireEvent.click(conservativeButton);

    expect(mockOnScenarioChange).toHaveBeenCalledWith(
      expect.objectContaining({
        inflation_annual_pct: 1.5,
        shock_pct: -5,
        weight_by_venue: true
      })
    );
  });

  test('shows scenario summary', () => {
    render(<ScenarioControls onScenarioChange={mockOnScenarioChange} />);

    expect(screen.getByText('Scenario Summary')).toBeInTheDocument();
    expect(screen.getByText('Inflation: 2.5% annually')).toBeInTheDocument();
    expect(screen.getByText('Shock: 0% immediate')).toBeInTheDocument();
  });
});

describe('QualityPanel', () => {
  test('renders quality metrics when data is available', () => {
    render(<QualityPanel quality={mockQuality} />);

    expect(screen.getByText('Forecast Quality')).toBeInTheDocument();
    expect(screen.getByText('90-day window')).toBeInTheDocument();
    expect(screen.getByText('ewma')).toBeInTheDocument();
  });

  test('shows all quality metrics', () => {
    render(<QualityPanel quality={mockQuality} />);

    expect(screen.getByText('SMAPE')).toBeInTheDocument();
    expect(screen.getByText('15.0%')).toBeInTheDocument();
    expect(screen.getByText('MAPE')).toBeInTheDocument();
    expect(screen.getByText('14.0%')).toBeInTheDocument();
    expect(screen.getByText('WAPE')).toBeInTheDocument();
    expect(screen.getByText('16.0%')).toBeInTheDocument();
    expect(screen.getByText('Bias')).toBeInTheDocument();
    expect(screen.getByText('+2.0%')).toBeInTheDocument();
  });

  test('shows quality badges', () => {
    render(<QualityPanel quality={mockQuality} />);

    expect(screen.getByText('Good')).toBeInTheDocument();
    expect(screen.getByText('Slight Bias')).toBeInTheDocument();
  });

  test('shows overall quality score', () => {
    render(<QualityPanel quality={mockQuality} />);

    expect(screen.getByText('Overall Quality')).toBeInTheDocument();
    expect(screen.getByText('Quality Score')).toBeInTheDocument();
  });

  test('shows quality guide', () => {
    render(<QualityPanel quality={mockQuality} />);

    expect(screen.getByText('Quality Guide')).toBeInTheDocument();
    expect(screen.getByText(/SMAPE\/MAPE\/WAPE:/)).toBeInTheDocument();
    expect(screen.getByText(/Bias:/)).toBeInTheDocument();
  });

  test('renders empty state when no quality data', () => {
    render(<QualityPanel quality={null} />);

    expect(screen.getByText('Forecast Quality')).toBeInTheDocument();
    expect(screen.getByText('No quality metrics available')).toBeInTheDocument();
  });

  test('applies correct colors for different quality levels', () => {
    const excellentQuality: ForecastQuality = {
      ...mockQuality,
      smape: 5.0,
      mape: 4.0,
      wape: 6.0,
      bias_pct: 1.0
    };

    render(<QualityPanel quality={excellentQuality} />);

    expect(screen.getByText('Excellent')).toBeInTheDocument();
    expect(screen.getByText('Unbiased')).toBeInTheDocument();
  });

  test('applies correct colors for poor quality', () => {
    const poorQuality: ForecastQuality = {
      ...mockQuality,
      smape: 25.0,
      mape: 30.0,
      wape: 28.0,
      bias_pct: 15.0
    };

    render(<QualityPanel quality={poorQuality} />);

    expect(screen.getByText('Poor')).toBeInTheDocument();
    expect(screen.getByText('Biased')).toBeInTheDocument();
  });
});

describe('Forecast UI Integration', () => {
  test('components handle edge cases gracefully', () => {
    // Test with empty forecast points
    const emptyForecast: ForecastSeries = {
      ...mockForecast,
      points: []
    };

    render(<ForecastChart forecast={emptyForecast} />);
    expect(screen.getByText('Price Forecast')).toBeInTheDocument();

    // Test with null quality
    render(<QualityPanel quality={null} />);
    expect(screen.getByText('No quality metrics available')).toBeInTheDocument();
  });

  test('components are accessible', () => {
    render(
      <ItemForecastCard
        item={mockItem}
        isSelected={false}
        onClick={jest.fn()}
      />
    );

    const card = screen.getByText('Test Item').closest('div');
    expect(card).toHaveAttribute('role', 'button');
  });

  test('components handle loading states', () => {
    // This would typically be tested in the parent component
    // but we can test that components render without crashing
    render(<ScenarioControls onScenarioChange={jest.fn()} />);
    expect(screen.getByText('Scenario Controls')).toBeInTheDocument();
  });
}); 