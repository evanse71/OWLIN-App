import React, { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';

interface EscalateDialogProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: (toRole: 'gm' | 'finance', reason?: string) => void;
  selectedCount: number;
  isLoading?: boolean;
}

export default function EscalateDialog({
  isOpen,
  onClose,
  onConfirm,
  selectedCount,
  isLoading = false
}: EscalateDialogProps) {
  const [toRole, setToRole] = useState<'gm' | 'finance' | ''>('');
  const [reason, setReason] = useState('');

  const handleConfirm = () => {
    if (toRole) {
      onConfirm(toRole as 'gm' | 'finance', reason.trim() || undefined);
    }
  };

  const handleClose = () => {
    setToRole('');
    setReason('');
    onClose();
  };

  const isConfirmDisabled = !toRole || isLoading;

  return (
    <Dialog open={isOpen} onOpenChange={handleClose}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Escalate {selectedCount} Issue{selectedCount !== 1 ? 's' : ''}</DialogTitle>
        </DialogHeader>
        
        <div className="space-y-4">
          <div>
            <Label className="text-sm font-medium">Escalate to:</Label>
            <div className="space-y-2 mt-2">
              <div className="flex items-center space-x-2">
                <input
                  type="radio"
                  id="gm"
                  name="toRole"
                  value="gm"
                  checked={toRole === 'gm'}
                  onChange={(e) => setToRole(e.target.value as 'gm' | 'finance')}
                  className="w-4 h-4 text-amber-600"
                />
                <Label htmlFor="gm">General Manager</Label>
              </div>
              <div className="flex items-center space-x-2">
                <input
                  type="radio"
                  id="finance"
                  name="toRole"
                  value="finance"
                  checked={toRole === 'finance'}
                  onChange={(e) => setToRole(e.target.value as 'gm' | 'finance')}
                  className="w-4 h-4 text-amber-600"
                />
                <Label htmlFor="finance">Finance</Label>
              </div>
            </div>
          </div>

          <div>
            <Label htmlFor="reason" className="text-sm font-medium">
              Reason (optional)
            </Label>
            <Textarea
              id="reason"
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              placeholder="Brief explanation for escalation..."
              maxLength={250}
              className="mt-1"
              rows={3}
            />
            <div className="text-xs text-gray-500 mt-1">
              {reason.length}/250 characters
            </div>
          </div>

          <div className="flex justify-end space-x-2 pt-4">
            <Button variant="outline" onClick={handleClose} disabled={isLoading}>
              Cancel
            </Button>
            <Button 
              onClick={handleConfirm} 
              disabled={isConfirmDisabled}
              className="bg-amber-600 hover:bg-amber-700"
            >
              {isLoading ? 'Escalating...' : 'Escalate'}
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
} 