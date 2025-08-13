import React from 'react';

interface PillProps {
  children: React.ReactNode;
  tone?: 'info' | 'success' | 'warn' | 'neutral';
  className?: string;
}

export const Pill: React.FC<PillProps> = ({ children, tone = 'neutral', className = '' }) => {
  const toneClasses = {
    info: 'bg-[color-mix(in_oklab,var(--owlin-spiro)_20%,white)] text-owlin-rich',
    success: 'bg-[color-mix(in_oklab,var(--owlin-success)_20%,white)] text-owlin-rich',
    warn: 'bg-[color-mix(in_oklab,var(--owlin-warning)_25%,white)] text-owlin-rich',
    neutral: 'bg-owlin-bg text-owlin-muted'
  }[tone];
  return (
    <span className={`inline-flex items-center h-[22px] rounded-full px-2 text-[12px] font-medium ${toneClasses} ${className}`}>
      {children}
    </span>
  );
}; 