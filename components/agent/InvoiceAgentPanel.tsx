import React, { useState, useRef, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import AgentContextPanel from './AgentContextPanel';
import AgentEscalationBanner from './AgentEscalationBanner';

interface AgentAction {
  type: string;
  description: string;
  priority: string;
}

interface AgentResponse {
  markdown: string;
  actions: AgentAction[];
  confidence: number;
  entities: Record<string, any>;
  urgency: string;
  error?: string;
}

interface LineItem {
  id: string;
  name: string;
  quantity: number;
  unit_price: number;
  total: number;
  status?: 'flagged' | 'missing' | 'mismatched' | 'normal';
  expected_quantity?: number;
  actual_quantity?: number;
  notes?: string;
}

interface InvoiceData {
  id: string;
  supplier_name: string;
  invoice_number: string;
  invoice_date: string;
  subtotal: number;
  vat: number;
  total: number;
  confidence: number;
  manual_review_required: boolean;
  line_items: LineItem[];
  status: 'pending' | 'reviewed' | 'approved' | 'flagged';
}

interface DeliveryNoteData {
  id: string;
  delivery_number: string;
  delivery_date: string;
  supplier_name: string;
  items: LineItem[];
  matching_status: 'matched' | 'unmatched' | 'partial';
  match_confidence: number;
}

interface SupplierMetrics {
  supplierId: string;
  supplierName: string;
  mismatchRate: number;
  avgConfidence: number;
  lateDeliveryRate: number;
  flaggedIssueCount: number;
  totalInvoices: number;
  recentIssues: string[];
}

interface InvoiceAgentPanelProps {
  invoiceId: string;
  userId: string;
  userRole: 'gm' | 'finance' | 'shift';
  onAgentAction?: (action: AgentAction) => void;
  invoiceData?: InvoiceData;
  deliveryNote?: DeliveryNoteData;
}

interface ChatMessage {
  id: string;
  type: 'user' | 'agent';
  content: string;
  timestamp: Date;
  response?: AgentResponse;
}

const InvoiceAgentPanel: React.FC<InvoiceAgentPanelProps> = ({
  invoiceId,
  userId,
  userRole,
  onAgentAction,
  invoiceData,
  deliveryNote
}) => {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isContextCollapsed, setIsContextCollapsed] = useState(true);
  const [escalationData, setEscalationData] = useState<SupplierMetrics | null>(null);
  const [showEscalation, setShowEscalation] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Focus input on mount
  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  // Auto-expand context panel if confidence is low or there are issues
  useEffect(() => {
    if (invoiceData) {
      const shouldExpand = 
        invoiceData.confidence < 60 || 
        invoiceData.manual_review_required ||
        invoiceData.line_items.some(item => item.status && item.status !== 'normal') ||
        (deliveryNote && deliveryNote.matching_status !== 'matched');
      
      setIsContextCollapsed(!shouldExpand);
    }
  }, [invoiceData, deliveryNote]);

  // Check for escalation when invoice data changes
  useEffect(() => {
    if (invoiceData && userRole === 'gm') {
      checkForEscalation();
    }
  }, [invoiceData, userRole]);

  const checkForEscalation = async () => {
    if (!invoiceData) return;

    try {
      // In a real implementation, this would call the backend API
      // For now, we'll simulate escalation detection based on invoice data
      const hasIssues = invoiceData.line_items.some(item => 
        item.status === 'flagged' || item.status === 'missing' || item.status === 'mismatched'
      );

      if (hasIssues) {
        // Simulate escalation data
        const mockEscalationData: SupplierMetrics = {
          supplierId: `SUP-${invoiceData.supplier_name.replace(/\s+/g, '').toUpperCase()}`,
          supplierName: invoiceData.supplier_name,
          mismatchRate: 35,
          avgConfidence: 65,
          lateDeliveryRate: 45,
          flaggedIssueCount: 6,
          totalInvoices: 8,
          recentIssues: [
            "Delivery quantity mismatch detected",
            "Multiple price discrepancies flagged",
            "Missing items in delivery"
          ]
        };

        setEscalationData(mockEscalationData);
        setShowEscalation(true);
      }
    } catch (error) {
      console.error('Error checking for escalation:', error);
    }
  };

  const sendMessage = async () => {
    if (!inputValue.trim() || isLoading) return;

    const userMessage: ChatMessage = {
      id: Date.now().toString(),
      type: 'user',
      content: inputValue.trim(),
      timestamp: new Date()
    };

    setMessages(prev => [...prev, userMessage]);
    setInputValue('');
    setIsLoading(true);
    setError(null);

    try {
      const response = await fetch('/api/agent/ask', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          user_prompt: userMessage.content,
          user_id: userId,
          invoice_id: invoiceId,
          role: userRole
        })
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const agentResponse: AgentResponse = await response.json();

      const agentMessage: ChatMessage = {
        id: (Date.now() + 1).toString(),
        type: 'agent',
        content: agentResponse.markdown,
        timestamp: new Date(),
        response: agentResponse
      };

      setMessages(prev => [...prev, agentMessage]);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to get agent response');
      console.error('Agent API error:', err);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const handleAgentAction = (action: AgentAction) => {
    if (onAgentAction) {
      onAgentAction(action);
    }
    // You could also add a visual confirmation here
    console.log('Agent action triggered:', action);
  };

  const handleEscalate = (supplierId: string, reason: string) => {
    console.log('Escalating supplier:', supplierId, 'Reason:', reason);
    // In a real application, this would trigger the escalation modal
    // and log the escalation action
    setShowEscalation(false);
  };

  const handleViewHistory = (supplierId: string) => {
    console.log('Viewing history for supplier:', supplierId);
    // In a real application, this would open the supplier module
  };

  const handleDismissEscalation = () => {
    setShowEscalation(false);
  };

  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 80) return 'bg-green-100 text-green-800';
    if (confidence >= 60) return 'bg-yellow-100 text-yellow-800';
    return 'bg-red-100 text-red-800';
  };

  const getUrgencyColor = (urgency: string) => {
    switch (urgency) {
      case 'high': return 'bg-red-100 text-red-800';
      case 'medium': return 'bg-yellow-100 text-yellow-800';
      case 'low': return 'bg-green-100 text-green-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  const formatTimestamp = (timestamp: Date) => {
    return timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };

  // Mock invoice data if not provided
  const mockInvoiceData: InvoiceData = {
    id: invoiceId,
    supplier_name: "ABC Corporation",
    invoice_number: `INV-${invoiceId.slice(-5)}`,
    invoice_date: "2024-01-15",
    subtotal: 125.00,
    vat: 25.50,
    total: 150.50,
    confidence: 85,
    manual_review_required: false,
    line_items: [
      {
        id: "1",
        name: "Tomatoes",
        quantity: 10,
        unit_price: 2.50,
        total: 25.00,
        status: "flagged",
        notes: "Price 12% higher than usual"
      },
      {
        id: "2",
        name: "Onions",
        quantity: 5,
        unit_price: 1.20,
        total: 6.00,
        status: "normal"
      },
      {
        id: "3",
        name: "Olive Oil",
        quantity: 3,
        unit_price: 7.00,
        total: 21.00,
        status: "normal"
      },
      {
        id: "4",
        name: "IPA Beer",
        quantity: 6,
        unit_price: 4.50,
        total: 27.00,
        status: "missing",
        notes: "Only 2 received"
      }
    ],
    status: "flagged"
  };

  const currentInvoiceData = invoiceData || mockInvoiceData;

  return (
    <div className="flex h-full space-x-4">
      {/* Agent Context Panel */}
      <div className="w-80 flex-shrink-0">
        <AgentContextPanel
          invoiceData={currentInvoiceData}
          deliveryNote={deliveryNote}
          isCollapsed={isContextCollapsed}
          onToggle={setIsContextCollapsed}
        />
      </div>

      {/* Chat Panel */}
      <div className="flex-1 bg-white rounded-lg shadow-lg border border-gray-200 flex flex-col">
        {/* Header */}
        <div className="px-4 py-3 border-b border-gray-200 bg-gradient-to-r from-blue-50 to-indigo-50">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <div className="w-8 h-8 bg-blue-500 rounded-full flex items-center justify-center">
                <span className="text-white text-sm font-semibold">AI</span>
              </div>
              <div>
                <h3 className="text-sm font-semibold text-gray-900">Owlin Agent</h3>
                <p className="text-xs text-gray-600">Ask me anything about this invoice</p>
              </div>
            </div>
            <div className="flex items-center space-x-2">
              <span className={`px-2 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-800`}>
                {userRole.toUpperCase()}
              </span>
            </div>
          </div>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {messages.length === 0 && (
            <div className="text-center py-8">
              <div className="w-12 h-12 bg-blue-100 rounded-full flex items-center justify-center mx-auto mb-3">
                <span className="text-blue-500 text-xl">🤖</span>
              </div>
              <h3 className="text-sm font-medium text-gray-900 mb-1">Welcome to Owlin Agent</h3>
              <p className="text-xs text-gray-500">
                Ask me questions about this invoice, request credits, or get insights.
              </p>
            </div>
          )}

          {/* Escalation Banner */}
          {showEscalation && escalationData && (
            <AgentEscalationBanner
              supplierMetrics={escalationData}
              onEscalate={handleEscalate}
              onViewHistory={handleViewHistory}
              onDismiss={handleDismissEscalation}
              userRole={userRole}
            />
          )}

          {messages.map((message) => (
            <div
              key={message.id}
              className={`flex ${message.type === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              <div
                className={`max-w-xs lg:max-w-md px-4 py-2 rounded-lg ${
                  message.type === 'user'
                    ? 'bg-blue-500 text-white'
                    : 'bg-gray-100 text-gray-900'
                }`}
              >
                {message.type === 'agent' && message.response && (
                  <div className="mb-2 flex items-center justify-between">
                    <span className="text-xs text-gray-500">
                      {formatTimestamp(message.timestamp)}
                    </span>
                    <div className="flex items-center space-x-2">
                      <span
                        className={`px-2 py-1 rounded-full text-xs font-medium ${getConfidenceColor(
                          message.response.confidence
                        )}`}
                      >
                        {message.response.confidence}% confident
                      </span>
                      <span
                        className={`px-2 py-1 rounded-full text-xs font-medium ${getUrgencyColor(
                          message.response.urgency
                        )}`}
                      >
                        {message.response.urgency}
                      </span>
                    </div>
                  </div>
                )}

                <div className="prose prose-sm max-w-none">
                  <ReactMarkdown>{message.content}</ReactMarkdown>
                </div>

                {message.type === 'agent' && message.response?.actions && message.response.actions.length > 0 && (
                  <div className="mt-3 space-y-2">
                    {message.response.actions.map((action, index) => (
                      <button
                        key={index}
                        onClick={() => handleAgentAction(action)}
                        className="w-full text-left p-3 bg-white border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors"
                      >
                        <div className="flex items-center justify-between">
                          <div>
                            <div className="text-sm font-medium text-gray-900">
                              {action.description}
                            </div>
                            <div className="text-xs text-gray-500">
                              Priority: {action.priority}
                            </div>
                          </div>
                          <div className="text-blue-500">
                            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                            </svg>
                          </div>
                        </div>
                      </button>
                    ))}
                  </div>
                )}

                {message.type === 'user' && (
                  <div className="text-xs opacity-70 mt-1">
                    {formatTimestamp(message.timestamp)}
                  </div>
                )}
              </div>
            </div>
          ))}

          {isLoading && (
            <div className="flex justify-start">
              <div className="bg-gray-100 text-gray-900 px-4 py-2 rounded-lg">
                <div className="flex items-center space-x-2">
                  <div className="flex space-x-1">
                    <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></div>
                    <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
                    <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
                  </div>
                  <span className="text-sm">Agent is thinking...</span>
                </div>
              </div>
            </div>
          )}

          {error && (
            <div className="flex justify-start">
              <div className="bg-red-50 border border-red-200 text-red-800 px-4 py-2 rounded-lg">
                <div className="flex items-center space-x-2">
                  <span className="text-sm">⚠️ {error}</span>
                </div>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Input */}
        <div className="border-t border-gray-200 p-4">
          <div className="flex space-x-2">
            <textarea
              ref={inputRef}
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="Ask me about this invoice..."
              className="flex-1 resize-none border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              rows={2}
              disabled={isLoading}
            />
            <button
              onClick={sendMessage}
              disabled={!inputValue.trim() || isLoading}
              className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
              </svg>
            </button>
          </div>
          <div className="mt-2 text-xs text-gray-500">
            Press Enter to send, Shift+Enter for new line
          </div>
        </div>
      </div>
    </div>
  );
};

export default InvoiceAgentPanel; 