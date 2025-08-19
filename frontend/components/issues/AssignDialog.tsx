import React, { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Label } from '@/components/ui/label';
import { Search, User } from 'lucide-react';

interface User {
  id: string;
  name: string;
  role: string;
  email: string;
}

interface AssignDialogProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: (assigneeId: string) => void;
  selectedCount: number;
  isLoading?: boolean;
}

export default function AssignDialog({
  isOpen,
  onClose,
  onConfirm,
  selectedCount,
  isLoading = false
}: AssignDialogProps) {
  const [users, setUsers] = useState<User[]>([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedUserId, setSelectedUserId] = useState<string>('');
  const [loadingUsers, setLoadingUsers] = useState(false);

  useEffect(() => {
    if (isOpen) {
      fetchUsers();
    }
  }, [isOpen]);

  const fetchUsers = async () => {
    setLoadingUsers(true);
    try {
      const response = await fetch('/api/users');
      if (response.ok) {
        const data = await response.json();
        setUsers(data.users || []);
      }
    } catch (error) {
      console.error('Error fetching users:', error);
    } finally {
      setLoadingUsers(false);
    }
  };

  const filteredUsers = users.filter(user =>
    user.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    user.email.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const handleConfirm = () => {
    if (selectedUserId) {
      onConfirm(selectedUserId);
    }
  };

  const handleClose = () => {
    setSelectedUserId('');
    setSearchTerm('');
    onClose();
  };

  const isConfirmDisabled = !selectedUserId || isLoading;

  return (
    <Dialog open={isOpen} onOpenChange={handleClose}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Assign {selectedCount} Issue{selectedCount !== 1 ? 's' : ''}</DialogTitle>
        </DialogHeader>
        
        <div className="space-y-4">
          <div>
            <Label htmlFor="search" className="text-sm font-medium">Search users:</Label>
            <div className="relative mt-1">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4" />
              <input
                id="search"
                type="text"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                placeholder="Search by name or email..."
                className="w-full pl-10 pr-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
          </div>

          <div className="max-h-60 overflow-y-auto border border-gray-200 rounded-md">
            {loadingUsers ? (
              <div className="p-4 text-center text-gray-500">Loading users...</div>
            ) : filteredUsers.length === 0 ? (
              <div className="p-4 text-center text-gray-500">
                {searchTerm ? 'No users found' : 'No users available'}
              </div>
            ) : (
              <div className="divide-y divide-gray-200">
                {filteredUsers.map((user) => (
                  <div
                    key={user.id}
                    className={`p-3 cursor-pointer hover:bg-gray-50 transition-colors ${
                      selectedUserId === user.id ? 'bg-blue-50 border-l-4 border-blue-500' : ''
                    }`}
                    onClick={() => setSelectedUserId(user.id)}
                  >
                    <div className="flex items-center space-x-3">
                      <div className="w-8 h-8 bg-gray-200 rounded-full flex items-center justify-center">
                        <User className="w-4 h-4 text-gray-600" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="text-sm font-medium text-gray-900 truncate">
                          {user.name}
                        </div>
                        <div className="text-xs text-gray-500 truncate">
                          {user.email}
                        </div>
                        <div className="text-xs text-gray-400 capitalize">
                          {user.role}
                        </div>
                      </div>
                      {selectedUserId === user.id && (
                        <div className="w-4 h-4 bg-blue-500 rounded-full flex items-center justify-center">
                          <div className="w-2 h-2 bg-white rounded-full"></div>
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div className="flex justify-end space-x-2 pt-4">
            <Button variant="outline" onClick={handleClose} disabled={isLoading}>
              Cancel
            </Button>
            <Button 
              onClick={handleConfirm} 
              disabled={isConfirmDisabled}
              className="bg-blue-600 hover:bg-blue-700"
            >
              {isLoading ? 'Assigning...' : 'Assign'}
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
} 