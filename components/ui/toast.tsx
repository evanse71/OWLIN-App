import React, { createContext, useContext, useState, useCallback, useEffect } from "react";

type T = { id: number; kind: "success"|"error"|"info"; text: string };
const Ctx = createContext<{ push: (t: Omit<T,"id">)=>void } | null>(null);

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [items, setItems] = useState<T[]>([]);
  const push = useCallback((t: Omit<T,"id">) => {
    const id = Date.now() + Math.random();
    setItems((s)=>[...s, { id, ...t }]);
    setTimeout(()=> setItems((s)=>s.filter(i=>i.id!==id)), 3000);
  }, []);
  return (
    <Ctx.Provider value={{ push }}>
      {children}
      <div className="fixed top-4 right-4 z-[2000] space-y-2">
        {items.map(i=>(
          <div key={i.id} className={`rounded-xl px-3 py-2 shadow border ${
            i.kind==="success"?"bg-emerald-50 border-emerald-200 text-emerald-800":
            i.kind==="error"?"bg-rose-50 border-rose-200 text-rose-800":
                          "bg-slate-50 border-slate-200 text-slate-800"}`}>
            {i.text}
          </div>
        ))}
      </div>
    </Ctx.Provider>
  );
}

export function useToast() {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error("Wrap app with <ToastProvider>");
  return {
    success: (text: string)=>ctx.push({ kind:"success", text }),
    error:   (text: string)=>ctx.push({ kind:"error", text }),
    info:    (text: string)=>ctx.push({ kind:"info", text }),
  };
}