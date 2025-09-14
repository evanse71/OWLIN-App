import * as React from "react";

export interface CardProps extends React.HTMLAttributes<HTMLDivElement> {}

export const Card = React.forwardRef<HTMLDivElement, CardProps>(
  ({ className = "", ...props }, ref) => (
    <div data-stub="Card" className={`card ${className}`} ref={ref} {...props} />
  )
);
Card.displayName = "Card";

export interface CardContentProps extends React.HTMLAttributes<HTMLDivElement> {}

export const CardContent = React.forwardRef<HTMLDivElement, CardContentProps>(
  ({ className = "", ...props }, ref) => (
    <div data-stub="CardContent" className={`card-content ${className}`} ref={ref} {...props} />
  )
);
CardContent.displayName = "CardContent";

export interface CardHeaderProps extends React.HTMLAttributes<HTMLDivElement> {}

export const CardHeader = React.forwardRef<HTMLDivElement, CardHeaderProps>(
  ({ className = "", ...props }, ref) => (
    <div data-stub="CardHeader" className={`card-header ${className}`} ref={ref} {...props} />
  )
);
CardHeader.displayName = "CardHeader";

export interface CardTitleProps extends React.HTMLAttributes<HTMLHeadingElement> {}

export const CardTitle = React.forwardRef<HTMLHeadingElement, CardTitleProps>(
  ({ className = "", ...props }, ref) => (
    <h3 data-stub="CardTitle" className={`card-title ${className}`} ref={ref} {...props} />
  )
);
CardTitle.displayName = "CardTitle";