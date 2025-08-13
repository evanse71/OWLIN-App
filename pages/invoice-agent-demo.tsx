import React, { useState } from 'react';
import AppShell from '@/components/layout/AppShell';
import InvoiceAgentPanel from '@/components/agent/InvoiceAgentPanel';

interface AgentAction {
  type: string;
  description: string;
  priority: string;
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

const InvoiceAgentDemo: React.FC = () => {
  const [selectedRole, setSelectedRole] = useState<'gm' | 'finance' | 'shift'>('gm');
  const [userId] = useState('demo_user_123');
  const [invoiceId] = useState('INV-73318');

  // Sample invoice data with issues (triggers escalation)
  const sampleInvoiceData: InvoiceData = {
    id: invoiceId,
    supplier_name: "Tom's Meats",
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
        name: "Beef Steaks",
        quantity: 10,
        unit_price: 8.50,
        total: 85.00,
        status: "flagged",
        notes: "Price 15% higher than usual"
      },
      {
        id: "2",
        name: "Chicken Breast",
        quantity: 5,
        unit_price: 4.20,
        total: 21.00,
        status: "missing",
        notes: "Only 3 received instead of 5"
      },
      {
        id: "3",
        name: "Pork Chops",
        quantity: 8,
        unit_price: 3.80,
        total: 30.40,
        status: "mismatched",
        notes: "Expected 10, received 8"
      },
      {
        id: "4",
        name: "Lamb Cutlets",
        quantity: 6,
        unit_price: 6.50,
        total: 39.00,
        status: "flagged",
        notes: "Quality below standard"
      }
    ],
    status: "flagged"
  };

  // Sample delivery note data
  const sampleDeliveryNote: DeliveryNoteData = {
    id: "DN-001",
    delivery_number: "DN-73318",
    delivery_date: "2024-01-15",
    supplier_name: "Tom's Meats",
    items: [
      {
        id: "1",
        name: "Beef Steaks",
        quantity: 10,
        unit_price: 8.50,
        total: 85.00,
        status: "normal"
      },
      {
        id: "2",
        name: "Chicken Breast",
        quantity: 3,
        unit_price: 4.20,
        total: 12.60,
        status: "missing",
        notes: "Only 3 received instead of 5"
      },
      {
        id: "3",
        name: "Pork Chops",
        quantity: 8,
        unit_price: 3.80,
        total: 30.40,
        status: "normal"
      }
    ],
    matching_status: "partial",
    match_confidence: 65
  };

  const handleAgentAction = (action: AgentAction) => {
    console.log('Agent action triggered:', action);
    // In a real application, this would trigger the appropriate business logic
    // For example, applying a credit, flagging an item, etc.
  };

  const exampleQuestions = [
    "Why is this line item flagged?",
    "Should I request a credit for the missing chicken?",
    "What's the best way to handle this price discrepancy?",
    "Can you help me understand this invoice?",
    "What actions should I take on this invoice?",
    "Why is the delivery note showing a partial match?",
    "Should I escalate this supplier?"
  ];

  return (
    <AppShell>
      <div className="py-8">
        <div className="max-w-7xl mx-auto space-y-8">
          {/* Page Header */}
          <div className="text-center">
            <h1 className="text-3xl font-bold text-gray-900 mb-2">
              Owlin Agent Demo
            </h1>
            <p className="text-gray-600">
              Experience the intelligent invoice assistant with context awareness and escalation detection
            </p>
          </div>

          {/* Role Selector */}
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
            <h2 className="text-xl font-semibold text-gray-900 mb-4">
              👤 Select Your Role
            </h2>
            <div className="flex space-x-4">
              {(['gm', 'finance', 'shift'] as const).map((role) => (
                <button
                  key={role}
                  onClick={() => setSelectedRole(role)}
                  className={`px-4 py-2 rounded-lg font-medium transition-colors ${
                    selectedRole === role
                      ? 'bg-blue-500 text-white'
                      : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                  }`}
                >
                  {role.toUpperCase()}
                </button>
              ))}
            </div>
            <div className="mt-4 text-sm text-gray-600">
              <strong>Role descriptions:</strong>
              <ul className="mt-2 space-y-1">
                <li><strong>GM:</strong> Can see escalation suggestions and take action</li>
                <li><strong>Finance:</strong> Focus on accuracy and compliance (no escalation)</li>
                <li><strong>Shift:</strong> Focus on immediate operations (no escalation)</li>
              </ul>
            </div>
          </div>

          {/* Escalation Information */}
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
            <h2 className="text-xl font-semibold text-gray-900 mb-4">
              🚨 Escalation Detection System
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <h3 className="font-semibold text-gray-900 mb-3">Escalation Triggers</h3>
                <ul className="space-y-2 text-sm text-gray-600">
                  <li className="flex items-start">
                    <span className="text-red-500 mr-2">•</span>
                    <span><strong>Mismatch Rate &gt; 25%:</strong> Delivery vs invoice mismatches</span>
                  </li>
                  <li className="flex items-start">
                    <span className="text-red-500 mr-2">•</span>
                    <span><strong>Confidence &lt; 60%:</strong> Low processing confidence</span>
                  </li>
                  <li className="flex items-start">
                    <span className="text-red-500 mr-2">•</span>
                    <span><strong>Late Delivery &gt; 40%:</strong> Frequent late deliveries</span>
                  </li>
                  <li className="flex items-start">
                    <span className="text-red-500 mr-2">•</span>
                    <span><strong>Flagged Issues ≥ 5:</strong> Multiple issues in 30 days</span>
                  </li>
                </ul>
              </div>
              <div>
                <h3 className="font-semibold text-gray-900 mb-3">Current Invoice Issues</h3>
                <ul className="space-y-2 text-sm text-gray-600">
                  <li className="flex items-start">
                    <span className="text-red-500 mr-2">⚠️</span>
                    <span><strong>Beef Steaks:</strong> Price 15% higher than usual</span>
                  </li>
                  <li className="flex items-start">
                    <span className="text-red-500 mr-2">❌</span>
                    <span><strong>Chicken Breast:</strong> Only 3 received instead of 5</span>
                  </li>
                  <li className="flex items-start">
                    <span className="text-red-500 mr-2">⚠️</span>
                    <span><strong>Pork Chops:</strong> Expected 10, received 8</span>
                  </li>
                  <li className="flex items-start">
                    <span className="text-red-500 mr-2">⚠️</span>
                    <span><strong>Lamb Cutlets:</strong> Quality below standard</span>
                  </li>
                </ul>
              </div>
            </div>
            <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-lg">
              <p className="text-sm text-red-800">
                <strong>Note:</strong> This invoice will trigger an escalation banner for GM users due to multiple issues detected.
              </p>
            </div>
          </div>

          {/* Context Information */}
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
            <h2 className="text-xl font-semibold text-gray-900 mb-4">
              📊 Sample Invoice Context
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
              <div>
                <h3 className="font-semibold text-gray-900 mb-2">Invoice Details</h3>
                <ul className="space-y-1 text-gray-600">
                  <li><strong>Supplier:</strong> Tom&apos;s Meats</li>
                  <li><strong>Invoice #:</strong> INV-73318</li>
                  <li><strong>Total:</strong> £150.50</li>
                  <li><strong>Confidence:</strong> 75% (Manual review required)</li>
                </ul>
              </div>
              <div>
                <h3 className="font-semibold text-gray-900 mb-2">Issues Detected</h3>
                <ul className="space-y-1 text-gray-600">
                  <li>⚠️ Beef Steaks: Price 15% higher than usual</li>
                  <li>❌ Chicken Breast: Only 3 received instead of 5</li>
                  <li>⚠️ Pork Chops: Quantity mismatch (8 vs 10)</li>
                  <li>⚠️ Lamb Cutlets: Quality below standard</li>
                  <li>📋 Delivery Note: Partial match (65% confidence)</li>
                </ul>
              </div>
            </div>
          </div>

          {/* Example Questions */}
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
            <h2 className="text-xl font-semibold text-gray-900 mb-4">
              💡 Example Questions to Try
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {exampleQuestions.map((question, index) => (
                <div
                  key={index}
                  className="p-3 bg-gray-50 rounded-lg border border-gray-200"
                >
                  <p className="text-sm text-gray-700">&quot;{question}&quot;</p>
                </div>
              ))}
            </div>
          </div>

          {/* Agent Panel */}
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
            <div className="mb-4">
              <h2 className="text-xl font-semibold text-gray-900">
                🤖 Owlin Agent Chat with Escalation Detection
              </h2>
              <p className="text-sm text-gray-600">
                The agent now has access to invoice context and can detect supplier issues that warrant escalation. 
                {selectedRole === 'gm' ? ' As a GM, you will see escalation suggestions when issues are detected.' : 
                ' As a ' + selectedRole.toUpperCase() + ', escalation suggestions are hidden from your view.'}
              </p>
            </div>
            
            {/* Agent Panel Container */}
            <div className="h-96">
              <InvoiceAgentPanel
                invoiceId={invoiceId}
                userId={userId}
                userRole={selectedRole}
                onAgentAction={handleAgentAction}
                invoiceData={sampleInvoiceData}
                deliveryNote={sampleDeliveryNote}
              />
            </div>
          </div>

          {/* Features Overview */}
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
            <h2 className="text-xl font-semibold text-gray-900 mb-4">
              ✨ Enhanced Features
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              <div className="p-4 bg-blue-50 rounded-lg">
                <h3 className="font-semibold text-blue-900 mb-2">🎯 Context Awareness</h3>
                <p className="text-sm text-blue-700">
                  The agent has access to invoice data and can provide informed suggestions
                </p>
              </div>
              <div className="p-4 bg-green-50 rounded-lg">
                <h3 className="font-semibold text-green-900 mb-2">📊 Context Panel</h3>
                <p className="text-sm text-green-700">
                  Collapsible sidebar showing invoice details, financials, and delivery notes
                </p>
              </div>
              <div className="p-4 bg-purple-50 rounded-lg">
                <h3 className="font-semibold text-purple-900 mb-2">🔍 Issue Detection</h3>
                <p className="text-sm text-purple-700">
                  Automatically highlights flagged items, missing goods, and price discrepancies
                </p>
              </div>
              <div className="p-4 bg-yellow-50 rounded-lg">
                <h3 className="font-semibold text-yellow-900 mb-2">📋 Delivery Matching</h3>
                <p className="text-sm text-yellow-700">
                  Shows delivery note matching status and confidence levels
                </p>
              </div>
              <div className="p-4 bg-red-50 rounded-lg">
                <h3 className="font-semibold text-red-900 mb-2">🚨 Escalation Detection</h3>
                <p className="text-sm text-red-700">
                  Proactively detects supplier issues and suggests escalation to GMs
                </p>
              </div>
              <div className="p-4 bg-indigo-50 rounded-lg">
                <h3 className="font-semibold text-indigo-900 mb-2">👤 Role-Based Access</h3>
                <p className="text-sm text-indigo-700">
                  Escalation suggestions only visible to GMs, respecting user roles
                </p>
              </div>
            </div>
          </div>

          {/* Technical Details */}
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
            <h2 className="text-xl font-semibold text-gray-900 mb-4">
              🔧 Technical Details
            </h2>
            <div className="space-y-4">
              <div>
                <h3 className="font-semibold text-gray-900 mb-2">Escalation System</h3>
                <div className="bg-gray-50 p-3 rounded-lg">
                  <ul className="text-sm text-gray-700 space-y-1">
                    <li>• Backend logic in <code>agentSuggestEscalation.py</code></li>
                    <li>• Frontend banner component with calm red styling</li>
                    <li>• Role-based visibility (GM only)</li>
                    <li>• Configurable thresholds for different metrics</li>
                    <li>• Auto-dismiss functionality</li>
                  </ul>
                </div>
              </div>
              <div>
                <h3 className="font-semibold text-gray-900 mb-2">Threshold Logic</h3>
                <div className="bg-gray-50 p-3 rounded-lg">
                  <ul className="text-sm text-gray-700 space-y-1">
                    <li>• Mismatch rate &gt; 25% (with minimum 3 invoices)</li>
                    <li>• Average confidence &lt; 60%</li>
                    <li>• Late delivery rate &gt; 40%</li>
                    <li>• Flagged issues ≥ 5 in 30 days</li>
                    <li>• Multiple thresholds can trigger simultaneously</li>
                  </ul>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </AppShell>
  );
};

export default InvoiceAgentDemo; 