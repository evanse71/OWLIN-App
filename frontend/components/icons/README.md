# Owlin Icon Library

A local SVG icon library for the Owlin application, providing consistent, minimal, and accessible icons.

## Usage

```tsx
import { UploadIcon, WarningTriangleIcon } from "@/components/icons";

<button className="inline-flex items-center gap-2 px-3 py-1.5 rounded-[8px] border border-[#E5E7EB]">
  <UploadIcon ariaLabel="Upload invoices" />
  <span className="text-[14px]">Upload</span>
</button>

<div className="flex items-center gap-2 bg-[#FFFBEB] border border-[#FDE68A] text-[#7C2D12] rounded-[8px] p-2">
  <WarningTriangleIcon stroke="#D97706" ariaLabel="Warning" />
  <span className="text-[12px]">OCR confidence low on latest file.</span>
</div>
```

## Icon Props

All icons accept the following props:

- `size?: number` - Size in pixels (default: 20)
- `stroke?: string` - Stroke color (default: '#1C2A39' Owlin Navy)
- `strokeWidth?: number` - Stroke width (default: 1.5)
- `className?: string` - Optional Tailwind classes
- `ariaLabel?: string` - Accessible label (falls back to component name)

## Color Guidelines

- **Default**: `#1C2A39` (Owlin Navy)
- **Muted/Disabled**: `#6B7280`
- **Success**: Use icon color override `stroke="#15803D"` or keep navy inside green UI
- **Warning**: `#D97706`
- **Error**: `#E07A5F`

## Adding New Icons

1. Copy the template from `IconTypes.ts` comment
2. Keep viewBox at `0 0 24 24`
3. Verify at 16/20/24px in **IconGallery**
4. Export in `index.ts`
5. Use navy by default; don't hardcode colors unless semantic (warn/error)

## Accessibility

- Always set `ariaLabel` when used in buttons without text
- All icons have `role="img"` and proper ARIA labels
- Icons are pure components with no side effects

## Available Icons

### Core (8)
- InvoiceIcon, UploadIcon, DownloadIcon, SupplierIcon
- DeliveryNoteIcon, CreditNoteIcon, DashboardIcon, ReportIcon

### Feedback (5)
- CheckCircleIcon, WarningTriangleIcon, InfoIcon, ErrorOctagonIcon, ProgressCircleIcon

### Utility (15)
- SearchIcon, FilterIcon, SortIcon, CalendarIcon, ClockIcon
- LinkIcon, UnlinkIcon, EditIcon, LockIcon, UnlockIcon
- RefreshIcon, SyncIcon, ExportIcon, ImportIcon

Total: 28 icons 