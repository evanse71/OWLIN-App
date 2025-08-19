import React from "react";
import { IconProps } from "./IconTypes";

export function UploadIcon({ size = 20, stroke = "#1C2A39", strokeWidth = 1.5, className, ariaLabel }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" role="img" aria-label={ariaLabel || "Upload"} className={className}
      fill="none" xmlns="http://www.w3.org/2000/svg" stroke={stroke} strokeWidth={strokeWidth} strokeLinecap="round" strokeLinejoin="round">
      <path d="M4 17v2a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-2"/>
      <polyline points="7 9 12 4 17 9"/>
      <line x1="12" y1="4" x2="12" y2="16"/>
    </svg>
  );
} 