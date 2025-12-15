import { ReactNode } from 'react'
import { ChatAssistant } from '../ChatAssistant'
import './AppHeader.css'

interface AppHeaderProps {
  children: ReactNode
}

export function AppHeader({ children }: AppHeaderProps) {
  return (
    <header className="app-header">
      <div className="app-header-content">
        <div className="app-header-page-content">
          {children}
        </div>
        <div className="app-header-assistant">
          <ChatAssistant compactInputExternal={true} useSharedState={true} />
        </div>
      </div>
    </header>
  )
}

