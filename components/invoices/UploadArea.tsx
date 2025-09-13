import { useState } from 'react'
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Upload } from 'lucide-react'

interface UploadAreaProps {
  onFiles?: (files: File[]) => void
  isUploading?: boolean
}

export default function UploadArea({ onFiles, isUploading = false }: UploadAreaProps) {
  const [dragActive, setDragActive] = useState(false)

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true)
    } else if (e.type === "dragleave") {
      setDragActive(false)
    }
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setDragActive(false)
    
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      const files = Array.from(e.dataTransfer.files)
      onFiles?.(files)
    }
  }

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      const files = Array.from(e.target.files)
      onFiles?.(files)
    }
  }

  return (
    <Card className="ow-card">
      <CardContent className="p-6">
        <div 
          className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors ${
            dragActive 
              ? 'border-[var(--ow-primary)] bg-[var(--ow-primary)]/5' 
              : 'border-[var(--ow-border)]'
          }`}
          onDragEnter={handleDrag}
          onDragLeave={handleDrag}
          onDragOver={handleDrag}
          onDrop={handleDrop}
        >
          <Upload className="h-12 w-12 text-[var(--ow-ink-dim)] mx-auto mb-4" />
          <h3 className="text-lg font-medium mb-2 text-[var(--ow-ink)]">Upload Documents</h3>
          <p className="text-[var(--ow-ink-dim)] mb-4">
            Drag and drop your invoice files here, or click to browse
          </p>
          <input
            type="file"
            accept=".pdf,.png,.jpg,.jpeg"
            onChange={handleFileSelect}
            className="hidden"
            id="file-upload"
            disabled={isUploading}
            multiple
          />
          <label htmlFor="file-upload">
            <Button asChild disabled={isUploading}>
              <span>
                <Upload className="h-4 w-4 mr-2" />
                {isUploading ? 'Uploading...' : 'Choose Files'}
              </span>
            </Button>
          </label>
        </div>
      </CardContent>
    </Card>
  )
} 