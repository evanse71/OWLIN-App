export type MatchScore = number;

export interface DocumentMeta {
  id: string;
  filename: string;
  supplier?: string | null;
  date?: string | null;
}

export interface DocumentPairData {
  left: DocumentMeta;
  right: DocumentMeta;
  score?: MatchScore;
}

export interface MatchSummary {
  totalPairs: number;
  unmatchedLeft: number;
  unmatchedRight: number;
  averageScore?: MatchScore;
} 