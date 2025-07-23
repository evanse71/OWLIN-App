import React from 'react';
import DocumentCard from './DocumentCard';
import { FileStatus, Invoice, DeliveryNote } from '@/services/api';

interface DocumentSectionProps {
  title: string;
  icon: string;
  documents: (FileStatus | Invoice | DeliveryNote)[];
  emptyMessage: string;
  onDocumentClick?: (document: FileStatus | Invoice | DeliveryNote) => void;
  onRetry?: (document: FileStatus | Invoice | DeliveryNote) => void;
  onCancel?: (document: FileStatus | Invoice | DeliveryNote) => void;
}

const DocumentSection: React.FC<DocumentSectionProps> = ({
  title,
  icon,
  documents,
  emptyMessage,
  onDocumentClick,
  onRetry,
  onCancel,
}) => {
  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
      <div className="flex items-center mb-4">
        <span className="text-2xl mr-3">{icon}</span>
        <h2 className="text-lg font-semibold text-gray-900">
          {title} ({documents.length})
        </h2>
      </div>

      {documents.length === 0 ? (
        <div className="text-center py-8">
          <p className="text-gray-500 text-sm">{emptyMessage}</p>
        </div>
      ) : (
        <div className="space-y-3 max-h-96 overflow-y-auto">
          {documents.map((document, index) => (
            <DocumentCard
              key={'id' in document ? document.id : `file-${(document as FileStatus).original_filename || index}`}
              document={document}
              onClick={() => onDocumentClick?.(document)}
              onRetry={() => onRetry?.(document)}
              onCancel={() => onCancel?.(document)}
            />
          ))}
        </div>
      )}
    </div>
  );
};

export default DocumentSection; 