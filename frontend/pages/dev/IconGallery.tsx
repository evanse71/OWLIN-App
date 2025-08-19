import React from "react";
import * as Icons from "../../components/icons";

const groups: Record<string, (keyof typeof Icons)[]> = {
  "Core": ["InvoiceIcon","UploadIcon","DownloadIcon","SupplierIcon","DeliveryNoteIcon","CreditNoteIcon","DashboardIcon","ReportIcon"],
  "Feedback": ["CheckCircleIcon","WarningTriangleIcon","InfoIcon","ErrorOctagonIcon","ProgressCircleIcon"],
  "Utility": ["SearchIcon","FilterIcon","SortIcon","CalendarIcon","ClockIcon","LinkIcon","UnlinkIcon","EditIcon","LockIcon","UnlockIcon","RefreshIcon","SyncIcon","ExportIcon","ImportIcon"],
};

export default function IconGallery() {
  const sizes = [16, 20, 24];
  
  React.useEffect(() => {
    console.log("Rendered icons:");
    Object.entries(groups).forEach(([groupName, iconKeys]) => {
      console.log(`${groupName}: ${iconKeys.join(', ')}`);
    });
  }, []);

  return (
    <div className="min-h-screen bg-[#F8F9FB] font-[Inter] text-[#1F2937]">
      <div className="max-w-[1100px] mx-auto px-6 py-6">
        <h1 className="text-[16px] font-semibold mb-4">Owlin Icon Gallery</h1>
        {Object.entries(groups).map(([label, keys]) => (
          <div key={label} className="mb-8">
            <h2 className="text-[14px] font-semibold mb-2">{label}</h2>
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-4">
              {keys.map((k) => {
                const Icon = (Icons as any)[k];
                return (
                  <div key={k} className="bg-white rounded-[12px] border border-[#E5E7EB] shadow-sm p-3">
                    <div className="text-[12px] text-[#6B7280] mb-2">{k}</div>
                    <div className="flex items-center gap-4">
                      {sizes.map(sz => (
                        <div key={sz} className="flex flex-col items-center">
                          <Icon size={sz} />
                          <div className="text-[12px] text-[#6B7280] mt-1">{sz}px</div>
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