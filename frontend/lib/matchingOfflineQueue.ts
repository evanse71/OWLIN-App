interface QueuedMatchAction {
  id: string;
  actionType: "confirm" | "reject";
  invoiceId: string;
  deliveryNoteId: string;
  timestamp: string;
  retryCount: number;
}

class MatchingOfflineQueue {
  private readonly STORAGE_KEY = 'owlin_matching_offline_queue';
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

  private getQueue(): QueuedMatchAction[] {
    try {
      const stored = localStorage.getItem(this.STORAGE_KEY);
      return stored ? JSON.parse(stored) : [];
    } catch (error) {
      console.error('Error reading matching offline queue:', error);
      return [];
    }
  }

  private saveQueue(queue: QueuedMatchAction[]) {
    try {
      localStorage.setItem(this.STORAGE_KEY, JSON.stringify(queue));
    } catch (error) {
      console.error('Error saving matching offline queue:', error);
    }
  }

  async addToQueue(actionType: QueuedMatchAction['actionType'], invoiceId: string, deliveryNoteId: string): Promise<string> {
    const action: QueuedMatchAction = {
      id: crypto.randomUUID(),
      actionType,
      invoiceId,
      deliveryNoteId,
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
    const failedActions: QueuedMatchAction[] = [];

    for (const action of actionsToProcess) {
      try {
        await this.processAction(action);
        successfulActions.push(action.id);
      } catch (error) {
        console.error(`Failed to process matching action ${action.id}:`, error);
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

  private async processAction(action: QueuedMatchAction): Promise<void> {
    const endpoint = this.getEndpointForAction(action.actionType);
    
    const response = await fetch(endpoint, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        invoice_id: action.invoiceId,
        delivery_note_id: action.deliveryNoteId
      }),
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    const result = await response.json();
    if (result.status !== 'confirmed' && result.status !== 'rejected') {
      throw new Error('Action failed');
    }
  }

  private getEndpointForAction(actionType: QueuedMatchAction['actionType']): string {
    switch (actionType) {
      case 'confirm':
        return '/api/matching/confirm';
      case 'reject':
        return '/api/matching/reject';
      default:
        throw new Error(`Unknown action type: ${actionType}`);
    }
  }

  private notifySuccess(count: number) {
    // Dispatch custom event for toast notification
    window.dispatchEvent(new CustomEvent('matchingOfflineQueueSuccess', {
      detail: { count, message: `${count} match actions synced successfully` }
    }));
  }

  private notifyFailure(count: number) {
    // Dispatch custom event for toast notification
    window.dispatchEvent(new CustomEvent('matchingOfflineQueueFailure', {
      detail: { count, message: `${count} match actions failed after retries` }
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
export const matchingOfflineQueue = new MatchingOfflineQueue();
export default matchingOfflineQueue; 