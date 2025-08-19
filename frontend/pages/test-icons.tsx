import React from "react";
import * as Icons from "../components/icons";

const groups: Record<string, (keyof typeof Icons)[]> = {
  "Core": ["InvoiceIcon","UploadIcon","DownloadIcon","SupplierIcon","DeliveryNoteIcon","CreditNoteIcon","DashboardIcon","ReportIcon"],
  "Feedback": ["CheckCircleIcon","WarningTriangleIcon","InfoIcon","ErrorOctagonIcon","ProgressCircleIcon"],
  "Utility": ["SearchIcon","FilterIcon","SortIcon","CalendarIcon","ClockIcon","LinkIcon","UnlinkIcon","EditIcon","LockIcon","UnlockIcon","RefreshIcon","SyncIcon","ExportIcon","ImportIcon"],
};

export default function TestIcons() {
  const sizes = [16, 20, 24];
  
  React.useEffect(() => {
    console.log("=== OWLIN ICON GALLERY - RENDERED ICONS ===");
    Object.entries(groups).forEach(([groupName, iconKeys]) => {
      console.log(`${groupName}: ${iconKeys.join(', ')}`);
    });
    console.log("=== END ICON GALLERY ===");
  }, []);

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-6xl mx-auto">
        <h1 className="text-2xl font-bold mb-6">Icon Test Page</h1>
        <p className="text-gray-600 mb-8">Check browser console for icon list</p>
        
        {Object.entries(groups).map(([label, keys]) => (
          <div key={label} className="mb-8">
            <h2 className="text-lg font-semibold mb-4">{label}</h2>
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-4">
              {keys.map((k) => {
                const Icon = (Icons as any)[k];
                return (
                  <div key={k} className="bg-white rounded-lg border p-4">
                    <div className="text-sm text-gray-600 mb-2">{k}</div>
                    <div className="flex items-center gap-4">
                      {sizes.map(sz => (
                        <div key={sz} className="flex flex-col items-center">
                          <Icon size={sz} />
                          <div className="text-xs text-gray-500 mt-1">{sz}px</div>
                        </div>
                      ))}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
} 