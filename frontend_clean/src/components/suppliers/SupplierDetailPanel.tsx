/**
 * Supplier Detail Panel Component
 * Right-side panel with tabs for supplier details
 */

import { OverviewTab } from './tabs/OverviewTab'
import { IssuesCreditsTab } from './tabs/IssuesCreditsTab'
import { PricingTab } from './tabs/PricingTab'
import { DeliveriesTab } from './tabs/DeliveriesTab'
import { NotesAuditTab } from './tabs/NotesAuditTab'
import type { SupplierDetail } from '../../lib/suppliersApi'
import './SupplierDetailPanel.css'

const getScoreColor = (score: string) => {
  switch (score) {
    case 'A':
      return 'green'
    case 'B':
      return 'blue'
    case 'C':
      return 'amber'
    case 'D':
      return 'orange'
    case 'E':
      return 'red'
    default:
      return 'gray'
  }
}

const getStatusColor = (status: string) => {
  switch (status) {
    case 'Active':
      return 'green'
    case 'On Watch':
      return 'amber'
    case 'Blocked':
      return 'red'
    default:
      return 'gray'
  }
}

const formatCurrency = (value: number) => {
  return new Intl.NumberFormat('en-GB', {
    style: 'currency',
    currency: 'GBP',
    maximumFractionDigits: 0,
  }).format(value)
}

const getInitial = (name: string) => {
  return name.charAt(0).toUpperCase()
}

interface SupplierDetailPanelProps {
  supplier: SupplierDetail
  supplierId: string
  activeTab: string
  onTabChange: (tab: string) => void
  loading: boolean
  currentRole: 'GM' | 'Finance' | 'ShiftLead'
}

const TABS = [
  { id: 'overview', label: 'Overview' },
  { id: 'issues', label: 'Issues & Credits' },
  { id: 'pricing', label: 'Pricing' },
  { id: 'deliveries', label: 'Deliveries' },
  { id: 'notes', label: 'Notes & Audit' },
]

export function SupplierDetailPanel({
  supplier,
  supplierId,
  activeTab,
  onTabChange,
  loading,
  currentRole,
}: SupplierDetailPanelProps) {
  if (loading) {
    return (
      <div className="supplier-detail-panel">
        <div className="supplier-detail-panel-loading">Loading supplier details...</div>
      </div>
    )
  }

  const scoreColor = getScoreColor(supplier.score)
  const statusColor = getStatusColor(supplier.status)

  return (
    <div className="supplier-detail-panel">
      {/* Top strip matching card design */}
      <div className="supplier-detail-panel-header">
        <div className="supplier-detail-panel-header-top">
          <div className={`supplier-detail-panel-avatar supplier-detail-panel-avatar-${scoreColor}`}>
            {getInitial(supplier.name)}
          </div>
          <div className="supplier-detail-panel-header-info">
            <div className="supplier-detail-panel-name">{supplier.name}</div>
            <div className="supplier-detail-panel-selected-indicator">Selected from list</div>
          </div>
          <div className={`supplier-detail-panel-grade supplier-detail-panel-grade-${scoreColor}`}>
            {supplier.score}
          </div>
        </div>
        <div className="supplier-detail-panel-header-bottom">
          <div className="supplier-detail-panel-spend">
            {formatCurrency(supplier.totalSpend)}
          </div>
          <div className={`supplier-detail-panel-status supplier-detail-panel-status-${statusColor}`}>
            {supplier.status}
          </div>
        </div>
      </div>

      <div className="supplier-detail-panel-tabs">
        {TABS.map((tab) => (
          <button
            key={tab.id}
            className={`supplier-detail-panel-tab ${
              activeTab === tab.id ? 'active' : ''
            }`}
            onClick={() => onTabChange(tab.id)}
          >
            {tab.label}
          </button>
        ))}
      </div>

      <div className="supplier-detail-panel-content">
        {activeTab === 'overview' && (
          <OverviewTab supplier={supplier} supplierId={supplierId} currentRole={currentRole} />
        )}
        {activeTab === 'issues' && (
          <IssuesCreditsTab supplier={supplier} supplierId={supplierId} currentRole={currentRole} />
        )}
        {activeTab === 'pricing' && (
          <PricingTab supplier={supplier} supplierId={supplierId} currentRole={currentRole} />
        )}
        {activeTab === 'deliveries' && (
          <DeliveriesTab supplier={supplier} supplierId={supplierId} currentRole={currentRole} />
        )}
        {activeTab === 'notes' && (
          <NotesAuditTab supplier={supplier} supplierId={supplierId} currentRole={currentRole} />
        )}
      </div>
    </div>
  )
}

