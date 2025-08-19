import { useState, useEffect, useCallback } from 'react';

interface QueuedUpload {
  id: string;
  file: File;
  timestamp: number;
  retryCount: number;
}

const QUEUE_STORAGE_KEY = 'owlin_offline_queue';
const MAX_RETRY_COUNT = 3;

export const useOfflineQueue = () => {
  const [queuedUploads, setQueuedUploads] = useState<QueuedUpload[]>([]);
  const [isOnline, setIsOnline] = useState(true);
  const [isProcessing, setIsProcessing] = useState(false);

  // Load queued uploads from localStorage
  useEffect(() => {
    if (typeof window !== 'undefined') {
      try {
        const stored = localStorage.getItem(QUEUE_STORAGE_KEY);
        if (stored) {
          const parsed = JSON.parse(stored);
          // Note: We can't restore File objects from localStorage, so we'll need to handle this differently
          // For now, we'll just track the metadata
          setQueuedUploads(parsed.map((item: any) => ({
            ...item,
            file: null // File objects can't be serialized
          })));
        }
      } catch (error) {
        console.warn('Failed to load offline queue:', error);
      }
    }
  }, []);

  // Monitor online/offline status
  useEffect(() => {
    const handleOnline = () => setIsOnline(true);
    const handleOffline = () => setIsOnline(false);

    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);
    setIsOnline(navigator.onLine);

    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, []);

  // Save queue to localStorage
  const saveQueue = useCallback((uploads: QueuedUpload[]) => {
    if (typeof window !== 'undefined') {
      try {
        // Convert File objects to metadata for storage
        const serializable = uploads.map(upload => ({
          id: upload.id,
          filename: upload.file.name,
          size: upload.file.size,
          type: upload.file.type,
          timestamp: upload.timestamp,
          retryCount: upload.retryCount
        }));
        localStorage.setItem(QUEUE_STORAGE_KEY, JSON.stringify(serializable));
      } catch (error) {
        console.warn('Failed to save offline queue:', error);
      }
    }
  }, []);

  // Add file to queue
  const addToQueue = useCallback((file: File) => {
    const upload: QueuedUpload = {
      id: `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
      file,
      timestamp: Date.now(),
      retryCount: 0
    };

    setQueuedUploads(prev => {
      const newQueue = [...prev, upload];
      saveQueue(newQueue);
      return newQueue;
    });

    return upload.id;
  }, [saveQueue]);

  // Remove file from queue
  const removeFromQueue = useCallback((id: string) => {
    setQueuedUploads(prev => {
      const newQueue = prev.filter(upload => upload.id !== id);
      saveQueue(newQueue);
      return newQueue;
    });
  }, [saveQueue]);

  // Process queue when online
  const processQueue = useCallback(async (uploadHandler: (files: File[]) => Promise<void>) => {
    if (!isOnline || isProcessing || queuedUploads.length === 0) {
      return;
    }

    setIsProcessing(true);

    try {
      const uploadsToProcess = [...queuedUploads];
      const successful: string[] = [];
      const failed: string[] = [];

      for (const upload of uploadsToProcess) {
        try {
          // Note: In a real implementation, you'd need to handle the fact that File objects
          // can't be restored from localStorage. You might need to:
          // 1. Store files in IndexedDB
          // 2. Use a different approach for offline storage
          // 3. Prompt user to re-select files when coming back online
          
          if (upload.file) {
            await uploadHandler([upload.file]);
            successful.push(upload.id);
          } else {
            // File object was lost, mark as failed
            failed.push(upload.id);
          }
        } catch (error) {
          console.error(`Failed to process upload ${upload.id}:`, error);
          
          if (upload.retryCount < MAX_RETRY_COUNT) {
            // Increment retry count
            setQueuedUploads(prev => {
              const newQueue = prev.map(u => 
                u.id === upload.id 
                  ? { ...u, retryCount: u.retryCount + 1 }
                  : u
              );
              saveQueue(newQueue);
              return newQueue;
            });
          } else {
            // Max retries reached, mark as failed
            failed.push(upload.id);
          }
        }
      }

      // Remove successful uploads from queue
      successful.forEach(id => removeFromQueue(id));
      
      // Remove failed uploads (max retries reached)
      failed.forEach(id => removeFromQueue(id));

      return {
        successful: successful.length,
        failed: failed.length
      };

    } finally {
      setIsProcessing(false);
    }
  }, [isOnline, isProcessing, queuedUploads, removeFromQueue, saveQueue]);

  // Clear entire queue
  const clearQueue = useCallback(() => {
    setQueuedUploads([]);
    if (typeof window !== 'undefined') {
      localStorage.removeItem(QUEUE_STORAGE_KEY);
    }
  }, []);

  // Get queue statistics
  const queueStats = {
    total: queuedUploads.length,
    pending: queuedUploads.filter(u => u.retryCount === 0).length,
    retrying: queuedUploads.filter(u => u.retryCount > 0 && u.retryCount < MAX_RETRY_COUNT).length,
    failed: queuedUploads.filter(u => u.retryCount >= MAX_RETRY_COUNT).length,
    isOnline,
    isProcessing
  };

  return {
    queuedUploads,
    addToQueue,
    removeFromQueue,
    processQueue,
    clearQueue,
    queueStats,
    isOnline,
    isProcessing
  };
}; 