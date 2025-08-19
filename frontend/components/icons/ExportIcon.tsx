import React from "react";
import { IconProps } from "./IconTypes";

export function ExportIcon({ size = 20, stroke = "#1C2A39", strokeWidth = 1.5, className, ariaLabel }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" role="img" aria-label={ariaLabel || "Export"} className={className}
      fill="none" xmlns="http://www.w3.org/2000/svg" stroke={stroke} strokeWidth={strokeWidth} strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 16V4"/>
      <path d="M8 8l4-4 4 4"/>
      <rect x="4" y="16" width="16" height="4" rx="1"/>
    </svg>
  );
} 