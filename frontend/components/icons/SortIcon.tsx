import React from "react";
import { IconProps } from "./IconTypes";

export function SortIcon({ size = 20, stroke = "#1C2A39", strokeWidth = 1.5, className, ariaLabel }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" role="img" aria-label={ariaLabel || "Sort"} className={className}
      fill="none" xmlns="http://www.w3.org/2000/svg" stroke={stroke} strokeWidth={strokeWidth} strokeLinecap="round" strokeLinejoin="round">
      <path d="M6 4v16M6 4l-3 3M6 4l3 3"/>
      <path d="M18 20V4M18 20l3-3M18 20l-3-3"/>
    </svg>
  );
} 