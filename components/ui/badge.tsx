import * as React from "react";

export interface BadgeProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: "default" | "secondary" | "destructive" | "outline";
}

export const Badge = React.forwardRef<HTMLDivElement, BadgeProps>(
  ({ className = "", variant = "default", ...props }, ref) => (
    <div data-stub="Badge" className={`badge badge-${variant} ${className}`} ref={ref} {...props} />
  )
);
Badge.displayName = "Badge";