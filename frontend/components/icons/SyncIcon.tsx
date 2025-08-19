import React from "react";
import { IconProps } from "./IconTypes";

export function SyncIcon({ size = 20, stroke = "#1C2A39", strokeWidth = 1.5, className, ariaLabel }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" role="img" aria-label={ariaLabel || "Sync"} className={className}
      fill="none" xmlns="http://www.w3.org/2000/svg" stroke={stroke} strokeWidth={strokeWidth} strokeLinecap="round" strokeLinejoin="round">
      <path d="M3 12a9 9 0 0 1 15.54-5.64"/>
      <path d="M21 3v6h-6"/>
      <path d="M21 12a9 9 0 0 1-15.54 5.64"/>
      <path d="M3 21v-6h6"/>
    </svg>
  );
} 