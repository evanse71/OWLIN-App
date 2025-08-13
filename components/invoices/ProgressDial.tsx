import React, { useEffect, useMemo, useState } from "react";

type Props = {
  progress?: { processed_pages?: number; total_pages?: number } | null;
  status?: "idle" | "processing" | "processed" | "error";
  size?: number; // px
};

export default function ProgressDial({ progress, status = "idle", size = 28 }: Props) {
  const [justCompleted, setJustCompleted] = useState(false);
  const total = progress?.total_pages ?? 0;
  const done = progress?.processed_pages ?? 0;

  const pct = useMemo(() => {
    if (!total || total <= 0) return 0;
    const val = Math.max(0, Math.min(1, done / total));
    return val;
  }, [done, total]);

  const showDeterminate = status === "processing" && total > 0;
  const showIndeterminate = status === "processing" && total <= 0;
  const completed = status === "processed" || (showDeterminate && pct >= 1);

  useEffect(() => {
    if (completed) {
      setJustCompleted(true);
      const t = setTimeout(() => setJustCompleted(false), 220);
      return () => clearTimeout(t);
    }
  }, [completed]);

  const stroke = 3;
  const r = (size - stroke) / 2;
  const c = 2 * Math.PI * r;
  const dash = showDeterminate ? c : 0;
  const offset = showDeterminate ? c * (1 - pct) : 0;

  return (
    <div
      aria-label="Processing progress"
      className="relative"
      style={{ width: size, height: size }}
    >
      {/* Track */}
      <svg width={size} height={size} className="rotate-[-90deg]">
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="rgba(3,8,18,0.08)" strokeWidth={stroke} />
        {/* Determinate arc */}
        {showDeterminate && (
          <circle
            cx={size / 2} cy={size / 2} r={r} fill="none"
            stroke="var(--owlin-sapphire)" strokeWidth={stroke}
            strokeLinecap="round"
            strokeDasharray={dash} strokeDashoffset={offset}
            style={{ transition: "stroke-dashoffset var(--dur-fast) var(--ease-out)" }}
          />
        )}
      </svg>

      {/* Indeterminate spinner */}
      {showIndeterminate && (
        <div className="absolute inset-0 rounded-full border-2 border-[rgba(3,8,18,0.08)] border-t-[var(--owlin-sapphire)] animate-spin" style={{ animationDuration: "1.2s" }} />
      )}

      {/* Check overlay when completed */}
      {completed && (
        <div className="absolute inset-0 grid place-items-center">
          <div className="grid place-items-center bg-[var(--owlin-sapphire)] text-white rounded-full"
               style={{ width: size - 6, height: size - 6, transform: justCompleted ? "scale(1)" : "scale(0.95)", transition: "transform 180ms var(--ease-out)" }}>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M20 6L9 17l-5-5"></path>
            </svg>
          </div>
        </div>
      )}
    </div>
  );
} 