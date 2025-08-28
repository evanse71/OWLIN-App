import React from 'react';
import type { DocumentPairData } from '@types/matching';

type Props = { pair: DocumentPairData; onSelect?: (id: string) => void };

const DocumentPair: React.FC<Props> = ({ pair, onSelect }) => (
  <div className="rounded-md border p-2 flex justify-between items-center">
    <div className="truncate">
      <div className="text-sm">{pair.left.filename} ⇄ {pair.right.filename}</div>
      {pair.score != null && <div className="text-xs text-neutral-500">score {pair.score.toFixed(2)}</div>}
    </div>
    <button className="text-blue-600 text-sm" onClick={() => onSelect?.(pair.left.id)}>Open</button>
  </div>
);

export default DocumentPair; 