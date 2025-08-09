import React, { useEffect, useState } from 'react';

interface ProgressCircleProps {
  size?: number;
  strokeWidth?: number;
  duration?: number;
  color?: string;
  onComplete?: () => void;
}

const ProgressCircle: React.FC<ProgressCircleProps> = ({
  size = 36,
  strokeWidth = 4,
  duration = 8000,
  color = '#3B82F6', // blue-500
  onComplete
}) => {
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;

  const [progress, setProgress] = useState(0);

  useEffect(() => {
    const start = Date.now();
    const tick = () => {
      const elapsed = Date.now() - start;
      const newProgress = Math.min(elapsed / duration, 1);
      setProgress(newProgress);
      if (newProgress < 1) {
        requestAnimationFrame(tick);
      } else if (onComplete) {
        onComplete();
      }
    };
    tick();
  }, [duration, onComplete]);

  const strokeDashoffset = circumference * (1 - progress);

  return (
    <svg width={size} height={size}>
      <circle
        stroke="#e5e7eb" // Tailwind slate-200
        fill="transparent"
        strokeWidth={strokeWidth}
        r={radius}
        cx={size / 2}
        cy={size / 2}
      />
      <circle
        stroke={color}
        fill="transparent"
        strokeWidth={strokeWidth}
        strokeLinecap="round"
        strokeDasharray={circumference}
        strokeDashoffset={strokeDashoffset}
        r={radius}
        cx={size / 2}
        cy={size / 2}
        style={{ transition: 'stroke-dashoffset 0.1s linear' }}
      />
    </svg>
  );
};

export default ProgressCircle; 