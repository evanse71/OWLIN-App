import React from 'react';
import { Button } from '@/components/ui/button';
import { CheckCircle, XCircle, AlertTriangle, UserPlus, MessageSquare } from 'lucide-react';

interface BulkActionBarProps {
  selectedCount: number;
  userRole: 'gm' | 'finance' | 'shift_lead';
  onResolve: () => void;
  onDismiss: () => void;
  onEscalate: () => void;
  onAssign: () => void;
  onComment: () => void;
  onClearSelection: () => void;
  isLoading?: boolean;
}

export default function BulkActionBar({
  selectedCount,
  userRole,
  onResolve,
  onDismiss,
  onEscalate,
  onAssign,
  onComment,
  onClearSelection,
  isLoading = false
}: BulkActionBarProps) {
  if (selectedCount === 0) return null;

  const canResolve = userRole === 'gm' || userRole === 'finance';
  const canEscalate = userRole === 'gm';
  const canAssign = userRole === 'gm' || userRole === 'finance';
  const canComment = userRole === 'gm' || userRole === 'finance' || userRole === 'shift_lead';

  return (
    <div className="fixed bottom-0 left-0 right-0 z-40 bg-white border-t border-gray-200 shadow-lg">
      <div className="max-w-7xl mx-auto px-4 py-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <div className="flex items-center space-x-2">
              <span className="text-sm font-medium text-gray-900">
                {selectedCount} selected
              </span>
              <button
                onClick={onClearSelection}
                className="text-gray-400 hover:text-gray-600 transition-colors"
                title="Clear selection"
              >
                <XCircle className="w-4 h-4" />
              </button>
            </div>
          </div>

          <div className="flex items-center space-x-2">
            <Button
              variant="outline"
              size="sm"
              onClick={onResolve}
              disabled={!canResolve || isLoading}
              className="flex items-center space-x-1"
            >
              <CheckCircle className="w-4 h-4" />
              <span>Resolve</span>
            </Button>

            <Button
              variant="outline"
              size="sm"
              onClick={onDismiss}
              disabled={!canResolve || isLoading}
              className="flex items-center space-x-1"
            >
              <XCircle className="w-4 h-4" />
              <span>Dismiss</span>
            </Button>

            <Button
              variant="outline"
              size="sm"
              onClick={onEscalate}
              disabled={!canEscalate || isLoading}
              className="flex items-center space-x-1"
            >
              <AlertTriangle className="w-4 h-4" />
              <span>Escalate</span>
            </Button>

            <Button
              variant="outline"
              size="sm"
              onClick={onAssign}
              disabled={!canAssign || isLoading}
              className="flex items-center space-x-1"
            >
              <UserPlus className="w-4 h-4" />
              <span>Assign</span>
            </Button>

            <Button
              variant="outline"
              size="sm"
              onClick={onComment}
              disabled={!canComment || isLoading}
              className="flex items-center space-x-1"
            >
              <MessageSquare className="w-4 h-4" />
              <span>Comment</span>
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
} 