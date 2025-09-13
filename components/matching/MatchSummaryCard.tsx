import React from 'react';
import type { MatchSummary } from '@/types/matching';

type Props = { summary: MatchSummary };

const MatchSummaryCard: React.FC<Props> = ({ summary }) => (
  <div className="rounded-lg border p-3">
    <div className="font-medium">Matching summary</div>
    <div className="text-sm text-neutral-600">
      {summary.totalPairs} pairs · {summary.unmatchedLeft} unmatched left · {summary.unmatchedRight} unmatched right
      {summary.averageScore != null && <> · avg score {summary.averageScore.toFixed(2)}</>}
    </div>
  </div>
);

export default MatchSummaryCard; 