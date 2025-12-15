// src/lib/api/ocrV2.ts
import type { OcrV2Response } from '@/types/ocr';

export async function postOcrV2(apiBaseUrl: string, file: File, signal?: AbortSignal): Promise<OcrV2Response> {
  const form = new FormData();
  form.append('file', file, file.name);
  const res = await fetch(`${apiBaseUrl}/api/ocr/run`, {
    method: 'POST',
    body: form,
    signal,
  });
  let json: any = null;
  try {
    json = await res.json();
  } catch (e) {
    throw new Error(`Non-JSON response (${res.status}): ${await res.text()}`);
  }
  if (!res.ok) {
    const detail = json?.detail ?? json?.error ?? JSON.stringify(json);
    throw new Error(`HTTP ${res.status}: ${detail}`);
  }
  return json as OcrV2Response;
}
