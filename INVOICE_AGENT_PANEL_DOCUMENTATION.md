# InvoiceAgentPanel Component Documentation

## ✅ **Implementation Status: COMPLETE**

Successfully implemented the `InvoiceAgentPanel.tsx` component that provides an intelligent chat interface for users to interact with the Owlin Agent about invoice-related questions.

## 📦 **Component Overview**

### File Location
```
components/agent/InvoiceAgentPanel.tsx
```

### Demo Page
```
pages/invoice-agent-demo.tsx
```

## 🎯 **Key Features**

### 1. **Intelligent Chat Interface**
- ✅ Natural language question input
- ✅ Real-time agent responses
- ✅ Markdown rendering of responses
- ✅ Loading indicators and error handling

### 2. **Role-Aware Interactions**
- ✅ Different responses based on user role (GM, Finance, Shift)
- ✅ Role-specific action suggestions
- ✅ Contextual guidance

### 3. **Structured Action Cards**
- ✅ Clickable action buttons from agent responses
- ✅ Priority-based action display
- ✅ Visual action cards with descriptions

### 4. **Confidence & Urgency Indicators**
- ✅ Confidence score badges (0-100%)
- ✅ Urgency level indicators (low, medium, high)
- ✅ Color-coded confidence levels

### 5. **Conversation Management**
- ✅ Persistent chat history during session
- ✅ Auto-scroll to latest messages
- ✅ Timestamp display for messages

## 🔧 **Component Props**

```typescript
interface InvoiceAgentPanelProps {
  invoiceId: string;           // ID of the invoice being discussed
  userId: string;              // Current user ID
  userRole: 'gm' | 'finance' | 'shift';  // User's role
  onAgentAction?: (action: AgentAction) => void;  // Callback for actions
}
```

## 📊 **Response Structure**

```typescript
interface AgentResponse {
  markdown: string;            // Agent's response in markdown
  actions: AgentAction[];      // Suggested actions
  confidence: number;          // Confidence score (0-100)
  entities: Record<string, any>; // Extracted entities
  urgency: string;            // Urgency level
  error?: string;             // Error message if any
}

interface AgentAction {
  type: string;               // Action type
  description: string;        // Human-readable description
  priority: string;          // Priority level
}
```

## 🎨 **UI Components**

### 1. **Header Section**
- Agent avatar and title
- User role indicator
- Welcome message for new conversations

### 2. **Messages Area**
- User messages (right-aligned, blue background)
- Agent messages (left-aligned, gray background)
- Markdown rendering for agent responses
- Confidence and urgency badges
- Action cards for suggested actions

### 3. **Input Section**
- Textarea for typing questions
- Send button with icon
- Keyboard shortcuts (Enter to send, Shift+Enter for new line)
- Loading state handling

### 4. **Loading & Error States**
- Animated loading indicators
- Error message display
- Graceful fallback handling

## 🚀 **Usage Examples**

### Basic Implementation
```tsx
import InvoiceAgentPanel from '@/components/agent/InvoiceAgentPanel';

const InvoicePage = () => {
  const handleAgentAction = (action) => {
    console.log('Agent action:', action);
    // Handle the action (e.g., apply credit, flag item)
  };

  return (
    <div className="h-96">
      <InvoiceAgentPanel
        invoiceId="INV-73318"
        userId="user_123"
        userRole="finance"
        onAgentAction={handleAgentAction}
      />
    </div>
  );
};
```

### Integration with Invoice Detail Page
```tsx
const InvoiceDetailPage = ({ invoiceId, user }) => {
  const [agentActions, setAgentActions] = useState([]);

  const handleAgentAction = (action) => {
    switch (action.type) {
      case 'credit_suggestion':
        // Apply credit logic
        break;
      case 'flag_item':
        // Flag item logic
        break;
      case 'escalate':
        // Escalation logic
        break;
    }
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      {/* Invoice Details */}
      <div className="bg-white rounded-lg shadow p-6">
        {/* Invoice content */}
      </div>
      
      {/* Agent Panel */}
      <div className="bg-white rounded-lg shadow p-6">
        <InvoiceAgentPanel
          invoiceId={invoiceId}
          userId={user.id}
          userRole={user.role}
          onAgentAction={handleAgentAction}
        />
      </div>
    </div>
  );
};
```

## 🧪 **Demo Page Features**

### 1. **Role Selector**
- Switch between GM, Finance, and Shift roles
- See how responses change based on role
- Role descriptions and explanations

### 2. **Example Questions**
- Pre-written example questions to try
- Covers common invoice scenarios
- Demonstrates different agent capabilities

