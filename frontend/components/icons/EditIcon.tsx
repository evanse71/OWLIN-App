import React from "react";
import { IconProps } from "./IconTypes";

export function EditIcon({ size = 20, stroke = "#1C2A39", strokeWidth = 1.5, className, ariaLabel }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" role="img" aria-label={ariaLabel || "Edit"} className={className}
      fill="none" xmlns="http://www.w3.org/2000/svg" stroke={stroke} strokeWidth={strokeWidth} strokeLinecap="round" strokeLinejoin="round">
      <path d="M3 21l3.5-.5L19 8.5 15.5 5 3.5 18.5 3 21z"/>
      <path d="M14.5 6.5l3 3"/>
    </svg>
  );
} 