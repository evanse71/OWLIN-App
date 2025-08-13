import React, { forwardRef } from 'react';

interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  className?: string;
}

export const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ className = '', ...props }, ref) => {
    return (
      <input
        ref={ref}
        className={`flex h-10 w-full rounded-owlin border border-owlin-stroke bg-owlin-card px-3 text-sm placeholder:text-owlin-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-owlin-sapphire focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-60 ${className}`}
        {...props}
      />
    );
  }
);

Input.displayName = 'Input'; 