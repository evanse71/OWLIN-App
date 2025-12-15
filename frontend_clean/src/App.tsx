/**
 * App Component - Root router with Layout and Sidebar
 * 
 * ACTIVE FRONTEND: frontend_clean (served on port 5176)
 * This is the actual app that localhost:5176 is serving.
 */

import { Routes, Route, Navigate, Outlet } from 'react-router-dom'
import { useState, useEffect } from 'react'
import * as React from 'react'
import { Sidebar } from './components/layout/Sidebar'
import { AppHeader } from './components/layout/AppHeader'
import { Dashboard } from './pages/Dashboard'
import { Invoices } from './pages/Invoices'
import InvoicesGenPage from './pages/InvoicesGenPage'
import { Suppliers } from './pages/Suppliers'
import { Waste } from './pages/Waste'
import { DevDebug } from './pages/DevDebug'
import { ChatAssistant } from './components/ChatAssistant'
import { ErrorBoundary } from './components/ErrorBoundary'
import { ChatAssistantProvider } from './components/ChatAssistantContext'
import './App.css'

function Settings() {
  return (
    <div style={{ padding: '24px', maxWidth: '1200px', margin: '0 auto' }}>
      <h1>Settings</h1>
      <p>Settings page coming soon...</p>
    </div>
  )
}

function Reports() {
  return (
    <div style={{ padding: '24px', maxWidth: '1200px', margin: '0 auto' }}>
      <h1>Reports</h1>
      <p>Reports page coming soon...</p>
    </div>
  )
}

function FlaggedIssues() {
  return (
    <div style={{ padding: '24px', maxWidth: '1200px', margin: '0 auto' }}>
      <h1>Flagged Issues</h1>
      <p>Flagged issues page coming soon...</p>
    </div>
  )
}

function DeliveryNotes() {
  return (
    <div style={{ padding: '24px', maxWidth: '1200px', margin: '0 auto' }}>
      <h1>Delivery Notes</h1>
      <p>Delivery notes page coming soon...</p>
    </div>
  )
}

function Forecasting() {
  return (
    <div style={{ padding: '24px', maxWidth: '1200px', margin: '0 auto' }}>
      <h1>Forecasting</h1>
      <p>Forecasting page coming soon...</p>
    </div>
  )
}

function Notes() {
  return (
    <div style={{ padding: '24px', maxWidth: '1200px', margin: '0 auto' }}>
      <h1>Notes & Logs</h1>
      <p>Notes & logs page coming soon...</p>
    </div>
  )
}

function Products() {
  return (
    <div style={{ padding: '24px', maxWidth: '1200px', margin: '0 auto', minHeight: '100%' }}>
      <AppHeader>
        <h1 style={{ margin: 0 }}>Products</h1>
      </AppHeader>
      <div style={{ marginTop: '24px' }}>
        <h1>Products</h1>
        <p>Products page coming soon. See <code>docs/PRODUCTS_PAGE_SPEC.md</code> for details.</p>
      </div>
    </div>
  )
}

// Layout component with responsive sidebar
function Layout() {
  const [sidebarWidth, setSidebarWidth] = useState(280)
  const [isExpanded, setIsExpanded] = useState(true)
  
  // Mock role - in real app this would come from auth context
  const currentRole: 'GM' | 'Finance' | 'ShiftLead' = 'GM'

  // Set CSS variable for sidebar width so footer can use it
  useEffect(() => {
    const isDesktop = typeof window !== "undefined" && window.innerWidth >= 1024
    if (isDesktop) {
      document.documentElement.style.setProperty('--sidebar-width', `${sidebarWidth}px`)
    } else {
      document.documentElement.style.setProperty('--sidebar-width', '0px')
    }
  }, [sidebarWidth])

  return (
    <div style={{ minHeight: '100vh', display: 'flex' }}>
      <Sidebar 
        currentRole={currentRole} 
        onWidthChange={setSidebarWidth}
        onToggle={setIsExpanded}
      />
      <div style={{ 
        flex: 1,
        display: 'flex',
        flexDirection: 'column',
        paddingLeft: (typeof window !== "undefined" && window.innerWidth >= 1024) ? `${sidebarWidth}px` : '0',
        transition: 'padding-left 300ms cubic-bezier(0.4, 0, 0.2, 1)',
        minWidth: 0,
        width: '100%',
        boxSizing: 'border-box',
        overflowX: 'hidden'
      }}>
        <main style={{ flex: 1, overflow: 'auto', display: 'flex', flexDirection: 'column' }}>
          <Outlet />
        </main>
      </div>
    </div>
  )
}

function App() {
  console.log('[Owlin] App component rendering - Sidebar should be visible')
  
  return (
    <ChatAssistantProvider>
      <div className="App">
        <Routes>
          <Route path="/" element={<Layout />}>
          <Route index element={<Dashboard />} />
          <Route 
            path="invoices" 
            element={
              <ErrorBoundary>
                <Invoices />
              </ErrorBoundary>
            } 
          />
          <Route 
            path="invoices-gen" 
            element={
              <ErrorBoundary>
                <InvoicesGenPage />
              </ErrorBoundary>
            } 
          />
          <Route path="delivery-notes" element={<DeliveryNotes />} />
          <Route path="suppliers" element={<Suppliers />} />
          <Route path="issues" element={<FlaggedIssues />} />
          <Route 
            path="products" 
            element={
              <ErrorBoundary>
                <Products />
              </ErrorBoundary>
            } 
          />
          <Route 
            path="waste" 
            element={
              <ErrorBoundary>
                <Waste />
              </ErrorBoundary>
            } 
          />
          <Route path="reports" element={<Reports />} />
          <Route path="forecasting" element={<Forecasting />} />
          <Route path="notes" element={<Notes />} />
          <Route path="settings" element={<Settings />} />
          <Route path="dev/debug" element={<DevDebug />} />
        </Route>
      </Routes>
      </div>
    </ChatAssistantProvider>
  )
}

export default App
