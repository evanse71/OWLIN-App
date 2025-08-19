import React from "react";
import { IconProps } from "./IconTypes";

export function ProgressCircleIcon({ size = 20, stroke = "#1C2A39", strokeWidth = 1.5, className, ariaLabel }: IconProps) {
  const r = 9, c = 2 * Math.PI * r;
  const dash = c * 0.65; // 65% slice
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" role="img" aria-label={ariaLabel || "Progress"} className={className}
      fill="none" xmlns="http://www.w3.org/2000/svg">
      <circle cx="12" cy="12" r={r} stroke="#E5E7EB" strokeWidth={strokeWidth}/>
      <circle cx="12" cy="12" r={r} stroke={stroke} strokeWidth={strokeWidth} strokeLinecap="round"
              strokeDasharray={`${dash} ${c - dash}`} transform="rotate(-90 12 12)"/>
    </svg>
  );
} 