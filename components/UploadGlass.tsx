import React, { useRef, useState } from "react";
import { apiUpload } from "@/lib/api";

export default function UploadGlass({
  docType, onCreated
}: {
  docType?: "invoice"|"delivery_note";
  onCreated: (items: {type:string; id:string; pages:number[]; page_count:number}[]) => void;
}) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [state, setState] = useState<"idle"|"uploading"|"processing"|"done"|"error">("idle");
  const [err, setErr] = useState<string | null>(null);

  const handle = async (files: FileList | null) => {
    if (!files || !files.length) return;
    setErr(null); setState("uploading");
    const file = files[0];
    try {
      const fd = new FormData();
      fd.append("file", file);
      if (docType) fd.append("doc_type", docType);
      const res = await fetch("/api/uploads", { method: "POST", body: fd });
      if (!res.ok) {
        const txt = await res.text();
        throw new Error(`${res.status} ${res.statusText}: ${txt}`);
      }
      setState("processing");
      const json = await res.json();
      setState("done");
      onCreated(json.items || []);
    } catch (e:any) {
      setErr(e.message || "Upload failed");
      setState("error");
    }
  };

  return (
    <div className="rounded-2xl border bg-white/60 backdrop-blur p-6">
      <div
        onDrop={(e)=>{e.preventDefault(); handle(e.dataTransfer.files);}}
        onDragOver={(e)=>e.preventDefault()}
        className="rounded-xl border border-dashed p-8 text-center"
      >
        <div className="text-sm font-medium">Upload {docType==="delivery_note" ? "Delivery Note" : "Invoice"}</div>
        <div className="text-xs text-zinc-500 mt-1">Drag & drop <b>PDF/PNG/JPG</b> here, or <button className="underline" onClick={()=>inputRef.current?.click()}>browse</button></div>
        <input ref={inputRef} type="file" accept=".pdf,.png,.jpg,.jpeg" className="hidden" onChange={(e)=>handle(e.target.files)} />
        <div className="mt-3 h-2 w-full bg-zinc-100 rounded overflow-hidden">
          <div className={`h-2 ${state==="idle"?"w-0":state==="uploading"?"w-1/3":state==="processing"?"w-2/3":state==="done"?"w-full":"w-full bg-red-300"}`} />
        </div>
        <div className="mt-2 text-xs text-zinc-500">
          {state==="idle" && "Awaiting file"}
          {state==="uploading" && "Uploading..."}
          {state==="processing" && "Scanning & grouping..."}
          {state==="done" && "Complete"}
          {state==="error" && (<>Failed — {err}</>)}
        </div>
      </div>
    </div>
  );
}
