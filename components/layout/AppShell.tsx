import { Sidebar } from './Sidebar'

interface AppShellProps {
  children: React.ReactNode
}

export default function AppShell({ children }: AppShellProps) {
  return (
    <div className="flex h-screen bg-[var(--ow-bg)]">
      {/* Sidebar with proper z-index */}
      <div className="sticky top-0 z-30 h-screen bg-[var(--ow-card)] border-r border-[var(--ow-border)]">
        <Sidebar />
      </div>
      
      {/* Main content area */}
      <main className="flex-1 overflow-auto">
        {children}
      </main>
    </div>
  )
} 