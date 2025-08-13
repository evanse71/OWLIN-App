import React from 'react';

export const Section: React.FC<{ children: React.ReactNode; className?: string }> = ({ children, className = '' }) => (
  <div className={`max-w-[1280px] mx-auto px-6 lg:px-8 py-6 bg-owlin-bg ${className}`}>{children}</div>
); 