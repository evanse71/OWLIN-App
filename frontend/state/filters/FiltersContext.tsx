import { createContext, useContext, useEffect, useMemo, useRef, useState } from "react";

export type Role = "Finance" | "GM" | "ShiftLead";
export type SortKey = "newest"|"oldest"|"value_desc"|"value_asc"|"supplier_az"|"most_issues";

export type FiltersState = {
  role: Role;
  venueIds: number[];
  dateFrom?: string; dateTo?: string;
  supplierQuery: string; searchText: string;
  sort: SortKey;
  onlyUnmatched: boolean; onlyFlagged: boolean; onlyWithCredit: boolean;
};

export const LOCAL_KEY = "owlin_invoice_filters_v2";

const DEFAULTS: Record<Role, Omit<FiltersState,"role">> = {
  Finance:   { venueIds:[], supplierQuery:"", searchText:"", sort:"newest",     onlyUnmatched:false, onlyFlagged:false, onlyWithCredit:false },
  GM:        { venueIds:[], supplierQuery:"", searchText:"", sort:"supplier_az", onlyUnmatched:false, onlyFlagged:true,  onlyWithCredit:false },
  ShiftLead: { venueIds:[], supplierQuery:"", searchText:"", sort:"newest",     onlyUnmatched:true,  onlyFlagged:false, onlyWithCredit:false },
};

const Ctx = createContext<{filters:FiltersState; setFilters:(u:Partial<FiltersState>)=>void; reset:()=>void;}|null>(null);

export const useFilters = () => useContext(Ctx)!;

function parseURL(): Partial<FiltersState> {
  if (typeof window==="undefined") return {};
  const sp = new URLSearchParams(window.location.search);
  const v = sp.get("venue"); const venueIds = v? v.split(",").map(x=>parseInt(x,10)).filter(Boolean):[];
  return {
    venueIds,
    dateFrom: sp.get("from") || undefined,
    dateTo: sp.get("to") || undefined,
    supplierQuery: sp.get("supplier") || "",
    searchText: sp.get("q") || "",
    sort: (sp.get("sort") as FiltersState["sort"]) || "newest",
    onlyUnmatched: sp.get("unmatched")==="1",
    onlyFlagged: sp.get("flagged")==="1",
    onlyWithCredit: sp.get("credit")==="1",
  };
}

function writeURL(s: FiltersState) {
  const p = new URLSearchParams();
  if (s.venueIds.length) p.set("venue", s.venueIds.join(","));
  if (s.dateFrom) p.set("from", s.dateFrom);
  if (s.dateTo) p.set("to", s.dateTo);
  if (s.supplierQuery) p.set("supplier", s.supplierQuery);
  if (s.searchText) p.set("q", s.searchText);
  p.set("sort", s.sort);
  p.set("unmatched", s.onlyUnmatched ? "1" : "0");
  p.set("flagged", s.onlyFlagged ? "1" : "0");
  p.set("credit", s.onlyWithCredit ? "1" : "0");
  window.history.replaceState(null, "", `?${p.toString()}`);
}

export function FiltersProvider({ role, children }: { role: Role; children: React.ReactNode }) {
  const first = useRef(true);
  const [filters, setFiltersState] = useState<FiltersState>(() => {
    let local: any = {};
    try { local = JSON.parse(localStorage.getItem(LOCAL_KEY) || "null") || {}; } catch {}
    return { role, ...DEFAULTS[role], ...local, ...parseURL() };
  });

  useEffect(() => {
    const t = setTimeout(() => {
      writeURL(filters);
      try { localStorage.setItem(LOCAL_KEY, JSON.stringify({ ...filters, role: undefined })); } catch {}
    }, 50);
    return () => clearTimeout(t);
  }, [filters]);

  const api = useMemo(() => ({
    filters,
    setFilters: (u: Partial<FiltersState>) => setFiltersState(s => ({ ...s, ...u })),
    reset: () => setFiltersState(s => ({ ...s, ...DEFAULTS[s.role] })),
  }), [filters]);

  return <Ctx.Provider value={api}>{children}</Ctx.Provider>;
} 