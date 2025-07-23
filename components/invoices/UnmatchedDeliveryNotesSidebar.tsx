import React from 'react';

interface DeliveryNote {
  id: string;
  filename: string;
  supplier: string;
  deliveryNumber: string;
  deliveryDate: string;
  status: 'Unmatched' | 'Processing' | 'Error' | 'Unknown';
  confidence?: number;
  parsedData?: any;
}

interface UnmatchedDeliveryNotesSidebarProps {
  deliveryNotes: DeliveryNote[];
}

const UnmatchedDeliveryNotesSidebar: React.FC<UnmatchedDeliveryNotesSidebarProps> = ({ deliveryNotes }) => {
  const unmatchedNotes = deliveryNotes.filter(note => note.status === 'Unmatched');
  
  const getStatusIcon = (status: DeliveryNote['status']) => {
    switch (status) {
      case 'Processing':
        return <div className="w-4 h-4 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />;
      case 'Error':
        return <span className="text-red-600">✗</span>;
      case 'Unknown':
        return <span className="text-gray-600">?</span>;
      default:
        return <span className="text-orange-600">⚠</span>;
    }
  };

  const getStatusColor = (status: DeliveryNote['status']) => {
    switch (status) {
      case 'Processing':
        return 'bg-blue-100 text-blue-800';
      case 'Error':
        return 'bg-red-100 text-red-800';
      case 'Unknown':
        return 'bg-gray-100 text-gray-800';
      default:
        return 'bg-orange-100 text-orange-800';
    }
  };

  return (
    <div className="hidden md:block w-80 bg-white border-l border-gray-200 p-6">
      <div className="sticky top-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
          <span>📋</span>
          <span>Unmatched Delivery Notes</span>
          {unmatchedNotes.length > 0 && (
            <span className="bg-orange-100 text-orange-800 text-xs px-2 py-1 rounded-full font-medium">
              {unmatchedNotes.length}
            </span>
          )}
        </h2>

        {deliveryNotes.length === 0 ? (
          <div className="text-center py-8">
            <div className="text-gray-400 mb-2">
              <svg className="w-12 h-12 mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
            </div>
            <p className="text-sm text-gray-500 mb-1">No delivery notes uploaded</p>
            <p className="text-xs text-gray-400">Upload delivery notes to see them here</p>
          </div>
        ) : unmatchedNotes.length === 0 ? (
          <div className="text-center py-8">
            <div className="text-green-400 mb-2">
              <svg className="w-12 h-12 mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
            <p className="text-sm text-gray-500 mb-1">No unmatched delivery notes</p>
            <p className="text-xs text-gray-400">All delivery notes have been matched with invoices</p>
          </div>
        ) : (
          <div className="space-y-3 max-h-[calc(100vh-200px)] overflow-y-auto pr-2 scrollbar-thin scrollbar-thumb-gray-300 scrollbar-track-gray-100">
            {unmatchedNotes.map((note) => (
              <div
                key={note.id}
                className="bg-gray-50 rounded-lg p-4 border border-gray-200 hover:border-gray-300 transition-colors duration-200 cursor-pointer"
              >
                <div className="flex justify-between items-start mb-2">
                  <span className="text-xs text-gray-500 truncate">#{note.deliveryNumber}</span>
                  <span className="text-xs text-gray-500 flex-shrink-0 ml-2">{note.deliveryDate}</span>
                </div>
                
                <div className="flex justify-between items-start">
                  <div className="flex-1 min-w-0">
                    <h3 className="text-sm font-semibold text-gray-800 truncate">{note.supplier}</h3>
                    <p className="text-xs text-gray-600 mt-1 truncate">{note.filename}</p>
                  </div>
                  <div className="flex-shrink-0 ml-3">
                    <span
                      className={`text-xs px-2 py-1 rounded-full font-medium flex items-center gap-1 ${getStatusColor(note.status)}`}
                    >
                      {getStatusIcon(note.status)}
                      {note.status}
                    </span>
                  </div>
                </div>

                {/* Show confidence if available */}
                {note.confidence && (
                  <div className="mt-2 flex items-center gap-2">
                    <span className="text-xs text-gray-500">Confidence:</span>
                    <span className={`text-xs font-medium ${
                      note.confidence >= 80 ? 'text-green-600' : 
                      note.confidence >= 60 ? 'text-yellow-600' : 'text-red-600'
                    }`}>
                      {note.confidence}%
                    </span>
                  </div>
                )}

                {/* Show parsed data summary if available */}
                {note.parsedData && (
                  <div className="mt-2 p-2 bg-white rounded border border-gray-200">
                    <div className="text-xs text-gray-600">
                      {note.parsedData.total_items && (
                        <div className="mb-1">
                          <span className="font-medium">Items:</span> {note.parsedData.total_items}
                        </div>
                      )}
                      {note.parsedData.delivery_note_number && (
                        <div className="mb-1">
                          <span className="font-medium">Note #:</span> {note.parsedData.delivery_note_number}
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}

        {/* Footer with summary */}
        <div className="mt-6 pt-4 border-t border-gray-200">
          <div className="text-xs text-gray-500 text-center">
            {deliveryNotes.length > 0 ? (
              <>
                <p>Delivery notes that haven't been matched to invoices</p>
                <p className="mt-1">Click to view details or manually match</p>
              </>
            ) : (
              <>
                <p>Upload delivery notes to see them here</p>
                <p className="mt-1">They'll appear in this sidebar when unmatched</p>
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default UnmatchedDeliveryNotesSidebar; 