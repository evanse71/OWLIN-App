import React, { useState } from 'react';
import { TableDiff as TableDiffType, DiffRow, DiffCell } from '../../lib/recoveryClient';

interface TableDiffProps {
  diff: TableDiffType;
  onDecisionChange: (rowKey: string, decision: string) => void;
  decisions: Record<string, string>;
}

export default function TableDiff({ diff, onDecisionChange, decisions }: TableDiffProps) {
  const [expandedRows, setExpandedRows] = useState<Set<string>>(new Set());

  const toggleRowExpansion = (rowKey: string) => {
    const newExpanded = new Set(expandedRows);
    if (newExpanded.has(rowKey)) {
      newExpanded.delete(rowKey);
    } else {
      newExpanded.add(rowKey);
    }
    setExpandedRows(newExpanded);
  };

  const getCellBackground = (cell: DiffCell, op: string) => {
    if (op === 'add') {
      return 'bg-[#ECFDF5]'; // Green tint
    } else if (op === 'remove') {
      return 'bg-[#FEE2E2]'; // Red tint
    } else if (cell.changed) {
      return 'bg-[#FEF3C7]'; // Amber tint
    }
    return 'bg-white';
  };

  const getOpBadge = (op: string) => {
    const colors = {
      add: 'bg-green-100 text-green-800',
      remove: 'bg-red-100 text-red-800',
      change: 'bg-amber-100 text-amber-800',
      identical: 'bg-gray-100 text-gray-800'
    };

    return (
      <span className={`px-2 py-1 rounded text-xs font-medium ${colors[op as keyof typeof colors]}`}>
        {op.toUpperCase()}
      </span>
    );
  };

  const formatValue = (value: any) => {
    if (value === null) return 'NULL';
    if (value === undefined) return 'undefined';
    if (typeof value === 'string' && value.length > 50) {
      return value.substring(0, 50) + '...';
    }
    return String(value);
  };

  return (
    <div className="bg-white border border-[#E5E7EB] rounded-[12px] overflow-hidden">
      {/* Header */}
      <div className="bg-[#F9FAFB] px-4 py-3 border-b border-[#E5E7EB]">
        <div className="flex items-center justify-between">
          <h3 className="text-[16px] font-semibold text-[#1F2937]">
            Table: {diff.table}
          </h3>
          <div className="flex items-center gap-4 text-sm text-[#6B7280]">
            <span>Add: {diff.stats.add}</span>
            <span>Remove: {diff.stats.remove}</span>
            <span>Change: {diff.stats.change}</span>
            <span>Identical: {diff.stats.identical}</span>
          </div>
        </div>
      </div>

      {/* Table */}
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead className="bg-[#F9FAFB]">
            <tr>
              <th className="px-4 py-2 text-left text-sm font-medium text-[#374151] w-24">
                Decision
              </th>
              <th className="px-4 py-2 text-left text-sm font-medium text-[#374151] w-20">
                Op
              </th>
              <th className="px-4 py-2 text-left text-sm font-medium text-[#374151] w-32">
                Row Key
              </th>
              <th className="px-4 py-2 text-left text-sm font-medium text-[#374151] w-1/2">
                Live Data
              </th>
              <th className="px-4 py-2 text-left text-sm font-medium text-[#374151] w-1/2">
                Snapshot Data
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[#E5E7EB]">
            {diff.rows.map((row) => (
              <React.Fragment key={row.key}>
                <tr className="hover:bg-[#F9FAFB]">
                  <td className="px-4 py-2">
                    <select
                      value={decisions[row.key] || 'keep_live'}
                      onChange={(e) => onDecisionChange(row.key, e.target.value)}
                      className="text-sm border border-[#D1D5DB] rounded px-2 py-1"
                    >
                      <option value="keep_live">Keep Live</option>
                      <option value="take_snapshot">Take Snapshot</option>
                      <option value="merge">Merge</option>
                    </select>
                  </td>
                  <td className="px-4 py-2">
                    {getOpBadge(row.op)}
                  </td>
                  <td className="px-4 py-2">
                    <button
                      onClick={() => toggleRowExpansion(row.key)}
                      className="text-sm text-[#3B82F6] hover:text-[#2563EB] font-mono"
                    >
                      {row.key.length > 30 ? row.key.substring(0, 30) + '...' : row.key}
                    </button>
                  </td>
                  <td className="px-4 py-2">
                    <div className="text-sm text-[#6B7280]">
                      {row.op === 'add' ? '—' : `${row.cells.length} columns`}
                    </div>
                  </td>
                  <td className="px-4 py-2">
                    <div className="text-sm text-[#6B7280]">
                      {row.op === 'remove' ? '—' : `${row.cells.length} columns`}
                    </div>
                  </td>
                </tr>
                
                {/* Expanded row details */}
                {expandedRows.has(row.key) && (
                  <tr>
                    <td colSpan={5} className="px-4 py-2 bg-[#F9FAFB]">
                      <div className="grid grid-cols-2 gap-4">
                        <div>
                          <h4 className="text-sm font-medium text-[#374151] mb-2">Live Data</h4>
                          <div className="space-y-1">
                            {row.cells.map((cell) => (
                              <div key={cell.col} className={`p-2 rounded border ${getCellBackground(cell, row.op)}`}>
                                <div className="text-xs font-medium text-[#6B7280]">{cell.col}</div>
                                <div className="text-sm">{formatValue(cell.old)}</div>
                              </div>
                            ))}
                          </div>
                        </div>
                        <div>
                          <h4 className="text-sm font-medium text-[#374151] mb-2">Snapshot Data</h4>
                          <div className="space-y-1">
                            {row.cells.map((cell) => (
                              <div key={cell.col} className={`p-2 rounded border ${getCellBackground(cell, row.op)}`}>
                                <div className="text-xs font-medium text-[#6B7280]">{cell.col}</div>
                                <div className="text-sm">{formatValue(cell.new)}</div>
                              </div>
                            ))}
                          </div>
                        </div>
                      </div>
                    </td>
                  </tr>
                )}
              </React.Fragment>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
} 