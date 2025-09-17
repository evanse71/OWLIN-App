"use client";
import React from "react";
import { Check, TrendingUp, AlertCircle, X } from "lucide-react";

interface ConfidenceBadgeProps {
  score: number; // 0-1
  size?: "xs" | "sm" | "md" | "lg";
  showIcon?: boolean;
  className?: string;
}

export const ConfidenceBadge: React.FC<ConfidenceBadgeProps> = ({
  score,
  size = "sm",
  showIcon = true,
  className = ""
}) => {
  const percentage = Math.round(score * 100);
  
  const getTone = (score: number) => {
    if (score >= 0.9) return "success";
    if (score >= 0.7) return "warning";
    if (score >= 0.5) return "info";
    return "error";
  };
  
  const getIcon = (score: number) => {
    if (score >= 0.9) return <Check className="h-3 w-3" />;
    if (score >= 0.7) return <TrendingUp className="h-3 w-3" />;
    if (score >= 0.5) return <AlertCircle className="h-3 w-3" />;
    return <X className="h-3 w-3" />;
  };
  
  const getLabel = (score: number) => {
    if (score >= 0.9) return "High";
    if (score >= 0.7) return "Medium";
    if (score >= 0.5) return "Low";
    return "Very Low";
  };
  
  const tone = getTone(score);
  const icon = getIcon(score);
  const label = getLabel(score);
  
  const sizeClasses = {
    xs: "px-1.5 py-0.5 text-xs",
    sm: "px-2 py-0.5 text-xs",
    md: "px-3 py-1 text-sm",
    lg: "px-4 py-1.5 text-base"
  };
  
  const toneClasses = {
    success: "bg-emerald-50 text-emerald-700 border-emerald-200",
    warning: "bg-amber-50 text-amber-700 border-amber-200",
    info: "bg-blue-50 text-blue-700 border-blue-200",
    error: "bg-rose-50 text-rose-700 border-rose-200"
  };
  
  return (
    <span className={`inline-flex items-center gap-1 rounded-full border font-medium ${sizeClasses[size]} ${toneClasses[tone]} ${className}`}>
      {showIcon && icon}
      <span className="hidden sm:inline">{label}</span>
      <span className="sm:hidden">{percentage}%</span>
    </span>
  );
};

export default ConfidenceBadge;
