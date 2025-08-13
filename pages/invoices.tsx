import React, { useState, useEffect, useCallback } from 'react';
import AppShell from '@/components/layout/AppShell';
import UploadHero from '@/components/invoices/UploadHero';
import CardsRail from '@/components/invoices/CardsRail';
import InvoiceCard from '@/components/invoices/InvoiceCard';
import StickyFooter from '@/components/invoices/StickyFooter';
import ConfirmSubmitDrawer from '@/components/invoices/ConfirmSubmitDrawer';
import BatchPill from '@/components/invoices/BatchPill';
import enhancedAPIService from '@/services/enhanced_api_service';
import { emit } from '@/lib/events';
import { toCents } from '@/lib/money';

interface Invoice {
  id: string;
  supplier_name: string;
  invoice_number: string;
  invoice_date: string;
  total_amount: number;
  doc_type: "invoice" | "delivery_note" | "receipt" | "utility" | "other";
  page_range: string;
  line_items: any[];
  addresses: { supplier_address?: string; delivery_address?: string };
  signature_regions: any[];
  field_confidence: Record<string, number>;
  status: "processing" | "processed" | "reviewed";
  progress?: { processed_pages: number; total_pages: number };
  flags?: { total_mismatch?: boolean; [key: string]: any };
  _localFile?: File;
  _appearIndex?: number;
}

interface BatchProgress {
  filesTotal: number;
  filesDone: number;
  pagesProcessed: number;
  pagesTotal: number;
}

