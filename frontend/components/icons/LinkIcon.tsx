import React from "react";
import { IconProps } from "./IconTypes";

export function LinkIcon({ size = 20, stroke = "#6B7280", strokeWidth = 1.5, className, ariaLabel }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" role="img" aria-label={ariaLabel || "Link"} className={className}
      fill="none" xmlns="http://www.w3.org/2000/svg" stroke={stroke} strokeWidth={strokeWidth} strokeLinecap="round" strokeLinejoin="round">
      <path d="M9 15a4 4 0 0 1 0-6l2-2"/>
      <path d="M15 9a4 4 0 0 1 0 6l-2 2"/>
      <path d="M8 12h8"/>
    </svg>
  );
} 