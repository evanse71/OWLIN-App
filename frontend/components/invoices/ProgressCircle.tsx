"use client";
import React from "react";

interface ProgressCircleProps {
  progress: number; // 0-1
  size?: "sm" | "md" | "lg";
  strokeWidth?: number;
  showPercentage?: boolean;
  className?: string;
}

export const ProgressCircle: React.FC<ProgressCircleProps> = ({
  progress,
  size = "md",
  strokeWidth,
  showPercentage = true,
  className = ""
}) => {
  const sizeClasses = {
    sm: "h-8 w-8",
    md: "h-12 w-12",
    lg: "h-16 w-16"
  };
  
  const defaultStrokeWidth = {
    sm: 2,
    md: 3,
    lg: 4
  };
  
  const actualStrokeWidth = strokeWidth ?? defaultStrokeWidth[size];
  const radius = (size === "sm" ? 16 : size === "md" ? 24 : 32) - actualStrokeWidth;
  const circumference = 2 * Math.PI * radius;
  const strokeDasharray = circumference;
  const strokeDashoffset = circumference - (progress * circumference);
  
  const percentage = Math.round(progress * 100);
  
  return (
    <div className={`relative ${sizeClasses[size]} ${className}`}>
      <svg
        className="h-full w-full -rotate-90 transform"
        viewBox={`0 0 ${(size === "sm" ? 32 : size === "md" ? 48 : 64)} ${(size === "sm" ? 32 : size === "md" ? 48 : 64)}`}
      >
        {/* Background circle */}
        <circle
          cx={(size === "sm" ? 16 : size === "md" ? 24 : 32)}
          cy={(size === "sm" ? 16 : size === "md" ? 24 : 32)}
          r={radius}
          stroke="currentColor"
          strokeWidth={actualStrokeWidth}
          fill="none"
          className="text-slate-200"
        />
        
        {/* Progress circle */}
        <circle
          cx={(size === "sm" ? 16 : size === "md" ? 24 : 32)}
          cy={(size === "sm" ? 16 : size === "md" ? 24 : 32)}
          r={radius}
          stroke="currentColor"
          strokeWidth={actualStrokeWidth}
          fill="none"
          strokeDasharray={strokeDasharray}
          strokeDashoffset={strokeDashoffset}
          strokeLinecap="round"
          className={`transition-all duration-300 ${
            progress >= 0.9 ? "text-emerald-500" :
            progress >= 0.7 ? "text-amber-500" :
            progress >= 0.5 ? "text-blue-500" :
            "text-rose-500"
          }`}
        />
      </svg>
      
      {/* Percentage text */}
      {showPercentage && (
        <div className="absolute inset-0 flex items-center justify-center">
          <span className={`font-semibold ${
            size === "sm" ? "text-xs" :
            size === "md" ? "text-sm" :
            "text-base"
          } text-slate-700`}>
            {percentage}%
          </span>
        </div>
      )}
    </div>
  );
};

export default ProgressCircle;
