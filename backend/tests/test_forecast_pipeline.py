import pytest
import numpy as np
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from services.forecast_service import (
    ForecastService,
    preprocess_price_history,
    select_best_model,
    calculate_confidence_intervals,
    apply_scenario_adjustments
)
from contracts import ForecastPoint, ForecastSeries, ForecastQuality, ForecastScenario


class TestForecastService:
    @pytest.fixture
    def forecast_service(self):
        return ForecastService()

    @pytest.fixture
    def sample_price_history(self):
        """Generate sample price history for testing"""
        dates = []
        prices = []
        base_price = 100.0
        
        for i in range(24):  # 2 years of monthly data
            date = datetime.now() - timedelta(days=30 * i)
            dates.append(date.strftime('%Y-%m-%d'))
            # Add some trend and noise
            price = base_price + (i * 2) + np.random.normal(0, 5)
            prices.append(max(price, 10))  # Ensure positive prices
        
        return list(zip(dates, prices))

    def test_preprocess_price_history(self, sample_price_history):
        """Test price history preprocessing"""
        processed = preprocess_price_history(sample_price_history)
        
        assert len(processed) > 0
        assert all(isinstance(p, (int, float)) for p in processed)
        assert all(p > 0 for p in processed)
        
        # Test outlier handling
        outlier_data = [
            ('2024-01-01', 100),
            ('2024-02-01', 2000),  # Outlier
            ('2024-03-01', 110),
            ('2024-04-01', 105)
        ]
        processed_outlier = preprocess_price_history(outlier_data)
        assert len(processed_outlier) == 4
        # Outlier should be capped
        assert processed_outlier[1] < 2000

    def test_select_best_model(self, sample_price_history):
        """Test model selection logic"""
        processed_data = preprocess_price_history(sample_price_history)
        
        # Test with sufficient data
        if len(processed_data) >= 12:
            model, metrics = select_best_model(processed_data)
            assert model in ['naive', 'seasonal_naive', 'ewma', 'holt_winters']
            assert 'smape' in metrics
            assert 'mape' in metrics
            assert 'wape' in metrics
            assert 'bias_pct' in metrics

    def test_calculate_confidence_intervals(self):
        """Test confidence interval calculation"""
        forecast_values = [100, 105, 110, 115, 120]
        residual_std = 5.0
        
        intervals = calculate_confidence_intervals(forecast_values, residual_std)
        
        assert len(intervals) == len(forecast_values)
        for lower, upper in intervals:
            assert lower < upper
            assert lower > 0

    def test_apply_scenario_adjustments(self):
        """Test scenario adjustment application"""
        base_forecast = [100, 105, 110, 115, 120]
        scenario = ForecastScenario(
            inflation_annual_pct=2.5,
            shock_pct=5.0,
            weight_by_venue=False,
            alt_supplier_id=None
        )
        
        adjusted = apply_scenario_adjustments(base_forecast, scenario)
        
        assert len(adjusted) == len(base_forecast)
        # With 5% shock, first value should be higher
        assert adjusted[0] > base_forecast[0]
        # With inflation, later values should be progressively higher
        assert adjusted[-1] > adjusted[0]

    @patch('services.forecast_service.get_conn')
    def test_generate_forecast(self, mock_get_conn, forecast_service, sample_price_history):
        """Test full forecast generation"""
        # Mock database connection
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_get_conn.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        
        # Mock price history query
        mock_cursor.fetchall.return_value = sample_price_history
        
        # Test forecast generation
        item_id = 1
        horizon_months = 12
        
        with patch.object(forecast_service, 'select_best_model') as mock_select:
            mock_select.return_value = ('ewma', {
                'smape': 15.0,
                'mape': 14.0,
                'wape': 16.0,
                'bias_pct': 2.0
            })
            
            forecast = forecast_service.generate_forecast(item_id, horizon_months)
            
            assert isinstance(forecast, ForecastSeries)
            assert forecast.item_id == item_id
            assert forecast.horizon_months == horizon_months
            assert len(forecast.points) == horizon_months
            assert forecast.model == 'ewma'

    def test_forecast_quality_calculation(self, forecast_service):
        """Test forecast quality metrics calculation"""
        actual_values = [100, 105, 110, 115, 120]
        predicted_values = [102, 104, 108, 116, 118]
        
        quality = forecast_service.calculate_quality_metrics(actual_values, predicted_values)
        
        assert isinstance(quality, ForecastQuality)
        assert 0 <= quality.smape <= 100
        assert 0 <= quality.mape <= 100
        assert 0 <= quality.wape <= 100
        assert isinstance(quality.bias_pct, float)

    @patch('services.forecast_service.get_conn')
    def test_rolling_backtest(self, mock_get_conn, forecast_service):
        """Test rolling backtest functionality"""
        # Mock database connection
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_get_conn.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        
        # Mock historical data
        mock_cursor.fetchall.return_value = [
            ('2024-01-01', 100),
            ('2024-02-01', 105),
            ('2024-03-01', 110),
            ('2024-04-01', 115),
            ('2024-05-01', 120)
        ]
        
        item_id = 1
        window_days = 90
        
        results = forecast_service.rolling_backtest(item_id, window_days)
        
        assert isinstance(results, list)
        if results:  # If we have enough data for backtesting
            for result in results:
                assert 'model' in result
                assert 'smape' in result
                assert 'mape' in result
                assert 'wape' in result
                assert 'bias_pct' in result

    def test_scenario_validation(self, forecast_service):
        """Test scenario parameter validation"""
        # Valid scenario
        valid_scenario = ForecastScenario(
            inflation_annual_pct=2.5,
            shock_pct=5.0,
            weight_by_venue=True,
            alt_supplier_id=None
        )
        assert forecast_service.validate_scenario(valid_scenario)
        
        # Invalid scenario (negative inflation)
        invalid_scenario = ForecastScenario(
            inflation_annual_pct=-1.0,
            shock_pct=0.0,
            weight_by_venue=False,
            alt_supplier_id=None
        )
        assert not forecast_service.validate_scenario(invalid_scenario)

    @patch('services.forecast_service.get_conn')
    def test_forecast_persistence(self, mock_get_conn, forecast_service):
        """Test forecast data persistence"""
        # Mock database connection
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_get_conn.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        
        # Create sample forecast
        forecast = ForecastSeries(
            item_id=1,
            horizon_months=12,
            granularity="month",
            model="ewma",
            version=1,
            points=[
                ForecastPoint(
                    t="2024-01-01",
                    yhat=100.0,
                    yhat_lower=95.0,
                    yhat_upper=105.0
                )
            ],
            explain={"residual_sd": 5.0}
        )
        
        # Test persistence
        success = forecast_service.save_forecast(forecast)
        assert success
        
        # Verify SQL was called
        mock_cursor.execute.assert_called()

    def test_performance_targets(self, forecast_service, sample_price_history):
        """Test performance targets are met"""
        import time
        
        processed_data = preprocess_price_history(sample_price_history)
        
        # Test preprocessing performance
        start_time = time.time()
        preprocess_price_history(sample_price_history)
        preprocessing_time = time.time() - start_time
        
        # Test model selection performance
        start_time = time.time()
        select_best_model(processed_data)
        selection_time = time.time() - start_time
        
        # Test confidence interval calculation performance
        start_time = time.time()
        calculate_confidence_intervals([100, 105, 110], 5.0)
        interval_time = time.time() - start_time
        
        # All operations should be fast
        assert preprocessing_time < 0.1  # 100ms
        assert selection_time < 0.1      # 100ms
        assert interval_time < 0.01      # 10ms

    def test_error_handling(self, forecast_service):
        """Test error handling in forecast pipeline"""
        # Test with empty data
        with pytest.raises(ValueError):
            preprocess_price_history([])
        
        # Test with insufficient data
        insufficient_data = [('2024-01-01', 100)]
        with pytest.raises(ValueError):
            select_best_model(preprocess_price_history(insufficient_data))
        
        # Test with invalid scenario
        invalid_scenario = ForecastScenario(
            inflation_annual_pct=15.0,  # Too high
            shock_pct=0.0,
            weight_by_venue=False,
            alt_supplier_id=None
        )
        assert not forecast_service.validate_scenario(invalid_scenario)

    def test_model_explainability(self, forecast_service):
        """Test model explainability features"""
        # Test EWMA explanation
        ewma_explanation = forecast_service.explain_model('ewma', {'alpha': 0.3})
        assert 'alpha' in ewma_explanation
        assert 'smoothing_factor' in ewma_explanation
        
        # Test Holt-Winters explanation
        hw_explanation = forecast_service.explain_model('holt_winters', {
            'alpha': 0.3,
            'beta': 0.1,
            'gamma': 0.2
        })
        assert 'alpha' in hw_explanation
        assert 'beta' in hw_explanation
        assert 'gamma' in hw_explanation


if __name__ == '__main__':
    pytest.main([__file__]) 