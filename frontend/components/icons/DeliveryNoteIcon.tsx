import React from "react";
import { IconProps } from "./IconTypes";

export function DeliveryNoteIcon({ size = 20, stroke = "#1C2A39", strokeWidth = 1.5, className, ariaLabel }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" role="img" aria-label={ariaLabel || "Delivery note"} className={className}
      fill="none" xmlns="http://www.w3.org/2000/svg" stroke={stroke} strokeWidth={strokeWidth} strokeLinecap="round" strokeLinejoin="round">
      <rect x="4" y="3" width="16" height="18" rx="2" ry="2"/>
      <path d="M8 7h8M8 11h6M8 15h8"/>
      <path d="M4 7h2M18 7h2"/>
    </svg>
  );
} 