import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
import AppShell from '@/components/layout/AppShell';

interface EnvHealth { [k: string]: any }
interface ReportDoc { doc_id: string; file: string; total_percent: number; stages: { stage: string; ok: boolean; duration_ms: number; meta: any }[]; error?: string }
interface Scenario { avg_total_percent: number; docs: ReportDoc[] }
interface Report { run_id: string; env: EnvHealth; scenarios: { [k: string]: Scenario }; aggregate: { overall_total_percent: number } }

export default function OCRDiagnosticsPage() {
  const router = useRouter();
  const { docId } = router.query as { docId?: string };

  const [env, setEnv] = useState<EnvHealth | null>(null);
  const [report, setReport] = useState<Report | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchHealth = async () => {
    try {
      const res = await fetch('/api/ocr/diagnostics/health', { cache: 'no-store' });
      const json = await res.json();
      setEnv(json.env || {});
    } catch (e: any) {
      setError(String(e?.message || e));
    }
  };

  const run = async () => {
    setLoading(true); setError(null);
    try {
      const res = await fetch('/api/ocr/diagnostics/run', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({}) });
      const json = await res.json();
      setReport(json);
      if (!env) setEnv(json.env || {});
    } catch (e: any) {
      setError(String(e?.message || e));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchHealth();
  }, []);

  useEffect(() => {
    if (!report || !docId) return;
    requestAnimationFrame(() => {
      const el = document.querySelector(`[data-doc-id="${docId}"]`) as HTMLElement | null;
      if (el) {
        el.scrollIntoView({ behavior: 'smooth', block: 'center' });
        el.classList.add('ring-2','ring-yellow-400');
        setTimeout(() => el.classList.remove('ring-2','ring-yellow-400'), 2000);
      }
    });
  }, [report, docId]);

  const rag = (n: number) => n >= 80 ? 'text-green-700' : n >= 50 ? 'text-yellow-700' : 'text-red-700';

  return (
    <AppShell>
      <div className="max-w-6xl mx-auto py-6">
        <div className="flex items-center justify-between mb-4">
          <h1 className="text-2xl font-semibold text-owlin-text">OCR Diagnostics</h1>
          <div className="flex items-center gap-2">
            <button onClick={fetchHealth} className="px-3 py-2 border border-owlin-stroke rounded-owlin">Check Env</button>
            <button onClick={run} disabled={loading} className="px-3 py-2 bg-[var(--owlin-sapphire)] text-white rounded-owlin hover:brightness-110 disabled:opacity-50">{loading ? 'Running…' : 'Run OCR Self‑Check'}</button>
          </div>
        </div>

        {error && <div className="mb-4 p-3 rounded-owlin border border-red-300 text-red-700">{error}</div>}

        {env && (
          <div className="bg-owlin-card border border-owlin-stroke rounded-owlin p-4 mb-4">
            <h2 className="text-sm font-semibold mb-2">Environment</h2>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-2 text-sm">
              {Object.entries(env).map(([k,v]) => (
                <div key={k} className="flex items-center justify-between"><span className="text-owlin-muted">{k}</span><span className="text-owlin-text">{String(v)}</span></div>
              ))}
            </div>
          </div>
        )}

        {report && (
          <div>
            <div className="bg-owlin-card border border-owlin-stroke rounded-owlin p-4 mb-4">
              <div className="text-sm text-owlin-muted">Overall</div>
              <div className={`text-3xl font-semibold ${rag(report.aggregate?.overall_total_percent || 0)}`}>{report.aggregate?.overall_total_percent ?? 0}%</div>
              <div className="text-xs text-owlin-muted">Run ID: {report.run_id}</div>
            </div>

            <div className="space-y-4">
              {Object.entries(report.scenarios || {}).map(([name, sc]) => (
                <div key={name} className="bg-owlin-card border border-owlin-stroke rounded-owlin p-4">
                  <div className="flex items-center justify-between mb-2">
                    <div className="font-semibold">{name}</div>
                    <div className={`text-lg font-semibold ${rag(sc.avg_total_percent)}`}>{sc.avg_total_percent}%</div>
                  </div>
                  <div className="overflow-x-auto">
                    <table className="min-w-full text-sm">
                      <thead className="sticky top-0 bg-owlin-card border-b border-owlin-stroke">
                        <tr>
                          <th className="text-left py-2 pr-4">File</th>
                          <th className="text-left py-2 pr-4">Total</th>
                          <th className="text-left py-2 pr-4">Stages</th>
                          <th className="text-left py-2 pr-4">Error</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-owlin-stroke">
                        {sc.docs.map((d, i) => (
                          <tr key={i} data-doc-id={d.doc_id}>
                            <td className="py-2 pr-4 text-owlin-text">{d.file}</td>
                            <td className={`py-2 pr-4 ${rag(d.total_percent)}`}>{d.total_percent}%</td>
                            <td className="py-2 pr-4">
                              <div className="flex flex-wrap gap-1">
                                {d.stages.map((s, si) => (
                                  <span key={si} className={`px-2 py-0.5 rounded-owlin border ${s.ok ? 'border-owlin-stroke' : 'border-red-300 text-red-700'}`}>{s.stage}:{' '}{s.meta && (s.meta.text_len||s.meta.items_count||s.meta.confidence||s.meta.doc_type||s.meta.currency_found||'ok')}</span>
                                ))}
                              </div>
                            </td>
                            <td className="py-2 pr-4 text-red-700 text-xs">{d.error || ''}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </AppShell>
  );
} 