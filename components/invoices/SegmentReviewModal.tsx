import React, { useState } from 'react';
import { X, Scissors, Type, FileText } from 'lucide-react';
import { Badge } from '@/components/ui/badge';

interface Segment {
  id: string;
  doc_type: string;
  page_range: number[];
  supplier_guess: string;
  confidence: number;
  text: string;
}

interface SegmentReviewModalProps {
  isOpen: boolean;
  onClose: () => void;
  segments: Segment[];
  onSegmentsUpdate: (segments: Segment[]) => void;
  onConfirm: (segments: Segment[]) => void;
}

export default function SegmentReviewModal({
  isOpen,
  onClose,
  segments: initialSegments,
  onSegmentsUpdate,
  onConfirm
}: SegmentReviewModalProps) {
  const [segments, setSegments] = useState<Segment[]>(initialSegments);
  const [selectedSegment, setSelectedSegment] = useState<string | null>(null);
  const [editingSegment, setEditingSegment] = useState<Segment | null>(null);

  const getDocTypeColor = (docType: string) => {
    switch (docType) {
      case 'invoice': return 'bg-blue-100 text-blue-800';
      case 'delivery': return 'bg-green-100 text-green-800';
      case 'receipt': return 'bg-yellow-100 text-yellow-800';
      case 'utility': return 'bg-purple-100 text-purple-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  const handleSegmentSplit = (segmentId: string, splitPage: number) => {
    const targetSegment = segments.find(s => s.id === segmentId);
    if (!targetSegment) return;

    const beforePages = targetSegment.page_range.filter(p => p < splitPage);
    const afterPages = targetSegment.page_range.filter(p => p >= splitPage);

    if (beforePages.length === 0 || afterPages.length === 0) return;

    const newSegments = segments.filter(s => s.id !== segmentId);
    
    const beforeSegment: Segment = {
      ...targetSegment,
      id: `${targetSegment.id}_before`,
      page_range: beforePages,
      text: `Split from ${targetSegment.id} - Pages ${beforePages.join(', ')}`
    };

    const afterSegment: Segment = {
      ...targetSegment,
      id: `${targetSegment.id}_after`,
      page_range: afterPages,
      text: `Split from ${targetSegment.id} - Pages ${afterPages.join(', ')}`
    };

    setSegments([...newSegments, beforeSegment, afterSegment]);
  };

  const handleSegmentTypeChange = (segmentId: string, newType: string) => {
    setSegments(prev => prev.map(s => 
      s.id === segmentId ? { ...s, doc_type: newType } : s
    ));
  };

  const handleConfirm = () => {
    onSegmentsUpdate(segments);
    onConfirm(segments);
    onClose();
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl max-w-4xl w-full mx-4 max-h-[90vh] overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b">
          <div>
            <h2 className="text-2xl font-bold text-gray-900">Review Document Segments</h2>
            <p className="text-gray-600 mt-1">
              Review and edit the automatically detected document segments
            </p>
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 transition-colors"
          >
            <X size={24} />
          </button>
        </div>

        {/* Content */}
        <div className="flex h-[70vh]">
          {/* Left panel - Segment list */}
          <div className="w-1/2 border-r overflow-y-auto">
            <div className="p-4">
              <h3 className="font-semibold text-lg mb-4">Segments ({segments.length})</h3>
              <div className="space-y-3">
                {segments.map((segment) => (
                  <div
                    key={segment.id}
                    className={`p-4 border rounded-lg cursor-pointer transition-colors ${
                      selectedSegment === segment.id
                        ? 'border-blue-500 bg-blue-50'
                        : 'border-gray-200 hover:border-gray-300'
                    }`}
                    onClick={() => setSelectedSegment(segment.id)}
                  >
                    <div className="flex items-center justify-between mb-2">
                      <Badge className={getDocTypeColor(segment.doc_type)}>
                        {segment.doc_type}
                      </Badge>
                      <div className="text-sm text-gray-500">
                        Pages {segment.page_range.join(', ')}
                      </div>
                    </div>
                    
                    <div className="text-sm font-medium text-gray-900 mb-1">
                      {segment.supplier_guess || 'Unknown Supplier'}
                    </div>
                    
                    <div className="flex items-center justify-between">
                      <div className="text-xs text-gray-500">
                        Confidence: {Math.round(segment.confidence * 100)}%
                      </div>
                      <div className="flex space-x-2">
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            setEditingSegment(segment);
                          }}
                          className="p-1 text-gray-400 hover:text-blue-600"
                        >
                          <Type size={16} />
                        </button>
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            if (segment.page_range.length > 1) {
                              const splitPage = segment.page_range[Math.floor(segment.page_range.length / 2)];
                              handleSegmentSplit(segment.id, splitPage);
                            }
                          }}
                          className="p-1 text-gray-400 hover:text-orange-600"
                        >
                          <Scissors size={16} />
                        </button>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Right panel - Segment details */}
          <div className="w-1/2 p-4">
            {selectedSegment ? (
              <div>
                <h3 className="font-semibold text-lg mb-4">Segment Details</h3>
                {(() => {
                  const segment = segments.find(s => s.id === selectedSegment);
                  if (!segment) return null;

                  return (
                    <div className="space-y-4">
                      {/* Basic info */}
                      <div className="grid grid-cols-2 gap-4">
                        <div>
                          <label className="block text-sm font-medium text-gray-700 mb-1">
                            Document Type
                          </label>
                          <select
                            value={segment.doc_type}
                            onChange={(e) => handleSegmentTypeChange(segment.id, e.target.value)}
                            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                          >
                            <option value="invoice">Invoice</option>
                            <option value="delivery">Delivery Note</option>
                            <option value="receipt">Receipt</option>
                            <option value="utility">Utility Bill</option>
                            <option value="other">Other</option>
                          </select>
                        </div>
                        
                        <div>
                          <label className="block text-sm font-medium text-gray-700 mb-1">
                            Page Range
                          </label>
                          <div className="px-3 py-2 bg-gray-50 border border-gray-300 rounded-md">
                            {segment.page_range.join(', ')}
                          </div>
                        </div>
                      </div>

                      {/* Supplier */}
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                          Supplier
                        </label>
                        <input
                          type="text"
                          value={segment.supplier_guess || ''}
                          onChange={(e) => {
                            setSegments(prev => prev.map(s => 
                              s.id === segment.id ? { ...s, supplier_guess: e.target.value } : s
                            ));
                          }}
                          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                          placeholder="Enter supplier name"
                        />
                      </div>

                      {/* Confidence */}
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                          Confidence
                        </label>
                        <div className="flex items-center space-x-2">
                          <div className="flex-1 bg-gray-200 rounded-full h-2">
                            <div
                              className="bg-blue-600 h-2 rounded-full"
                              style={{ width: `${segment.confidence * 100}%` }}
                            />
                          </div>
                          <span className="text-sm text-gray-600">
                            {Math.round(segment.confidence * 100)}%
                          </span>
                        </div>
                      </div>

                      {/* Text preview */}
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                          Text Preview
                        </label>
                        <div className="max-h-40 overflow-y-auto p-3 bg-gray-50 border border-gray-300 rounded-md text-sm">
                          {segment.text.length > 200
                            ? `${segment.text.substring(0, 200)}...`
                            : segment.text
                          }
                        </div>
                      </div>

                      {/* Actions */}
                      <div className="flex space-x-2 pt-4">
                        <button
                          onClick={() => setEditingSegment(null)}
                          className="flex-1 px-4 py-2 bg-gray-100 text-gray-700 rounded-md hover:bg-gray-200 transition-colors"
                        >
                          Cancel
                        </button>
                        <button
                          onClick={handleConfirm}
                          className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors"
                        >
                          Confirm Segments
                        </button>
                      </div>
                    </div>
                  );
                })()}
              </div>
            ) : (
              <div className="flex items-center justify-center h-full text-gray-500">
                <div className="text-center">
                  <FileText size={48} className="mx-auto mb-4 text-gray-300" />
                  <p>Select a segment to view details</p>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
} 