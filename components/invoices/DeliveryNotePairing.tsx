import React, { useState } from 'react';
import { DeliveryNote } from '@/services/api';

interface DeliveryNotePairingProps {
  isOpen: boolean;
  onClose: () => void;
  invoiceId: string;
  invoiceNumber?: string;
  supplierName?: string;
  onPair: (deliveryNoteId: string) => void;
}

const DeliveryNotePairing: React.FC<DeliveryNotePairingProps> = ({
  isOpen,
  onClose,
  invoiceId,
  invoiceNumber,
  supplierName,
  onPair,
}) => {
  const [selectedDeliveryNote, setSelectedDeliveryNote] = useState<string>('');
  const [searchTerm, setSearchTerm] = useState('');

  // Mock delivery notes - in real app, this would come from API
  const mockDeliveryNotes: DeliveryNote[] = [
    {
      id: 'dn-1',
      delivery_note_number: 'DN-2024-001',
      delivery_date: '2024-01-14',
      supplier_name: supplierName || 'ABC Corporation',
      total_amount: 1200.00,
      status: 'unmatched',
      confidence: 95,
      upload_timestamp: '2024-01-14T10:00:00Z',
    },
    {
      id: 'dn-2',
      delivery_note_number: 'DN-2024-002',
      delivery_date: '2024-01-15',
      supplier_name: supplierName || 'ABC Corporation',
      total_amount: 1350.00,
      status: 'unmatched',
      confidence: 88,
      upload_timestamp: '2024-01-15T09:00:00Z',
    },
    {
      id: 'dn-3',
      delivery_note_number: 'DN-2024-003',
      delivery_date: '2024-01-16',
      supplier_name: 'XYZ Company',
      total_amount: 950.00,
      status: 'unmatched',
      confidence: 92,
      upload_timestamp: '2024-01-16T11:00:00Z',
    },
  ];

  // Filter delivery notes based on search term
  const filteredDeliveryNotes = mockDeliveryNotes.filter(dn =>
    dn.delivery_note_number?.toLowerCase().includes(searchTerm.toLowerCase()) ||
    dn.supplier_name?.toLowerCase().includes(searchTerm.toLowerCase()) ||
    dn.delivery_date?.includes(searchTerm)
  );

  const handlePair = () => {
    if (selectedDeliveryNote) {
      onPair(selectedDeliveryNote);
      onClose();
    }
  };

  const calculatePairingConfidence = (deliveryNote: DeliveryNote) => {
    let confidence = 0;
    
    // Supplier name match
    if (deliveryNote.supplier_name === supplierName) {
      confidence += 40;
    }
    
    // Date proximity (within 7 days)
    if (deliveryNote.delivery_date && invoiceNumber) {
      const deliveryDate = new Date(deliveryNote.delivery_date);
      const today = new Date();
      const daysDiff = Math.abs((deliveryDate.getTime() - today.getTime()) / (1000 * 3600 * 24));
      if (daysDiff <= 7) {
        confidence += 30;
      } else if (daysDiff <= 14) {
        confidence += 15;
      }
    }
    
    // Amount similarity
    if (deliveryNote.total_amount) {
      confidence += 20;
    }
    
    return Math.min(confidence, 100);
  };

  if (!isOpen) return null;

  return (
    <>
      {/* Backdrop */}
      <div 
        className="fixed inset-0 bg-black bg-opacity-50 z-40"
        onClick={onClose}
      />

      {/* Modal */}
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-2xl w-full max-h-[80vh] overflow-hidden">
          {/* Header */}
          <div className="flex items-center justify-between p-6 border-b border-gray-200 dark:border-gray-700">
            <div>
              <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
                Pair Delivery Note
              </h2>
              <p className="text-sm text-gray-600 dark:text-gray-400">
                Select a delivery note to pair with invoice {invoiceNumber}
              </p>
            </div>
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
            >
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          {/* Search */}
          <div className="p-6 border-b border-gray-200 dark:border-gray-700">
            <input
              type="text"
              placeholder="Search delivery notes by number, supplier, or date..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent dark:bg-gray-700 dark:text-gray-100"
            />
          </div>

          {/* Delivery Notes List */}
          <div className="flex-1 overflow-y-auto p-6">
            <div className="space-y-3">
              {filteredDeliveryNotes.length === 0 ? (
                <div className="text-center py-8 text-gray-500 dark:text-gray-400">
                  No delivery notes found matching your search.
                </div>
              ) : (
                filteredDeliveryNotes.map((deliveryNote) => {
                  const pairingConfidence = calculatePairingConfidence(deliveryNote);
                  const isSelected = selectedDeliveryNote === deliveryNote.id;
                  
                  return (
                    <div
                      key={deliveryNote.id}
                      onClick={() => setSelectedDeliveryNote(deliveryNote.id)}
                      className={`p-4 border rounded-lg cursor-pointer transition-colors ${
                        isSelected
                          ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20'
                          : 'border-gray-200 dark:border-gray-700 hover:border-gray-300 dark:hover:border-gray-600'
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex-1">
                          <div className="flex items-center space-x-3">
                            <div className="text-lg">📦</div>
                            <div>
                              <div className="font-medium text-gray-900 dark:text-gray-100">
                                {deliveryNote.delivery_note_number}
                              </div>
                              <div className="text-sm text-gray-600 dark:text-gray-400">
                                {deliveryNote.supplier_name} • {deliveryNote.delivery_date}
                              </div>
                            </div>
                          </div>
                        </div>
                        
                        <div className="flex items-center space-x-3">
                          {/* Pairing Confidence */}
                          <div className="text-right">
                            <div className="text-sm font-medium text-gray-900 dark:text-gray-100">
                              {pairingConfidence}%
                            </div>
                            <div className="text-xs text-gray-500 dark:text-gray-400">
                              Match
                            </div>
                          </div>
                          
                          {/* Amount */}
                          <div className="text-right">
                            <div className="text-sm font-medium text-gray-900 dark:text-gray-100">
                              £{deliveryNote.total_amount?.toFixed(2) || '0.00'}
                            </div>
                            <div className="text-xs text-gray-500 dark:text-gray-400">
                              Total
                            </div>
                          </div>
                          
                          {/* Selection Radio */}
                          <div className={`w-4 h-4 rounded-full border-2 ${
                            isSelected
                              ? 'border-blue-500 bg-blue-500'
                              : 'border-gray-300 dark:border-gray-600'
                          }`}>
                            {isSelected && (
                              <div className="w-2 h-2 bg-white rounded-full m-0.5"></div>
                            )}
                          </div>
                        </div>
                      </div>
                      
                      {/* Confidence Indicators */}
                      <div className="mt-3 flex items-center space-x-4 text-xs">
                        {deliveryNote.supplier_name === supplierName && (
                          <span className="text-green-600 dark:text-green-400">✅ Supplier Match</span>
                        )}
                        {deliveryNote.delivery_date && (
                          <span className="text-blue-600 dark:text-blue-400">📅 Date: {deliveryNote.delivery_date}</span>
                        )}
                        {deliveryNote.total_amount && (
                          <span className="text-purple-600 dark:text-purple-400">💰 Amount: £{deliveryNote.total_amount.toFixed(2)}</span>
                        )}
                      </div>
                    </div>
                  );
                })
              )}
            </div>
          </div>

          {/* Footer */}
          <div className="flex items-center justify-between p-6 border-t border-gray-200 dark:border-gray-700">
            <div className="text-sm text-gray-600 dark:text-gray-400">
              {filteredDeliveryNotes.length} delivery note{filteredDeliveryNotes.length !== 1 ? 's' : ''} found
            </div>
            <div className="flex space-x-3">
              <button
                onClick={onClose}
                className="px-4 py-2 text-sm text-gray-600 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-200 transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handlePair}
                disabled={!selectedDeliveryNote}
                className="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                Pair Delivery Note
              </button>
            </div>
          </div>
        </div>
      </div>
    </>
  );
};

export default DeliveryNotePairing; 