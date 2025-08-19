import React from "react";
import { IconProps } from "./IconTypes";

export function WarningTriangleIcon({ size = 20, stroke = "#D97706", strokeWidth = 1.5, className, ariaLabel }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" role="img" aria-label={ariaLabel || "Warning"} className={className}
      fill="none" xmlns="http://www.w3.org/2000/svg" stroke={stroke} strokeWidth={strokeWidth} strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 3l9 16H3l9-16z"/>
      <path d="M12 9v4M12 17h.01"/>
    </svg>
  );
} 