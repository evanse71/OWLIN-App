import React from "react";
import { IconProps } from "./IconTypes";

export function ImportIcon({ size = 20, stroke = "#1C2A39", strokeWidth = 1.5, className, ariaLabel }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" role="img" aria-label={ariaLabel || "Import"} className={className}
      fill="none" xmlns="http://www.w3.org/2000/svg" stroke={stroke} strokeWidth={strokeWidth} strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 8v12"/>
      <path d="M8 12l4 4 4-4"/>
      <rect x="4" y="4" width="16" height="4" rx="1"/>
    </svg>
  );
} 