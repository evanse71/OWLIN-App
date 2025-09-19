import React from 'react';

interface DeliveryNotesPanelProps {
  selectedInvoiceId: string | null;
  siteId: string | null;
  onPaired: (dnId: string, invId: string) => void;
}

export default function DeliveryNotesPanel({ selectedInvoiceId, siteId, onPaired }: DeliveryNotesPanelProps) {
  return (
    <div className="p-4 border rounded-lg bg-gray-50">
      <h3 className="font-semibold mb-2">Delivery Notes</h3>
      <p className="text-sm text-gray-600">
        Delivery notes panel for invoice {selectedInvoiceId || 'none selected'}
      </p>
      <p className="text-xs text-gray-500 mt-2">
        Site: {siteId || 'none'}
      </p>
    </div>
  );
}