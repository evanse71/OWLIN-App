# AgentContextPanel Component Documentation

## ✅ **Implementation Status: COMPLETE**

Successfully implemented the `AgentContextPanel.tsx` component that provides a collapsible sidebar showing the invoice and delivery note data that the agent uses to make intelligent suggestions.

## 📦 **Component Overview**

### File Location
```
components/agent/AgentContextPanel.tsx
```

### Integration
The component is integrated into `InvoiceAgentPanel.tsx` as a collapsible sidebar.

## 🎯 **Key Features**

### 1. **Collapsible Interface**
- ✅ Collapsible sidebar design
- ✅ Smart auto-expansion based on issues
- ✅ Smooth expand/collapse animations
- ✅ Compact collapsed state with summary

### 2. **Invoice Overview**
- ✅ Supplier name and invoice details
- ✅ Confidence scoring with color coding
- ✅ Manual review flags
- ✅ Date formatting

### 3. **Key Financials**
- ✅ Subtotal, VAT, and total breakdown
- ✅ Currency formatting (GBP)
- ✅ Clear financial hierarchy

### 4. **Line Items Summary**
- ✅ Up to 5 items displayed
- ✅ Issue highlighting (flagged, missing, mismatched)
- ✅ Color-coded status indicators
- ✅ Detailed notes for issues

### 5. **Delivery Note Integration**
- ✅ Matching status indicators
- ✅ Confidence scoring
- ✅ Key items from delivery note
- ✅ Comparison with invoice items

### 6. **Smart Behavior**
- ✅ Auto-expands when confidence < 60%
- ✅ Auto-expands when manual review required
- ✅ Auto-expands when issues detected
- ✅ Auto-expands when delivery note mismatched

## 🔧 **Component Props**

```typescript
interface AgentContextPanelProps {
  invoiceData: InvoiceData;           // Invoice information
  deliveryNote?: DeliveryNoteData;    // Optional delivery note
  isCollapsed?: boolean;              // Collapsed state
  onToggle?: (collapsed: boolean) => void;  // Toggle callback
}
```

## 📊 **Data Structures**

### InvoiceData
```typescript
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
```

### DeliveryNoteData
```typescript
interface DeliveryNoteData {
  id: string;
  delivery_number: string;
  delivery_date: string;
  supplier_name: string;
  items: LineItem[];
  matching_status: 'matched' | 'unmatched' | 'partial';
  match_confidence: number;
}
```

### LineItem
```typescript
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
```

## 🎨 **UI Components**

### 1. **Collapsed State**
- Compact header with title
- Summary information (item count, total)
- Expand button

### 2. **Expanded State**
- Full invoice overview
- Financial breakdown
- Line items with issue highlighting
- Delivery note information
- Tooltips for each section

### 3. **Issue Highlighting**
- **Red**: Flagged, missing, or mismatched items
- **Green**: Normal items
- **Yellow**: Manual review required
- **Gray**: Default state

### 4. **Confidence Indicators**
- **Green**: 80%+ confidence
- **Yellow**: 60-79% confidence
- **Red**: <60% confidence

## 🚀 **Usage Examples**

### Basic Implementation
```tsx
import AgentContextPanel from '@/components/agent/AgentContextPanel';

const InvoicePage = () => {
  const [isCollapsed, setIsCollapsed] = useState(false);
  
  const invoiceData = {
    id: "INV-73318",
    supplier_name: "ABC Corporation",
    invoice_number: "INV-73318",
    invoice_date: "2024-01-15",
    subtotal: 125.00,
    vat: 25.50,
    total: 150.50,
    confidence: 75,
    manual_review_required: true,
    line_items: [
      {
        id: "1",
        name: "Tomatoes",
        quantity: 10,
        unit_price: 2.80,
        total: 28.00,
        status: "flagged",
        notes: "Price 12% higher than usual"
      }
    ],
    status: "flagged"
  };

  return (
    <div className="w-80">
      <AgentContextPanel
        invoiceData={invoiceData}
        isCollapsed={isCollapsed}
        onToggle={setIsCollapsed}
      />
    </div>
  );
};
```

### With Delivery Note
```tsx
const deliveryNote = {
  id: "DN-001",
  delivery_number: "DN-73318",
  delivery_date: "2024-01-15",
  supplier_name: "ABC Corporation",
  items: [
    {
      id: "1",
      name: "IPA Beer",
      quantity: 2,
      unit_price: 4.50,
      total: 9.00,
      status: "missing",
      notes: "Only 2 received instead of 6"
    }
  ],
  matching_status: "partial",
  match_confidence: 65
};

<AgentContextPanel
  invoiceData={invoiceData}
  deliveryNote={deliveryNote}
  isCollapsed={isCollapsed}
  onToggle={setIsCollapsed}
/>
```

## 🎯 **Smart Auto-Expansion Logic**

The context panel automatically expands when:

```typescript
const shouldExpand = 
  invoiceData.confidence < 60 || 
  invoiceData.manual_review_required ||
  invoiceData.line_items.some(item => item.status && item.status !== 'normal') ||
  (deliveryNote && deliveryNote.matching_status !== 'matched');
```

