import React, { useState, useRef } from "react";
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { FileText, Package } from 'lucide-react'
import { apiUpload } from "@/lib/api";

type Props = {
  onCreated: (items: {type:string; id:string|null; page:number}[], jobId:string) => void;
  docType?: "invoice"|"delivery_note";
};

export default function UploadGlass({ onCreated, docType }: Props) {
  const [hover, setHover] = useState(false);
  const [progress, setProgress] = useState<"idle"|"uploading"|"processing"|"done"|"error">("idle");
  const inputRef = useRef<HTMLInputElement>(null);

  const handleFiles = async (files: FileList | null) => {
    if (!files || !files.length) return;
    setProgress("uploading");
    try {
      const file = files[0];
      const data = await apiUpload(file, docType);
      setProgress("processing");
      onCreated(data.items, data.job_id);
      setProgress("done");
    } catch (e) {
      console.error(e);
      setProgress("error");
    }
  };

  const glassStyle = "backdrop-blur-sm bg-white/60 border border-slate-200/60 rounded-xl shadow-sm transition-all duration-200"
  const dragStyle = "border-blue-400 bg-blue-50/80 shadow-lg scale-105"

  return (
    <Card className={`${glassStyle} ${hover ? dragStyle : ''}`}>
      <CardContent className="p-6">
        <div
          onDrop={(e) => { e.preventDefault(); handleFiles(e.dataTransfer.files); }}
          onDragOver={(e)=>e.preventDefault()}
          onDragEnter={()=>setHover(true)}
          onDragLeave={()=>setHover(false)}
          className="h-32 flex flex-col items-center justify-center cursor-pointer"
        >
          <input ref={inputRef} type="file" className="hidden" onChange={(e)=>handleFiles(e.target.files)} />
          <div className="text-center">
            {docType === 'invoice' ? (
              <FileText className="h-8 w-8 text-blue-600 mb-2 mx-auto" />
            ) : (
              <Package className="h-8 w-8 text-green-600 mb-2 mx-auto" />
            )}
            <h3 className="font-medium text-sm mb-1">
              {docType === 'invoice' ? 'Upload Invoice' : 'Upload Delivery Note'}
            </h3>
            <div className="text-xs text-zinc-600 mb-3">
              Drag & drop **PDF/PNG/JPG** here, or{" "}
              <button className="underline" onClick={()=>inputRef.current?.click()}>browse</button>
            </div>
            <div className="mt-3 h-2 w-full bg-zinc-100 rounded overflow-hidden">
              <div
                className={`h-2 transition-all ${
                  progress==="idle"?"w-0":
                  progress==="uploading"?"w-1/3":
                  progress==="processing"?"w-2/3":
                  progress==="done"?"w-full":
                  "w-full bg-red-300"
                }`}
                style={{ background: progress==="error" ? undefined : undefined }}
              />
            </div>
            <div className="mt-2 text-xs text-zinc-500">
              {progress==="idle" && "Awaiting file"}
              {progress==="uploading" && "Uploading..."}
              {progress==="processing" && "Scanning & parsing..."}
              {progress==="done" && "Complete"}
              {progress==="error" && "Failed — try again"}
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
