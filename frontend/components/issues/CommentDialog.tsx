import React, { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';

interface CommentDialogProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: (comment: string) => void;
  selectedCount: number;
  isLoading?: boolean;
}

export default function CommentDialog({
  isOpen,
  onClose,
  onConfirm,
  selectedCount,
  isLoading = false
}: CommentDialogProps) {
  const [comment, setComment] = useState('');

  const handleConfirm = () => {
    if (comment.trim()) {
      onConfirm(comment.trim());
    }
  };

  const handleClose = () => {
    setComment('');
    onClose();
  };

  const isConfirmDisabled = !comment.trim() || isLoading;
  const charCount = comment.length;
  const maxChars = 4000;
  const isOverLimit = charCount > maxChars;

  return (
    <Dialog open={isOpen} onOpenChange={handleClose}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Comment on {selectedCount} Issue{selectedCount !== 1 ? 's' : ''}</DialogTitle>
        </DialogHeader>
        
        <div className="space-y-4">
          <div>
            <Label htmlFor="comment" className="text-sm font-medium">
              Comment
            </Label>
            <Textarea
              id="comment"
              value={comment}
              onChange={(e) => setComment(e.target.value)}
              placeholder="Add a comment to these issues..."
              maxLength={maxChars}
              className="mt-1"
              rows={6}
            />
            <div className={`text-xs mt-1 ${
              isOverLimit ? 'text-red-500' : 'text-gray-500'
            }`}>
              {charCount}/{maxChars} characters
              {isOverLimit && ' (over limit)'}
            </div>
          </div>

          <div className="flex justify-end space-x-2 pt-4">
            <Button variant="outline" onClick={handleClose} disabled={isLoading}>
              Cancel
            </Button>
            <Button 
              onClick={handleConfirm} 
              disabled={isConfirmDisabled}
              className="bg-green-600 hover:bg-green-700"
            >
              {isLoading ? 'Adding Comment...' : 'Add Comment'}
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
} 