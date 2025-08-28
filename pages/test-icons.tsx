import React from 'react';
import Icons from '@/components/icons';

export default function TestIcons() {
  return (
    <div className="grid grid-cols-6 gap-3">
      {Object.entries(Icons).map(([name, Icon]) => (
        <div key={String(name)} className="flex items-center gap-2 text-sm">
          <Icon className="h-4 w-4" aria-hidden="true" />
          <span>{String(name)}</span>
        </div>
      ))}
    </div>
  );
} 