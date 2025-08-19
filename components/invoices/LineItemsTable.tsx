import React, { useEffect, useMemo, useRef, useState, useCallback } from 'react';
import { toCents, formatGBP } from '@/lib/money';
import { Virtuoso, VirtuosoHandle } from 'react-virtuoso';

interface LineItem {
	description: string;
	quantity: number;
	unit?: string;
	unit_price?: number;
	vat_percent?: number;
	line_total?: number;
	page?: number;
	row_idx?: number;
	flags?: string[];
	confidence?: number;
	id?: string | number;
}

interface LineItemsTableProps {
	lineItems: LineItem[];
	editable?: boolean;
	onEditLineItem?: (rowIdx: number, patch: Partial<LineItem>) => void;
	reviewOnly?: boolean;
	density?: 'compact' | 'comfort';
	invoiceId?: string; // for scroll/density memory
}

// Persist UI state per invoice across mounts
const SCROLL_MEMORY: Map<string, { scrollTop: number; scrollLeft: number; density: 'compact' | 'comfort'; query: string; filter: 'all' | 'low' | 'flagged'; }> = new Map();

export default function LineItemsTable({
	lineItems,
	editable = false,
	onEditLineItem,
	reviewOnly = false,
	density = 'compact',
	invoiceId
}: LineItemsTableProps) {
	const [query, setQuery] = useState('');
	const [filter, setFilter] = useState<'all' | 'low' | 'flagged'>('all');
	const [savedRow, setSavedRow] = useState<number | null>(null);
	const [densityState, setDensityState] = useState<'compact' | 'comfort'>(density);
	const [liveMessage, setLiveMessage] = useState('');
	const [focused, setFocused] = useState<{ key: string | number; col: string } | null>(null);
	const searchInputRef = useRef<HTMLInputElement | null>(null);
	const virtuosoRef = useRef<VirtuosoHandle | null>(null);
	const scrollBodyRef = useRef<HTMLDivElement | null>(null);
	const headerInnerRef = useRef<HTMLDivElement | null>(null);
	const totalsInnerRef = useRef<HTMLDivElement | null>(null);

	// Restore memory on mount
	useEffect(() => {
		if (!invoiceId) return;
		const mem = SCROLL_MEMORY.get(invoiceId);
		if (mem) {
			setDensityState(mem.density);
			setQuery(mem.query);
			setFilter(mem.filter);
			requestAnimationFrame(() => {
				if (scrollBodyRef.current) {
					scrollBodyRef.current.scrollTop = mem.scrollTop;
					scrollBodyRef.current.scrollLeft = mem.scrollLeft;
				}
			});
		}
	}, [invoiceId]);

	// Save memory on unmount/changes
	useEffect(() => {
		return () => {
			if (invoiceId && scrollBodyRef.current) {
				SCROLL_MEMORY.set(invoiceId, {
					scrollTop: scrollBodyRef.current.scrollTop,
					scrollLeft: scrollBodyRef.current.scrollLeft,
					density: densityState,
					query,
					filter
				});
			}
		};
	}, [invoiceId, densityState, query, filter]);

	// Filtered items (memoize reference for Virtuoso stability)
	const filteredItems = useMemo(() => {
		let items = lineItems;
		if (reviewOnly) items = items.filter(it => (it.flags && it.flags.length > 0));
		if (filter === 'low') items = items.filter(it => (it.confidence ?? 1) < 0.75);
		if (filter === 'flagged') items = items.filter(it => (it.flags && it.flags.length > 0));
		if (query.trim()) {
			const q = query.toLowerCase();
			items = items.filter(it => (it.description || '').toLowerCase().includes(q));
		}
		return items;
	}, [lineItems, reviewOnly, filter, query]);

	// Totals in cents
	const { subtotalCents, vatTotalCents, totalCents } = useMemo(() => {
		const lineTotalsCents = filteredItems.map(item => {
			const base = typeof item.line_total === 'number'
				? toCents(item.line_total)
				: toCents((item.quantity || 0) * (item.unit_price || 0));
			const vatPct = typeof item.vat_percent === 'number' ? item.vat_percent : 0;
			const vatCents = Math.round(base * (vatPct / 100));
			return { base, vatCents };
		});
		const subtotal = lineTotalsCents.reduce((a, v) => a + v.base, 0);
		const vatTotal = lineTotalsCents.reduce((a, v) => a + v.vatCents, 0);
		return { subtotalCents: subtotal, vatTotalCents: vatTotal, totalCents: subtotal + vatTotal };
	}, [filteredItems]);

	// Density styles & grid columns
	const rowPad = densityState === 'compact' ? 'py-1.5 text-[12px]' : 'py-2.5 text-[13px]';
	const numericClass = 'text-right tabular';
	const gridCols = 'grid grid-cols-[minmax(20rem,1fr)_5rem_6rem_7rem_6rem_8rem] gap-2';

	// Keyboard: Cmd/Ctrl+F focuses search; Cmd/Ctrl+J focuses jump
	const jumpRef = useRef<HTMLInputElement | null>(null);
	useEffect(() => {
		const onKey = (e: KeyboardEvent) => {
			const key = e.key.toLowerCase();
			if ((e.ctrlKey || e.metaKey) && key === 'f') {
				e.preventDefault();
				searchInputRef.current?.focus();
			} else if ((e.ctrlKey || e.metaKey) && key === 'j') {
				e.preventDefault();
				jumpRef.current?.focus();
				jumpRef.current?.select?.();
			}
		};
		window.addEventListener('keydown', onKey);
		return () => window.removeEventListener('keydown', onKey);
	}, []);

	// Editing handlers
	const announceSaved = useCallback((rowIndex: number) => {
		setSavedRow(rowIndex);
		setLiveMessage(`Row ${rowIndex + 1} saved`);
		setTimeout(() => setSavedRow(prev => (prev === rowIndex ? null : prev)), 1500);
	}, []);

	const handleCommit = useCallback((rowIndex: number, patch: Partial<LineItem>) => {
		if (!onEditLineItem) return;
		onEditLineItem(rowIndex, patch);
		announceSaved(rowIndex);
	}, [onEditLineItem, announceSaved]);

	const focusMove = useCallback((current: HTMLInputElement, delta: number) => {
		const col = current.getAttribute('data-col');
		const rowStr = current.getAttribute('data-row');
		if (!col || !rowStr) return;
		const nextRow = Number(rowStr) + delta;
		const selector = `input[data-col="${col}"][data-row="${nextRow}"]`;
		const container = scrollBodyRef.current || document;
		const next = container.querySelector(selector) as HTMLInputElement | null;
		if (next) {
			next.focus();
			next.select?.();
		}
	}, []);

	// Manage focus retention key
	const getRowKey = (row: LineItem, index: number) => (row.id ?? index);
	const rememberFocus = useCallback((row: LineItem, index: number, col: string) => {
		setFocused({ key: getRowKey(row, index), col });
	}, []);
	useEffect(() => {
		if (!focused) return;
		const index = filteredItems.findIndex((r, i) => getRowKey(r, i) === focused.key);
		if (index >= 0) {
			// ensure in view
			virtuosoRef.current?.scrollToIndex({ index, align: 'center' });
			setTimeout(() => {
				const selector = `input[data-col="${focused.col}"][data-row="${index}"]`;
				const input = (scrollBodyRef.current || document).querySelector(selector) as HTMLInputElement | null;
				input?.focus();
				input?.select?.();
			}, 50);
		}
	}, [filteredItems, focused]);

	// Row component
	const LineRow = useMemo(() => React.memo(function Row({ row, index }: { row: LineItem; index: number }) {
		const confidence = row.confidence ?? 1;
		const lowConfidence = confidence < 0.75;
		const underline = lowConfidence ? 'border-b border-amber-300/60' : '';
		// Highlight search
		const desc = row.description || '';
		const q = query.trim().toLowerCase();
		let descContent: React.ReactNode = desc;
		if (q && desc.toLowerCase().includes(q)) {
			const start = desc.toLowerCase().indexOf(q);
			const end = start + q.length;
			descContent = (
				<span>
					{desc.slice(0, start)}
					<span className="bg-[color-mix(in_oklab,var(--owlin-sapphire)_12%,transparent)]">{desc.slice(start, end)}</span>
					{desc.slice(end)}
				</span>
			);
		}
		return (
			<div className={`${gridCols} odd:bg-[#FAFBFF] hover:bg-[color-mix(in_oklab,var(--owlin-sapphire)_10%,transparent)] ${rowPad} relative`} role="row" aria-rowindex={index + 1}>
				{/* Description (sticky) */}
				<div className={`px-3 ${underline} sticky left-0 bg-[var(--owlin-card)] z-10 border-r border-owlin-stroke`}>{editable ? (
					<input
						className="w-full px-2 py-1 border border-owlin-stroke rounded-owlin text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-owlin-sapphire"
						defaultValue={row.description || ''}
						data-col="desc"
						data-row={index}
						onFocus={() => rememberFocus(row, index, 'desc')}
						onBlur={(e) => handleCommit(index, { description: e.currentTarget.value })}
						onKeyDown={(e) => { if (e.key === 'Enter') handleCommit(index, { description: (e.target as HTMLInputElement).value }); if (e.key === 'ArrowDown') { e.preventDefault(); focusMove(e.currentTarget, 1); } if (e.key === 'ArrowUp') { e.preventDefault(); focusMove(e.currentTarget, -1); } if (e.key === 'Escape') { (e.currentTarget as HTMLInputElement).blur(); } }}
					/>
				) : descContent}</div>
				{/* Qty */}
				<div className={`px-3 ${numericClass} ${underline}`} style={{ fontVariantNumeric: 'tabular-nums' }}>
					{editable ? (
						<input type="number" className="w-full px-2 py-1 border border-owlin-stroke rounded-owlin text-sm text-right" defaultValue={Number.isFinite(row.quantity) ? String(row.quantity) : ''} data-col="qty" data-row={index} onFocus={() => rememberFocus(row, index, 'qty')} onBlur={(e) => handleCommit(index, { quantity: parseFloat(e.currentTarget.value || '0') })} onKeyDown={(e) => { if (e.key === 'Enter') handleCommit(index, { quantity: parseFloat((e.target as HTMLInputElement).value || '0') }); if (e.key === 'ArrowDown') { e.preventDefault(); focusMove(e.currentTarget, 1); } if (e.key === 'ArrowUp') { e.preventDefault(); focusMove(e.currentTarget, -1); } if (e.key === 'Escape') { (e.currentTarget as HTMLInputElement).blur(); } }} />
					) : (Number.isFinite(row.quantity) ? row.quantity.toFixed(2) : '')}
				</div>
				{/* Unit */}
				<div className={`px-3 ${underline}`}>
					{editable ? (
						<input className="w-full px-2 py-1 border border-owlin-stroke rounded-owlin text-sm" defaultValue={row.unit || ''} data-col="unit" data-row={index} onFocus={() => rememberFocus(row, index, 'unit')} onBlur={(e) => handleCommit(index, { unit: e.currentTarget.value })} onKeyDown={(e) => { if (e.key === 'Enter') handleCommit(index, { unit: (e.target as HTMLInputElement).value }); if (e.key === 'ArrowDown') { e.preventDefault(); focusMove(e.currentTarget, 1); } if (e.key === 'ArrowUp') { e.preventDefault(); focusMove(e.currentTarget, -1); } if (e.key === 'Escape') { (e.currentTarget as HTMLInputElement).blur(); } }} />
					) : (row.unit || '')}
				</div>
				{/* Unit Price */}
				<div className={`px-3 ${numericClass} ${underline}`} style={{ fontVariantNumeric: 'tabular-nums' }}>
					{editable ? (
						<input type="number" className="w-full px-2 py-1 border border-owlin-stroke rounded-owlin text-sm text-right" defaultValue={Number.isFinite(row.unit_price) ? String(row.unit_price) : ''} data-col="price" data-row={index} onFocus={() => rememberFocus(row, index, 'price')} onBlur={(e) => handleCommit(index, { unit_price: parseFloat(e.currentTarget.value || '0') })} onKeyDown={(e) => { if (e.key === 'Enter') handleCommit(index, { unit_price: parseFloat((e.target as HTMLInputElement).value || '0') }); if (e.key === 'ArrowDown') { e.preventDefault(); focusMove(e.currentTarget, 1); } if (e.key === 'ArrowUp') { e.preventDefault(); focusMove(e.currentTarget, -1); } if (e.key === 'Escape') { (e.currentTarget as HTMLInputElement).blur(); } }} />
					) : (Number.isFinite(row.unit_price) ? `£${(row.unit_price as number).toFixed(2)}` : '')}
				</div>
				{/* VAT % */}
				<div className={`px-3 ${numericClass} ${underline}`} style={{ fontVariantNumeric: 'tabular-nums' }}>
					{editable ? (
						<input type="number" className="w-full px-2 py-1 border border-owlin-stroke rounded-owlin text-sm text-right" defaultValue={Number.isFinite(row.vat_percent) ? String(row.vat_percent) : ''} data-col="vat" data-row={index} onFocus={() => rememberFocus(row, index, 'vat')} onBlur={(e) => handleCommit(index, { vat_percent: parseFloat(e.currentTarget.value || '0') })} onKeyDown={(e) => { if (e.key === 'Enter') handleCommit(index, { vat_percent: parseFloat((e.target as HTMLInputElement).value || '0') }); if (e.key === 'ArrowDown') { e.preventDefault(); focusMove(e.currentTarget, 1); } if (e.key === 'ArrowUp') { e.preventDefault(); focusMove(e.currentTarget, -1); } if (e.key === 'Escape') { (e.currentTarget as HTMLInputElement).blur(); } }} />
					) : (Number.isFinite(row.vat_percent) ? (row.vat_percent as number).toFixed(2) : '')}
				</div>
				{/* Line Total */}
				<div className={`px-3 ${numericClass} ${underline} font-semibold`} style={{ fontVariantNumeric: 'tabular-nums' }}>
					{editable ? (
						<input type="number" className="w-full px-2 py-1 border border-owlin-stroke rounded-owlin text-sm text-right" defaultValue={Number.isFinite(row.line_total) ? String(row.line_total) : ''} data-col="total" data-row={index} onFocus={() => rememberFocus(row, index, 'total')} onBlur={(e) => handleCommit(index, { line_total: parseFloat(e.currentTarget.value || '0') })} onKeyDown={(e) => { if (e.key === 'Enter') handleCommit(index, { line_total: parseFloat((e.target as HTMLInputElement).value || '0') }); if (e.key === 'ArrowDown') { e.preventDefault(); focusMove(e.currentTarget, 1); } if (e.key === 'ArrowUp') { e.preventDefault(); focusMove(e.currentTarget, -1); } if (e.key === 'Escape') { (e.currentTarget as HTMLInputElement).blur(); } }} />
					) : (Number.isFinite(row.line_total) ? `£${(row.line_total as number).toFixed(2)}` : '')}
				</div>
			</div>
		);
	}), [editable, handleCommit, rowPad, focusMove, gridCols, query, rememberFocus]);

	// Header component (inner content synced horizontally)
	const TableHeader = useCallback(() => (
		<div ref={headerInnerRef} className={`${gridCols} py-2`}>
			<div className="px-3 sticky left-0 bg-[#F9FAFF] z-10 border-r border-owlin-stroke">Description</div>
			<div className="px-3 text-right">Qty</div>
			<div className="px-3 text-center">Unit</div>
			<div className="px-3 text-right">Unit Price</div>
			<div className="px-3 text-right">VAT %</div>
			<div className="px-3 text-right">Line Total</div>
		</div>
	), [gridCols]);

	// Toolbar (search, filters, density, jump)
	const [jumpVal, setJumpVal] = useState('');
	const Toolbar = useCallback(() => (
		<div className="flex items-center justify-between py-2 gap-2">
			<div className="flex items-center gap-2">
				<input ref={searchInputRef} value={query} onChange={e => setQuery(e.target.value)} placeholder="Search description" className="h-8 w-[220px] px-2 rounded-owlin border border-owlin-stroke bg-owlin-bg text-sm" aria-label="Search line items" />
				<div className="inline-flex items-center gap-1 text-xs">
					<button onClick={() => setFilter('all')} className={`px-2 py-1 rounded-owlin border ${filter==='all'?'border-owlin-stroke bg-owlin-bg':'border-transparent hover:bg-owlin-bg'}`}>All</button>
					<button onClick={() => setFilter('low')} className={`px-2 py-1 rounded-owlin border ${filter==='low'?'border-owlin-stroke bg-owlin-bg':'border-transparent hover:bg-owlin-bg'}`}>Low-confidence</button>
					<button onClick={() => setFilter('flagged')} className={`px-2 py-1 rounded-owlin border ${filter==='flagged'?'border-owlin-stroke bg-owlin-bg':'border-transparent hover:bg-owlin-bg'}`}>Flagged</button>
				</div>
			</div>
			<div className="flex items-center gap-3 text-xs text-owlin-muted">
				<span className="rounded-full px-2 py-0.5 border border-owlin-stroke bg-owlin-bg">Rows: {filteredItems.length}</span>
				<label className="flex items-center gap-1">
					<span>Density</span>
					<select value={densityState} onChange={(e) => setDensityState(e.target.value as any)} className="h-7 px-2 rounded-owlin border border-owlin-stroke bg-owlin-bg text-xs">
						<option value="compact">Compact</option>
						<option value="comfort">Comfort</option>
					</select>
				</label>
				<label className="flex items-center gap-1">
					<span>Go to</span>
					<input ref={jumpRef} value={jumpVal} onChange={e => setJumpVal(e.target.value)} onKeyDown={(e) => { if (e.key === 'Enter') { const idx = Math.max(0, Math.min(filteredItems.length - 1, parseInt(jumpVal || '0', 10) - 1)); virtuosoRef.current?.scrollToIndex({ index: idx, align: 'center' }); setTimeout(() => { const input = (scrollBodyRef.current || document).querySelector(`input[data-col="desc"][data-row="${idx}"]`) as HTMLInputElement | null; input?.focus(); }, 50); } }} className="h-7 w-16 px-2 rounded-owlin border border-owlin-stroke bg-owlin-bg text-xs" placeholder="#"/>
				</label>
			</div>
		</div>
	), [query, filter, densityState, filteredItems.length, jumpVal]);

	// Totals bar (inner content synced horizontally)
	const TotalsBar = useCallback(() => (
		<div className="py-3 px-0 bg-[var(--owlin-card)]">
			<div ref={totalsInnerRef} className={`${gridCols} px-3`}>
				<div className="px-3 sticky left-0 bg-[var(--owlin-card)] z-10 border-r border-owlin-stroke" />
				<div className="col-span-5">
					<div className="flex justify-between text-sm">
						<span>Subtotal:</span>
						<span className="tabular font-semibold">{formatGBP(subtotalCents)}</span>
					</div>
					<div className="flex justify-between text-sm">
						<span>VAT:</span>
						<span className="tabular font-semibold">{formatGBP(vatTotalCents)}</span>
					</div>
					<div className="flex justify-between text-base font-semibold border-t border-owlin-stroke pt-2">
						<span>Total:</span>
						<span className="tabular flex items-center gap-2">{formatGBP(totalCents)} {savedRow !== null && (<span className="text-green-600 text-sm">Saved ✓</span>)}</span>
					</div>
				</div>
			</div>
		</div>
	), [subtotalCents, vatTotalCents, totalCents, savedRow, gridCols]);

	// Sync header/totals horizontal scroll with body
	const onBodyScroll = useCallback<React.UIEventHandler<HTMLDivElement>>((e) => {
		const el = e.currentTarget;
		const x = el.scrollLeft;
		if (headerInnerRef.current) headerInnerRef.current.style.transform = `translateX(${-x}px)`;
		if (totalsInnerRef.current) totalsInnerRef.current.style.transform = `translateX(${-x}px)`;
	}, []);

	return (
		<div className="relative rounded-[var(--owlin-radius-lg)] border border-[var(--owlin-stroke)] bg-[var(--owlin-card)] h-[560px] lg:h-[640px] overflow-hidden" role="table" aria-rowcount={filteredItems.length}>
			{/* a11y live region */}
			<div role="status" aria-live="polite" className="sr-only">{liveMessage}</div>

			{/* Sticky header + toolbar */}
			<div className="sticky top-0 z-10 bg-[#F9FAFF] border-b border-[var(--owlin-stroke)] px-3">
				<div className="py-2 text-[13px] text-owlin-muted font-medium"><TableHeader /></div>
				<Toolbar />
			</div>

			{/* Scrollable (vertical) + horizontally scrollable body */}
			<div ref={scrollBodyRef} onScroll={onBodyScroll} className="overflow-y-auto overflow-x-auto h-[calc(100%-108px)]" id="line-items-scroll">
				<Virtuoso
					ref={virtuosoRef}
					data={filteredItems}
					overscan={8}
					itemContent={(index, row) => (
						<div className="px-3"><LineRow row={row} index={index} /></div>
					)}
					className="virt-table"
				/>
			</div>

			{/* Sticky totals (bottom) */}
			<div className="sticky bottom-0 z-10 bg-[var(--owlin-card)] border-t border-[var(--owlin-stroke)]">
				<TotalsBar />
			</div>
		</div>
	);
} 