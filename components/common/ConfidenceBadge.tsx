import React from 'react';
import { motion } from 'framer-motion';

interface ConfidenceBadgeProps {
  confidence: number;
}

const ConfidenceBadge: React.FC<ConfidenceBadgeProps> = ({ confidence }) => {
  const getConfidenceLevel = () => {
    if (confidence >= 90) return 'high';
    if (confidence >= 70) return 'medium';
    return 'low';
  };

  const confidenceLevel = getConfidenceLevel();
  const colorMap: Record<string, string> = {
    high: 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/30 dark:text-emerald-200',
    medium: 'bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-200',
    low: 'bg-rose-100 text-rose-800 dark:bg-rose-900/30 dark:text-rose-200',
  };

  const labelMap: Record<string, string> = {
    high: 'High',
    medium: 'Medium',
    low: 'Low – click to review',
  };

  return (
    <motion.div
      className={`inline-block rounded-full px-2 py-0.5 text-xs font-medium ${colorMap[confidenceLevel]}`}
      initial={{ opacity: 0, y: 3 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      title={`OCR confidence: ${confidence}% — ${labelMap[confidenceLevel]}`}
    >
      OCR {confidence}%
    </motion.div>
  );
};

export default ConfidenceBadge; 