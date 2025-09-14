import * as React from "react";

export const Toast = React.forwardRef<HTMLDivElement, any>(({ children, ...props }, ref) => (
  <div data-stub="Toast" ref={ref} {...props}>{children}</div>
));
Toast.displayName = "Toast";

export const ToastClose = React.forwardRef<HTMLButtonElement, any>(({ children, ...props }, ref) => (
  <button data-stub="ToastClose" ref={ref} {...props}>{children}</button>
));
ToastClose.displayName = "ToastClose";

export const ToastDescription = React.forwardRef<HTMLDivElement, any>(({ children, ...props }, ref) => (
  <div data-stub="ToastDescription" ref={ref} {...props}>{children}</div>
));
ToastDescription.displayName = "ToastDescription";

export const ToastTitle = React.forwardRef<HTMLDivElement, any>(({ children, ...props }, ref) => (
  <div data-stub="ToastTitle" ref={ref} {...props}>{children}</div>
));
ToastTitle.displayName = "ToastTitle";

export const ToastViewport = React.forwardRef<HTMLDivElement, any>(({ children, ...props }, ref) => (
  <div data-stub="ToastViewport" ref={ref} {...props}>{children}</div>
));
ToastViewport.displayName = "ToastViewport";

export const ToastActionElement = React.forwardRef<HTMLButtonElement, any>(({ children, ...props }, ref) => (
  <button data-stub="ToastActionElement" ref={ref} {...props}>{children}</button>
));
ToastActionElement.displayName = "ToastActionElement";

export interface ToastProps {
  children?: React.ReactNode;
  [key: string]: any;
}

export const ToastProvider = React.forwardRef<HTMLDivElement, any>(({ children, ...props }, ref) => (
  <div data-stub="ToastProvider" ref={ref} {...props}>{children}</div>
));
ToastProvider.displayName = "ToastProvider";