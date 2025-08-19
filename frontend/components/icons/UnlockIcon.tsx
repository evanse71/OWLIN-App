import React from "react";
import { IconProps } from "./IconTypes";

export function UnlockIcon({ size = 20, stroke = "#6B7280", strokeWidth = 1.5, className, ariaLabel }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" role="img" aria-label={ariaLabel || "Unlocked"} className={className}
      fill="none" xmlns="http://www.w3.org/2000/svg" stroke={stroke} strokeWidth={strokeWidth} strokeLinecap="round" strokeLinejoin="round">
      <rect x="5" y="10" width="14" height="10" rx="2"/>
      <path d="M9 10V7a4 4 0 0 1 7.5-2"/>
    </svg>
  );
} 