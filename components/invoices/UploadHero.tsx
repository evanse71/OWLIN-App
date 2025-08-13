import React, { useState, useRef, useCallback } from 'react';

interface UploadHeroProps {
  onFiles: (files: File[]) => void;
  onManualInvoice: () => void;
}

export default function UploadHero({ onFiles, onManualInvoice }: UploadHeroProps) {
  const [isDragOver, setIsDragOver] = useState(false);
  const [fileChips, setFileChips] = useState<Array<{ id: string; file: File; type: string }>>([]);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
    const files = Array.from(e.dataTransfer.files);
    if (files.length > 0) {
      handleFiles(files);
    }
  }, []);

  const handleFileSelect = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || []);
    if (files.length > 0) {
      handleFiles(files);
    }
  }, []);

  const handleFiles = useCallback((files: File[]) => {
    const newChips = files.map(file => ({
      id: `file-${Date.now()}-${Math.random()}`,
      file,
      type: getFileType(file.name)
    }));
    setFileChips(prev => [...prev, ...newChips]);
    onFiles(files);
  }, [onFiles]);

  const removeFile = useCallback((id: string) => {
    setFileChips(prev => prev.filter(chip => chip.id !== id));
  }, []);

  const getFileType = (filename: string): string => {
    const ext = filename.split('.').pop()?.toLowerCase();
    switch (ext) {
      case 'pdf': return 'PDF';
      case 'png': case 'jpg': case 'jpeg': return 'Image';
      case 'tiff': case 'tif': return 'TIFF';
      default: return 'Document';
    }
  };

  const handleDropzoneClick = () => {
    fileInputRef.current?.click();
  };

  return (
    <div 
      className={`relative w-full rounded-[var(--owlin-radius)] bg-[color-mix(in_oklab,var(--owlin-card)_60%,transparent)] backdrop-blur border border-[var(--owlin-stroke)] shadow-[var(--owlin-shadow)] p-6`}
      role="region" 
      aria-label="Upload documents"
    >
      {/* Header row */}
      <div className="flex items-center justify-between mb-4">
        <div>
          <h2 className="text-[16px] font-semibold text-[var(--owlin-text)] mb-1">
            Upload invoices, delivery notes, receipts, utilities
          </h2>
          <p className="text-[13px] text-[var(--owlin-muted)]">
            No cloud. Files never leave this device.
          </p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => fileInputRef.current?.click()}
            className="min-h-[40px] rounded-[12px] px-4 bg-[var(--owlin-sapphire)] text-white hover:brightness-110 transition duration-[var(--dur-fast)]"
          >
            Upload from Files
          </button>
          <button
            onClick={onManualInvoice}
            className="min-h-[40px] rounded-[12px] px-4 border border-[var(--owlin-stroke)] text-[var(--owlin-cerulean)] bg-transparent hover:bg-[#F9FAFF] transition duration-[var(--dur-fast)]"
          >
            New Manual Invoice
          </button>
        </div>
      </div>

      {/* Dropzone */}
      <div
        className={`h-28 flex items-center justify-center rounded-[12px] border border-dashed border-[var(--owlin-stroke)] bg-[color-mix(in_oklab,var(--owlin-card)_40%,transparent)] text-[13px] text-[var(--owlin-muted)] transition-all duration-[var(--dur-fast)] cursor-pointer ${
          isDragOver ? 'ring-2 ring-[color-mix(in_oklab,var(--owlin-sapphire)_60%,transparent)] border-[var(--owlin-sapphire)]/60 scale-[0.99]' : ''
        }`}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={handleDropzoneClick}
        role="button"
        aria-label="Drag and drop files or click to upload"
        tabIndex={0}
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            handleDropzoneClick();
          }
        }}
      >
        {isDragOver ? 'Drop files here' : 'Drag and drop files here, or click to browse'}
      </div>

      {/* Hidden file input */}
      <input
        ref={fileInputRef}
        type="file"
        multiple
        accept=".pdf,.png,.jpg,.jpeg,.tiff,.tif"
        onChange={handleFileSelect}
        className="hidden"
      />

      {/* File chips */}
      {fileChips.length > 0 && (
        <div className="flex flex-wrap gap-2 mt-4">
          {fileChips.map((chip) => (
            <div key={chip.id} className="inline-flex items-center gap-2 rounded-full bg-[var(--owlin-bg)] border border-[var(--owlin-stroke)] px-2 py-1 text-[12px]">
              <span className="text-[10px] bg-[var(--owlin-stroke)] px-1.5 py-0.5 rounded text-[var(--owlin-muted)]">
                {chip.type}
              </span>
              <span className="max-w-[160px] truncate text-[var(--owlin-text)]">{chip.file.name}</span>
              <button
                onClick={() => removeFile(chip.id)}
                className="text-[var(--owlin-muted)] hover:text-[var(--owlin-text)] transition-colors"
                aria-label={`Remove ${chip.file.name}`}
                title="Remove file"
              >
                ×
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}; 