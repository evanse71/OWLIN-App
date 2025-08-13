import React from 'react';

interface BatchProgress {
  filesTotal: number;
  filesDone: number;
  pagesProcessed: number;
  pagesTotal: number;
}

interface BatchPillProps {
  progress?: BatchProgress;
  isReady?: boolean;
}

export default function BatchPill({ progress, isReady = false }: BatchPillProps) {
  if (isReady) {
    return (
      <div className="chip chip-success">
        <span>✓</span>
        Ready to review
      </div>
    );
  }

  if (!progress) {
    return null;
  }

  const { filesTotal, filesDone, pagesProcessed, pagesTotal } = progress;
  
  if (filesDone === filesTotal && pagesProcessed === pagesTotal) {
    return (
      <div className="chip chip-success">
        <span>✓</span>
        Ready to review
      </div>
    );
  }

  return (
    <div className="chip">
      <div className="progress-spin" />
      Scanning {filesDone} of {filesTotal} • {pagesProcessed} pages
    </div>
  );
}; 