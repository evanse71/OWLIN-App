import React from 'react';

interface ButtonProps {
  children: React.ReactNode;
  variant?: 'primary' | 'secondary' | 'quiet' | 'destructive';
  disabled?: boolean;
  onClick?: () => void;
  className?: string;
  type?: 'button' | 'submit' | 'reset';
}

export const Button: React.FC<ButtonProps> = ({ 
  children, 
  variant = 'primary', 
  disabled = false,
  onClick,
  className = '',
  type = 'button'
}) => {
  const base = 'inline-flex items-center justify-center h-10 px-4 rounded-owlin font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-owlin-sapphire focus-visible:ring-offset-2 disabled:opacity-60 disabled:pointer-events-none';
  const tone = {
    primary: 'bg-owlin-sapphire text-white hover:brightness-110',
    secondary: 'border border-owlin-stroke text-owlin-cerulean bg-transparent hover:bg-[color-mix(in_oklab,var(--owlin-card)_92%,transparent)]',
    quiet: 'text-owlin-cerulean hover:bg-[color-mix(in_oklab,var(--owlin-card)_92%,transparent)]',
    destructive: 'bg-owlin-danger text-white hover:brightness-110'
  }[variant];

  return (
    <button
      type={type}
      className={`${base} ${tone} ${className}`}
      disabled={disabled}
      onClick={onClick}
    >
      {children}
    </button>
  );
}; 