### Expansion Triggers
1. **Low Confidence**: < 60% confidence score
2. **Manual Review**: Invoice requires manual review
3. **Issues Detected**: Any flagged, missing, or mismatched items
4. **Delivery Mismatch**: Delivery note doesn't match invoice

## 🎨 **Styling & Design**

### Color Scheme
- **Primary**: White background with gray borders
- **Success**: Green for normal items and high confidence
- **Warning**: Yellow for medium confidence and manual review
- **Error**: Red for issues and low confidence
- **Info**: Blue for interactive elements

### Layout
- **Width**: 320px (w-80) when expanded
- **Collapsed**: Compact header with summary
- **Expanded**: Full details with sections

### Responsive Design
- Fixed width sidebar
- Scrollable content for long lists
- Touch-friendly interface

## 🔍 **Issue Detection**

### 1. **Price Discrepancies**
- Items flagged as "flagged"
- Price comparison with historical data
- Percentage difference indicators

### 2. **Missing Goods**
- Items marked as "missing"
- Delivery note vs invoice comparison
- Quantity shortfall indicators

### 3. **Quantity Mismatches**
- Items marked as "mismatched"
- Expected vs actual quantities
- Variance calculations

### 4. **Delivery Note Issues**
- Matching status indicators
- Confidence scoring
- Item-by-item comparison

## 💡 **Tooltips**

Each section includes helpful tooltips:

- **Invoice Overview**: "Basic invoice information and confidence level"
- **Key Financials**: "Financial breakdown of the invoice"
- **Line Items**: "Key items from the invoice with any issues highlighted"
- **Delivery Note**: "Matching delivery note information if available"

## 🔧 **Integration with InvoiceAgentPanel**

The context panel is integrated into the main agent panel:

```tsx
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
  <div className="flex-1">
    {/* Chat interface */}
  </div>
</div>
```

## 🎯 **User Flow Examples**

### Example 1: Price Discrepancy
1. **User opens invoice** with flagged tomatoes
2. **Context panel auto-expands** showing flagged item
3. **User sees** "Price 12% higher than usual"
4. **User asks agent** "Why is this flagged?"
5. **Agent responds** with context-aware explanation

### Example 2: Missing Goods
1. **User opens invoice** with missing IPA beer
2. **Context panel shows** delivery note mismatch
3. **User sees** "Only 2 received instead of 6"
4. **User asks** "Should I request a credit?"
5. **Agent suggests** credit for missing items

### Example 3: Manual Review
1. **User opens invoice** requiring manual review
2. **Context panel expands** showing review flag
3. **User sees** confidence score and issues
4. **User asks** "What should I do?"
5. **Agent provides** escalation guidance

## 🔒 **Error Handling**

### Data Validation
- Graceful handling of missing data
- Default values for optional fields
- Type safety with TypeScript

### Display Errors
- Fallback for missing invoice data
- Error states for failed data loading
- User-friendly error messages

## 📈 **Performance Features**

### 1. **Efficient Rendering**
- Only renders visible items
- Optimized re-renders
- Memory management for large datasets

### 2. **Smart Updates**
- Conditional re-rendering
- Debounced state updates
- Efficient prop handling

### 3. **Responsive Design**
- Fixed width layout
- Scrollable content areas
- Touch-friendly interface

## 🎯 **Integration Points**

### 1. **Invoice Management**
- Connect with invoice data sources
- Real-time updates
- Status synchronization

### 2. **Delivery Note System**
- Delivery note matching
- Real-time comparison
- Confidence scoring

### 3. **Agent Integration**
- Context data sharing
- Issue detection
- Smart suggestions

## 🔮 **Future Enhancements**

### 1. **Advanced Features**
- Historical price comparison
- Supplier performance metrics
- Trend analysis
- Predictive insights

### 2. **Enhanced UI**
- Interactive charts
- Drill-down capabilities
- Export functionality
- Print-friendly views

### 3. **Integration Extensions**
- Third-party data sources
- Real-time notifications
- Advanced filtering
- Custom dashboards

## ✅ **Implementation Checklist**

- ✅ Component created with TypeScript
- ✅ Collapsible interface implemented
- ✅ Smart auto-expansion logic
- ✅ Issue detection and highlighting
- ✅ Tooltip system
- ✅ Responsive design
- ✅ Integration with InvoiceAgentPanel
- ✅ Comprehensive error handling
- ✅ Performance optimizations
- ✅ Documentation completed

## 🎉 **Conclusion**

The `AgentContextPanel` component is **fully functional** and provides:

- ✅ Collapsible sidebar interface
- ✅ Smart auto-expansion based on issues
- ✅ Comprehensive invoice data display
- ✅ Delivery note integration
- ✅ Issue highlighting and detection
- ✅ Helpful tooltips and guidance
- ✅ Responsive and accessible design

The component successfully provides users with clear visibility into the data that the agent uses to make intelligent suggestions, improving trust and understanding of the agent's recommendations. 