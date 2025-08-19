import React, { useState, useEffect } from 'react';
import { useSupplierEvents, SupplierEvent, SupplierEventRequest, logSupplierEvent } from '../../hooks/useSupplierBehaviour';
import dayjs from 'dayjs';

interface EventLogModalProps {
  isOpen: boolean;
  onClose: () => void;
  supplierId?: string;
  mode: 'list' | 'create';
  filters?: {
    type?: string;
    severity?: string;
  };
}

// Event type icons (inline SVG)
const EventIcons = {
  missed_delivery: (
    <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" fill="none" stroke="#B45309" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-label="Missed delivery">
      <rect x="2" y="5" width="14" height="9" rx="2" ry="2"/>
      <path d="M2 8.5h14M6 2v3M12 2v3"/>
    </svg>
  ),
  invoice_mismatch: (
    <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" fill="none" stroke="#6B7280" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-label="Invoice mismatch">
      <path d="M4 2h8l3 3v11a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2z"/>
      <path d="M12 2v3h3M6 8h6M6 12h4"/>
      <path d="M14 14l2 2M16 14l-2 2"/>
    </svg>
  ),
  late_delivery: (
    <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" fill="none" stroke="#D97706" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-label="Late delivery">
      <circle cx="9" cy="9" r="7"/>
      <path d="M9 5v4l3 2"/>
    </svg>
  ),
  quality_issue: (
    <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" fill="none" stroke="#DC2626" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-label="Quality issue">
      <path d="M10 2l7 7-7 7-7-7 7-7z"/>
      <path d="M10 6v4M10 14h.01"/>
    </svg>
  ),
  price_spike: (
    <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" fill="none" stroke="#16A34A" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-label="Price spike">
      <path d="M2 14l4-4 3 3 5-6 2 2"/>
      <path d="M2 16h14"/>
    </svg>
  )
};

const getSeverityColor = (severity: string) => {
  switch (severity) {
    case 'low':
      return 'bg-[#E5E7EB] text-[#374151]';
    case 'medium':
      return 'bg-[#FCD34D] text-[#92400E]';
    case 'high':
      return 'bg-[#F87171] text-[#7F1D1D]';
    default:
      return 'bg-[#E5E7EB] text-[#374151]';
  }
};

