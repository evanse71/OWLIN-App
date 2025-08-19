import React, { useState } from 'react';
import { ForecastScenario } from '../../types/forecast';

interface ScenarioControlsProps {
  onScenarioChange: (scenario: ForecastScenario) => void;
}

const ScenarioControls: React.FC<ScenarioControlsProps> = ({ onScenarioChange }) => {
  const [scenario, setScenario] = useState<ForecastScenario>({
    inflation_annual_pct: 2.5,
    shock_pct: 0,
    weight_by_venue: false,
    alt_supplier_id: undefined
  });

  const handleChange = (field: keyof ForecastScenario, value: any) => {
    const newScenario = { ...scenario, [field]: value };
    setScenario(newScenario);
    onScenarioChange(newScenario);
  };

  const resetScenario = () => {
    const defaultScenario: ForecastScenario = {
      inflation_annual_pct: 2.5,
      shock_pct: 0,
      weight_by_venue: false,
      alt_supplier_id: undefined
    };
    setScenario(defaultScenario);
    onScenarioChange(defaultScenario);
  };

  return (
    <div className="bg-white rounded-[12px] p-6 shadow-sm">
      <div className="flex justify-between items-center mb-4">
        <h3 className="text-lg font-semibold text-gray-900">Scenario Controls</h3>
        <button
          onClick={resetScenario}
          className="text-sm text-[#2563EB] hover:text-[#1D4ED8]"
        >
          Reset
        </button>
      </div>

      <div className="space-y-4">
        {/* Inflation Rate */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Annual Inflation Rate
          </label>
          <div className="flex items-center space-x-2">
            <input
              type="range"
              min="0"
              max="10"
              step="0.1"
              value={scenario.inflation_annual_pct}
              onChange={(e) => handleChange('inflation_annual_pct', parseFloat(e.target.value))}
              className="flex-1 h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer slider"
            />
            <span className="text-sm font-medium text-gray-900 w-12">
              {scenario.inflation_annual_pct}%
            </span>
          </div>
          <div className="flex justify-between text-xs text-gray-500 mt-1">
            <span>0%</span>
            <span>10%</span>
          </div>
        </div>

        {/* Shock Percentage */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Last-Minute Shock
          </label>
          <div className="flex items-center space-x-2">
            <input
              type="range"
              min="-20"
              max="20"
              step="1"
              value={scenario.shock_pct}
              onChange={(e) => handleChange('shock_pct', parseFloat(e.target.value))}
              className="flex-1 h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer slider"
            />
            <span className={`text-sm font-medium w-12 ${
              scenario.shock_pct > 0 ? 'text-red-600' : 
              scenario.shock_pct < 0 ? 'text-green-600' : 'text-gray-900'
            }`}>
              {scenario.shock_pct > 0 ? '+' : ''}{scenario.shock_pct}%
            </span>
          </div>
          <div className="flex justify-between text-xs text-gray-500 mt-1">
            <span>-20%</span>
            <span>+20%</span>
          </div>
        </div>

        {/* Venue Weighting */}
        <div>
          <label className="flex items-center">
            <input
              type="checkbox"
              checked={scenario.weight_by_venue}
              onChange={(e) => handleChange('weight_by_venue', e.target.checked)}
              className="rounded border-gray-300 text-[#2563EB] focus:ring-[#A7C4A0]"
            />
            <span className="ml-2 text-sm text-gray-700">Weight by venue volume</span>
          </label>
          <p className="text-xs text-gray-500 mt-1">
            Adjust forecasts based on venue-specific demand patterns
          </p>
        </div>

        {/* Alternative Supplier */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Alternative Supplier
          </label>
          <select
            value={scenario.alt_supplier_id || ''}
            onChange={(e) => handleChange('alt_supplier_id', e.target.value ? parseInt(e.target.value) : undefined)}
            className="w-full px-3 py-2 border border-gray-300 rounded-[8px] focus:outline-none focus:ring-2 focus:ring-[#A7C4A0] text-sm"
          >
            <option value="">Use current supplier</option>
            <option value="1">Supplier A (Premium)</option>
            <option value="2">Supplier B (Budget)</option>
            <option value="3">Supplier C (Local)</option>
          </select>
          <p className="text-xs text-gray-500 mt-1">
            Simulate pricing from alternative suppliers
          </p>
        </div>

        {/* Scenario Summary */}
        <div className="mt-6 p-3 bg-gray-50 rounded-[8px]">
          <h4 className="text-sm font-medium text-gray-900 mb-2">Scenario Summary</h4>
          <div className="text-xs text-gray-600 space-y-1">
            <div>Inflation: {scenario.inflation_annual_pct}% annually</div>
            <div>Shock: {scenario.shock_pct > 0 ? '+' : ''}{scenario.shock_pct}% immediate</div>
            <div>Venue weighting: {scenario.weight_by_venue ? 'Enabled' : 'Disabled'}</div>
            <div>Supplier: {scenario.alt_supplier_id ? `Alternative (ID: ${scenario.alt_supplier_id})` : 'Current'}</div>
          </div>
        </div>

        {/* Preset Scenarios */}
        <div className="mt-4">
          <h4 className="text-sm font-medium text-gray-900 mb-2">Quick Presets</h4>
          <div className="grid grid-cols-2 gap-2">
            <button
              onClick={() => {
                const conservative: ForecastScenario = {
                  inflation_annual_pct: 1.5,
                  shock_pct: -5,
                  weight_by_venue: true,
                  alt_supplier_id: undefined
                };
                setScenario(conservative);
                onScenarioChange(conservative);
              }}
              className="px-3 py-2 text-xs bg-green-50 text-green-700 border border-green-200 rounded-[6px] hover:bg-green-100"
            >
              Conservative
            </button>
            <button
              onClick={() => {
                const aggressive: ForecastScenario = {
                  inflation_annual_pct: 4.0,
                  shock_pct: 10,
                  weight_by_venue: false,
                  alt_supplier_id: undefined
                };
                setScenario(aggressive);
                onScenarioChange(aggressive);
              }}
              className="px-3 py-2 text-xs bg-red-50 text-red-700 border border-red-200 rounded-[6px] hover:bg-red-100"
            >
              Aggressive
            </button>
            <button
              onClick={() => {
                const stable: ForecastScenario = {
                  inflation_annual_pct: 2.0,
                  shock_pct: 0,
                  weight_by_venue: true,
                  alt_supplier_id: undefined
                };
                setScenario(stable);
                onScenarioChange(stable);
              }}
              className="px-3 py-2 text-xs bg-blue-50 text-blue-700 border border-blue-200 rounded-[6px] hover:bg-blue-100"
            >
              Stable
            </button>
            <button
              onClick={() => {
                const alternative: ForecastScenario = {
                  inflation_annual_pct: 2.5,
                  shock_pct: 0,
                  weight_by_venue: false,
                  alt_supplier_id: 2
                };
                setScenario(alternative);
                onScenarioChange(alternative);
              }}
              className="px-3 py-2 text-xs bg-purple-50 text-purple-700 border border-purple-200 rounded-[6px] hover:bg-purple-100"
            >
              Alternative Supplier
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ScenarioControls; 