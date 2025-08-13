import React, { forwardRef } from 'react';

interface SelectProps extends React.SelectHTMLAttributes<HTMLSelectElement> {
  className?: string;
}

export const Select = forwardRef<HTMLSelectElement, SelectProps>(({ className = '', children, ...props }, ref) => {
  return (
    <select
      ref={ref}
      className={`h-10 rounded-owlin border border-owlin-stroke bg-owlin-card px-3 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-owlin-sapphire focus-visible:ring-offset-2 ${className}`}
      {...props}
    >
      {children}
    </select>
  );
});

Select.displayName = 'Select'; 