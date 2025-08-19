import React from 'react';
import { CheckCircleIcon, ClockIcon, WarningTriangleIcon } from '../icons';

interface ConfidenceBadgeProps {
  confidence: number; // 0-100
  showTooltip?: boolean;
  size?: 'sm' | 'md' | 'lg';
}

export default function ConfidenceBadge({ 
  confidence, 
  showTooltip = true, 
  size = 'md' 
}: ConfidenceBadgeProps) {
  const getConfidenceLevel = (conf: number) => {
    if (conf >= 85) return 'high';
    if (conf >= 60) return 'medium';
    return 'low';
  };
  
  const getConfidenceColor = (level: string) => {
    switch (level) {
      case 'high':
        return {
          bg: 'bg-green-100',
          text: 'text-green-800',
          border: 'border-green-200',
          icon: 'text-green-600'
        };
      case 'medium':
        return {
          bg: 'bg-yellow-100',
          text: 'text-yellow-800',
          border: 'border-yellow-200',
          icon: 'text-yellow-600'
        };
      case 'low':
        return {
          bg: 'bg-red-100',
          text: 'text-red-800',
          border: 'border-red-200',
          icon: 'text-red-600'
        };
      default:
        return {
          bg: 'bg-gray-100',
          text: 'text-gray-800',
          border: 'border-gray-200',
          icon: 'text-gray-600'
        };
    }
  };
  
  const getConfidenceIcon = (level: string) => {
    switch (level) {
      case 'high':
        return <CheckCircleIcon size={size === 'sm' ? 12 : size === 'lg' ? 20 : 16} stroke="currentColor" />;
      case 'medium':
        return <ClockIcon size={size === 'sm' ? 12 : size === 'lg' ? 20 : 16} stroke="currentColor" />;
      case 'low':
        return <WarningTriangleIcon size={size === 'sm' ? 12 : size === 'lg' ? 20 : 16} stroke="currentColor" />;
      default:
        return null;
    }
  };
  
  const getTooltipText = (level: string) => {
    switch (level) {
      case 'high':
        return 'OCR results are reliable. Minimal review needed.';
      case 'medium':
        return 'Some uncertainty detected. Please double-check totals.';
      case 'low':
        return 'OCR may have split this invoice incorrectly. Manual review recommended.';
      default:
        return 'Confidence level unknown.';
    }
  };
  
  const level = getConfidenceLevel(confidence);
  const colors = getConfidenceColor(level);
  const icon = getConfidenceIcon(level);
  const tooltipText = getTooltipText(level);
  
  const sizeClasses = {
    sm: 'px-2 py-1 text-xs',
    md: 'px-3 py-1.5 text-sm',
    lg: 'px-4 py-2 text-base'
  };
  
  const badge = (
    <div className={`
      inline-flex items-center gap-1.5 rounded-full border
      ${colors.bg} ${colors.text} ${colors.border}
      ${sizeClasses[size]}
      font-medium
    `}>
      {icon && <span className={colors.icon}>{icon}</span>}
      <span>{confidence}%</span>
    </div>
  );
  
  if (!showTooltip) {
    return badge;
  }
  
  return (
    <div className="relative group" data-ui="confidence-badge">
      {badge}
      <div className="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 px-3 py-2 bg-gray-900 text-white text-xs rounded-lg opacity-0 group-hover:opacity-100 transition-opacity duration-200 pointer-events-none whitespace-nowrap z-10">
        {tooltipText}
        <div className="absolute top-full left-1/2 transform -translate-x-1/2 border-4 border-transparent border-t-gray-900"></div>
      </div>
    </div>
  );
} 