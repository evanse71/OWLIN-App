import React from "react";
import { IconProps } from "./IconTypes";

export function CalendarIcon({ size = 20, stroke = "#1C2A39", strokeWidth = 1.5, className, ariaLabel }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" role="img" aria-label={ariaLabel || "Calendar"} className={className}
      fill="none" xmlns="http://www.w3.org/2000/svg" stroke={stroke} strokeWidth={strokeWidth} strokeLinecap="round" strokeLinejoin="round">
      <rect x="3" y="5" width="18" height="16" rx="2"/>
      <line x1="16" y1="3" x2="16" y2="7"/>
      <line x1="8" y1="3" x2="8" y2="7"/>
      <line x1="3" y1="11" x2="21" y2="11"/>
    </svg>
  );
} 