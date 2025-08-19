export interface RecoveryStatus {
  state: 'normal' | 'degraded' | 'recovery' | 'restore_pending';
  reason?: string;
  details: string[];
  snapshots: SnapshotInfo[];
  live_db_hash: string;
  schema_version: number;
  app_version: string;
}

export interface SnapshotInfo {
  id: string;
  size_bytes: number;
  created_at: string;
  manifest_ok: boolean;
}

export interface RestorePreview {
  snapshot: SnapshotInfo;
  tables: any[];
  summary: {
    rows_add: number;
    rows_remove: number;
    rows_change: number;
  };
}

export interface TableDiff {
  table: string;
  pk: string[];
  stats: {
    add: number;
    remove: number;
    change: number;
    identical: number;
  };
  rows: DiffRow[];
}

export interface DiffRow {
  key: string;
  op: 'add' | 'remove' | 'change' | 'identical';
  cells: DiffCell[];
}

export interface DiffCell {
  col: string;
  old: any;
  new: any;
  changed: boolean;
}

export interface ResolvePlan {
  snapshot_id: string;
  decisions: Record<string, Record<string, string>>;
  merge_fields?: Record<string, Record<string, Record<string, string>>>;
}

export interface RestoreCommitResponse {
  ok: boolean;
  restore_id: string;
}

class RecoveryClient {
  private baseUrl = '/api/recovery';

  async getStatus(): Promise<RecoveryStatus> {
    try {
      const response = await fetch(`${this.baseUrl}/status`);
      if (!response.ok) {
        throw new Error('Failed to get recovery status');
      }
      return await response.json();
    } catch (error) {
      console.error('Error getting recovery status:', error);
      throw error;
    }
  }

  async scanSystem(): Promise<RecoveryStatus> {
    try {
      const response = await fetch(`${this.baseUrl}/scan`, {
        method: 'POST',
      });
      if (!response.ok) {
        throw new Error('Failed to scan system');
      }
      return await response.json();
    } catch (error) {
      console.error('Error scanning system:', error);
      throw error;
    }
  }

  async previewRestore(snapshotId: string, limit: number = 200, offset: number = 0): Promise<RestorePreview> {
    try {
      const response = await fetch(`${this.baseUrl}/preview?snapshot_id=${snapshotId}&limit=${limit}&offset=${offset}`, {
        method: 'POST',
      });
      if (!response.ok) {
        throw new Error('Failed to create restore preview');
      }
      return await response.json();
    } catch (error) {
      console.error('Error creating restore preview:', error);
      throw error;
    }
  }

  async getTableDiff(table: string, snapshotId: string, limit: number = 200, offset: number = 0): Promise<TableDiff> {
    try {
      const response = await fetch(
        `${this.baseUrl}/diff/${table}?snapshot_id=${snapshotId}&limit=${limit}&offset=${offset}`
      );
      if (!response.ok) {
        throw new Error('Failed to get table diff');
      }
      return await response.json();
    } catch (error) {
      console.error('Error getting table diff:', error);
      throw error;
    }
  }

  async commitRestore(resolvePlan: ResolvePlan): Promise<RestoreCommitResponse> {
    try {
      const response = await fetch(`${this.baseUrl}/commit`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(resolvePlan),
      });
      if (!response.ok) {
        throw new Error('Failed to commit restore');
      }
      return await response.json();
    } catch (error) {
      console.error('Error committing restore:', error);
      throw error;
    }
  }

  async rollbackToSnapshot(snapshotId: string): Promise<{ ok: boolean; message: string }> {
    try {
      const response = await fetch(`${this.baseUrl}/rollback/${snapshotId}`, {
        method: 'POST',
      });
      if (!response.ok) {
        throw new Error('Failed to rollback to snapshot');
      }
      return await response.json();
    } catch (error) {
      console.error('Error rolling back to snapshot:', error);
      throw error;
    }
  }
}

export const recoveryClient = new RecoveryClient(); 