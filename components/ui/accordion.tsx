import * as React from "react";

export interface AccordionProps extends React.HTMLAttributes<HTMLDivElement> {
  type?: "single" | "multiple";
  collapsible?: boolean;
}

export const Accordion = React.forwardRef<HTMLDivElement, AccordionProps>(
  ({ className = "", type = "single", collapsible = false, ...props }, ref) => (
    <div data-stub="Accordion" className={`accordion ${className}`} ref={ref} {...props} />
  )
);
Accordion.displayName = "Accordion";

export interface AccordionItemProps extends React.HTMLAttributes<HTMLDivElement> {
  value: string;
}

export const AccordionItem = React.forwardRef<HTMLDivElement, AccordionItemProps>(
  ({ className = "", value, ...props }, ref) => (
    <div data-stub="AccordionItem" className={`accordion-item ${className}`} ref={ref} {...props} />
  )
);
AccordionItem.displayName = "AccordionItem";

export interface AccordionTriggerProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {}

export const AccordionTrigger = React.forwardRef<HTMLButtonElement, AccordionTriggerProps>(
  ({ className = "", ...props }, ref) => (
    <button data-stub="AccordionTrigger" className={`accordion-trigger ${className}`} ref={ref} {...props} />
  )
);
AccordionTrigger.displayName = "AccordionTrigger";

export interface AccordionContentProps extends React.HTMLAttributes<HTMLDivElement> {}

export const AccordionContent = React.forwardRef<HTMLDivElement, AccordionContentProps>(
  ({ className = "", ...props }, ref) => (
    <div data-stub="AccordionContent" className={`accordion-content ${className}`} ref={ref} {...props} />
  )
);
AccordionContent.displayName = "AccordionContent";
