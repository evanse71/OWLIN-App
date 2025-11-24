import { memo, useState } from 'react'
import './DetailPanelTabs.css'

export type TabId = 'overview' | 'lineItems' | 'issues' | 'pairing'

interface Tab {
  id: TabId
  label: string
  icon?: string
  badge?: number
}

interface DetailPanelTabsProps {
  tabs: Tab[]
  activeTab: TabId
  onTabChange: (tabId: TabId) => void
  children: React.ReactNode
}

export const DetailPanelTabs = memo(function DetailPanelTabs({
  tabs,
  activeTab,
  onTabChange,
  children,
}: DetailPanelTabsProps) {
  return (
    <div className="detail-panel-tabs">
      <div className="detail-panel-tabs-header">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            className={`detail-panel-tab ${activeTab === tab.id ? 'active' : ''}`}
            onClick={() => onTabChange(tab.id)}
            aria-selected={activeTab === tab.id}
          >
            {tab.icon && <span className="detail-panel-tab-icon">{tab.icon}</span>}
            <span>{tab.label}</span>
            {tab.badge !== undefined && tab.badge > 0 && (
              <span className="detail-panel-tab-badge">{tab.badge}</span>
            )}
          </button>
        ))}
      </div>
      <div className="detail-panel-tabs-content">
        {children}
      </div>
    </div>
  )
})

