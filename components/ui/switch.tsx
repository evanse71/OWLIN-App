import React, { forwardRef } from 'react';

interface SwitchProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  checked?: boolean;
  onCheckedChange?: (checked: boolean) => void;
  disabled?: boolean;
  className?: string;
}

export const Switch = forwardRef<HTMLButtonElement, SwitchProps>(
  ({ checked = false, onCheckedChange, disabled = false, className = '', ...props }, ref) => {
    return (
      <button
        ref={ref}
        type="button"
        role="switch"
        aria-checked={checked}
        disabled={disabled}
        onClick={() => onCheckedChange?.(!checked)}
        className={`
          relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50
          ${checked ? 'bg-blue-600' : 'bg-gray-200'}
          ${disabled ? 'cursor-not-allowed' : 'cursor-pointer'}
          ${className}
        `}
        {...props}
      >
        <span
          className={`
            pointer-events-none block h-5 w-5 rounded-full bg-white shadow-lg ring-0 transition-transform
            ${checked ? 'translate-x-5' : 'translate-x-0.5'}
          `}
        />
      </button>
    );
  }
);

Switch.displayName = 'Switch'; 