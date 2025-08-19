import React, { useState } from 'react';
import { DownloadIcon, CalendarIcon } from '../icons';

interface AuditLogExportProps {
  onExport: (timeframe: string, fromDate?: string, toDate?: string) => void;
}

const AuditLogExport: React.FC<AuditLogExportProps> = ({ onExport }) => {
  const [isOpen, setIsOpen] = useState(false);
  const [timeframe, setTimeframe] = useState('today');
  const [customFrom, setCustomFrom] = useState('');
  const [customTo, setCustomTo] = useState('');

  const handleExport = () => {
    let fromDate: string | undefined;
    let toDate: string | undefined;

    if (timeframe === 'custom') {
      fromDate = customFrom;
      toDate = customTo;
    } else {
      const now = new Date();
      switch (timeframe) {
        case 'today':
          fromDate = now.toISOString().split('T')[0];
          toDate = now.toISOString().split('T')[0];
          break;
        case 'week':
          const weekAgo = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);
          fromDate = weekAgo.toISOString().split('T')[0];
          toDate = now.toISOString().split('T')[0];
          break;
        case 'month':
          const monthAgo = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000);
          fromDate = monthAgo.toISOString().split('T')[0];
          toDate = now.toISOString().split('T')[0];
          break;
      }
    }

    onExport(timeframe, fromDate, toDate);
    setIsOpen(false);
  };

  const getTimeframeLabel = () => {
    switch (timeframe) {
      case 'today':
        return 'Today';
      case 'week':
        return 'This Week';
      case 'month':
        return 'This Month';
      case 'custom':
        return 'Custom Range';
      default:
        return 'Today';
    }
  };

  return (
    <div className="relative">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="bg-white border border-[#E5E7EB] hover:bg-[#F9FAFB] text-[#374151] rounded-[8px] px-3 py-1.5 text-[13px] font-medium transition-colors flex items-center gap-2"
      >
        <DownloadIcon className="w-4 h-4" />
        Export Log
      </button>

      {isOpen && (
        <div className="absolute top-full right-0 mt-2 w-80 bg-white rounded-[12px] border border-[#E5E7EB] shadow-lg p-4 z-50">
          <h3 className="text-[14px] font-semibold text-[#1F2937] mb-3">Export Audit Log</h3>
          
          <div className="space-y-3">
            {/* Timeframe Selection */}
            <div>
              <label className="block text-[12px] text-[#6B7280] mb-2">Timeframe</label>
              <select
                value={timeframe}
                onChange={(e) => setTimeframe(e.target.value)}
                className="w-full px-3 py-2 rounded-[8px] border border-[#E5E7EB] text-[13px] focus:outline-none focus:ring-2 focus:ring-[#2563EB] focus:border-transparent"
              >
                <option value="today">Today</option>
                <option value="week">This Week</option>
                <option value="month">This Month</option>
                <option value="custom">Custom Range</option>
              </select>
            </div>

            {/* Custom Date Range */}
            {timeframe === 'custom' && (
              <div className="space-y-2">
                <div>
                  <label className="block text-[12px] text-[#6B7280] mb-1">From</label>
                  <input
                    type="date"
                    value={customFrom}
                    onChange={(e) => setCustomFrom(e.target.value)}
                    className="w-full px-3 py-2 rounded-[8px] border border-[#E5E7EB] text-[13px] focus:outline-none focus:ring-2 focus:ring-[#2563EB] focus:border-transparent"
                  />
                </div>
                <div>
                  <label className="block text-[12px] text-[#6B7280] mb-1">To</label>
                  <input
                    type="date"
                    value={customTo}
                    onChange={(e) => setCustomTo(e.target.value)}
                    className="w-full px-3 py-2 rounded-[8px] border border-[#E5E7EB] text-[13px] focus:outline-none focus:ring-2 focus:ring-[#2563EB] focus:border-transparent"
                  />
                </div>
              </div>
            )}

            {/* Export Options */}
            <div>
              <label className="block text-[12px] text-[#6B7280] mb-2">Include</label>
              <div className="space-y-2">
                <label className="flex items-center">
                  <input type="checkbox" defaultChecked className="mr-2" />
                  <span className="text-[13px] text-[#374151]">Invoice uploads</span>
                </label>
                <label className="flex items-center">
                  <input type="checkbox" defaultChecked className="mr-2" />
                  <span className="text-[13px] text-[#374151]">OCR processing</span>
                </label>
                <label className="flex items-center">
                  <input type="checkbox" defaultChecked className="mr-2" />
                  <span className="text-[13px] text-[#374151]">Delivery note pairings</span>
                </label>
                <label className="flex items-center">
                  <input type="checkbox" defaultChecked className="mr-2" />
                  <span className="text-[13px] text-[#374151]">Issue resolutions</span>
                </label>
                <label className="flex items-center">
                  <input type="checkbox" defaultChecked className="mr-2" />
                  <span className="text-[13px] text-[#374151]">User actions</span>
                </label>
              </div>
            </div>

            {/* Action Buttons */}
            <div className="flex gap-2 pt-2">
              <button
                onClick={handleExport}
                className="flex-1 bg-[#2563EB] hover:bg-[#1D4ED8] text-white rounded-[8px] px-3 py-2 text-[13px] font-medium transition-colors"
              >
                Export CSV
              </button>
              <button
                onClick={() => setIsOpen(false)}
                className="bg-white border border-[#E5E7EB] hover:bg-[#F9FAFB] text-[#374151] rounded-[8px] px-3 py-2 text-[13px] font-medium transition-colors"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Backdrop */}
      {isOpen && (
        <div 
          className="fixed inset-0 z-40" 
          onClick={() => setIsOpen(false)}
        />
      )}
    </div>
  );
};

export default AuditLogExport; 