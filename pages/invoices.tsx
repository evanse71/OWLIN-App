import * as React from "react";
import { useRouter } from "next/router";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Search, Plus, FileText, Package } from "lucide-react";
import UploadGlass from "@/components/invoices/UploadGlass";
import InvoiceCardEnhanced from "@/components/invoices/InvoiceCardEnhanced";
import DeliveryNoteCard from "@/components/invoices/DeliveryNoteCard";
import ManualInvoiceModal from "@/components/invoices/ManualInvoiceModal";
import ManualDeliveryNoteModal from "@/components/invoices/ManualDeliveryNoteModal";
import { getInvoices, getDNs, type Invoice, type DeliveryNote } from "@/lib/api";

// Types imported from lib/api.ts

export default function InvoicesPage() {
  const router = useRouter();
  const [invoices, setInvoices] = React.useState<Invoice[]>([]);
  const [deliveryNotes, setDeliveryNotes] = React.useState<DeliveryNote[]>([]);
  const [searchTerm, setSearchTerm] = React.useState<string>("");
  const [showManualInvoice, setShowManualInvoice] = React.useState(false);
  const [showManualDN, setShowManualDN] = React.useState(false);

  const refresh = React.useCallback(async () => {
    try {
      const [invoicesData, dnsData] = await Promise.all([
        getInvoices(),
        getDNs()
      ]);
      setInvoices(invoicesData.items);
      setDeliveryNotes(dnsData.items);
    } catch (error) {
      console.error('Failed to refresh data:', error);
    }
  }, []);

  React.useEffect(() => { refresh(); }, [refresh]);

  React.useEffect(() => {
    const supplier = String(router.query.supplier || "");
    if (supplier) setSearchTerm(supplier);
  }, [router.query.supplier]);

  // Polling for queued invoices
  React.useEffect(() => {
    const hasQueued = invoices.some(inv => inv.status === 'queued');
    if (!hasQueued) return;

    const interval = setInterval(refresh, 3000); // Poll every 3 seconds
    return () => clearInterval(interval);
  }, [invoices, refresh]);

  const handleUploaded = React.useCallback((res: {invoice_id?: string, dn_id?: string}) => {
    // Optimistic update - refresh after a short delay to allow backend processing
    setTimeout(refresh, 1000);
  }, [refresh]);

  const filteredInvoices = React.useMemo(() => {
    const s = (searchTerm || "").toLowerCase().trim();
    if (!s) return invoices;
    
    return invoices.filter(inv =>
      [inv.supplier, inv.id, inv.document_id, inv.filename].filter(Boolean)
        .map(x => String(x).toLowerCase())
        .some(txt => txt.includes(s))
    );
  }, [invoices, searchTerm]);

  return (
    <div className="space-y-6">
      {/* Header with dual glass upload */}
      <Card className="rounded-2xl">
        <CardHeader className="p-4 sm:p-6">
          <CardTitle className="text-lg font-semibold">Upload Documents</CardTitle>
        </CardHeader>
        <CardContent className="p-4 sm:p-6 pt-0">
          <UploadGlass onUploaded={handleUploaded} />
        </CardContent>
      </Card>

      {/* Search and controls */}
      <Card className="rounded-2xl">
        <CardContent className="p-4 sm:p-6">
          <div className="flex items-center gap-4">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4" />
              <input
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                placeholder="Search invoices..."
                className="w-full h-10 pl-10 pr-4 rounded-lg border border-gray-200 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
            </div>
            <Button variant="outline" onClick={refresh}>
              Refresh
            </Button>
            <Button variant="outline" onClick={() => setShowManualInvoice(true)}>
              <FileText className="w-4 h-4 mr-2" />
              Manual Invoice
            </Button>
            <Button variant="outline" onClick={() => setShowManualDN(true)}>
              <Package className="w-4 h-4 mr-2" />
              Manual DN
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Delivery Notes Section */}
      {deliveryNotes.length > 0 && (
        <Card className="rounded-2xl">
          <CardHeader className="p-4 sm:p-6">
            <CardTitle className="text-lg font-semibold">
              Delivery Notes ({deliveryNotes.length})
            </CardTitle>
          </CardHeader>
          <CardContent className="p-4 sm:p-6 pt-0">
            <div className="space-y-3">
              {deliveryNotes.slice(0, 3).map(dn => (
                <DeliveryNoteCard key={dn.id} dn={dn} />
              ))}
              {deliveryNotes.length > 3 && (
                <div className="text-center pt-2">
                  <Button variant="ghost" size="sm">
                    View all {deliveryNotes.length} delivery notes
                  </Button>
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Invoices List */}
      <div className="space-y-4">
        {filteredInvoices.map(invoice => (
          <InvoiceCardEnhanced 
            key={invoice.id} 
            inv={invoice} 
            onChanged={refresh}
          />
        ))}
        
        {filteredInvoices.length === 0 && (
          <Card className="rounded-2xl">
            <CardContent className="py-12 text-center">
              <div className="text-gray-500">
                {searchTerm ? (
                  <div>
                    <Search className="w-12 h-12 mx-auto mb-4 text-gray-300" />
                    <p>No invoices match your search criteria.</p>
                    <Button 
                      variant="outline" 
                      onClick={() => {
                        setSearchTerm('');
                        router.push('/invoices');
                      }} 
                      className="mt-2"
                    >
                      Clear filters
                    </Button>
                  </div>
                ) : (
                  <div>
                    <p>No invoices yet. Upload a PDF or create a manual invoice to get started.</p>
                  </div>
                )}
              </div>
            </CardContent>
          </Card>
        )}
      </div>

      {/* Manual Modals */}
      <ManualInvoiceModal
        isOpen={showManualInvoice}
        onClose={() => setShowManualInvoice(false)}
        onCreated={refresh}
      />
      <ManualDeliveryNoteModal
        isOpen={showManualDN}
        onClose={() => setShowManualDN(false)}
        onCreated={refresh}
      />
    </div>
  );
}