const InvoicesPage: React.FC = () => {
  const [docs, setDocs] = useState<Invoice[]>([]);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [batchProgress, setBatchProgress] = useState<BatchProgress | null>(null);
  const [showConfirmDrawer, setShowConfirmDrawer] = useState(false);
  const [unseenChanges, setUnseenChanges] = useState(false);
  const [toolbar, setToolbar] = useState({
    filter: 'all',
    search: '',
    sort: 'date'
  });

  // Cross-fade helpers
  const fadeOut = useCallback((el: HTMLElement) => {
    if (!el) return;
    el.style.transition = "opacity 120ms ease-out";
    el.style.opacity = "0";
  }, []);

  const fadeIn = useCallback((el: HTMLElement, i = 0) => {
    if (!el) return;
    el.style.opacity = "0";
    el.style.transition = `opacity 120ms ease-out ${i * 60}ms`;
    requestAnimationFrame(() => {
      el.style.opacity = "1";
    });
  }, []);

  // Create placeholder for a file
  const createPlaceholder = (file: File, index: number): Invoice => ({
    id: `local-${Date.now()}-${index}`,
    supplier_name: "",
    invoice_number: "",
    invoice_date: "",
    total_amount: 0,
    doc_type: "invoice",
    page_range: "",
    line_items: [],
    addresses: {},
    signature_regions: [],
    field_confidence: {},
    status: "processing",
    _localFile: file
  });

  // Stage-based progress approximation
  const STAGE_WEIGHTS = { preprocess: 0.1, ocr: 0.6, parse: 0.2, save: 0.1 }; // totals to 1.0

  // Handle file uploads
  const handleFiles = useCallback(async (files: File[]) => {
    // Create placeholders immediately
    const placeholders = files.map((file, i) => createPlaceholder(file, i));
    setDocs(prev => [...prev, ...placeholders]);

    // Add placeholder glow effect
    placeholders.forEach((placeholder, i) => {
      setTimeout(() => {
        const element = document.getElementById(`card-${placeholder.id}`);
        if (element) {
          element.classList.add('placeholder-glow');
          setTimeout(() => {
            element.classList.remove('placeholder-glow');
            element.classList.add('fade');
          }, 2000);
        }
      }, i * 100);
    });

    // Initialize batch progress
    setBatchProgress({
      filesTotal: files.length,
      filesDone: 0,
      pagesProcessed: 0,
      pagesTotal: 0
    });

    // Real upload loop
    for (let i = 0; i < files.length; i++) {
      const file = files[i];
      const placeholder = placeholders[i];

      try {
        const result = await enhancedAPIService.uploadDocument(file, (p) => {
          // Update progress on the placeholder
          setDocs(prev => prev.map(doc =>
            doc.id === placeholder.id
              ? {
                  ...doc,
                  status: p.stage === 'complete' ? 'processed' : 'processing',
                  progress: { processed_pages: Math.round(p.progress), total_pages: 100 }
                }
              : doc
          ));
        });

        // Transform API result to Invoice shape
        const invoice: Invoice = {
          id: (result as any).invoice_id || `processed-${Date.now()}-${i}`,
          supplier_name: (result as any).data?.supplier_name || '',
          invoice_number: (result as any).data?.invoice_number || '',
          invoice_date: (result as any).data?.invoice_date || '',
          total_amount: (result as any).data?.total_amount ?? 0,
          doc_type: ((result as any).document_type || 'invoice') as Invoice['doc_type'],
          page_range: '',
          line_items: ((result as any).line_items || []).map((li: any, idx: number) => ({
            description: li.description ?? li.item_description ?? '',
            quantity: li.quantity ?? li.qty ?? null,
            unit: li.unit ?? undefined,
            unit_price: li.unit_price ?? li.price ?? null,
            vat_percent: li.vat_percent ?? li.vat ?? null,
            line_total: li.line_total ?? li.total_price ?? null,
            page: li.page ?? null,
            row_idx: li.row ?? li.row_idx ?? idx,
            confidence: li.confidence ?? null,
            description_confidence: li.description_confidence,
            quantity_confidence: li.quantity_confidence,
            unit_price_confidence: li.unit_price_confidence,
            vat_confidence: li.vat_confidence,
            line_total_confidence: li.line_total_confidence,
          })),
          addresses: (result as any).addresses || {},
          signature_regions: (result as any).signature_regions || [],
          field_confidence: (result as any).field_confidence || {},
          status: 'processed',
          progress: { processed_pages: 100, total_pages: 100 },
          _appearIndex: i
        };

        // Cross-fade: replace placeholder with real invoice
        const placeholderElement = document.getElementById(`card-${placeholder.id}`);
        if (placeholderElement) {
          fadeOut(placeholderElement);
          setTimeout(() => {
            setDocs(prev => {
              const withoutPlaceholder = prev.filter(d => d.id !== placeholder.id);
              return [...withoutPlaceholder, invoice];
            });
            setTimeout(() => {
              const el = document.getElementById(`card-${invoice.id}`);
              if (el) fadeIn(el, 0);
            }, 50);
          }, 120);
        } else {
          // Fallback replace without animation
          setDocs(prev => prev.map(d => d.id === placeholder.id ? invoice : d));
        }

        // Update batch progress
        setBatchProgress(prev => prev ? {
          ...prev,
          filesDone: prev.filesDone + 1
        } : null);

      } catch (error) {
        console.error('Upload failed:', error);
        // Mark placeholder as failed
        setDocs(prev => prev.map(doc =>
          doc.id === placeholder.id ? { ...doc, status: 'processed', field_confidence: {}, line_items: [], progress: undefined } : doc
        ));
        setBatchProgress(prev => prev ? { ...prev, filesDone: prev.filesDone + 1 } : null);
      }
    }
  }, [fadeOut, fadeIn]);

  const handleManualInvoice = useCallback(() => {
    // Implement manual invoice creation
    console.log('Manual invoice creation');
  }, []);

  const handleToggleCard = useCallback((id: string) => {
    setActiveId(prev => prev === id ? null : id);
  }, []);

  const handleEditLineItem = useCallback((docId: string, rowIdx: number, patch: Partial<any>) => {
    setDocs(prev => prev.map(doc => {
      if (doc.id === docId) {
        const updatedLineItems = [...doc.line_items];
        updatedLineItems[rowIdx] = { ...updatedLineItems[rowIdx], ...patch };
        return { ...doc, line_items: updatedLineItems };
      }
      return doc;
    }));
    setUnseenChanges(true);
  }, []);

  const handleClearAll = useCallback(() => {
    setDocs([]);
    setActiveId(null);
    setBatchProgress(null);
    setUnseenChanges(false);
  }, []);

  const handleSubmit = useCallback(() => {
    setShowConfirmDrawer(true);
  }, []);

  const handleConfirmSubmit = useCallback(() => {
    // Implement actual submission logic
    console.log('Submitting invoices:', docs.filter(d => d.status === "processed"));
    setShowConfirmDrawer(false);
    setUnseenChanges(false);
    const processed = docs.filter(d => d.status === 'processed');
    const totalCents = processed.reduce((acc, d) => acc + toCents(d.total_amount || 0), 0);
    emit({ type: 'INVOICES_SUBMITTED', payload: { count: processed.length, total_cents: totalCents, at: new Date().toISOString() } });
  }, [docs]);

  const handleKeyDown = useCallback((e: KeyboardEvent) => {
    if (e.key === 'j' || e.key === 'k') {
      e.preventDefault();
      const processedDocs = docs.filter(d => d.status === "processed");
      if (processedDocs.length === 0) return;

      const currentIndex = activeId ? processedDocs.findIndex(d => d.id === activeId) : -1;
      let newIndex;

      if (e.key === 'j') {
        newIndex = currentIndex < processedDocs.length - 1 ? currentIndex + 1 : 0;
      } else {
        newIndex = currentIndex > 0 ? currentIndex - 1 : processedDocs.length - 1;
      }

      const newActiveId = processedDocs[newIndex].id;
      setActiveId(newActiveId);

      // Scroll into view
      const element = document.getElementById(`card-${newActiveId}`);
      if (element) {
        element.scrollIntoView({ behavior: 'smooth', block: 'center' });
      }
    } else if (e.key === 'r') {
      e.preventDefault();
      // Toggle review only mode - could be implemented as a filter
      console.log('Toggle review only mode');
    }
  }, [docs, activeId]);

  useEffect(() => {
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [handleKeyDown]);

  useEffect(() => {
    // Load any existing invoices from backend (will be empty on first boot)
    (async () => {
      try {
        const existing = await enhancedAPIService.getInvoices();
        if (Array.isArray(existing) && existing.length > 0) {
          const mapped: Invoice[] = existing.map((inv: any, i: number) => ({
            id: inv.id || inv.invoice_id || `inv-${i}`,
            supplier_name: inv.supplier_name || '',
            invoice_number: inv.invoice_number || '',
            invoice_date: inv.invoice_date || '',
            total_amount: inv.total_amount ?? inv.total_incl_vat ?? 0,
            doc_type: 'invoice',
            page_range: '',
            line_items: (inv.line_items || []).map((li: any, idx: number) => ({
              description: li.description ?? li.item_description ?? '',
              quantity: li.quantity ?? null,
              unit: li.unit ?? undefined,
              unit_price: li.unit_price ?? null,
              vat_percent: li.vat_percent ?? null,
              line_total: li.line_total ?? li.total_price ?? null,
              row_idx: li.row_idx ?? idx,
              page: li.page ?? null,
              confidence: li.confidence ?? null,
            })),
            addresses: inv.addresses || {},
            signature_regions: inv.signature_regions || [],
            field_confidence: inv.field_confidence || {},
            status: 'processed',
          }));
          setDocs(mapped);
        }
      } catch (e) {
        // Ignore; initial state will be empty
      }
    })();
  }, []);

  const filteredDocs = docs.filter(doc => {
    if (toolbar.filter !== 'all') {
      if (toolbar.filter === 'needs_review' && doc.status !== "reviewed") return true;
      if (toolbar.filter === 'invoices' && doc.doc_type === "invoice") return true;
      if (toolbar.filter === 'delivery_notes' && doc.doc_type === "delivery_note") return true;
      if (toolbar.filter === 'receipts' && doc.doc_type === "receipt") return true;
      if (toolbar.filter === 'utilities' && doc.doc_type === "utility") return true;
    }
    return true;
  });

  const isReady = batchProgress && 
    batchProgress.filesDone === batchProgress.filesTotal && 
    batchProgress.pagesProcessed === batchProgress.pagesTotal;

  return (
    <AppShell>
      <div className="bg-owlin-bg">
        {/* Sticky sub-toolbar */}
        <section className="sticky top-[64px] z-30 bg-[color-mix(in_oklab,var(--owlin-card)_92%,transparent)] backdrop-blur border-b border-[var(--owlin-stroke)]">
          <div className="mx-auto w-full max-w-6xl px-4 lg:px-6 py-3">
            <div className="flex items-center justify-between">
              {/* Filter chips */}
              <div className="flex items-center gap-1">
                {[
                  { key: 'all', label: 'All' },
                  { key: 'needs_review', label: 'Needs review' },
                  { key: 'invoices', label: 'Invoices' },
                  { key: 'delivery_notes', label: 'Delivery notes' },
                  { key: 'receipts', label: 'Receipts' },
                  { key: 'utilities', label: 'Utilities' }
                ].map(filter => (
                  <button
                    key={filter.key}
                    onClick={() => setToolbar(prev => ({ ...prev, filter: filter.key }))}
                    className={`px-3 py-1.5 rounded-[12px] text-[13px] transition-colors ${
                      toolbar.filter === filter.key
                        ? 'bg-[var(--owlin-bg)] text-[var(--owlin-text)]'
                        : 'text-[var(--owlin-muted)] hover:bg-[var(--owlin-bg)]'
                    }`}
                  >
                    {filter.label}
                  </button>
                ))}
              </div>

              {/* Search and sort */}
              <div className="flex items-center gap-3">
                <input
                  type="text"
                  placeholder="Search invoices..."
                  value={toolbar.search}
                  onChange={(e) => setToolbar(prev => ({ ...prev, search: e.target.value }))}
                  className="w-56 px-3 py-1.5 rounded-[12px] border border-[var(--owlin-stroke)] text-[13px] focus:outline-none focus:ring-2 focus:ring-[var(--owlin-sapphire)]"
                />
                <select
                  value={toolbar.sort}
                  onChange={(e) => setToolbar(prev => ({ ...prev, sort: e.target.value }))}
                  className="px-3 py-1.5 rounded-[12px] border border-[var(--owlin-stroke)] text-[13px] focus:outline-none focus:ring-2 focus:ring-[var(--owlin-sapphire)]"
                >
                  <option value="date">Date</option>
                  <option value="supplier">Supplier</option>
                  <option value="amount">Amount</option>
                </select>
              </div>

              {/* Batch pill */}
              <BatchPill progress={batchProgress || undefined} isReady={isReady || false} />
            </div>
          </div>
        </section>

        <main className="w-full">
          {/* UploadHero */}
          <UploadHero onFiles={handleFiles} onManualInvoice={handleManualInvoice} />

          {/* Cards rail */}
          <CardsRail>
            {filteredDocs.map((doc) => (
              <InvoiceCard
                key={doc.id}
                doc={doc}
                isActive={activeId === doc.id}
                onToggle={() => handleToggleCard(doc.id)}
                onEditLineItem={(rowIdx, patch) => handleEditLineItem(doc.id, rowIdx, patch)}
              />
            ))}
          </CardsRail>
        </main>

        <StickyFooter
          docs={docs}
          unseenChanges={unseenChanges}
          onClearAll={handleClearAll}
          onSubmit={handleSubmit}
        />
        
        <ConfirmSubmitDrawer
          open={showConfirmDrawer}
          onClose={() => setShowConfirmDrawer(false)}
          docs={docs}
          onSubmit={handleConfirmSubmit}
        />
      </div>
    </AppShell>
  );
};

export default InvoicesPage; 