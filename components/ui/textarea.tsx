import React, { forwardRef } from 'react';

interface TextareaProps extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {
  className?: string;
}

export const Textarea = forwardRef<HTMLTextAreaElement, TextareaProps>(({ className = '', ...props }, ref) => {
  return (
    <textarea
      ref={ref}
      className={`w-full rounded-owlin border border-owlin-stroke bg-owlin-card px-3 py-2 text-sm placeholder:text-owlin-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-owlin-sapphire focus-visible:ring-offset-2 ${className}`}
      {...props}
    />
  );
});

Textarea.displayName = 'Textarea'; 