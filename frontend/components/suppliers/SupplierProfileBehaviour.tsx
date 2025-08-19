import React, { useState } from 'react';
import { useSupplierEvents, useSupplierInsights, SupplierEvent, SupplierInsight } from '../../hooks/useSupplierBehaviour';
import dayjs from 'dayjs';

interface SupplierProfileBehaviourProps {
  supplierId: string;
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

// Trend direction icons
const TrendIcons = {
  up: (
    <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" fill="none" stroke="#16A34A" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-label="Trend up">
      <path d="M12 8L7 3 2 8"/>
    </svg>
  ),
  down: (
    <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" fill="none" stroke="#DC2626" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-label="Trend down">
      <path d="M2 6l5 5 5-5"/>
    </svg>
  ),
  flat: (
    <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" fill="none" stroke="#6B7280" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-label="Trend flat">
      <path d="M2 7h10"/>
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

const getTrendColor = (direction: string) => {
  switch (direction) {
    case 'up':
      return 'text-[#16A34A]';
    case 'down':
      return 'text-[#DC2626]';
    case 'flat':
      return 'text-[#6B7280]';
    default:
      return 'text-[#6B7280]';
  }
};

const EventTimelineCard: React.FC<{ event: SupplierEvent }> = ({ event }) => {
  const [showDetails, setShowDetails] = useState(false);

  return (
    <div 
      className="bg-white rounded-[12px] border border-[#E5E7EB] p-4 hover:shadow-md transition-shadow duration-150 ease-out cursor-pointer"
      onClick={() => setShowDetails(!showDetails)}
    >
      <div className="flex items-start gap-3">
        <div className="flex-shrink-0 mt-1">
          {EventIcons[event.event_type]}
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center justify-between mb-2">
            <h4 className="text-[16px] font-semibold text-[#1F2937]">
              {event.event_type.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())} ({event.severity})
            </h4>
            <span className={`px-2 py-1 rounded-[6px] text-xs font-medium ${getSeverityColor(event.severity)}`}>
              {event.severity}
            </span>
          </div>
          <p className="text-[14px] text-[#6B7280] mb-2">
            {dayjs(event.created_at).format('DD MMM YYYY, HH:mm')}
          </p>
          {event.description && (
            <p className="text-[14px] text-[#374151] line-clamp-2">
              {event.description.length > 120 
                ? `${event.description.substring(0, 120)}...` 
                : event.description
              }
            </p>
          )}
          {showDetails && event.description && event.description.length > 120 && (
            <div className="mt-2 p-3 bg-[#F8F9FB] rounded-lg">
              <p className="text-[14px] text-[#374151]">{event.description}</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

const InsightCard: React.FC<{ insight: SupplierInsight }> = ({ insight }) => {
  return (
    <div className="bg-white rounded-[12px] border border-[#E5E7EB] p-4 hover:shadow-[0_0_0_1px_rgba(0,0,0,0.05)] transition-shadow">
      <div className="flex items-center justify-between mb-3">
        <h4 className="text-[14px] font-semibold text-[#1F2937]">{insight.metric_name}</h4>
        <div className="flex items-center gap-1">
          {TrendIcons[insight.trend_direction]}
          <span className={`text-xs font-medium ${getTrendColor(insight.trend_direction)}`}>
            {insight.trend_percentage.toFixed(1)}%
          </span>
        </div>
      </div>
      <div className="text-[24px] font-bold text-[#1F2937] mb-2">
        {insight.metric_value.toFixed(1)}%
      </div>
      <p className="text-[12px] text-[#6B7280]">
        Last updated: {dayjs(insight.last_updated).format('DD MMM YYYY, HH:mm')}
      </p>
    </div>
  );
};

const LoadingSkeleton: React.FC = () => (
  <div className="space-y-4">
    {[1, 2, 3].map((i) => (
      <div key={i} className="bg-white rounded-[12px] border border-[#E5E7EB] p-4 animate-pulse">
        <div className="flex items-start gap-3">
          <div className="w-[18px] h-[18px] bg-gray-200 rounded"></div>
          <div className="flex-1">
            <div className="h-4 bg-gray-200 rounded mb-2"></div>
            <div className="h-3 bg-gray-200 rounded w-1/2"></div>
          </div>
        </div>
      </div>
    ))}
  </div>
);

const EmptyState: React.FC<{ message: string }> = ({ message }) => (
  <div className="text-center py-8">
    <div className="w-12 h-12 bg-gray-200 rounded-full flex items-center justify-center mx-auto mb-3">
      <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" fill="none" stroke="#9CA3AF" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M16 4h16v4H16z"/>
        <rect x="8" y="8" width="32" height="36" rx="2" ry="2"/>
      </svg>
    </div>
    <p className="text-[14px] text-[#6B7280]">{message}</p>
  </div>
);

const ErrorState: React.FC<{ error: string; onRetry: () => void }> = ({ error, onRetry }) => (
  <div className="bg-[#FFEBEE] border border-[#E57373] rounded-[12px] p-4">
    <div className="flex items-center justify-between">
      <p className="text-[14px] text-[#C62828]">{error}</p>
      <button 
        onClick={onRetry}
        className="px-3 py-1 bg-[#C62828] text-white rounded-[8px] text-xs font-medium hover:bg-[#B71C1C] transition-colors"
      >
        Retry
      </button>
    </div>
  </div>
);

export default function SupplierProfileBehaviour({ supplierId }: SupplierProfileBehaviourProps) {
  const { events, loading: eventsLoading, error: eventsError, isCachedData: eventsCached } = useSupplierEvents(supplierId);
  const { insights, loading: insightsLoading, error: insightsError, isCachedData: insightsCached } = useSupplierInsights(supplierId);

  const handleRetryEvents = () => {
    window.location.reload();
  };

  const handleRetryInsights = () => {
    window.location.reload();
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h2 className="text-[16px] font-semibold text-[#1F2937]">Supplier Behaviour</h2>
        {(eventsCached || insightsCached) && (
          <span className="px-2 py-1 bg-[#E5E7EB] text-[#374151] rounded-[6px] text-xs font-medium">
            Viewing cached data
          </span>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Left Column - Event Timeline */}
        <div>
          <h3 className="text-[16px] font-semibold text-[#1F2937] mb-4">Event Timeline</h3>
          
          {eventsLoading && <LoadingSkeleton />}
          
          {eventsError && (
            <ErrorState error={eventsError} onRetry={handleRetryEvents} />
          )}
          
          {!eventsLoading && !eventsError && events.length === 0 && (
            <EmptyState message="No supplier events recorded in the last 90 days." />
          )}
          
          {!eventsLoading && !eventsError && events.length > 0 && (
            <div className="space-y-4">
              {events.map((event) => (
                <EventTimelineCard key={event.id} event={event} />
              ))}
            </div>
          )}
        </div>

        {/* Right Column - Insights Grid */}
        <div>
          <h3 className="text-[16px] font-semibold text-[#1F2937] mb-4">Insights</h3>
          
          {insightsLoading && (
            <div className="grid grid-cols-1 gap-4">
              {[1, 2, 3].map((i) => (
                <div key={i} className="bg-white rounded-[12px] border border-[#E5E7EB] p-4 animate-pulse">
                  <div className="h-4 bg-gray-200 rounded mb-2"></div>
                  <div className="h-6 bg-gray-200 rounded mb-2"></div>
                  <div className="h-3 bg-gray-200 rounded w-1/2"></div>
                </div>
              ))}
            </div>
          )}
          
          {insightsError && (
            <ErrorState error={insightsError} onRetry={handleRetryInsights} />
          )}
          
          {!insightsLoading && !insightsError && insights.length === 0 && (
            <EmptyState message="No insights available. Log events to generate trends." />
          )}
          
          {!insightsLoading && !insightsError && insights.length > 0 && (
            <div className="grid grid-cols-1 gap-4">
              {insights.map((insight, index) => (
                <InsightCard key={index} insight={insight} />
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
} 