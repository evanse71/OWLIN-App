import React from "react";
import { IconProps } from "./IconTypes";

export function CreditNoteIcon({ size = 20, stroke = "#1C2A39", strokeWidth = 1.5, className, ariaLabel }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" role="img" aria-label={ariaLabel || "Credit note"} className={className}
      fill="none" xmlns="http://www.w3.org/2000/svg" stroke={stroke} strokeWidth={strokeWidth} strokeLinecap="round" strokeLinejoin="round">
      <rect x="4" y="3" width="16" height="18" rx="2" ry="2"/>
      <path d="M8 9h8M8 13h4"/>
      <circle cx="16.5" cy="13" r="1.5"/>
    </svg>
  );
} 