const CreateEventForm: React.FC<{ supplierId: string; onClose: () => void }> = ({ supplierId, onClose }) => {
  const [formData, setFormData] = useState<SupplierEventRequest>({
    supplier_id: supplierId,
    event_type: 'missed_delivery',
    severity: 'medium',
    description: '',
    source: 'manual'
  });
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    setError(null);

    try {
      const success = await logSupplierEvent(formData);
      if (success) {
        onClose();
      } else {
        setError('Failed to log event. Please try again.');
      }
    } catch (err) {
      setError('An error occurred. Please try again.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div>
        <label className="block text-[14px] font-medium text-[#1F2937] mb-2">
          Event Type
        </label>
        <select
          value={formData.event_type}
          onChange={(e) => setFormData({ ...formData, event_type: e.target.value as any })}
          className="w-full p-3 border border-[#E5E7EB] rounded-[8px] text-[14px] focus:ring-2 focus:ring-[#3B82F6] focus:border-transparent"
          required
        >
          <option value="missed_delivery">Missed Delivery</option>
          <option value="invoice_mismatch">Invoice Mismatch</option>
          <option value="late_delivery">Late Delivery</option>
          <option value="quality_issue">Quality Issue</option>
          <option value="price_spike">Price Spike</option>
        </select>
      </div>

      <div>
        <label className="block text-[14px] font-medium text-[#1F2937] mb-2">
          Severity
        </label>
        <div className="flex gap-3">
          {['low', 'medium', 'high'].map((severity) => (
            <label key={severity} className="flex items-center">
              <input
                type="radio"
                name="severity"
                value={severity}
                checked={formData.severity === severity}
                onChange={(e) => setFormData({ ...formData, severity: e.target.value as any })}
                className="mr-2"
                required
              />
              <span className="text-[14px] capitalize">{severity}</span>
            </label>
          ))}
        </div>
      </div>

      <div>
        <label className="block text-[14px] font-medium text-[#1F2937] mb-2">
          Description (optional)
        </label>
        <textarea
          value={formData.description}
          onChange={(e) => setFormData({ ...formData, description: e.target.value })}
          className="w-full p-3 border border-[#E5E7EB] rounded-[8px] text-[14px] focus:ring-2 focus:ring-[#3B82F6] focus:border-transparent"
          rows={3}
          maxLength={1000}
          placeholder="Describe the event..."
        />
        <p className="text-[12px] text-[#6B7280] mt-1">
          {formData.description?.length || 0}/1000 characters
        </p>
      </div>

      {error && (
        <div className="bg-[#FFEBEE] border border-[#E57373] rounded-[8px] p-3">
          <p className="text-[14px] text-[#C62828]">{error}</p>
        </div>
      )}

      <div className="flex justify-end gap-3 pt-4">
        <button
          type="button"
          onClick={onClose}
          className="px-4 py-2 border border-[#E5E7EB] rounded-[8px] text-[14px] font-medium text-[#374151] hover:bg-[#F8F9FB] transition-colors"
        >
          Cancel
        </button>
        <button
          type="submit"
          disabled={isSubmitting}
          className="px-4 py-2 bg-[#3B82F6] text-white rounded-[8px] text-[14px] font-medium hover:bg-[#2563EB] transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isSubmitting ? 'Logging...' : 'Log Event'}
        </button>
      </div>
    </form>
  );
};

const EventTable: React.FC<{ events: SupplierEvent[]; filters: any; onFilterChange: (filters: any) => void }> = ({ events, filters, onFilterChange }) => {
  const filteredEvents = events.filter(event => {
    if (filters.type && event.event_type !== filters.type) return false;
    if (filters.severity && event.severity !== filters.severity) return false;
    return true;
  });

  return (
    <div className="space-y-4">
      {/* Filters */}
      <div className="flex gap-4">
        <div>
          <label className="block text-[12px] font-medium text-[#6B7280] mb-1">Type</label>
          <select
            value={filters.type || ''}
            onChange={(e) => onFilterChange({ ...filters, type: e.target.value || undefined })}
            className="p-2 border border-[#E5E7EB] rounded-[6px] text-[12px]"
          >
            <option value="">All Types</option>
            <option value="missed_delivery">Missed Delivery</option>
            <option value="invoice_mismatch">Invoice Mismatch</option>
            <option value="late_delivery">Late Delivery</option>
            <option value="quality_issue">Quality Issue</option>
            <option value="price_spike">Price Spike</option>
          </select>
        </div>
        <div>
          <label className="block text-[12px] font-medium text-[#6B7280] mb-1">Severity</label>
          <div className="flex gap-2">
            {['low', 'medium', 'high'].map((severity) => (
              <button
                key={severity}
                onClick={() => onFilterChange({ ...filters, severity: filters.severity === severity ? undefined : severity })}
                className={`px-2 py-1 rounded-[4px] text-[10px] font-medium transition-colors ${
                  filters.severity === severity 
                    ? getSeverityColor(severity)
                    : 'bg-[#F8F9FB] text-[#6B7280] hover:bg-[#E5E7EB]'
                }`}
              >
                {severity}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Table */}
      <div className="border border-[#E5E7EB] rounded-[8px] overflow-hidden">
        <table className="w-full">
          <thead className="bg-[#F8F9FB]">
            <tr>
              <th className="text-left p-3 text-[12px] font-medium text-[#6B7280]">Type</th>
              <th className="text-left p-3 text-[12px] font-medium text-[#6B7280]">Severity</th>
              <th className="text-left p-3 text-[12px] font-medium text-[#6B7280]">Description</th>
              <th className="text-left p-3 text-[12px] font-medium text-[#6B7280]">Date</th>
              <th className="text-left p-3 text-[12px] font-medium text-[#6B7280]">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[#E5E7EB]">
            {filteredEvents.map((event) => (
              <tr key={event.id} className="hover:bg-[#F8F9FB]">
                <td className="p-3">
                  <div className="flex items-center gap-2">
                    {EventIcons[event.event_type]}
                    <span className="text-[14px] text-[#1F2937]">
                      {event.event_type.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())}
                    </span>
                  </div>
                </td>
                <td className="p-3">
                  <span className={`px-2 py-1 rounded-[4px] text-[10px] font-medium ${getSeverityColor(event.severity)}`}>
                    {event.severity}
                  </span>
                </td>
                <td className="p-3">
                  <span className="text-[14px] text-[#374151] max-w-xs truncate block">
                    {event.description || '-'}
                  </span>
                </td>
                <td className="p-3">
                  <span className="text-[14px] text-[#6B7280]">
                    {dayjs(event.created_at).format('DD MMM YYYY, HH:mm')}
                  </span>
                </td>
                <td className="p-3">
                  <button className="text-[12px] text-[#3B82F6] hover:text-[#2563EB] transition-colors">
                    {event.is_acknowledged ? 'Acknowledged' : 'Acknowledge'}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {filteredEvents.length === 0 && (
        <div className="text-center py-8">
          <div className="w-12 h-12 bg-gray-200 rounded-full flex items-center justify-center mx-auto mb-3">
            <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" fill="none" stroke="#9CA3AF" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M16 4h16v4H16z"/>
              <rect x="8" y="8" width="32" height="36" rx="2" ry="2"/>
            </svg>
          </div>
          <p className="text-[14px] text-[#6B7280]">No events found. Try changing filters.</p>
        </div>
      )}
    </div>
  );
};

export default function EventLogModal({ isOpen, onClose, supplierId, mode, filters: initialFilters }: EventLogModalProps) {
  const [filters, setFilters] = useState(initialFilters || {});
  const { events, loading, error } = useSupplierEvents(supplierId || '');

  useEffect(() => {
    if (isOpen) {
      setFilters(initialFilters || {});
    }
  }, [isOpen, initialFilters]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-[12px] max-w-4xl w-full mx-4 max-h-[90vh] overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-[#E5E7EB]">
          <h2 className="text-[16px] font-semibold text-[#1F2937]">
            {mode === 'create' ? 'Log New Event' : 'Event Log'}
          </h2>
          <button
            onClick={onClose}
            className="text-[#6B7280] hover:text-[#374151] transition-colors"
          >
            <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M18 6L6 18M6 6l12 12"/>
            </svg>
          </button>
        </div>

        {/* Content */}
        <div className="p-6 overflow-y-auto max-h-[calc(90vh-120px)]">
          {mode === 'create' && supplierId ? (
            <CreateEventForm supplierId={supplierId} onClose={onClose} />
          ) : (
            <>
              {loading && (
                <div className="space-y-4">
                  {[1, 2, 3].map((i) => (
                    <div key={i} className="h-16 bg-gray-200 rounded animate-pulse"></div>
                  ))}
                </div>
              )}
              
              {error && (
                <div className="bg-[#FFEBEE] border border-[#E57373] rounded-[8px] p-4">
                  <p className="text-[14px] text-[#C62828]">{error}</p>
                </div>
              )}
              
              {!loading && !error && (
                <EventTable 
                  events={events} 
                  filters={filters} 
                  onFilterChange={setFilters}
                />
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
} 