### 3. **Features Overview**
- Visual showcase of component capabilities
- Technical details and API integration
- Usage examples and best practices

## 🔧 **API Integration**

### Request Format
```javascript
POST /api/agent/ask
{
  "user_prompt": "Why is this line item flagged?",
  "user_id": "user_123",
  "invoice_id": "INV-73318",
  "role": "finance"
}
```

### Response Format
```javascript
{
  "markdown": "This line item is flagged because the price is 15% higher than usual...",
  "actions": [
    {
      "type": "credit_suggestion",
      "description": "Suggest credit: £4.20 for onions",
      "priority": "medium"
    }
  ],
  "confidence": 85,
  "entities": {
    "suppliers": ["ABC Corp"],
    "amounts": ["£4.20"],
    "items": ["onions"]
  },
  "urgency": "medium"
}
```

## 🎯 **User Flow Examples**

### Example 1: Credit Request
1. **User (Finance role)** types: "Should I request a credit for the onions?"
2. **Agent responds** with analysis and credit suggestion
3. **UI displays** action card: "Suggest credit: £4.20 for onions"
4. **User clicks** action card
5. **System applies** the credit automatically

### Example 2: Price Discrepancy
1. **User (GM role)** types: "Why is this more expensive than usual?"
2. **Agent analyzes** historical data and current prices
3. **Agent suggests** actions: flag item, contact supplier, or escalate
4. **User selects** appropriate action
5. **System executes** the chosen action

### Example 3: Invoice Review
1. **User (Shift role)** types: "What should I do about this invoice?"
2. **Agent provides** role-specific guidance
3. **Agent suggests** immediate actions for shift operations
4. **User follows** agent recommendations
5. **System tracks** actions for reporting

## 🎨 **Styling & Design**

### Color Scheme
- **Primary**: Blue (#3B82F6) for user messages and actions
- **Secondary**: Gray (#6B7280) for agent messages
- **Success**: Green for high confidence responses
- **Warning**: Yellow for medium confidence
- **Error**: Red for low confidence or errors

### Responsive Design
- Mobile-friendly layout
- Adaptive message bubbles
- Flexible action card layout
- Touch-friendly interface

### Accessibility
- Keyboard navigation support
- Screen reader compatibility
- High contrast mode support
- Focus management

## 🔒 **Error Handling**

### Network Errors
- Graceful fallback messages
- Retry mechanisms
- User-friendly error messages

### API Errors
- Structured error responses
- Error state management
- Recovery options

### Component Errors
- Boundary error handling
- Fallback UI states
- Error logging

## 📈 **Performance Optimizations**

### 1. **Message Management**
- Efficient message rendering
- Virtual scrolling for large conversations
- Memory management for long sessions

### 2. **API Calls**
- Debounced input handling
- Request cancellation on unmount
- Caching for repeated questions

### 3. **UI Performance**
- Optimized re-renders
- Lazy loading of markdown
- Efficient state updates

## 🎯 **Integration Points**

### 1. **Invoice Detail Pages**
- Add agent panel to invoice view
- Context-aware responses
- Action integration with invoice data

### 2. **User Management**
- Role-based access control
- User preferences and history
- Personalized responses

### 3. **Business Logic**
- Credit application workflows
- Flagging and escalation systems
- Audit trail for agent actions

## 🔮 **Future Enhancements**

### 1. **Advanced Features**
- Voice input/output
- Image analysis integration
- Multi-language support
- Advanced markdown features

### 2. **Analytics & Insights**
- Conversation analytics
- User behavior tracking
- Agent performance metrics
- A/B testing capabilities

### 3. **Integration Extensions**
- Third-party system integration
- Webhook support
- API rate limiting
- Advanced caching strategies

## ✅ **Implementation Checklist**

- ✅ Component created with TypeScript
- ✅ React hooks for state management
- ✅ API integration with error handling
- ✅ Markdown rendering with react-markdown
- ✅ Role-based response handling
- ✅ Action card system
- ✅ Loading and error states
- ✅ Responsive design
- ✅ Accessibility features
- ✅ Demo page created
- ✅ Documentation completed

## 🎉 **Conclusion**

The `InvoiceAgentPanel` component is **fully functional** and ready for integration into invoice detail pages. It provides:

- ✅ Intelligent chat interface
- ✅ Role-aware responses
- ✅ Structured action system
- ✅ Comprehensive error handling
- ✅ Responsive design
- ✅ Accessibility support
- ✅ Demo and documentation

The component successfully bridges the gap between users and the intelligent agent system, providing a natural and intuitive way to interact with invoice data and get intelligent recommendations. 