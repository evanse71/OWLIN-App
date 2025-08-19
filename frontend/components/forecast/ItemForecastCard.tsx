// ICONS: replaced inline SVGs with local icon components
import React from 'react';
import { ForecastItem } from '../../types/forecast';
import { InfoIcon } from '../icons';

interface ItemForecastCardProps {
  item: ForecastItem;
  isSelected: boolean;
  onClick: () => void;
}

const ItemForecastCard: React.FC<ItemForecastCardProps> = ({ item, isSelected, onClick }) => {
  const getTrendColor = (trend: string) => {
    switch (trend.toLowerCase()) {
      case 'up':
        return 'text-red-600';
      case 'down':
        return 'text-green-600';
      case 'stable':
        return 'text-gray-600';
      default:
        return 'text-gray-600';
    }
  };

  const getTrendIcon = (trend: string) => {
    switch (trend.toLowerCase()) {
      case 'up':
        return (
          <svg className="h-4 w-4" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M12 7a1 1 0 110-2h5a1 1 0 011 1v5a1 1 0 11-2 0V8.414l-4.293 4.293a1 1 0 01-1.414 0L8 10.414l-4.293 4.293a1 1 0 01-1.414-1.414l5-5a1 1 0 011.414 0L11 10.586 14.586 7H12z" clipRule="evenodd" />
          </svg>
        );
      case 'down':
        return (
          <svg className="h-4 w-4" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M12 13a1 1 0 100 2h5a1 1 0 001-1v-5a1 1 0 10-2 0v2.586l-4.293-4.293a1 1 0 00-1.414 0L8 9.586l-4.293-4.293a1 1 0 00-1.414 1.414l5 5a1 1 0 001.414 0L11 9.414 14.586 13H12z" clipRule="evenodd" />
          </svg>
        );
      case 'stable':
        return (
          <svg className="h-4 w-4" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M3 10a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1z" clipRule="evenodd" />
          </svg>
        );
      default:
        return <InfoIcon size={16} className="text-gray-400" ariaLabel="Unknown trend" />;
    }
  };

  const formatPrice = (price: number) => {
    return new Intl.NumberFormat('en-GB', {
      style: 'currency',
      currency: 'GBP',
      minimumFractionDigits: 2
    }).format(price);
  };

  const getPriceChange = (current: number, forecast: number) => {
    const change = ((forecast - current) / current) * 100;
    return change > 0 ? `+${change.toFixed(1)}%` : `${change.toFixed(1)}%`;
  };

  return (
    <div
      onClick={onClick}
      className={`
        p-3 rounded-[8px] border cursor-pointer transition-all duration-200
        ${isSelected 
          ? 'border-[#2563EB] bg-[#EFF6FF] shadow-sm' 
          : 'border-[#E5E7EB] bg-white hover:border-[#D1D5DB] hover:shadow-sm'
        }
      `}
    >
      <div className="flex justify-between items-start mb-2">
        <h4 className="font-medium text-gray-900 text-sm truncate flex-1">
          {item.name}
        </h4>
        <div className={`flex items-center gap-1 ${getTrendColor(item.trend)}`}>
          {getTrendIcon(item.trend)}
          <span className="text-xs font-medium">{item.trend}</span>
        </div>
      </div>
      
      <div className="space-y-1">
        <div className="flex justify-between items-center">
          <span className="text-xs text-gray-600">Current:</span>
          <span className="text-sm font-medium text-gray-900">
            {formatPrice(item.latest_price)}
          </span>
        </div>
        
        <div className="flex justify-between items-center">
          <span className="text-xs text-gray-600">1M:</span>
          <span className="text-sm font-medium text-gray-900">
            {formatPrice(item.forecast_1m)}
            <span className={`ml-1 text-xs ${item.forecast_1m > item.latest_price ? 'text-red-600' : 'text-green-600'}`}>
              {getPriceChange(item.latest_price, item.forecast_1m)}
            </span>
          </span>
        </div>
        
        <div className="flex justify-between items-center">
          <span className="text-xs text-gray-600">3M:</span>
          <span className="text-sm font-medium text-gray-900">
            {formatPrice(item.forecast_3m)}
            <span className={`ml-1 text-xs ${item.forecast_3m > item.latest_price ? 'text-red-600' : 'text-green-600'}`}>
              {getPriceChange(item.latest_price, item.forecast_3m)}
            </span>
          </span>
        </div>
        
        <div className="flex justify-between items-center">
          <span className="text-xs text-gray-600">12M:</span>
          <span className="text-sm font-medium text-gray-900">
            {formatPrice(item.forecast_12m)}
            <span className={`ml-1 text-xs ${item.forecast_12m > item.latest_price ? 'text-red-600' : 'text-green-600'}`}>
              {getPriceChange(item.latest_price, item.forecast_12m)}
            </span>
          </span>
        </div>
      </div>
    </div>
  );
};

export default ItemForecastCard; 