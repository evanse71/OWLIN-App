interface QueuedAction {
  id: string;
  actionType: 'bulk-update' | 'bulk-escalate' | 'bulk-assign' | 'bulk-comment';
  payload: any;
  timestamp: string;
  retryCount: number;
}

class OfflineQueue {
  private readonly STORAGE_KEY = 'owlin_offline_queue';
  private readonly MAX_RETRIES = 3;
  private isOnline = navigator.onLine;

  constructor() {
    this.setupOnlineOfflineListeners();
  }

  private setupOnlineOfflineListeners() {
    window.addEventListener('online', () => {
      this.isOnline = true;
      this.processQueue();
    });

    window.addEventListener('offline', () => {
      this.isOnline = false;
    });
  }

  private getQueue(): QueuedAction[] {
    try {
      const stored = localStorage.getItem(this.STORAGE_KEY);
      return stored ? JSON.parse(stored) : [];
    } catch (error) {
      console.error('Error reading offline queue:', error);
      return [];
    }
  }

  private saveQueue(queue: QueuedAction[]) {
    try {
      localStorage.setItem(this.STORAGE_KEY, JSON.stringify(queue));
    } catch (error) {
      console.error('Error saving offline queue:', error);
    }
  }

  async addToQueue(actionType: QueuedAction['actionType'], payload: any): Promise<string> {
    const action: QueuedAction = {
      id: crypto.randomUUID(),
      actionType,
      payload,
      timestamp: new Date().toISOString(),
      retryCount: 0
    };

    const queue = this.getQueue();
    queue.push(action);
    this.saveQueue(queue);

    // If online, try to process immediately
    if (this.isOnline) {
      this.processQueue();
    }

    return action.id;
  }

  private async processQueue() {
    if (!this.isOnline) return;

    const queue = this.getQueue();
    if (queue.length === 0) return;

    const actionsToProcess = [...queue];
    const successfulActions: string[] = [];
    const failedActions: QueuedAction[] = [];

    for (const action of actionsToProcess) {
      try {
        await this.processAction(action);
        successfulActions.push(action.id);
      } catch (error) {
        console.error(`Failed to process action ${action.id}:`, error);
        action.retryCount++;
        
        if (action.retryCount >= this.MAX_RETRIES) {
          failedActions.push(action);
        }
      }
    }

    // Remove successful actions and failed actions that exceeded retry limit
    const remainingQueue = queue.filter(
      action => !successfulActions.includes(action.id) && 
                !failedActions.some(failed => failed.id === action.id)
    );
    
    this.saveQueue(remainingQueue);

    // Notify about results
    if (successfulActions.length > 0) {
      this.notifySuccess(successfulActions.length);
    }

    if (failedActions.length > 0) {
      this.notifyFailure(failedActions.length);
    }
  }

  private async processAction(action: QueuedAction): Promise<void> {
    const endpoint = this.getEndpointForAction(action.actionType);
    
    const response = await fetch(endpoint, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(action.payload),
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    const result = await response.json();
    if (!result.ok) {
      throw new Error(result.message || 'Action failed');
    }
  }

  private getEndpointForAction(actionType: QueuedAction['actionType']): string {
    switch (actionType) {
      case 'bulk-update':
        return '/api/flagged-issues/bulk-update';
      case 'bulk-escalate':
        return '/api/flagged-issues/bulk-escalate';
      case 'bulk-assign':
        return '/api/flagged-issues/bulk-assign';
      case 'bulk-comment':
        return '/api/flagged-issues/bulk-comment';
      default:
        throw new Error(`Unknown action type: ${actionType}`);
    }
  }

  private notifySuccess(count: number) {
    // Dispatch custom event for toast notification
    window.dispatchEvent(new CustomEvent('offlineQueueSuccess', {
      detail: { count, message: `${count} queued actions synced successfully` }
    }));
  }

  private notifyFailure(count: number) {
    // Dispatch custom event for toast notification
    window.dispatchEvent(new CustomEvent('offlineQueueFailure', {
      detail: { count, message: `${count} actions failed after retries` }
    }));
  }

  getQueueLength(): number {
    return this.getQueue().length;
  }

  clearQueue(): void {
    this.saveQueue([]);
  }

  isOnlineStatus(): boolean {
    return this.isOnline;
  }
}

// Export singleton instance
export const offlineQueue = new OfflineQueue();
export default offlineQueue; 