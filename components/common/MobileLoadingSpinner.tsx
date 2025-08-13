import React from 'react';
import { cn } from '@/lib/utils';
import { Loader2 } from 'lucide-react';

interface MobileLoadingSpinnerProps {
  size?: 'sm' | 'md' | 'lg';
  variant?: 'default' | 'primary' | 'success' | 'warning' | 'error';
  text?: string;
  className?: string;
  showText?: boolean;
}

const MobileLoadingSpinner: React.FC<MobileLoadingSpinnerProps> = ({
  size = 'md',
  variant = 'default',
  text = 'Loading...',
  className,
  showText = true,
}) => {
  const sizeClasses = {
    sm: 'w-4 h-4',
    md: 'w-6 h-6',
    lg: 'w-8 h-8',
  };

  const variantClasses = {
    default: 'text-gray-600',
    primary: 'text-blue-600',
    success: 'text-green-600',
    warning: 'text-yellow-600',
    error: 'text-red-600',
  };

  const textSizeClasses = {
    sm: 'text-xs',
    md: 'text-sm',
    lg: 'text-base',
  };

  return (
    <div className={cn(
      "flex flex-col items-center justify-center space-y-2 touch-optimized",
      className
    )}>
      {/* Spinner */}
      <div className="relative">
        <Loader2 
          className={cn(
            "animate-spin",
            sizeClasses[size],
            variantClasses[variant]
          )} 
        />
        
        {/* Pulse effect for mobile */}
        <div className={cn(
          "absolute inset-0 rounded-full animate-ping opacity-20",
          sizeClasses[size],
          variantClasses[variant]
        )} />
      </div>

      {/* Loading text */}
      {showText && text && (
        <div className={cn(
          "text-center font-medium",
          textSizeClasses[size],
          variantClasses[variant]
        )}>
          {text}
        </div>
      )}

      {/* Mobile-optimized dots animation */}
      <div className="flex space-x-1">
        <div className={cn(
          "w-1.5 h-1.5 rounded-full animate-bounce",
          variantClasses[variant]
        )} 
        style={{ animationDelay: '0ms' }} 
        />
        <div className={cn(
          "w-1.5 h-1.5 rounded-full animate-bounce",
          variantClasses[variant]
        )} 
        style={{ animationDelay: '150ms' }} 
        />
        <div className={cn(
          "w-1.5 h-1.5 rounded-full animate-bounce",
          variantClasses[variant]
        )} 
        style={{ animationDelay: '300ms' }} 
        />
      </div>
    </div>
  );
};

export default MobileLoadingSpinner; 