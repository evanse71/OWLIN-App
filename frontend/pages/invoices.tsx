import React from "react";
import Sidebar from "../components/layout/Sidebar";
import InvoiceFilterPanel from "../components/invoices/InvoiceFilterPanel";
import UploadSection from "../components/invoices/UploadSection";
import InvoiceCardsPanel from "../components/invoices/InvoiceCardsPanel";
import InvoiceDetailBox from "../components/invoices/InvoiceDetailBox";
import { FiltersProvider } from "../state/filters/FiltersContext";
import { useRole } from "../hooks/useRole";
import { useLicense } from "../hooks/useLicense";

function Safe({ children }: { children: React.ReactNode }) {
  try { 
    return <>{children}</>; 
  }
  catch (e) {
    console.error("InvoicesPage runtime error:", e);
    return (
      <div className="p-4">
        <div className="mb-2 text-sm text-red-700 bg-red-50 border border-red-200 rounded-md px-3 py-2">
          Invoices page failed to render. Showing a safe skeleton so you can navigate.
        </div>
        <div className="grid grid-cols-12 gap-4">
          <div className="col-span-12 lg:col-span-3">
            <div className="h-64 bg-gray-100 rounded-lg" />
          </div>
          <div className="col-span-12 lg:col-span-9">
            <div className="h-10 bg-gray-100 rounded-lg mb-3" />
            <div className="h-40 bg-gray-100 rounded-lg" />
          </div>
        </div>
      </div>
    );
  }
}

export default function InvoicesPage() {
  const roleInfo = useRole();
  const role = (roleInfo?.name ?? "Finance") as "Finance"|"GM"|"ShiftLead";
  const license = useLicense(); // { valid:boolean }
  
  return (
    <div data-ui="invoices-page" className="min-h-screen bg-[#F8F9FB]" role="main" aria-label="Invoices">
      <div className="mx-auto max-w-[1200px] px-6 py-4">
        <div className="grid grid-cols-12 gap-4">
          <aside className="col-span-12 lg:col-span-3" data-ui="sidebar" role="navigation" aria-label="Primary">
            <Sidebar />
          </aside>

          <section className="col-span-12 lg:col-span-9" role="region" aria-label="Invoices workspace">
            <FiltersProvider role={role}>
              <Safe>
                <div className="grid grid-cols-12 gap-4">
                  <div className="col-span-12 lg:col-span-4">
                    <section data-ui="filter-panel" className="mb-3">
                      <InvoiceFilterPanel />
                    </section>
                    <section data-ui="upload-section" className="mb-3">
                      <UploadSection
                        onFilesUpload={async (files: File[]) => {
                          console.log('Upload files:', files);
                          // TODO: Implement actual upload
                        }}
                      />
                    </section>
                    <section data-ui="invoice-cards">
                      <InvoiceCardsPanel 
                        invoices={[]}
                        expandedId={null}
                        onCardClick={() => {}}
                        onCardKeyDown={() => {}}
                      />
                    </section>
                  </div>

                  <aside className="col-span-12 lg:col-span-8" data-ui="invoice-detail">
                    <InvoiceDetailBox 
                      invoice={null}
                      onRetryOCR={() => {}}
                      onResolveIssue={() => {}}
                    />
                  </aside>
                </div>
              </Safe>
            </FiltersProvider>
          </section>
        </div>
      </div>
    </div>
  );
} 