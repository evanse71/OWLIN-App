import React, { useState } from 'react';
import { X, Move, Check, X as XIcon, FileText, ArrowRight } from 'lucide-react';
import { Badge } from '@/components/ui/badge';

interface StitchSegment {
  id: string;
  file_id: string;
  doc_type: string;
  supplier_guess: string;
  page_range: number[];
  confidence: number;
}

interface StitchGroup {
  id: string;
  segments: StitchSegment[];
  confidence: number;
  doc_type: string;
  supplier_guess: string;
  invoice_numbers: string[];
  dates: string[];
  reasons: string[];
}

interface StitchReviewModalProps {
  isOpen: boolean;
  onClose: () => void;
  stitchGroups: StitchGroup[];
  onConfirm: (stitchGroups: StitchGroup[]) => void;
  onReject: (stitchGroupId: string) => void;
}

export default function StitchReviewModal({
  isOpen,
  onClose,
  stitchGroups: initialStitchGroups,
  onConfirm,
  onReject
}: StitchReviewModalProps) {
  const [stitchGroups, setStitchGroups] = useState<StitchGroup[]>(initialStitchGroups);
  const [selectedGroup, setSelectedGroup] = useState<string | null>(null);
  const [dragState, setDragState] = useState<{
    isDragging: boolean;
    draggedSegmentId: string | null;
    sourceGroupId: string | null;
  }>({
    isDragging: false,
    draggedSegmentId: null,
    sourceGroupId: null
  });

  const getDocTypeColor = (docType: string) => {
    switch (docType) {
      case 'invoice': return 'bg-blue-100 text-blue-800';
      case 'delivery': return 'bg-green-100 text-green-800';
      case 'receipt': return 'bg-yellow-100 text-yellow-800';
      case 'utility': return 'bg-purple-100 text-purple-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  const handleDragStart = (e: React.DragEvent, segmentId: string, groupId: string) => {
    setDragState({
      isDragging: true,
      draggedSegmentId: segmentId,
      sourceGroupId: groupId
    });
    e.dataTransfer.setData('text/plain', segmentId);
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
  };

  const handleDrop = (e: React.DragEvent, targetGroupId: string) => {
    e.preventDefault();
    const draggedSegmentId = dragState.draggedSegmentId;
    const sourceGroupId = dragState.sourceGroupId;

    if (!draggedSegmentId || !sourceGroupId || sourceGroupId === targetGroupId) {
      setDragState({ isDragging: false, draggedSegmentId: null, sourceGroupId: null });
      return;
    }

    // Find the dragged segment
    const sourceGroup = stitchGroups.find(g => g.id === sourceGroupId);
    const segment = sourceGroup?.segments.find(s => s.id === draggedSegmentId);

    if (!segment) {
      setDragState({ isDragging: false, draggedSegmentId: null, sourceGroupId: null });
      return;
    }

    // Move segment to target group
    setStitchGroups(prev => prev.map(group => {
      if (group.id === sourceGroupId) {
        return {
          ...group,
          segments: group.segments.filter(s => s.id !== draggedSegmentId)
        };
      }
      if (group.id === targetGroupId) {
        return {
          ...group,
          segments: [...group.segments, segment]
        };
      }
      return group;
    }));

    setDragState({ isDragging: false, draggedSegmentId: null, sourceGroupId: null });
  };

  const handleConfirmGroup = (groupId: string) => {
    const group = stitchGroups.find(g => g.id === groupId);
    if (group) {
      onConfirm([group]);
    }
  };

  const handleRejectGroup = (groupId: string) => {
    onReject(groupId);
    setStitchGroups(prev => prev.filter(g => g.id !== groupId));
  };

  const handleConfirmAll = () => {
    onConfirm(stitchGroups);
    onClose();
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl max-w-6xl w-full mx-4 max-h-[90vh] overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b">
          <div>
            <h2 className="text-2xl font-bold text-gray-900">Review Stitch Groups</h2>
            <p className="text-gray-600 mt-1">
              Review and confirm cross-file stitching results. Drag segments to reorder or move between groups.
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
          {/* Left panel - Stitch groups */}
          <div className="w-2/3 border-r overflow-y-auto">
            <div className="p-4">
              <div className="flex items-center justify-between mb-4">
                <h3 className="font-semibold text-lg">
                  Stitch Groups ({stitchGroups.length})
                </h3>
                <button
                  onClick={handleConfirmAll}
                  className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors"
                >
                  Confirm All
                </button>
              </div>
              
              <div className="space-y-4">
                {stitchGroups.map((group) => (
                  <div
                    key={group.id}
                    className={`border rounded-lg p-4 transition-colors ${
                      selectedGroup === group.id
                        ? 'border-blue-500 bg-blue-50'
                        : 'border-gray-200 hover:border-gray-300'
                    }`}
                    onDragOver={handleDragOver}
                    onDrop={(e) => handleDrop(e, group.id)}
                  >
                    {/* Group header */}
                    <div className="flex items-center justify-between mb-3">
                      <div className="flex items-center space-x-3">
                        <Badge className={getDocTypeColor(group.doc_type)}>
                          {group.doc_type}
                        </Badge>
                        <span className="font-medium text-gray-900">
                          {group.supplier_guess || 'Unknown Supplier'}
                        </span>
                        <span className="text-sm text-gray-500">
                          {group.segments.length} segments
                        </span>
                      </div>
                      
                      <div className="flex items-center space-x-2">
                        <span className="text-sm text-gray-500">
                          Confidence: {Math.round(group.confidence * 100)}%
                        </span>
                        <button
                          onClick={() => handleConfirmGroup(group.id)}
                          className="p-1 text-green-600 hover:text-green-700"
                        >
                          <Check size={16} />
                        </button>
                        <button
                          onClick={() => handleRejectGroup(group.id)}
                          className="p-1 text-red-600 hover:text-red-700"
                        >
                          <XIcon size={16} />
                        </button>
                      </div>
                    </div>

                    {/* Stitch reasons */}
                    {group.reasons.length > 0 && (
                      <div className="mb-3">
                        <p className="text-sm text-gray-600">
                          <strong>Reasons:</strong> {group.reasons.join(', ')}
                        </p>
                      </div>
                    )}

                    {/* Segments */}
                    <div className="space-y-2">
                      {group.segments.map((segment, index) => (
                        <div
                          key={segment.id}
                          className={`flex items-center justify-between p-2 border rounded ${
                            dragState.draggedSegmentId === segment.id
                              ? 'opacity-50 bg-gray-100'
                              : 'bg-white'
                          }`}
                          draggable
                          onDragStart={(e) => handleDragStart(e, segment.id, group.id)}
                          onClick={() => setSelectedGroup(group.id)}
                        >
                          <div className="flex items-center space-x-3">
                            <div className="flex items-center justify-center w-6 h-6 bg-gray-200 rounded-full text-xs font-medium">
                              {index + 1}
                            </div>
                            <div>
                              <div className="text-sm font-medium">
                                {segment.supplier_guess || 'Unknown Supplier'}
                              </div>
                              <div className="text-xs text-gray-500">
                                Pages {segment.page_range.join(', ')} • {segment.doc_type}
                              </div>
                            </div>
                          </div>
                          
                          <div className="flex items-center space-x-2">
                            <span className="text-xs text-gray-500">
                              {Math.round(segment.confidence * 100)}%
                            </span>
                            <Move size={14} className="text-gray-400" />
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Right panel - Group details */}
          <div className="w-1/3 p-4">
            {selectedGroup ? (
              <div>
                <h3 className="font-semibold text-lg mb-4">Group Details</h3>
                {(() => {
                  const group = stitchGroups.find(g => g.id === selectedGroup);
                  if (!group) return null;

                  return (
                    <div className="space-y-4">
                      {/* Basic info */}
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                          Document Type
                        </label>
                        <Badge className={getDocTypeColor(group.doc_type)}>
                          {group.doc_type}
                        </Badge>
                      </div>

                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                          Supplier
                        </label>
                        <div className="px-3 py-2 bg-gray-50 border border-gray-300 rounded-md">
                          {group.supplier_guess || 'Unknown Supplier'}
                        </div>
                      </div>

                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                          Confidence
                        </label>
                        <div className="flex items-center space-x-2">
                          <div className="flex-1 bg-gray-200 rounded-full h-2">
                            <div
                              className="bg-blue-600 h-2 rounded-full"
                              style={{ width: `${group.confidence * 100}%` }}
                            />
                          </div>
                          <span className="text-sm text-gray-600">
                            {Math.round(group.confidence * 100)}%
                          </span>
                        </div>
                      </div>

                      {/* Invoice numbers */}
                      {group.invoice_numbers.length > 0 && (
                        <div>
                          <label className="block text-sm font-medium text-gray-700 mb-1">
                            Invoice Numbers
                          </label>
                          <div className="space-y-1">
                            {group.invoice_numbers.map((number, index) => (
                              <div key={index} className="px-3 py-1 bg-blue-50 border border-blue-200 rounded text-sm">
                                {number}
                              </div>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Dates */}
                      {group.dates.length > 0 && (
                        <div>
                          <label className="block text-sm font-medium text-gray-700 mb-1">
                            Dates
                          </label>
                          <div className="space-y-1">
                            {group.dates.map((date, index) => (
                              <div key={index} className="px-3 py-1 bg-green-50 border border-green-200 rounded text-sm">
                                {date}
                              </div>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Actions */}
                      <div className="flex space-x-2 pt-4">
                        <button
                          onClick={() => handleConfirmGroup(group.id)}
                          className="flex-1 px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 transition-colors"
                        >
                          Confirm Group
                        </button>
                        <button
                          onClick={() => handleRejectGroup(group.id)}
                          className="flex-1 px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 transition-colors"
                        >
                          Reject Group
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
                  <p>Select a stitch group to view details</p>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
} 