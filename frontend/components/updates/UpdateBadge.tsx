import React from 'react';

interface UpdateBadgeProps {
  type: 'validation' | 'dependency';
  status: 'ok' | 'warn' | 'error';
  text: string;
}

export default function UpdateBadge({ type, status, text }: UpdateBadgeProps) {
  const getStatusColors = () => {
    switch (status) {
      case 'ok':
        return 'bg-green-100 text-green-800 border-green-200';
      case 'warn':
        return 'bg-yellow-100 text-yellow-800 border-yellow-200';
      case 'error':
        return 'bg-red-100 text-red-800 border-red-200';
      default:
        return 'bg-gray-100 text-gray-800 border-gray-200';
    }
  };

  const getIcon = () => {
    switch (type) {
      case 'validation':
        return status === 'ok' ? '✓' : status === 'warn' ? '⚠' : '✗';
      case 'dependency':
        return status === 'ok' ? '🔗' : status === 'warn' ? '⚠' : '❌';
      default:
        return '•';
    }
  };

  return (
    <span className={`inline-flex items-center gap-1 px-2 py-1 text-xs font-medium rounded-full border ${getStatusColors()}`}>
      <span className="text-xs">{getIcon()}</span>
      {text}
    </span>
  );
}
