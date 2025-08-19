import React from "react";
import { IconProps } from "./IconTypes";

export function ErrorOctagonIcon({ size = 20, stroke = "#E07A5F", strokeWidth = 1.5, className, ariaLabel }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" role="img" aria-label={ariaLabel || "Error"} className={className}
      fill="none" xmlns="http://www.w3.org/2000/svg" stroke={stroke} strokeWidth={strokeWidth} strokeLinecap="round" strokeLinejoin="round">
      <path d="M8 3h8l5 5v8l-5 5H8l-5-5V8l5-5z"/>
      <path d="M12 8v5M12 16h.01"/>
    </svg>
  );
} 