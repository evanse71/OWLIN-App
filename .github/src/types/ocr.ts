// src/types/ocr.ts
export type OcrBlock = {
  type: string;
  bbox: number[];            // [x, y, w, h]
  ocr_text: string;
  confidence: number;        // 0..1
  table_data: string[][] | null;
};

export type OcrPage = {
  page_num: number;
  confidence: number;        // 0..1
  preprocessed_image_path: string;
  blocks: OcrBlock[];
};

export type OcrV2Response = {
  status: 'ok' | 'partial' | 'error' | 'disabled';
  message?: string;
  pages?: OcrPage[];
  overall_confidence?: number; // 0..1
  artifact_dir?: string;
  elapsed_sec?: number;
  trace_id?: string;
  feature?: 'v2';
  error?: string;
};
