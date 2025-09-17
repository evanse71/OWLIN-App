"use client";
import React from "react";
import { Check, X, AlertCircle, TrendingUp } from "lucide-react";

interface SuggestionData {
  title: string;
  subtitle: string;
  meta: string;
}

interface DocumentPairingSuggestionCardProps {
  left: SuggestionData;
  right: SuggestionData;
  score: number;
  reason?: string;
  onConfirm: () => void;
  onReject: () => void;
  loading?: boolean;
}

function ConfidenceBadge({ score, size = "sm" }: { score: number; size?: "sm" | "md" | "lg" }) {
  const percentage = Math.round(score * 100);
  
  const getTone = (score: number) => {
    if (score >= 0.9) return "success";
    if (score >= 0.7) return "warning";
    return "error";
  };
  
  const getIcon = (score: number) => {
    if (score >= 0.9) return <Check className="h-3 w-3" />;
    if (score >= 0.7) return <TrendingUp className="h-3 w-3" />;
    return <AlertCircle className="h-3 w-3" />;
  };
  
  const tone = getTone(score);
  const icon = getIcon(score);
  
  const sizeClasses = {
    sm: "px-2 py-0.5 text-xs",
    md: "px-3 py-1 text-sm",
    lg: "px-4 py-1.5 text-base"
  };
  
  const toneClasses = {
    success: "bg-emerald-50 text-emerald-700 border-emerald-200",
    warning: "bg-amber-50 text-amber-700 border-amber-200",
    error: "bg-rose-50 text-rose-700 border-rose-200"
  };
  
  return (
    <span className={`inline-flex items-center gap-1 rounded-full border font-medium ${sizeClasses[size]} ${toneClasses[tone]}`}>
      {icon}
      {percentage}%
    </span>
  );
}

export const DocumentPairingSuggestionCard: React.FC<DocumentPairingSuggestionCardProps> = ({
  left,
  right,
  score,
  reason,
  onConfirm,
  onReject,
  loading = false
}) => {
  const confidence = score >= 0.8 ? "high" : score >= 0.6 ? "medium" : "low";
  
  return (
    <div className="rounded-2xl border border-blue-200 bg-gradient-to-r from-blue-50 to-indigo-50 p-4 shadow-sm">
      {/* Header with confidence badge */}
      <div className="mb-3 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="h-2 w-2 rounded-full bg-blue-500"></div>
          <span className="text-sm font-medium text-slate-700">AI Suggestion</span>
        </div>
        <ConfidenceBadge score={score} size="sm" />
      </div>
      
      {/* Main content */}
      <div className="space-y-3">
        {/* Left and right items */}
        <div className="flex items-center justify-between">
          <div className="flex-1 min-w-0">
            <div className="text-sm font-semibold text-slate-800 truncate">
              {left.title}
            </div>
            <div className="text-sm text-slate-600 truncate">
              {left.subtitle}
            </div>
            <div className="text-xs text-slate-500 truncate">
              {left.meta}
            </div>
          </div>
          
          {/* Arrow/connector */}
          <div className="mx-4 flex items-center">
            <div className="h-px w-8 bg-slate-300"></div>
            <div className="mx-2 h-2 w-2 rounded-full bg-blue-500"></div>
            <div className="h-px w-8 bg-slate-300"></div>
          </div>
          
          <div className="flex-1 min-w-0 text-right">
            <div className="text-sm font-semibold text-slate-800 truncate">
              {right.title}
            </div>
            <div className="text-sm text-slate-600 truncate">
              {right.subtitle}
            </div>
            <div className="text-xs text-slate-500 truncate">
              {right.meta}
            </div>
          </div>
        </div>
        
        {/* Reason */}
        {reason && (
          <div className="rounded-lg bg-white/60 p-2">
            <div className="text-xs text-slate-600">
              <span className="font-medium">Reason:</span> {reason}
            </div>
          </div>
        )}
        
        {/* Actions */}
        <div className="flex items-center justify-between">
          <div className="text-xs text-slate-500">
            Confidence: {confidence}
          </div>
          
          <div className="flex gap-2">
            <button
              onClick={onReject}
              disabled={loading}
              className="inline-flex items-center gap-1 rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <X className="h-3 w-3" />
              Reject
            </button>
            <button
              onClick={onConfirm}
              disabled={loading}
              className="inline-flex items-center gap-1 rounded-lg bg-blue-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <Check className="h-3 w-3" />
              {loading ? "Confirming..." : "Confirm"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default DocumentPairingSuggestionCard;
